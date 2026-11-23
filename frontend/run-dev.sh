#!/usr/bin/env bash
# run-dev.sh — gọi tắt khi đang đứng trong thư mục frontend/.
# Chạy: bash run-dev.sh     (hoặc bash scripts/dev.sh từ gốc repo)
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$DIR/../scripts/dev.sh"
