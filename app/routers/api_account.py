"""routers/api_account.py — tài khoản tự phục vụ: đổi mật khẩu của chính mình."""
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session as OrmSession

from app.db import get_db
from app.models import User
from app.routers.api import api_user
from app.services import security

router = APIRouter(prefix="/api", tags=["account"])

ERRORS = {
    "wrong_old": "Mật khẩu hiện tại không đúng.",
    "too_short": "Mật khẩu mới phải có ít nhất 8 ký tự.",
    "same": "Mật khẩu mới phải khác mật khẩu hiện tại.",
}


@router.post("/auth/password")
def change_password(request: Request, payload: dict = Body(...),
                    user: User = Depends(api_user), db: OrmSession = Depends(get_db)):
    ok, error = security.change_password(
        db, user,
        str(payload.get("old_password", "")),
        str(payload.get("new_password", "")),
        keep_token=request.cookies.get(security.COOKIE_NAME),
    )
    if not ok:
        raise HTTPException(status_code=400, detail=ERRORS.get(error or "", "Không đổi được mật khẩu."))
    return {"ok": True, "message": "Đã đổi mật khẩu. Các thiết bị khác đã bị đăng xuất."}
