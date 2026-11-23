"""Test F7 — nộp bài nói bằng file tải lên (MediaRecorder không test được trong pytest).

Phần ghi âm bằng MediaRecorder chỉ chạy trong secure context; ở đây kiểm tra đường dự phòng
(tải file) và toàn bộ phần quyền/phân quyền của audio.
"""
import io

from sqlalchemy import select

from app.models import Lesson, Submission, Unit
from app.services.security import hash_password
from app.models import User
from tests.conftest import PASSWORD, client_for, csrf_of

FAKE_AUDIO = b"\x1aE\xdf\xa3" + b"fake-webm-bytes" * 100


def _setup(db) -> Lesson:
    from app.seed import ensure_demo_unit

    ensure_demo_unit(db)
    unit = db.execute(select(Unit).where(Unit.grade == 8)).scalars().first()
    return db.execute(select(Lesson).where(Lesson.unit_id == unit.id, Lesson.code == "U1-L4")).scalar_one()


def _upload(client, lesson_id, data=FAKE_AUDIO, name="bai-noi.webm"):
    return client.post(f"/speaking/{lesson_id}/upload",
                       data={"_csrf": csrf_of(client)},
                       files={"file": (name, data, "audio/webm")},
                       follow_redirects=False)


def test_trang_luyen_noi_co_hai_cach_va_canh_bao_https(student, db, student_client):
    lesson = _setup(db)
    r = student_client.get(f"/speaking/{lesson.id}")
    assert r.status_code == 200
    assert "Ghi âm ngay trên trình duyệt" in r.text
    assert "Tải file ghi âm lên" in r.text          # phương án dự phòng R2
    assert "https" in r.text                        # cảnh báo secure context


def test_nop_file_tao_ban_ghi_va_cho_giao_vien_cham(student, db, student_client):
    lesson = _setup(db)
    r = _upload(student_client, lesson.id)
    assert r.status_code == 303
    assert r.headers["location"] == f"/speaking/{lesson.id}/result"

    sub = db.execute(select(Submission)).scalars().first()
    assert sub.status == "awaiting_teacher"
    assert sub.audio_path and sub.audio_path.startswith("speaking/")
    assert sub.text_content == ""


def test_chan_file_qua_lon(student, db, student_client):
    lesson = _setup(db)
    big = b"x" * (10 * 1024 * 1024 + 10)
    r = _upload(student_client, lesson.id, data=big)
    assert r.status_code == 422
    assert "vượt quá 10 MB" in r.text
    assert db.execute(select(Submission)).scalars().first() is None


def test_chan_dinh_dang_khong_ho_tro(student, db, student_client):
    lesson = _setup(db)
    r = _upload(student_client, lesson.id, name="bai-noi.exe")
    assert r.status_code == 422
    assert "không hỗ trợ" in r.text


def test_chi_chu_so_huu_va_giao_vien_lop_nghe_duoc_audio(student, db, student_client, teacher_client,
                                                          other_teacher):
    lesson = _setup(db)
    _upload(student_client, lesson.id)
    sub = db.execute(select(Submission)).scalars().first()

    # chính chủ nghe được
    assert student_client.get(f"/audio/{sub.id}").status_code == 200
    # giáo viên lớp nghe được
    assert teacher_client.get(f"/audio/{sub.id}").status_code == 200

    # học sinh khác bị chặn
    other_student = User(email="khac2@test.vn", password_hash=hash_password(PASSWORD),
                         full_name="HS Khác", role="student")
    db.add(other_student)
    db.commit()
    c = client_for(other_student.email)
    assert c.get(f"/audio/{sub.id}").status_code == 403

    # giáo viên lớp khác bị chặn
    c2 = client_for(other_teacher.email)
    assert c2.get(f"/audio/{sub.id}").status_code == 403


def test_admin_khong_nghe_duoc_audio_goc(student, db, student_client):
    """Mục 1.3: quản trị xem được dữ liệu hệ thống TRỪ audio gốc của học sinh."""
    lesson = _setup(db)
    _upload(student_client, lesson.id)
    sub = db.execute(select(Submission)).scalars().first()

    admin = User(email="ad2@test.vn", password_hash=hash_password(PASSWORD),
                 full_name="QT", role="admin")
    db.add(admin)
    db.commit()
    c = client_for(admin.email)
    assert c.get(f"/audio/{sub.id}").status_code == 403


def test_bai_noi_vao_hang_doi_cham_cua_giao_vien(student, db, student_client, teacher_client):
    lesson = _setup(db)
    _upload(student_client, lesson.id)
    queue = teacher_client.get("/teacher/writing")
    assert queue.status_code == 200
    assert "Bài nói" in queue.text


def test_het_luot_thi_khong_nop_them_duoc(student, db, student_client):
    lesson = _setup(db)
    assert _upload(student_client, lesson.id).status_code == 303
    assert _upload(student_client, lesson.id).status_code == 303
    r = _upload(student_client, lesson.id)     # lượt 3, max_attempts = 2
    assert r.status_code == 422
    assert "hết lượt" in r.text
