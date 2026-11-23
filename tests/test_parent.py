"""Test F3/F14 — phụ huynh liên kết, duyệt, xem báo cáo, job báo cáo tuần."""
import os
from pathlib import Path

from sqlalchemy import select

from app.models import Notification, ParentLink, User
from tests.conftest import PASSWORD, client_for, csrf_of, login


def _make_parent(client, email="ph@test.vn") -> None:
    r = client.post("/auth/register-parent",
                    data={"email": email, "password": PASSWORD, "full_name": "Phụ Huynh Test",
                          "_csrf": csrf_of(client)}, follow_redirects=False)
    assert r.status_code == 303, r.text


def test_phu_huynh_tu_dang_ky_va_vao_trang_rieng(anon_client):
    _make_parent(anon_client)
    r = anon_client.get("/parent")
    assert r.status_code == 200
    assert "Liên kết với tài khoản của con" in r.text


def test_gui_yeu_cau_lien_ket_thi_cho_duyet(student, db, anon_client):
    _make_parent(anon_client)
    r = anon_client.post("/parent/link",
                         data={"student_email": student.email, "_csrf": csrf_of(anon_client)},
                         follow_redirects=True)
    assert r.status_code == 200
    link = db.execute(select(ParentLink)).scalar_one()
    assert link.status == "pending"

    # BR3: chưa duyệt thì không xem được báo cáo
    assert anon_client.get(f"/parent/report/{student.id}").status_code == 403


def test_giao_vien_duyet_thi_phu_huynh_xem_duoc_bao_cao(student, db, anon_client, teacher_client):
    _make_parent(anon_client)
    anon_client.post("/parent/link", data={"student_email": student.email,
                                           "_csrf": csrf_of(anon_client)}, follow_redirects=True)

    queue = teacher_client.get("/teacher/parents")
    assert queue.status_code == 200
    assert "Phụ Huynh Test" in queue.text

    link = db.execute(select(ParentLink)).scalar_one()
    r = teacher_client.post(f"/teacher/parents/{link.id}/approve",
                            data={"_csrf": csrf_of(teacher_client)}, follow_redirects=False)
    assert r.status_code == 303

    page = anon_client.get(f"/parent/report/{student.id}")
    assert page.status_code == 200
    assert "Điểm theo kỹ năng" in page.text


def test_tu_choi_thi_van_khong_xem_duoc(student, db, anon_client, teacher_client):
    _make_parent(anon_client)
    anon_client.post("/parent/link", data={"student_email": student.email,
                                           "_csrf": csrf_of(anon_client)}, follow_redirects=True)
    link = db.execute(select(ParentLink)).scalar_one()
    teacher_client.post(f"/teacher/parents/{link.id}/reject",
                        data={"_csrf": csrf_of(teacher_client)}, follow_redirects=False)

    assert anon_client.get(f"/parent/report/{student.id}").status_code == 403


def test_huy_lien_ket_thi_mat_quyen_ngay(student, db, anon_client, teacher_client):
    _make_parent(anon_client)
    anon_client.post("/parent/link", data={"student_email": student.email,
                                           "_csrf": csrf_of(anon_client)}, follow_redirects=True)
    link = db.execute(select(ParentLink)).scalar_one()
    teacher_client.post(f"/teacher/parents/{link.id}/approve",
                        data={"_csrf": csrf_of(teacher_client)}, follow_redirects=False)
    assert anon_client.get(f"/parent/report/{student.id}").status_code == 200

    anon_client.post(f"/parent/unlink/{student.id}", data={"_csrf": csrf_of(anon_client)},
                     follow_redirects=False)
    assert anon_client.get(f"/parent/report/{student.id}").status_code == 403


def test_giao_vien_lop_khac_khong_duyet_duoc(student, db, anon_client, other_teacher):
    _make_parent(anon_client)
    anon_client.post("/parent/link", data={"student_email": student.email,
                                           "_csrf": csrf_of(anon_client)}, follow_redirects=True)
    link = db.execute(select(ParentLink)).scalar_one()

    c = client_for(other_teacher.email)
    c.post(f"/teacher/parents/{link.id}/approve", data={"_csrf": csrf_of(c)},
           follow_redirects=False)
    db.expire_all()
    assert db.get(ParentLink, link.id).status == "pending"   # vẫn chờ


def test_job_bao_cao_tuan_idempotent_va_sinh_file_eml(student, db, anon_client, teacher_client):
    from app.jobs import weekly_email

    _make_parent(anon_client)
    anon_client.post("/parent/link", data={"student_email": student.email,
                                           "_csrf": csrf_of(anon_client)}, follow_redirects=True)
    link = db.execute(select(ParentLink)).scalar_one()
    teacher_client.post(f"/teacher/parents/{link.id}/approve",
                        data={"_csrf": csrf_of(teacher_client)}, follow_redirects=False)

    first = weekly_email.run_weekly(send=False)
    assert first["created"] == 1
    assert first["smtp"] is False          # chưa cấu hình SMTP → không nói dối là đã gửi

    files = list(Path(first["out_dir"]).glob("*.eml"))
    assert len(files) == 1
    content = files[0].read_text(errors="replace")
    assert "Báo cáo tuần này" in content
    assert "Học Sinh Test" in content

    # Chạy lại: không nhân đôi tệp, không nhân đôi thông báo
    second = weekly_email.run_weekly(send=False)
    assert second["created"] == 0 and second["skipped"] == 1
    assert len(list(Path(first["out_dir"]).glob("*.eml"))) == 1
    # Chỉ đếm thông báo của job tuần (việc duyệt phụ huynh cũng sinh 1 thông báo riêng)
    job_notes = [n for n in db.execute(select(Notification)).scalars()
                 if "báo cáo tuần" in n.title.lower()]
    assert len(job_notes) == 1
