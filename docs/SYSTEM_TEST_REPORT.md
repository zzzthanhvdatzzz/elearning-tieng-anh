# Báo cáo kiểm thử hệ thống (bản chạy thật — không điền tay)

| Mục | Giá trị |
|---|---|
| Ngày chạy | 24/11/2026 |
| Lệnh | `.venv/bin/python -m pytest -q` |
| Kết quả | **152 passed, 0 failed** (xem mục 5 để biết cách tái lập) |
| Thời gian | ~9 phút (máy i7-6820HQ, SQLite tạm cho mỗi test) |
| Môi trường | Python 3.11.16, SQLite, `DISABLE_JOBS=1` |
| Build giao diện | `npm run build` (Next 16.4.6) — thành công, 24 route |
| UAT tự động | `scripts/run_uat.py` — **39/39 PASS** (`docs/UAT_RESULT.md`) |
| Kiểm route + CSDL | `scripts/check_backend.py` — 114 route đủ, **19/19 bảng** |

## 1. Phân bố test theo nhóm chức năng

| File | Số test | Phủ yêu cầu |
|---|---|---|
| `test_auth.py` | 9 | F1 đăng ký/đăng nhập/phiên, CSRF, 8 giờ, thu hồi phiên |
| `test_scoring.py` | 18 | BR5, BR6, BR8, ngưỡng CEFR, rubric (đơn vị, không cần server) |
| `test_placement.py` | 7 | F3/UC-03: 25 câu, chấm, chờ chấm, BR4, phân quyền giáo viên |
| `test_learning.py` | 9 | F5/F6: lộ trình, chặn bài khối khác, cộng dồn giây, kẹp 100% |
| `test_practice.py` | 8 | F9: chấm ngay, không lộ đáp án, BR7 chặn lượt 4 ở server |
| `test_writing.py` | 8 | F8 + F12: nháp, đếm từ, rubric, bắt buộc nhận xét khi < 5,0 |
| `test_speaking.py` | 8 | F7: tải file, chặn 10 MB, chặn định dạng, quyền nghe audio |
| `test_speaking_grading.py` | 5 | F7 (nửa còn lại): hàng đợi bài nói, nghe audio, chấm, mở lại bài |
| `test_classes.py` | 9 | F10/F11: mã lớp 6 ký tự, BR2, giao bài, deadline quá khứ |
| `test_report.py` | 7 | F13/F14: báo cáo học sinh/lớp, CSV, phân quyền |
| `test_parent.py` | 7 | F3: liên kết, duyệt, BR3, huỷ liên kết, job tuần idempotent |
| `test_parent_api.py` | 2 | Hàng đợi duyệt phụ huynh trên API JSON (từng 500 do sai tên cột) |
| `test_admin.py` | 9 | F2/F15: tạo/khoá/mật khẩu, import Excel bỏ dòng lỗi |
| `test_api.py` | 5 | Lớp JSON cho Next.js: 401, CSRF header, không lộ đáp án |
| `test_notify.py` | 4 | Thông báo: giao bài, chấm bài, duyệt phụ huynh, cách ly người dùng |
| `test_grade_notify.py` | 2 | Chấm qua API → học sinh nhận thông báo + thấy điểm; chấm lại bị chặn |
| `test_assignment_flow.py` | 5 | Bài giao áp dụng thật (hạn + số lượt), BR8 nộp muộn |
| `test_account.py` | 5 | Tự đổi mật khẩu (huỷ phiên khác), phân trang tài khoản |
| `test_export_backup.py` | 5 | Xuất Excel bảng điểm, sao lưu/khôi phục CSDL, lọc hàng đợi |
| `test_smtp.py` | 3 | Gửi email thật (SMTP giả lập): gọi send_message, lỗi ghi `failed` |
| `test_video.py` | 8 | Video: link YouTube/Drive, tải file, phân quyền khối, xoá |
| `test_video_progress.py` | 7 | Chống tua (tối đa 20s/nhịp), hoàn thành khi ≥80%, cách ly |
| `test_video_report.py` | 4 | Video nối vào dashboard + báo cáo học sinh/phụ huynh |
| `test_theme_sync.py` | 4 | CSS Jinja khớp bản Next, không hotlink ảnh ngoài, ảnh tồn tại |
| **Tổng** | **152** | |

