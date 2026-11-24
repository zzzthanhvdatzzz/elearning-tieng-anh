"""services/speaking_queue.py — hàng đợi chấm bài nói cho giáo viên (nửa còn lại của F7).

Trước đây học sinh nộp được bài nói nhưng giáo viên không có chỗ nào để nghe và cho điểm,
nên bài nằm mãi ở trạng thái chờ. Module này gom bài theo lớp + bài học để giáo viên chấm.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.models import Assignment, Class, Enrollment, Lesson, Submission, User


def _teacher_student_ids(db: OrmSession, teacher: User) -> list[int]:
    return [
        row.student_id
        for row in db.execute(
            select(Enrollment).join(Class, Class.id == Enrollment.class_id)
            .where(Class.teacher_id == teacher.id)
        ).scalars()
    ]


def queue(db: OrmSession, teacher: User, only_pending: bool = True) -> list[dict]:
    ids = _teacher_student_ids(db, teacher)
    if not ids:
        return []
    rows = db.execute(
        select(Submission, Assignment, User, Lesson, Class)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .join(User, User.id == Submission.student_id)
        .join(Class, Class.id == Assignment.class_id)
        .outerjoin(Lesson, Lesson.id == Assignment.lesson_id)
        .where(Assignment.kind == "speaking", Submission.student_id.in_(ids))
        .order_by(Submission.id.desc())
    ).all()

    out = []
    for sub, assignment, student, lesson, klass in rows:
        if only_pending and sub.status == "graded":
            continue
        out.append({
            "id": sub.id,
            "student": student.full_name or student.email,
            "student_id": student.id,
            "klass": klass.name,
            "lesson": lesson.title if lesson else assignment.title,
            "status": sub.status,
            "attempt_no": sub.attempt_no,
            "score": sub.final_score,
            "late_days": sub.late_days,
            "at": sub.submitted_at.strftime("%d/%m %H:%M") if sub.submitted_at else "",
            "has_audio": bool(sub.audio_path),
        })
    return out


def detail(db: OrmSession, teacher: User, submission_id: int) -> dict | None:
    ids = _teacher_student_ids(db, teacher)
    sub = db.get(Submission, submission_id)
    if sub is None or sub.student_id not in ids:
        return None
    assignment = db.get(Assignment, sub.assignment_id)
    if assignment is None or assignment.kind != "speaking":
        return None
    student = db.get(User, sub.student_id)
    lesson = db.get(Lesson, assignment.lesson_id) if assignment.lesson_id else None
    return {
        "id": sub.id, "status": sub.status, "attempt_no": sub.attempt_no,
        "student": student.full_name or student.email if student else "",
        "lesson": lesson.title if lesson else assignment.title,
        "audio": f"/api/submissions/{sub.id}/audio" if sub.audio_path else None,
        "audio_name": Path(sub.audio_path).name if sub.audio_path else None,
        "score": sub.final_score, "late_days": sub.late_days,
        "deadline": assignment.deadline.strftime("%d/%m/%Y %H:%M") if assignment.deadline else None,
    }
