"""Test chấm bài NÓI (nửa còn lại của F7) và mở lại bài đã chấm.

Trước đây học sinh nộp bài nói nhưng giáo viên không có chỗ nghe/cho điểm; bài nằm mãi
ở trạng thái chờ. Test này khoá toàn bộ vòng: nộp → hàng đợi → nghe → chấm → thông báo.
"""
from sqlalchemy import select

from app.models import Assignment, AuditLog, Lesson, Notification, RubricScore, Submission, Unit
from app.seed import ensure_demo_unit


def _lesson(db, code="U1-L1"):
    ensure_demo_unit(db)
    unit = db.execute(select(Unit).where(Unit.grade == 8)).scalars().first()
    return db.execute(select(Lesson).where(Lesson.unit_id == unit.id,
                                           Lesson.code == code)).scalar_one()


def _submit_audio(student_client, lesson_id):
    r = student_client.post(
        f"/api/speaking/{lesson_id}/upload",
        files={"file": ("bai-noi.webm", b"\x1aE\xdf\xa3" + b"0" * 2048, "audio/webm")},
        headers={"X-Requested-With": "fetch"},
    )
    assert r.status_code in (200, 201, 303), r.text
    return r


def test_nop_bai_noi_thi_giao_vien_thay_trong_hang_doi(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _submit_audio(student_client, lesson.id)

    r = teacher_client.get("/api/teacher/speaking")
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) == 1
    row = items[0]
    assert row["student"] and row["klass"] and row["has_audio"] is True
    assert row["status"] != "graded"
    assert "Phát âm" in r.json()["labels"].values()


def test_giao_vien_nghe_duoc_audio_con_nguoi_khac_thi_khong(student, db, student_client, teacher_client, other_teacher):
    lesson = _lesson(db)
    _submit_audio(student_client, lesson.id)
    sub = db.execute(select(Submission).order_by(Submission.id.desc())).scalars().first()

    ok = teacher_client.get(f"/api/submissions/{sub.id}/audio")
    assert ok.status_code == 200
    assert len(ok.content) > 100

    # chính chủ nghe lại được
    assert student_client.get(f"/api/submissions/{sub.id}/audio").status_code == 200

    # giáo viên lớp khác: không
    from tests.conftest import client_for

    other = client_for(other_teacher.email)
    assert other.get(f"/api/submissions/{sub.id}/audio").status_code == 403


def test_cham_bai_noi_va_hoc_sinh_nhan_thong_bao(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _submit_audio(student_client, lesson.id)
    sub = db.execute(select(Submission).order_by(Submission.id.desc())).scalars().first()
    db.query(Notification).delete()
    db.commit()

    detail = teacher_client.get(f"/api/teacher/speaking/{sub.id}").json()
    assert detail["audio"] == f"/api/submissions/{sub.id}/audio"
    assert set(detail["criteria"]) == {"task", "pronunciation", "fluency", "vocab"}

    g = teacher_client.post(f"/api/teacher/speaking/{sub.id}/grade",
                            json={"task": 2, "pronunciation": 2, "fluency": 2, "vocab": 2,
                                  "comment": "Phát âm rõ, cần nói chậm hơn một chút."},
                            headers={"X-Requested-With": "fetch"})
    assert g.status_code == 200, g.text
    assert g.json()["final_score"] == 8.0

    notes = db.execute(select(Notification).where(Notification.user_id == student.id)).scalars().all()
    assert len(notes) == 1
    assert "8.0" in notes[0].body
    assert "bài nói" in notes[0].body

    # hàng đợi mặc định chỉ còn bài chưa chấm
    assert teacher_client.get("/api/teacher/speaking").json()["items"] == []
    assert len(teacher_client.get("/api/teacher/speaking?only_pending=false").json()["items"]) == 1


def test_cham_thieu_tieu_chi_bi_tu_choi(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _submit_audio(student_client, lesson.id)
    sub = db.execute(select(Submission).order_by(Submission.id.desc())).scalars().first()

    r = teacher_client.post(f"/api/teacher/speaking/{sub.id}/grade",
                            json={"task": 2, "pronunciation": 2, "fluency": 2},
                            headers={"X-Requested-With": "fetch"})
    assert r.status_code == 422
    assert "Từ vựng" in r.json()["detail"]


def test_mo_lai_bai_de_cham_lai(student, db, student_client, teacher_client):
    lesson = _lesson(db)
    _submit_audio(student_client, lesson.id)
    sub = db.execute(select(Submission).order_by(Submission.id.desc())).scalars().first()
    body = {"task": 1, "pronunciation": 1, "fluency": 1, "vocab": 1, "comment": "Cần cố gắng."}
    assert teacher_client.post(f"/api/teacher/speaking/{sub.id}/grade", json=body,
                               headers={"X-Requested-With": "fetch"}).status_code == 200

    # chấm lại khi chưa mở → bị chặn
    assert teacher_client.post(f"/api/teacher/speaking/{sub.id}/grade", json=body,
                               headers={"X-Requested-With": "fetch"}).status_code == 422

    # mở lại mà không ghi lý do → bị chặn
    short = teacher_client.post(f"/api/teacher/submissions/{sub.id}/reopen",
                               json={"reason": "sai"}, headers={"X-Requested-With": "fetch"})
    assert short.status_code == 422
    assert "lý do" in short.json()["detail"]

    ok = teacher_client.post(f"/api/teacher/submissions/{sub.id}/reopen",
                             json={"reason": "Chấm nhầm thang điểm, học sinh phát âm tốt hơn."},
                             headers={"X-Requested-With": "fetch"})
    assert ok.status_code == 200

    better = {"task": 2, "pronunciation": 2, "fluency": 2, "vocab": 2, "comment": "Đã nghe lại."}
    assert teacher_client.post(f"/api/teacher/speaking/{sub.id}/grade", json=better,
                               headers={"X-Requested-With": "fetch"}).status_code == 200

    db.expire_all()
    fresh = db.get(Submission, sub.id)
    assert fresh.final_score == 8.0
    # điểm cũ bị xoá, không cộng dồn thành 8 tiêu chí
    rows = db.execute(select(RubricScore).where(RubricScore.submission_id == sub.id)).scalars().all()
    assert len(rows) == 4

    logs = db.execute(select(AuditLog).where(AuditLog.action == "reopen")).scalars().all()
    assert len(logs) == 1
    assert "Chấm nhầm" in logs[0].detail
    assert logs[0].actor_email
