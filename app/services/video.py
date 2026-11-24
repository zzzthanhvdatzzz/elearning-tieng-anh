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
CHECKPOINT_RATIO = 0.5        # tới 50% thì dừng lại hỏi một câu
MAX_HEARTBEAT_DELTA = 20      # một nhịp tim chỉ được cộng tối đa 20 giây (chặn nhảy cóc)
HEARTBEAT_EVERY = 10          # client gửi mỗi 10 giây
CLOCK_GRACE = 8               # dung sai đồng hồ: nhịp 10 giây có thể tới trễ/sớm vài giây


def _row(db: OrmSession, student_id: int, lesson_id: int):
    from app.models import VideoProgress

    return db.execute(
        select(VideoProgress).where(VideoProgress.student_id == student_id,
                                    VideoProgress.lesson_id == lesson_id)
    ).scalar_one_or_none()


def record_heartbeat(db: OrmSession, student: User, lesson: Lesson, position: float,
                     duration: float) -> tuple[dict | None, str | None]:
    """Ghi nhận một nhịp xem. Chỉ cộng phần CHÊNH LỆCH HỢP LỆ, không cộng cú tua.

    Ba lớp chặn:
    1. delta < 0 (tua lùi) → không cộng.
    2. delta > MAX_HEARTBEAT_DELTA (tua tới) → chỉ cộng 20 giây, không dời mốc xem.
    3. delta > thời_gian_thực_đã_trôi + CLOCK_GRACE → chỉ cộng phần thời gian thực.
       Lớp 3 là để chặn trò mở Console bắn liên tiếp nhiều request trong 1 giây.
    """
    from datetime import datetime

    from app.models import VideoProgress

    if duration <= 0:
        return None, "Thiếu thời lượng video."
    if position < 0:
        position = 0
    duration = int(round(duration))
    position = int(round(position))
    now = datetime.utcnow()

    row = _row(db, student.id, lesson.id)
    fresh = row is None
    if fresh:
        row = VideoProgress(student_id=student.id, lesson_id=lesson.id,
                            watched_seconds=0, duration_seconds=duration, position=0,
                            started_at=now)
        db.add(row)
        db.flush()
    if row.started_at is None:
        row.started_at = now

    delta = position - row.position
    if delta > 0:
        elapsed = (now - row.updated_at).total_seconds() if not fresh else CLOCK_GRACE
        by_last = max(0, int(elapsed) + CLOCK_GRACE)
        # Trần tổng: không thể xem nhiều hơn thời gian thực đã trôi kể từ lần đầu bật video.
        # Đây là lớp chặn trò bắn liên tiếp nhiều request để cộng dồn.
        since_start = (now - row.started_at).total_seconds() + CLOCK_GRACE
        headroom = max(0, int(since_start) - row.watched_seconds)
        credited = max(0, min(delta, MAX_HEARTBEAT_DELTA, by_last, headroom))
        row.watched_seconds = min(row.watched_seconds + credited, duration * 2)
        row.position = min(row.position + credited, duration)
    row.duration_seconds = duration or row.duration_seconds

    if row.completed_at is None and _is_complete(db, row, lesson):
        row.completed_at = now
    db.commit()
    return progress_of(db, student, lesson), None


def checkpoint_question(db: OrmSession, lesson: Lesson):
    """Câu hỏi kiểm tra giữa video: dùng câu hỏi đầu tiên có sẵn của bài học.

    Không bắt giáo viên soạn thêm gì — mọi bài đã có câu hỏi luyện tập.
    """
    rows = list(lesson.questions)
    return rows[0] if rows else None


def _is_complete(db: OrmSession, row, lesson: Lesson) -> bool:
    """Hoàn thành = xem ≥ 80% VÀ (bài không có câu hỏi, hoặc đã trả lời đúng câu giữa video)."""
    if not row.duration_seconds:
        return False
    if row.watched_seconds < row.duration_seconds * COMPLETE_RATIO:
        return False
    if checkpoint_question(db, lesson) is None:
        return True
    return bool(row.checkpoint_passed)


