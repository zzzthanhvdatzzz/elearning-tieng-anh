"""services/classes.py — F10: giáo viên tạo lớp, sinh mã tham gia, ghi danh (BR2, BR9)."""
from __future__ import annotations

import secrets
import string

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.models import Class, Enrollment, User

CODE_ALPHABET = string.ascii_uppercase + string.digits


def _new_join_code(db: OrmSession) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        if db.execute(select(Class).where(Class.join_code == code)).scalar_one_or_none() is None:
            return code
    raise RuntimeError("không sinh được mã lớp duy nhất")


def create_class(db: OrmSession, teacher: User, name: str, grade: int) -> Class:
    klass = Class(name=name.strip()[:80], grade=int(grade), join_code=_new_join_code(db),
                  teacher_id=teacher.id)
    db.add(klass)
    db.commit()
    db.refresh(klass)
    return klass


def teacher_classes(db: OrmSession, teacher: User) -> list[dict]:
    classes = list(
        db.execute(select(Class).where(Class.teacher_id == teacher.id).order_by(Class.created_at.desc())).scalars()
    )
    out = []
    for klass in classes:
        count = len([e for e in klass.enrollments if e.status == "active"])
        out.append({"klass": klass, "students": count})
    return out


def owned_class(db: OrmSession, teacher: User, class_id: int) -> Class | None:
    """BR9: giáo viên chỉ thao tác trên lớp mình phụ trách."""
    klass = db.get(Class, class_id)
    if klass is None or klass.teacher_id != teacher.id:
        return None
    return klass


def roster(db: OrmSession, klass: Class) -> list[dict]:
    rows = db.execute(
        select(Enrollment, User)
        .join(User, User.id == Enrollment.student_id)
        .where(Enrollment.class_id == klass.id, Enrollment.status == "active")
        .order_by(User.full_name)
    ).all()
    return [{"enrollment": e, "student": u} for e, u in rows]


def add_student_by_email(db: OrmSession, klass: Class, email: str) -> tuple[User | None, str | None]:
    """BR2: học sinh chỉ thuộc tối đa MỘT lớp đang hoạt động cho mỗi môn trong học kỳ."""
    email = email.strip().lower()
    student = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if student is None:
        return None, "Không tìm thấy tài khoản với email này. Học sinh cần tự đăng ký trước."
    if student.role != "student":
        return None, "Tài khoản này không phải học sinh."

    existing = db.execute(
        select(Enrollment).where(Enrollment.student_id == student.id, Enrollment.status == "active")
    ).scalars().first()
    if existing is not None:
        if existing.class_id == klass.id:
            return None, "Học sinh đã ở trong lớp này rồi."
        return None, "Học sinh đang thuộc một lớp khác (BR2: mỗi môn một lớp mỗi học kỳ)."

    db.add(Enrollment(class_id=klass.id, student_id=student.id))
    db.commit()
    return student, None


def remove_student(db: OrmSession, klass: Class, student_id: int) -> bool:
    row = db.execute(
        select(Enrollment).where(Enrollment.class_id == klass.id, Enrollment.student_id == student_id,
                                 Enrollment.status == "active")
    ).scalar_one_or_none()
    if row is None:
        return False
    row.status = "removed"   # giữ lịch sử, không xoá dòng
    db.commit()
    return True
