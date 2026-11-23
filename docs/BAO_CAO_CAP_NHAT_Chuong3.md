# Nội dung cập nhật Chương 3 — chuyển frontend sang Next.js

> Dùng để dán vào `Bao_cao_Nhom05.docx`. Các đoạn dưới đây **thay thế** đúng mục ghi trong tiêu đề,
> không thêm mục mới ngoài chương trình khung.

---

## 3.1. Kiến trúc tổng thể (VIẾT LẠI TOÀN BỘ MỤC)

Hệ thống chạy hai tiến trình độc lập: **FastAPI** đảm nhiệm toàn bộ nghiệp vụ và dữ liệu, **Next.js**
đảm nhiệm giao diện. Hai tiến trình nói chuyện với nhau qua lớp JSON `/api/*`; frontend không truy
cập cơ sở dữ liệu và không chứa quy tắc nghiệp vụ nào.

Ở phía máy chủ, FastAPI vẫn giữ bốn lớp như thiết kế ban đầu: lớp giao diện (template Jinja2 cho
các trang quản trị nội bộ), lớp ứng dụng (router), lớp nghiệp vụ (service thuần) và lớp dữ liệu
(PostgreSQL, SQLite khi phát triển). Ranh giới quan trọng nhất vẫn là **router ↔ service**: router
nhận yêu cầu, kiểm tra quyền, gọi service và trả kết quả; service không biết gì về HTTP. Nhờ ranh
giới này, cùng một hàm chấm điểm phục vụ cả trang HTML và endpoint JSON mà không phải viết lại.

Ở phía người dùng, Next.js (App Router, React 19) render giao diện học sinh. Mọi lời gọi API đều đi
qua một hàm bọc duy nhất (`lib/api.ts`) để bảo đảm ba điều kiện: gửi kèm cookie phiên
(`credentials: "include"`), mang header `X-Requested-With: fetch` làm hàng rào CSRF, và chuẩn hoá
thông báo lỗi về một dạng đọc được.

Bảng so sánh hai phương án đã cân nhắc:

| Tiêu chí | Một tiến trình, Jinja2 | Hai tiến trình, Next.js + API JSON |
|---|---|---|
| Số dịch vụ phải triển khai | 1 | 2 (Nginx đứng trước) |
| Thời gian dựng một màn hình mới | Thấp (template + router) | Cao hơn (component + endpoint) |
| Tương tác phía client (chấm ngay, ghi âm) | Phải viết JavaScript rời | Có sẵn mô hình component |
| Kiểm thử giao diện | Kiểm thử HTML bằng pytest | Cần thêm công cụ trình duyệt |
| Bảo mật phiên | Cookie cùng origin | Cookie + CORS có allowlist |
| Phù hợp khi nhóm có 1 người làm frontend | Có | Chỉ khi người đó đã quen React |

Nhóm chọn phương án hai sau khi đã có bản chạy đầy đủ bằng Jinja2; bản Jinja2 được giữ lại làm
đường dự phòng và làm công cụ đối chiếu khi kiểm thử.

Công việc chạy nền (nhắc hạn nộp và gửi báo cáo tuần cho phụ huynh) vẫn nằm trong tiến trình
FastAPI dưới dạng một thread nền. Đánh đổi được ghi nhận: nếu tiến trình chết thì worker cũng
dừng, nhưng nhóm không phải vận hành thêm dịch vụ. Job được thiết kế **idempotent** theo
(tuần ISO, phụ huynh, học sinh) và có cơ chế **catch-up**, nên máy tắt lúc 7 giờ thứ Hai thì lần
chạy kế tiếp vẫn gửi đúng một báo cáo, không gửi trùng.

---

## 3.2. Lựa chọn công nghệ và lý do (SỬA 3 DÒNG TRONG BẢNG 3.1)

| Thành phần | Lựa chọn | Lý do | Phương án loại |
|---|---|---|---|
| Template (trang quản trị) | Jinja2 | Đi kèm FastAPI, không cần bước build | — (giữ nguyên) |
| **Giao diện học sinh** | **Next.js 16 (App Router) + React 19** | Tương tác phức tạp (chấm ngay, đếm giờ học, ghi âm) viết gọn theo mô hình component; tách giao diện khỏi API để sau này dùng lại cho ứng dụng di động | Jinja2 + JavaScript rời — khó bảo trì khi số màn hình tăng |
| **API** | **JSON `/api/*` + CORS allowlist** | Frontend và backend tách rời, kiểm thử API độc lập bằng pytest | GraphQL — vượt nhu cầu |
| **Chống CSRF cho API** | **Header tuỳ biến `X-Requested-With`** | Trình duyệt không cho form HTML tự gắn header tuỳ biến; header này buộc preflight nên origin lạ bị CORS chặn trước khi tới server | CSRF token trong form — chỉ hợp với trang render phía server |

