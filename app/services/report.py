"""services/report.py — F13/F14: báo cáo học sinh và báo cáo lớp.

Quyết định ở Bảng 3.12: báo cáo TÍNH LẠI mỗi lần xem, không lưu bảng tổng hợp.
Đúng ở quy mô thử nghiệm, nhanh hơn việc phải đồng bộ job.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.models import (
    Assignment,
    Class,
    Enrollment,
    Lesson,
    Progress,
    RubricScore,
    Submission,
    User,
)

SKILL_LABELS = {
    "grammar": "Ngữ pháp", "reading": "Đọc hiểu", "listening": "Nghe",
    "vocab": "Từ vựng", "writing": "Viết", "speaking": "Nói", "mixed": "Tổng hợp",
}
PASS_MARK = 5.0


def _skill_rows(db: OrmSession, student_id: int) -> list[dict]:
    rows = db.execute(
        select(Submission, Assignment, Lesson)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .outerjoin(Lesson, Lesson.id == Assignment.lesson_id)
        .where(Submission.student_id == student_id, Submission.final_score.is_not(None))
    ).all()

    buckets: dict[str, list[float]] = {}
    for sub, assignment, lesson in rows:
        skill = "writing" if assignment.kind == "writing" else (lesson.skill if lesson else "mixed")
        buckets.setdefault(skill, []).append(sub.final_score)
    return [
        {"skill": s, "label": SKILL_LABELS.get(s, s),
         "avg": round(sum(v) / len(v), 1), "count": len(v),
         "weak": (sum(v) / len(v)) < PASS_MARK}
        for s, v in sorted(buckets.items())
    ]


def _minutes(db: OrmSession, student_id: int) -> int:
    rows = db.execute(select(Progress).where(Progress.student_id == student_id)).scalars()
    return round(sum(p.seconds for p in rows) / 60)


def _weekly(db: OrmSession, student_id: int, weeks: int = 6) -> list[dict]:
    """Số phút học theo tuần (dựa trên last_seen_at của progress)."""
    now = datetime.utcnow()
    out = []
    for i in range(weeks - 1, -1, -1):
        start = (now - timedelta(days=7 * (i + 1))).date()
        end = (now - timedelta(days=7 * i)).date()
        rows = db.execute(
            select(Progress).where(Progress.student_id == student_id,
                                   Progress.last_seen_at >= datetime.combine(start, datetime.min.time()),
                                   Progress.last_seen_at < datetime.combine(end, datetime.min.time()))
        ).scalars()
        out.append({"label": f"tuần {weeks - i}", "minutes": round(sum(p.seconds for p in rows) / 60)})
    return out


def _submissions(db: OrmSession, student_id: int, limit: int = 12) -> list[dict]:
    rows = db.execute(
        select(Submission, Assignment)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .where(Submission.student_id == student_id)
        .order_by(Submission.submitted_at.desc())
        .limit(limit)
    ).all()
    return [{"submission": s, "assignment": a} for s, a in rows]


def student_report(db: OrmSession, student: User) -> dict:
    skills = _skill_rows(db, student.id)
    weak = [s for s in skills if s["weak"]]
    return {
        "student": student,
        "skills": skills,
        "weakest": weak[0] if weak else None,
        "minutes": _minutes(db, student.id),
        "weekly": _weekly(db, student.id),
        "submissions": _submissions(db, student.id),
        "progress": db.execute(
            select(Progress).where(Progress.student_id == student.id,
                                   Progress.percent >= 100)
        ).scalars().all(),
    }


def class_report(db: OrmSession, klass: Class) -> dict:
    students = db.execute(
        select(User).join(Enrollment, Enrollment.student_id == User.id)
        .where(Enrollment.class_id == klass.id, Enrollment.status == "active")
    ).scalars().all()

    rows = []
    for s in students:
        subs = db.execute(
            select(Submission).join(Assignment, Assignment.id == Submission.assignment_id)
            .where(Assignment.class_id == klass.id, Submission.student_id == s.id,
                   Submission.final_score.is_not(None))
        ).scalars().all()
        scores = [x.final_score for x in subs]
        avg = round(sum(scores) / len(scores), 1) if scores else None
        rows.append({
            "student": s,
            "attempts": len(subs),
            "avg": avg,
            "minutes": _minutes(db, s.id),
            "needs_help": avg is not None and avg < PASS_MARK,
        })

    with_score = [r["avg"] for r in rows if r["avg"] is not None]
    return {
        "klass": klass,
        "rows": sorted(rows, key=lambda r: (r["avg"] is None, r["avg"] or 0)),
        "class_avg": round(sum(with_score) / len(with_score), 1) if with_score else None,
        "needs_help": [r for r in rows if r["needs_help"]],
        "students": len(rows),
    }


def class_csv(db: OrmSession, klass: Class) -> str:
    report = class_report(db, klass)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Học sinh", "Email", "CEFR", "Số bài đã nộp", "Điểm trung bình", "Phút học"])
    for r in report["rows"]:
        writer.writerow([
            r["student"].full_name or "", r["student"].email, r["student"].cefr_level or "",
            r["attempts"], r["avg"] if r["avg"] is not None else "", r["minutes"],
        ])
    return buf.getvalue()
