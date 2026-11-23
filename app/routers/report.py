"""routers/report.py — F13/F14: báo cáo học sinh, báo cáo lớp, xuất CSV."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session as OrmSession

from app.db import get_db
from app.deps import role_required
from app.models import Class, Enrollment, User
from app.services import classes as cls_svc
from app.services import report as svc
from app.templating import templates

router = APIRouter(prefix="/reports", tags=["report"])


def _can_view(db: OrmSession, viewer: User, student_id: int) -> bool:
    """Quyền S của ma trận 3.12: chính chủ, giáo viên lớp đó, hoặc quản trị (chỉ đọc)."""
    if viewer.id == student_id:
        return True
    if viewer.role == "admin":
        return True
    if viewer.role == "teacher":
        row = db.query(Enrollment).join(Class, Class.id == Enrollment.class_id).filter(
            Enrollment.student_id == student_id, Class.teacher_id == viewer.id,
            Enrollment.status == "active",
        ).first()
        return row is not None
    return False


@router.get("/student/{student_id}", response_class=HTMLResponse)
def student_report(student_id: int, request: Request, user: User = Depends(role_required(
        "student", "teacher", "admin")), db: OrmSession = Depends(get_db)):
    if not _can_view(db, user, student_id):
        raise HTTPException(status_code=403, detail="Bạn chỉ được xem dữ liệu của mình")
    student = db.get(User, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy học sinh")
    return templates.TemplateResponse(
        request, "report_student.html",
        {"user": user, "title": "Báo cáo học sinh",
         "is_self": user.id == student_id, "report": svc.student_report(db, student),
         "labels": svc.SKILL_LABELS},
    )


@router.get("/class/{class_id}", response_class=HTMLResponse)
def class_report(class_id: int, request: Request,
                 user: User = Depends(role_required("teacher")),
                 db: OrmSession = Depends(get_db)):
    klass = cls_svc.owned_class(db, user, class_id)
    if klass is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp")
    return templates.TemplateResponse(
        request, "report_class.html",
        {"user": user, "title": f"Báo cáo lớp {klass.name}",
         "report": svc.class_report(db, klass)},
    )


@router.get("/class/{class_id}/export.csv")
def class_csv(class_id: int, user: User = Depends(role_required("teacher")),
              db: OrmSession = Depends(get_db)):
    klass = cls_svc.owned_class(db, user, class_id)
    if klass is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp")
    body = svc.class_csv(db, klass)
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="bao-cao-lop-{klass.join_code}.csv"'},
    )
