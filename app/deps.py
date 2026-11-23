"""Dependency dùng chung: lấy người dùng hiện tại và chặn theo vai trò.

Mọi endpoint bảo vệ đều đi qua đây, nên quy tắc quyền chỉ nằm ở một chỗ (mục 3.12).
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session as OrmSession

from app.db import get_db
from app.models import User
from app.services.security import COOKIE_NAME, get_session_user


def optional_user(request: Request, db: OrmSession = Depends(get_db)) -> User | None:
    return get_session_user(db, request.cookies.get(COOKIE_NAME))


def current_user(request: Request, db: OrmSession = Depends(get_db)) -> User:
    """Chưa đăng nhập → chuyển hướng về trang đăng nhập (303) thay vì JSON 401."""
    user = get_session_user(db, request.cookies.get(COOKIE_NAME))
    if user is None:
        raise HTTPException(status_code=303, headers={"Location": "/auth/login"})
    return user


def role_required(*roles: str):
    def _dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập chức năng này")
        return user

    return _dep


def require_owner_or_teacher(staff: bool = False):
    """BR9 + quyền S: học sinh chỉ xem dữ liệu của mình; giáo viên chỉ lớp mình.

    Bản Sprint 0 mới xử lý nhánh "chính chủ"; nhánh giáo viên/phụ huynh được nối
    khi có module report (tuần 5). Viết sẵn chữ ký để 24 endpoint dùng chung.
    """

    def _check(user: User, student_id: int) -> None:
        if user.role in ("teacher", "admin"):
            if staff:
                return
            raise HTTPException(status_code=403, detail="Cần quan hệ lớp học để xem dữ liệu này")
        if user.id != student_id:
            raise HTTPException(status_code=403, detail="Bạn chỉ được xem dữ liệu của mình")

    return _check
