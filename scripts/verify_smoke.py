"""Kiểm chứng thật qua HTTP: phụ huynh, quản trị, import Excel, job email tuần."""
import io
import re
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
import http.cookiejar

BASE = "http://127.0.0.1:8010"
DB = "data/app.db"


class NoRedir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def mk():
    jar = http.cookiejar.CookieJar()
    return jar, urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), NoRedir)


def get(op, jar, path):
    try:
        r = op.open(BASE + path)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def post(op, jar, path, data):
    csrf = [c.value for c in jar if c.name == "csrf"]
    body = dict(data)
    if csrf:
        body["_csrf"] = csrf[0]
    try:
        r = op.open(urllib.request.Request(BASE + path, data=urllib.parse.urlencode(body).encode()))
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def login(op, jar, email, pw="matkhau123"):
    get(op, jar, "/auth/login")
    return post(op, jar, "/auth/login", {"email": email, "password": pw})


con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

# ---------- 1. phụ huynh tự đăng ký + gửi yêu cầu
pj, po = mk()
get(po, pj, "/auth/login")
st, _ = post(po, pj, "/auth/register-parent",
             {"email": "phuhuynh@truong.edu.vn", "password": "matkhau123", "full_name": "Phụ Huynh Demo"})
print("1) phụ huynh đăng ký:", st)

student = con.execute("SELECT id, email FROM users WHERE email='hs.lop9@truong.edu.vn'").fetchone()
st, body = post(po, pj, "/parent/link", {"student_email": student["email"]})
print("2) gửi yêu cầu liên kết:", st)
st, page = get(po, pj, f"/parent/report/{student['id']}")
print("3) xem báo cáo khi CHƯA duyệt (phải 403):", st)

# ---------- 2. giáo viên duyệt
tj, to = mk()
login(to, tj, "gv.an@truong.edu.vn")
st, q = get(to, tj, "/teacher/parents")
link = re.search(r"/teacher/parents/(\d+)/approve", q)
print("4) hàng đợi duyệt:", "có yêu cầu" if link else "TRỐNG")
st, _ = post(to, tj, f"/teacher/parents/{link.group(1)}/approve", {})
print("5) duyệt:", st)

st, page = get(po, pj, f"/parent/report/{student['id']}")
print("6) phụ huynh xem báo cáo SAU duyệt:", st, "| có điểm kỹ năng:", "Điểm theo kỹ năng" in page)

# ---------- 3. quản trị + import Excel
aj, ao = mk()
login(ao, aj, "admin@truong.edu.vn")
st, users = get(ao, aj, "/admin/users")
print("7) trang tài khoản:", st, "| số dòng user:", users.count("/admin/users/") // 2)

from openpyxl import Workbook
wb = Workbook()
ws = wb.active
ws.append(["skill", "prompt", "option_a", "option_b", "option_c", "option_d", "correct_key", "explanation"])
ws.append(["grammar", "Câu import 1 ______ ok.", "is", "are", "be", "been", "A", "giải thích"])
ws.append(["grammar", "Câu import 2 ______ ok.", "is", "are", "be", "been", "B", ""])
ws.append(["sai", "Câu lỗi", "a", "b", "c", "d", "A", ""])          # dòng lỗi
buf = io.BytesIO()
wb.save(buf)
data = buf.getvalue()

lesson = con.execute("SELECT id FROM lessons WHERE code='U1-L2'").fetchone()["id"]
csrf = [c.value for c in aj if c.name == "csrf"][0]
boundary = "----MaoBoundary"
parts = [
    f'--{boundary}\r\nContent-Disposition: form-data; name="_csrf"\r\n\r\n{csrf}\r\n'.encode(),
    f'--{boundary}\r\nContent-Disposition: form-data; name="lesson_id"\r\n\r\n{lesson}\r\n'.encode(),
    (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="cau-hoi.xlsx"\r\n'
     "Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n").encode()
    + data + b"\r\n",
    f"--{boundary}--\r\n".encode(),
]
req = urllib.request.Request(BASE + "/admin/questions/import", data=b"".join(parts),
                             headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
try:
    r = ao.open(req)
    st, html = r.status, r.read().decode()
except urllib.error.HTTPError as e:
    st, html = e.code, e.read().decode()
m = re.search(r"<b>(\d+)</b> câu hợp lệ[^<]*<b class=\"wrong\">(\d+)</b>", html)
print("8) import Excel:", st, "| thêm:", m.group(1) if m else "?", "| dòng lỗi:", m.group(2) if m else "?")
print("   CSDL có câu mới:", con.execute(
    "SELECT COUNT(*) FROM questions WHERE lesson_id=? AND prompt LIKE 'Câu import%'", (lesson,)).fetchone()[0])

# ---------- 4. job báo cáo tuần
from app.jobs import weekly_email
res = weekly_email.run_weekly(send=False)
print("9) job báo cáo tuần:", res["created"], "thư tạo |", res["skipped"], "bỏ qua | SMTP:", res["smtp"])
res2 = weekly_email.run_weekly(send=False)
print("   chạy lại (idempotent):", res2["created"], "tạo |", res2["skipped"], "bỏ qua")

files = list(__import__("pathlib").Path(res["out_dir"]).glob("*.eml"))
if files:
    txt = files[0].read_text(errors="replace")
    print("10) nội dung thư:", "Báo cáo tuần này" in txt, "| có tên học sinh:", "Lê Thị Demo" in txt)
