"""services/notify.py — thông báo trong ứng dụng (bảng `notifications`).

Một chỗ duy nhất để tạo thông báo, để không nơi nào tự `db.add(Notification(...))` rồi quên
`commit`, và để dễ thêm kênh khác (email/push) sau này.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from app.models import Notification


def push(db: OrmSession, user_id: int, title: str, body: str = "") -> Notification:
    n = Notification(user_id=user_id, title=title[:160], body=body[:2000])
    db.add(n)
    return n


def push_many(db: OrmSession, user_ids: list[int], title: str, body: str = "") -> int:
    for uid in set(user_ids):
        push(db, uid, title, body)
    return len(set(user_ids))


def recent(db: OrmSession, user_id: int, limit: int = 30) -> list[Notification]:
    return list(
        db.execute(
            select(Notification).where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .limit(limit)
        ).scalars()
    )


def unread_count(db: OrmSession, user_id: int) -> int:
    return db.execute(
        select(func.count()).select_from(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
    ).scalar_one()


def mark_read(db: OrmSession, user_id: int, notification_id: int | None = None) -> int:
    rows = db.execute(select(Notification).where(Notification.user_id == user_id)).scalars().all()
    changed = 0
    for n in rows:
        if notification_id is not None and n.id != notification_id:
            continue
        if not n.is_read:
            n.is_read = True
            changed += 1
    db.commit()
    return changed
