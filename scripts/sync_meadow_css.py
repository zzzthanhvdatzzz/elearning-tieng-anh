"""scripts/sync_meadow_css.py — sinh bản CSS Meadowbell cho trang Jinja từ bản của Next.

Vì sao: theme tồn tại ở hai nơi (Next và template Jinja). Chép tay thì sớm muộn lệch nhau.
Nguồn duy nhất là frontend/app/meadow.css; script này đổi đường dẫn ảnh sang bản tĩnh của
FastAPI (/meadow/… → /static/img/meadow/…) rồi ghi ra app/static/css/meadow.css.

Dùng:  .venv/bin/python scripts/sync_meadow_css.py [--check]
       --check: chỉ so sánh, thoát mã 1 nếu lệch (dùng cho test).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "frontend" / "app" / "meadow.css"
DST = ROOT / "app" / "static" / "css" / "meadow.css"

HEADER = ("/* BẢN SINH TỰ ĐỘNG từ frontend/app/meadow.css — "
          "chạy scripts/sync_meadow_css.py, đừng sửa tay. */\n")


def render() -> str:
    css = SRC.read_text(encoding="utf-8")
    return HEADER + css.replace("/meadow/", "/static/img/meadow/")


def main() -> int:
    check_only = "--check" in sys.argv
    expected = render()
    current = DST.read_text(encoding="utf-8") if DST.exists() else ""
    if current == expected:
        print("CSS Jinja đã đồng bộ với bản Next.")
        return 0
    if check_only:
        print("LỆCH: app/static/css/meadow.css không khớp frontend/app/meadow.css")
        print("Chạy: .venv/bin/python scripts/sync_meadow_css.py")
        return 1
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(expected, encoding="utf-8")
    print(f"Đã ghi {DST.relative_to(ROOT)} ({len(expected)} ký tự).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
