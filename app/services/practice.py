"""services/practice.py — F9/UC-05: luyện tập trắc nghiệm và chấm tự động.

Tái dùng `grade_mcq`/`auto_score` của services/scoring.py: KHÔNG viết lại công thức ở đây
(BR5 chỉ có một chỗ duy nhất — mục 2.4).

Bài luyện tập cũng là một `assignment` kind='practice' gắn với lớp và bài học, tạo lười
lần đầu giống placement: nhờ vậy mọi điểm số đều nằm trong `submissions` và báo cáo (F13)
chỉ cần đọc một bảng.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from app.models import (
    Answer,
    Assignment,
    AssignmentQuestion,
    Question,
    Submission,
    User,
)
from app.services.learning import lesson_detail
from app.services.placement import active_class
from app.services.scoring import auto_score, days_late, grade_mcq, with_late_penalty

DEFAULT_MAX_ATTEMPTS = 3  # BR7: cấu hình mặc định của bài luyện tập


def lesson_questions(db: OrmSession, lesson_id: int) -> list[Question]:
    return list(
        db.execute(
            select(Question).where(Question.lesson_id == lesson_id).order_by(Question.order_no)
        ).scalars()
    )


def ensure_practice_assignment(db: OrmSession, klass, lesson, questions: list[Question]) -> Assignment:
    assignment = db.execute(
        select(Assignment).where(
            Assignment.class_id == klass.id,
            Assignment.kind == "practice",
            Assignment.lesson_id == lesson.id,
        )
    ).scalars().first()
    if assignment is not None:
        return assignment

    assignment = Assignment(
        class_id=klass.id,
        teacher_id=klass.teacher_id,
        kind="practice",
        lesson_id=lesson.id,
        title=f"Luyện tập — {lesson.title}",
        max_attempts=DEFAULT_MAX_ATTEMPTS,
        weight_auto=1.0,   # BR6: không có phần giáo viên chấm → điểm cuối = điểm tự động
        weight_teacher=0.0,
    )
    db.add(assignment)
    db.flush()
    for i, q in enumerate(questions, start=1):
        db.add(AssignmentQuestion(assignment_id=assignment.id, question_id=q.id, order_no=i))
    db.commit()
    return assignment


def practice_state(db: OrmSession, student: User, lesson_id: int) -> dict | None:
    """Trả None nếu bài không thuộc khối lớp của học sinh (chặn IDOR)."""
    detail = lesson_detail(db, student, lesson_id)
    if detail is None:
        return None
    lesson = detail["lesson"]
    questions = lesson_questions(db, lesson.id)
    klass = active_class(db, student.id)
    if klass is None or not questions:
        return None

    assignment = ensure_practice_assignment(db, klass, lesson, questions)
    used = db.execute(
        select(func.count()).select_from(Submission).where(
            Submission.assignment_id == assignment.id, Submission.student_id == student.id
        )
    ).scalar_one()
    last = db.execute(
        select(Submission)
        .where(Submission.assignment_id == assignment.id, Submission.student_id == student.id)
        .order_by(Submission.attempt_no.desc())
    ).scalars().first()

    return {
        "lesson": lesson,
        "questions": questions,
        "assignment": assignment,
        "attempts_used": used,
        "attempts_left": max(0, assignment.max_attempts - used),
        "last": last,
    }


def submit_practice(
    db: OrmSession, student: User, lesson_id: int, answers: dict[int, str]
) -> tuple[Submission | None, str | None]:
    state = practice_state(db, student, lesson_id)
    if state is None:
        return None, "Không tìm thấy bài học."
    assignment = state["assignment"]
    if state["attempts_left"] <= 0:
        # BR7: từ chối ở SERVER, không chỉ ẩn nút trên giao diện
        return None, "Bạn đã hết lượt làm bài này."
    if not answers:
        return None, "Chưa có câu trả lời nào được gửi lên."

    questions = state["questions"]
    correct, detail = grade_mcq(answers, questions)
    raw = auto_score(correct, len(questions))

    late = days_late(datetime.utcnow(), assignment.deadline)
    final = with_late_penalty(raw, late)

    submission = Submission(
        assignment_id=assignment.id,
        student_id=student.id,
        attempt_no=state["attempts_used"] + 1,
        status="graded",          # chỉ có phần tự động → chấm xong ngay
        auto_score=raw,
        final_score=final,
        late_days=late,
        graded_at=datetime.utcnow(),
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


def submission_review(db: OrmSession, submission: Submission) -> list[dict]:
    """Chi tiết từng câu để hiện sau khi nộp: đã chọn gì, đáp án, giải thích."""
    by_id = {q.id: q for q in lesson_questions(db, _lesson_id_of(db, submission))}
    chosen = {a.question_id: a for a in submission.answers}
    out = []
    for q in by_id.values():
        a = chosen.get(q.id)
        out.append({
            "question": q,
            "choice": a.choice if a else "",
            "is_correct": bool(a and a.is_correct),
        })
    return out


def _lesson_id_of(db: OrmSession, submission: Submission) -> int:
    assignment = db.get(Assignment, submission.assignment_id)
    return assignment.lesson_id if assignment else 0


def history(db: OrmSession, student: User, lesson_id: int) -> list[Submission]:
    state = practice_state(db, student, lesson_id)
    if state is None:
        return []
    return list(
        db.execute(
            select(Submission)
            .where(Submission.assignment_id == state["assignment"].id,
                   Submission.student_id == student.id)
            .order_by(Submission.attempt_no)
        ).scalars()
    )