def answer_checkpoint(db: OrmSession, student: User, lesson: Lesson,
                      answer: str) -> tuple[dict | None, str | None]:
    """Trả lời câu hỏi kiểm tra. Sai thì cho thử lại, nhưng chưa được tính hoàn thành."""
    from datetime import datetime

    question = checkpoint_question(db, lesson)
    if question is None:
        return None, "Bài này không có câu hỏi kiểm tra."
    row = _row(db, student.id, lesson.id)
    if row is None or row.watched_seconds < row.duration_seconds * CHECKPOINT_RATIO:
        return None, "Bạn cần xem tới 50% video trước khi trả lời."

    row.checkpoint_tries = (row.checkpoint_tries or 0) + 1
    correct = (answer or "").strip().upper() == (question.correct_key or "").upper()
    if correct:
        row.checkpoint_passed = True
        row.checkpoint_question_id = question.id
    if row.completed_at is None and _is_complete(db, row, lesson):
        row.completed_at = datetime.utcnow()
    db.commit()
    return {"correct": correct, **progress_of(db, student, lesson)}, None


def student_summary(db: OrmSession, student: User) -> dict:
    """Tổng hợp video cho học sinh: bao nhiêu bài có video, đã xem xong bao nhiêu, tổng giây.

    Dùng cho trang tổng quan và báo cáo — trước đây bảng video_progress có dữ liệu nhưng
    không nơi nào đọc, nên xem video xong hệ thống vẫn báo "chưa học gì".
    """
    from app.models import VideoProgress

    grades = grades_of_student(db, student)
    if not grades:
        return {"videos_total": 0, "videos_completed": 0, "watched_seconds": 0,
                "percent": 0, "items": []}

    lessons = list(db.execute(
        select(Lesson).join(Unit, Unit.id == Lesson.unit_id).where(Unit.grade.in_(grades))
    ).scalars())
    with_video = [ls for ls in lessons if ls.video_url or ls.video_path]
    ids = [ls.id for ls in with_video]

    rows = {}
    if ids:
        for row in db.execute(select(VideoProgress).where(
                VideoProgress.student_id == student.id,
                VideoProgress.lesson_id.in_(ids))).scalars():
            rows[row.lesson_id] = row

    completed = [ls for ls in with_video if rows.get(ls.id) and rows[ls.id].completed_at]
    watched = sum(r.watched_seconds for lid, r in rows.items() if lid in ids)
    return {
        "videos_total": len(with_video),
        "videos_completed": len(completed),
        "watched_seconds": watched,
        "percent": round(100 * len(completed) / len(with_video)) if with_video else 0,
        "items": [
            {"lesson_id": ls.id, "title": ls.title,
             "percent": min(100, round(100 * rows[ls.id].watched_seconds
                                       / rows[ls.id].duration_seconds))
             if rows.get(ls.id) and rows[ls.id].duration_seconds else 0,
             "completed": bool(rows.get(ls.id) and rows[ls.id].completed_at)}
            for ls in with_video
        ],
    }


def progress_of(db: OrmSession, student: User, lesson: Lesson) -> dict:
    row = _row(db, student.id, lesson.id)
    if row is None:
        return {"watched_seconds": 0, "duration_seconds": 0, "position": 0,
                "percent": 0, "completed": False, "needed_seconds": 0,
                "needs_checkpoint": False, "checkpoint_passed": False}
    duration = row.duration_seconds or 0
    percent = min(100, round(100 * row.watched_seconds / duration)) if duration else 0
    q = checkpoint_question(db, lesson)
    needs = bool(q) and not row.checkpoint_passed and percent >= 50
    return {
        "watched_seconds": row.watched_seconds,
        "duration_seconds": duration,
        "position": row.position,
        "percent": percent,
        "completed": row.completed_at is not None,
        "needed_seconds": max(0, int(duration * COMPLETE_RATIO) - row.watched_seconds),
        "needs_checkpoint": needs,
        "checkpoint_passed": bool(row.checkpoint_passed),
    }
