# Lộ trình code — nối báo cáo với mã nguồn

Mỗi mục dưới đây ứng với một mã đầu việc trong Bảng 4.1 và một cột mốc M1–M5.
Làm đúng thứ tự này vì phụ thuộc đã ghi ở Phụ lục A.

## Vá báo cáo trước khi gõ dòng đầu (30 phút)

1. **F4 bị thiếu trong Bảng 2.1.** Bảng nhảy F3 → F5 nhưng F4 (kiểm tra đầu vào) được
   dùng khắp nơi: mục 2.6 (Sprint 1), Bảng 2.6, UC-03, mục 3.9. Phải thêm dòng F4 vào
   Bảng 2.1 và đánh số lại, nếu không ma trận truy vết bị đứt ngay từ đầu.
2. **Bảng 3.9 thiếu 3 endpoint mà thiết kế khác đã giả định:** danh sách bài giao cho
   học sinh (`GET /assignments`), hàng đợi chấm (`GET /teacher/submissions?status=pending`
   — mục 3.11 S12 cần), và đọc/thông báo (`GET /notifications` — bảng `notifications`
   có trong ERD nhưng không có API). Thêm vào bảng cho khớp 16 bảng.
3. **Tên hệ thống đang để trống.** Toàn báo cáo có câu kiểu "Kiến trúc bốn lớp của "
   — biến tên sản phẩm bị mất. Chốt một tên rồi thay hàng loạt (Word: Ctrl+H, tìm
   "của  trong" → "của <Tên> trong").

## Tuần 2 — Sprint 0 (mốc M2): đăng nhập chạy được ✅ ĐÃ XONG

| Việc | Mã | Trạng thái |
|---|---|---|
| Khung repo, CI | C1 | ✅ `main.py`, `db.py`, pytest, `.gitignore` |
| Model 16 bảng + seed | C3 | ✅ 17 bảng (16 theo Bảng 3.8 + `sessions`), `app/seed.py` |
| Auth: đăng ký/đăng nhập/phiên | C2 | ✅ bcrypt cost 12, session DB, CSRF double-submit, 9 test |
| base.html + S1–S2 | C4 | ✅ `base.html`, `auth_login.html`, `auth_register.html` (CSS tay, Bootstrap thay ở C4 hoàn chỉnh) |

Nghiệm thu M2: giáo viên đăng nhập, thấy tên + vai trò ở `/me`. Còn thiếu để đóng M2:
màn hình tạo lớp S11 của giáo viên (đầu việc E1) — lớp hiện tạo bằng seed.

## Tuần 3 — Sprint 1 (M3): vòng học mở

- ✅ D6: `services/scoring.py` — BR5, BR6, BR8, ngưỡng CEFR, rubric; 18 test riêng.
- ✅ D1: `services/placement.py` + `routers/placement.py` — 25 câu (10/8/7), bài viết,
  chấm tự động, hàng đợi chấm của giáo viên, giáo viên xác nhận CEFR (±1 bậc, bắt buộc
  nhận xét khi điểm < 5,0), BR4 chặn làm lại trong học kỳ. Chạy thật: 10.0 + 8.0 → 9.4 → B2.
- ✅ D2: `services/learning.py` + `routers/learning.py` — S5 lộ trình theo khối lớp (6 bài/Unit),
  S6 trang học bài (mục tiêu, từ vựng, ngữ pháp, bài đọc, audio + transcript ẩn/hiện),
  `POST /lessons/{id}/progress` cộng dồn giây, phần trăm chỉ tăng và kẹp 0–100, chặn client
  gửi số giây vô lý (3600s/lần). Chạy thật: 120s → 180s → 190s + 100%, bài tiếp theo tự chuyển.

**Mốc M3 đã đóng**: đăng nhập → placement → xếp CEFR → mở lộ trình → học bài → ghi tiến độ.

Lỗ hổng thứ 4 phát hiện khi code: **bảng `submissions` trong Bảng 3.8 thiếu cột lưu nội
dung bài viết / đường dẫn audio**. Đã thêm `text_content`, `audio_path`, `cefr_proposed`,
`graded_by` — cần bổ sung vào báo cáo cho khớp.

## Tuần 4 — Sprint 2 (M4a): nộp bài và chấm

