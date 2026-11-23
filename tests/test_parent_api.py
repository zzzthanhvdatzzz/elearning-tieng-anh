"""Test hàng đợi liên kết phụ huynh trên API JSON (Next.js).

Lỗi thật đã gặp: endpoint dùng `link.created_at` trong khi model chỉ có `requested_at`
→ 500 Internal Server Error, trang /teacher/parents của giáo viên hỏng hoàn toàn.
Test này khoá lại cả hình dạng dữ liệu trả về.
"""
from datetime import datetime, timedelta

from sqlalchemy import select

from app.models import ParentLink
from app.services.security import hash_password
from tests.conftest import PASSWORD, client_for


def _make_pending(db, student, teacher_and_class):
    parent = type(student)(
        email="ph.api@test.vn", full_name="Phụ Huynh API", role="parent",
        password_hash=hash_password(PASSWORD),
    )
    db.add(parent)
    db.commit()
    db.add(ParentLink(parent_id=parent.id, student_id=student.id, status="pending",
                      requested_at=datetime.utcnow() - timedelta(hours=3)))
    db.commit()
    return parent


def _class_name(db):
    from app.models import Class

    return db.query(Class).filter_by(join_code="TEST01").one().name


def test_hang_doi_phu_huynh_tra_200_va_co_du_lieu(student, db, teacher_and_class, teacher_client):
    parent = _make_pending(db, student, teacher_and_class)

    r = teacher_client.get("/api/teacher/parent-requests")
    assert r.status_code == 200, r.text        # từng là 500 vì dùng sai tên cột
    items = r.json()["items"]
    assert len(items) == 1
    row = items[0]
    assert row["student"] == (student.full_name or student.email)
    assert row["student_id"] == student.id
    assert row["parent"] == parent.full_name
    assert row["parent_email"] == parent.email      # giáo viên cần xem email để xác minh
    assert row["klass"] == _class_name(db)
    assert row["at"]                                # có giờ gửi yêu cầu
    assert row["id"]


def test_duyet_qua_api_mo_quyen_xem_bao_cao(student, db, teacher_and_class, teacher_client):
    parent = _make_pending(db, student, teacher_and_class)
    link = db.execute(select(ParentLink)).scalar_one()

    parent_client = client_for(parent.email)
    assert parent_client.get(f"/api/parent/report/{student.id}").status_code == 403

    r = teacher_client.post(f"/api/teacher/parent-requests/{link.id}", json={"approve": True},
                            headers={"X-Requested-With": "fetch"})
    assert r.status_code == 200, r.text

    # Thiếu header CSRF thì phải bị chặn (hàng rào cho API JSON)
    assert teacher_client.post(f"/api/teacher/parent-requests/{link.id}",
                               json={"approve": True}).status_code == 403

    assert parent_client.get(f"/api/parent/report/{student.id}").status_code == 200
    assert teacher_client.get("/api/teacher/parent-requests").json()["items"] == []
    db.expire_all()
    assert db.get(ParentLink, link.id).status == "approved"
