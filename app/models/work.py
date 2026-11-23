"""Giao bài, bài nộp, điểm — nhóm "Giao bài" (trái tim của hệ thống)."""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # placement dùng CHUNG bảng này (quyết định ở mục 3.7) — tránh nhân đôi luồng chấm.
    kind: Mapped[str] = mapped_column(String(16), default="practice")  # practice|placement|writing|speaking
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id"), default=None)
    title: Mapped[str] = mapped_column(String(200))
    deadline: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    max_attempts: Mapped[int] = mapped_column(default=1)  # BR7
    weight_auto: Mapped[float] = mapped_column(Float, default=1.0)  # BR6
    weight_teacher: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AssignmentQuestion(Base):
    __tablename__ = "assignment_questions"
    __table_args__ = (UniqueConstraint("assignment_id", "question_id", name="uq_aq"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    order_no: Mapped[int] = mapped_column(default=1)
    points: Mapped[float] = mapped_column(Float, default=1.0)


class Submission(Base):
    """Máy trạng thái ở Hình 3.8: pending → auto_scored → graded | expired | late_zero."""

    __tablename__ = "submissions"
    __table_args__ = (UniqueConstraint("assignment_id", "student_id", "attempt_no", name="uq_attempt"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    attempt_no: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    auto_score: Mapped[float | None] = mapped_column(Float, default=None)
    teacher_score: Mapped[float | None] = mapped_column(Float, default=None)
    final_score: Mapped[float | None] = mapped_column(Float, default=None)
    late_days: Mapped[int] = mapped_column(default=0)
    # Bài viết / bài nói: Bảng 3.8 chưa có cột này nhưng F8 (luyện viết) và F3 (bài viết
    # placement) bắt buộc phải lưu nội dung → cần bổ sung vào báo cáo.
    text_content: Mapped[str] = mapped_column(Text, default="")
    audio_path: Mapped[str | None] = mapped_column(String(255), default=None)
    # Mức CEFR hệ thống đề xuất trước khi giáo viên xác nhận (UC-03 bước 5)
    cefr_proposed: Mapped[str | None] = mapped_column(String(4), default=None)
    graded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    graded_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    answers: Mapped[list["Answer"]] = relationship(back_populates="submission", cascade="all, delete-orphan")
    rubric_scores: Mapped[list["RubricScore"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (UniqueConstraint("submission_id", "question_id", name="uq_answer"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    choice: Mapped[str] = mapped_column(String(8), default="")
    is_correct: Mapped[bool] = mapped_column(default=False)

    submission: Mapped[Submission] = relationship(back_populates="answers")


class RubricScore(Base):
    """Tách khỏi submissions để 4 tiêu chí = 4 dòng, không phải JSON (mục 3.7)."""

    __tablename__ = "rubric_scores"
    __table_args__ = (UniqueConstraint("submission_id", "criterion", name="uq_rubric"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), index=True)
    criterion: Mapped[str] = mapped_column(String(32))  # task|grammar|vocab|coherence
    score: Mapped[float] = mapped_column(Float, default=0.0)  # 0–2,5
    comment: Mapped[str] = mapped_column(Text, default="")
    grader_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    submission: Mapped[Submission] = relationship(back_populates="rubric_scores")
