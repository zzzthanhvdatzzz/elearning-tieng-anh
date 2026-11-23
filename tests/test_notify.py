"""Test thông báo trong ứng dụng.

Bảng `notifications` có từ đầu nhưng chưa nơi nào hiển thị; test này khoá lại hành vi:
sự kiện thật (giáo viên chấm bài, giao bài, duyệt phụ huynh) phải sinh thông báo,
và mỗi người chỉ đọc được thông báo của chính mình.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.models import Assignment, Class, Enrollment, Notification, Submission, User
from app.seed import ensure_demo_unit


def _lesson(db, code="U1-L1"):
    from app.models import Lesson, Unit

    ensure_demo_unit(db)
    unit = db.execute(select(Unit).where(Unit.grade == 8)).scalars().first()
    return db.execute(select(Lesson).where(Lesson.unit_id == unit.id,
                                           Lesson.code == code)).scalar_one()


def _class_of(db, student_id):
    return db.execute(
        select(Class).join(Enrollment, Enrollment.class_id == Class.id)
        .where(Enrollment.student_id == student_id)
    ).scalars().first()


def test_giao_vien_cham_bai_sinh_thong_bao_cho_hoc_sinh(student, db, student_client, teacher_client):
    from app.services.writing import ensure_writing_assignment
    from tests.conftest import csrf_of

    lesson = _lesson(db)
    klass = _class_of(db, student.id)
    ensure_writing_assignment(db, klass, lesson)
    essay = ("My neighbourhood is quiet and clean. There is a small market near my house, "
             "and people here are very friendly to each other.")
    student_client.post(f"/writing/{lesson.id}/submit",
                        data={"text": essay, "_csrf": csrf_of(student_client)},
                        follow_redirects=False)
    sub = db.execute(select(Submission).order_by(Submission.id.desc())).scalars().first()

    db.query(Notification).delete()
    db.commit()

    teacher_client.post(f"/teacher/writing/{sub.id}/grade",
                        data={"task": 2, "grammar": 2, "vocab": 2, "coherence": 2,
                              "comment": "Khá tốt.", "_csrf": csrf_of(teacher_client)},
                        follow_redirects=False)

    notes = db.execute(select(Notification).where(Notification.user_id == student.id)).scalars().all()
    assert len(notes) == 1
    assert "đã được chấm" in notes[0].title
    assert "8.0" in notes[0].body


def test_api_thong_bao_doc_va_danh_dau(student, db, student_client):
    from app.services import notify

    db.query(Notification).delete()
    db.commit()
    notify.push(db, student.id, "Thông báo A", "nội dung A")
    notify.push(db, student.id, "Thông báo B", "nội dung B")
    db.commit()

    r = student_client.get("/api/notifications")
    assert r.status_code == 200
    data = r.json()
    assert data["unread"] == 2
    assert [x["title"] for x in data["items"]][0] == "Thông báo B"   # mới nhất trước

    assert student_client.post("/api/notifications/read",
                               headers={"X-Requested-With": "fetch"}).json()["changed"] == 2
    assert student_client.get("/api/notifications").json()["unread"] == 0


def test_giao_bai_sinh_thong_bao_cho_ca_lop(student, db, teacher_client):
    from tests.conftest import csrf_of

    lesson = _lesson(db)
    klass = _class_of(db, student.id)
    db.query(Notification).delete()
    db.commit()

    r = teacher_client.post(f"/teacher/classes/{klass.id}/assignments",
                            data={"title": "Bài giao mới", "lesson_id": lesson.id,
                                  "max_attempts": 2,
                                  "deadline": (datetime.utcnow() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M"),
                                  "_csrf": csrf_of(teacher_client)},
                            follow_redirects=False)
    assert r.status_code in (200, 303)

    student_ids = db.execute(select(Enrollment.student_id).where(Enrollment.class_id == klass.id)).scalars().all()
    assert student_ids, "lớp phải có học sinh để kiểm"
    got = {n.user_id for n in db.execute(select(Notification)).scalars()}
    assert set(student_ids) == got
    assert all("Bài mới" in n.title for n in db.execute(select(Notification)).scalars())


def test_moi_nguoi_chi_doc_thong_bao_cua_minh(student, db):
    from tests.conftest import client_for

    from app.services import notify

    other = User(email="hs.khac@truong.edu.vn", full_name="Học sinh khác",
                 role="student", password_hash=student.password_hash)
    db.add(other)
    db.commit()
    db.query(Notification).delete()
    db.commit()
    notify.push(db, other.id, "Riêng của người khác", "")
    notify.push(db, student.id, "Của tôi", "")
    db.commit()

    c = client_for("hs.khac@truong.edu.vn")
    items = c.get("/api/notifications").json()["items"]
    assert [i["title"] for i in items] == ["Riêng của người khác"]

    c2 = client_for(student.email)
    assert [i["title"] for i in c2.get("/api/notifications").json()["items"]] == ["Của tôi"]
