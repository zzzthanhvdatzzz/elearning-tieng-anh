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
- **Chống tua khi học video (video tải lên)**: học sinh không kéo được thanh tua vượt vị trí đã xem
  (client kéo về chỗ cũ); server chỉ cộng phần chênh lệch hợp lệ mỗi nhịp 10 giây, tối đa 20 giây,
  nên gọi API bằng tay cũng không nhảy cóc. **Hoàn thành khi đã xem ≥ 80% thời lượng** (bảng
  `video_progress`). Video nhúng YouTube/Drive **không** chặn tua được và không đo được thời lượng —
  muốn tính hoàn thành thì phải tải video lên hệ thống (đã ghi rõ trên giao diện).
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


---

# Báo cáo kiểm thử hệ thống (bản chạy thật — không điền tay)

| Mục | Giá trị |
|---|---|
| Ngày chạy | 24/11/2026 |
| Lệnh | `.venv/bin/python -m pytest -q` |
| Kết quả | **158 passed, 0 failed** (xem mục 5 để biết cách tái lập) |
| Thời gian | 567 giây (9 phút 27 giây), máy i7-6820HQ |
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
| **Tổng** | **158** | |

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
