"""Test tự đổi mật khẩu và phân trang danh sách tài khoản."""
from sqlalchemy import select

from app.models import Session as LoginSession
from app.models import User
from app.services.security import hash_password
from tests.conftest import PASSWORD, client_for, csrf_of, login


def test_doi_mat_khau_thanh_cong_va_dang_xuat_thiet_bi_khac(student, db):
    c1 = client_for(student.email)
    c2 = client_for(student.email)          # thiết bị thứ hai
    assert c1.get("/api/me").status_code == 200
    assert c2.get("/api/me").status_code == 200

    r = c1.post("/api/auth/password",
                json={"old_password": PASSWORD, "new_password": "MatKhauMoi123"},
                headers={"X-Requested-With": "fetch"})
    assert r.status_code == 200
    assert "đã đổi" in r.json()["message"].lower()

    # Thiết bị đang thao tác vẫn dùng được
    assert c1.get("/api/me").status_code == 200
    # Thiết bị khác bị đẩy ra
    assert c2.get("/api/me").status_code == 401

    db.expire_all()
    from app.services.security import verify_password

    assert verify_password("MatKhauMoi123", db.get(User, student.id).password_hash)


def test_sai_mat_khau_cu_bi_tu_choi(student, db):
    c = client_for(student.email)
    r = c.post("/api/auth/password",
               json={"old_password": "sai-hoan-toan", "new_password": "MatKhauMoi123"},
               headers={"X-Requested-With": "fetch"})
    assert r.status_code == 400
    assert "không đúng" in r.json()["detail"].lower()


def test_mat_khau_moi_qua_ngan_hoac_trung_cu(student, db):
    c = client_for(student.email)
    short = c.post("/api/auth/password",
                   json={"old_password": PASSWORD, "new_password": "abc123"},
                   headers={"X-Requested-With": "fetch"})
    assert short.status_code == 400 and "8 ký tự" in short.json()["detail"]

    same = c.post("/api/auth/password",
                  json={"old_password": PASSWORD, "new_password": PASSWORD},
                  headers={"X-Requested-With": "fetch"})
    assert same.status_code == 400 and "khác" in same.json()["detail"]


def test_doi_mat_khau_dang_nhap_lai_bang_mat_khau_moi(student, db, anon_client):
    c = client_for(student.email)
    c.post("/api/auth/password", json={"old_password": PASSWORD, "new_password": "MatKhauMoi123"},
           headers={"X-Requested-With": "fetch"})
    login(anon_client, student.email, "MatKhauMoi123")
    assert anon_client.get("/api/me").status_code == 200


def test_phan_trang_danh_sach_tai_khoan(db):
    from app.models import User as U

    admin = U(email="admin@pt.vn", password_hash=hash_password(PASSWORD),
              full_name="Quản trị PT", role="admin")
    db.add(admin)
    db.commit()
    admin_client = client_for("admin@pt.vn")

    for i in range(7):
        db.add(User(email=f"hs.pt{i}@truong.edu.vn", full_name=f"PT {i}", role="student",
                    password_hash=hash_password(PASSWORD)))
    db.commit()

    d = admin_client.get("/api/admin/users?page=1&size=5").json()
    assert d["size"] == 5 and len(d["items"]) == 5
    assert d["total"] >= 8 and d["pages"] >= 2

    d2 = admin_client.get("/api/admin/users?page=2&size=5").json()
    assert d2["page"] == 2
    assert {x["email"] for x in d["items"]}.isdisjoint({x["email"] for x in d2["items"]})

    # trang vượt quá bị kẹp về trang cuối, không trả rỗng khó hiểu
    d3 = admin_client.get("/api/admin/users?page=999&size=5").json()
    assert d3["page"] == d3["pages"] and d3["items"]
