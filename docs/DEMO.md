# Kịch bản demo 7 phút và checklist trước buổi báo cáo

## 0. Chuẩn bị (5 phút trước khi vào)

```bash
# tab 1
cd ~/elearning-tieng-anh && .venv/bin/python -m uvicorn app.main:app --port 8010
# tab 2
cd ~/elearning-tieng-anh/frontend && npm run dev
```

Kiểm tra nhanh trước khi trình bày:

```bash
python3 scripts/check_state.py     # phải ra: học sinh 14 · bài nộp 50 · chờ chấm 2 · câu hỏi 265
curl -s http://localhost:8010/health
```

Mở sẵn 2 tab: `localhost:3000` (giao diện mới) và `localhost:8010/docs` (tài liệu API).
Đăng xuất hết; mỗi vai trò dùng **một cửa sổ ẩn danh riêng** để không lẫn cookie.

| Vai trò | Tài khoản | Mật khẩu |
|---|---|---|
| Học sinh | `an.nm@truong.edu.vn` | `matkhau123` |
| Giáo viên | `gv.an@truong.edu.vn` | `matkhau123` |
| Phụ huynh | `phuhuynh.demo@truong.edu.vn` | `matkhau123` |
| Quản trị | `admin@truong.edu.vn` | `matkhau123` |

## 1. Kịch bản 7 phút

**Phút 1 — Bài toán (nói, không bấm máy)**
"Học sinh biết ngữ pháp nhưng không nghe, không nói được; giáo viên không có dữ liệu về quá trình
học. Vòng phản hồi hiện tại dài hàng tuần. Hệ thống rút nó xuống vài giây."

**Phút 2 — Học sinh (ẩn danh 1)**
1. `/units` → lộ trình Unit 1, bài 1 đã có dấu ✓, có ô "Bài tiếp theo"
2. Mở bài → từ vựng, ngữ pháp, transcript ẩn/hiện
3. Bấm "Luyện tập 10 câu" → nộp → **điểm hiện ngay + giải thích từng câu**
4. Nói: "Đây là chỗ vòng phản hồi rút từ một tuần xuống dưới 2 giây."

**Phút 3 — Giáo viên (ẩn danh 2)**
1. `/teacher/classes` → 8A1 có 9 học sinh, mã tham gia
2. "Quản lý →" → danh sách tên thật, CEFR từng em
3. "Chấm bài" → chọn một bài viết → chấm 4 tiêu chí → trả bài
4. Nói: "Rubric 4 tiêu chí là thứ biến việc chấm thành dữ liệu so sánh được, không còn cảm tính."

**Phút 4 — Báo cáo**
1. Trong màn lớp → "Xem báo cáo lớp" → danh sách **cần can thiệp**
2. Nói: "Giáo viên mở trong 1 phút, biết ngay em nào cần gặp."

**Phút 5 — Phụ huynh (ẩn danh 3)**
1. `/parent` → đã liên kết (được duyệt) → xem báo cáo con: phút học, điểm kỹ năng, kỹ năng yếu nhất
2. Nói: "BR3 — chưa duyệt thì không xem được; huỷ liên kết là mất quyền ngay."

**Phút 6 — Quản trị (ẩn danh 4)**
1. `/admin/users` → khoá một tài khoản → nói "phiên đang mở chết ngay"
2. `/admin/import` → chọn file `data/templates/mau_cau_hoi.xlsx` → thấy "2 câu hợp lệ, 1 dòng lỗi"
3. Nói: "AC15.2 — dòng sai bị bỏ qua và báo số dòng, không làm hỏng cả file."

**Phút 7 — Kiến trúc & kiểm thử (nói, mở `/docs`)**
"FastAPI giữ toàn bộ nghiệp vụ; Next.js chỉ là lớp giao diện gọi `/api/*`. Router không chứa
nghiệp vụ, service không biết HTTP — nên cùng một hàm chấm điểm phục vụ cả hai giao diện.
**104 test tự động**, báo cáo ở `docs/SYSTEM_TEST_REPORT.md`."

## 2. Câu hỏi giảng viên hay hỏi — và câu trả lời đã có căn cứ

| Câu hỏi | Trả lời ngắn |
|---|---|
| "Sao lại đổi từ Jinja2 sang Next.js?" | Bảng 3.1 đã cập nhật: tương tác client (chấm ngay, đếm giờ, ghi âm) viết gọn theo component; cái giá là 2 tiến trình + CORS — ghi rõ trong Bảng 3.12 |
| "Làm sao chắc điểm không sai?" | BR5/BR6 nằm trong **một** hàm `services/scoring.py`, có 18 test riêng; đổi trọng số chỉ sửa một chỗ |
| "Học sinh sửa điểm được không?" | Đáp án đọc từ CSDL ở server, client chỉ gửi lựa chọn; `GET /api/practice` không trả `correct_key` |
| "Học sinh xem bài người khác được không?" | Chặn ở service, có test: bài khối khác → 404, dữ liệu người khác → 403 |
| "Ghi âm chạy chưa?" | Đã code 2 đường (MediaRecorder + tải file). Test được đường tải file (8 test). Ghi âm cần HTTPS — có `scripts/run_https.py`; **chưa test trên điện thoại thật**, ghi rõ trong báo cáo kiểm thử |
| "Nội dung 240 câu do ai làm?" | Sinh tự động từ bộ từ vựng theo Unit, **nhóm Nội dung phải rà lại**; phần nghe chưa có audio thật — đã ghi trong `README` và báo cáo test |
| "Chịu được 200 người?" | Chưa đo. NFR1 ghi ngưỡng p95 ≤ 500 ms; phải chạy Locust trên staging. **Không nói "đã đo" khi chưa đo** |

## 3. Checklist việc thật trước khi nộp

| # | Việc | Ai | Xong khi |
|---|---|---|---|
| 1 | Rà 240 câu, sửa nghĩa tiếng Việt, thêm audio bài nghe | An | Import lại không còn dòng lỗi, nghe được 7 câu/listening |
| 2 | Chạy 30 kịch bản trong `docs/UAT.md`, điền biên bản | Quang Anh | Có biên bản ký, ghi rõ lỗi mức 1–3 |
| 3 | Dựng staging HTTPS, test ghi âm trên điện thoại | Trung | `https://<domain>` vào được, ghi âm nộp thành công |
| 4 | Vá 4 lỗ hổng trong Word + dán Chương 3 mới | Đạt | Bảng 2.1 có F4, Bảng 3.8 có `sessions`, `submissions` có cột bài viết/audio, tên hệ thống đã chốt |
| 5 | Đo p95 + cài lại từ đầu ≤ 10 phút (SC6) | Đạt | Có số thật ghi vào báo cáo, không ước lượng |

## 4. Nếu bị hỏi "còn gì chưa xong?"

Trả lời thẳng theo đúng thực tế, đừng giấu:

> "Ba việc còn lại là: rà nội dung 240 câu, UAT với 4 vai trò người thật, và đo hiệu năng trên
> staging. Cả ba đều đã có kịch bản và công cụ, chỉ chưa có người chạy xong."
