"""services/storage.py — lưu audio bài nói trên đĩа, có chặn dung lượng (NFR7).

BR10: audio lưu tối đa một học kỳ, sau đó job dọn sẽ xoá (xem `purge_old_audio`).
"""
from __future__ import annotations

import secrets
from pathlib import Path

from app.db import BASE_DIR

UPLOAD_DIR = Path(BASE_DIR) / "data" / "uploads" / "speaking"
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXT = {".webm", ".ogg", ".mp3", ".m4a", ".wav"}


def save_audio(student_id: int, lesson_id: int, filename: str, data: bytes) -> tuple[str | None, str | None]:
    """Trả (đường_dẫn_tương_đối, lỗi). Đường dẫn lưu vào submissions.audio_path."""
    ext = Path(filename or "").suffix.lower() or ".webm"
    if ext not in ALLOWED_EXT:
        return None, f"Định dạng {ext} không hỗ trợ. Chấp nhận: {', '.join(sorted(ALLOWED_EXT))}"
    if not data:
        return None, "File rỗng."
    if len(data) > MAX_AUDIO_BYTES:
        return None, f"File vượt quá {MAX_AUDIO_BYTES // (1024 * 1024)} MB."

    folder = UPLOAD_DIR / str(student_id)
    folder.mkdir(parents=True, exist_ok=True)
    name = f"lesson{lesson_id}-{secrets.token_hex(8)}{ext}"
    (folder / name).write_bytes(data)
    return f"speaking/{student_id}/{name}", None


def audio_response_path(relative: str) -> Path:
    return Path(BASE_DIR) / "data" / "uploads" / relative


def purge_old_audio(db, days: int = 150) -> dict:
    """BR10: xoá audio cũ hơn một học kỳ. Gọi từ job tuần."""
    from datetime import datetime, timedelta

    from sqlalchemy import select

    from app.models import Submission

    cutoff = datetime.utcnow() - timedelta(days=days)
    removed = 0
    rows = db.execute(
        select(Submission).where(Submission.audio_path.is_not(None),
                                 Submission.submitted_at < cutoff)
    ).scalars()
    for sub in rows:
        path = audio_response_path(sub.audio_path)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        sub.audio_path = None
        removed += 1
    db.commit()
    return {"removed": removed}
