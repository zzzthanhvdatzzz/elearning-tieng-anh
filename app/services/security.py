"""services/security.py — băm mật khẩu, phiên đăng nhập, phân quyền.

Service thuần: không đọc Request, không trả JSONResponse. Nhờ vậy test được bằng
dict/đối tượng, không cần dựng server (mục 3.1).
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.models import Session as LoginSession
from app.models import User

COOKIE_NAME = "sid"
SESSION_HOURS = 8  # F1: phiên hết hạn sau 8 giờ
BCRYPT_COST = 12  # NFR3: cost >= 12

ROLE_LABELS = {
    "student": "Học sinh",
    "teacher": "Giáo viên",
    "parent": "Phụ huynh",
    "admin": "Quản trị",
}


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_COST)).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_session(db: OrmSession, user: User) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=SESSION_HOURS)
    db.add(LoginSession(token=token, user_id=user.id, expires_at=expires))
    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return token


def get_session_user(db: OrmSession, token: str | None) -> User | None:
    """Trả None nếu không có token / token sai / đã hết hạn / tài khoản bị khoá."""
    if not token:
        return None
    row = db.execute(select(LoginSession).where(LoginSession.token == token)).scalar_one_or_none()
    if row is None:
        return None
    if row.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        db.delete(row)
        db.commit()
        return None
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        return None
    return user


def revoke_session(db: OrmSession, token: str | None) -> None:
    if not token:
        return
    row = db.execute(select(LoginSession).where(LoginSession.token == token)).scalar_one_or_none()
    if row is not None:
        db.delete(row)
        db.commit()


def revoke_all_sessions(db: OrmSession, user_id: int) -> int:
    """Dùng khi quản trị khoá tài khoản — phiên đang mở phải chết ngay (US2/AC2)."""
    rows = db.execute(select(LoginSession).where(LoginSession.user_id == user_id)).scalars().all()
    for row in rows:
        db.delete(row)
    db.commit()
    return len(rows)


MIN_PASSWORD_LEN = 8


def change_password(db: OrmSession, user: User, old_password: str, new_password: str,
                    keep_token: str | None = None) -> tuple[bool, str | None]:
    """Người dùng tự đổi mật khẩu.

    Trả (False, mã_lỗi) khi: mật khẩu cũ sai, mật khẩu mới quá ngắn, hoặc trùng mật khẩu cũ.
    Đổi xong thì các phiên KHÁC bị huỷ (giữ phiên đang thao tác) — nếu tài khoản bị lộ,
    kẻ khác đang đăng nhập sẽ bị đẩy ra ngay.
    """
    if not verify_password(old_password, user.password_hash):
        return False, "wrong_old"
    if len(new_password or "") < MIN_PASSWORD_LEN:
        return False, "too_short"
    if new_password == old_password:
        return False, "same"
    user.password_hash = hash_password(new_password)
    db.commit()

    rows = db.execute(select(LoginSession).where(LoginSession.user_id == user.id)).scalars().all()
    for row in rows:
        if keep_token and row.token == keep_token:
            continue
        db.delete(row)
    db.commit()
    return True, None
