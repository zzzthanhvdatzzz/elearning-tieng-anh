"""services/assignments.py — F11: giao bài có deadline và số lần làm cho cả lớp."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.models import (
    Assignment,
    AssignmentQuestion,
    Class,
    Enrollment,
    Lesson,
    Submission,
    User,
)


def parse_deadline(value: str | None) -> datetime | None:
    """Nhận 'YYYY-MM-DDTHH:MM' từ <input type="datetime-local"> (giờ Việt Nam, không TZ)."""
    if not value:
        return None
    text = value.strip().replace(" ", "T")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt.replace(tzinfo=None)


def create_assignment(
    db: OrmSession,
    teacher: User,
    klass: Class,
    lesson: Lesson | None,
    title: str,
    deadline: datetime | None,
    max_attempts: int,
    kind: str = "practice",
) -> tuple[Assignment | None, str | None]:
    if deadline is not None and deadline <= datetime.utcnow():
        return None, "Hạn nộp phải ở tương lai."
    if max_attempts < 1 or max_attempts > 10:
        return None, "Số lần làm phải từ 1 đến 10."
    if not title.strip():
        return None, "Cần đặt tên cho bài giao."

    assignment = Assignment(
        class_id=klass.id,
        teacher_id=teacher.id,
        kind=kind,
        lesson_id=lesson.id if lesson else None,
        title=title.strip()[:200],
        deadline=deadline,
        max_attempts=int(max_attempts),
        weight_auto=0.0 if kind == "writing" else 1.0,
        weight_teacher=1.0 if kind == "writing" else 0.0,
    )
    db.add(assignment)
    db.flush()

    if lesson is not None:
        for i, q in enumerate(lesson.questions, start=1):
            db.add(AssignmentQuestion(assignment_id=assignment.id, question_id=q.id, order_no=i))
    db.commit()
    db.refresh(assignment)
    return assignment, None


def lessons_for_class(db: OrmSession, klass: Class) -> list[Lesson]:
    from app.models import Unit

    return list(
        db.execute(
            select(Lesson).join(Unit, Unit.id == Lesson.unit_id)
            .where(Unit.grade == klass.grade)
            .order_by(Unit.order_no, Lesson.order_no)
        ).scalars()
    )


def student_todo(db: OrmSession, student: User) -> list[dict]:
    """Bài được giao cho lớp của học sinh, kèm trạng thái làm bài của chính em đó."""
    enrollment = db.execute(
        select(Enrollment).where(Enrollment.student_id == student.id,
                                 Enrollment.status == "active")
    ).scalars().first()
    if enrollment is None:
        return []

    assignments = list(
        db.execute(
            select(Assignment)
            .where(Assignment.class_id == enrollment.class_id,
                   Assignment.kind != "placement")   # placement có màn hình riêng
            .order_by(Assignment.deadline.is_(None), Assignment.deadline)
        ).scalars()
    )
    out = []
    for a in assignments:
        subs = list(
            db.execute(
                select(Submission).where(Submission.assignment_id == a.id,
                                         Submission.student_id == student.id)
                .order_by(Submission.attempt_no.desc())
            ).scalars()
        )
        best = max((s.final_score for s in subs if s.final_score is not None), default=None)
        out.append({
            "assignment": a,
            "attempts_used": len(subs),
            "attempts_left": max(0, a.max_attempts - len(subs)),
            "best": best,
            "last": subs[0] if subs else None,
            "overdue": bool(a.deadline and a.deadline < datetime.utcnow()),
        })
    return out
