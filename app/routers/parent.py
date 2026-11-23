"""routers/parent.py — S14: phụ huynh liên kết với con và xem báo cáo tuần (F3, F14)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session as OrmSession

from app.db import get_db
from app.deps import role_required
from app.models import User
from app.services import parent as svc
from app.services import report as report_svc
from app.templating import templates

router = APIRouter(prefix="/parent", tags=["parent"])


@router.get("", response_class=HTMLResponse)
def parent_home(request: Request, user: User = Depends(role_required("parent")),
                db: OrmSession = Depends(get_db)):
    return templates.TemplateResponse(
        request, "parent_home.html",
        {"user": user, "title": "Báo cáo của con", "children": svc.children(db, user)},
    )


@router.post("/link")
def link(student_email: str = Form(...), user: User = Depends(role_required("parent")),
         db: OrmSession = Depends(get_db)):
    _, error = svc.request_link(db, user, student_email)
    if error:
        from urllib.parse import quote

        return RedirectResponse(f"/parent?error={quote(error)}", status_code=303)
    return RedirectResponse("/parent", status_code=303)


@router.get("/report/{student_id}", response_class=HTMLResponse)
def parent_report(student_id: int, request: Request, user: User = Depends(role_required("parent")),
                  db: OrmSession = Depends(get_db)):
    if not svc.can_view(db, user, student_id):
        # BR3: chưa duyệt thì không thấy gì, kể cả sự tồn tại của học sinh
        raise HTTPException(status_code=403, detail="Bạn chưa được duyệt xem báo cáo của học sinh này")
    student = db.get(User, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy học sinh")
    report = report_svc.student_report(db, student)
    return templates.TemplateResponse(
        request, "parent_report.html",
        {"user": user, "title": f"Báo cáo của {student.full_name or student.email}",
         "report": report, "parent_view": True},
    )


@router.post("/unlink/{student_id}")
def unlink(student_id: int, user: User = Depends(role_required("parent")),
           db: OrmSession = Depends(get_db)):
    svc.unlink(db, user, student_id)
    return RedirectResponse("/parent", status_code=303)
