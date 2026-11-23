"""routers/speaking.py — S7 ghi âm / tải file bài nói (F7).

Hai đường vào: ghi âm bằng MediaRecorder (chỉ chạy HTTPS) hoặc tải file ghi âm sẵn
(phương án dự phòng cho rủi ro R2).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session as OrmSession

from app.db import get_db
from app.deps import current_user, role_required
from app.models import Assignment, Class, Submission, User
from app.services import speaking as svc
from app.services.storage import ALLOWED_EXT, MAX_AUDIO_BYTES, audio_response_path
from app.templating import templates

router = APIRouter(tags=["speaking"])


@router.get("/speaking/{lesson_id}", response_class=HTMLResponse)
def speaking_form(lesson_id: int, request: Request,
                  user: User = Depends(role_required("student")),
                  db: OrmSession = Depends(get_db)):
    state = svc.speaking_state(db, user, lesson_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài nói")
    if state["attempts_left"] <= 0 and state["last"] is not None:
        return RedirectResponse(f"/speaking/{lesson_id}/result", status_code=303)
    return templates.TemplateResponse(
        request, "speaking_form.html",
        {"user": user, "title": "Luyện nói", "max_mb": MAX_AUDIO_BYTES // (1024 * 1024),
         "exts": ", ".join(sorted(ALLOWED_EXT)), **state},
    )


@router.post("/speaking/{lesson_id}/upload")
def speaking_upload(lesson_id: int, request: Request,
                    file: UploadFile | None = File(None),
                    user: User = Depends(role_required("student")),
                    db: OrmSession = Depends(get_db)):
    if file is None:
        return _error_page(request, db, user, lesson_id, "Chưa chọn file ghi âm", 422)

    data = file.file.read(MAX_AUDIO_BYTES + 1)   # endpoint sync → đọc đồng bộ
    submission, error = svc.submit_speaking(db, user, lesson_id, file.filename or "bai-noi.webm", data)
    if error:
        return _error_page(request, db, user, lesson_id, error, 422)
    return RedirectResponse(f"/speaking/{lesson_id}/result", status_code=303)


def _error_page(request, db, user, lesson_id, message, code):
    state = svc.speaking_state(db, user, lesson_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài nói")
    return templates.TemplateResponse(
        request, "speaking_form.html",
        {"user": user, "error": message, "max_mb": MAX_AUDIO_BYTES // (1024 * 1024),
         "exts": ", ".join(sorted(ALLOWED_EXT)), **state},
        status_code=code,
    )


@router.get("/speaking/{lesson_id}/result", response_class=HTMLResponse)
def speaking_result(lesson_id: int, request: Request,
                    user: User = Depends(role_required("student")),
                    db: OrmSession = Depends(get_db)):
    state = svc.speaking_state(db, user, lesson_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài nói")
    return templates.TemplateResponse(
        request, "speaking_result.html",
        {"user": user, "title": "Bài nói của tôi", **state},
    )


@router.get("/audio/{submission_id}")
def audio(submission_id: int, user: User = Depends(current_user),
          db: OrmSession = Depends(get_db)):
    """Trả file audio có kiểm quyền — KHÔNG mount thư mục uploads tĩnh (NFR3, mục 1.3)."""
    submission = db.get(Submission, submission_id)
    if submission is None or not submission.audio_path:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi")

    # Mục 1.3: quản trị KHÔNG được nghe audio gốc của học sinh; chỉ chính chủ và giáo viên lớp đó.
    allowed = user.id == submission.student_id
    if not allowed and user.role == "teacher":
        allowed = db.query(Assignment).join(Class, Class.id == Assignment.class_id).filter(
            Assignment.id == submission.assignment_id, Class.teacher_id == user.id
        ).first() is not None
    if not allowed:
        raise HTTPException(status_code=403, detail="Bạn không có quyền nghe bản ghi này")

    path = audio_response_path(submission.audio_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File đã bị xoá theo chính sách lưu trữ")
    return FileResponse(path)
