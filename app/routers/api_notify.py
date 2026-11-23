"""routers/api_notify.py — API thông báo trong ứng dụng cho mọi vai trò."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as OrmSession

from app.db import get_db
from app.models import User
from app.routers.api import api_user
from app.services import notify

router = APIRouter(prefix="/api", tags=["notifications"])


def _row(n) -> dict:
    return {
        "id": n.id,
        "title": n.title,
        "body": n.body or "",
        "is_read": bool(n.is_read),
        "at": n.created_at.strftime("%d/%m/%Y %H:%M"),
    }


@router.get("/notifications")
def list_notifications(user: User = Depends(api_user), db: OrmSession = Depends(get_db)):
    return {
        "unread": notify.unread_count(db, user.id),
        "items": [_row(n) for n in notify.recent(db, user.id)],
    }


@router.post("/notifications/read")
def read_notifications(user: User = Depends(api_user), db: OrmSession = Depends(get_db)):
    return {"changed": notify.mark_read(db, user.id)}
