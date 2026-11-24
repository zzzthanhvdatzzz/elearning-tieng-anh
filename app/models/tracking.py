"""Tiến độ, huy hiệu, thông báo — nhóm "Theo dõi" + "Phụ trợ"."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Progress(Base):
    """Lưu CẢ phần trăm VÀ số giây: 5 phút và 50 phút không được ra cùng một con số (mục 3.7)."""

    __tablename__ = "progress"
    __table_args__ = (UniqueConstraint("student_id", "lesson_id", name="uq_progress"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    percent: Mapped[int] = mapped_column(default=0)  # 0-100
    seconds: Mapped[int] = mapped_column(default=0)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Badge(Base):
    __tablename__ = "badges"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(String(120))
    condition: Mapped[str] = mapped_column(Text, default="{}")  # JSON điều kiện nhận


class StudentBadge(Base):
    __tablename__ = "student_badges"
    __table_args__ = (UniqueConstraint("student_id", "badge_id", name="uq_student_badge"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    badge_id: Mapped[int] = mapped_column(ForeignKey("badges.id", ondelete="CASCADE"))
    awarded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text, default="")
    is_read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class VideoProgress(Base):
    """Tiến độ xem video bài giảng.

    Chỉ cộng phần thời gian THỰC SỰ xem (client gửi nhịp tim), không cộng cú nhảy tua.
    Hoàn thành khi đã xem ≥ 80% thời lượng (quy tắc của nhóm).
    """

    __tablename__ = "video_progress"
    __table_args__ = (UniqueConstraint("student_id", "lesson_id", name="uq_video_progress"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    watched_seconds: Mapped[int] = mapped_column(default=0)   # tổng giây đã xem (chỉ tiến)
    duration_seconds: Mapped[int] = mapped_column(default=0)  # thời lượng video
    position: Mapped[int] = mapped_column(default=0)          # vị trí xa nhất đã xem tới
    checkpoint_passed: Mapped[bool] = mapped_column(default=False)  # đã trả lời đúng câu hỏi giữa video
    checkpoint_tries: Mapped[int] = mapped_column(default=0)
    checkpoint_question_id: Mapped[int | None] = mapped_column(
        ForeignKey("questions.id"), default=None)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(),
                                                 onupdate=func.now())


class AuditLog(Base):
    """Nhật ký hành động nhạy cảm: ai khoá tài khoản, duyệt phụ huynh, chấm/mở lại bài, import.

    Không lưu nội dung bài làm, chỉ lưu *việc gì* và *ai làm* — đủ để truy trách nhiệm,
    không thành bản sao dữ liệu học sinh (mục 1.3: quản trị không đọc nội dung gốc).
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, default=None)
    actor_email: Mapped[str] = mapped_column(String(255), default="")
    action: Mapped[str] = mapped_column(String(48), index=True)
    target: Mapped[str] = mapped_column(String(120), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
