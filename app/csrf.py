"""CSRF — double-submit cookie.

Cookie `csrf` (KHÔNG HttpOnly để JS đọc được) + form field `_csrf` hoặc header
`X-CSRF-Token`. Kiểm tra bằng MỘT dependency gắn ở cấp app, không ở từng router,
để không endpoint ghi nào bị bỏ sót (mục 3.8).

Vì sao không làm ở middleware: middleware đọc `await request.form()` sẽ tiêu thụ
body, endpoint phía sau nhận 422. Dependency của FastAPI thì form đã được cache
nên endpoint đọc lại bình thường.
"""
import secrets

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
COOKIE = "csrf"


def get_csrf(request: Request) -> str:
    """Dùng trong template: <input type="hidden" name="_csrf" value="{{ csrf_token(request) }}">"""
    return request.cookies.get(COOKIE, "")


async def verify_csrf(request: Request) -> None:
    if request.method in SAFE_METHODS:
        return
    expected = request.cookies.get(COOKIE, "")
    sent = request.headers.get("X-CSRF-Token", "")
    if not sent:
        ctype = request.headers.get("content-type", "")
        if ctype.startswith(("application/x-www-form-urlencoded", "multipart/form-data")):
            form = await request.form()
            sent = str(form.get("_csrf", ""))
    if not expected or not sent or not secrets.compare_digest(expected, sent):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="CSRF token không hợp lệ hoặc đã hết hạn")


class CsrfCookieMiddleware(BaseHTTPMiddleware):
    """Chỉ CẤP cookie, không kiểm tra. Nhờ vậy mọi trang GET đều có token để dùng."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if COOKIE not in request.cookies:
            response.set_cookie(COOKIE, secrets.token_urlsafe(24), samesite="lax", max_age=60 * 60 * 12)
        return response
