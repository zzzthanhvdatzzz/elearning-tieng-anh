"""routers/api_misc.py — JSON cho bài nói, phụ huynh và quản trị.

Tách file để api.py không vượt 500 dòng (NFR5).
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.db import get_db
from app.models import Lesson, Submission, User
from app.routers.api import api_user
from app.services import admin as admin_svc
from app.services import parent as parent_svc
from app.services import report as report_svc
from app.services import speaking as speaking_svc
from app.services.storage import MAX_AUDIO_BYTES

router = APIRouter(prefix="/api", tags=["api-misc"])


def role_only(*roles: str):
    def _dep(user: User = Depends(api_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập chức năng này")
        return user

    return _dep


# ------------------------------------------------------------------ bài nói


@router.get("/speaking/{lesson_id}")
def speaking_state(lesson_id: int, user: User = Depends(role_only("student")),
                   db: OrmSession = Depends(get_db)):
    state = speaking_svc.speaking_state(db, user, lesson_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài nói")
    last = state["last"]
    return {
        "lesson": {"id": state["lesson"].id, "title": state["lesson"].title},
        "prompt": state["prompt"], "attempts_left": state["attempts_left"],
        "max_attempts": state["assignment"].max_attempts,
        "last": ({"id": last.id, "status": last.status, "score": last.final_score}
                 if last else None),
    }


@router.post("/speaking/{lesson_id}/upload")
def speaking_upload(lesson_id: int, file: UploadFile | None = File(None),
                    user: User = Depends(role_only("student")),
                    db: OrmSession = Depends(get_db)):
    if file is None:
        raise HTTPException(status_code=422, detail="Chưa chọn file ghi âm")
    data = file.file.read(MAX_AUDIO_BYTES + 1)
    sub, error = speaking_svc.submit_speaking(db, user, lesson_id,
                                             file.filename or "bai-noi.webm", data)
    if error:
        raise HTTPException(status_code=422, detail=error)
    return {"ok": True, "submission_id": sub.id}


# ------------------------------------------------------------------ phụ huynh


@router.get("/parent/children")
def parent_children(user: User = Depends(role_only("parent")), db: OrmSession = Depends(get_db)):
    links = db.execute(select(parent_svc.ParentLink).where(
        parent_svc.ParentLink.parent_id == user.id)).scalars().all()
    out = []
    for link in links:
        student = db.get(User, link.student_id)
        out.append({"student_id": link.student_id,
                    "name": (student.full_name or student.email) if student else "",
                    "status": link.status})
    return {"items": out}


@router.post("/parent/link")
def parent_link(payload: dict = Body(...), user: User = Depends(role_only("parent")),
                db: OrmSession = Depends(get_db)):
    _, error = parent_svc.request_link(db, user, str(payload.get("student_email", "")))
    if error:
        raise HTTPException(status_code=409, detail=error)
    return {"ok": True, "status": "pending"}


@router.delete("/parent/link/{student_id}")
def parent_unlink(student_id: int, user: User = Depends(role_only("parent")),
                  db: OrmSession = Depends(get_db)):
    parent_svc.unlink(db, user, student_id)
    return {"ok": True}


@router.get("/parent/report/{student_id}")
def parent_report(student_id: int, user: User = Depends(role_only("parent")),
                  db: OrmSession = Depends(get_db)):
    if not parent_svc.can_view(db, user, student_id):
        raise HTTPException(status_code=403, detail="Chưa được duyệt xem báo cáo của học sinh này")
    student = db.get(User, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy học sinh")
    r = report_svc.student_report(db, student)
    return {
        "student": {"id": student.id, "name": student.full_name or student.email,
                    "cefr": student.cefr_level},
        "minutes": r["minutes"], "skills": r["skills"],
        "weakest": r["weakest"], "submitted": len(r["submissions"]),
        "weekly": r["weekly"],
    }


# ------------------------------------------------------------------ quản trị


@router.get("/admin/users")
def admin_users(role: str = "", q: str = "", user: User = Depends(role_only("admin")),
                db: OrmSession = Depends(get_db)):
    return {"items": [
        {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role,
         "active": u.is_active}
        for u in admin_svc.list_users(db, role or None, q)
    ], "roles": list(admin_svc.ROLES)}


@router.post("/admin/users")
def admin_create_user(payload: dict = Body(...), user: User = Depends(role_only("admin")),
                      db: OrmSession = Depends(get_db)):
    _, error = admin_svc.create_user(db, str(payload.get("email", "")),
                                     str(payload.get("full_name", "")),
                                     str(payload.get("role", "teacher")),
                                     str(payload.get("password", "")))
    if error:
        raise HTTPException(status_code=422, detail=error)
    return {"ok": True}


@router.post("/admin/users/{user_id}/toggle")
def admin_toggle(user_id: int, user: User = Depends(role_only("admin")),
                 db: OrmSession = Depends(get_db)):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")
    if target.id == user.id:
        raise HTTPException(status_code=422, detail="Không tự khoá tài khoản của mình")
    admin_svc.set_active(db, user_id, not target.is_active)
    return {"ok": True, "active": not target.is_active}


@router.get("/admin/lessons")
def admin_lessons(user: User = Depends(role_only("admin")), db: OrmSession = Depends(get_db)):
    rows = db.execute(select(Lesson).order_by(Lesson.code)).scalars().all()
    return {"items": [{"id": l.id, "code": l.code, "title": l.title} for l in rows]}


@router.post("/admin/import")
def admin_import(lesson_id: int = Body(...), user: User = Depends(role_only("admin")),
                 db: OrmSession = Depends(get_db)):
    raise HTTPException(status_code=415, detail="Dùng /import-upload (multipart) cho thao tác này")


@router.post("/admin/import-upload")
def admin_import_upload(lesson_id: int = 0, file: UploadFile | None = File(None),
                        user: User = Depends(role_only("admin")),
                        db: OrmSession = Depends(get_db)):
    lesson = db.get(Lesson, lesson_id) if lesson_id else None
    if lesson is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài học")
    if file is None:
        raise HTTPException(status_code=422, detail="Chưa chọn file Excel")
    data = file.file.read(5 * 1024 * 1024 + 1)
    if not (file.filename or "").lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=422, detail="Chỉ nhận file .xlsx")
    result = admin_svc.import_questions(db, lesson, data)
    return {"added": result["added"], "errors": result["errors"]}
