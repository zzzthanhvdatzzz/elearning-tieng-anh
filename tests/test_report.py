"""Test F13/F14 — báo cáo học sinh, báo cáo lớp, CSV, phân quyền (ma trận 3.12)."""
from sqlalchemy import select

from app.models import Lesson, Unit
from app.services.security import hash_password
from app.models import User
from tests.conftest import PASSWORD, csrf_of, client_for


def _l1(db) -> Lesson:
    from app.seed import ensure_demo_unit

    ensure_demo_unit(db)
    unit = db.execute(select(Unit).where(Unit.grade == 8)).scalars().first()
    return db.execute(select(Lesson).where(Lesson.unit_id == unit.id, Lesson.code == "U1-L1")).scalar_one()


def _submit_all_wrong(client, db, lesson):
    data = {f"q_{q.id}": ("B" if q.correct_key != "B" else "A") for q in lesson.questions}
    data["_csrf"] = csrf_of(client)
    client.post(f"/practice/{lesson.id}/submit", data=data, follow_redirects=False)


def _submit_all_right(client, db, lesson):
    data = {f"q_{q.id}": q.correct_key for q in lesson.questions}
    data["_csrf"] = csrf_of(client)
    client.post(f"/practice/{lesson.id}/submit", data=data, follow_redirects=False)


def test_hoc_sinh_xem_bao_cao_cua_minh(student, db, student_client):
    lesson = _l1(db)
    _submit_all_right(student_client, db, lesson)

    r = student_client.get(f"/reports/student/{student.id}")
    assert r.status_code == 200
    assert "Điểm theo kỹ năng" in r.text
    assert "10.0" in r.text
    assert "đã chấm" in r.text


def test_hoc_sinh_khac_khong_xem_duoc_bao_cao(student, db, student_client):
    from app.services.classes import _new_join_code  # noqa: F401

    other = User(email="khac@test.vn", password_hash=hash_password(PASSWORD),
                 full_name="HS Khác", role="student")
    db.add(other)
    db.commit()
    r = student_client.get(f"/reports/student/{other.id}")
    assert r.status_code == 403


def test_giao_vien_lop_xem_duoc_bao_cao_hoc_sinh(student, db, student_client, teacher_client):
    lesson = _l1(db)
    _submit_all_right(student_client, db, lesson)
    r = teacher_client.get(f"/reports/student/{student.id}")
    assert r.status_code == 200


def test_giao_vien_lop_khac_bi_chan(student, db, student_client, other_teacher):
    c = client_for(other_teacher.email)
    assert c.get(f"/reports/student/{student.id}").status_code == 403


def test_bao_cao_lop_liet_ke_hoc_sinh_can_can_thiep(student, db, student_client, teacher_client):
    lesson = _l1(db)
    _submit_all_wrong(student_client, db, lesson)   # 0.0 điểm → dưới ngưỡng 5.0

    r = teacher_client.get("/teacher/classes")
    assert r.status_code == 200
    from app.models import Class

    klass = db.execute(select(Class).where(Class.join_code == "TEST01")).scalar_one()

    page = teacher_client.get(f"/reports/class/{klass.id}")
    assert page.status_code == 200
    assert "Cần can thiệp" in page.text
    assert "Học Sinh Test" in page.text


def test_xuat_csv_co_tieu_de_va_du_lieu(student, db, student_client, teacher_client):
    from app.models import Class

    lesson = _l1(db)
    _submit_all_right(student_client, db, lesson)
    klass = db.execute(select(Class).where(Class.join_code == "TEST01")).scalar_one()

    r = teacher_client.get(f"/reports/class/{klass.id}/export.csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    body = r.text
    assert body.splitlines()[0].startswith("Học sinh,Email")
    assert "hs@test.vn" in body


def test_hoc_sinh_khong_xuat_duoc_csv(student, db, student_client):
    from app.models import Class

    klass = db.execute(select(Class).where(Class.join_code == "TEST01")).scalar_one()
    assert student_client.get(f"/reports/class/{klass.id}/export.csv",
                              follow_redirects=False).status_code == 403
