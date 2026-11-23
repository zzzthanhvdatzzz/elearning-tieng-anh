"""services/scoring.py — TOÀN BỘ công thức điểm nằm ở đây, không rải ở router/template.

Lý do (mục 2.4): BR5 và BR6 nhạy cảm vì ảnh hưởng điểm học sinh. Khi giảng viên đổi
trọng số 0,7/0,3 sang 0,6/0,4 thì chỉ sửa một chỗ và chạy lại bộ test của module này.

Service thuần: không biết HTTP, không đọc DB → test bằng dict.
"""
from __future__ import annotations

from datetime import datetime

# Ngưỡng xếp trình độ (mục 3.9)
CEFR_THRESHOLDS = ((8.0, "B2"), (6.0, "B1"), (4.0, "A2"), (0.0, "A1"))
CEFR_ORDER = ["A1", "A2", "B1", "B2"]


def auto_score(correct: int, total: int) -> float:
    """BR5: điểm tự động = 10 × số câu đúng / tổng số câu, làm tròn 1 chữ số thập phân."""
    if total <= 0:
        return 0.0
    return round(10 * correct / total, 1)


def grade_mcq(answers: dict[int, str], questions) -> tuple[int, list[dict]]:
    """Chấm từng câu. `questions` chỉ cần .id và .correct_key (dùng được cả dict giả).

    Trả (số_câu_đúng, chi tiết từng câu). Không có đáp án đúng nào được gửi từ client.
    """
    correct = 0
    detail: list[dict] = []
    for q in questions:
        chosen = (answers.get(q.id) or "").strip().upper()
        is_ok = chosen == q.correct_key.upper()
        correct += int(is_ok)
        detail.append({"question_id": q.id, "choice": chosen, "is_correct": is_ok})
    return correct, detail


def with_late_penalty(score: float, days_late: int) -> float:
    """BR8: trừ 10 % mỗi ngày, tối đa ba ngày; quá ba ngày nhận 0."""
    if days_late <= 0:
        return score
    if days_late > 3:
        return 0.0
    return round(score * (1 - 0.1 * days_late), 1)


def days_late(submitted_at: datetime | None, deadline: datetime | None) -> int:
    if not deadline or not submitted_at or submitted_at <= deadline:
        return 0
    delta = submitted_at - deadline
    days = delta.days
    if delta.seconds or delta.microseconds:
        days += 1  # trễ 1 giây vẫn tính là trễ 1 ngày
    return days


def final_score(
    auto: float | None, teacher: float | None, weight_auto: float = 0.7, weight_teacher: float = 0.3
) -> float | None:
    """BR6: điểm cuối = 0,7 × tự động + 0,3 × giáo viên.

    Trả None khi thiếu một trong hai phần — KHÔNG trả điểm cuối (mục 3.10).
    """
    if auto is None or teacher is None:
        return None
    return round(weight_auto * auto + weight_teacher * teacher, 1)


def cefr_from_score(score: float) -> str:
    """0–3,9 A1 · 4,0–5,9 A2 · 6,0–7,9 B1 · 8,0–10 B2."""
    for lower, level in CEFR_THRESHOLDS:
        if score >= lower:
            return level
    return "A1"


def placement_total(mcq: float, writing: float | None) -> float | None:
    """Điểm xếp trình độ = 0,7 × trắc nghiệm + 0,3 × bài viết (mục 3.9).

    Chưa chấm bài viết → None, trạng thái "chờ chấm" (luồng thay thế 3a).
    """
    if writing is None:
        return None
    return round(0.7 * mcq + 0.3 * writing, 1)


def adjust_level(level: str, delta: int) -> str:
    """Giáo viên điều chỉnh ±1 bậc, không vượt khung A1–B2."""
    if level not in CEFR_ORDER:
        return level
    idx = CEFR_ORDER.index(level)
    return CEFR_ORDER[max(0, min(len(CEFR_ORDER) - 1, idx + delta))]


def rubric_total(scores: list[float]) -> float:
    """Rubric 4 tiêu chí, mỗi tiêu chí 0–2,5 → tổng thang 10."""
    total = sum(scores)
    return round(min(10.0, max(0.0, total)), 1)
