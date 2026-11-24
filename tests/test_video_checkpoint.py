"""Test câu hỏi kiểm tra giữa video: bắt buộc trả lời đúng mới tính hoàn thành.

Mục đích sư phạm: chặn trò "bật video rồi đi chỗ khác" — xem hết vẫn phải trả lời được
một câu hỏi về nội dung bài.
"""
from datetime import datetime

from sqlalchemy import select

from app.models import Lesson, Question, Unit, VideoProgress
from app.seed import ensure_demo_unit


def _lesson(db):
    ensure_demo_unit(db)
    unit = db.execute(select(Unit).where(Unit.grade == 8)).scalars().first()
    return db.execute(select(Lesson).where(Lesson.unit_id == unit.id,
                                           Lesson.code == "U1-L1")).scalar_one()


def _attach(teacher_client, lesson):
    payload = b"\x00\x00\x00\x18ftypmp42" + b"0" * 3000
    assert teacher_client.post(
        f"/api/teacher/lessons/{lesson.id}/video/upload",
        files={"file": ("v.mp4", payload, "video/mp4")},
        headers={"X-Requested-With": "fetch"},
    ).status_code == 200


def _seed(db, student, lesson, watched, passed=False):
    db.add(VideoProgress(student_id=student.id, lesson_id=lesson.id,
                         watched_seconds=watched, duration_seconds=100, position=watched,
                         checkpoint_passed=passed, started_at=datetime.utcnow()))
    db.commit()


def _answer(student_client, lesson_id, key):
    return student_client.post(f"/api/lessons/{lesson_id}/video/checkpoint",
                               json={"answer": key},
                               headers={"X-Requested-With": "fetch"})


def test_tra_loi_sai_thi_chua_hoan_thanh(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _attach(teacher_client, lesson)
    q = db.execute(select(Question).where(Question.lesson_id == lesson.id)
                   .order_by(Question.order_no)).scalars().first()
    _seed(db, student, lesson, watched=85)

    wrong = "B" if q.correct_key != "B" else "C"
    r = _answer(student_client, lesson.id, wrong)
    assert r.status_code == 200
    assert r.json()["correct"] is False
    assert r.json()["completed"] is False


def test_tra_loi_dung_thi_hoan_thanh(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _attach(teacher_client, lesson)
    q = db.execute(select(Question).where(Question.lesson_id == lesson.id)
                   .order_by(Question.order_no)).scalars().first()
    _seed(db, student, lesson, watched=85)

    r = _answer(student_client, lesson.id, q.correct_key)
    assert r.status_code == 200, r.text
    assert r.json()["correct"] is True
    assert r.json()["completed"] is True


def test_chua_xem_du_50_thi_khong_duoc_tra_loi(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _attach(teacher_client, lesson)
    _seed(db, student, lesson, watched=20)

    r = _answer(student_client, lesson.id, "A")
    assert r.status_code == 409
    assert "50%" in r.json()["detail"]


def test_api_tra_cau_hoi_khong_lo_dap_an(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _attach(teacher_client, lesson)
    _seed(db, student, lesson, watched=60)

    d = student_client.get(f"/api/lessons/{lesson.id}/video").json()
    assert d["progress"]["needs_checkpoint"] is True
    assert d["checkpoint"] is not None
    assert d["checkpoint"]["options"], "phải có lựa chọn để học sinh chọn"
    assert "correct_key" not in d["checkpoint"]
    assert "answer" not in d["checkpoint"]


def test_giao_vien_khong_tra_loi_duoc(student, db, teacher_client):
    lesson = _lesson(db)
    _attach(teacher_client, lesson)
    r = teacher_client.post(f"/api/lessons/{lesson.id}/video/checkpoint",
                            json={"answer": "A"}, headers={"X-Requested-With": "fetch"})
    assert r.status_code == 403
