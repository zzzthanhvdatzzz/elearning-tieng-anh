"""Test F9/UC-05 — luyện tập trắc nghiệm, chấm tự động, BR7 hết lượt (AC9.1–AC9.3)."""
import json

from sqlalchemy import select

from app.models import Answer, Lesson, Submission, Unit
from tests.conftest import csrf_of


def _l1(db) -> Lesson:
    unit = db.execute(select(Unit).where(Unit.grade == 8)).scalars().first()
    return db.execute(select(Lesson).where(Lesson.unit_id == unit.id, Lesson.code == "U1-L1")).scalar_one()


def _correct(db, lesson) -> dict[str, str]:
    return {f"q_{q.id}": q.correct_key for q in lesson.questions}


def _setup(db):
    from app.seed import ensure_demo_unit

    ensure_demo_unit(db)
    return _l1(db)


def test_de_luyen_tap_co_10_cau_va_khong_lo_dap_an(student, db, student_client):
    lesson = _setup(db)
    r = student_client.get(f"/practice/{lesson.id}")
    assert r.status_code == 200
    assert r.text.count('type="radio"') == 40  # 10 câu × 4 lựa chọn
    assert "correct_key" not in r.text
    assert "Giải thích" not in r.text  # chỉ hiện sau khi nộp


def test_nop_dung_het_duoc_10_diem_va_co_giai_thich(student, db, student_client):
    lesson = _setup(db)
    data = _correct(db, lesson)
    data["_csrf"] = csrf_of(student_client)

    r = student_client.post(f"/practice/{lesson.id}/submit", data=data, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == f"/practice/{lesson.id}/result"

    sub = db.execute(select(Submission)).scalars().first()
    assert sub.auto_score == 10.0 and sub.final_score == 10.0
    assert sub.status == "graded"
    assert db.execute(select(Answer).where(Answer.submission_id == sub.id)).scalars().all()

    page = student_client.get(f"/practice/{lesson.id}/result")
    assert "10.0" in page.text
    assert "Giải thích" in page.text


def test_cham_dung_so_cau_dung(student, db, student_client):
    lesson = _setup(db)
    qs = lesson.questions
    # 7 câu đúng, 3 câu sai → 7.0 (BR5)
    data = {}
    for i, q in enumerate(qs):
        key = q.correct_key
        data[f"q_{q.id}"] = key if i < 7 else ("A" if key != "A" else "B")
    data["_csrf"] = csrf_of(student_client)
    student_client.post(f"/practice/{lesson.id}/submit", data=data, follow_redirects=False)

    sub = db.execute(select(Submission)).scalars().first()
    assert sub.auto_score == 7.0


def test_br7_het_luot_thi_server_tu_choi_ke_ca_goi_thang_api(student, db, student_client):
    lesson = _setup(db)
    data = _correct(db, lesson)
    data["_csrf"] = csrf_of(student_client)

    for _ in range(3):
        r = student_client.post(f"/practice/{lesson.id}/submit", data=data, follow_redirects=False)
        assert r.status_code == 303

    # Lượt thứ 4: gọi thẳng endpoint (không qua nút) vẫn bị chặn
    r4 = student_client.post(f"/practice/{lesson.id}/submit", data=data, follow_redirects=False)
    assert r4.status_code == 409
    assert "hết lượt" in r4.text
    assert db.execute(select(Submission)).scalars().all().__len__() == 3

    # Mở trang đề khi đã hết lượt → đưa về trang kết quả, không cho làm tiếp
    r = student_client.get(f"/practice/{lesson.id}", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].endswith("/result")


def test_moi_lan_nop_luu_mot_luot_rieng(student, db, student_client):
    lesson = _setup(db)
    data = _correct(db, lesson)
    data["_csrf"] = csrf_of(student_client)
    student_client.post(f"/practice/{lesson.id}/submit", data=data, follow_redirects=False)
    student_client.post(f"/practice/{lesson.id}/submit", data=data, follow_redirects=False)

    attempts = [s.attempt_no for s in db.execute(select(Submission)).scalars().all()]
    assert sorted(attempts) == [1, 2]


def test_giao_vien_khong_lam_bai_duoc(student, db, teacher_client):
    lesson = _setup(db)
    assert teacher_client.get(f"/practice/{lesson.id}", follow_redirects=False).status_code == 403


def test_bai_khoi_khac_tra_404(student, db, student_client):
    from app.seed import ensure_demo_unit

    ensure_demo_unit(db)
    unit10 = Unit(grade=10, code="U1-10", title="Family Life", order_no=1)
    db.add(unit10)
    db.flush()
    l10 = Lesson(unit_id=unit10.id, code="10-U1-L1", title="Family Life", skill="vocab",
                 content=json.dumps({"objectives": ["x"]}), order_no=1)
    db.add(l10)
    db.commit()
    assert student_client.get(f"/practice/{l10.id}").status_code == 404


def test_thieu_csrf_khi_nop_bai(student, db, student_client):
    lesson = _setup(db)
    data = _correct(db, lesson)
    r = student_client.post(f"/practice/{lesson.id}/submit", data=data, follow_redirects=False)
    assert r.status_code == 403
