# Hướng dẫn sử dụng EnglishHub

Hệ thống học tiếng Anh trực tuyến cho học sinh THCS & THPT — Nhóm 05.
Tài liệu này viết cho **người dùng cuối**: học sinh, giáo viên, phụ huynh, quản trị.

---

## 0. Chuẩn bị để chạy thử

```bash
cd elearning-nhom05
bash run-dev.sh          # mở backend (cổng 8010) và giao diện (cổng 3000)
```

Mở trình duyệt: **http://localhost:3000**

**Tài khoản demo** (mật khẩu chung: `matkhau123`)

| Vai trò | Email |
|---|---|
| Giáo viên | `gv.an@truong.edu.vn` |
| Học sinh lớp 8A1 | `an.nm@truong.edu.vn` |
| Học sinh lớp 9 | `hs.lop9@truong.edu.vn` |
| Phụ huynh | `phuhuynh.demo@truong.edu.vn` |
| Quản trị | `admin@truong.edu.vn` |

Mã lớp demo: **8A1X21**

---

## 1. HỌC SINH

### 1.1 Đăng ký tài khoản
1. Vào **http://localhost:3000/register**
2. Chọn tab **Học sinh**
3. Nhập họ tên, email, mật khẩu (≥ 8 ký tự)
4. Nhập **mã lớp 6 ký tự** do giáo viên cấp (ví dụ `8A1X21`)
5. Bấm **Tạo tài khoản học sinh**

> Nếu không có mã lớp, hỏi giáo viên chủ nhiệm. Mã sai sẽ bị từ chối.

### 1.2 Kiểm tra trình độ (làm một lần)
Sau khi đăng ký, hệ thống đưa vào bài **kiểm tra đầu vào**: 25 câu trắc nghiệm (ngữ pháp, đọc, nghe) + 1 bài viết ngắn.
- Trắc nghiệm chấm ngay; bài viết chờ giáo viên chấm.
- Kết quả tổng hợp xếp trình độ **A1–B2** và lưu vào hồ sơ.
- **Chỉ được làm một lần.** Không làm lại được.

### 1.3 Trang tổng quan
Sau khi đăng nhập, bạn luôn vào **/dashboard**:
- Ô số: bài đã hoàn thành · phút đã học · bài cần làm · **video đã xem xong**
- **Bài tiếp theo** → nút **Học ngay**
- **Việc cần làm**: bài được giao, hạn nộp, số lượt còn lại
- **Video bài giảng**: thanh tiến độ và danh sách bài chưa xem xong
- **Bài đã nộp gần đây**: điểm và trạng thái (đã chấm / chờ chấm)
- Chuông 🔔 góc phải: thông báo mới (tự cập nhật mỗi 30 giây)

### 1.4 Học một bài
1. Menu **Lộ trình** → chọn Unit → chọn bài
2. Trang bài học gồm: **video bài giảng** (nếu có) + nội dung + câu hỏi luyện tập
3. Thời gian học được cộng dồn tự động

### 1.5 Xem video bài giảng — luật quan trọng
- **Không tua được**: kéo thanh tua vượt chỗ đã xem thì video tự nhảy về chỗ cũ.
- **Phải xem đủ 80% thời lượng** mới được tính hoàn thành.
- **Xem tới 50% sẽ có câu hỏi kiểm tra**: video tự dừng, bạn phải trả lời đúng mới được tính hoàn thành. Sai thì xem lại đoạn vừa rồi và chọn lại.
- Video nhúng từ YouTube/Drive: xem được nhưng **không** tính hoàn thành theo 80%.
- Nếu video bị giật: báo giáo viên chuyển sang link YouTube, hoặc xem ở máy khác.

### 1.6 Luyện tập trắc nghiệm
1. Vào bài học → bấm **Luyện tập**
2. Làm 10 câu, bấm **Nộp bài** → điểm hiện ngay
3. **Điểm = 10 × số câu đúng / tổng số câu**
4. **Số lượt do giáo viên đặt** (mặc định 3). Hết lượt sẽ báo *"Bạn đã hết lượt làm bài này"*.
5. Nộp muộn so với hạn: **trừ 10% mỗi ngày**, trễ quá 3 ngày = 0 điểm. Trễ 1 giây cũng tính 1 ngày.

### 1.7 Nộp bài viết
1. Vào bài học → **Bài viết**
2. Viết tối thiểu 20 từ, có đếm từ trực tiếp
3. Bấm **Nộp bài** → trạng thái "chờ chấm"
4. Khi giáo viên chấm: bạn nhận thông báo và xem được **điểm + nhận xét theo 4 tiêu chí**
5. Bài đã nộp không sửa được; hết lượt thì không nộp lại

