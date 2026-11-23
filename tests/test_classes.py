"""Test F10/F11 — tạo lớp, mã tham gia 6 ký tự, ghi danh BR2, giao bài có deadline (AC10.x, AC11.x)."""
from datetime import datetime, timedelta

from sqlalchemy import select

from app.models import Assignment, Class, Enrollment, User
from tests.conftest import csrf_of


def test_giao_vien_tao_lop_sinh_ma_6_ky_tu(teacher_client, teacher_and_class, db):
    r = teacher_client.post("/teacher/classes",
                            data={"name": "9A1 — Tiếng Anh", "grade": "8", "_csrf": csrf_of(teacher_client)},
                            follow_redirects=False)
    assert r.status_code == 303
    new = db.execute(select(Class).where(Class.name == "9A1 — Tiếng Anh")).scalar_one()
    assert len(new.join_code) == 6
    assert new.join_code.isalnum()
    assert new.teacher_id == teacher_and_class.id


def test_chi_ho_tro_khoi_8_va_10(teacher_client, teacher_and_class):
    r = teacher_client.post("/teacher/classes",
                            data={"name": "Lớp 12", "grade": "12", "_csrf": csrf_of(teacher_client)},
                            follow_redirects=False)
    assert r.status_code == 422


def test_them_hoc_sinh_bang_email_va_chan_trung_lop(teacher_client, teacher_and_class, db):
    klass = db.execute(select(Class).where(Class.join_code == "TEST01")).scalar_one()
    from app.services.security import hash_password

    s = User(email="them@test.vn", password_hash=hash_password("matkhau123"),
             full_name="HS Thêm", role="student")
    db.add(s)
    db.commit()

    r = teacher_client.post(f"/teacher/classes/{klass.id}/students",
                            data={"email": "them@test.vn", "_csrf": csrf_of(teacher_client)},
                            follow_redirects=True)
    assert r.status_code == 200
    assert db.execute(select(Enrollment).where(Enrollment.student_id == s.id)).scalar_one()

    # Thêm lần hai → báo đã ở trong lớp
    r2 = teacher_client.post(f"/teacher/classes/{klass.id}/students",
                             data={"email": "them@test.vn", "_csrf": csrf_of(teacher_client)},
                             follow_redirects=True)
    assert "đã ở trong lớp" in r2.text


def test_br2_hoc_sinh_khong_thuoc_hai_lop(teacher_client, teacher_and_class, db):
    from app.services.security import hash_password

    s = User(email="br2@test.vn", password_hash=hash_password("matkhau123"),
             full_name="HS BR2", role="student")
    db.add(s)
    db.commit()
    # tạo lớp thứ hai rồi thử thêm học sinh đã ở lớp TEST01
    klass2 = Class(name="Lớp Hai", grade=8, join_code="SECOND", teacher_id=teacher_and_class.id)
    db.add(klass2)
    db.commit()

    r = teacher_client.post(f"/teacher/classes/{klass2.id}/students",
                            data={"email": "br2@test.vn", "_csrf": csrf_of(teacher_client)},
                            follow_redirects=True)
    # học sinh này chưa thuộc lớp nào → thêm được (đối chứng)
    assert db.execute(select(Enrollment).where(Enrollment.student_id == s.id)).scalar_one() is not None

    klass1 = db.execute(select(Class).where(Class.join_code == "TEST01")).scalar_one()
    r2 = teacher_client.post(f"/teacher/classes/{klass1.id}/students",
                             data={"email": "br2@test.vn", "_csrf": csrf_of(teacher_client)},
                             follow_redirects=True)
    assert "lớp khác" in r2.text          # BR2 chặn
    assert len(db.execute(select(Enrollment).where(Enrollment.student_id == s.id)).scalars().all()) == 1


def test_giao_vien_khac_khong_vao_duoc_lop(teacher_and_class, other_teacher, db):
    from tests.conftest import client_for

    klass = db.execute(select(Class).where(Class.join_code == "TEST01")).scalar_one()
    c = client_for(other_teacher.email)
    assert c.get(f"/teacher/classes/{klass.id}").status_code == 404


def test_giao_bai_co_deadline_va_so_lan_lam(teacher_client, teacher_and_class, db):
    from app.seed import ensure_demo_unit
    from app.models import Lesson, Unit

    ensure_demo_unit(db)
    klass = db.execute(select(Class).where(Class.join_code == "TEST01")).scalar_one()
    unit = db.execute(select(Unit).where(Unit.grade == 8)).scalars().first()
    lesson = db.execute(select(Lesson).where(Lesson.unit_id == unit.id, Lesson.code == "U1-L1")).scalar_one()
    deadline = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")

    r = teacher_client.post(
        f"/teacher/classes/{klass.id}/assignments",
        data={"title": "Luyện tập U1-L1", "lesson_id": str(lesson.id), "deadline": deadline,
              "max_attempts": "2", "kind": "practice", "_csrf": csrf_of(teacher_client)},
        follow_redirects=False)
    assert r.status_code == 303

    a = db.execute(select(Assignment).where(Assignment.title == "Luyện tập U1-L1")).scalar_one()
    assert a.max_attempts == 2
    assert a.deadline is not None and a.deadline > datetime.now()
    assert a.class_id == klass.id


def test_deadline_trong_qua_khu_bi_tu_choi(teacher_client, teacher_and_class, db):
    klass = db.execute(select(Class).where(Class.join_code == "TEST01")).scalar_one()
    past = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
    r = teacher_client.post(
        f"/teacher/classes/{klass.id}/assignments",
        data={"title": "Bài quá hạn", "lesson_id": "0", "deadline": past, "max_attempts": "1",
              "kind": "practice", "_csrf": csrf_of(teacher_client)},
        follow_redirects=True)
    assert "Hạn nộp phải ở tương lai" in r.text


def test_hoc_sinh_thay_bai_duoc_giao(teacher_client, student, student_client, teacher_and_class, db):
    klass = db.execute(select(Class).where(Class.join_code == "TEST01")).scalar_one()
    db.add(Assignment(class_id=klass.id, teacher_id=teacher_and_class.id, kind="practice",
                      title="Bài về nhà tuần 1", max_attempts=2, weight_auto=1.0))
    db.commit()

    r = student_client.get("/assignments")
    assert r.status_code == 200
    assert "Bài về nhà tuần 1" in r.text
    assert "0/2" in r.text


def test_hoc_sinh_khong_tao_duoc_lop(student, student_client):
    r = student_client.post("/teacher/classes",
                            data={"name": "Lậu", "grade": "8", "_csrf": csrf_of(student_client)},
                            follow_redirects=False)
    assert r.status_code == 403
