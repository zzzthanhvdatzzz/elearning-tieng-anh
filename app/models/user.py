"""Người dùng, phiên đăng nhập — Bảng 3.8 nhóm "Người dùng"."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120), default="")
    # BR1: mỗi tài khoản MỘT vai trò chính; quyền bổ sung cấp riêng nếu cần.
    role: Mapped[str] = mapped_column(String(16), index=True)  # student|teacher|parent|admin
    cefr_level: Mapped[str | None] = mapped_column(String(4), default=None)  # A1..B2
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"


class Session(Base):
    """Phiên server-side: đăng xuất/khoá tài khoản là xoá dòng → thu hồi ngay.

    Lưu ý: bảng này KHÔNG có trong 16 bảng của Bảng 3.8 nhưng thiết kế ở mục 3.13
    ("Session thay vì JWT — thu hồi phiên ngay") bắt buộc phải có chỗ lưu.
    Cần bổ sung dòng này vào Bảng 3.8 trong báo cáo.
    """

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)

    user: Mapped[User] = relationship(back_populates="sessions")
