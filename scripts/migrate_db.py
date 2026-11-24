"""scripts/migrate_db.py — tạo các bảng còn thiếu trong CSDL đang có.

Vì sao cần: `create_all` chỉ chạy khi seed/test. Một CSDL tạo từ bản cũ (17 bảng) sẽ thiếu bảng
mới (`audit_logs`) cho tới khi có bước này → API mới trả 500 "no such table".

Việc script làm: đọc toàn bộ model hiện tại, tạo những bảng CHƯA có. Không xoá, không sửa bảng cũ,
không đụng dữ liệu. Chạy lại nhiều lần vô hại.

Dùng:  .venv/bin/python scripts/migrate_db.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Script nằm trong scripts/ nên sys.path không có gốc repo (lỗi đã gặp với run_https.py)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import inspect  # noqa: E402

from app.db import Base, engine  # noqa: E402
import app.models  # noqa: E402,F401  — import để Base biết toàn bộ bảng

EXPECTED = 18  # số bảng trong thiết kế hiện tại


def add_missing_columns() -> list[str]:
    """Thêm cột mới vào bảng đã có. SQLite chỉ cho ADD COLUMN nên phải viết tay từng cột."""
    from sqlalchemy import text

    wanted = {
        "lessons": {
            "video_url": "VARCHAR(500)",
            "video_path": "VARCHAR(500)",
            "video_title": "VARCHAR(200)",
            "video_by": "INTEGER",
        },
    }
    added: list[str] = []
    existing = {t: {c["name"] for c in inspect(engine).get_columns(t)} for t in wanted}
    with engine.begin() as conn:
        for table, cols in wanted.items():
            for col, ddl in cols.items():
                if col in existing.get(table, set()):
                    continue
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))
                added.append(f"{table}.{col}")
    return added


def main() -> int:
    before = set(inspect(engine).get_table_names())
    Base.metadata.create_all(engine)
    after = set(inspect(engine).get_table_names())

    created = sorted(after - before)
    print(f"Bảng trước: {len(before)} · sau: {len(after)}")
    if created:
        print("Đã tạo: " + ", ".join(created))
    else:
        print("Không thiếu bảng nào.")

    # create_all KHÔNG thêm cột vào bảng đã tồn tại → phải ALTER TABLE thủ công.
    added = add_missing_columns()
    if added:
        print("Đã thêm cột: " + ", ".join(added))
    else:
        print("Không thiếu cột nào.")

    missing = {t.name for t in Base.metadata.sorted_tables} - after
    if missing:
        print("VẪN THIẾU: " + ", ".join(sorted(missing)))
        return 1
    if len(after) != EXPECTED:
        print(f"CẢNH BÁO: thiết kế có {EXPECTED} bảng, CSDL đang có {len(after)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
