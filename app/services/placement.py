"""services/placement.py — F3/UC-03: kiểm tra đầu vào và xếp trình độ CEFR.

Chỉ nghiệp vụ, không biết HTTP: router gọi vào đây.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from app.models import (
    Answer,
    Assignment,
    AssignmentQuestion,
    Class,
    Enrollment,
    Lesson,
    Question,
    RubricScore,
    Submission,
    Unit,
    User,
)
from app.services.scoring import (
    adjust_level,
    auto_score,
    cefr_from_score,
    grade_mcq,
    placement_total,
    rubric_total,
)

PLACEMENT_UNIT_CODE = "PL"
PLACEMENT_LESSON_CODE = "PL-25"
RUBRIC_CRITERIA = ["task", "grammar", "vocab", "coherence"]
RUBRIC_LABELS = {
    "task": "Hoàn thành yêu cầu đề",
    "grammar": "Ngữ pháp",
    "vocab": "Từ vựng",
    "coherence": "Liên kết câu",
}


def active_class(db: OrmSession, student_id: int) -> Class | None:
    """Lớp hiện tại của học sinh (BR2: tối đa một lớp đang hoạt động)."""
    row = db.execute(
        select(Class)
        .join(Enrollment, Enrollment.class_id == Class.id)
        .where(Enrollment.student_id == student_id, Enrollment.status == "active")
        .order_by(Enrollment.created_at.desc())
    ).scalars().first()
    return row


def placement_lesson(db: OrmSession) -> Lesson | None:
    return db.execute(select(Lesson).where(Lesson.code == PLACEMENT_LESSON_CODE)).scalar_one_or_none()


def placement_questions(db: OrmSession) -> list[Question]:
    lesson = placement_lesson(db)
    if lesson is None:
        return []
    return list(
        db.execute(select(Question).where(Question.lesson_id == lesson.id).order_by(Question.order_no)).scalars()
    )


def ensure_placement_assignment(db: OrmSession, klass: Class) -> Assignment | None:
    """Bài placement là một assignment kind='placement' gắn với lớp (quyết định mục 3.7).

    Tự tạo lần đầu nếu lớp chưa có — nhờ vậy không phải thêm bảng riêng.
    """
    questions = placement_questions(db)
    if not questions:
        return None

    assignment = db.execute(
        select(Assignment).where(Assignment.class_id == klass.id, Assignment.kind == "placement")
    ).scalars().first()
    if assignment is None:
        assignment = Assignment(
            class_id=klass.id,
            teacher_id=klass.teacher_id,
            kind="placement",
            title="Kiểm tra đầu vào — xếp trình độ CEFR",
            max_attempts=1,  # BR4
            weight_auto=0.7,
            weight_teacher=0.3,
        )
        db.add(assignment)
        db.flush()
        for i, q in enumerate(questions, start=1):
            db.add(AssignmentQuestion(assignment_id=assignment.id, question_id=q.id, order_no=i))
        db.commit()
    return assignment


def student_submission(db: OrmSession, assignment_id: int, student_id: int) -> Submission | None:
    return db.execute(
        select(Submission)
        .where(Submission.assignment_id == assignment_id, Submission.student_id == student_id)
        .order_by(Submission.attempt_no.desc())
    ).scalars().first()


def part_scores(detail: list[dict], questions: list[Question]) -> dict[str, float]:
    """Điểm theo từng phần: ngữ pháp 10, đọc 8, nghe 7 (mục 3.9)."""
    by_id = {q.id: q for q in questions}
    buckets: dict[str, list[bool]] = {}
    for d in detail:
        q = by_id.get(d["question_id"])
        if q is None:
            continue
        buckets.setdefault(q.skill, []).append(d["is_correct"])
    return {skill: auto_score(sum(v), len(v)) for skill, v in buckets.items()}


def submit_placement(
    db: OrmSession, student: User, answers: dict[int, str], essay: str
) -> tuple[Submission | None, str | None]:
    """Nộp bài. Trả (submission, lỗi). Lỗi dạng chuỗi tiếng Việt để router hiển thị."""

    klass = active_class(db, student.id)
    if klass is None:
        return None, "Tài khoản của bạn chưa được ghi danh vào lớp nào."

    assignment = ensure_placement_assignment(db, klass)
    if assignment is None:
        return None, "Chưa có ngân hàng câu hỏi cho bài kiểm tra đầu vào."

    if student_submission(db, assignment.id, student.id) is not None:
        return None, "Bạn đã làm bài kiểm tra đầu vào trong học kỳ này (BR4)."

    questions = placement_questions(db)
    if not answers:
        return None, "Chưa có câu trả lời nào được gửi lên."

    correct, detail = grade_mcq(answers, questions)
    mcq = auto_score(correct, len(questions))

    submission = Submission(
        assignment_id=assignment.id,
        student_id=student.id,
        attempt_no=1,
        status="awaiting_teacher",  # luôn có bài viết cần chấm
        auto_score=mcq,
        text_content=essay.strip(),
    )
    db.add(submission)
    db.flush()
    for d in detail:
        if d["choice"]:
            db.add(Answer(submission_id=submission.id, question_id=d["question_id"],
                          choice=d["choice"], is_correct=d["is_correct"]))
    db.commit()
    db.refresh(submission)
    return submission, None


def grade_placement(
    db: OrmSession,
    submission: Submission,
    rubric: dict[str, float],
    teacher: User,
    level_override: int = 0,
    reason: str = "",
) -> tuple[User | None, str | None]:
    """Giáo viên chấm bài viết theo 4 tiêu chí rồi xác nhận mức CEFR cho học sinh."""

    if submission.status == "graded":
        return None, "Bài này đã chấm. Mở lại phải có lý do và ghi log (UC-03 luồng thay thế)."

    required = set(RUBRIC_CRITERIA)
    if set(rubric) != required:
        return None, "Cần chấm đủ bốn tiêu chí."
    if any(not (0 <= v <= 2.5) for v in rubric.values()):
        return None, "Mỗi tiêu chí cho điểm từ 0 đến 2,5."

    writing = rubric_total(list(rubric.values()))
    if writing < 5.0 and not reason.strip():
        # AC12.2 — điểm dưới trung bình bắt buộc có nhận xét
        return None, "Điểm bài viết dưới 5,0 nên bắt buộc nhập nhận xét."

    for criterion, score in rubric.items():
        db.add(RubricScore(
            submission_id=submission.id,
            criterion=criterion,
            score=score,
            comment=reason.strip(),
            grader_id=teacher.id,
        ))

    total = placement_total(submission.auto_score or 0.0, writing) or 0.0
    proposed = cefr_from_score(total)
    final_level = adjust_level(proposed, level_override)

    submission.teacher_score = writing
    submission.final_score = total
    submission.cefr_proposed = final_level
    submission.status = "graded"
    submission.graded_by = teacher.id
    submission.graded_at = datetime.utcnow()

    student = db.get(User, submission.student_id)
    if student is not None:
        student.cefr_level = final_level

    db.commit()
    db.refresh(submission)
    return student, None


def pending_queue(db: OrmSession, teacher: User) -> list[Submission]:
    """Hàng đợi chấm của giáo viên — chỉ bài của lớp mình phụ trách (BR9)."""
    return list(
        db.execute(
            select(Submission)
            .join(Assignment, Assignment.id == Submission.assignment_id)
            .join(Class, Class.id == Assignment.class_id)
            .where(Class.teacher_id == teacher.id, Submission.status == "awaiting_teacher")
            .order_by(Submission.submitted_at)
        ).scalars()
    )


def class_stats(db: OrmSession, klass: Class) -> dict:
    total = db.execute(
        select(func.count()).select_from(Enrollment).where(
            Enrollment.class_id == klass.id, Enrollment.status == "active"
        )
    ).scalar_one()
    return {"students": total}
