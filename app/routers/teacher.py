"""routers/teacher.py — S10/S11: lớp học, ghi danh và giao bài (F10, F11)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session as OrmSession

from app.db import get_db
from app.deps import role_required
from app.models import Lesson, User
from app.services import assignments as asg_svc
from app.services import classes as cls_svc
from app.templating import templates

router = APIRouter(prefix="/teacher", tags=["teacher"])


def _klass_or_404(db: OrmSession, teacher: User, class_id: int):
    klass = cls_svc.owned_class(db, teacher, class_id)
    if klass is None:
        # Không tiết lộ lớp người khác có tồn tại hay không (BR9)
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp")
    return klass


@router.get("/classes", response_class=HTMLResponse)
def classes_page(request: Request, user: User = Depends(role_required("teacher")),
                 db: OrmSession = Depends(get_db)):
    return templates.TemplateResponse(
        request, "teacher_classes.html",
        {"user": user, "title": "Lớp của tôi", "rows": cls_svc.teacher_classes(db, user)},
    )


@router.post("/classes")
def create_class(name: str = Form(...), grade: int = Form(...),
                 user: User = Depends(role_required("teacher")),
                 db: OrmSession = Depends(get_db)):
    if grade not in (8, 10):
        raise HTTPException(status_code=422, detail="Chỉ hỗ trợ khối 8 và khối 10 trong bản MVP")
    klass = cls_svc.create_class(db, user, name, grade)
    return RedirectResponse(f"/teacher/classes/{klass.id}", status_code=303)


@router.get("/classes/{class_id}", response_class=HTMLResponse)
def class_detail(class_id: int, request: Request, error: str | None = None,
                 user: User = Depends(role_required("teacher")),
                 db: OrmSession = Depends(get_db)):
    klass = _klass_or_404(db, user, class_id)
    return templates.TemplateResponse(
        request, "teacher_class_detail.html",
        {"user": user, "title": klass.name, "error": error, "klass": klass,
         "roster": cls_svc.roster(db, klass),
         "lessons": asg_svc.lessons_for_class(db, klass)},
    )


@router.post("/classes/{class_id}/students")
def add_student(class_id: int, email: str = Form(...),
                user: User = Depends(role_required("teacher")),
                db: OrmSession = Depends(get_db)):
    klass = _klass_or_404(db, user, class_id)
    _, error = cls_svc.add_student_by_email(db, klass, email)
    if error:
        from urllib.parse import quote

        return RedirectResponse(f"/teacher/classes/{class_id}?error={quote(error)}", status_code=303)
    return RedirectResponse(f"/teacher/classes/{class_id}", status_code=303)


@router.post("/classes/{class_id}/students/{student_id}/remove")
def remove_student(class_id: int, student_id: int,
                   user: User = Depends(role_required("teacher")),
                   db: OrmSession = Depends(get_db)):
    klass = _klass_or_404(db, user, class_id)
    cls_svc.remove_student(db, klass, student_id)
    return RedirectResponse(f"/teacher/classes/{class_id}", status_code=303)


@router.post("/classes/{class_id}/assignments")
def create_assignment(
    class_id: int,
    title: str = Form(...),
    lesson_id: int = Form(0),
    deadline: str = Form(""),
    max_attempts: int = Form(1),
    kind: str = Form("practice"),
    user: User = Depends(role_required("teacher")),
    db: OrmSession = Depends(get_db),
):
    klass = _klass_or_404(db, user, class_id)
    lesson = db.get(Lesson, lesson_id) if lesson_id else None
    parsed = asg_svc.parse_deadline(deadline)
    if deadline and parsed is None:
        raise HTTPException(status_code=422, detail="Hạn nộp không đúng định dạng ngày giờ")

    _, error = asg_svc.create_assignment(db, user, klass, lesson, title, parsed, max_attempts, kind)
    if error:
        from urllib.parse import quote

        return RedirectResponse(f"/teacher/classes/{class_id}?error={quote(error)}", status_code=303)
    return RedirectResponse(f"/teacher/classes/{class_id}", status_code=303)
