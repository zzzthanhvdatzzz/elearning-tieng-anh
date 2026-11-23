# Triển khai hệ thống (hai tiến trình: FastAPI + Next.js)

## 1. Cách nhanh nhất — Docker Compose

```bash
docker compose up -d --build
docker compose exec api python -m app.seed
docker compose exec api python -m app.content_pack
```

| Dịch vụ | Cổng máy host | Ghi chú |
|---|---|---|
| `web` (Next.js) | 3000 | giao diện chính cho học sinh/giáo viên/phụ huynh/quản trị |
| `api` (FastAPI) | 8010 | API `/api/*`, giao diện HTML dự phòng, `/docs`, `/health` |

**Lưu ý bắt buộc:** `NEXT_PUBLIC_API_URL` được **nhúng vào bundle lúc build**, không đọc được lúc chạy.
Đổi địa chỉ API thì phải build lại ảnh `web` (`docker compose build web`), sửa biến môi trường
runtime không có tác dụng.

## 2. Chạy không dùng Docker (máy phát triển)

```bash
# cửa sổ 1
.venv/bin/python -m uvicorn app.main:app --port 8010
# cửa sổ 2
cd frontend && npm install && npm run dev     # http://localhost:3000
```

Cổng 8000 đang bị ứng dụng khác chiếm trên máy phát triển của nhóm, nên API dùng 8010.

## 3. Nginx đứng trước (bắt buộc HTTPS nếu dùng ghi âm)

```nginx
server {
    listen 443 ssl;
    server_name elearning.example.edu.vn;

    client_max_body_size 12m;            # audio bài nói ≤ 10 MB (NFR7)

    # Frontend Next.js
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API FastAPI — giữ nguyên tiền tố /api để khớp CORS và cookie path
    location /api/ {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Giao diện HTML dự phòng + tài liệu API
    location ~ ^/(auth|units|lessons|practice|writing|speaking|teacher|parent|admin|reports|audio|docs|health|static)/ {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Vì sao HTTPS là bắt buộc:** `MediaRecorder` chỉ chạy trong secure context. Trên `http://` — kể cả
khi điện thoại truy cập qua LAN — trình duyệt chặn micro (`navigator.mediaDevices === undefined`).
Đây là rủi ro R2; phương án dự phòng là tải file ghi âm lên, đã có sẵn trên giao diện.

Nếu đặt cả hai sau một domain, CORS không còn cần thiết (cùng origin) — khi đó có thể bỏ
`CORSMiddleware` trong `app/main.py`.

## 4. Biến môi trường

| Tên | Dùng ở | Ghi chú |
|---|---|---|
| `DATABASE_URL` | API | mặc định `sqlite:///data/app.db`; đổi sang PostgreSQL khi nhiều lớp |
| `NEXT_PUBLIC_API_URL` | Web | **nhúng lúc build**; mặc định `http://localhost:8010` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM` | API | chưa cấu hình thì báo cáo tuần chỉ ghi `data/out/weekly/*.eml` |
| `DISABLE_JOBS` | API | `1` để tắt job báo cáo tuần (dùng khi test) |

## 5. Sao lưu (RPO 24 giờ — NFR7)

```bash
# crontab -e
0 2 * * * cp /srv/elearning/data/app.db /srv/backup/app-$(date +\%F).db
0 3 * * 0 find /srv/backup -name 'app-*.db' -mtime +30 -delete
```

## 6. Checklist nghiệm thu (dán vào biên bản bàn giao)

```bash
curl -s https://<domain>/health                        # {"status":"ok","db":"ok"}
curl -s -o /dev/null -w '%{http_code}\n' https://<domain>/login        # 200
curl -s https://<domain>/api/units -o /dev/null -w '%{http_code}\n'    # 401 (chưa đăng nhập)
curl -s -X POST https://<domain>/api/auth/login -H 'Content-Type: application/json' \
     -H 'X-Requested-With: fetch' -d '{"email":"gv.an@truong.edu.vn","password":"matkhau123"}' \
     -o /dev/null -w '%{http_code}\n'                  # 200
```
