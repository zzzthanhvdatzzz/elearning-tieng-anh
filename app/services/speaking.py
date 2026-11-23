"""services/speaking.py — F7: nộp bài nói (ghi âm hoặc tải file lên).

Phương án dự phòng khi trình duyệt chặn micro (rủi ro R2): học sinh ghi âm bằng điện thoại
rồi tải file lên. Hai đường vào, cùng một chỗ lưu.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from app.models import Assignment, Class, Submission, User
from app.services.learning import lesson_detail
from app.services.placement import active_class
from app.services.storage import save_audio

DEFAULT_MAX_ATTEMPTS = 2


def ensure_speaking_assignment(db: OrmSession, klass, lesson) -> Assignment:
    assignment = db.execute(
        select(Assignment).where(Assignment.class_id == klass.id,
                                 Assignment.kind == "speaking",
                                 Assignment.lesson_id == lesson.id)
    ).scalars().first()
    if assignment is not None:
        return assignment
    assignment = Assignment(
        class_id=klass.id, teacher_id=klass.teacher_id, kind="speaking",
        lesson_id=lesson.id, title=f"Bài nói — {lesson.title}",
        max_attempts=DEFAULT_MAX_ATTEMPTS, weight_auto=0.0, weight_teacher=1.0,
    )
    db.add(assignment)
    db.commit()
    return assignment


def speaking_state(db: OrmSession, student: User, lesson_id: int) -> dict | None:
    detail = lesson_detail(db, student, lesson_id)
    if detail is None:
        return None
    lesson = detail["lesson"]
    klass = active_class(db, student.id)
    if klass is None:
        return None
    assignment = ensure_speaking_assignment(db, klass, lesson)

    used = db.execute(
        select(func.count()).select_from(Submission).where(
            Submission.assignment_id == assignment.id, Submission.student_id == student.id)
    ).scalar_one()
    last = db.execute(
        select(Submission).where(Submission.assignment_id == assignment.id,
                                 Submission.student_id == student.id)
        .order_by(Submission.attempt_no.desc())
    ).scalars().first()

    prompt = detail["content"].get("speaking_prompt") or (
        f"Nói 45–60 giây bằng tiếng Anh về chủ đề: {lesson.title}. "
        "Nêu 2 ý chính, nói rõ ràng và đủ to."
    )
    return {"lesson": lesson, "assignment": assignment, "prompt": prompt,
            "attempts_used": used, "attempts_left": max(0, assignment.max_attempts - used),
            "last": last}


def submit_speaking(db: OrmSession, student: User, lesson_id: int, filename: str,
                    data: bytes, use_recorder: bool = True) -> tuple[Submission | None, str | None]:
    state = speaking_state(db, student, lesson_id)
    if state is None:
        return None, "Không tìm thấy bài học."
    if state["attempts_left"] <= 0:
        return None, "Bạn đã hết lượt nộp bài nói này."

    path, error = save_audio(student.id, lesson_id, filename, data)
    if error:
        return None, error

    submission = Submission(
        assignment_id=state["assignment"].id,
        student_id=student.id,
        attempt_no=state["attempts_used"] + 1,
        status="awaiting_teacher",
        audio_path=path,
        text_content="",   # bài nói không có văn bản; để trống cho rõ
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission, None
