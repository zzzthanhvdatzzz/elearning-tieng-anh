"""scripts/backup_db.py — sao lưu và khôi phục CSDL SQLite (an toàn khi đang chạy).

Dùng API `sqlite3.Connection.backup` (không phải copy tệp) nên bản sao luôn nhất quán kể cả
khi server đang ghi. Tệp sao lưu có đuôi .db và được đặt tên theo thời điểm.

Dùng:
  .venv/bin/python scripts/backup_db.py                 # sao lưu vào data/backups/
  .venv/bin/python scripts/backup_db.py --keep 14       # giữ 14 bản gần nhất
  .venv/bin/python scripts/backup_db.py --restore <file>  # khôi phục (tự sao lưu bản hiện tại trước)

Khôi phục xong phải khởi động lại server: kết nối đang mở vẫn trỏ vào tệp cũ.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "app.db"
BACKUP_DIR = ROOT / "data" / "backups"


def backup(db_path: Path = DB, out_dir: Path = BACKUP_DIR) -> Path:
    if not db_path.exists():
        raise FileNotFoundError(f"Không thấy CSDL: {db_path}")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = out_dir / f"app-{stamp}.db"

    src = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)          # bản sao nhất quán, không cần tắt server
        dst.execute("PRAGMA integrity_check")
        ok = dst.execute("PRAGMA integrity_check").fetchone()[0]
        if ok != "ok":
            raise RuntimeError(f"Bản sao hỏng: {ok}")
    finally:
        dst.close()
        src.close()
    return target


def prune(out_dir: Path = BACKUP_DIR, keep: int = 10) -> list[Path]:
    files = sorted(out_dir.glob("app-*.db"), reverse=True)
    removed = []
    for f in files[keep:]:
        f.unlink()
        removed.append(f)
    return removed


def restore(backup_file: Path, db_path: Path = DB) -> Path:
    """Khôi phục: sao lưu bản đang chạy trước, rồi ghi đè bằng bản trong tệp backup."""
    if not backup_file.exists():
        raise FileNotFoundError(f"Không thấy tệp sao lưu: {backup_file}")
    safety = backup(db_path) if db_path.exists() else None
    src = sqlite3.connect(backup_file)
    dst = sqlite3.connect(db_path)
    try:
        src.backup(dst)
        dst.execute("PRAGMA integrity_check")
    finally:
        dst.close()
        src.close()
    return safety  # type: ignore[return-value]


def main() -> int:
    ap = argparse.ArgumentParser(description="Sao lưu / khôi phục CSDL SQLite")
    ap.add_argument("--keep", type=int, default=10, help="số bản sao lưu giữ lại")
    ap.add_argument("--restore", metavar="FILE", help="khôi phục từ tệp sao lưu")
    args = ap.parse_args()

    if args.restore:
        safety = restore(Path(args.restore))
        print(f"Đã khôi phục từ {args.restore}")
        if safety:
            print(f"Bản hiện tại được sao lưu an toàn tại: {safety}")
        print("Hãy khởi động lại server để dùng CSDL vừa khôi phục.")
        return 0

    target = backup()
    removed = prune(keep=args.keep)
    size_kb = target.stat().st_size // 1024
    print(f"Đã sao lưu: {target.relative_to(ROOT)} ({size_kb} KB)")
    if removed:
        print(f"Dọn {len(removed)} bản cũ, giữ {args.keep} bản gần nhất.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
