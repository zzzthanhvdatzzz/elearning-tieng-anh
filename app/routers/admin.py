"""routers/admin.py — S15: quản trị tài khoản (F2) và import câu hỏi (F15)."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.db import get_db
from app.deps import role_required
from app.models import Lesson, User
from app.services import admin as svc
from app.templating import templates

router = APIRouter(prefix="/admin", tags=["admin"])
MAX_IMPORT_BYTES = 5 * 1024 * 1024


def _redirect_error(path: str, message: str, code: int = 303):
    from urllib.parse import quote

    return RedirectResponse(f"{path}?error={quote(message)}", status_code=code)


@router.get("/users", response_class=HTMLResponse)
def users_page(request: Request, role: str = "", q: str = "", error: str | None = None,
               user: User = Depends(role_required("admin")),
               db: OrmSession = Depends(get_db)):
    return templates.TemplateResponse(
        request, "admin_users.html",
        {"user": user, "title": "Tài khoản", "error": error,
         "rows": svc.list_users(db, role or None, q),
         "role_filter": role, "q": q, "roles": svc.ROLES},
    )


@router.post("/users")
def create_user(email: str = Form(...), full_name: str = Form(""), role: str = Form(...),
                password: str = Form(...), user: User = Depends(role_required("admin")),
                db: OrmSession = Depends(get_db)):
    _, error = svc.create_user(db, email, full_name, role, password)
    if error:
        return _redirect_error("/admin/users", error)
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/lock")
def lock_user(user_id: int, user: User = Depends(role_required("admin")),
              db: OrmSession = Depends(get_db)):
    if user_id == user.id:
        raise HTTPException(status_code=422, detail="Không tự khoá tài khoản của mình")
    svc.set_active(db, user_id, False)
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/unlock")
def unlock_user(user_id: int, user: User = Depends(role_required("admin")),
                db: OrmSession = Depends(get_db)):
    svc.set_active(db, user_id, True)
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: int, new_password: str = Form(...),
                   user: User = Depends(role_required("admin")),
                   db: OrmSession = Depends(get_db)):
    _, error = svc.reset_password(db, user_id, new_password)
    if error:
        return _redirect_error("/admin/users", error)
    return RedirectResponse("/admin/users", status_code=303)


@router.get("/import", response_class=HTMLResponse)
def import_page(request: Request, error: str | None = None,
                user: User = Depends(role_required("admin")),
                db: OrmSession = Depends(get_db)):
    lessons = list(db.execute(select(Lesson).order_by(Lesson.code)).scalars())
    return templates.TemplateResponse(
        request, "admin_import.html",
        {"user": user, "title": "Import câu hỏi", "error": error, "lessons": lessons,
         "columns": svc.IMPORT_COLUMNS},
    )


@router.post("/questions/import")
def import_questions(request: Request, lesson_id: int = Form(...),
                     file: UploadFile | None = File(None),
                     user: User = Depends(role_required("admin")),
                     db: OrmSession = Depends(get_db)):
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài học")

    if file is None:
        return _redirect_error("/admin/import", "Chưa chọn file Excel")

    data = file.file.read(MAX_IMPORT_BYTES + 1)   # endpoint sync: đọc đồng bộ, không await
    if not data:
        return _redirect_error("/admin/import", "File rỗng")
    if len(data) > MAX_IMPORT_BYTES:
        return _redirect_error("/admin/import", "File vượt quá 5 MB")
    if not (file.filename or "").lower().endswith((".xlsx", ".xlsm")):
        return _redirect_error("/admin/import", "Chỉ nhận file .xlsx")

    result = svc.import_questions(db, lesson, data)
    lessons = list(db.execute(select(Lesson).order_by(Lesson.code)).scalars())
    return templates.TemplateResponse(
        request, "admin_import.html",
        {"user": user, "title": "Import câu hỏi", "lessons": lessons,
         "columns": svc.IMPORT_COLUMNS, "result": result, "lesson": lesson},
    )
