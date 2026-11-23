"""Điểm vào ứng dụng — cấu hình app, middleware, và các trang khung.

Sprint 0 (tuần 2, mốc M2): đăng nhập chạy được, tạo lớp chạy được.
Mỗi nhóm chức năng mới sẽ là một router riêng trong app/routers/.
"""
import os
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session as OrmSession

from app.csrf import CsrfCookieMiddleware, verify_csrf
from app.db import get_db
from app.deps import current_user, optional_user
from app.models import User
from app.routers import admin, auth, learning, parent, placement, practice, report, teacher, writing
from app.templating import templates

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Hệ thống học tiếng Anh trực tuyến — Nhóm 05",
    dependencies=[Depends(verify_csrf)],  # CSRF áp cho MỌI endpoint ghi
)
app.add_middleware(CsrfCookieMiddleware)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.include_router(auth.router)
app.include_router(placement.router)
app.include_router(learning.router)
app.include_router(practice.router)
app.include_router(writing.router)
app.include_router(teacher.router)
app.include_router(report.router)
app.include_router(parent.router)
app.include_router(admin.router)


@app.on_event("startup")
def _start_background_jobs() -> None:
    """Worker báo cáo tuần chạy trong cùng tiến trình (mục 3.1) — tắt được bằng DISABLE_JOBS=1."""
    if os.getenv("DISABLE_JOBS") == "1":
        return
    from app.jobs import weekly_email

    weekly_email.start()


@app.get("/health")
def health():
    with db_engine().connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "db": "ok"}


def db_engine():
    from app.db import engine

    return engine


@app.get("/", response_class=HTMLResponse)
def index(request: Request, user: User | None = Depends(optional_user)):
    return templates.TemplateResponse(request, "index.html", {"user": user, "title": "Trang chủ"})


@app.get("/me", response_class=HTMLResponse)
def me(request: Request, user: User = Depends(current_user)):
    """Trang tạm: chứng minh phiên đăng nhập hoạt động và phân quyền đúng vai trò."""
    return templates.TemplateResponse(request, "me.html", {"user": user, "title": "Tài khoản"})


@app.get("/placement", response_class=HTMLResponse)
def placement_placeholder(request: Request, user: User = Depends(current_user),
                          db: OrmSession = Depends(get_db)):
    """S3 — sẽ thay bằng bài kiểm tra thật ở Sprint 1 (D1)."""
    return templates.TemplateResponse(request, "placement_soon.html", {"user": user, "title": "Kiểm tra đầu vào"})
