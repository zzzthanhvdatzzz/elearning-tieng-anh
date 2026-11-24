#!/usr/bin/env bash
# scripts/install_cron.sh — cài lịch chạy tự động cho job email tuần và sao lưu CSDL.
#
# Vì sao cần: code job đã chạy được nhưng chưa có ai hẹn giờ, nên trên máy thật
# chưa có email nào tự gửi và chưa có bản sao lưu tự động.
#
# Dùng:      bash scripts/install_cron.sh          (cài)
#            bash scripts/install_cron.sh --remove (gỡ)
#
# Ghi chú: cron KHÔNG chạy khi máy tắt/ngủ. Với laptop, nên dùng launchd (macOS) hoặc
# systemd timer (Linux) — script này in hướng dẫn ở cuối.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"
LOG_DIR="$ROOT/data/logs"
mkdir -p "$LOG_DIR"

TAG="# elearning-nhom05"
CRON_LINES="$TAG weekly-email
0 7 * * 1 cd $ROOT && $PY -m app.jobs.weekly_email >> $LOG_DIR/weekly-email.log 2>&1
$TAG backup-db
30 2 * * * cd $ROOT && $PY scripts/backup_db.py --keep 14 >> $LOG_DIR/backup.log 2>&1"

if [ "${1:-}" = "--remove" ]; then
  (crontab -l 2>/dev/null | grep -v "elearning-nhom05" || true) | crontab -
  echo "Đã gỡ lịch tự động của elearning-nhom05."
  exit 0
fi

# Cài idempotent: gỡ dòng cũ trước rồi thêm lại
EXISTING="$(crontab -l 2>/dev/null | grep -v "elearning-nhom05" || true)"
printf '%s\n%s\n' "$EXISTING" "$CRON_LINES" | sed '/^$/d' | crontab -

echo "Đã cài 2 lịch:"
echo "  • Thứ 2 hằng tuần 07:00 — gửi báo cáo tuần cho phụ huynh"
echo "  • Hằng ngày 02:30 — sao lưu CSDL, giữ 14 bản gần nhất"
echo "Log: $LOG_DIR/"
echo
echo "Kiểm tra lịch:  crontab -l | grep elearning"
echo
echo "LƯU Ý: cron không chạy khi máy tắt hoặc ngủ."
echo "  macOS (launchd):  xem docs/CAP_NHAT_KIEN_TRUC.md mục 'Chạy tự động'"
echo "  Linux (systemd): dùng timer thay cron nếu là máy chủ thật."
echo
if ! command -v crontab >/dev/null 2>&1; then
  echo "CẢNH BÁO: máy này không có crontab — hãy chạy trên máy chủ thật."
fi
