"""check_state.py — chẩn đoán: đang chạy bản code nào, CSDL nào, có dữ liệu chưa.

Chạy được bằng python hệ thống (chỉ dùng thư viện chuẩn):

    python3 scripts/check_state.py
"""
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "app.db"


def main() -> None:
    print("=" * 60)
    print("1. THƯ MỤC ĐANG CHẠY")
    print("   repo :", ROOT)
    print("   python:", sys.executable)

    try:
        sha = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%h %s"],
                             capture_output=True, text=True).stdout.strip()
        branch = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--abbrev-ref", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
        print("   nhánh:", branch)
        print("   commit:", sha or "(chưa có commit)")
    except FileNotFoundError:
        print("   ! không tìm thấy git")

    print("\n2. FILE CỦA BẢN MỚI CÓ KHÔNG")
    for rel in ["app/demo_data.py", "app/content_pack.py", "app/routers/api_teacher.py",
                "frontend/app/teacher/classes/page.tsx", "frontend/package.json"]:
        print(f"   {'OK ' if (ROOT / rel).exists() else 'THIẾU'}  {rel}")

    print("\n3. CƠ SỞ DỮ LIỆU")
    print("   đường dẫn:", DB, "| tồn tại:", DB.exists())
    if not DB.exists():
        print("   → chưa có CSDL: chạy `.venv/bin/python -m app.seed` trước")
        return

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    one = lambda sql, *a: con.execute(sql, a).fetchone()[0]

    print("   dung lượng:", f"{DB.stat().st_size / 1024:.0f} KB")
    print("   người dùng:", one("SELECT COUNT(*) FROM users"),
          "| học sinh:", one("SELECT COUNT(*) FROM users WHERE role='student'"))
    print("   lớp:", one("SELECT COUNT(*) FROM classes"),
          "| ghi danh:", one("SELECT COUNT(*) FROM enrollments"),
          "| bài nộp:", one("SELECT COUNT(*) FROM submissions"),
          "| câu hỏi:", one("SELECT COUNT(*) FROM questions"))
    print("   chờ chấm:", one("SELECT COUNT(*) FROM submissions WHERE status='awaiting_teacher'"))

    print("\n   Chi tiết lớp:")
    for r in con.execute("""SELECT c.name, c.join_code, COUNT(e.id) n FROM classes c
                            LEFT JOIN enrollments e ON e.class_id=c.id AND e.status='active'
                            GROUP BY c.id ORDER BY c.id"""):
        print(f"     - {r['name']:<26} mã {r['join_code']:<8} {r['n']} học sinh")

    print("\n4. TIẾN TRÌNH ĐANG NGHE CỔNG")
    try:
        out = subprocess.run(["bash", "-lc", "ss -ltnp 2>/dev/null | grep -E ':(8010|3000)'"],
                             capture_output=True, text=True).stdout.strip()
        print("  ", out or "không thấy tiến trình nào trên 8010/3000")
    except Exception:
        print("   (bỏ qua)")

    print("\n5. KẾT LUẬN GỢI Ý")
    if not (ROOT / "app/demo_data.py").exists():
        print("   → BẢN CODE CŨ. Hãy cd vào đúng thư mục vừa `git pull`")
        print("     (kiểm tra: có thư mục khác cũng tên elearning-* trên máy không)")
    elif one("SELECT COUNT(*) FROM enrollments") < 5:
        print("   → Chưa nạp dữ liệu demo: chạy `.venv/bin/python -m app.demo_data`")
    elif one("SELECT COUNT(*) FROM submissions WHERE status='awaiting_teacher'") == 0:
        print("   → Dữ liệu có nhưng hàng đợi chấm trống; chạy lại demo_data (idempotent)")
    else:
        print("   → CSDL đã có dữ liệu. Nếu giao diện vẫn trống thì:")
        print("     (a) backend đang chạy với DATABASE_URL khác — kiểm tra biến môi trường")
        print("     (b) trình duyệt cache — Ctrl+Shift+R")
        print("     (c) đang đăng nhập bằng tài khoản khác chủ lớp")
    print("=" * 60)


if __name__ == "__main__":
    main()
