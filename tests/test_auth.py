"""Test cho F1 — đăng ký, đăng nhập, đăng xuất (AC1.1–AC1.3, US2/AC2)."""
from sqlalchemy import select

from app.models import Enrollment, Session, User
from tests.conftest import PASSWORD, csrf_of


def test_health_ok(anon_client):
    assert anon_client.get("/health").json() == {"status": "ok", "db": "ok"}


def test_login_sai_mat_khau_tra_401(anon_client, teacher_and_class):
    token = csrf_of(anon_client)
    r = anon_client.post("/auth/login", data={"email": "gv@test.vn", "password": "sai", "_csrf": token},
                         follow_redirects=False)
    assert r.status_code == 401
    assert "không đúng" in r.text


def test_login_dung_tao_phien_va_vao_duoc_trang_rieng(anon_client, teacher_and_class):
    token = csrf_of(anon_client)
    r = anon_client.post("/auth/login", data={"email": "gv@test.vn", "password": PASSWORD, "_csrf": token},
                         follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/me"
    cookie = r.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "samesite=lax" in cookie.lower()
    assert "Max-Age=28800" in cookie  # 8 giờ theo F1

    me = anon_client.get("/me")
    assert me.status_code == 200
    assert "Giáo viên Test" in me.text


def test_chua_dang_nhap_bi_dua_ve_trang_login(anon_client):
    r = anon_client.get("/me", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/auth/login"


def test_dang_ky_thanh_cong_tao_hoc_sinh_va_ghi_danh(anon_client, teacher_and_class, db):
    token = csrf_of(anon_client)
    payload = {"email": "hs1@test.vn", "password": PASSWORD, "full_name": "Học Sinh Một",
               "join_code": "TEST01", "_csrf": token}
    r = anon_client.post("/auth/register", data=payload, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/placement"  # AC1.3

    student = db.execute(select(User).where(User.email == "hs1@test.vn")).scalar_one()
    assert student.role == "student"
    assert student.password_hash.startswith("$2b$")  # bcrypt
    assert db.execute(select(Enrollment).where(Enrollment.student_id == student.id)).scalar_one()


def test_dang_ky_trung_email_tra_409(anon_client, teacher_and_class, db):
    token = csrf_of(anon_client)
    base = {"password": PASSWORD, "full_name": "Trùng", "join_code": "TEST01", "_csrf": token}
    anon_client.post("/auth/register", data={**base, "email": "hsdup@test.vn"}, follow_redirects=False)
    r = anon_client.post("/auth/register", data={**base, "email": "hsdup@test.vn"}, follow_redirects=False)
    assert r.status_code == 409
    assert "đã được đăng ký" in r.text


def test_ma_lop_sai_khong_tao_tai_khoan(anon_client, teacher_and_class, db):
    token = csrf_of(anon_client)
    payload = {"email": "hs2@test.vn", "password": PASSWORD, "full_name": "Mã Sai",
               "join_code": "SAIMA", "_csrf": token}
    r = anon_client.post("/auth/register", data=payload, follow_redirects=False)
    assert r.status_code == 422
    assert db.execute(select(User).where(User.email == "hs2@test.vn")).scalar_one_or_none() is None


def test_thieu_csrf_bi_tu_choi(anon_client, teacher_and_class):
    anon_client.get("/auth/login")
    r = anon_client.post("/auth/login", data={"email": "gv@test.vn", "password": PASSWORD},
                         follow_redirects=False)
    assert r.status_code == 403


def test_dang_xuat_xoa_phien_trong_csdl(anon_client, teacher_and_class, db):
    token = csrf_of(anon_client)
    anon_client.post("/auth/login", data={"email": "gv@test.vn", "password": PASSWORD, "_csrf": token},
                     follow_redirects=False)
    sid = anon_client.cookies.get("sid")
    assert db.execute(select(Session).where(Session.token == sid)).scalar_one_or_none() is not None

    r = anon_client.post("/auth/logout", data={"_csrf": csrf_of(anon_client)}, follow_redirects=False)
    assert r.status_code == 303
    # Thu hồi thật ở server, không chỉ xoá cookie ở trình duyệt
    assert db.execute(select(Session).where(Session.token == sid)).scalar_one_or_none() is None
    assert anon_client.get("/me", follow_redirects=False).status_code == 303
