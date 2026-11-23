"""Test F2 (quản trị tài khoản) và F15 (import câu hỏi từ Excel)."""
import io

import pytest
from sqlalchemy import select

from app.models import Lesson, Question, Session, Unit, User
from app.services.security import hash_password
from tests.conftest import PASSWORD, client_for, csrf_of


@pytest.fixture()
def admin_user(db):
    a = User(email="admin@test.vn", password_hash=hash_password(PASSWORD),
             full_name="Quản trị Test", role="admin")
    db.add(a)
    db.commit()
    return a


@pytest.fixture()
def admin_client(admin_user):
    return client_for(admin_user.email)


def test_admin_tao_giao_vien(admin_client, db):
    r = admin_client.post("/admin/users",
                          data={"email": "gvmoi@test.vn", "full_name": "GV Mới", "role": "teacher",
                                "password": PASSWORD, "_csrf": csrf_of(admin_client)},
                          follow_redirects=False)
    assert r.status_code == 303
    u = db.execute(select(User).where(User.email == "gvmoi@test.vn")).scalar_one()
    assert u.role == "teacher"
    assert u.password_hash.startswith("$2b$")


def test_admin_tao_trung_email_bao_loi(admin_client, db, teacher_and_class):
    r = admin_client.post("/admin/users",
                          data={"email": teacher_and_class.email, "full_name": "Trùng",
                                "role": "teacher", "password": PASSWORD,
                                "_csrf": csrf_of(admin_client)},
                          follow_redirects=True)
    assert "đã được đăng ký" in r.text


def test_khoa_tai_khoan_huy_phien_ngay(admin_client, db, teacher_and_class):
    c = client_for(teacher_and_class.email)
    assert c.get("/me").status_code == 200

    r = admin_client.post(f"/admin/users/{teacher_and_class.id}/lock",
                          data={"_csrf": csrf_of(admin_client)}, follow_redirects=False)
    assert r.status_code == 303

    db.expire_all()
    assert db.get(User, teacher_and_class.id).is_active is False
    assert db.execute(select(Session).where(Session.user_id == teacher_and_class.id)).scalars().all() == []
    assert c.get("/me", follow_redirects=False).status_code == 303   # phiên chết


def test_dang_nhap_tai_khoan_bi_khoa_tra_423(anon_client, admin_client, teacher_and_class, db):
    admin_client.post(f"/admin/users/{teacher_and_class.id}/lock",
                      data={"_csrf": csrf_of(admin_client)}, follow_redirects=False)
    r = anon_client.post("/auth/login",
                         data={"email": teacher_and_class.email, "password": PASSWORD,
                               "_csrf": csrf_of(anon_client)}, follow_redirects=False)
    assert r.status_code == 423


def test_dat_lai_mat_khau_thi_mat_khau_cu_het_hieu_luc(admin_client, db, teacher_and_class, anon_client):
    r = admin_client.post(f"/admin/users/{teacher_and_class.id}/reset-password",
                          data={"new_password": "matkhaumoi123", "_csrf": csrf_of(admin_client)},
                          follow_redirects=False)
    assert r.status_code == 303

    old = anon_client.post("/auth/login",
                           data={"email": teacher_and_class.email, "password": PASSWORD,
                                 "_csrf": csrf_of(anon_client)}, follow_redirects=False)
    assert old.status_code == 401

    new = anon_client.post("/auth/login",
                           data={"email": teacher_and_class.email, "password": "matkhaumoi123",
                                 "_csrf": csrf_of(anon_client)}, follow_redirects=False)
    assert new.status_code == 303


def test_giao_vien_khong_vao_duoc_trang_quan_tri(teacher_client):
    assert teacher_client.get("/admin/users", follow_redirects=False).status_code == 403


def _xlsx(rows: list[list]) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    header = ["skill", "prompt", "option_a", "option_b", "option_c", "option_d",
              "correct_key", "explanation"]
    ws.append(header)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _lesson(db) -> Lesson:
    from app.seed import ensure_demo_unit

    ensure_demo_unit(db)
    unit = db.execute(select(Unit).where(Unit.grade == 8)).scalars().first()
    return db.execute(select(Lesson).where(Lesson.unit_id == unit.id, Lesson.code == "U1-L2")).scalar_one()


def test_import_excel_bo_dong_loi_va_bao_so_dong(admin_client, db):
    lesson = _lesson(db)
    before = len(db.execute(select(Question).where(Question.lesson_id == lesson.id)).scalars().all())

    data = _xlsx([
        ["grammar", "Câu tốt 1 ______ fine.", "is", "are", "be", "been", "A", "giải thích 1"],
        ["grammar", "Câu tốt 2 ______ fine.", "is", "are", "be", "been", "B", ""],
        ["sai_skill", "Câu lỗi skill", "a", "b", "c", "d", "A", ""],       # lỗi 1
        ["grammar", "", "a", "b", "c", "d", "A", ""],                     # lỗi 2: thiếu prompt
        ["grammar", "Câu lỗi key", "a", "b", "c", "d", "Z", ""],          # lỗi 3: key sai
        ["grammar", "Câu thiếu option", "a", "", "c", "d", "A", ""],      # lỗi 4
    ])
    r = admin_client.post("/admin/questions/import",
                          data={"lesson_id": str(lesson.id), "_csrf": csrf_of(admin_client)},
                          files={"file": ("cau-hoi.xlsx", data,
                                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert r.status_code == 200
    assert "câu hợp lệ đã thêm" in r.text
    assert "dòng lỗi bị bỏ qua" in r.text

    db.expire_all()
    after = len(db.execute(select(Question).where(Question.lesson_id == lesson.id)).scalars().all())
    assert after - before == 2


def test_import_file_sai_dinh_dang_bi_tu_choi(admin_client, db):
    lesson = _lesson(db)
    r = admin_client.post("/admin/questions/import",
                          data={"lesson_id": str(lesson.id), "_csrf": csrf_of(admin_client)},
                          files={"file": ("cau-hoi.csv", b"a,b,c", "text/csv")},
                          follow_redirects=True)
    assert "Chỉ nhận file .xlsx" in r.text


def test_import_file_thieu_cot_bao_ro(admin_client, db):
    from openpyxl import Workbook

    lesson = _lesson(db)
    wb = Workbook()
    wb.active.append(["prompt", "correct_key"])
    buf = io.BytesIO()
    wb.save(buf)

    r = admin_client.post("/admin/questions/import",
                          data={"lesson_id": str(lesson.id), "_csrf": csrf_of(admin_client)},
                          files={"file": ("thieu-cot.xlsx", buf.getvalue(),
                                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert "Thiếu cột" in r.text
