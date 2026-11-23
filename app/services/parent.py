"""services/parent.py — F3/BR3: liên kết phụ huynh ↔ học sinh, cần giáo viên duyệt.

BR3: phụ huynh CHỈ xem được dữ liệu của con sau khi liên kết được học sinh tạo và giáo
viên xác nhận. Mọi truy vấn báo cáo của phụ huynh phải đi qua `approved_student_ids`.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.models import Class, Enrollment, ParentLink, User


def request_link(db: OrmSession, parent: User, student_email: str) -> tuple[ParentLink | None, str | None]:
    student = db.execute(
        select(User).where(User.email == student_email.strip().lower())
    ).scalar_one_or_none()
    if student is None or student.role != "student":
        return None, "Không tìm thấy tài khoản học sinh với email này."

    existing = db.execute(
        select(ParentLink).where(ParentLink.parent_id == parent.id,
                                 ParentLink.student_id == student.id)
    ).scalars().first()
    if existing is not None:
        if existing.status == "approved":
            return None, "Bạn đã liên kết với học sinh này rồi."
        if existing.status == "pending":
            return None, "Yêu cầu đang chờ giáo viên duyệt."
        existing.status = "pending"      # bị từ chối trước đó → cho gửi lại
        db.commit()
        return existing, None

    link = ParentLink(parent_id=parent.id, student_id=student.id, status="pending")
    db.add(link)
    db.commit()
    db.refresh(link)
    return link, None


def approved_student_ids(db: OrmSession, parent: User) -> list[int]:
    return [
        row.student_id
        for row in db.execute(
            select(ParentLink).where(ParentLink.parent_id == parent.id,
                                     ParentLink.status == "approved")
        ).scalars()
    ]


def children(db: OrmSession, parent: User) -> list[User]:
    ids = approved_student_ids(db, parent)
    if not ids:
        return []
    return list(db.execute(select(User).where(User.id.in_(ids))).scalars())


def pending_for_teacher(db: OrmSession, teacher: User) -> list[dict]:
    """Yêu cầu chờ duyệt của học sinh thuộc lớp giáo viên phụ trách (BR9)."""
    rows = db.execute(
        select(ParentLink, User, Enrollment, Class)
        .join(User, User.id == ParentLink.student_id)
        .join(Enrollment, Enrollment.student_id == User.id)
        .join(Class, Class.id == Enrollment.class_id)
        .where(ParentLink.status == "pending", Class.teacher_id == teacher.id,
               Enrollment.status == "active")
    ).all()
    out = []
    for link, student, _, klass in rows:
        parent = db.get(User, link.parent_id)
        out.append({"link": link, "student": student, "parent": parent, "klass": klass})
    return out


def decide(db: OrmSession, teacher: User, link_id: int, approve: bool) -> tuple[bool, str | None]:
    link = db.get(ParentLink, link_id)
    if link is None:
        return False, "Không tìm thấy yêu cầu liên kết."
    # chỉ giáo viên phụ trách lớp của học sinh mới được duyệt
    row = db.query(Enrollment).join(Class, Class.id == Enrollment.class_id).filter(
        Enrollment.student_id == link.student_id, Class.teacher_id == teacher.id
    ).first()
    if row is None:
        return False, "Học sinh này không thuộc lớp bạn phụ trách."
    link.status = "approved" if approve else "rejected"
    link.approved_by = teacher.id
    db.commit()
    return True, None


def can_view(db: OrmSession, parent: User, student_id: int) -> bool:
    return student_id in approved_student_ids(db, parent)


def unlink(db: OrmSession, parent: User, student_id: int) -> bool:
    """AC3.3: huỷ liên kết thì mất quyền ngay (xoá dòng, không chỉ đổi trạng thái)."""
    row = db.execute(
        select(ParentLink).where(ParentLink.parent_id == parent.id,
                                 ParentLink.student_id == student_id)
    ).scalar_one_or_none()
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True
