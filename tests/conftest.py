"""Cấu hình test: CSDL tạm + mỗi test một client riêng theo vai trò.

Đặt biến môi trường TRƯỚC khi import app.db, vì engine được tạo lúc import.
"""
import os
import tempfile
from pathlib import Path

_TMP_DB = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"
os.environ["DISABLE_JOBS"] = "1"                       # không chạy thread báo cáo tuần khi test
os.environ["EMAIL_OUT_DIR"] = str(Path(tempfile.mkdtemp()) / "weekly")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402,F401  (đăng ký toàn bộ bảng)
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Class, Enrollment, User  # noqa: E402
from app.seed import ensure_placement_content  # noqa: E402
from app.services.security import hash_password  # noqa: E402

PASSWORD = "matkhau123"


@pytest.fixture(autouse=True)
def _fresh_db():
    """Xoá sạch – tạo lại schema mỗi test.

    Vì sao không dùng chung một CSDL: một test chấm điểm sẽ làm hỏng test sau
    (bài nộp đã ở trạng thái graded). Cách ly theo test là rẻ nhất.
    """
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    s = SessionLocal()
    try:
        ensure_placement_content(s)
    finally:
        s.close()
    yield


@pytest.fixture()
def db():
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture()
def teacher_and_class(db):
    teacher = User(email="gv@test.vn", password_hash=hash_password(PASSWORD),
                   full_name="Giáo viên Test", role="teacher")
    db.add(teacher)
    db.flush()
    db.add(Class(name="Lớp Test", grade=8, join_code="TEST01", teacher_id=teacher.id))
    db.commit()
    return teacher


@pytest.fixture()
def other_teacher(db):
    t = User(email="gv2@test.vn", password_hash=hash_password(PASSWORD),
             full_name="Giáo viên Khác", role="teacher")
    db.add(t)
    db.commit()
    return t


@pytest.fixture()
def student(db, teacher_and_class):
    s = User(email="hs@test.vn", password_hash=hash_password(PASSWORD),
             full_name="Học Sinh Test", role="student")
    db.add(s)
    db.flush()
    klass = db.query(Class).filter_by(join_code="TEST01").one()
    db.add(Enrollment(class_id=klass.id, student_id=s.id))
    db.commit()
    return s


def csrf_of(client: TestClient) -> str:
    """Gọi một trang GET để server cấp cookie csrf, rồi trả token đó."""
    client.get("/auth/login")
    return client.cookies.get("csrf", "")


def login(client: TestClient, email: str, password: str = PASSWORD) -> None:
    token = csrf_of(client)
    r = client.post("/auth/login", data={"email": email, "password": password, "_csrf": token},
                    follow_redirects=False)
    assert r.status_code == 303, r.text


def client_for(email: str) -> TestClient:
    """Mỗi vai trò một TestClient riêng — KHÔNG dùng chung cookie jar (lỗi thật đã gặp)."""
    c = TestClient(app)
    login(c, email)
    return c


@pytest.fixture()
def anon_client():
    return TestClient(app)


@pytest.fixture()
def student_client(student):
    return client_for(student.email)


@pytest.fixture()
def teacher_client(teacher_and_class):
    return client_for(teacher_and_class.email)
