# Cập nhật kiến trúc & chức năng — dán vào Chương 3 / báo cáo

Tài liệu này ghi **những gì đã thay đổi so với bản thiết kế ban đầu**, để Chương 3 trong báo cáo
không còn nói sai về hệ thống đang chạy.

## 1. Kiến trúc

| Hạng mục | Bản thiết kế | Thực tế đã làm |
|---|---|---|
| Giao diện | Jinja2 server-side | **Next.js 16 (App Router, TypeScript)** cho toàn bộ màn hình; FastAPI thành **API JSON thuần**. Bản Jinja2 vẫn còn để đối chiếu, không dùng khi demo |
| Số bảng CSDL | 16 bảng | **18 bảng**: thêm `sessions` (phiên đăng nhập) và `audit_logs` (nhật ký kiểm toán) |
| API | không tách | **~100 route**, chia 4 nhóm: học sinh, giáo viên, phụ huynh, quản trị |
| Bảo mật API | CSRF form | **CSRF double-submit cho HTML** + **header `X-Requested-With: fetch`** cho API JSON (buộc preflight, chặn origin lạ) |
| Ảnh/theme | không có | Ảnh **tự lưu trong repo**, không hotlink CDN ngoài |

## 2. Chức năng bổ sung so với Bảng 2.1

- **Thông báo trong ứng dụng** (chuông + trang `/notifications`): sinh khi giao bài, chấm bài,
  duyệt/từ chối phụ huynh, mở lại bài. Chuông tự cập nhật 30 giây/lần.
- **Giáo viên chấm bài nói**: hàng đợi riêng, nghe lại audio, rubric 4 tiêu chí
  **Hoàn thành yêu cầu · Phát âm · Độ trôi chảy · Từ vựng** (mỗi tiêu chí 0–2,5).
  Quyền nghe: **chính chủ hoặc giáo viên lớp đó** — quản trị không nghe được.
- **Mở lại bài đã chấm**: bắt buộc ghi lý do ≥10 ký tự, xoá điểm cũ (không cộng dồn),
  ghi nhật ký, báo cho học sinh.
- **Nhật ký kiểm toán** (`audit_logs`): chấm bài, mở lại, khoá/mở khoá tài khoản,
  duyệt/từ chối phụ huynh. Không lưu nội dung bài làm.
- **Tự đổi mật khẩu**: đổi xong huỷ mọi phiên khác, giữ phiên đang thao tác.
- **Phân trang** danh sách tài khoản; **lọc** hàng đợi chấm theo tên/email và theo lớp.
- **Video bài giảng**: giáo viên gắn **link YouTube/Drive** (nhúng iframe) hoặc **tải video tự quay**
  (mp4/webm/mov, tối đa 200 MB, phát bằng range request nên tua được). Quyền: giáo viên dạy khối đó
  mới gắn/xoá; học sinh chỉ xem video của khối mình; quản trị xem được nhưng không sửa.
  Mỗi bài chỉ có một video — gắn link sẽ thay file và ngược lại.
- **Xuất bảng điểm lớp ra Excel** (`.xlsx`), có dòng điểm trung bình lớp.
- **Sao lưu/khôi phục CSDL**: `scripts/backup_db.py` (dùng `sqlite3.backup`, kiểm tra toàn vẹn,
  tự sao lưu bản đang chạy trước khi khôi phục).

## 3. Quy tắc nghiệp vụ đã cài trong code

| Mã | Nội dung | Nơi cài |
|---|---|---|
| BR2 | Một học sinh chỉ thuộc một lớp đang hoạt động | `services/classes.py` |
| BR3 | Phụ huynh chỉ xem dữ liệu con sau khi giáo viên duyệt | `services/parent.py` |
| BR5 | Điểm trắc nghiệm = 10 × số đúng / tổng, làm tròn 1 chữ số | `services/scoring.py` |
| BR6 | Điểm cuối = 0,7 × tự động + 0,3 × giáo viên | `services/scoring.py` |
| BR7 | Hết lượt làm bài thì chặn bằng **409** | `services/practice.py` |
| BR8 | Nộp muộn trừ 10%/ngày, **làm tròn LÊN**, quá 3 ngày = 0 | `services/scoring.py` |
| BR9 | Giáo viên chỉ duyệt phụ huynh của học sinh lớp mình | `services/parent.py` |
| BR10 | Audio lưu tối đa một học kỳ, sau đó job dọn xoá | `services/storage.py` |
| — | Bài giao của giáo viên **áp dụng thật** (hạn nộp + số lượt), không dùng bài tự sinh | `services/practice.py` |
| — | Chấm thiếu tiêu chí ⇒ **422** kèm tên tiêu chí thiếu (không tự điền 0) | `services/grading.py` |

## 4. Cấu hình gửi email thật cho phụ huynh

Job `app/jobs/weekly_email.py` chạy hằng tuần. Mặc định **không gửi**, chỉ ghi `.eml` vào
`data/out/weekly/`. Muốn gửi thật, đặt biến môi trường trước khi chạy server:

```bash
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=<email>          # ví dụ: zzzthanhvdatzzz@gmail.com
export SMTP_PASS=<mật khẩu ứng dụng 16 ký tự của Gmail>
export SMTP_FROM="EnglishHub <email>"
```

Gmail **không dùng mật khẩu đăng nhập thường** — phải bật xác thực 2 bước rồi tạo
“Mật khẩu ứng dụng”. Nếu sai mật khẩu, job ghi lỗi vào `failed` và **không** đánh dấu đã gửi;
chạy lại tuần đó vẫn gửi được (idempotent theo tuần).

## 5. Việc CHƯA làm — nói rõ để không hứa quá

1. **Chấm nói tự động bằng AI**: chưa làm. Cần dịch vụ ASR (Whisper API hoặc model tự huấn luyện)
   và bộ tiêu chí phát âm; máy hiện tại không có GPU. Trong báo cáo nên ghi là **hướng phát triển**,
   không ghi là chức năng đã có.
2. **Huy hiệu**: bảng có trong CSDL nhưng chưa có luật trao và giao diện — chờ nhóm chốt luật.
3. **Xuất PDF**: hiện có Excel + CSV; PDF nên in từ trình duyệt (đã có CSS in cơ bản).
4. **Kiểm thử tải (p95 với 200 người)**: chưa đo.
5. **UAT với người thật**: 39 kịch bản chạy tự động, chưa có người dùng thật thao tác.

## 6. Cách chạy

```bash
bash scripts/dev.sh          # backend --reload + next dev (sửa code thấy ngay)
.venv/bin/python scripts/check_backend.py    # kiểm backend đang chạy đủ route
.venv/bin/python scripts/backup_db.py        # sao lưu CSDL
.venv/bin/python -m pytest -q                # toàn bộ test
```
