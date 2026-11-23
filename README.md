# Hệ thống học tiếng Anh trực tuyến — Nhóm 05

Bản dựng theo báo cáo `Bao_cao_Nhom05.docx` (bước 1–4 đã xong, repo này là bước 5 trở đi).

## Chạy trong 4 lệnh

```bash
cd ~/Documents/elearning-nhom05
uv venv .venv                        # chỉ lần đầu
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Mở http://127.0.0.1:8010 — kiểm tra http://127.0.0.1:8010/health trả `{"status":"ok","db":"ok"}`.
(Cổng 8000 đang bị app VDL Timesheet chiếm trên máy này, nên dùng 8010.)
Tài liệu API tự sinh: http://127.0.0.1:8010/docs

Chạy test: `.venv/bin/python -m pytest -q` (75 test, ~3,5 phút vì mỗi test dựng lại CSDL)

Nạp dữ liệu mẫu: `.venv/bin/python -m app.seed`
→ giáo viên `gv.an@truong.edu.vn` / `matkhau123`, mã lớp `8A1X21`, 25 câu kiểm tra đầu vào.

Nạp nội dung 4 Unit / 24 bài / 240 câu: `.venv/bin/python -m app.content_pack`
(ngân hàng từ vựng + ngữ pháp sinh tự động — nhóm Nội dung phải rà lại nghĩa trước khi dùng thật).

Chạy cả hệ thống bằng Docker: `docker compose up -d --build` — xem `deploy.md`.
Kịch bản kiểm thử và biên bản UAT: `docs/UAT.md`. Biểu mẫu câu hỏi: `data/templates/mau_cau_hoi.xlsx`.

## Vai trò và đường dẫn chính

| Vai trò | Trang | Chức năng |
|---|---|---|
| Khách | `/auth/register`, `/auth/register-parent` | học sinh tự đăng ký bằng mã lớp; phụ huynh tự đăng ký |
| Học sinh | `/placement`, `/units`, `/assignments`, `/practice/{lesson}`, `/writing/{lesson}`, `/reports/student/{id}` | kiểm tra đầu vào → lộ trình → học bài → luyện tập/viết → xem điểm |
| Giáo viên | `/teacher/classes`, `/teacher/placement`, `/teacher/writing`, `/teacher/parents`, `/reports/class/{id}` | tạo lớp, giao bài, chấm placement và bài viết, duyệt phụ huynh, báo cáo lớp + CSV |
| Phụ huynh | `/parent` | gửi yêu cầu liên kết, xem báo cáo của con sau khi giáo viên duyệt |
| Quản trị | `/admin/users`, `/admin/import` | tạo/khoá tài khoản, đặt lại mật khẩu, import câu hỏi từ Excel |

## Frontend Next.js (nhánh chuyển đổi, đang làm)

Giao diện cũ bằng Jinja2 vẫn chạy đủ 15 màn hình ở cổng 8010. Bản Next.js nằm trong `frontend/`
và gọi FastAPI qua lớp JSON `/api/*`.

```bash
# cửa sổ 1 — backend
.venv/bin/python -m uvicorn app.main:app --port 8010

# cửa sổ 2 — frontend
cd frontend
npm install            # lần đầu
npm run dev            # http://localhost:3000
```

Đã chuyển: `/` (điều hướng theo vai trò), `/login`, `/units`, `/lesson/[id]`.
Còn lại: register, assignments, practice, writing, speaking, giáo viên (5 màn), phụ huynh, quản trị (2 màn).

Ba điểm kỹ thuật bắt buộc khi nối Next.js với FastAPI:
- `credentials: "include"` trong mọi `fetch` — không có thì cookie phiên không đi kèm.
- Header `X-Requested-With: fetch` — FastAPI dùng làm hàng rào CSRF cho `/api/*` (header tuỳ biến buộc preflight, form HTML không tự gắn được).
- CORS chỉ mở `http://localhost:3000` với `allow_credentials=True` (`app/main.py`).

## Cấu trúc (đúng kiến trúc 4 lớp ở mục 3.1)

```
app/
  main.py            # khởi tạo FastAPI, mount static, gắn router
  db.py              # engine + session + Base (một chỗ duy nhất)
  models/            # 16 bảng ở Bảng 3.8 (SQLAlchemy)
  routers/           # 7 router: auth, placement, learning, practice, grading, report, admin
  services/          # 6 service thuần: scoring, placement, progress, report, storage, notify
  templates/         # Jinja2 + Bootstrap 5
  static/            # css, js (recorder.js), audio mẫu
  jobs/              # weekly_email.py — báo cáo tuần cho phụ huynh
tests/               # pytest, mỗi AC một test
data/                # app.db, uploads/ (không commit)
```

Ranh giới bắt buộc: **router không chứa nghiệp vụ**, service không biết HTTP.
Nhờ vậy `services/scoring.py` test được bằng dict, không cần dựng server (mục 3.1).

## Biến môi trường

| Tên | Mặc định | Ghi chú |
|---|---|---|
| `DATABASE_URL` | `sqlite:///data/app.db` | đổi sang `postgresql+psycopg://...` khi lên staging |
| `SECRET_KEY` | (chưa dùng) | sẽ dùng cho session cookie ở C2 |