### 1.8 Nộp bài nói
1. Vào bài học → **Bài nói**
2. Chọn **Ghi âm trực tiếp** (cần cho phép micro) hoặc **Tải tệp lên**
3. Định dạng: webm, ogg, mp3, m4a, wav — tối đa 10 MB
4. Giáo viên nghe và chấm 4 tiêu chí: Hoàn thành yêu cầu · Phát âm · Độ trôi chảy · Từ vựng
5. Chỉ bạn và giáo viên lớp bạn nghe được bản ghi.

### 1.9 Xem điểm và báo cáo
- Menu **Báo cáo**: điểm theo kỹ năng, kỹ năng yếu nhất, biểu đồ 6 tuần, bài đã nộp
- Giáo viên và phụ huynh (sau khi được duyệt) xem cùng dữ liệu này

### 1.10 Đổi mật khẩu
Menu **Mật khẩu** → nhập mật khẩu hiện tại + mật khẩu mới (≥ 8 ký tự).
Đổi xong, **mọi thiết bị khác bị đăng xuất**, máy đang dùng vẫn giữ phiên.

### 1.11 Lỗi thường gặp
| Hiện tượng | Nguyên nhân | Cách xử lý |
|---|---|---|
| "Mã lớp không đúng" | Sai mã hoặc lớp khác khối | Xin lại mã từ giáo viên |
| Không tua được video | Đúng thiết kế | Xem tiếp từ chỗ dừng |
| "Bạn đã hết lượt" | Hết số lần làm bài | Xin giáo viên giao lại |
| 403 khi xem bài | Bài thuộc khối khác | Chỉ học bài của khối mình |
| Trang trắng / lỗi Not Found | Backend đang chạy bản cũ | Nhờ người quản trị khởi động lại |

---

## 2. GIÁO VIÊN

### 2.1 Tạo lớp và lấy mã
1. Menu **Lớp** → nhập tên lớp + khối → **Tạo lớp và sinh mã**
2. Hệ thống sinh **mã 6 ký tự**; gửi mã này cho học sinh
3. Bảng lớp hiển thị sĩ số, mã lớp, nút **Quản lý**

### 2.2 Giao bài cho lớp
1. Vào **Lớp** → **Quản lý** lớp
2. Chọn bài học, nhập tiêu đề, **hạn nộp**, **số lần làm tối đa**, loại bài (Trắc nghiệm / Viết / Nói)
3. Bấm **Giao bài cho lớp** → học sinh nhận thông báo ngay

> Hạn nộp và số lượt **có tác dụng thật**: hết lượt là bị chặn, nộp muộn bị trừ điểm.

### 2.3 Chấm bài viết
1. Menu **Chấm bài viết** → chọn bài trong hàng đợi
2. Chấm 4 tiêu chí, mỗi tiêu chí 0–2,5 điểm
3. **Bắt buộc nhập nhận xét nếu tổng điểm < 5**
4. Bấm **Lưu điểm** → học sinh nhận thông báo kèm điểm

### 2.4 Chấm bài nói
1. Menu **Chấm bài nói** → chọn bài → nghe bằng trình phát trong trang
2. Chấm 4 tiêu chí: Hoàn thành yêu cầu · Phát âm · Độ trôi chảy · Từ vựng
3. Bấm **Lưu điểm**

> Mỗi bài chỉ chấm một lần. Chấm sai thì dùng **Mở lại để chấm lại** (xem 2.5).

### 2.5 Mở lại bài đã chấm
1. Trong trang bài đã chấm, nhập **lý do** (ít nhất 10 ký tự)
2. Bấm **Mở lại để chấm lại**
3. Chấm lại bình thường — điểm cũ bị xoá, không cộng dồn
4. Lý do được ghi vào **Nhật ký hoạt động** (chỉ quản trị xem)

### 2.6 Gắn video bài giảng
1. Menu **Video bài giảng** (hoặc mở trang bài học)
2. Chọn bài ở danh sách bên trái
3. Chọn **Dán link** (YouTube/Drive) hoặc **Tải video lên** (mp4/webm/mov, tối đa 200 MB)
4. Bấm **Gắn link** hoặc chọn tệp

> Chỉ giáo viên dạy khối đó mới gắn được. Mỗi bài một video.
> **Nên tải video lên** nếu muốn áp luật chống tua + 80% + câu hỏi kiểm tra; link ngoài không áp được.

### 2.7 Duyệt liên kết phụ huynh
1. Menu **Phụ huynh** (số trong ngoặc = số yêu cầu chờ)
2. Kiểm tra đúng phụ huynh của học sinh lớp mình → **Duyệt** hoặc **Từ chối**
3. Chưa duyệt thì phụ huynh **không xem được** báo cáo

