"""routers/api.py — lớp JSON cho frontend Next.js.

Giữ nguyên toàn bộ service ở dưới: router này chỉ là adapter HTTP, không chứa nghiệp vụ.
Khác router HTML ở một điểm: chưa đăng nhập trả 401 JSON thay vì chuyển hướng 303.
"""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.db import get_db
from app.models import Assignment, Class, Enrollment, User
from app.services import assignments as asg_svc
from app.services import learning as learning_svc
from app.services import placement as placement_svc
from app.services import practice as practice_svc
from app.services.security import (
    COOKIE_NAME,
    SESSION_HOURS,
    create_session,
    get_session_user,
    hash_password,
    revoke_session,
    verify_password,
)

router = APIRouter(prefix="/api", tags=["api"])

ROLE_HOME = {"student": "/units", "teacher": "/teacher/classes", "parent": "/parent",
             "admin": "/admin/users"}


def api_user(request: Request, db: OrmSession = Depends(get_db)) -> User:
    user = get_session_user(db, request.cookies.get(COOKIE_NAME))
    if user is None:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")
    return user


def _user_json(user: User) -> dict:
    return {"id": user.id, "email": user.email, "full_name": user.full_name,
            "role": user.role, "cefr": user.cefr_level, "home": ROLE_HOME.get(user.role, "/")}


def _set_session_cookie(response: JSONResponse, token: str) -> None:
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax",
                        max_age=SESSION_HOURS * 3600, path="/")


def _session_response(user: User, token: str) -> JSONResponse:
    resp = JSONResponse(_user_json(user))
    _set_session_cookie(resp, token)
    return resp


@router.post("/auth/login")
def api_login(payload: dict = Body(...), db: OrmSession = Depends(get_db)):
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
    if not user.is_active:
        raise HTTPException(status_code=423, detail="Tài khoản đã bị khoá")
    return _session_response(user, create_session(db, user))


@router.post("/auth/register")
def api_register(payload: dict = Body(...), db: OrmSession = Depends(get_db)):
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    join_code = str(payload.get("join_code", "")).strip().upper()
    full_name = str(payload.get("full_name", "")).strip()

    if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email này đã được đăng ký")
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="Mật khẩu phải có ít nhất 8 ký tự")

    klass = db.execute(select(Class).where(Class.join_code == join_code)).scalar_one_or_none()
    if klass is None:
        raise HTTPException(status_code=422, detail="Mã lớp không đúng, hãy hỏi giáo viên")

    user = User(email=email, password_hash=hash_password(password), full_name=full_name, role="student")
    db.add(user)
    db.flush()
    db.add(Enrollment(class_id=klass.id, student_id=user.id))
    db.commit()
    return _session_response(user, create_session(db, user))


@router.post("/auth/logout")
def api_logout(request: Request, db: OrmSession = Depends(get_db)):
    revoke_session(db, request.cookies.get(COOKIE_NAME))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE_NAME, path="/")
    return resp


@router.get("/me")
def api_me(user: User = Depends(api_user)):
    return _user_json(user)


# ------------------------------------------------------------------ học sinh


@router.get("/units")
def api_units(user: User = Depends(api_user), db: OrmSession = Depends(get_db)):
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Chỉ dành cho học sinh")
    plan = learning_svc.units_for_student(db, user)
    nxt = learning_svc.next_lesson(db, user)
    return {
        "next": ({"id": nxt["lesson"].id, "title": nxt["lesson"].title} if nxt else None),
        "summary": learning_svc.progress_summary(db, user),
        "units": [
            {"id": u["unit"].id, "code": u["unit"].code, "title": u["unit"].title,
             "percent": u["percent"],
             "lessons": [{"id": i["lesson"].id, "code": i["lesson"].code,
                          "title": i["lesson"].title, "skill": i["lesson"].skill,
                          "percent": i["percent"]} for i in u["lessons"]]}
            for u in plan
        ],
    }


