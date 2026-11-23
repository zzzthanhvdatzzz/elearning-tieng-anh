"""Test luồng placement end-to-end — ứng với UC-03 và AC4.1–AC4.3.

Dùng TestClient nên đây là test tích hợp: router → service → CSDL → template.
"""
from sqlalchemy import select

from app.models import Answer, Question, Submission, User
from app.services.placement import placement_questions
from tests.conftest import csrf_of


def _all_correct_answers(db) -> dict[int, str]:
    qs = placement_questions(db)
    assert len(qs) == 25, "Ngân hàng placement phải có đúng 25 câu"
    return {q.id: q.correct_key for q in qs}


def test_de_bai_co_du_25_cau_ba_phan(student_client, db):
    qs = placement_questions(db)
    counts = {}
    for q in qs:
        counts[q.skill] = counts.get(q.skill, 0) + 1
    assert counts == {"grammar": 10, "reading": 8, "listening": 7}

    r = student_client.get("/placement")
    assert r.status_code == 200
    assert "Phần 1 — Ngữ pháp" in r.text
    assert "Phần 4 — Bài viết" in r.text


def test_nop_bai_dung_het_diem_10_va_cho_giao_vien_cham_viet(student_client, db, student):
    answers = _all_correct_answers(db)
    token = csrf_of(student_client)
    data = {f"q_{qid}": key for qid, key in answers.items()}
    data["essay"] = "My neighbourhood is quiet and green. There is a small market and a temple."
    data["_csrf"] = token

    r = student_client.post("/placement/submit", data=data, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/placement/result"

    sub = db.execute(select(Submission).where(Submission.student_id == student.id)).scalar_one()
    assert sub.auto_score == 10.0
    assert sub.status == "awaiting_teacher"  # AC4.3: chưa xếp CEFR khi chưa chấm bài viết
    assert sub.final_score is None
    assert db.execute(select(Answer).where(Answer.submission_id == sub.id)).scalars().all()

    # BR4: làm lại lần hai bị từ chối, không tạo lượt mới
    r2 = student_client.post("/placement/submit", data=data, follow_redirects=False)
    assert r2.status_code == 409
    assert "đã làm bài kiểm tra đầu vào" in r2.text


def test_ket_qua_hien_thi_cho_cham_chua_xep_trinh_do(student_client, db):
    answers = _all_correct_answers(db)
    data = {f"q_{qid}": key for qid, key in answers.items()}
    data["essay"] = "My neighbourhood is quiet."
    data["_csrf"] = csrf_of(student_client)
    student_client.post("/placement/submit", data=data, follow_redirects=False)

    r = student_client.get("/placement/result")
    assert r.status_code == 200
    assert "chờ giáo viên chấm" in r.text


def test_giao_vien_cham_4_tieu_chi_thi_xep_cefr(student_client, teacher_client, db, student):
    answers = _all_correct_answers(db)
    data = {f"q_{qid}": key for qid, key in answers.items()}
    data["essay"] = "My neighbourhood is quiet and green."
    data["_csrf"] = csrf_of(student_client)
    student_client.post("/placement/submit", data=data, follow_redirects=False)

    sub = db.execute(select(Submission).where(Submission.student_id == student.id)).scalar_one()

    # Hàng đợi của giáo viên có bài này
    queue = teacher_client.get("/teacher/placement")
    assert queue.status_code == 200
    assert f"/teacher/placement/{sub.id}" in queue.text

    r = teacher_client.post(
        f"/teacher/placement/{sub.id}/grade",
        data={"task": 2.5, "grammar": 2.0, "vocab": 2.0, "coherence": 1.5,
              "level_override": 0, "comment": "Diễn đạt rõ, cần thêm ví dụ.", "_csrf": csrf_of(teacher_client)},
        follow_redirects=False,
    )
    assert r.status_code == 303

    db.expire_all()
    sub = db.get(Submission, sub.id)
    assert sub.status == "graded"
    assert sub.teacher_score == 8.0
    assert sub.final_score == 9.4          # 0,7×10 + 0,3×8
    assert sub.cefr_proposed == "B2"
    assert db.get(User, student.id).cefr_level == "B2"


def test_diem_thap_ma_khong_co_nhan_xet_thi_khong_luu(student_client, teacher_client, db, student):
    answers = _all_correct_answers(db)
    data = {f"q_{qid}": key for qid, key in answers.items()}
    data["essay"] = "short"
    data["_csrf"] = csrf_of(student_client)
    student_client.post("/placement/submit", data=data, follow_redirects=False)
    sub = db.execute(select(Submission).where(Submission.student_id == student.id)).scalar_one()

    r = teacher_client.post(
        f"/teacher/placement/{sub.id}/grade",
        data={"task": 0.5, "grammar": 0.5, "vocab": 0.5, "coherence": 0.5,
              "level_override": 0, "comment": "", "_csrf": csrf_of(teacher_client)},
        follow_redirects=False,
    )
    assert r.status_code == 422
    assert "bắt buộc nhập nhận xét" in r.text
    db.expire_all()
    assert db.get(Submission, sub.id).status == "awaiting_teacher"


def test_giao_vien_khac_khong_mo_duoc_bai_lop_minh_khong_day(student_client, teacher_client,
                                                              other_teacher, db, student):
    answers = _all_correct_answers(db)
    data = {f"q_{qid}": key for qid, key in answers.items()}
    data["essay"] = "My neighbourhood."
    data["_csrf"] = csrf_of(student_client)
    student_client.post("/placement/submit", data=data, follow_redirects=False)
    sub = db.execute(select(Submission).where(Submission.student_id == student.id)).scalar_one()

    # Giáo viên khác đăng nhập ở client riêng
    from fastapi.testclient import TestClient
    from app.main import app
    from tests.conftest import login

    with TestClient(app) as c:
        login(c, other_teacher.email)
        r = c.get(f"/teacher/placement/{sub.id}")
        assert r.status_code == 403


def test_hoc_sinh_khong_vao_duoc_hang_doi_cham(student_client):
    r = student_client.get("/teacher/placement", follow_redirects=False)
    assert r.status_code == 403
