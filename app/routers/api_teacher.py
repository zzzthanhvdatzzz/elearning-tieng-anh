"""routers/api_teacher.py — JSON cho giáo viên: chấm bài viết/nói, hàng đợi, lớp học.

Tách khỏi api.py để file không dài quá 500 dòng (NFR5).
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.db import get_db
from app.models import Assignment, Class, Submission, User
from app.routers.api import api_user
from app.services import classes as cls_svc
from app.services import grading as grading_svc
from app.services import writing as writing_svc

router = APIRouter(prefix="/api", tags=["api-teacher"])


def teacher_only(user: User = Depends(api_user)) -> User:
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Chỉ dành cho giáo viên")
    return user


def _owned(db: OrmSession, teacher: User, submission_id: int) -> Submission:
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài nộp")
    allowed = db.query(Assignment).join(Class, Class.id == Assignment.class_id).filter(
        Assignment.id == submission.assignment_id, Class.teacher_id == teacher.id
    ).first()
    if allowed is None:
        raise HTTPException(status_code=403, detail="Bài nộp không thuộc lớp bạn phụ trách")
    return submission


@router.get("/teacher/parent-requests")
def parent_requests(user: User = Depends(teacher_only), db: OrmSession = Depends(get_db)):
    from app.services import parent as parent_svc

    return {"items": [
        {"id": r["link"].id, "student": r["student"].full_name or r["student"].email,
         "klass": r["klass"].name,
         "parent": (r["parent"].full_name or r["parent"].email) if r["parent"] else ""}
        for r in parent_svc.pending_for_teacher(db, user)
    ]}


@router.post("/teacher/parent-requests/{link_id}")
def decide_parent(link_id: int, payload: dict = Body(...),
                  user: User = Depends(teacher_only), db: OrmSession = Depends(get_db)):
    from app.services import parent as parent_svc

    ok, error = parent_svc.decide(db, user, link_id, bool(payload.get("approve")))
    if not ok:
        raise HTTPException(status_code=422, detail=error)
    return {"ok": True}


@router.get("/teacher/classes/{class_id}")
def class_detail(class_id: int, user: User = Depends(teacher_only), db: OrmSession = Depends(get_db)):
    from app.services import assignments as asg_svc

    klass = cls_svc.owned_class(db, user, class_id)
    if klass is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp")
    assignments = db.execute(
        select(Assignment).where(Assignment.class_id == klass.id)
        .order_by(Assignment.created_at.desc())
    ).scalars().all()
    return {
        "klass": {"id": klass.id, "name": klass.name, "grade": klass.grade,
                  "join_code": klass.join_code},
        "roster": [{"id": r["student"].id, "name": r["student"].full_name or r["student"].email,
                    "email": r["student"].email, "cefr": r["student"].cefr_level}
                   for r in cls_svc.roster(db, klass)],
        "lessons": [{"id": l.id, "code": l.code, "title": l.title}
                    for l in asg_svc.lessons_for_class(db, klass)],
        "assignments": [{"id": a.id, "title": a.title, "kind": a.kind,
                         "deadline": a.deadline.isoformat() if a.deadline else None,
                         "max_attempts": a.max_attempts} for a in assignments],
    }


@router.post("/teacher/classes/{class_id}/students")
def add_student(class_id: int, payload: dict = Body(...),
                user: User = Depends(teacher_only), db: OrmSession = Depends(get_db)):
    klass = cls_svc.owned_class(db, user, class_id)
    if klass is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp")
    _, error = cls_svc.add_student_by_email(db, klass, str(payload.get("email", "")))
    if error:
        raise HTTPException(status_code=422, detail=error)
    return {"ok": True}


@router.delete("/teacher/classes/{class_id}/students/{student_id}")
def remove_student(class_id: int, student_id: int, user: User = Depends(teacher_only),
                   db: OrmSession = Depends(get_db)):
    klass = cls_svc.owned_class(db, user, class_id)
    if klass is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp")
    cls_svc.remove_student(db, klass, student_id)
    return {"ok": True}


@router.post("/teacher/classes/{class_id}/assignments")
def create_assignment(class_id: int, payload: dict = Body(...),
                      user: User = Depends(teacher_only), db: OrmSession = Depends(get_db)):
    from app.services import assignments as asg_svc
    from app.models import Lesson

    klass = cls_svc.owned_class(db, user, class_id)
    if klass is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp")
    lesson = db.get(Lesson, int(payload["lesson_id"])) if payload.get("lesson_id") else None
    deadline = asg_svc.parse_deadline(payload.get("deadline") or None)
    if payload.get("deadline") and deadline is None:
        raise HTTPException(status_code=422, detail="Hạn nộp không đúng định dạng")
    _, error = asg_svc.create_assignment(
        db, user, klass, lesson, str(payload.get("title", "")), deadline,
        int(payload.get("max_attempts", 1)), str(payload.get("kind", "practice")),
    )
    if error:
        raise HTTPException(status_code=422, detail=error)
    return {"ok": True}


@router.get("/teacher/classes/{class_id}/report")
def class_report(class_id: int, user: User = Depends(teacher_only),
                 db: OrmSession = Depends(get_db)):
    from app.services import report as report_svc

    klass = cls_svc.owned_class(db, user, class_id)
    if klass is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp")
    r = report_svc.class_report(db, klass)
    return {
        "klass": {"id": klass.id, "name": klass.name},
        "students": r["students"], "class_avg": r["class_avg"],
        "rows": [{"id": row["student"].id, "name": row["student"].full_name or row["student"].email,
                  "attempts": row["attempts"], "avg": row["avg"],
                  "minutes": row["minutes"], "needs_help": row["needs_help"]}
                 for row in r["rows"]],
    }


@router.get("/teacher/classes")
def teacher_classes(user: User = Depends(teacher_only), db: OrmSession = Depends(get_db)):
    return {"items": [
        {"id": r["klass"].id, "name": r["klass"].name, "grade": r["klass"].grade,
         "join_code": r["klass"].join_code, "students": r["students"]}
        for r in cls_svc.teacher_classes(db, user)
    ]}


@router.get("/teacher/submissions")
def teacher_queue(kind: str = "writing", user: User = Depends(teacher_only),
                  db: OrmSession = Depends(get_db)):
    rows = []
    if kind == "writing":
        queue = writing_svc.teacher_queue(db, user)
    else:
        queue = []
    for s in queue:
        assignment = db.get(Assignment, s.assignment_id)
        student = db.get(User, s.student_id)
        rows.append({
            "id": s.id, "student": student.full_name or student.email if student else "",
            "title": assignment.title if assignment else "",
            "kind": assignment.kind if assignment else "",
            "words": writing_svc.word_count(s.text_content or ""),
            "has_audio": bool(s.audio_path),
            "submitted_at": s.submitted_at.isoformat(),
        })
    return {"items": rows}


@router.get("/teacher/submissions/{submission_id}")
def submission_detail(submission_id: int, user: User = Depends(teacher_only),
                      db: OrmSession = Depends(get_db)):
    sub = _owned(db, user, submission_id)
    assignment = db.get(Assignment, sub.assignment_id)
    student = db.get(User, sub.student_id)
    return {
        "id": sub.id, "kind": assignment.kind if assignment else "",
        "title": assignment.title if assignment else "",
        "student": (student.full_name or student.email) if student else "",
        "text": sub.text_content or "", "has_audio": bool(sub.audio_path),
        "words": writing_svc.word_count(sub.text_content or ""),
        "status": sub.status, "auto_score": sub.auto_score,
        "criteria": grading_svc.RUBRIC_CRITERIA, "labels": grading_svc.RUBRIC_LABELS,
    }


@router.post("/teacher/submissions/{submission_id}/grade")
def grade(submission_id: int, payload: dict = Body(...),
          user: User = Depends(teacher_only), db: OrmSession = Depends(get_db)):
    sub = _owned(db, user, submission_id)
    rubric = {c: float(payload.get(c, 0)) for c in grading_svc.RUBRIC_CRITERIA}
    graded, error = grading_svc.grade_writing(db, sub, rubric, user, str(payload.get("comment", "")))
    if error:
        raise HTTPException(status_code=422, detail=error)
    return {"ok": True, "final_score": graded.final_score, "teacher_score": graded.teacher_score}


# ------------------------------------------------------------------ học sinh: bài viết


@router.get("/writing/{lesson_id}")
def writing_state(lesson_id: int, user: User = Depends(api_user), db: OrmSession = Depends(get_db)):
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Chỉ dành cho học sinh")
    state = writing_svc.writing_state(db, user, lesson_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")
    return {
        "lesson": {"id": state["lesson"].id, "title": state["lesson"].title},
        "prompt": state["prompt"], "min_words": state["min_words"],
        "attempts_left": state["attempts_left"], "max_attempts": state["assignment"].max_attempts,
        "last": ({"id": state["last"].id, "text": state["last"].text_content,
                  "status": state["last"].status, "score": state["last"].final_score}
                 if state["last"] else None),
    }


@router.post("/writing/{lesson_id}/submit")
def writing_submit(lesson_id: int, payload: dict = Body(...),
                   user: User = Depends(api_user), db: OrmSession = Depends(get_db)):
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Chỉ dành cho học sinh")
    sub, error = writing_svc.submit_writing(db, user, lesson_id, str(payload.get("text", "")))
    if error:
        raise HTTPException(status_code=422, detail=error)
    return {"ok": True, "submission_id": sub.id, "status": sub.status}


@router.get("/writing/{lesson_id}/result")
def writing_result(lesson_id: int, user: User = Depends(api_user), db: OrmSession = Depends(get_db)):
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Chỉ dành cho học sinh")
    state = writing_svc.writing_state(db, user, lesson_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")
    last = state["last"]
    if last is None:
        return {"submission": None}
    rubric = grading_svc.rubric_of(db, last.id) if last.status == "graded" else {}
    return {
        "submission": {"id": last.id, "text": last.text_content, "status": last.status,
                       "score": last.final_score, "attempt_no": last.attempt_no},
        "rubric": rubric, "feedback": grading_svc.feedback_of(db, last.id),
        "labels": grading_svc.RUBRIC_LABELS, "attempts_left": state["attempts_left"],
    }
