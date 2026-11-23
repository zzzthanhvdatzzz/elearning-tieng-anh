"""Lớp, ghi danh, liên kết phụ huynh — nhóm "Người dùng"."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Class(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    grade: Mapped[int] = mapped_column()  # 8 (THCS) hoặc 10 (THPT)
    join_code: Mapped[str] = mapped_column(String(6), unique=True, index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="klass", cascade="all, delete-orphan")


class Enrollment(Base):
    """BR2: mỗi học sinh tối đa một lớp cho mỗi môn trong một học kỳ."""

    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("class_id", "student_id", name="uq_enrollment"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active|removed
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    klass: Mapped[Class] = relationship(back_populates="enrollments")


class ParentLink(Base):
    """BR3: phụ huynh chỉ xem dữ liệu của con sau khi giáo viên duyệt."""

    __tablename__ = "parent_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|approved|rejected
    requested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
