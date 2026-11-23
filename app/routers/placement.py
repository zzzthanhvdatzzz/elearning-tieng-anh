"""routers/placement.py — S3 làm bài kiểm tra đầu vào + hàng đợi chấm của giáo viên.

Lưu ý kỹ thuật: endpoint giữ `def` (sync) để SQLAlchemy chạy trong threadpool của
FastAPI — chuyển sang `async def` sẽ gặp lỗi "SQLite objects created in a thread...".
Form động (danh sách câu trả lời) đọc qua dependency `form_data` (async) nên vẫn
không phải đổi endpoint thành async.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.datastructures import FormData
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session as OrmSession

from app.db import get_db
from app.deps import role_required
from app.models import Question, Submission, User
from app.services import placement as svc
from app.templating import templates

router = APIRouter(tags=["placement"])


async def form_data(request: Request) -> FormData:
    return await request.form()


def _grouped_questions(questions: list[Question]) -> list[tuple[str, list[dict]]]:
    labels = {"grammar": "Phần 1 — Ngữ pháp (10 câu)",
              "reading": "Phần 2 — Đọc hiểu (8 câu)",
              "listening": "Phần 3 — Nghe (7 câu)"}
    order = ["grammar", "reading", "listening"]
    groups: dict[str, list[dict]] = {}
    for q in questions:
        groups.setdefault(q.skill, []).append({"q": q, "options": json.loads(q.options or "[]")})
    return [(labels.get(k, k), groups[k]) for k in order if k in groups]


@router.get("/placement", response_class=HTMLResponse)
def placement_exam(request: Request, user: User = Depends(role_required("student")),
                   db: OrmSession = Depends(get_db)):
    klass = svc.active_class(db, user.id)
    if klass is None:
        return templates.TemplateResponse(
            request, "placement_result.html",
            {"user": user, "error": "Bạn chưa được ghi danh vào lớp nào. Hãy hỏi giáo viên mã lớp."},
            status_code=403,
        )

    assignment = svc.ensure_placement_assignment(db, klass)
    if assignment is None:
        return templates.TemplateResponse(
            request, "placement_result.html",
            {"user": user, "error": "Ngân hàng câu hỏi kiểm tra đầu vào chưa được nạp."},
            status_code=409,
        )

    existing = svc.student_submission(db, assignment.id, user.id)
    if existing is not None:
        return RedirectResponse("/placement/result", status_code=status.HTTP_303_SEE_OTHER)

    questions = svc.placement_questions(db)
    return templates.TemplateResponse(
        request, "placement_exam.html",
        {"user": user, "title": "Kiểm tra đầu vào", "groups": _grouped_questions(questions),
         "total": len(questions), "klass": klass},
    )


@router.post("/placement/submit")
def placement_submit(request: Request, form: FormData = Depends(form_data),
                     user: User = Depends(role_required("student")),
                     db: OrmSession = Depends(get_db)):
    answers: dict[int, str] = {}
    for key, value in form.multi_items():
        if key.startswith("q_") and isinstance(value, str) and value:
            try:
                answers[int(key[2:])] = value.upper()[:1]
            except ValueError:
                continue

    essay = str(form.get("essay", ""))
    submission, error = svc.submit_placement(db, user, answers, essay)
    if error:
        return templates.TemplateResponse(
            request, "placement_result.html", {"user": user, "error": error}, status_code=409
        )
    return RedirectResponse("/placement/result", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/placement/result", response_class=HTMLResponse)
def placement_result(request: Request, user: User = Depends(role_required("student")),
                     db: OrmSession = Depends(get_db)):
    klass = svc.active_class(db, user.id)
    submission = None
    questions: list[Question] = []
    parts: dict[str, float] = {}
    if klass is not None:
        assignment = svc.ensure_placement_assignment(db, klass)
        if assignment is not None:
            submission = svc.student_submission(db, assignment.id, user.id)
    if submission is not None:
        questions = svc.placement_questions(db)
        detail = [{"question_id": a.question_id, "is_correct": a.is_correct} for a in submission.answers]
        parts = svc.part_scores(detail, questions)

    return templates.TemplateResponse(
        request, "placement_result.html",
        {"user": user, "title": "Kết quả kiểm tra đầu vào", "submission": submission,
         "parts": parts, "total_questions": len(questions)},
    )


# ---------------------------------------------------------------- giáo viên


@router.get("/teacher/placement", response_class=HTMLResponse)
def teacher_queue(request: Request, user: User = Depends(role_required("teacher")),
                  db: OrmSession = Depends(get_db)):
    queue = svc.pending_queue(db, user)
    return templates.TemplateResponse(
        request, "teacher_queue.html",
        {"user": user, "title": "Chấm bài kiểm tra đầu vào", "queue": queue},
    )


@router.get("/teacher/placement/{submission_id}", response_class=HTMLResponse)
def teacher_open(request: Request, submission_id: int,
                 user: User = Depends(role_required("teacher")), db: OrmSession = Depends(get_db)):
    submission = _owned_submission(db, user, submission_id)
    questions = svc.placement_questions(db)
    answers = {a.question_id: a for a in submission.answers}
    return templates.TemplateResponse(
        request, "teacher_grade.html",
        {"user": user, "title": "Chấm bài", "submission": submission, "questions": questions,
         "answers": answers, "criteria": svc.RUBRIC_CRITERIA, "labels": svc.RUBRIC_LABELS},
    )


@router.post("/teacher/placement/{submission_id}/grade")
def teacher_grade(
    request: Request,
    submission_id: int,
    task: float = Form(...),
    grammar: float = Form(...),
    vocab: float = Form(...),
    coherence: float = Form(...),
    level_override: int = Form(0),
    comment: str = Form(""),
    user: User = Depends(role_required("teacher")),
    db: OrmSession = Depends(get_db),
):
    submission = _owned_submission(db, user, submission_id)
    rubric = {"task": task, "grammar": grammar, "vocab": vocab, "coherence": coherence}
    student, error = svc.grade_placement(db, submission, rubric, user, level_override, comment)
    if error:
        questions = svc.placement_questions(db)
        answers = {a.question_id: a for a in submission.answers}
        return templates.TemplateResponse(
            request, "teacher_grade.html",
            {"user": user, "error": error, "submission": submission, "questions": questions,
             "answers": answers, "criteria": svc.RUBRIC_CRITERIA, "labels": svc.RUBRIC_LABELS},
            status_code=422,
        )
    return RedirectResponse("/teacher/placement", status_code=status.HTTP_303_SEE_OTHER)


def _owned_submission(db: OrmSession, teacher: User, submission_id: int) -> Submission:
    """BR9 + chống IDOR: giáo viên chỉ mở được bài của lớp mình phụ trách."""
    from app.models import Assignment, Class

    submission = db.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài nộp")
    allowed = db.query(Assignment).join(Class, Class.id == Assignment.class_id).filter(
        Assignment.id == submission.assignment_id, Class.teacher_id == teacher.id
    ).first()
    if allowed is None:
        raise HTTPException(status_code=403, detail="Bài nộp này không thuộc lớp bạn phụ trách")
    return submission
