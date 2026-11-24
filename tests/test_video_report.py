"""Test nối video vào tiến độ học: dashboard, báo cáo học sinh, báo cáo phụ huynh.

Tiến độ được ghi thẳng vào CSDL để kiểm phần ĐỌC dữ liệu (không phụ thuộc đồng hồ).
"""
from datetime import datetime

from sqlalchemy import select

from app.models import Lesson, ParentLink, Unit, User, VideoProgress
from app.seed import ensure_demo_unit
from app.services.security import hash_password
from tests.conftest import PASSWORD, client_for


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


def _seed(db, student, lesson, watched, completed=True, passed=True):
    db.add(VideoProgress(student_id=student.id, lesson_id=lesson.id,
                         watched_seconds=watched, duration_seconds=100, position=watched,
                         checkpoint_passed=passed, started_at=datetime.utcnow(),
                         completed_at=datetime.utcnow() if completed else None))
    db.commit()


def test_dashboard_hoc_sinh_co_so_lieu_video(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _attach(teacher_client, lesson)
    _seed(db, student, lesson, 80)

    d = student_client.get("/api/dashboard").json()
    assert d["videos"]["videos_total"] == 1
    assert d["videos"]["videos_completed"] == 1
    assert d["videos"]["watched_seconds"] == 80
    assert d["videos"]["percent"] == 100
    assert d["videos"]["items"][0]["completed"] is True


def test_dashboard_chua_xong_thi_dem_sai(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _attach(teacher_client, lesson)
    _seed(db, student, lesson, 40, completed=False, passed=False)

    v = student_client.get("/api/dashboard").json()["videos"]
    assert v["videos_total"] == 1
    assert v["videos_completed"] == 0
    assert v["percent"] == 0
    assert v["items"][0]["percent"] == 40


def test_bao_cao_hoc_sinh_co_video(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _attach(teacher_client, lesson)
    _seed(db, student, lesson, 40, completed=False, passed=False)

    r = student_client.get(f"/api/reports/student/{student.id}").json()
    assert r["videos"]["videos_total"] == 1
    assert r["videos"]["videos_completed"] == 0
    assert r["videos"]["watched_seconds"] == 40


def test_bao_cao_phu_huynh_co_video(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _attach(teacher_client, lesson)
    _seed(db, student, lesson, 80)

    parent = User(email="ph.video@test.vn", full_name="PH Video", role="parent",
                  password_hash=hash_password(PASSWORD))
    db.add(parent)
    db.commit()
    db.add(ParentLink(parent_id=parent.id, student_id=student.id, status="approved"))
    db.commit()

    r = client_for(parent.email).get(f"/api/parent/report/{student.id}")
    assert r.status_code == 200
    assert r.json()["videos"]["videos_completed"] == 1


def test_chua_co_video_thi_khong_hien_khoi(student, db, student_client):
    _lesson(db)
    d = student_client.get("/api/dashboard").json()
    assert d["videos"]["videos_total"] == 0
    assert d["videos"]["items"] == []
