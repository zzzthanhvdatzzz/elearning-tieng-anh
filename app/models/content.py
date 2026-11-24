"""Nội dung học: Unit, Lesson, Question — nhóm "Nội dung"."""
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(primary_key=True)
    grade: Mapped[int] = mapped_column(index=True)  # 8 | 10
    code: Mapped[str] = mapped_column(String(16))  # "U1", "U2"
    title: Mapped[str] = mapped_column(String(160))  # "Local Environment"
    order_no: Mapped[int] = mapped_column(default=1)

    lessons: Mapped[list["Lesson"]] = relationship(back_populates="unit", cascade="all, delete-orphan")


class Lesson(Base):
    """Nội dung bài học lưu dạng JSON (quyết định ở Bảng 3.12): linh hoạt nhiều dạng bài."""

    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(16))  # "U1-L1"
    title: Mapped[str] = mapped_column(String(160))
    skill: Mapped[str] = mapped_column(String(16))  # vocab|grammar|listening|reading|writing|speaking
    content: Mapped[str] = mapped_column(Text, default="{}")  # JSON: mục tiêu, từ vựng, ngữ pháp...
    audio_url: Mapped[str | None] = mapped_column(String(255), default=None)
    transcript: Mapped[str | None] = mapped_column(Text, default=None)
    # Video bài giảng: hoặc link ngoài (YouTube/Drive) hoặc file giáo viên tự tải lên.
    video_url: Mapped[str | None] = mapped_column(String(500), default=None)
    video_path: Mapped[str | None] = mapped_column(String(500), default=None)
    video_title: Mapped[str | None] = mapped_column(String(200), default=None)
    video_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    order_no: Mapped[int] = mapped_column(default=1)

    unit: Mapped[Unit] = relationship(back_populates="lessons")
    questions: Mapped[list["Question"]] = relationship(back_populates="lesson", cascade="all, delete-orphan")


class Question(Base):
    """Đáp án đúng nằm ở server — client chỉ gửi lựa chọn (mục 3.10)."""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    qtype: Mapped[str] = mapped_column(String(16), default="mcq")  # mcq|gap|essay
    skill: Mapped[str] = mapped_column(String(16), default="grammar")  # grammar|reading|listening
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[str] = mapped_column(Text, default="[]")  # JSON list 4 lựa chọn
    correct_key: Mapped[str] = mapped_column(String(8), default="A")  # A|B|C|D
    explanation: Mapped[str] = mapped_column(Text, default="")
    order_no: Mapped[int] = mapped_column(default=1)

    lesson: Mapped[Lesson] = relationship(back_populates="questions")
