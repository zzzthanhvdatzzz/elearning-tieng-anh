"""services/writing.py — F8: luyện viết, nháp, nộp bài; giáo viên chấm rubric.

Bài viết là một `assignment` kind='writing' gắn lớp + bài học (tạo lười như placement),
trọng số 0/1: chỉ giáo viên chấm nên điểm cuối = điểm rubric (BR6).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from app.models import Assignment, Class, Submission, User
from app.services.grading import grade_writing  # noqa: F401  (dùng lại qua router)
from app.services.learning import lesson_detail
from app.services.placement import active_class
from app.services.scoring import days_late, with_late_penalty

MIN_WORDS = 40       # dưới ngưỡng này giáo viên nhận cảnh báo (mục 3.9)
DEFAULT_MAX_ATTEMPTS = 2


def ensure_writing_assignment(db: OrmSession, klass, lesson) -> Assignment:
    assignment = db.execute(
        select(Assignment).where(
            Assignment.class_id == klass.id,
            Assignment.kind == "writing",
            Assignment.lesson_id == lesson.id,
        )
    ).scalars().first()
    if assignment is not None:
        return assignment
    assignment = Assignment(
        class_id=klass.id,
        teacher_id=klass.teacher_id,
        kind="writing",
        lesson_id=lesson.id,
        title=f"Bài viết — {lesson.title}",
        max_attempts=DEFAULT_MAX_ATTEMPTS,
        weight_auto=0.0,
        weight_teacher=1.0,
    )
    db.add(assignment)
    db.commit()
    return assignment


def writing_state(db: OrmSession, student: User, lesson_id: int) -> dict | None:
    detail = lesson_detail(db, student, lesson_id)
    if detail is None:
        return None
    lesson = detail["lesson"]
    klass = active_class(db, student.id)
    if klass is None:
        return None

    assignment = ensure_writing_assignment(db, klass, lesson)
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

    prompt = detail["content"].get("writing_prompt") or (
        f"Viết một đoạn văn tiếng Anh khoảng 80 từ về chủ đề: {lesson.title}. "
        "Nêu 2–3 ý chính và kết bằng một câu cảm nhận của em."
    )
    return {
        "lesson": lesson,
        "assignment": assignment,
        "prompt": prompt,
        "attempts_used": used,
        "attempts_left": max(0, assignment.max_attempts - used),
        "last": last,
        "min_words": MIN_WORDS,
    }


def word_count(text: str) -> int:
    return len(text.split()) if text.strip() else 0


def submit_writing(
    db: OrmSession, student: User, lesson_id: int, text: str
) -> tuple[Submission | None, str | None]:
    state = writing_state(db, student, lesson_id)
    if state is None:
        return None, "Không tìm thấy bài học."
    if state["attempts_left"] <= 0:
        return None, "Bạn đã hết lượt nộp bài viết này."

    words = word_count(text)
    if words < 20:
        return None, f"Bài viết quá ngắn ({words} từ). Hãy viết ít nhất 20 từ trước khi nộp."

    assignment = state["assignment"]
    late = days_late(datetime.utcnow(), assignment.deadline)

    submission = Submission(
        assignment_id=assignment.id,
        student_id=student.id,
        attempt_no=state["attempts_used"] + 1,
        status="awaiting_teacher",   # chờ giáo viên chấm rubric
        text_content=text.strip(),
        auto_score=None,
        late_days=late,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission, None


def teacher_queue(db: OrmSession, teacher: User) -> list[Submission]:
    """Hàng đợi chấm: bài viết + bài nói của lớp mình (BR9)."""
    return list(
        db.execute(
            select(Submission)
            .join(Assignment, Assignment.id == Submission.assignment_id)
            .join(Class, Class.id == Assignment.class_id)
            .where(
                Class.teacher_id == teacher.id,
                Submission.status == "awaiting_teacher",
                Assignment.kind.in_(("writing", "speaking")),
            )
            .order_by(Submission.submitted_at)
        ).scalars()
    )


def student_of(db: OrmSession, submission: Submission) -> User | None:
    return db.get(User, submission.student_id)


def late_note(submission: Submission, assignment: Assignment) -> float | None:
    """Điểm sau trừ muộn — chỉ để hiển thị cảnh báo, BR8 áp khi tính điểm cuối."""
    if submission.teacher_score is None or not assignment.deadline:
        return None
    return with_late_penalty(submission.teacher_score, submission.late_days)
