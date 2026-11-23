#!/usr/bin/env bash
# scripts/dev.sh — chạy cả backend và frontend ở chế độ TỰ NẠP LẠI khi sửa code.
#
# Vì sao có script này: chạy `npm run start` (bản production) thì mọi thay đổi CSS/code
# phải build lại mới thấy — đó là lý do "sửa rồi mà giao diện vẫn như cũ".
#
# Dùng:  bash scripts/dev.sh
# Dừng:  Ctrl-C (script tự tắt cả hai tiến trình)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Cho phép gọi từ bất kỳ thư mục con nào (vd frontend/): luôn chạy ở gốc repo.
if [ ! -f "$ROOT/app/main.py" ]; then
  echo "Không tìm thấy app/main.py ở $ROOT — hãy chạy trong thư mục repo elearning."
  exit 1
fi

API_PORT="${API_PORT:-8010}"
WEB_PORT="${WEB_PORT:-3000}"

# Dọn tiến trình cũ trên hai cổng để không phải nhớ "có phải đang chạy bản cũ không"
for port in "$API_PORT" "$WEB_PORT"; do
  pids="$(lsof -ti "tcp:$port" 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "Cổng $port đang bận — tắt tiến trình cũ: $pids"
    kill $pids 2>/dev/null || true
    sleep 1
  fi
done

PY=".venv/bin/python"
[ -x "$PY" ] || PY="python3"

cleanup() {
  echo
  echo "Đang tắt..."
  kill "${API_PID:-}" "${WEB_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "→ Backend  http://localhost:$API_PORT   (--reload: sửa Python là tự nạp lại)"
"$PY" -m uvicorn app.main:app --port "$API_PORT" --reload &
API_PID=$!

cd frontend
[ -d node_modules ] || { echo "→ Cài gói npm lần đầu..."; npm install; }
echo "→ Frontend http://localhost:$WEB_PORT  (dev: sửa CSS/TSX là thấy ngay)"
npm run dev -- -p "$WEB_PORT" &
WEB_PID=$!

wait
