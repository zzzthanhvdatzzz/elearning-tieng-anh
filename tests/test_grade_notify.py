"""Chấm bài qua API của giáo viên → học sinh phải nhận thông báo VÀ thấy điểm.

Đây chính là luồng người dùng báo lỗi: "giáo viên chấm nhưng học sinh không nhận được".
"""
from sqlalchemy import select

from app.models import Assignment, Lesson, Notification, Submission, Unit
from app.seed import ensure_demo_unit


def _lesson(db, code="U1-L1"):
    ensure_demo_unit(db)
    unit = db.execute(select(Unit).where(Unit.grade == 8)).scalars().first()
    return db.execute(select(Lesson).where(Lesson.unit_id == unit.id,
                                           Lesson.code == code)).scalar_one()


def test_cham_bai_qua_api_giao_vien_thi_hoc_sinh_nhan_thong_bao(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    essay = ("I live in a small town near Hanoi. There is a river and a market, and the people "
             "are very friendly, so I love my neighbourhood.")
    r = student_client.post(f"/api/writing/{lesson.id}/submit", json={"text": essay},
                            headers={"X-Requested-With": "fetch"})
    assert r.status_code == 200, r.text
    sub = db.execute(select(Submission).order_by(Submission.id.desc())).scalars().first()

    db.query(Notification).delete()
    db.commit()

    g = teacher_client.post(f"/api/teacher/submissions/{sub.id}/grade",
                            json={"task": 2, "grammar": 2, "vocab": 2, "coherence": 2,
                                  "comment": "Bài tốt, cần thêm ví dụ."},
                            headers={"X-Requested-With": "fetch"})
    assert g.status_code == 200, g.text
    assert g.json()["final_score"] == 8.0

    notes = db.execute(select(Notification).where(Notification.user_id == student.id)).scalars().all()
    assert len(notes) == 1, "học sinh phải nhận đúng 1 thông báo sau khi được chấm"
    assert "đã được chấm" in notes[0].title
    assert "8.0" in notes[0].body

    # Học sinh đọc thông báo qua API mà chuông dùng
    api = student_client.get("/api/notifications").json()
    assert api["unread"] == 1
    assert "đã được chấm" in api["items"][0]["title"]

    # Và thấy điểm trong kết quả bài viết (score nằm trong `submission`)
    res = student_client.get(f"/api/writing/{lesson.id}/result").json()
    assert res["submission"]["score"] == 8.0
    assert res["submission"]["status"] == "graded"
    assert res["feedback"] == "Bài tốt, cần thêm ví dụ."


def test_cham_lai_bi_chan_va_khong_sinh_them_thong_bao(student, db, student_client, teacher_client):
    """Quy tắc: mỗi bài chỉ chấm một lần (muốn chấm lại phải mở lại kèm lý do)."""
    lesson = _lesson(db)
    student_client.post(f"/api/writing/{lesson.id}/submit",
                        json={"text": ("My house is near the school. There are many green trees, "
                                       "a small park and a lake where children play every afternoon. "
                                       "I love my quiet neighbourhood very much.")},
                        headers={"X-Requested-With": "fetch"})
    sub = db.execute(select(Submission).order_by(Submission.id.desc())).scalars().first()
    db.query(Notification).delete()
    db.commit()

    body = {"task": 2, "grammar": 2, "vocab": 2, "coherence": 2, "comment": "Đã chấm."}
    first = teacher_client.post(f"/api/teacher/submissions/{sub.id}/grade", json=body,
                                headers={"X-Requested-With": "fetch"})
    assert first.status_code == 200
    second = teacher_client.post(f"/api/teacher/submissions/{sub.id}/grade", json=body,
                                 headers={"X-Requested-With": "fetch"})
    assert second.status_code == 422
    assert "đã chấm" in second.json()["detail"]

    notes = db.execute(select(Notification).where(Notification.user_id == student.id)).scalars().all()
    assert len(notes) == 1, "chấm bị từ chối thì không được sinh thông báo thứ hai"
