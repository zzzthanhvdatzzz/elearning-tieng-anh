# Triển khai (F3 — Docker + Nginx + Uvicorn)

## 1. Chạy bằng Docker (một lệnh)

```bash
docker build -t elearning-nhom05 .
docker run -d --name elearning -p 8000:8000 \
  -v "$PWD/data:/app/data" \
  -e DATABASE_URL="sqlite:////app/data/app.db" \
  elearning-nhom05
```

Nạp dữ liệu mẫu lần đầu (CSDL nằm trong volume):

```bash
docker exec -it elearning python -m app.seed
```

Kiểm tra: `curl http://127.0.0.1:8000/health` → `{"status":"ok","db":"ok"}`

## 2. Nginx đứng trước (bắt buộc HTTPS nếu dùng ghi âm)

`/etc/nginx/sites-available/elearning`:

```nginx
server {
    listen 80;
    server_name elearning.example.edu.vn;

    client_max_body_size 12m;          # audio bài nói ≤ 10 MB (NFR7)

    location /static/ {
        alias /app/app/static/;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Lấy chứng chỉ: `certbot --nginx -d elearning.example.edu.vn`.

**Vì sao HTTPS là bắt buộc:** `MediaRecorder` (ghi âm bài nói, F7) chỉ chạy trong secure
context. Trên `http://` — kể cả `http://localhost` trên điện thoại truy cập qua LAN —
trình duyệt chặn micro và trả `navigator.mediaDevices === undefined`. Đây là rủi ro R2
trong sổ rủi ro, đã có phương án dự phòng là tải file ghi âm lên.

## 3. Biến môi trường

| Tên | Bắt buộc | Ghi chú |
|---|---|---|
| `DATABASE_URL` | không | mặc định `sqlite:///data/app.db`; đổi sang PostgreSQL khi nhiều lớp |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS` / `SMTP_FROM` | không | chưa cấu hình thì báo cáo tuần chỉ ghi ra `data/out/weekly/*.eml` |
| `EMAIL_OUT_DIR` | không | đổi thư mục xuất email |
| `DISABLE_JOBS` | không | `1` để tắt thread báo cáo tuần (dùng khi test) |

## 4. Sao lưu (RPO 24 giờ, NFR7)

```bash
# crontab -e
0 2 * * * cp /srv/elearning/data/app.db /srv/backup/app-$(date +\%F).db
0 3 * * 0 find /srv/backup -name 'app-*.db' -mtime +30 -delete
```

## 5. Kiểm tra sau triển khai (dùng cho biên bản bàn giao)

```bash
curl -s https://<domain>/health
curl -s -o /dev/null -w '%{http_code}\n' https://<domain>/auth/login     # 200
curl -s -o /dev/null -w '%{http_code}\n' https://<domain>/admin/users   # 303 (chưa đăng nhập)
```
