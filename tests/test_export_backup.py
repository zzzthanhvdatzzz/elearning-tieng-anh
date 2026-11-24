"""Test xuất bảng điểm Excel, sao lưu/khôi phục CSDL và lọc hàng đợi chấm."""
import importlib.util
import sqlite3
from pathlib import Path

from sqlalchemy import select

from app.models import User
from app.seed import ensure_demo_unit

ROOT = Path(__file__).resolve().parent.parent


def test_xuat_bang_diem_lop_ra_excel(student, db, teacher_client, teacher_and_class):
    import io

    from openpyxl import load_workbook

    from app.models import Class

    ensure_demo_unit(db)
    klass = db.execute(select(Class).where(Class.join_code == "TEST01")).scalar_one()
    r = teacher_client.get(f"/api/teacher/classes/{klass.id}/report.xlsx")
    assert r.status_code == 200, r.text
    assert "spreadsheetml" in r.headers["content-type"]
    assert "attachment" in r.headers["content-disposition"]

    wb = load_workbook(io.BytesIO(r.content))
    ws = wb.active
    header = [c.value for c in ws[1]]
    assert header[:3] == ["Học sinh", "Email", "CEFR"]
    assert ws.max_row >= 2
    names = [ws.cell(row=i, column=1).value for i in range(2, ws.max_row + 1)]
    assert any(n and "Học Sinh" in n for n in names)


def test_giao_vien_khac_khong_xuat_duoc_bang_diem(student, db, teacher_and_class):
    from app.models import Class
    from tests.conftest import client_for
    from app.services.security import hash_password
    from tests.conftest import PASSWORD

    other = User(email="gv.xuat@test.vn", password_hash=hash_password(PASSWORD),
                 full_name="GV Khác", role="teacher")
    db.add(other)
    db.commit()
    klass = db.execute(select(Class).where(Class.join_code == "TEST01")).scalar_one()
    c = client_for(other.email)
    assert c.get(f"/api/teacher/classes/{klass.id}/report.xlsx").status_code == 404


def test_sao_luu_va_khoi_phuc_csdl(tmp_path):
    spec = importlib.util.spec_from_file_location("backup_db", ROOT / "scripts" / "backup_db.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    db_file = tmp_path / "app.db"
    con = sqlite3.connect(db_file)
    con.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    con.execute("INSERT INTO t (v) VALUES ('trước khi sao lưu')")
    con.commit()
    con.close()

    saved = mod.backup(db_file, tmp_path / "backups")
    assert saved.exists() and saved.stat().st_size > 0

    # ghi bậy sau khi sao lưu
    con = sqlite3.connect(db_file)
    con.execute("DELETE FROM t")
    con.commit()
    con.close()

    safety = mod.restore(saved, db_file)
    assert safety is not None and safety.exists()
    con = sqlite3.connect(db_file)
    rows = con.execute("SELECT v FROM t").fetchall()
    con.close()
    assert rows == [("trước khi sao lưu",)]


def test_don_ban_sao_luu_cu(tmp_path):
    spec = importlib.util.spec_from_file_location("backup_db2", ROOT / "scripts" / "backup_db.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    out = tmp_path / "backups"
    out.mkdir()
    for i in range(5):
        (out / f"app-2026010{i}-000000.db").write_bytes(b"x")
    removed = mod.prune(out, keep=2)
    assert len(removed) == 3
    assert len(list(out.glob("app-*.db"))) == 2


def test_loc_hang_doi_cham_theo_ten(student, db, student_client, teacher_client):
    from app.models import Lesson, Unit
    from app.services.writing import ensure_writing_assignment

    ensure_demo_unit(db)
    unit = db.execute(select(Unit).where(Unit.grade == 8)).scalars().first()
    lesson = db.execute(select(Lesson).where(Lesson.unit_id == unit.id,
                                            Lesson.code == "U1-L1")).scalar_one()
    from app.models import Class as Klass

    klass = db.execute(select(Klass).where(Klass.join_code == "TEST01")).scalar_one()
    ensure_writing_assignment(db, klass, lesson)
    student_client.post(f"/api/writing/{lesson.id}/submit",
                        json={"text": ("My neighbourhood is quiet and clean. There is a small market, "
                                       "a temple and a lake near my house. People here are friendly, "
                                       "and the air is fresh every morning.")},
                        headers={"X-Requested-With": "fetch"})

    all_items = teacher_client.get("/api/teacher/submissions").json()["items"]
    assert len(all_items) >= 1

    hit = teacher_client.get("/api/teacher/submissions?q=học sinh").json()["items"]
    assert len(hit) == len(all_items)
    miss = teacher_client.get("/api/teacher/submissions?q=khong-ai-ten-nay").json()["items"]
    assert miss == []
