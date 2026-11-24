"""routers/api_video.py — video bài giảng: xem (học sinh) và gắn/ghi đè/xoá (giáo viên).

Hai đường: link YouTube/Drive (nhúng iframe) hoặc file giáo viên tự quay tải lên
(phát bằng FileResponse có hỗ trợ Range để tua được).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as OrmSession

from app.db import get_db
from app.models import Lesson, User
from app.routers.api import api_user
from app.routers.api_teacher import teacher_only
from app.services import video as video_svc

router = APIRouter(prefix="/api", tags=["video"])


def _lesson_or_404(db: OrmSession, lesson_id: int) -> Lesson:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài học")
    return lesson


def _manage_or_403(db: OrmSession, teacher: User, lesson: Lesson) -> None:
    if not video_svc.can_manage(db, teacher, lesson):
        raise HTTPException(status_code=403,
                            detail="Chỉ giáo viên dạy khối này mới gắn được video bài giảng")


def _options_of(question) -> list[dict]:
    """questions.options là JSON: có thể là ["...","..."] hoặc [{"key":"A","text":"..."}]."""
    import json

    try:
        raw = json.loads(question.options or "[]")
    except (TypeError, ValueError):
        raw = []
    out = []
    for i, item in enumerate(raw):
        if isinstance(item, dict):
            out.append({"key": str(item.get("key") or chr(65 + i)),
                        "text": str(item.get("text") or "")})
        else:
            out.append({"key": chr(65 + i), "text": str(item)})
    return out


@router.get("/lessons/{lesson_id}/video")
def lesson_video(lesson_id: int, user: User = Depends(api_user),
                 db: OrmSession = Depends(get_db)):
    lesson = _lesson_or_404(db, lesson_id)
    if not video_svc.can_view(db, user, lesson):
        raise HTTPException(status_code=403, detail="Bài học này không thuộc khối bạn học")
    progress = (video_svc.progress_of(db, user, lesson)
                if user.role == "student" else None)
    checkpoint = None
    if progress and progress.get("needs_checkpoint"):
        q = video_svc.checkpoint_question(db, lesson)
        if q is not None:
            checkpoint = {"question": q.prompt, "options": _options_of(q), "id": q.id}
    return {"lesson": {"id": lesson.id, "title": lesson.title}, **video_svc.info(lesson),
            "progress": progress,
            "checkpoint": checkpoint,
            "rules": {"complete_ratio": video_svc.COMPLETE_RATIO,
                      "checkpoint_ratio": video_svc.CHECKPOINT_RATIO,
                      "heartbeat_seconds": video_svc.HEARTBEAT_EVERY,
                      "seek_blocked": True},
            "can_manage": user.role == "teacher" and video_svc.can_manage(db, user, lesson)}


@router.post("/lessons/{lesson_id}/video/checkpoint")
def video_checkpoint(lesson_id: int, payload: dict,
                     user: User = Depends(api_user), db: OrmSession = Depends(get_db)):
    """Trả lời câu hỏi kiểm tra giữa video (bắt buộc để được tính hoàn thành)."""
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Chỉ học sinh trả lời câu hỏi kiểm tra")
    lesson = _lesson_or_404(db, lesson_id)
    if not video_svc.can_view(db, user, lesson):
        raise HTTPException(status_code=403, detail="Bài học này không thuộc khối bạn học")
    data, error = video_svc.answer_checkpoint(db, user, lesson, str(payload.get("answer", "")))
    if error:
        raise HTTPException(status_code=409, detail=error)
    return data


@router.post("/lessons/{lesson_id}/video/heartbeat")
def video_heartbeat(lesson_id: int, payload: dict,
                    user: User = Depends(api_user), db: OrmSession = Depends(get_db)):
    """Client gửi mỗi ~10 giây. Server chỉ cộng phần xem thật, không cộng cú tua."""
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Chỉ học sinh có tiến độ xem video")
    lesson = _lesson_or_404(db, lesson_id)
    if not video_svc.can_view(db, user, lesson):
        raise HTTPException(status_code=403, detail="Bài học này không thuộc khối bạn học")
    if video_svc.info(lesson)["kind"] is None:
        raise HTTPException(status_code=409, detail="Bài học chưa có video")

    try:
        position = float(payload.get("position", 0))
        duration = float(payload.get("duration", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="position/duration phải là số")

    data, error = video_svc.record_heartbeat(db, user, lesson, position, duration)
    if error:
        raise HTTPException(status_code=422, detail=error)
    return data


@router.get("/lessons/{lesson_id}/video/stream")
def lesson_video_stream(lesson_id: int, user: User = Depends(api_user),
                        db: OrmSession = Depends(get_db)):
    lesson = _lesson_or_404(db, lesson_id)
    if not video_svc.can_view(db, user, lesson):
        raise HTTPException(status_code=403, detail="Không có quyền xem video này")
    path = video_svc.video_path_of(lesson.video_path)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Bài học chưa có video tải lên")
    # FileResponse của Starlette tự xử lý Range → tua được, không tải lại từ đầu
    return FileResponse(path, media_type="video/mp4", filename=path.name)


@router.post("/teacher/lessons/{lesson_id}/video")
def set_video_link(lesson_id: int, payload: dict, user: User = Depends(teacher_only),
                   db: OrmSession = Depends(get_db)):
    lesson = _lesson_or_404(db, lesson_id)
    _manage_or_403(db, user, lesson)

    url, error = video_svc.parse_link(str(payload.get("url", "")))
    if error:
        raise HTTPException(status_code=422, detail=error)

    lesson.video_url = url
    lesson.video_path = None            # một bài chỉ có một video: link thay thế file
    lesson.video_title = str(payload.get("title", "")).strip()[:200] or None
    lesson.video_by = user.id
    db.commit()
    return {"ok": True, **video_svc.info(lesson)}


@router.post("/teacher/lessons/{lesson_id}/video/upload")
async def upload_video(lesson_id: int, request: Request, file: UploadFile = File(...),
                       title: str = Form(""), user: User = Depends(teacher_only),
                       db: OrmSession = Depends(get_db)):
    lesson = _lesson_or_404(db, lesson_id)
    _manage_or_403(db, user, lesson)

    data = await file.read()
    path, error = video_svc.save_video(lesson.id, file.filename or "", data)
    if error:
        raise HTTPException(status_code=422, detail=error)

    old = video_svc.video_path_of(lesson.video_path)
    lesson.video_path = path
    lesson.video_url = None
    lesson.video_title = (title or file.filename or "")[:200] or None
    lesson.video_by = user.id
    db.commit()

    # Xoá tệp cũ sau khi đã ghi tệp mới (không xoá trước kẻo mất cả hai)
    if old and old.exists() and old != video_svc.video_path_of(path):
        try:
            old.unlink()
        except OSError:
            pass
    return {"ok": True, **video_svc.info(lesson)}


@router.delete("/teacher/lessons/{lesson_id}/video")
def delete_video(lesson_id: int, user: User = Depends(teacher_only),
                 db: OrmSession = Depends(get_db)):
    lesson = _lesson_or_404(db, lesson_id)
    _manage_or_403(db, user, lesson)
    old = video_svc.video_path_of(lesson.video_path)
    lesson.video_url = None
    lesson.video_path = None
    lesson.video_title = None
    lesson.video_by = None
    db.commit()
    if old and old.exists():
        try:
            old.unlink()
        except OSError:
            pass
    return {"ok": True}