Các dòng còn lại của Bảng 3.1 giữ nguyên.

---

## 3.8. Hợp đồng API (BỔ SUNG: 9 endpoint JSON)

Ngoài 24 endpoint trả HTML, hệ thống có 9 endpoint JSON cho frontend Next.js. Quy ước lỗi giữ
nguyên: 401 chưa đăng nhập, 403 sai quyền hoặc thiếu header CSRF, 404 không tìm thấy, 409 xung đột
nghiệp vụ, 422 dữ liệu không hợp lệ.

| Endpoint | Vai trò | Mục đích | Lỗi chính |
|---|---|---|---|
| POST `/api/auth/login` | Khách | Tạo phiên, trả hồ sơ người dùng | 401, 423 |
| POST `/api/auth/register` | Khách | Đăng ký học sinh bằng mã lớp | 409, 422 |
| POST `/api/auth/logout` | Mọi vai trò | Huỷ phiên hiện tại | 401 |
| GET `/api/me` | Mọi vai trò | Hồ sơ người dùng đang đăng nhập | 401 |
| GET `/api/units` | Học sinh | Lộ trình theo khối lớp kèm % hoàn thành | 401, 403 |
| GET `/api/lessons/{id}` | Học sinh | Nội dung bài học, thời gian đã học | 403, 404 |
| POST `/api/lessons/{id}/progress` | Học sinh | Cộng dồn thời gian học | 403, 404 |
| GET `/api/assignments` | Học sinh | Bài được giao kèm hạn và số lượt | 401, 403 |
| GET `/api/practice/{lesson_id}` | Học sinh | Đề luyện tập (không kèm đáp án) | 403, 404 |
| POST `/api/practice/{lesson_id}/submit` | Học sinh | Nộp bài, nhận điểm và giải thích | 403, 409, 422 |

Ghi chú kỹ thuật: endpoint `GET /api/practice/{lesson_id}` **không** trả `correct_key`; đáp án chỉ
xuất hiện trong phản hồi của endpoint nộp bài, giữ nguyên nguyên tắc "không lộ đáp án" ở mục 3.10.

---

## 3.13. Quyết định thiết kế và đánh đổi (THÊM 1 DÒNG CUỐI BẢNG 3.12)

| Quyết định | Lợi ích | Cái giá |
|---|---|---|
| Tách frontend Next.js khỏi FastAPI | Giao diện tương tác gọn hơn, API dùng lại được cho ứng dụng khác | Phải triển khai và cấu hình 2 tiến trình; phải bật CORS có allowlist; kiểm thử giao diện cần công cụ trình duyệt |

---

## 3.14. Tổng hợp bước 3 (SỬA 1 CÂU HOẠT ĐỘNG)

Thay câu "…vẽ sơ đồ use case…" bằng: "…vẽ sơ đồ use case…; tách giao diện sang Next.js và đặc tả
thêm 9 endpoint JSON; thiết kế hàng rào CSRF cho API bằng header tuỳ biến."

---

# Phụ lục: 4 chỗ khác trong báo cáo PHẢI sửa cho khớp sản phẩm

1. **Bảng 2.1 thiếu F4** (kiểm tra đầu vào). Bảng đang nhảy F3 → F5, trong khi F4 được dùng ở
   Sprint 1, Bảng 2.6, UC-03 và mục 3.9. Thêm dòng F4 và đánh số lại.
2. **Bảng 3.8 thiếu bảng `sessions`** — thiết kế "session thay vì JWT, thu hồi phiên ngay" (mục 3.13)
   bắt buộc phải có chỗ lưu phiên. Số bảng đúng là **17**, không phải 16.
3. **Bảng 3.8 thiếu cột lưu bài viết và audio** trong `submissions`: đã thêm `text_content`,
   `audio_path`, `cefr_proposed`, `graded_by`.
4. **Tên hệ thống đang trống** ở mọi câu dạng "kiến trúc bốn lớp của …". Chốt tên rồi thay hàng loạt.

# Phụ lục: đường dẫn triển khai mới

- Backend: `uvicorn app.main:app --port 8010` (cổng 8000 bận trên máy phát triển).
- Frontend: `cd frontend && npm run dev` → `http://localhost:3000`.
- Biến môi trường frontend: `NEXT_PUBLIC_API_URL=http://localhost:8010` trong `frontend/.env.local`.
- Nginx phải có hai `location`: một `proxy_pass` tới Next.js, một tới FastAPI; `client_max_body_size`
  đặt 12 MB ở location của FastAPI để nhận audio bài nói.
