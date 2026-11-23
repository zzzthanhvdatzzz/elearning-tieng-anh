"""routers/practice.py — S7 luyện tập 10 câu, chấm ngay, hiện giải thích (F9).

Giống placement: endpoint giữ `def` (sync) và đọc form động qua dependency async.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.datastructures import FormData
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session as OrmSession

from app.db import get_db
from app.deps import role_required
from app.models import User
from app.services import practice as svc
from app.templating import templates

router = APIRouter(tags=["practice"])


async def form_data(request: Request) -> FormData:
    return await request.form()


def _with_options(questions) -> list[dict]:
    return [{"q": q, "options": json.loads(q.options or "[]")} for q in questions]


@router.get("/practice/{lesson_id}", response_class=HTMLResponse)
def practice_exam(lesson_id: int, request: Request,
                  user: User = Depends(role_required("student")),
                  db: OrmSession = Depends(get_db)):
    state = svc.practice_state(db, user, lesson_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài luyện tập")

    # Đã hết lượt và đã có bài thì đưa thẳng về trang kết quả
    if state["attempts_left"] <= 0 and state["last"] is not None:
        return RedirectResponse(f"/practice/{lesson_id}/result", status_code=303)

    return templates.TemplateResponse(
        request, "practice_exam.html",
        {"user": user, "title": "Luyện tập", "lesson": state["lesson"],
         "items": _with_options(state["questions"]), "attempts_left": state["attempts_left"],
         "attempt_no": state["attempts_used"] + 1, "max_attempts": state["assignment"].max_attempts},
    )


@router.post("/practice/{lesson_id}/submit")
def practice_submit(lesson_id: int, request: Request, form: FormData = Depends(form_data),
                    user: User = Depends(role_required("student")),
                    db: OrmSession = Depends(get_db)):
    answers: dict[int, str] = {}
    for key, value in form.multi_items():
        if key.startswith("q_") and isinstance(value, str) and value:
            try:
                answers[int(key[2:])] = value.upper()[:1]
            except ValueError:
                continue

    submission, error = svc.submit_practice(db, user, lesson_id, answers)
    if error:
        state = svc.practice_state(db, user, lesson_id)
        if state is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy bài luyện tập")
        return templates.TemplateResponse(
            request, "practice_exam.html",
            {"user": user, "error": error, "lesson": state["lesson"],
             "items": _with_options(state["questions"]),
             "attempts_left": state["attempts_left"], "attempt_no": state["attempts_used"] + 1,
             "max_attempts": state["assignment"].max_attempts},
            status_code=409,
        )
    return RedirectResponse(f"/practice/{lesson_id}/result", status_code=303)


@router.get("/practice/{lesson_id}/result", response_class=HTMLResponse)
def practice_result(lesson_id: int, request: Request,
                    user: User = Depends(role_required("student")),
                    db: OrmSession = Depends(get_db)):
    state = svc.practice_state(db, user, lesson_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài luyện tập")

    last = state["last"]
    review = svc.submission_review(db, last) if last is not None else []
    return templates.TemplateResponse(
        request, "practice_result.html",
        {"user": user, "title": "Kết quả luyện tập", "lesson": state["lesson"],
         "submission": last, "review": review, "history": svc.history(db, user, lesson_id),
         "attempts_left": state["attempts_left"]},
    )
