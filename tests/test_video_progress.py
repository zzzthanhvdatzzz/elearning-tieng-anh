"""Test quy tắc xem video: không tính cú tua, hoàn thành khi ≥ 80% thời lượng.

Yêu cầu của nhóm: "không cho tua nhanh mà phải qua 80% thời lượng mới được tính hoàn thành".
Chặn tua phía trình duyệt chỉ là một lớp; lớp quyết định là SERVER — nó chỉ cộng phần chênh
lệch hợp lệ, nên gọi API bằng tay cũng không nhảy cóc được.
"""
from sqlalchemy import select

from app.models import Class, Lesson, Unit, VideoProgress
from app.seed import ensure_demo_unit


def _lesson(db):
    ensure_demo_unit(db)
    unit = db.execute(select(Unit).where(Unit.grade == 8)).scalars().first()
    return db.execute(select(Lesson).where(Lesson.unit_id == unit.id,
                                           Lesson.code == "U1-L1")).scalar_one()


def _attach_file(student, db, teacher_client, lesson):
    payload = b"\x00\x00\x00\x18ftypmp42" + b"0" * 4000
    r = teacher_client.post(
        f"/api/teacher/lessons/{lesson.id}/video/upload",
        files={"file": ("bai.mp4", payload, "video/mp4")},
        headers={"X-Requested-With": "fetch"},
    )
    assert r.status_code == 200, r.text


def _beat(student_client, lesson_id, position, duration=100):
    return student_client.post(f"/api/lessons/{lesson_id}/video/heartbeat",
                               json={"position": position, "duration": duration},
                               headers={"X-Requested-With": "fetch"})


def test_moi_nhip_chi_cong_toi_da_20_giay(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _attach_file(student, db, teacher_client, lesson)

    r = _beat(student_client, lesson.id, 10, 100)
    assert r.status_code == 200, r.text
    assert r.json()["watched_seconds"] == 10
    assert r.json()["completed"] is False

    # tua thẳng lên 90 giây: server chỉ cộng 20 giây, KHÔNG cộng 80
    r2 = _beat(student_client, lesson.id, 90, 100)
    assert r2.json()["watched_seconds"] == 30
    assert r2.json()["position"] == 30          # mốc xem thật vẫn ở 30
    assert r2.json()["completed"] is False


def test_tua_lui_khong_bi_tru(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _attach_file(student, db, teacher_client, lesson)
    _beat(student_client, lesson.id, 15, 100)
    r = _beat(student_client, lesson.id, 5, 100)
    assert r.json()["watched_seconds"] == 15


def test_du_80_phan_tram_thi_hoan_thanh(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _attach_file(student, db, teacher_client, lesson)
    # xem tuần tự 10 giây mỗi nhịp, tổng 80 giây trên video 100 giây
    last = None
    for pos in range(10, 81, 10):
        last = _beat(student_client, lesson.id, pos, 100).json()
    assert last["completed"] is True
    assert last["percent"] >= 80
    assert last["needed_seconds"] == 0

    row = db.execute(select(VideoProgress)).scalar_one()
    assert row.completed_at is not None


def test_chua_du_80_thi_chua_hoan_thanh(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _attach_file(student, db, teacher_client, lesson)
    for pos in range(10, 71, 10):        # 70 giây
        last = _beat(student_client, lesson.id, pos, 100).json()
    assert last["completed"] is False
    assert last["needed_seconds"] == 10


def test_tien_do_moi_hoc_sinh_rieng(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _attach_file(student, db, teacher_client, lesson)
    _beat(student_client, lesson.id, 20, 100)

    from app.models import User
    from app.services.security import hash_password
    from tests.conftest import PASSWORD, client_for

    other = User(email="hs.khac2@test.vn", password_hash=hash_password(PASSWORD),
                 full_name="HS Khác", role="student")
    db.add(other)
    db.flush()
    klass = db.execute(select(Class).where(Class.join_code == "TEST01")).scalar_one()
    from app.models import Enrollment

    db.add(Enrollment(class_id=klass.id, student_id=other.id))
    db.commit()

    c = client_for(other.email)
    got = c.get(f"/api/lessons/{lesson.id}/video").json()
    assert got["progress"]["watched_seconds"] == 0
    assert got["progress"]["completed"] is False


def test_giao_vien_khong_gui_duoc_nhip_tim(student, db, teacher_client):
    lesson = _lesson(db)
    _attach_file(student, db, teacher_client, lesson)
    r = teacher_client.post(f"/api/lessons/{lesson.id}/video/heartbeat",
                            json={"position": 10, "duration": 100},
                            headers={"X-Requested-With": "fetch"})
    assert r.status_code == 403


def test_bai_chua_co_video_thi_409(student, db, student_client):
    lesson = _lesson(db)
    r = _beat(student_client, lesson.id, 10, 100)
    assert r.status_code == 409
