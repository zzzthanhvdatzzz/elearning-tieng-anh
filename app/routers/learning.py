"""routers/learning.py — S5 lộ trình Unit và S6 trang học bài (F5, F6).

Ghi chú: `POST /lessons/{id}/progress` là endpoint JSON (không trả HTML) vì được gọi
bằng fetch/keepalive từ trình duyệt mỗi 30 giây và khi rời trang.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session as OrmSession

from app.db import get_db
from app.deps import role_required
from app.models import User
from app.services import learning as svc
from app.templating import templates

router = APIRouter(tags=["learning"])


@router.get("/units", response_class=HTMLResponse)
def units(request: Request, user: User = Depends(role_required("student")),
          db: OrmSession = Depends(get_db)):
    plan = svc.units_for_student(db, user)
    return templates.TemplateResponse(
        request, "learning_units.html",
        {"user": user, "title": "Lộ trình học", "plan": plan,
         "next": svc.next_lesson(db, user), "summary": svc.progress_summary(db, user)},
    )


@router.get("/lessons/{lesson_id}", response_class=HTMLResponse)
def lesson_page(request: Request, lesson_id: int,
                user: User = Depends(role_required("student")),
                db: OrmSession = Depends(get_db)):
    data = svc.lesson_detail(db, user, lesson_id)
    if data is None:
        # Không tiết lộ bài của lớp khác tồn tại hay không
        raise HTTPException(status_code=404, detail="Không tìm thấy bài học")
    return templates.TemplateResponse(
        request, "lesson.html", {"user": user, "title": data["lesson"].title, **data}
    )


async def progress_payload(request: Request) -> dict:
    """Nhận cả JSON (fetch keepalive từ trang học) lẫn form (fallback không có JS)."""
    ctype = request.headers.get("content-type", "")
    if ctype.startswith("application/json"):
        try:
            return dict(await request.json())
        except Exception:
            return {}
    return dict(await request.form())


def _as_bool(value) -> bool:
    return str(value).lower() in ("1", "true", "on", "yes")


def _as_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@router.post("/lessons/{lesson_id}/progress")
def save_progress(
    lesson_id: int,
    payload: dict = Depends(progress_payload),
    user: User = Depends(role_required("student")),
    db: OrmSession = Depends(get_db),
):
    # Kiểm tra quyền sở hữu bài học trước khi ghi (chống ghi tiến độ bài lớp khác)
    if svc.lesson_detail(db, user, lesson_id) is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài học")
    try:
        result = svc.add_progress(
            db, user, lesson_id,
            seconds=_as_int(payload.get("seconds"), 0) or 0,
            percent=_as_int(payload.get("percent")),
            completed=_as_bool(payload.get("completed")),
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài học")
    return JSONResponse({"ok": True, **result})