- ✅ D6 (phần luyện tập): `services/practice.py` + `routers/practice.py` — 10 câu/đề, chấm ngay,
  hiện đáp án đúng + giải thích từng câu, lịch sử các lượt, BR7 chặn lượt thứ 4 **ở server**
  (gọi thẳng API vẫn 409), tái dùng `grade_mcq`/`auto_score` nên công thức vẫn chỉ một chỗ.
  Chạy thật: 10.0 → 7.0 (sai 3 câu) → 10.0 → lượt 4 = 409.
- ✅ D5 + D7: `services/writing.py`, `services/grading.py`, `routers/writing.py` — nháp tự lưu
  `localStorage` 10 giây, đếm từ, chặn bài < 20 từ; giáo viên chấm 4 tiêu chí × 0–2,5,
  bắt buộc nhận xét khi < 5,0, chấm lại bị từ chối, học sinh thấy điểm + nhận xét ngay.
  Chạy thật: 8.5/10 → hiện với học sinh.
- ⬜ D4 ghi âm MediaRecorder (**phải chạy HTTPS, kể cả localhost** — rủi ro R2);
  phương án dự phòng: tải file lên.
- D7 rubric 4 tiêu chí × 0–2,5; BR6 điểm cuối = 0,7 × tự động + 0,3 × giáo viên;
  chặn lưu khi điểm < 5,0 mà không có nhận xét (AC12.2).

## Tuần 5 — Sprint 3 (M4b): lớp, báo cáo, import

- ✅ E1/E2: `services/classes.py`, `services/assignments.py`, `routers/teacher.py` — tạo lớp sinh mã
  6 ký tự, thêm/xoá học sinh, BR2 chặn một em ở hai lớp, giao bài có deadline (chặn hạn quá khứ),
  số lần làm, trang "Bài được giao" cho học sinh. Chạy thật: lớp `OR41X0` → giao bài → học sinh
  tự đăng ký bằng mã → thấy bài "0/2".
- ✅ E3/E4 (một phần): `services/report.py`, `routers/report.py` — điểm theo kỹ năng, kỹ năng yếu
  nhất, phút học, biểu đồ 6 tuần, lịch sử nộp; báo cáo lớp có danh sách "cần can thiệp" và
  xuất CSV (đường dẫn `/reports/class/{id}/export.csv` — dạng `.csv` cũ trả 422 vì xung đột
  route với `{class_id}: int`).
- ✅ Email báo cáo tuần cho phụ huynh: `jobs/weekly_email.py` — thread nền trong cùng tiến trình,
  idempotent theo (tuần ISO, phụ huynh, học sinh), có catch-up; chưa cấu hình SMTP thì ghi
  `data/out/weekly/*.eml` và **nói rõ là chưa gửi thật** (`smtp: false` trong kết quả job).
- ✅ E5: liên kết phụ huynh + luồng duyệt giáo viên (`/parent`, `/teacher/parents`), BR3 chặn
  xem trước khi duyệt, huỷ liên kết thì mất quyền ngay.
- ✅ E6 + F15: import câu hỏi từ Excel (`services/admin.py`), kiểm tra từng dòng, bỏ dòng lỗi
  và liệt kê lý do, giới hạn 5 MB, chỉ nhận `.xlsx`.
- ✅ F2: quản trị tài khoản — tạo, khoá/mở, đặt lại mật khẩu; khoá tài khoản huỷ mọi phiên ngay.
- ✅ F3: `Dockerfile` + `deploy.md` (Nginx, HTTPS cho ghi âm, sao lưu, checklist nghiệm thu).

## Tuần 6 — UAT và bàn giao (M5)

- F1/F2 system test theo kịch bản, UAT, biên bản.
- F4 hồ sơ bàn giao: README, deploy.md, hướng dẫn sử dụng.

> Trạng thái code hiện tại: **15/15 màn hình có bản Next.js**, backend FastAPI đủ 4 vai trò, 265 câu hỏi
> trong CSDL (240 câu cho 24 bài + 25 câu placement), Docker Compose cho 2 tiến trình, khung UAT ở
> `docs/UAT.md`, biểu mẫu câu hỏi ở `data/templates/mau_cau_hoi.xlsx`.
>
> Việc còn lại là của con người: An rà nghĩa tiếng Việt + bổ sung câu nghe/đọc thật, Quang Anh chạy
> 30 kịch bản UAT, Trung dựng staging HTTPS để test ghi âm.

## Thứ tự cắt khi trễ (mục 2.6)

F7 (ghi âm) → F14 (báo cáo phụ huynh) → F15 (import) → **không cắt F12**.
