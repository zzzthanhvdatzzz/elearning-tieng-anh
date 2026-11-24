# Kết quả chạy kịch bản UAT (tự động qua HTTP)

- Thời điểm: 24/11/2026 10:00
- Lệnh: `.venv/bin/python scripts/run_uat.py`
- Kết quả: **39/39 PASS**

| Mã | Kịch bản | Kết quả | Bằng chứng |
|---|---|---|---|
| NF-00 | API sống | PASS | GET /health → 200 |
| SEC-01 | API không cho truy cập khi chưa đăng nhập | PASS | 401 |
| SEC-02 | Thiếu header CSRF bị chặn | PASS | 403 |
| ST-02 | Đăng ký bằng mã lớp sai bị từ chối | PASS | 422 {"detail":"Mã lớp không đúng, hãy hỏi giáo viên"} |
| ST-01 | Đăng ký bằng mã lớp đúng | PASS | 200 role=student |
| ST-05 | Lộ trình hiện đúng khối lớp | PASS | 200 units=2 lessons=12 |
| ST-06a | Mở bài học có nội dung | PASS | 200 có từ vựng=True |
| ST-06b | Thời gian học cộng dồn, không mất | PASS | 30s → 50s |
| ST-07a | Đề luyện tập không lộ đáp án | PASS | 200 14 câu |
| ST-07b | Chấm và trả điểm ngay (< 2 giây) | PASS | 200 điểm=8.6 67 ms |
| ST-08 | Hết lượt (3 lượt) thì chặn ở server | PASS | các lần nộp: [409, 409, 409, 409] |
| GV-00 | Giáo viên đăng nhập | PASS | 200 |
| GV-01a | Danh sách lớp của giáo viên | PASS | 200 8 lớp |
| GV-01b | Tạo lớp sinh mã 6 ký tự | PASS | 200 mã=KYWTA9 |
| GV-02a | Xem danh sách học sinh của lớp | PASS | 200 18 học sinh |
| GV-02b | Thêm học sinh chưa vào lớp; thêm lần hai bị từ chối | PASS | lần 1=200 lần 2=422 |
| GV-03 | Học sinh đã ở lớp khác thì bị chặn (BR2) | PASS | 422 |
| GV-04 | Hạn nộp trong quá khứ bị từ chối | PASS | 422 |
| GV-05a | Hàng đợi chấm có bài | PASS | 200 1 bài |
| GV-06 | Điểm < 5,0 mà thiếu nhận xét thì không lưu | PASS | 422 |
| GV-05b | Chấm rubric và trả bài | PASS | 200 điểm cuối=8.0 |
| GV-07a | Giáo viên mở đúng lớp của mình | PASS | 200 |
| GV-08 | Báo cáo lớp có số liệu | PASS | 200 19 học sinh, TB lớp=8.3 |
| GV-08b | Xuất CSV mở được, có tiêu đề | PASS | 200 1111 bytes |
| PH-01a | Phụ huynh tự đăng ký | PASS | 200 |
| PH-01b | Gửi yêu cầu liên kết | PASS | 200 |
| PH-01c | Trạng thái chờ duyệt | PASS | ['pending'] |
| PH-02 | Chưa duyệt thì không xem được báo cáo (BR3) | PASS | 403 |
| PH-03a | Giáo viên duyệt liên kết | PASS | 200 |
| PH-03b | Sau khi duyệt xem được báo cáo | PASS | 200 phút học=1 |
| PH-04 | Huỷ liên kết thì mất quyền ngay | PASS | 403 |
| QT-00 | Quản trị đăng nhập | PASS | 200 |
| QT-01a | Danh sách tài khoản | PASS | 200 20 tài khoản |
| QT-01b | Tạo tài khoản giáo viên | PASS | 200 |
| QT-01c | Tạo trùng email bị từ chối | PASS | 422 |
| QT-02 | Khoá tài khoản thì không đăng nhập được | PASS | đăng nhập → 423 |
| QT-04 | Import Excel: nhận dòng đúng, báo dòng lỗi | PASS | 200 thêm=2 lỗi=1 |
| SEC-03 | Học sinh không vào được API giáo viên | PASS | 403 |
| SEC-04 | Học sinh lớp 8 không mở được bài lớp 10 | PASS | lesson_id=14 → 404 |

## Những gì script KHÔNG kiểm được (phải làm tay, ghi vào biên bản)

| Mã | Việc | Cách làm |
|---|---|---|
| ST-10 | Ghi âm bằng micro trên điện thoại | `scripts/run_https.py`, mở `https://<IP-LAN>:8443` |
| NF-01 | p95 ≤ 500 ms với 200 người | Locust trên staging, ghi p95 thật |
| NF-04 | Cài lại từ đầu ≤ 10 phút | máy sạch, chạy README, bấm giờ |
| UAT | 4 vai trò người thật dùng thử | `docs/UAT.md`, biên bản có chữ ký |

> Script chạy trên CSDL phát triển và có tạo dữ liệu mới (học sinh/phụ huynh UAT).
> Muốn CSDL sạch: `rm data/app.db` rồi `app.seed` → `app.content_pack` → `app.demo_data`.
