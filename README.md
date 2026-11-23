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
