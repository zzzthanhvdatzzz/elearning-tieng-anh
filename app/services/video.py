"""services/video.py — video bài giảng: link YouTube/Drive hoặc file giáo viên tự quay.

Vì sao KHÔNG lưu video vào CSDL: file 100 MB không thuộc về SQLite. Tệp nằm trên đĩa
(`data/uploads/video/<lesson_id>/`), CSDL chỉ giữ đường dẫn.

Vì sao có cả hai đường: giáo viên thường đã có video trên YouTube (nhanh, không tốn ổ đĩa,
không tốn băng thông), nhưng bài giảng tự quay trên lớp thì không muốn đăng công khai.
"""
from __future__ import annotations

import re
import secrets
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.db import BASE_DIR
from app.models import Class, Enrollment, Lesson, Unit, User

VIDEO_DIR = Path(BASE_DIR) / "data" / "uploads" / "video"
MAX_VIDEO_BYTES = 200 * 1024 * 1024          # 200 MB — đủ một tiết 20 phút nén tốt
ALLOWED_VIDEO_EXT = {".mp4", ".webm", ".mov", ".m4v"}

_YOUTUBE = [
    re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([\w-]{6,20})"),
]
_DRIVE = re.compile(r"drive\.google\.com/file/d/([\w-]{10,})")


def parse_link(url: str) -> tuple[str | None, str | None]:
    """Trả (url_đã_chuẩn_hoá, lỗi). Chấp nhận YouTube (watch/youtu.be/embed/shorts) và Drive."""
    url = (url or "").strip()
    if not url:
        return None, "Chưa nhập link."
    if not url.startswith(("http://", "https://")):
        return None, "Link phải bắt đầu bằng http:// hoặc https://"

    for pattern in _YOUTUBE:
        m = pattern.search(url)
        if m:
            vid = m.group(1)
            return f"https://www.youtube.com/embed/{vid}", None
    if "/shorts/" in url:
        vid = url.split("/shorts/")[1].split("?")[0].strip("/")
        if vid:
            return f"https://www.youtube.com/embed/{vid}", None

    m = _DRIVE.search(url)
    if m:
        return f"https://drive.google.com/file/d/{m.group(1)}/preview", None

    return None, "Chỉ hỗ trợ link YouTube (watch/youtu.be/shorts) hoặc Google Drive."


def save_video(lesson_id: int, filename: str, data: bytes) -> tuple[str | None, str | None]:
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_VIDEO_EXT:
        return None, (f"Định dạng {ext or '(không rõ)'} không hỗ trợ. "
                      f"Chấp nhận: {', '.join(sorted(ALLOWED_VIDEO_EXT))}")
    if not data:
        return None, "File rỗng."
    if len(data) > MAX_VIDEO_BYTES:
        return None, f"Video vượt quá {MAX_VIDEO_BYTES // (1024 * 1024)} MB."

    folder = VIDEO_DIR / str(lesson_id)
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{secrets.token_hex(8)}{ext}"
    (folder / name).write_bytes(data)
    return f"video/{lesson_id}/{name}", None


def video_path_of(relative: str | None) -> Path | None:
    if not relative:
        return None
    return Path(BASE_DIR) / "data" / "uploads" / relative


def grades_of_teacher(db: OrmSession, teacher: User) -> set[int]:
    return {k.grade for k in db.execute(
        select(Class).where(Class.teacher_id == teacher.id)).scalars()}


def grades_of_student(db: OrmSession, student: User) -> set[int]:
    return {k.grade for k in db.execute(
        select(Class).join(Enrollment, Enrollment.class_id == Class.id).where(
            Enrollment.student_id == student.id)).scalars()}


def lesson_grade(db: OrmSession, lesson: Lesson) -> int | None:
    unit = db.get(Unit, lesson.unit_id)
    return unit.grade if unit else None


def can_manage(db: OrmSession, teacher: User, lesson: Lesson) -> bool:
    grade = lesson_grade(db, lesson)
    return grade is not None and grade in grades_of_teacher(db, teacher)


