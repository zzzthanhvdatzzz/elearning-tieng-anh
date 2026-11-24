"""Test quy tắc xem video: chống tua + chống bắn request liên tục + ngưỡng hoàn thành.

Test ghi thẳng tiến độ vào CSDL để kiểm LUẬT (không phụ thuộc đồng hồ thật), và dùng
heartbeat thật cho phần chống gian lận.
"""
from datetime import datetime

from sqlalchemy import select

from app.models import Lesson, Unit, VideoProgress
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
        files={"file": ("b.mp4", payload, "video/mp4")},
        headers={"X-Requested-With": "fetch"},
    ).status_code == 200


def _beat(student_client, lesson_id, position, duration=100):
    return student_client.post(f"/api/lessons/{lesson_id}/video/heartbeat",
                               json={"position": position, "duration": duration},
                               headers={"X-Requested-With": "fetch"}).json()


def _seed_progress(db, student, lesson, watched, duration=100, passed=False, completed=False):
    db.add(VideoProgress(student_id=student.id, lesson_id=lesson.id,
                         watched_seconds=watched, duration_seconds=duration,
                         position=watched, checkpoint_passed=passed,
                         started_at=datetime.utcnow(),
                         completed_at=datetime.utcnow() if completed else None))
    db.commit()


def test_ban_lien_tiep_nhieu_request_khong_cong_don(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _attach(teacher_client, lesson)

    _beat(student_client, lesson.id, 20, 100)
    last = None
    for pos in (40, 60, 80, 100):          # 4 request ngay lập tức, tổng "tua" 80 giây
        last = _beat(student_client, lesson.id, pos, 100)

    assert last["watched_seconds"] <= 12, last
    assert last["completed"] is False


def test_tua_lui_khong_bi_tru(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _attach(teacher_client, lesson)
    before = _beat(student_client, lesson.id, 20, 100)["watched_seconds"]
    after = _beat(student_client, lesson.id, 5, 100)["watched_seconds"]
    assert after == before


def test_du_80_phan_tram_va_da_tra_loi_thi_hoan_thanh(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _attach(teacher_client, lesson)
    _seed_progress(db, student, lesson, watched=80, passed=True, completed=True)

    d = student_client.get(f"/api/lessons/{lesson.id}/video").json()
    assert d["progress"]["percent"] == 80
    assert d["progress"]["completed"] is True
    assert d["progress"]["needs_checkpoint"] is False


def test_du_80_nhung_chua_tra_loi_thi_chua_hoan_thanh(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _attach(teacher_client, lesson)
    _seed_progress(db, student, lesson, watched=85, passed=False)

    d = student_client.get(f"/api/lessons/{lesson.id}/video").json()
    assert d["progress"]["completed"] is False
    assert d["progress"]["needs_checkpoint"] is True


def test_chua_du_50_thi_chua_hoi(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _attach(teacher_client, lesson)
    _seed_progress(db, student, lesson, watched=30)

    d = student_client.get(f"/api/lessons/{lesson.id}/video").json()
    assert d["progress"]["needs_checkpoint"] is False
    assert d["progress"]["completed"] is False


def test_giao_vien_khong_gui_duoc_nhip_tim(student, db, teacher_client):
    lesson = _lesson(db)
    _attach(teacher_client, lesson)
    r = teacher_client.post(f"/api/lessons/{lesson.id}/video/heartbeat",
                            json={"position": 10, "duration": 100},
                            headers={"X-Requested-With": "fetch"})
    assert r.status_code == 403


def test_bai_chua_co_video_thi_409(student, db, student_client):
    lesson = _lesson(db)
    r = student_client.post(f"/api/lessons/{lesson.id}/video/heartbeat",
                            json={"position": 10, "duration": 100},
                            headers={"X-Requested-With": "fetch"})
    assert r.status_code == 409
