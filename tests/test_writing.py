"""Test F8 + F12 (phần bài viết) — nháp/đếm từ phía client, nộp, chấm rubric (AC8.x, AC12.x)."""
from sqlalchemy import select

from app.models import Lesson, RubricScore, Submission, Unit
from app.services.security import hash_password
from app.models import User
from tests.conftest import PASSWORD, csrf_of, client_for, login

ESSAY = ("My neighbourhood is small but very friendly. There is a market near my house "
         "where my mother buys fresh fish every morning. A small temple stands at the end "
         "of the street and children often play there in the afternoon. I like living here "
         "because people know each other and always say hello.")


def _setup(db):
    from app.seed import ensure_demo_unit

    ensure_demo_unit(db)
    unit = db.execute(select(Unit).where(Unit.grade == 8)).scalars().first()
    return db.execute(select(Lesson).where(Lesson.unit_id == unit.id, Lesson.code == "U1-L6")).scalar_one()


def _submit(client, lesson_id, text):
    return client.post(f"/writing/{lesson_id}/submit",
                       data={"text": text, "_csrf": csrf_of(client)}, follow_redirects=False)


def test_trang_luyen_viet_co_de_bai_va_dem_tu(student, db, student_client):
    lesson = _setup(db)
    r = student_client.get(f"/writing/{lesson.id}")
    assert r.status_code == 200
    assert "Đề bài" in r.text
    assert 'id="wc"' in r.text          # đếm từ
    assert "localStorage" in r.text     # nháp tự lưu


def test_bai_qua_ngan_bi_tu_choi(student, db, student_client):
    lesson = _setup(db)
    r = _submit(student_client, lesson.id, "Hello world")
    assert r.status_code == 422
    assert "quá ngắn" in r.text
    assert db.execute(select(Submission)).scalars().first() is None


def test_nop_bai_du_dai_thi_vao_hang_doi_cho_cham(student, db, student_client):
    lesson = _setup(db)
    r = _submit(student_client, lesson.id, ESSAY)
    assert r.status_code == 303
    sub = db.execute(select(Submission)).scalars().first()
    assert sub.status == "awaiting_teacher"
    assert sub.text_content.startswith("My neighbourhood")
    assert sub.final_score is None


def test_giao_vien_cham_rubric_tra_diem_va_nhan_xet(student, db, student_client, teacher_client):
    lesson = _setup(db)
    _submit(student_client, lesson.id, ESSAY)
    sub = db.execute(select(Submission)).scalars().first()

    queue = teacher_client.get("/teacher/writing")
    assert queue.status_code == 200
    assert f"/teacher/writing/{sub.id}" in queue.text

    r = teacher_client.post(
        f"/teacher/writing/{sub.id}/grade",
        data={"task": 2.5, "grammar": 2.0, "vocab": 2.0, "coherence": 1.5,
              "comment": "Diễn đạt rõ, thêm ví dụ sẽ tốt hơn.", "_csrf": csrf_of(teacher_client)},
        follow_redirects=False,
    )
    assert r.status_code == 303

    db.expire_all()
    sub = db.get(Submission, sub.id)
    assert sub.status == "graded"
    assert sub.teacher_score == 8.0
    assert sub.final_score == 8.0       # bài viết: trọng số 0/1 → điểm cuối = rubric
    assert len(db.execute(select(RubricScore)).scalars().all()) == 4

    # Học sinh thấy điểm + nhận xét (AC12.3)
    page = student_client.get(f"/writing/{lesson.id}/result")
    assert "8.0" in page.text
    assert "Diễn đạt rõ" in page.text


def test_diem_duoi_5_khong_nhan_xet_thi_khong_luu(student, db, student_client, teacher_client):
    lesson = _setup(db)
    _submit(student_client, lesson.id, ESSAY)
    sub = db.execute(select(Submission)).scalars().first()

    r = teacher_client.post(
        f"/teacher/writing/{sub.id}/grade",
        data={"task": 1.0, "grammar": 1.0, "vocab": 1.0, "coherence": 1.0,
              "comment": "", "_csrf": csrf_of(teacher_client)},
        follow_redirects=False,
    )
    assert r.status_code == 422
    assert "bắt buộc nhập nhận xét" in r.text
    db.expire_all()
    assert db.get(Submission, sub.id).status == "awaiting_teacher"


def test_cham_lai_bai_da_cham_bi_tu_choi(student, db, student_client, teacher_client):
    lesson = _setup(db)
    _submit(student_client, lesson.id, ESSAY)
    sub = db.execute(select(Submission)).scalars().first()
    data = {"task": 2.0, "grammar": 2.0, "vocab": 2.0, "coherence": 2.0,
            "comment": "Tốt.", "_csrf": csrf_of(teacher_client)}
    teacher_client.post(f"/teacher/writing/{sub.id}/grade", data=data, follow_redirects=False)
    r = teacher_client.post(f"/teacher/writing/{sub.id}/grade", data=data, follow_redirects=False)
    assert r.status_code == 422
    assert "đã chấm" in r.text


def test_giao_vien_lop_khac_khong_cham_duoc(student, db, student_client, other_teacher):
    lesson = _setup(db)
    _submit(student_client, lesson.id, ESSAY)
    sub = db.execute(select(Submission)).scalars().first()

    c = client_for(other_teacher.email)
    assert c.get(f"/teacher/writing/{sub.id}").status_code == 403


def test_hoc_sinh_khong_vao_duoc_hang_doi_cham_bai_viet(student, db, student_client):
    lesson = _setup(db)
    assert student_client.get("/teacher/writing", follow_redirects=False).status_code == 403
