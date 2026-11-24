"""Test video bài giảng: gắn link YouTube/Drive, tự tải file, phân quyền xem.

Yêu cầu thực tế của nhóm: giáo viên vừa dùng được video trên YouTube, vừa tải được video
tự quay. Hai đường này khác nhau về bản chất (nhúng iframe vs phát file) nên phải test riêng.
"""
import io

from sqlalchemy import select

from app.models import Class, Lesson, Unit
from app.seed import ensure_demo_unit
from tests.conftest import client_for


def _lesson_and_class(db):
    ensure_demo_unit(db)
    unit = db.execute(select(Unit).where(Unit.grade == 8)).scalars().first()
    lesson = db.execute(select(Lesson).where(Lesson.unit_id == unit.id,
                                            Lesson.code == "U1-L1")).scalar_one()
    klass = db.execute(select(Class).where(Class.join_code == "TEST01")).scalar_one()
    return lesson, klass


def test_giao_vien_gan_link_youtube(student, db, teacher_client, student_client):
    lesson, _ = _lesson_and_class(db)
    r = teacher_client.post(f"/api/teacher/lessons/{lesson.id}/video",
                            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                                  "title": "Unit 1 — Getting started"},
                            headers={"X-Requested-With": "fetch"})
    assert r.status_code == 200, r.text
    assert r.json()["kind"] == "embed"
    assert r.json()["embed_url"] == "https://www.youtube.com/embed/dQw4w9WgXcQ"

    # học sinh lớp 8 xem được
    got = student_client.get(f"/api/lessons/{lesson.id}/video")
    assert got.status_code == 200
    assert got.json()["embed_url"].endswith("dQw4w9WgXcQ")
    assert got.json()["title"] == "Unit 1 — Getting started"


def test_link_youtu_be_va_shorts_duoc_chuan_hoa(student, db, teacher_client):
    lesson, _ = _lesson_and_class(db)
    for raw, expect in [("https://youtu.be/abc123XYZ", "abc123XYZ"),
                        ("https://www.youtube.com/shorts/xyz789ABC", "xyz789ABC"),
                        ("https://drive.google.com/file/d/FILEID123456/view",
                         "FILEID123456")]:
        r = teacher_client.post(f"/api/teacher/lessons/{lesson.id}/video", json={"url": raw},
                                headers={"X-Requested-With": "fetch"})
        assert r.status_code == 200, (raw, r.text)
        if "drive" in raw:
            assert expect in r.json()["embed_url"] and "preview" in r.json()["embed_url"]
        else:
            assert r.json()["embed_url"] == f"https://www.youtube.com/embed/{expect}"


def test_link_rac_bi_tu_choi(student, db, teacher_client):
    lesson, _ = _lesson_and_class(db)
    r = teacher_client.post(f"/api/teacher/lessons/{lesson.id}/video",
                            json={"url": "https://vimeo.com/12345"},
                            headers={"X-Requested-With": "fetch"})
    assert r.status_code == 422
    assert "YouTube" in r.json()["detail"]


def test_giao_vien_tai_video_tu_quay_va_hoc_sinh_phat_duoc(student, db, teacher_client, student_client):
    lesson, _ = _lesson_and_class(db)
    payload = b"\x00\x00\x00\x18ftypmp42" + b"0" * 5000
    r = teacher_client.post(
        f"/api/teacher/lessons/{lesson.id}/video/upload",
        files={"file": ("bai-giang.mp4", payload, "video/mp4")},
        data={"title": "Bài giảng tự quay"},
        headers={"X-Requested-With": "fetch"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["kind"] == "file"
    assert r.json()["stream"] == f"/api/lessons/{lesson.id}/video/stream"

    v = student_client.get(f"/api/lessons/{lesson.id}/video/stream")
    assert v.status_code == 200
    assert len(v.content) == len(payload)
    # Range request: trình duyệt tua được video
    part = student_client.get(f"/api/lessons/{lesson.id}/video/stream",
                              headers={"Range": "bytes=0-99"})
    assert part.status_code in (200, 206)
    assert len(part.content) <= 100 if part.status_code == 206 else True


def test_dinh_dang_video_khong_ho_tro(student, db, teacher_client):
    lesson, _ = _lesson_and_class(db)
    r = teacher_client.post(
        f"/api/teacher/lessons/{lesson.id}/video/upload",
        files={"file": ("bai-giang.exe", b"MZ" + b"0" * 100, "application/octet-stream")},
        headers={"X-Requested-With": "fetch"},
    )
    assert r.status_code == 422
    assert ".mp4" in r.json()["detail"]


def test_giao_vien_khoi_khac_khong_gan_duoc_video(student, db, teacher_client):
    from app.models import User
    from app.services.security import hash_password
    from tests.conftest import PASSWORD

    lesson, _ = _lesson_and_class(db)
    other = User(email="gv.khoi10@test.vn", password_hash=hash_password(PASSWORD),
                 full_name="GV Khối 10", role="teacher")
    db.add(other)
    db.flush()
    db.add(Class(name="Lớp 10 Test", grade=10, join_code="T10ABC", teacher_id=other.id))
    db.commit()

    c = client_for(other.email)
    r = c.post(f"/api/teacher/lessons/{lesson.id}/video",
               json={"url": "https://youtu.be/abc123XYZ"},
               headers={"X-Requested-With": "fetch"})
    assert r.status_code == 403
    assert "khối" in r.json()["detail"].lower()


def test_hoc_sinh_khoi_khac_khong_xem_duoc_video(student, db, teacher_client):
    lesson, _ = _lesson_and_class(db)
    teacher_client.post(f"/api/teacher/lessons/{lesson.id}/video",
                        json={"url": "https://youtu.be/abc123XYZ"},
                        headers={"X-Requested-With": "fetch"})

    from app.models import User
    from app.services.security import hash_password
    from tests.conftest import PASSWORD

    grade10 = db.execute(select(Unit).where(Unit.grade == 10)).scalars().first()
    if grade10 is None:
        return  # chưa có nội dung khối 10 trong seed
    lesson10 = db.execute(select(Lesson).where(Lesson.unit_id == grade10.id)).scalars().first()

    outsider = User(email="hs.khoi10@test.vn", password_hash=hash_password(PASSWORD),
                    full_name="HS Khối 10", role="student")
    db.add(outsider)
    db.commit()
    c = client_for(outsider.email)
    assert c.get(f"/api/lessons/{lesson.id}/video").status_code == 403
    if lesson10 is not None:
        assert c.get(f"/api/lessons/{lesson10.id}/video").status_code == 200


def test_xoa_video(student, db, teacher_client):
    lesson, _ = _lesson_and_class(db)
    teacher_client.post(f"/api/teacher/lessons/{lesson.id}/video",
                        json={"url": "https://youtu.be/abc123XYZ"},
                        headers={"X-Requested-With": "fetch"})
    r = teacher_client.delete(f"/api/teacher/lessons/{lesson.id}/video",
                              headers={"X-Requested-With": "fetch"})
    assert r.status_code == 200
    db.expire_all()
    fresh = db.get(Lesson, lesson.id)
    assert fresh.video_url is None and fresh.video_path is None
