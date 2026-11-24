"""Test nối video vào tiến độ học: dashboard, báo cáo học sinh, báo cáo phụ huynh.

Lỗ hổng đã sửa: bảng `video_progress` có dữ liệu nhưng không nơi nào đọc, nên học sinh xem
xong video hệ thống vẫn báo "chưa học gì" và phụ huynh không thấy con đã xem bài giảng.
"""
from sqlalchemy import select

from app.models import Class, Enrollment, Lesson, Unit, User
from app.seed import ensure_demo_unit


def _lesson(db):
    ensure_demo_unit(db)
    unit = db.execute(select(Unit).where(Unit.grade == 8)).scalars().first()
    return db.execute(select(Lesson).where(Lesson.unit_id == unit.id,
                                           Lesson.code == "U1-L1")).scalar_one()


def _attach_and_watch(db, teacher_client, student_client, lesson, to_second=80):
    payload = b"\x00\x00\x00\x18ftypmp42" + b"0" * 3000
    assert teacher_client.post(
        f"/api/teacher/lessons/{lesson.id}/video/upload",
        files={"file": ("b.mp4", payload, "video/mp4")},
        headers={"X-Requested-With": "fetch"},
    ).status_code == 200
    last = None
    for pos in range(10, to_second + 1, 10):
        last = student_client.post(
            f"/api/lessons/{lesson.id}/video/heartbeat",
            json={"position": pos, "duration": 100},
            headers={"X-Requested-With": "fetch"},
        ).json()
    return last


def test_dashboard_hoc_sinh_co_so_lieu_video(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _attach_and_watch(db, teacher_client, student_client, lesson, 80)

    d = student_client.get("/api/dashboard").json()
    assert d["videos"]["videos_total"] == 1
    assert d["videos"]["videos_completed"] == 1
    assert d["videos"]["watched_seconds"] == 80
    assert d["videos"]["percent"] == 100
    assert d["videos"]["items"][0]["completed"] is True


def test_bao_cao_hoc_sinh_co_video(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _attach_and_watch(db, teacher_client, student_client, lesson, 40)   # 40% — chưa xong

    r = student_client.get(f"/api/reports/student/{student.id}").json()
    assert r["videos"]["videos_total"] == 1
    assert r["videos"]["videos_completed"] == 0
    assert r["videos"]["watched_seconds"] == 40
    assert r["videos"]["percent"] == 0


def test_bao_cao_phu_huynh_co_video(student, db, student_client, teacher_client):
    from app.models import ParentLink
    from app.services.security import hash_password
    from tests.conftest import PASSWORD, client_for

    lesson = _lesson(db)
    _attach_and_watch(db, teacher_client, student_client, lesson, 80)

    parent = User(email="ph.video@test.vn", full_name="PH Video", role="parent",
                  password_hash=hash_password(PASSWORD))
    db.add(parent)
    db.commit()
    db.add(ParentLink(parent_id=parent.id, student_id=student.id, status="approved"))
    db.commit()

    c = client_for(parent.email)
    r = c.get(f"/api/parent/report/{student.id}")
    assert r.status_code == 200
    assert r.json()["videos"]["videos_completed"] == 1


def test_chua_co_video_thi_khong_hien_khoi(student, db, student_client):
    _lesson(db)                       # có bài học nhưng chưa gắn video nào
    d = student_client.get("/api/dashboard").json()
    assert d["videos"]["videos_total"] == 0
    assert d["videos"]["items"] == []
