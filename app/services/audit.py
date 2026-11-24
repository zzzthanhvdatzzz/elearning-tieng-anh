"""services/audit.py — ghi nhật ký hành động nhạy cảm (một chỗ duy nhất).

Quy ước: mỗi hàm gọi kèm `actor` (người làm) và `target` dạng "user:12", "submission:44",
"parent_link:7" để tra cứu được. `detail` là mô tả ngắn, KHÔNG chứa nội dung bài làm.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.models import AuditLog, User

ACTIONS = {
    "grade": "Chấm bài",
    "reopen": "Mở lại bài để chấm lại",
    "user_lock": "Khoá tài khoản",
    "user_unlock": "Mở khoá tài khoản",
    "parent_approve": "Duyệt liên kết phụ huynh",
    "parent_reject": "Từ chối liên kết phụ huynh",
    "import_users": "Nhập tài khoản từ Excel",
    "password_change": "Tự đổi mật khẩu",
    "reset_password": "Đặt lại mật khẩu",
}


def log(db: OrmSession, actor: User | None, action: str, target: str = "",
        detail: str = "") -> AuditLog:
    row = AuditLog(actor_id=actor.id if actor else None,
                   actor_email=(actor.email if actor else ""),
                   action=action, target=target[:120], detail=detail[:2000])
    db.add(row)
    return row


def recent(db: OrmSession, limit: int = 100, action: str = "") -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    return list(db.execute(stmt).scalars())
