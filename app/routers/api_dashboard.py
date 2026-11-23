"""routers/api_dashboard.py — một endpoint tổng quan cho trang chủ theo vai trò.

Mục đích: người dùng mở lên là thấy việc cần làm, không phải nhớ đường dẫn.
Mỗi vai trò trả về một cấu trúc khác nhau; frontend chỉ hiển thị.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from app.db import get_db
from app.models import Assignment, Class, Enrollment, ParentLink, Submission, User
from app.routers.api import api_user
from app.services import assignments as asg_svc
from app.services import learning as learning_svc
from app.services import placement as placement_svc
from app.services import report as report_svc

router = APIRouter(prefix="/api", tags=["api-dashboard"])


@router.get("/dashboard")
def dashboard(user: User = Depends(api_user), db: OrmSession = Depends(get_db)):
    klass = placement_svc.active_class(db, user.id) if user.role == "student" else None
    out: dict = {"role": user.role, "name": user.full_name or user.email,
                 "cefr": user.cefr_level}

    if user.role == "student":
        plan = learning_svc.units_for_student(db, user)
        nxt = learning_svc.next_lesson(db, user)
        todo = asg_svc.student_todo(db, user)
        pending_todo = [t for t in todo if t["attempts_left"] > 0 and t["best"] is None]
        subs = db.execute(
            select(Submission, Assignment)
            .join(Assignment, Assignment.id == Submission.assignment_id)
            .where(Submission.student_id == user.id,
                   Submission.status.in_(("graded", "awaiting_teacher")))
            .order_by(Submission.submitted_at.desc()).limit(5)
        ).all()
        out.update({
            "klass": {"name": klass.name, "grade": klass.grade} if klass else None,
            "next": ({"id": nxt["lesson"].id, "title": nxt["lesson"].title,
                      "unit": nxt["unit"].title} if nxt else None),
            "summary": learning_svc.progress_summary(db, user),
            "todo_count": len(pending_todo),
            "todo": [{"id": t["assignment"].id, "title": t["assignment"].title,
                      "kind": t["assignment"].kind, "lesson_id": t["assignment"].lesson_id,
                      "deadline": t["assignment"].deadline.isoformat() if t["assignment"].deadline else None,
                      "attempts_left": t["attempts_left"]} for t in pending_todo[:5]],
            "recent": [{"id": s.id, "title": a.title, "kind": a.kind,
                        "score": s.final_score, "status": s.status,
                        "at": s.submitted_at.strftime("%d/%m %H:%M")} for s, a in subs],
            "units": [{"id": u["unit"].id, "title": u["unit"].title, "percent": u["percent"],
                       "lessons": len(u["lessons"])} for u in plan],
        })

    elif user.role == "teacher":
        classes = db.execute(select(Class).where(Class.teacher_id == user.id)).scalars().all()
        class_ids = [c.id for c in classes]
        students = db.execute(
            select(func.count()).select_from(Enrollment)
            .where(Enrollment.class_id.in_(class_ids), Enrollment.status == "active")
        ).scalar_one() if class_ids else 0
        pending = db.execute(
            select(func.count()).select_from(Submission)
            .join(Assignment, Assignment.id == Submission.assignment_id)
            .where(Assignment.class_id.in_(class_ids) if class_ids else False,
                   Submission.status == "awaiting_teacher")
        ).scalar_one() if class_ids else 0
        parent_reqs = db.execute(
            select(func.count()).select_from(ParentLink)
            .join(Enrollment, Enrollment.student_id == ParentLink.student_id)
            .where(Enrollment.class_id.in_(class_ids) if class_ids else False,
                   ParentLink.status == "pending")
        ).scalar_one() if class_ids else 0
        out.update({
            "classes": [{"id": c.id, "name": c.name, "grade": c.grade,
                         "join_code": c.join_code} for c in classes],
            "students": students, "pending_grading": pending, "parent_requests": parent_reqs,
        })

    elif user.role == "parent":
        links = db.execute(select(ParentLink).where(ParentLink.parent_id == user.id)).scalars().all()
        children = []
        for link in links:
            s = db.get(User, link.student_id)
            if s is None:
                continue
            rep = report_svc.student_report(db, s) if link.status == "approved" else None
            children.append({
                "id": s.id, "name": s.full_name or s.email, "status": link.status,
                "minutes": rep["minutes"] if rep else None,
                "weakest": rep["weakest"]["label"] if rep and rep["weakest"] else None,
            })
        out.update({"children": children})

    else:  # admin
        out.update({
            "users": db.execute(select(func.count()).select_from(User)).scalar_one(),
            "students": db.execute(select(func.count()).select_from(User)
                                   .where(User.role == "student")).scalar_one(),
            "teachers": db.execute(select(func.count()).select_from(User)
                                   .where(User.role == "teacher")).scalar_one(),
            "classes": db.execute(select(func.count()).select_from(Class)).scalar_one(),
            "submissions": db.execute(select(func.count()).select_from(Submission)).scalar_one(),
        })

    out["server_time"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    return out
