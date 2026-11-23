"""services/grading.py — chấm bài tự luận bằng rubric 4 tiêu chí (BR6, AC12.2).

Dùng chung cho bài viết và bài nói: cùng thang điểm, cùng quy tắc bắt buộc nhận xét.
Công thức trộn điểm theo trọng số của assignment, không hard-code 0,7/0,3.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.models import Assignment, RubricScore, Submission, User
from app.services.scoring import final_score, rubric_total

RUBRIC_CRITERIA = ["task", "grammar", "vocab", "coherence"]
RUBRIC_LABELS = {
    "task": "Hoàn thành yêu cầu đề",
    "grammar": "Ngữ pháp",
    "vocab": "Từ vựng",
    "coherence": "Liên kết câu",
}
MIN_COMMENT_BELOW = 5.0


def final_for(assignment: Assignment, auto: float | None, teacher: float | None) -> float | None:
    """Trọng số lấy từ assignment: bài chỉ có tự động → 1.0/0.0, bài chỉ có giáo viên → 0.0/1.0.

    Bài trộn dùng đúng 0,7/0,3 (BR6). Thiếu một phần thì trả None — không có điểm cuối.
    """
    if assignment.weight_teacher <= 0:
        return auto
    if assignment.weight_auto <= 0:
        return teacher
    return final_score(auto, teacher, assignment.weight_auto, assignment.weight_teacher)


def grade_writing(
    db: OrmSession,
    submission: Submission,
    rubric: dict[str, float],
    teacher: User,
    comment: str = "",
) -> tuple[Submission, str | None]:
    if submission.status == "graded":
        return submission, "Bài này đã chấm rồi. Muốn chấm lại phải mở lại và ghi lý do."

    if set(rubric) != set(RUBRIC_CRITERIA):
        return submission, "Cần chấm đủ bốn tiêu chí."
    if any(not (0 <= v <= 2.5) for v in rubric.values()):
        return submission, "Mỗi tiêu chí cho điểm từ 0 đến 2,5."

    teacher_total = rubric_total(list(rubric.values()))
    if teacher_total < MIN_COMMENT_BELOW and not comment.strip():
        # AC12.2
        return submission, "Điểm dưới trung bình nên bắt buộc nhập nhận xét cho học sinh."

    for criterion, score in rubric.items():
        db.add(RubricScore(
            submission_id=submission.id,
            criterion=criterion,
            score=score,
            comment=comment.strip(),
            grader_id=teacher.id,
        ))

    assignment = db.get(Assignment, submission.assignment_id)
    submission.teacher_score = teacher_total
    submission.final_score = final_for(assignment, submission.auto_score, teacher_total) if assignment else teacher_total
    submission.status = "graded"
    submission.graded_by = teacher.id
    submission.graded_at = datetime.utcnow()
    db.commit()
    db.refresh(submission)
    return submission, None


def rubric_of(db: OrmSession, submission_id: int) -> dict[str, float]:
    rows = db.execute(select(RubricScore).where(RubricScore.submission_id == submission_id)).scalars()
    return {r.criterion: r.score for r in rows}


def feedback_of(db: OrmSession, submission_id: int) -> str:
    row = db.execute(
        select(RubricScore).where(RubricScore.submission_id == submission_id).limit(1)
    ).scalar_one_or_none()
    return row.comment if row else ""
