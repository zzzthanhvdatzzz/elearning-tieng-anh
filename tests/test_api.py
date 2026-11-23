"""Test lớp JSON cho Next.js — /api/* (khác router HTML ở chỗ trả 401 thay vì chuyển hướng)."""
from sqlalchemy import select

from app.models import Lesson, Unit

HDR = {"X-Requested-With": "fetch"}


def _login(client, email):
    return client.post("/api/auth/login", json={"email": email, "password": "matkhau123"}, headers=HDR)


def test_api_chua_dang_nhap_tra_401_json(anon_client):
    r = anon_client.get("/api/units")
    assert r.status_code == 401
    assert r.json()["detail"] == "Chưa đăng nhập"


def test_api_login_dung_va_sai(student, anon_client):
    bad = anon_client.post("/api/auth/login", json={"email": student.email, "password": "sai"}, headers=HDR)
    assert bad.status_code == 401

    ok = _login(anon_client, student.email)
    assert ok.status_code == 200
    body = ok.json()
    assert body["role"] == "student" and body["full_name"] == "Học Sinh Test"
    assert "sid" in anon_client.cookies

    me = anon_client.get("/api/me")
    assert me.status_code == 200 and me.json()["email"] == student.email


def test_api_thieu_header_csrf_bi_chan(student, anon_client):
    r = anon_client.post("/api/auth/login", json={"email": student.email, "password": "matkhau123"})
    assert r.status_code == 403


def test_api_units_va_bai_hoc(student, anon_client, db):
    from app.seed import ensure_demo_unit

    ensure_demo_unit(db)
    _login(anon_client, student.email)

    units = anon_client.get("/api/units").json()
    assert units["units"][0]["title"] == "Local Environment"

    lesson = units["units"][0]["lessons"][0]
    detail = anon_client.get(f"/api/lessons/{lesson['id']}").json()
    assert detail["question_count"] == 10
    assert detail["content"]["vocab"]


def test_api_luyen_tap_khong_lo_dap_an_va_cham_dung(student, anon_client, db):
    from app.seed import ensure_demo_unit

    ensure_demo_unit(db)
    _login(anon_client, student.email)

    unit = db.execute(select(Unit).where(Unit.grade == 8)).scalars().first()
    lesson = db.execute(select(Lesson).where(Lesson.unit_id == unit.id,
                                             Lesson.code == "U1-L1")).scalar_one()

    exam = anon_client.get(f"/api/practice/{lesson.id}")
    assert exam.status_code == 200
    assert "correct_key" not in exam.text

    answers = {str(q["id"]): "A" for q in exam.json()["questions"]}
    r = anon_client.post(f"/api/practice/{lesson.id}/submit", json={"answers": answers}, headers=HDR)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 10
    assert body["score"] is not None
    assert all("correct_key" in item for item in body["review"])  # chỉ lộ sau khi nộp