def can_view(db: OrmSession, user: User, lesson: Lesson) -> bool:
    """Học sinh xem video của khối mình học; giáo viên dạy khối đó; quản trị xem được."""
    if user.role == "admin":
        return True
    grade = lesson_grade(db, lesson)
    if grade is None:
        return False
    if user.role == "teacher":
        return grade in grades_of_teacher(db, user)
    if user.role == "student":
        return grade in grades_of_student(db, user)
    return False


def info(lesson: Lesson) -> dict:
    if lesson.video_url:
        return {"kind": "embed", "embed_url": lesson.video_url,
                "title": lesson.video_title or "", "stream": None}
    if lesson.video_path:
        return {"kind": "file", "embed_url": None,
                "title": lesson.video_title or "",
                "stream": f"/api/lessons/{lesson.id}/video/stream"}
    return {"kind": None, "embed_url": None, "title": "", "stream": None}


# ------------------------------------------------------------------ theo dõi đã xem
COMPLETE_RATIO = 0.8          # xem ≥ 80% thời lượng mới tính hoàn thành
MAX_HEARTBEAT_DELTA = 20      # một nhịp tim chỉ được cộng tối đa 20 giây (chặn nhảy cóc)
HEARTBEAT_EVERY = 10          # client gửi mỗi 10 giây


def _row(db: OrmSession, student_id: int, lesson_id: int):
    from app.models import VideoProgress

    return db.execute(
        select(VideoProgress).where(VideoProgress.student_id == student_id,
                                    VideoProgress.lesson_id == lesson_id)
    ).scalar_one_or_none()


def record_heartbeat(db: OrmSession, student: User, lesson: Lesson, position: float,
                     duration: float) -> tuple[dict | None, str | None]:
    """Ghi nhận một nhịp xem. Chỉ cộng phần CHÊNH LỆCH HỢP LỆ, không cộng cú tua.

    Quy tắc chống tua:
    - delta = vị_trí_mới − vị_trí_xa_nhất_đã_xem; nếu delta < 0 (tua lùi) → không cộng.
    - nếu delta > MAX_HEARTBEAT_DELTA (tua tới) → chỉ cộng MAX_HEARTBEAT_DELTA, và KHÔNG
      dời mốc `position` theo cú tua (người học phải xem tiếp từ chỗ cũ).
    """
    from datetime import datetime

    from app.models import VideoProgress

    if duration <= 0:
        return None, "Thiếu thời lượng video."
    if position < 0:
        position = 0
    duration = int(round(duration))
    position = int(round(position))

    row = _row(db, student.id, lesson.id)
    if row is None:
        row = VideoProgress(student_id=student.id, lesson_id=lesson.id,
                            watched_seconds=0, duration_seconds=duration, position=0)
        db.add(row)
        db.flush()

    delta = position - row.position
    if delta > 0:
        credited = min(delta, MAX_HEARTBEAT_DELTA)
        row.watched_seconds = min(row.watched_seconds + credited, duration * 2)
        row.position = min(row.position + credited, duration)
    row.duration_seconds = duration or row.duration_seconds

    target = row.duration_seconds * COMPLETE_RATIO
    if row.completed_at is None and row.watched_seconds >= target:
        row.completed_at = datetime.utcnow()
    db.commit()
    return progress_of(db, student, lesson), None


def progress_of(db: OrmSession, student: User, lesson: Lesson) -> dict:
    row = _row(db, student.id, lesson.id)
    if row is None:
        return {"watched_seconds": 0, "duration_seconds": 0, "position": 0,
                "percent": 0, "completed": False, "needed_seconds": 0}
    duration = row.duration_seconds or 0
    percent = min(100, round(100 * row.watched_seconds / duration)) if duration else 0
    return {
        "watched_seconds": row.watched_seconds,
        "duration_seconds": duration,
        "position": row.position,
        "percent": percent,
        "completed": row.completed_at is not None,
        "needed_seconds": max(0, int(duration * COMPLETE_RATIO) - row.watched_seconds),
    }
