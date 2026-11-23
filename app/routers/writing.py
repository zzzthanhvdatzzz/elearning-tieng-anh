"""routers/writing.py — S8 luyện viết (F8) và màn hình chấm rubric của giáo viên (F12)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session as OrmSession

from app.db import get_db
from app.deps import role_required
from app.models import Assignment, Class, Submission, User
from app.services import grading as grading_svc
from app.services import writing as svc
from app.templating import templates

router = APIRouter(tags=["writing"])


# ---------------------------------------------------------------- học sinh


@router.get("/writing/{lesson_id}", response_class=HTMLResponse)
def writing_form(lesson_id: int, request: Request,
                 user: User = Depends(role_required("student")),
                 db: OrmSession = Depends(get_db)):
    state = svc.writing_state(db, user, lesson_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")
    if state["attempts_left"] <= 0 and state["last"] is not None:
        return RedirectResponse(f"/writing/{lesson_id}/result", status_code=303)
    return templates.TemplateResponse(
        request, "writing_form.html",
        {"user": user, "title": "Luyện viết", **state},
    )


@router.post("/writing/{lesson_id}/submit")
def writing_submit(lesson_id: int, request: Request, text: str = Form(""),
                   user: User = Depends(role_required("student")),
                   db: OrmSession = Depends(get_db)):
    submission, error = svc.submit_writing(db, user, lesson_id, text)
    if error:
        state = svc.writing_state(db, user, lesson_id)
        if state is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")
        return templates.TemplateResponse(
            request, "writing_form.html",
            {"user": user, "error": error, **state}, status_code=422,
        )
    return RedirectResponse(f"/writing/{lesson_id}/result", status_code=303)


@router.get("/writing/{lesson_id}/result", response_class=HTMLResponse)
def writing_result(lesson_id: int, request: Request,
                   user: User = Depends(role_required("student")),
                   db: OrmSession = Depends(get_db)):
    state = svc.writing_state(db, user, lesson_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")
    last = state["last"]
    rubric = grading_svc.rubric_of(db, last.id) if last and last.status == "graded" else {}
    return templates.TemplateResponse(
        request, "writing_result.html",
        {"user": user, "title": "Bài viết của tôi", "submission": last, "rubric": rubric,
         "labels": grading_svc.RUBRIC_LABELS, "criteria": grading_svc.RUBRIC_CRITERIA,
         "feedback": grading_svc.feedback_of(db, last.id) if last else "",
         "attempts_left": state["attempts_left"], **state},
    )


# ---------------------------------------------------------------- giáo viên


@router.get("/teacher/writing", response_class=HTMLResponse)
def teacher_queue(request: Request, user: User = Depends(role_required("teacher")),
                  db: OrmSession = Depends(get_db)):
    rows = []
    for s in svc.teacher_queue(db, user):
        assignment = db.get(Assignment, s.assignment_id)
        student = svc.student_of(db, s)
        rows.append({"submission": s, "assignment": assignment, "student": student})
    return templates.TemplateResponse(
        request, "teacher_writing_queue.html",
        {"user": user, "title": "Chấm bài viết", "rows": rows},
    )


@router.get("/teacher/writing/{submission_id}", response_class=HTMLResponse)
def teacher_open(submission_id: int, request: Request,
                 user: User = Depends(role_required("teacher")),
                 db: OrmSession = Depends(get_db)):
    submission = _owned(db, user, submission_id)
    return templates.TemplateResponse(
        request, "teacher_writing_grade.html",
        {"user": user, "title": "Chấm bài viết", "submission": submission,
         "student": svc.student_of(db, submission),
         "words": svc.word_count(submission.text_content or ""),
         "criteria": grading_svc.RUBRIC_CRITERIA, "labels": grading_svc.RUBRIC_LABELS},
    )


@router.post("/teacher/writing/{submission_id}/grade")
def teacher_grade(submission_id: int, request: Request,
                  task: float = Form(...), grammar: float = Form(...),
                  vocab: float = Form(...), coherence: float = Form(...),
                  comment: str = Form(""),
                  user: User = Depends(role_required("teacher")),
                  db: OrmSession = Depends(get_db)):
    submission = _owned(db, user, submission_id)
    rubric = {"task": task, "grammar": grammar, "vocab": vocab, "coherence": coherence}
    graded, error = grading_svc.grade_writing(db, submission, rubric, user, comment)
    if error:
        return templates.TemplateResponse(
            request, "teacher_writing_grade.html",
            {"user": user, "error": error, "submission": graded,
             "student": svc.student_of(db, graded),
             "words": svc.word_count(graded.text_content or ""),
             "criteria": grading_svc.RUBRIC_CRITERIA, "labels": grading_svc.RUBRIC_LABELS},
            status_code=422,
        )
    return RedirectResponse("/teacher/writing", status_code=303)


def _owned(db: OrmSession, teacher: User, submission_id: int) -> Submission:
    """BR9 + chống IDOR: chỉ bài của lớp mình phụ trách."""
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài nộp")
    row = db.query(Assignment).join(Class, Class.id == Assignment.class_id).filter(
        Assignment.id == submission.assignment_id, Class.teacher_id == teacher.id
    ).first()
    if row is None:
        raise HTTPException(status_code=403, detail="Bài nộp này không thuộc lớp bạn phụ trách")
    return submission
