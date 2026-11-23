"""services/learning.py — F5/F6: lộ trình theo Unit và ghi nhận tiến độ học.

Ghi cả phần trăm VÀ số giây (quyết định ở mục 3.7): phần trăm một mình không phân biệt
được người học 5 phút với người học 50 phút.
"""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.models import Lesson, Progress, Unit, User
from app.services.placement import active_class

MAX_SECONDS_PER_PING = 3600  # chặn client gửi số giây vô lý (tab ngủ 8 tiếng)


def student_grade(db: OrmSession, student: User) -> int | None:
    klass = active_class(db, student.id)
    return klass.grade if klass else None


def units_for_student(db: OrmSession, student: User) -> list[dict]:
    """Các Unit của đúng khối lớp học sinh, kèm % hoàn thành từng bài."""
    grade = student_grade(db, student)
    if grade is None:
        return []

    units = list(
        db.execute(select(Unit).where(Unit.grade == grade).order_by(Unit.order_no)).scalars()
    )
    progress_rows = {
        p.lesson_id: p
        for p in db.execute(select(Progress).where(Progress.student_id == student.id)).scalars()
    }

    out = []
    for unit in units:
        lessons = list(
            db.execute(select(Lesson).where(Lesson.unit_id == unit.id).order_by(Lesson.order_no)).scalars()
        )
        items = []
        done = 0
        for lesson in lessons:
            p = progress_rows.get(lesson.id)
            percent = p.percent if p else 0
            done += int(percent >= 100)
            items.append({"lesson": lesson, "percent": percent, "seconds": p.seconds if p else 0})
        out.append({
            "unit": unit,
            "lessons": items,
            "percent": round(100 * done / len(items)) if items else 0,
        })
    return out


def next_lesson(db: OrmSession, student: User) -> dict | None:
    """Bài gợi ý tiếp theo: bài đầu tiên chưa hoàn thành."""
    for unit in units_for_student(db, student):
        for item in unit["lessons"]:
            if item["percent"] < 100:
                return {"unit": unit["unit"], **item}
    return None


def lesson_detail(db: OrmSession, student: User, lesson_id: int) -> dict | None:
    """Trả dữ liệu bài học nếu bài thuộc khối lớp của học sinh; ngược lại None.

    Chặn ở service, không tin vào id do client gửi (chống IDOR — NFR3).
    """
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        return None
    grade = student_grade(db, student)
    if grade is None:
        return None
    unit = db.get(Unit, lesson.unit_id)
    if unit is None or unit.grade != grade:
        return None

    content = {}
    if lesson.content:
        try:
            content = json.loads(lesson.content)
        except json.JSONDecodeError:
            content = {}

    p = db.execute(
        select(Progress).where(Progress.student_id == student.id, Progress.lesson_id == lesson.id)
    ).scalar_one_or_none()

    return {
        "lesson": lesson,
        "unit": unit,
        "content": content,
        "percent": p.percent if p else 0,
        "seconds": p.seconds if p else 0,
    }


def add_progress(
    db: OrmSession,
    student: User,
    lesson_id: int,
    seconds: int = 0,
    percent: int | None = None,
    completed: bool = False,
) -> dict:
    """Cộng dồn thời gian học. Phần trăm chỉ tăng, không bao giờ giảm; kẹp 0–100."""
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise ValueError("lesson_not_found")

    row = db.execute(
        select(Progress).where(Progress.student_id == student.id, Progress.lesson_id == lesson_id)
    ).scalar_one_or_none()
    if row is None:
        row = Progress(student_id=student.id, lesson_id=lesson_id, percent=0, seconds=0)
        db.add(row)
        db.flush()

    if seconds and seconds > 0:
        row.seconds += min(int(seconds), MAX_SECONDS_PER_PING)
    if percent is not None:
        row.percent = max(row.percent, min(100, max(0, int(percent))))
    if completed:
        row.percent = 100
    row.last_seen_at = datetime.utcnow()

    db.commit()
    db.refresh(row)
    return {"percent": row.percent, "seconds": row.seconds}


def progress_summary(db: OrmSession, student: User) -> dict:
    """Số liệu cho dashboard S4: thời gian tuần này, số bài hoàn thành."""
    rows = list(db.execute(select(Progress).where(Progress.student_id == student.id)).scalars())
    return {
        "lessons_started": len(rows),
        "lessons_done": sum(1 for r in rows if r.percent >= 100),
        "total_seconds": sum(r.seconds for r in rows),
    }
