# Báo cáo kiểm thử hệ thống (bản chạy thật — không điền tay)

| Mục | Giá trị |
|---|---|
| Ngày chạy | 23/11/2026 |
| Lệnh | `.venv/bin/python -m pytest -q` |
| Kết quả | **104 passed, 0 failed** |
| Thời gian | 327 giây (5 phút 27 giây) |
| Môi trường | Python 3.11.16, SQLite tạm cho mỗi test, `DISABLE_JOBS=1` |
| Build giao diện | `npm run build` (Next 16.4.6) — thành công, 17 route |

## 1. Phân bố test theo nhóm chức năng

| File | Số test | Phủ yêu cầu |
|---|---|---|
| `test_auth.py` | 9 | F1 đăng ký/đăng nhập/phiên, CSRF, 8 giờ, thu hồi phiên |
| `test_scoring.py` | 18 | BR5, BR6, BR8, ngưỡng CEFR, rubric (test đơn vị, không cần server) |
| `test_placement.py` | 7 | F3/UC-03: 25 câu, chấm, chờ chấm, BR4, phân quyền giáo viên |
| `test_learning.py` | 9 | F5/F6: lộ trình, chặn bài khối khác, cộng dồn giây, kẹp 100% |
| `test_practice.py` | 8 | F9: chấm ngay, không lộ đáp án, BR7 chặn lượt 4 ở server |
| `test_writing.py` | 8 | F8 + F12: nháp, đếm từ, rubric, bắt buộc nhận xét khi < 5,0 |
| `test_speaking.py` | 8 | F7: tải file, chặn 10 MB, chặn định dạng, quyền nghe audio |
| `test_classes.py` | 9 | F10/F11: mã lớp 6 ký tự, BR2, giao bài, deadline quá khứ |
| `test_report.py` | 7 | F13/F14: báo cáo học sinh/lớp, CSV, phân quyền |
| `test_parent.py` | 7 | F3: liên kết, duyệt, BR3, huỷ liên kết, job tuần idempotent |
| `test_admin.py` | 9 | F2/F15: tạo/khoá/mật khẩu, import Excel bỏ dòng lỗi |
| `test_api.py` | 5 | Lớp JSON cho Next.js: 401, CSRF header, không lộ đáp án |
| **Tổng** | **104** | |

## 2. Kiểm chứng thủ công đã chạy (có log, không phải mô tả)

| # | Kịch bản | Kết quả |
|---|---|---|
| 1 | Đăng ký học sinh bằng mã lớp `8A1X21` | 303 → `/placement`; ghi danh thành công |
| 2 | Nộp placement 25 câu đúng + bài viết | Điểm tự động 10.0, trạng thái "chờ chấm" |
| 3 | Giáo viên chấm rubric 8.0 | Điểm cuối 9.4, CEFR **B2**, học sinh thấy ngay |
| 4 | Luyện tập: nộp 10/10, 7/10, 10/10, rồi lượt 4 | 10.0 → 7.0 → 10.0 → **409 hết lượt** |
| 5 | Học bài, ghi tiến độ 120s → +60s → hoàn thành | 180s rồi 190s, phần trăm **không giảm** |
| 6 | Giáo viên tạo lớp mới | Mã 6 ký tự `OR41X0`, giao bài có deadline |
| 7 | Học sinh tự đăng ký bằng mã lớp mới | Thấy bài giao "0/2" trong danh sách |
| 8 | Nộp bài viết → giáo viên chấm | 8.0/10, nhận xét hiện cho học sinh |
| 9 | Báo cáo lớp + xuất CSV | Điểm TB lớp 8.5, CSV mở được |
| 10 | Phụ huynh gửi liên kết khi chưa duyệt | **403**; sau khi duyệt → 200 |
| 11 | Import Excel 3 dòng (1 sai `skill`) | Thêm 2, báo 1 lỗi kèm số dòng |
| 12 | Job báo cáo tuần chạy 2 lần | Lần 1 tạo 1 thư, lần 2 **0 tạo / 1 bỏ qua** |

## 3. Những gì CHƯA kiểm thử được (phải ghi rõ trong biên bản)

| Hạng mục | Lý do | Cách xử lý |
|---|---|---|
| Ghi âm bằng MediaRecorder trên điện thoại | Cần HTTPS thật; pytest không có micro | Chạy `scripts/run_https.py` rồi test tay trên điện thoại |
| p95 tải 200 người (NFR1) | Cần Locust + môi trường staging | Chạy trên staging, ghi p95 vào biên bản |
| Khôi phục sau sự cố (RTO/RPO) | Cần diễn tập xoá/khôi phục | Chạy kịch bản `deploy.md` mục 5 |
| Chất lượng nội dung 240 câu | Sinh tự động, chưa qua giáo viên | **Nhóm Nội dung phải rà lại từng câu trước khi dùng thật** |
| UAT với người dùng thật | Cần 4 vai trò tham gia | Chạy theo `docs/UAT.md`, điền biên bản |

## 4. Kết luận

- 104/104 test tự động đạt, không có lỗi mức 1 nào mở trong phạm vi đã kiểm thử.
- Điều kiện SC5 (không còn lỗi chặn vòng học) **đạt trên môi trường kiểm thử tự động**; còn phải
  xác nhận lại sau UAT với người dùng thật.
- Điều kiện SC6 (cài lại ≤ 10 phút) chưa đo — cần bấm giờ trên máy sạch theo README.