## 2. Kiểm chứng thủ công đã chạy (có log, không phải mô tả)

| Việc | Cách kiểm | Kết quả thật |
|---|---|---|
| HTTPS tự ký | `scripts/run_https.py` rồi `curl -k https://localhost:8443/health` | `{"status":"ok","db":"ok"}`, trang chủ 200, cert CN=`elearning.local` hạn 23/11/2027 |
| Job email tuần | `.venv/bin/python -m app.jobs.weekly_email` | `created 0, skipped 3` (idempotent), `smtp: False` — không giả vờ đã gửi |
| Sao lưu CSDL | `scripts/backup_db.py --keep 5` | `data/backups/app-20261124-145447.db` 392 KB |
| Chống tua video | POST heartbeat 10 → 95 giây | chỉ cộng 20 giây, `position 30`, chưa hoàn thành |
| Xem đủ 80% | heartbeat tuần tự tới 80/100 giây | `completed: true, percent 80` |
| Video nối báo cáo | dashboard + `/api/reports/student/{id}` | `1/1 video, 80 giây, 100%` |
| Cài lịch tự động | `bash scripts/install_cron.sh` | in 2 lịch (email thứ 2 07:00, sao lưu 02:30) |

## 3. Lỗi thật đã phát hiện và sửa trong quá trình kiểm thử

1. Fixture dùng chung cookie jar → phiên giáo viên đè học sinh (sửa `client_for`).
2. Route CSV `/{class_id}.csv` bị khớp `int` → 422; đổi sang `/{id}/export.csv`.
3. `POST /api/teacher/classes` 405 và `/api/auth/register-parent` 404 → thiếu endpoint.
4. Hàng đợi duyệt phụ huynh **500** vì dùng `link.created_at` (cột thật là `requested_at`).
5. `_weekly()` lấy mốc 00:00 hôm nay → hoạt động trong ngày bị loại khỏi tuần hiện tại.
6. Bài giao của giáo viên **không** áp dụng hạn/số lượt (học sinh làm trên assignment tự sinh).
7. Chấm thiếu tiêu chí tự điền **0** → bài bị trừ điểm âm thầm; nay trả 422 kèm tên tiêu chí.
8. Xuất Excel với tên lớp tiếng Việt → `UnicodeEncodeError` (header latin-1); sửa theo RFC 5987.
9. Bảng `audit_logs` thiếu trên CSDL cũ → trang Nhật ký 500 (`create_all` không thêm cột/bảng).
10. Trang chủ chỉ render "Đang tải…" trong HTML vì chặn render bằng state.

## 4. CHƯA kiểm thử được (nói rõ để không nhận là đã làm)

1. **Ghi âm bằng micro trên điện thoại thật** — chỉ mới test tải file lên.
2. **Tải 200 người dùng đồng thời (p95)** — chưa đo; SQLite + uvicorn không đại diện cho production.
3. **RTO/RPO** — sao lưu/khôi phục đã test thủ công, chưa đo thời gian khôi phục khi thảm hoạ.
4. **UAT với người thật** — 39 kịch bản chạy tự động, chưa có giáo viên/học sinh thật thao tác.
5. **Chất lượng sư phạm 240 câu hỏi** — cần giáo viên rà nghĩa.
6. **Chấm nói bằng AI** — chưa có, ghi là hướng phát triển.
7. **Phát video 200 MB cho cả lớp cùng lúc** — chưa đo; dự kiến nghẽn, nên dùng link ngoài.
8. **Cron trên máy chủ thật** — script cài đã có, chưa cài trên máy chủ production.

## 5. Cách tái lập

```bash
cd elearning-nhom05
.venv/bin/python -m pytest -q                      # 152 test
.venv/bin/python scripts/check_backend.py          # route + số bảng
bash scripts/dev.sh                                # chạy backend + frontend
.venv/bin/python scripts/run_uat.py                # 39 kịch bản UAT
bash scripts/install_cron.sh                       # cài lịch tự động
```