### 2.8 Báo cáo lớp
- Menu **Lớp** → **Quản lý** → **Báo cáo**: điểm trung bình lớp, từng học sinh, ai cần hỗ trợ
- Bấm **Tải bảng điểm (.xlsx)** để lấy file Excel (có dòng điểm trung bình lớp)
- Bấm **Xuất CSV** nếu cần dữ liệu thô

---

## 3. PHỤ HUYNH

### 3.1 Đăng ký
1. Vào **http://localhost:3000/register** → tab **Phụ huynh**
2. Nhập họ tên, email, mật khẩu (≥ 8 ký tự) → **Tạo tài khoản phụ huynh**
3. Tự chuyển tới trang **/parent**

### 3.2 Liên kết với con
1. Nhập **email tài khoản học sinh của con** (hỏi con hoặc giáo viên chủ nhiệm)
2. Bấm gửi → trạng thái **chờ duyệt**
3. Giáo viên chủ nhiệm duyệt xong mới xem được báo cáo

> Vì sao phải chờ duyệt: để người lạ không tự nhập email học sinh rồi đọc điểm của con người khác.

### 3.3 Xem báo cáo của con
Sau khi được duyệt, trang **/parent** hiện danh sách con → bấm **Xem báo cáo**:
- Số phút học, số bài đã nộp, trình độ CEFR
- **Số video đã xem xong**
- Điểm theo từng kỹ năng, kỹ năng yếu nhất
- Biểu đồ thời gian học 6 tuần

### 3.4 Email báo cáo hằng tuần
Hệ thống gửi báo cáo tuần vào **thứ Hai 07:00** cho phụ huynh đã được duyệt.
Nếu chưa thấy email: kiểm tra Hộp thư đến/Spam, hoặc hỏi nhà trường vì máy chủ có thể chưa cấu hình gửi thư.

### 3.5 Huỷ liên kết
Trong trang **/parent**, bấm huỷ ở dòng của con → mất quyền xem ngay lập tức.

---

## 4. QUẢN TRỊ

| Việc | Đường dẫn | Ghi chú |
|---|---|---|
| Danh sách tài khoản | **/admin/users** | Tìm theo email/tên, lọc vai trò, phân trang 20/trang |
| Tạo tài khoản | **/admin/users** | Nhập email, họ tên, vai trò, mật khẩu ban đầu |
| Khoá / mở khoá | **/admin/users** | Khoá thì mọi phiên đang mở bị đăng xuất ngay |
| Nhập từ Excel | **/admin/import** | Dòng lỗi được báo riêng, dòng đúng vẫn được thêm |
| Nhật ký hoạt động | **/admin/audit** | Ai chấm bài, mở lại, khoá tài khoản, duyệt phụ huynh |

> **Quản trị không nghe được bản ghi âm của học sinh** — chỉ chính chủ và giáo viên lớp đó.

---

## 5. Xử lý sự cố nhanh

| Mã lỗi | Nghĩa | Việc cần làm |
|---|---|---|
| 401 | Chưa đăng nhập / phiên hết hạn (8 giờ) | Đăng nhập lại |
| 403 | Không có quyền (khác khối, khác lớp) | Kiểm tra tài khoản/lớp |
| 404 | Không tìm thấy, hoặc **backend chạy bản cũ** | Chạy `scripts/check_backend.py` |
| 409 | Hết lượt làm bài / chưa xem đủ 50% video | Xem thông báo chi tiết |
| 422 | Dữ liệu nhập chưa đúng (thiếu tiêu chí, link sai) | Đọc nội dung lỗi |
| Trang trắng | Frontend chưa build lại | `npm run build` rồi `npm run start` |

**Ba lệnh quan trọng**

```bash
bash scripts/dev.sh                                   # chạy hệ thống (tự migrate CSDL)
.venv/bin/python scripts/check_backend.py             # kiểm backend đủ route + đủ bảng
.venv/bin/python scripts/backup_db.py                 # sao lưu CSDL trước khi sửa dữ liệu
```

**Sau khi `git pull`**: phải khởi động lại backend (code cũ vẫn nằm trong bộ nhớ) và build lại frontend nếu chạy bản production.

---

## 6. Những điều hệ thống CHƯA làm (nói rõ để không hứa quá)

1. **Chấm nói tự động bằng AI** — chưa có; giáo viên chấm thủ công.
2. **Huy hiệu** — đã có bảng trong CSDL nhưng chưa có luật trao và giao diện.
3. **Ứng dụng di động** — chỉ có web, dùng được trên điện thoại qua trình duyệt.
4. **Phát video cho cả lớp cùng lúc** — chưa đo tải; nên dùng link YouTube nếu lớp đông.
5. **Xuất PDF** — hiện có Excel và CSV; PDF in từ trình duyệt.
