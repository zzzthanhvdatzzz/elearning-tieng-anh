# Kịch bản kiểm thử hệ thống và biên bản UAT (khung cho Quang Anh)

Tài liệu này là **khung** để nhóm Kiểm thử điền kết quả thật. Không điền "Đạt" khi chưa chạy.

## 1. Phạm vi và môi trường

| Mục | Giá trị |
|---|---|
| Bản kiểm thử | commit `_______` |
| Môi trường | staging / local; `DATABASE_URL`, cổng API, cổng web |
| Trình duyệt | Chrome ___ , Firefox ___ , Chrome Android ___ |
| Người chạy | ___ |
| Ngày | ___ |

## 2. Kiểm thử tự động (đã có sẵn, chạy trước khi test tay)

```bash
.venv/bin/python -m pytest -q          # 96 test backend + API
cd frontend && npm run build           # kiểm tra build giao diện
```

Ghi lại: số test pass, thời gian chạy, commit hash. Nếu có test đỏ thì **dừng**, không test tay tiếp.

## 3. Kịch bản theo vai trò

### A. Học sinh
| Mã | Kịch bản | Kết quả mong đợi |
|---|---|---|
| ST-01 | Đăng ký bằng mã lớp đúng | Vào thẳng `/placement`, tài khoản được ghi danh |
| ST-02 | Đăng ký bằng mã lớp sai | Báo lỗi rõ, **không** tạo tài khoản |
| ST-03 | Làm bài kiểm tra đầu vào 25 câu + bài viết | Điểm trắc nghiệm hiện ngay, trạng thái "chờ chấm" |
| ST-04 | Làm lại bài kiểm tra lần hai | Bị từ chối (BR4) |
| ST-05 | Mở lộ trình | Thấy Unit đúng khối lớp, bài đã học có dấu ✓ |
| ST-06 | Học bài, chờ 1 phút, tải lại trang | Tiến độ và số giây học được cộng dồn, không mất |
| ST-07 | Luyện tập 10 câu, nộp bài | Điểm hiện ≤ 2 giây, có đáp án + giải thích từng câu |
| ST-08 | Nộp lượt thứ 4 (bài cho 3 lượt) | Bị chặn, thông báo hết lượt |
| ST-09 | Nộp bài viết, sau đó sửa | Không sửa được sau khi nộp |
| ST-10 | Ghi âm bài nói trên điện thoại (HTTPS) | Nghe lại được, nộp thành công, file ≤ 10 MB |
| ST-11 | Tải file ghi âm lên (không có micro) | Nộp thành công — phương án dự phòng R2 |

### B. Giáo viên
| Mã | Kịch bản | Kết quả mong đợi |
|---|---|---|
| GV-01 | Tạo lớp | Sinh mã 6 ký tự, không trùng |
| GV-02 | Thêm học sinh bằng email | Học sinh vào lớp; thêm lần hai báo trùng |
| GV-03 | Thêm học sinh đang ở lớp khác | Bị chặn (BR2) |
| GV-04 | Giao bài với hạn trong quá khứ | Bị từ chối (422) |
| GV-05 | Chấm bài viết 4 tiêu chí | Điểm cuối = tổng rubric (bài viết) |
| GV-06 | Chấm điểm dưới 5,0 mà bỏ trống nhận xét | Không lưu được (AC12.2) |
| GV-07 | Mở bài của lớp khác (đổi id trên URL) | 403/404, không lộ dữ liệu |
| GV-08 | Xem báo cáo lớp, xuất CSV | Danh sách "cần can thiệp" đúng, CSV mở được bằng Excel |

### C. Phụ huynh
| Mã | Kịch bản | Kết quả mong đợi |
|---|---|---|
| PH-01 | Đăng ký, gửi yêu cầu liên kết | Trạng thái "chờ duyệt" |
| PH-02 | Xem báo cáo khi chưa duyệt | 403 |
| PH-03 | Giáo viên duyệt → xem báo cáo | Thấy điểm kỹ năng, số phút học, kỹ năng yếu nhất |
| PH-04 | Huỷ liên kết | Mất quyền xem ngay |

### D. Quản trị
| Mã | Kịch bản | Kết quả mong đợi |
|---|---|---|
| QT-01 | Tạo tài khoản giáo viên | Đăng nhập được ngay |
| QT-02 | Khoá tài khoản đang có phiên mở | Phiên chết ngay, đăng nhập lại bị 423 |
| QT-03 | Đặt lại mật khẩu | Mật khẩu cũ không dùng được |
| QT-04 | Import Excel 240 dòng có 5 dòng lỗi | Nhập 235 dòng, liệt kê 5 lỗi kèm số dòng |
| QT-05 | Import file .csv | Bị từ chối, báo rõ định dạng |

### E. Phi chức năng (đo, không đoán)
| Mã | Chỉ số | Ngưỡng (NFR) | Cách đo |
|---|---|---|---|
| NF-01 | p95 trang bài học | ≤ 500 ms | 200 người bằng Locust trong 10 phút |
| NF-02 | Thời gian chấm 40 câu | ≤ 300 ms | đo trong log, p95 |
| NF-03 | Hiển thị ở 360 px | Không cuộn ngang | DevTools, kiểm 4 màn chính |
| NF-04 | Cài lại từ đầu | ≤ 10 phút | máy sạch, chạy README bấm giờ |

## 4. Biên bản UAT (mẫu điền)

| Trường | Nội dung |
|---|---|
| Thời gian, địa điểm | |
| Thành phần tham gia | (ghi rõ vai trò: giáo viên, học sinh, phụ huynh, người quan sát) |
| Kịch bản đã chạy | |
| Số kịch bản đạt / tổng | ___ / 30 |
| Lỗi phát hiện | Mã lỗi, mức độ (1 chặn vòng học / 2 nặng / 3 nhỏ), người xử lý |
| Quyết định | Chấp nhận bàn giao / Chấp nhận có điều kiện / Không chấp nhận |
| Chữ ký các bên | |

**Điều kiện chấp nhận (SC5):** không còn lỗi mức 1 nào khiến học sinh không hoàn thành được một bài
học hoặc giáo viên không chấm được bài.
