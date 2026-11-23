"""Test nối bài giao ↔ luồng làm bài và BR8 (nộp muộn trừ điểm).

Đây là lỗi kiến trúc đã sửa: trước đây học sinh làm trên assignment tự sinh nên hạn nộp
và số lượt giáo viên đặt không có tác dụng.
"""
from datetime import datetime, timedelta

from sqlalchemy import select

from app.models import Assignment, Class, Lesson, Submission, Unit
from app.services.security import hash_password
from app.models import User
from tests.conftest import PASSWORD, client_for, csrf_of


def _setup(db):
    from app.seed import ensure_demo_unit

    ensure_demo_unit(db)
    unit = db.execute(select(Unit).where(Unit.grade == 8)).scalars().first()
    lesson = db.execute(select(Lesson).where(Lesson.unit_id == unit.id,
                                             Lesson.code == "U1-L1")).scalar_one()
    klass = db.execute(select(Class).where(Class.join_code == "TEST01")).scalar_one()
    teacher = db.execute(select(User).where(User.role == "teacher")).scalars().first()
    return lesson, klass, teacher


def _answers(lesson) -> dict:
    return {f"q_{q.id}": q.correct_key for q in lesson.questions}


def _teacher_assignment(db, klass, teacher, lesson, *, deadline, max_attempts):
    a = Assignment(class_id=klass.id, teacher_id=teacher.id, kind="practice",
                   lesson_id=lesson.id, title="Bài giao của giáo viên",
                   deadline=deadline, max_attempts=max_attempts,
                   weight_auto=1.0, weight_teacher=0.0)
    db.add(a)
    db.commit()
    return a


def test_hoc_sinh_lam_bai_tren_dung_bai_giao_cua_giao_vien(student, db, student_client):
    lesson, klass, teacher = _setup(db)
    deadline = datetime.utcnow() + timedelta(days=2)
    a = _teacher_assignment(db, klass, teacher, lesson, deadline=deadline, max_attempts=1)

    data = _answers(lesson)
    data["_csrf"] = csrf_of(student_client)
    r = student_client.post(f"/practice/{lesson.id}/submit", data=data, follow_redirects=False)
    assert r.status_code == 303

    sub = db.execute(select(Submission)).scalars().first()
    assert sub.assignment_id == a.id, "bài nộp phải gắn vào bài giao, không phải assignment tự sinh"
    assert sub.late_days == 0


def test_so_lan_lam_theo_cau_hinh_bai_giao(student, db, student_client):
    lesson, klass, teacher = _setup(db)
    _teacher_assignment(db, klass, teacher, lesson,
                        deadline=datetime.utcnow() + timedelta(days=1), max_attempts=1)

    data = _answers(lesson)
    data["_csrf"] = csrf_of(student_client)
    assert student_client.post(f"/practice/{lesson.id}/submit", data=data,
                               follow_redirects=False).status_code == 303
    # Bài giao chỉ cho 1 lượt → lượt 2 bị chặn, dù assignment tự sinh cho 3 lượt
    r2 = student_client.post(f"/practice/{lesson.id}/submit", data=data, follow_redirects=False)
    assert r2.status_code == 409
    assert "hết lượt" in r2.text


def test_nop_muon_bi_tru_10_phan_tram_moi_ngay(student, db, student_client):
    lesson, klass, teacher = _setup(db)
    past = datetime.utcnow() - timedelta(days=2, hours=1)
    _teacher_assignment(db, klass, teacher, lesson, deadline=past, max_attempts=3)

    data = _answers(lesson)
    data["_csrf"] = csrf_of(student_client)
    student_client.post(f"/practice/{lesson.id}/submit", data=data, follow_redirects=False)

    sub = db.execute(select(Submission)).scalars().first()
    # Deadline cách đây 2 ngày 1 giờ → làm tròn LÊN thành 3 ngày trễ (trễ 1 giây vẫn tính 1 ngày)
    assert sub.late_days == 3
    assert sub.auto_score == 10.0
    assert sub.final_score == 7.0        # 10 − 10% × 3 ngày


def test_qua_ba_ngay_nop_muon_nhan_0(student, db, student_client):
    lesson, klass, teacher = _setup(db)
    past = datetime.utcnow() - timedelta(days=5)
    _teacher_assignment(db, klass, teacher, lesson, deadline=past, max_attempts=3)

    data = _answers(lesson)
    data["_csrf"] = csrf_of(student_client)
    student_client.post(f"/practice/{lesson.id}/submit", data=data, follow_redirects=False)

    sub = db.execute(select(Submission)).scalars().first()
    assert sub.late_days >= 4
    assert sub.final_score == 0.0


def test_bai_viet_nop_muon_cung_bi_tru_khi_giao_vien_cham(student, db, student_client, teacher_client):
    from app.services.writing import ensure_writing_assignment

    lesson, klass, teacher = _setup(db)
    a = ensure_writing_assignment(db, klass, lesson)
    a.deadline = datetime.utcnow() - timedelta(days=1, hours=2)
    db.commit()

    essay = ("My neighbourhood is quiet. There is a market and a temple. People are friendly "
             "and the air is clean, so I like living here very much.")
    r = student_client.post(f"/writing/{lesson.id}/submit",
                           data={"text": essay, "_csrf": csrf_of(student_client)},
                           follow_redirects=False)
    assert r.status_code == 303

    sub = db.execute(select(Submission).order_by(Submission.id.desc())).scalars().first()
    assert sub.late_days == 2            # 1 ngày 2 giờ → làm tròn lên 2 ngày

    # chấm 10/10 nhưng nộp muộn 2 ngày → còn 8.0
    teacher_client.post(f"/teacher/writing/{sub.id}/grade",
                        data={"task": 2.5, "grammar": 2.5, "vocab": 2.5, "coherence": 2.5,
                              "comment": "Tốt.", "_csrf": csrf_of(teacher_client)},
                        follow_redirects=False)
    db.expire_all()
    sub = db.get(Submission, sub.id)
    assert sub.teacher_score == 10.0
    assert sub.final_score == 8.0
