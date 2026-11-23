"""Test D2 — lộ trình Unit, trang học bài, cộng dồn tiến độ (F5, F6, US5, US6)."""
import json

from sqlalchemy import select

from app.models import Class, Enrollment, Lesson, Progress, Unit, User
from app.services.security import hash_password
from tests.conftest import PASSWORD, csrf_of, client_for, login


def _lesson_of_grade(db, grade: int, code: str) -> Lesson:
    unit = db.execute(select(Unit).where(Unit.grade == grade)).scalars().first()
    return db.execute(select(Lesson).where(Lesson.unit_id == unit.id, Lesson.code == code)).scalar_one()


def _student_in_grade(db, email: str, klass: Class) -> User:
    s = User(email=email, password_hash=hash_password(PASSWORD), full_name="HS " + email, role="student")
    db.add(s)
    db.flush()
    db.add(Enrollment(class_id=klass.id, student_id=s.id))
    db.commit()
    return s


def test_lo_trinh_hien_thi_unit_cua_dung_khoi_lop(student, db, student_client, teacher_and_class):
    from app.seed import ensure_demo_unit

    ensure_demo_unit(db)
    r = student_client.get("/units")
    assert r.status_code == 200
    assert "Local Environment" in r.text
    assert r.text.count("/lessons/") >= 6  # 6 bài của Unit 1


def test_bai_cua_khoi_lop_khac_tra_404(student, db, student_client, teacher_and_class):
    """Học sinh lớp 8 không mở được bài lớp 10 (chống IDOR)."""
    from app.seed import ensure_demo_unit

    ensure_demo_unit(db)
    unit10 = Unit(grade=10, code="U1-10", title="Family Life", order_no=1)
    db.add(unit10)
    db.flush()
    l10 = Lesson(unit_id=unit10.id, code="10-U1-L1", title="Family Life", skill="vocab",
                 content=json.dumps({"objectives": ["x"], "minutes": 10}), order_no=1)
    db.add(l10)
    db.commit()

    assert student_client.get(f"/lessons/{l10.id}").status_code == 404


def test_trang_hoc_bai_hien_thi_noi_dung(student, db, student_client):
    from app.seed import ensure_demo_unit

    ensure_demo_unit(db)
    lesson = _lesson_of_grade(db, 8, "U1-L1")
    r = student_client.get(f"/lessons/{lesson.id}")
    assert r.status_code == 200
    assert "Mục tiêu bài học" in r.text
    assert "Từ vựng" in r.text
    assert lesson.transcript in r.text


def test_ghi_tien_do_cong_don_giay_va_giu_percent_lon_nhat(student, db, student_client):
    from app.seed import ensure_demo_unit

    ensure_demo_unit(db)
    lesson = _lesson_of_grade(db, 8, "U1-L1")
    token = csrf_of(student_client)

    r1 = student_client.post(f"/lessons/{lesson.id}/progress",
                             json={"seconds": 120, "percent": 20},
                             headers={"X-CSRF-Token": token})
    assert r1.status_code == 200, r1.text
    assert r1.json()["seconds"] == 120 and r1.json()["percent"] == 20

    # Lần 2: cộng dồn giây, phần trăm KHÔNG bị giảm
    r2 = student_client.post(f"/lessons/{lesson.id}/progress",
                             json={"seconds": 60, "percent": 10},
                             headers={"X-CSRF-Token": token})
    assert r2.json()["seconds"] == 180
    assert r2.json()["percent"] == 20


def test_phan_tram_bi_kep_trong_0_100(student, db, student_client):
    from app.seed import ensure_demo_unit

    ensure_demo_unit(db)
    lesson = _lesson_of_grade(db, 8, "U1-L1")
    token = csrf_of(student_client)
    r = student_client.post(f"/lessons/{lesson.id}/progress",
                            json={"seconds": 999999, "percent": 500},
                            headers={"X-CSRF-Token": token})
    body = r.json()
    assert body["percent"] == 100
    assert body["seconds"] == 3600  # chặn client gửi số giây vô lý


def test_danh_dau_hoan_thanh_thi_lo_trinh_hien_dau_tich(student, db, student_client):
    from app.seed import ensure_demo_unit

    ensure_demo_unit(db)
    lesson = _lesson_of_grade(db, 8, "U1-L2")
    token = csrf_of(student_client)
    student_client.post(f"/lessons/{lesson.id}/progress",
                        json={"seconds": 30, "completed": True},
                        headers={"X-CSRF-Token": token})

    r = student_client.get("/units")
    assert "✓ đã học" in r.text
    assert db.execute(select(Progress).where(Progress.lesson_id == lesson.id)).scalar_one().percent == 100


def test_giao_vien_khong_ghi_duoc_tien_do_hoc_sinh(student, db, teacher_client):
    from app.seed import ensure_demo_unit

    ensure_demo_unit(db)
    lesson = _lesson_of_grade(db, 8, "U1-L1")
    r = teacher_client.post(f"/lessons/{lesson.id}/progress",
                            json={"seconds": 10}, headers={"X-CSRF-Token": csrf_of(teacher_client)})
    assert r.status_code == 403


def test_thieu_csrf_khi_ghi_tien_do_bi_tu_choi(student, db, student_client):
    from app.seed import ensure_demo_unit

    ensure_demo_unit(db)
    lesson = _lesson_of_grade(db, 8, "U1-L1")
    r = student_client.post(f"/lessons/{lesson.id}/progress", json={"seconds": 10})
    assert r.status_code == 403


def test_bai_tiep_theo_la_bai_dau_tien_chua_xong(student, db, student_client):
    from app.seed import ensure_demo_unit

    ensure_demo_unit(db)
    r = student_client.get("/units")
    assert "Bài tiếp theo" in r.text
    assert "Getting Started" in r.text  # bài 1 chưa học
