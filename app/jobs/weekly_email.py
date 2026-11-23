"""jobs/weekly_email.py — báo cáo tuần cho phụ huynh (F14, SC4).

Chạy trong CÙNG tiến trình bằng thread nền (quyết định ở mục 3.1). Hai nguyên tắc:
1. Idempotent: mỗi (phụ huynh, tuần ISO) chỉ tạo MỘT tệp `.eml` — chạy lại không nhân đôi.
2. Catch-up: máy tắt lúc 7h thứ Hai thì lần chạy sau vẫn gửi, vì điều kiện là "tuần này
   chưa có tệp", không phải "đúng 7h".

Chưa cấu hình SMTP thì thư được ghi ra `data/out/weekly/*.eml` (mở được bằng Outlook).
Nói rõ: khi chưa có SMTP_HOST thì KHÔNG có email nào thực sự được gửi đi.
"""
from __future__ import annotations

import os
import smtplib
import threading
import time
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Notification, ParentLink, User
from app.services import report as report_svc

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUT_DIR = Path(os.getenv("EMAIL_OUT_DIR", BASE_DIR / "data" / "out" / "weekly"))
CHECK_EVERY_SECONDS = 600  # 10 phút


def _iso_week(now: datetime) -> str:
    year, week, _ = now.isocalendar()
    return f"{year}-W{week:02d}"


def build_body(parent: User, student: User) -> tuple[str, str]:
    """Trả (subject, body) — báo cáo đọc trong dưới một phút (mục 1.2)."""
    db = SessionLocal()
    try:
        report = report_svc.student_report(db, student)
    finally:
        db.close()

    weak = report["weakest"]["label"] if report["weakest"] else "chưa đủ dữ liệu"
    lines = [
        f"Chào {parent.full_name or parent.email},",
        "",
        f"Báo cáo tuần này của {student.full_name or student.email}:",
        f"- Thời gian học: {report['minutes']} phút",
        f"- Số bài đã nộp: {len(report['submissions'])}",
        f"- Trình độ hiện tại: {student.cefr_level or 'chưa xếp'}",
        f"- Kỹ năng cần chú ý: {weak}",
        "",
    ]
    if report["skills"]:
        lines.append("Điểm theo kỹ năng:")
        for s in report["skills"]:
            lines.append(f"  · {s['label']}: {s['avg']}/10 ({s['count']} bài)")
    else:
        lines.append("Tuần này con chưa có bài nào được chấm.")
    lines += ["", "Trân trọng,", "Hệ thống học tiếng Anh trực tuyến — Nhóm 05"]

    subject = f"[Học tiếng Anh] Báo cáo tuần {_iso_week(datetime.utcnow())} — {student.full_name or student.email}"
    return subject, "\n".join(lines)


def run_weekly(now: datetime | None = None, send: bool = True) -> dict:
    """Sinh báo cáo cho mọi liên kết đã duyệt. Trả thống kê để test/kiểm tra."""
    now = now or datetime.utcnow()
    week = _iso_week(now)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    created, skipped, failed = 0, 0, []
    db = SessionLocal()
    try:
        links = list(
            db.execute(select(ParentLink).where(ParentLink.status == "approved")).scalars()
        )
        for link in links:
            parent = db.get(User, link.parent_id)
            student = db.get(User, link.student_id)
            if parent is None or student is None:
                continue

            target = OUT_DIR / f"{week}-parent{parent.id}-student{student.id}.eml"
            if target.exists():          # idempotent theo (tuần, phụ huynh, học sinh)
                skipped += 1
                continue

            subject, body = build_body(parent, student)
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = os.getenv("SMTP_FROM", "no-reply@elearning.local")
            msg["To"] = parent.email
            msg.set_content(body)
            target.write_bytes(bytes(msg))

            # Thông báo trong ứng dụng (bảng notifications) — idempotent theo tiêu đề
            exists = db.execute(
                select(Notification.id).where(Notification.user_id == parent.id,
                                              Notification.title == subject)
            ).first()
            if exists is None:
                db.add(Notification(user_id=parent.id, title=subject, body=body[:1000]))
            db.commit()

            if send and os.getenv("SMTP_HOST"):
                try:
                    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587")),
                                      timeout=10) as s:
                        s.starttls()
                        if os.getenv("SMTP_USER"):
                            s.login(os.environ["SMTP_USER"], os.getenv("SMTP_PASS", ""))
                        s.send_message(msg)
                except Exception as exc:  # noqa: BLE001
                    failed.append({"parent": parent.email, "error": str(exc)})
            created += 1
    finally:
        db.close()

    return {"week": week, "created": created, "skipped": skipped, "failed": failed,
            "out_dir": str(OUT_DIR), "smtp": bool(os.getenv("SMTP_HOST"))}


def _loop() -> None:
    while True:
        try:
            run_weekly()
        except Exception:  # noqa: BLE001
            pass  # thread nền không được chết vì một lỗi lẻ
        time.sleep(CHECK_EVERY_SECONDS)


def start() -> threading.Thread:
    t = threading.Thread(target=_loop, daemon=True, name="weekly-email")
    t.start()
    return t


if __name__ == "__main__":
    print(run_weekly())
