"""services/grading.py — chấm bài tự luận/bài nói bằng rubric 4 tiêu chí (BR6, AC12.2).

Bài viết và bài nói dùng cùng thang 4×2,5 và cùng quy tắc bắt buộc nhận xét, chỉ khác
tên tiêu chí. Công thức trộn điểm lấy theo trọng số của assignment, không hard-code 0,7/0,3.

Quy tắc chấm lại: bài đã chấm bị khoá. Giáo viên phải "mở lại" kèm lý do (lưu vào audit log),
sau đó mới chấm lại được — nhờ vậy không có chuyện sửa điểm âm thầm.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as OrmSession

from app.models import Assignment, RubricScore, Submission, User
from app.services import audit
from app.services.scoring import final_score, rubric_total, with_late_penalty

RUBRIC_CRITERIA = ["task", "grammar", "vocab", "coherence"]
RUBRIC_LABELS = {
    "task": "Hoàn thành yêu cầu đề",
    "grammar": "Ngữ pháp",
    "vocab": "Từ vựng",
    "coherence": "Liên kết câu",
}

SPEAKING_CRITERIA = ["task", "pronunciation", "fluency", "vocab"]
SPEAKING_LABELS = {
    "task": "Hoàn thành yêu cầu đề",
    "pronunciation": "Phát âm",
    "fluency": "Độ trôi chảy",
    "vocab": "Từ vựng",
}
MIN_COMMENT_BELOW = 5.0


def criteria_for(kind: str) -> tuple[list[str], dict[str, str]]:
    if kind == "speaking":
        return SPEAKING_CRITERIA, SPEAKING_LABELS
    return RUBRIC_CRITERIA, RUBRIC_LABELS


def final_for(assignment: Assignment, auto: float | None, teacher: float | None) -> float | None:
    """Trọng số lấy từ assignment: bài chỉ có tự động → 1.0/0.0, bài chỉ có giáo viên → 0.0/1.0.

    Bài trộn dùng đúng 0,7/0,3 (BR6). Thiếu một phần thì trả None — không có điểm cuối.
    """
    if assignment.weight_teacher <= 0:
        return auto
    if assignment.weight_auto <= 0:
        return teacher
    return final_score(auto, teacher, assignment.weight_auto, assignment.weight_teacher)


def grade_submission(
    db: OrmSession,
    submission: Submission,
    rubric: dict[str, float],
    teacher: User,
    comment: str = "",
    criteria: list[str] | None = None,
    labels: dict[str, str] | None = None,
) -> tuple[Submission, str | None]:
    assignment = db.get(Assignment, submission.assignment_id)
    kind = assignment.kind if assignment else "writing"
    criteria = criteria or criteria_for(kind)[0]
    labels = labels or criteria_for(kind)[1]

    if submission.status == "graded":
        return submission, "Bài này đã chấm rồi. Muốn chấm lại phải mở lại và ghi lý do."

    if set(rubric) != set(criteria):
        missing = [labels.get(c, c) for c in criteria if c not in rubric]
        return submission, f"Cần chấm đủ bốn tiêu chí. Còn thiếu: {', '.join(missing) or 'không rõ'}."
    if any(not (0 <= float(v) <= 2.5) for v in rubric.values()):
        return submission, "Mỗi tiêu chí cho điểm từ 0 đến 2,5."

    teacher_total = rubric_total([float(v) for v in rubric.values()])
    if teacher_total < MIN_COMMENT_BELOW and not comment.strip():
        return submission, "Điểm dưới trung bình nên bắt buộc nhập nhận xét cho học sinh."

    # Chấm lại sau khi mở: xoá điểm cũ để không cộng dồn hai bộ tiêu chí
    db.execute(delete(RubricScore).where(RubricScore.submission_id == submission.id))
    for criterion, score in rubric.items():
        db.add(RubricScore(
            submission_id=submission.id,
            criterion=criterion,
            score=float(score),
            comment=comment.strip(),
            grader_id=teacher.id,
        ))

    raw_final = final_for(assignment, submission.auto_score, teacher_total) if assignment else teacher_total
    # BR8: nộp muộn trừ 10%/ngày, tối đa 3 ngày; quá 3 ngày nhận 0.
    if raw_final is not None and submission.late_days:
        raw_final = with_late_penalty(raw_final, submission.late_days)
    submission.teacher_score = teacher_total
    submission.final_score = raw_final
    submission.status = "graded"
    submission.graded_by = teacher.id
    submission.graded_at = datetime.utcnow()

    from app.services import notify

    where = "bài nói" if kind == "speaking" else "bài viết"
    notify.push(db, submission.student_id,
                f"Bài đã được chấm: {assignment.title if assignment else 'bài tập'}",
                f"Điểm cuối: {raw_final}/10. Mở mục {where} để xem nhận xét của giáo viên.")
    audit.log(db, teacher, "grade", f"submission:{submission.id}",
              f"{kind} · điểm giáo viên {teacher_total} · cuối {raw_final}")
    db.commit()
    db.refresh(submission)
    return submission, None


def grade_writing(db: OrmSession, submission: Submission, rubric: dict[str, float],
                  teacher: User, comment: str = "") -> tuple[Submission, str | None]:
    return grade_submission(db, submission, rubric, teacher, comment,
                            criteria=RUBRIC_CRITERIA, labels=RUBRIC_LABELS)


def grade_speaking(db: OrmSession, submission: Submission, rubric: dict[str, float],
                   teacher: User, comment: str = "") -> tuple[Submission, str | None]:
    return grade_submission(db, submission, rubric, teacher, comment,
                            criteria=SPEAKING_CRITERIA, labels=SPEAKING_LABELS)


def can_grade(db: OrmSession, teacher: User, submission: Submission) -> bool:
    """Giáo viên chỉ chấm bài của lớp mình phụ trách."""
    from app.models import Class, Enrollment

    if submission.audio_path is None and submission.text_content is None:
        return False
    return db.execute(
        select(Enrollment).join(Class, Class.id == Enrollment.class_id).where(
            Enrollment.student_id == submission.student_id, Class.teacher_id == teacher.id)
    ).first() is not None


def reopen(db: OrmSession, submission: Submission, teacher: User, reason: str) -> tuple[bool, str | None]:
    """Mở lại bài đã chấm để sửa điểm. Bắt buộc có lý do và ghi vào audit log."""
    if submission.status != "graded":
        return False, "Chỉ mở lại được bài đã chấm."
    reason = (reason or "").strip()
    if len(reason) < 10:
        return False, "Cần ghi lý do mở lại (ít nhất 10 ký tự) để lưu vào nhật ký."

    old = submission.final_score
    submission.status = "awaiting_teacher"
    submission.graded_by = None
    submission.graded_at = None
    audit.log(db, teacher, "reopen", f"submission:{submission.id}",
              f"điểm cũ {old} · lý do: {reason}")
    from app.services import notify

    notify.push(db, submission.student_id, "Bài của bạn được mở lại để chấm lại",
                f"Lý do giáo viên ghi: {reason}")
    db.commit()
    return True, None


def rubric_of(db: OrmSession, submission_id: int) -> dict[str, float]:
    rows = db.execute(select(RubricScore).where(RubricScore.submission_id == submission_id)).scalars()
    return {r.criterion: r.score for r in rows}


def feedback_of(db: OrmSession, submission_id: int) -> str:
    row = db.execute(
        select(RubricScore).where(RubricScore.submission_id == submission_id).limit(1)
    ).scalar_one_or_none()
    return row.comment if row else ""