@router.get("/lessons/{lesson_id}")
def api_lesson(lesson_id: int, user: User = Depends(api_user), db: OrmSession = Depends(get_db)):
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Chỉ dành cho học sinh")
    data = learning_svc.lesson_detail(db, user, lesson_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài học")
    lesson = data["lesson"]
    return {
        "id": lesson.id, "code": lesson.code, "title": lesson.title, "skill": lesson.skill,
        "unit": data["unit"].title, "content": data["content"],
        "transcript": lesson.transcript, "audio_url": lesson.audio_url,
        "percent": data["percent"], "seconds": data["seconds"],
        "question_count": data["question_count"],
    }


@router.post("/lessons/{lesson_id}/progress")
def api_progress(lesson_id: int, payload: dict = Body(...),
                 user: User = Depends(api_user), db: OrmSession = Depends(get_db)):
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Chỉ dành cho học sinh")
    if learning_svc.lesson_detail(db, user, lesson_id) is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài học")
    return learning_svc.add_progress(
        db, user, lesson_id,
        seconds=int(payload.get("seconds") or 0),
        percent=int(payload["percent"]) if payload.get("percent") is not None else None,
        completed=bool(payload.get("completed")),
    )


@router.get("/assignments")
def api_assignments(user: User = Depends(api_user), db: OrmSession = Depends(get_db)):
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Chỉ dành cho học sinh")
    return {"items": [
        {"id": t["assignment"].id, "title": t["assignment"].title,
         "kind": t["assignment"].kind, "lesson_id": t["assignment"].lesson_id,
         "deadline": t["assignment"].deadline.isoformat() if t["assignment"].deadline else None,
         "max_attempts": t["assignment"].max_attempts,
         "attempts_used": t["attempts_used"], "attempts_left": t["attempts_left"],
         "best": t["best"], "overdue": t["overdue"]}
        for t in asg_svc.student_todo(db, user)
    ]}


# ------------------------------------------------------------------ luyện tập


@router.get("/practice/{lesson_id}")
def api_practice(lesson_id: int, user: User = Depends(api_user), db: OrmSession = Depends(get_db)):
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Chỉ dành cho học sinh")
    state = practice_svc.practice_state(db, user, lesson_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài luyện tập")
    # KHÔNG trả correct_key ở đây — chỉ trả sau khi nộp (mục 3.10)
    return {
        "lesson": {"id": state["lesson"].id, "title": state["lesson"].title},
        "attempts_left": state["attempts_left"], "max_attempts": state["assignment"].max_attempts,
        "questions": [{"id": q.id, "prompt": q.prompt, "options": json.loads(q.options or "[]")}
                      for q in state["questions"]],
    }


@router.post("/practice/{lesson_id}/submit")
def api_practice_submit(lesson_id: int, payload: dict = Body(...),
                        user: User = Depends(api_user), db: OrmSession = Depends(get_db)):
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Chỉ dành cho học sinh")
    raw = payload.get("answers") or {}
    answers = {}
    for k, v in raw.items():
        try:
            answers[int(k)] = str(v).upper()[:1]
        except (TypeError, ValueError):
            continue

    submission, error = practice_svc.submit_practice(db, user, lesson_id, answers)
    if error:
        raise HTTPException(status_code=409, detail=error)

    review = practice_svc.submission_review(db, submission)
    left = max(0, (db.get(Assignment, submission.assignment_id).max_attempts
                   - submission.attempt_no))
    return {
        "submission_id": submission.id,
        "score": submission.final_score,
        "correct": sum(1 for r in review if r["is_correct"]),
        "total": len(review),
        "review": [{"question_id": r["question"].id, "prompt": r["question"].prompt,
                    "chosen": r["choice"], "correct_key": r["question"].correct_key,
                    "is_correct": r["is_correct"], "explanation": r["question"].explanation}
                   for r in review],
        "attempts_left": left,
    }
