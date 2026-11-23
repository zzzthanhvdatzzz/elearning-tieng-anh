"""services/admin.py — F2 (tài khoản) và F15 (import câu hỏi từ Excel).

Import kiểm tra TỪNG DÒNG: dòng sai bị bỏ qua và báo lý do, dòng đúng vẫn vào CSDL.
Đó là AC15.2 — nhập 235/240 dòng hợp lệ, 5 dòng lỗi để tải về xem.
"""
from __future__ import annotations

import io
import json

from sqlalchemy import or_, select
from sqlalchemy.orm import Session as OrmSession

from app.models import Lesson, Question, User
from app.services.security import hash_password, revoke_all_sessions

ROLES = ("student", "teacher", "parent", "admin")
IMPORT_COLUMNS = ["skill", "prompt", "option_a", "option_b", "option_c", "option_d",
                  "correct_key", "explanation"]
SKILLS = ("grammar", "reading", "listening", "vocab", "writing", "speaking")


# ------------------------------------------------------------------ tài khoản


def list_users(db: OrmSession, role: str | None = None, q: str = "") -> list[User]:
    stmt = select(User).order_by(User.created_at.desc())
    if role in ROLES:
        stmt = stmt.where(User.role == role)
    if q.strip():
        needle = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(User.email.ilike(needle), User.full_name.ilike(needle)))
    return list(db.execute(stmt).scalars())


def create_user(db: OrmSession, email: str, full_name: str, role: str,
                password: str) -> tuple[User | None, str | None]:
    email = email.strip().lower()
    if role not in ROLES:
        return None, "Vai trò không hợp lệ."
    if len(password) < 8:
        return None, "Mật khẩu phải có ít nhất 8 ký tự."
    if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
        return None, "Email này đã được đăng ký."
    user = User(email=email, password_hash=hash_password(password),
                full_name=full_name.strip(), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, None


def set_active(db: OrmSession, user_id: int, active: bool) -> tuple[User | None, str | None]:
    user = db.get(User, user_id)
    if user is None:
        return None, "Không tìm thấy tài khoản."
    user.is_active = active
    db.commit()
    if not active:
        # US2/AC2: khoá tài khoản thì mọi phiên đang mở phải chết ngay
        revoke_all_sessions(db, user_id)
    return user, None


def reset_password(db: OrmSession, user_id: int, new_password: str) -> tuple[User | None, str | None]:
    user = db.get(User, user_id)
    if user is None:
        return None, "Không tìm thấy tài khoản."
    if len(new_password) < 8:
        return None, "Mật khẩu phải có ít nhất 8 ký tự."
    user.password_hash = hash_password(new_password)
    db.commit()
    revoke_all_sessions(db, user_id)   # đổi mật khẩu → phiên cũ hết hiệu lực
    return user, None


# ------------------------------------------------------------------ import


def import_questions(db: OrmSession, lesson: Lesson, file_bytes: bytes) -> dict:
    """Đọc file .xlsx, thêm câu hỏi hợp lệ, trả báo cáo lỗi theo từng dòng."""
    from openpyxl import load_workbook

    try:
        wb = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001
        return {"added": 0, "errors": [{"row": 0, "reason": f"Không đọc được file Excel: {exc}"}]}

    ws = wb[wb.sheetnames[0]]
    rows = ws.iter_rows(values_only=True)
    try:
        header = [str(c).strip().lower() if c is not None else "" for c in next(rows)]
    except StopIteration:
        return {"added": 0, "errors": [{"row": 0, "reason": "File rỗng."}]}

    missing = [c for c in IMPORT_COLUMNS if c not in header]
    if missing:
        return {"added": 0, "errors": [{"row": 1,
                "reason": "Thiếu cột: " + ", ".join(missing)}]}
    index = {name: header.index(name) for name in IMPORT_COLUMNS}

    added, errors = 0, []
    existing = db.execute(select(Question.order_no).where(Question.lesson_id == lesson.id)).scalars().all()
    next_order = max(existing) + 1 if existing else 1

    for offset, row in enumerate(rows, start=2):
        values = {name: row[i] if i < len(row) else None for name, i in index.items()}
        if not any(values.values()):
            continue  # dòng trống

        skill = str(values["skill"] or "").strip().lower()
        prompt = str(values["prompt"] or "").strip()
        key = str(values["correct_key"] or "").strip().upper()
        options = [str(values[f"option_{k}"] or "").strip() for k in ("a", "b", "c", "d")]

        reason = None
        if skill not in SKILLS:
            reason = f"skill '{skill}' không hợp lệ (phải là {', '.join(SKILLS)})"
        elif not prompt:
            reason = "thiếu nội dung câu hỏi"
        elif key not in ("A", "B", "C", "D"):
            reason = f"correct_key '{key}' phải là A/B/C/D"
        elif any(not o for o in options):
            reason = "thiếu một trong bốn lựa chọn"
        if reason:
            errors.append({"row": offset, "reason": reason})
            continue

        db.add(Question(lesson_id=lesson.id, qtype="mcq", skill=skill, prompt=prompt,
                        options=json.dumps(options), correct_key=key,
                        explanation=str(values["explanation"] or "").strip(),
                        order_no=next_order))
        next_order += 1
        added += 1

    db.commit()
    return {"added": added, "errors": errors}
