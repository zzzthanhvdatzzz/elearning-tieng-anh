"""routers/auth.py — F1: đăng ký, đăng nhập, đăng xuất.

Router chỉ làm ba việc: nhận yêu cầu, kiểm tra quyền, gọi service, trả kết quả.
"""
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.db import get_db
from app.models import Class, Enrollment, User
from app.services.security import (
    COOKIE_NAME,
    SESSION_HOURS,
    create_session,
    hash_password,
    revoke_session,
    verify_password,
)
from app.templating import templates

router = APIRouter(prefix="/auth", tags=["auth"])


def _render_error(request: Request, template: str, msg: str, code: int = 400, **ctx):
    return templates.TemplateResponse(
        request, template, {"error": msg, **ctx}, status_code=code
    )


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(request, "auth_login.html", {"next": request.query_params.get("next", "/me")})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next_path: str = Form("/me"),
    db: OrmSession = Depends(get_db),
):
    user = db.execute(select(User).where(User.email == email.strip().lower())).scalar_one_or_none()
    # Thông báo chung cho cả hai trường hợp: không tiết lộ email nào đã tồn tại.
    if user is None or not verify_password(password, user.password_hash):
        return _render_error(request, "auth_login.html", "Email hoặc mật khẩu không đúng", 401,
                             next_path=next_path)
    if not user.is_active:
        return _render_error(request, "auth_login.html", "Tài khoản đã bị khoá", 423, next_path=next_path)

    token = create_session(db, user)
    target = next_path if next_path.startswith("/") and not next_path.startswith("//") else "/me"
    resp = RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)
    resp.set_cookie(
        COOKIE_NAME, token, httponly=True, samesite="lax", max_age=SESSION_HOURS * 3600, path="/"
    )
    return resp


@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse(request, "auth_register.html", {})


@router.post("/register")
def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(""),
    join_code: str = Form(...),
    db: OrmSession = Depends(get_db),
):
    email = email.strip().lower()

    # AC1.1 — email đã tồn tại thì không tạo (BR1)
    if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
        return _render_error(request, "auth_register.html", "Email này đã được đăng ký", 409,
                             email=email, full_name=full_name, join_code=join_code)

    # AC1.2 — mã lớp sai thì báo lỗi rõ, KHÔNG tạo tài khoản nửa vời
    klass = db.execute(
        select(Class).where(Class.join_code == join_code.strip().upper())
    ).scalar_one_or_none()
    if klass is None:
        return _render_error(request, "auth_register.html", "Mã lớp không đúng, hãy hỏi giáo viên", 422,
                             email=email, full_name=full_name, join_code=join_code)

    if len(password) < 8:
        return _render_error(request, "auth_register.html", "Mật khẩu phải có ít nhất 8 ký tự", 422,
                             email=email, full_name=full_name, join_code=join_code)

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        role="student",
    )
    db.add(user)
    db.flush()  # cần user.id trước khi tạo enrollment
    db.add(Enrollment(class_id=klass.id, student_id=user.id))
    db.commit()

    token = create_session(db, user)
    # AC1.3 — đăng ký xong vào thẳng bài kiểm tra đầu vào (S3)
    resp = RedirectResponse("/placement", status_code=status.HTTP_303_SEE_OTHER)
    resp.set_cookie(
        COOKIE_NAME, token, httponly=True, samesite="lax", max_age=SESSION_HOURS * 3600, path="/"
    )
    return resp


@router.get("/register-parent", response_class=HTMLResponse)
def register_parent_form(request: Request):
    return templates.TemplateResponse(request, "auth_register_parent.html", {})


@router.post("/register-parent")
def register_parent(request: Request,
                    email: str = Form(...),
                    password: str = Form(...),
                    full_name: str = Form(""),
                    db: OrmSession = Depends(get_db)):
    email = email.strip().lower()
    if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
        return _render_error(request, "auth_register_parent.html", "Email này đã được đăng ký", 409,
                             email=email, full_name=full_name)
    if len(password) < 8:
        return _render_error(request, "auth_register_parent.html", "Mật khẩu phải có ít nhất 8 ký tự", 422,
                             email=email, full_name=full_name)

    parent = User(email=email, password_hash=hash_password(password),
                  full_name=full_name.strip(), role="parent")
    db.add(parent)
    db.commit()
    db.refresh(parent)

    token = create_session(db, parent)
    resp = RedirectResponse("/parent", status_code=status.HTTP_303_SEE_OTHER)
    resp.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax",
                    max_age=SESSION_HOURS * 3600, path="/")
    return resp


@router.post("/logout")
def logout(request: Request, db: OrmSession = Depends(get_db)):
    revoke_session(db, request.cookies.get(COOKIE_NAME))
    resp = RedirectResponse("/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    resp.delete_cookie(COOKIE_NAME, path="/")
    return resp
