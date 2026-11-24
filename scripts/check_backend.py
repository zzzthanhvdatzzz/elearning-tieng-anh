"""scripts/check_backend.py — kiểm tra backend đang chạy có đủ route cho giao diện Next không.

Vì sao cần: một tiến trình uvicorn khởi động TRƯỚC khi code mới được pull sẽ phục vụ route cũ,
giao diện báo "Not Found" dù code trong repo đã đúng. Script này chỉ thẳng vào chỗ đó.

Chạy:  .venv/bin/python scripts/check_backend.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("API_URL", "http://localhost:8010")

# Mỗi route giao diện Next thực sự gọi. Thiếu một cái là một màn hình hỏng.
REQUIRED = [
    ("GET", "/api/me"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/register"),
    ("POST", "/api/auth/register-parent"),
    ("POST", "/api/auth/password"),
    ("GET", "/api/dashboard"),
    ("GET", "/api/notifications"),
    ("POST", "/api/notifications/read"),
    ("GET", "/api/units"),
    ("GET", "/api/lessons/{lesson_id}"),
    ("GET", "/api/practice/{lesson_id}"),
    ("POST", "/api/practice/{lesson_id}/submit"),
    ("GET", "/api/writing/{lesson_id}"),
    ("POST", "/api/writing/{lesson_id}/submit"),
    ("GET", "/api/assignments"),
    ("GET", "/api/reports/student/{student_id}"),
    ("GET", "/api/parent/children"),
    ("POST", "/api/parent/link"),
    ("GET", "/api/parent/report/{student_id}"),
    ("GET", "/api/teacher/classes"),
    ("POST", "/api/teacher/classes"),
    ("GET", "/api/teacher/classes/{class_id}/report"),
    ("GET", "/api/teacher/parent-requests"),
    ("POST", "/api/teacher/parent-requests/{link_id}"),
    ("GET", "/api/teacher/submissions"),
    ("GET", "/api/submissions/{submission_id}/audio"),
    ("GET", "/api/teacher/speaking"),
    ("POST", "/api/teacher/speaking/{submission_id}/grade"),
    ("POST", "/api/teacher/submissions/{submission_id}/reopen"),
    ("GET", "/api/teacher/classes/{class_id}/report.xlsx"),
    ("GET", "/api/admin/audit"),
    ("GET", "/api/lessons/{lesson_id}/video"),
    ("POST", "/api/teacher/lessons/{lesson_id}/video"),
    ("POST", "/api/teacher/lessons/{lesson_id}/video/upload"),
    ("DELETE", "/api/teacher/lessons/{lesson_id}/video"),
    ("GET", "/api/admin/users"),
    ("POST", "/api/admin/users"),
    ("POST", "/api/admin/import-upload"),
]


REQUIRED_TABLES = 18  # thiết kế hiện tại; thiếu bảng mới → API mới trả 500 "no such table"


def check_tables() -> list[str]:
    """So số bảng trong CSDL SQLite với thiết kế. Bắt lỗi 'quên migrate' — đã lọt qua một lần."""
    import sqlite3
    from pathlib import Path

    db = Path(__file__).resolve().parent.parent / "data" / "app.db"
    if not db.exists():
        return []
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        names = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    finally:
        con.close()
    problems = []
    if len(names) < REQUIRED_TABLES:
        problems.append(f"CSDL chỉ có {len(names)}/{REQUIRED_TABLES} bảng — chạy: "
                        f".venv/bin/python scripts/migrate_db.py")
    if "audit_logs" not in names:
        problems.append("thiếu bảng audit_logs (trang Nhật ký sẽ 500)")
    return problems


def main() -> int:
    try:
        with urllib.request.urlopen(f"{BASE}/openapi.json", timeout=8) as r:
            spec = json.load(r)
    except (urllib.error.URLError, OSError) as exc:
        print(f"KHÔNG kết nối được {BASE} — backend chưa chạy? ({exc})")
        return 2

    have = {(m.upper(), path) for path, ops in spec.get("paths", {}).items() for m in ops}
    missing = [f"{m} {p}" for m, p in REQUIRED if (m, p) not in have]
    table_problems = check_tables()

    print(f"Backend: {BASE}")
    print(f"Tổng route: {len(have)}")
    if table_problems:
        print("VẤN ĐỀ CSDL:")
        for p in table_problems:
            print(f"  • {p}")
    if not missing:
        print("ĐỦ route cho giao diện Next — không thiếu gì.")
        return 1 if table_problems else 0

    print(f"THIẾU {len(missing)} route:")
    for item in missing:
        print(f"  • {item}")
    print("\nCách sửa: dừng tiến trình cũ rồi khởi động lại (tiến trình cũ vẫn giữ code trước khi pull):")
    print("  pkill -f 'uvicorn app.main:app'")
    print(f"  .venv/bin/python -m uvicorn app.main:app --port {BASE.rsplit(':', 1)[-1]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
