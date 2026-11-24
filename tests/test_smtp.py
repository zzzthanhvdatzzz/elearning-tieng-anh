"""Test phần gửi email thật của job báo cáo tuần (F14).

Máy chủ SMTP được giả lập bằng monkeypatch — không cần tài khoản email thật, nhưng kiểm được
đúng thứ quan trọng: khi có SMTP_HOST thì hệ thống THỰC SỰ gọi send_message; khi SMTP lỗi thì
job ghi nhận `failed` chứ không chết và không đánh dấu đã gửi.
"""
import os

import pytest
from sqlalchemy import select

from app.jobs import weekly_email
from app.models import ParentLink


class FakeSMTP:
    sent: list = []
    raise_on_send: Exception | None = None

    def __init__(self, host, port, timeout=None):
        self.host, self.port, self.timeout = host, port, timeout
        FakeSMTP.instances.append(self)

    instances: list = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.tls = True

    def login(self, user, password):
        self.logged_in = (user, password)

    def send_message(self, msg):
        if FakeSMTP.raise_on_send:
            raise FakeSMTP.raise_on_send
        FakeSMTP.sent.append(msg)


@pytest.fixture()
def approved_parent(student, db, teacher_client, anon_client):
    from tests.conftest import csrf_of
    from app.models import User
    from app.services.security import hash_password
    from tests.conftest import PASSWORD

    parent = User(email="ph.smtp@test.vn", full_name="PH SMTP", role="parent",
                  password_hash=hash_password(PASSWORD))
    db.add(parent)
    db.commit()
    db.add(ParentLink(parent_id=parent.id, student_id=student.id, status="approved"))
    db.commit()
    return parent


def test_co_smtp_host_thi_gui_that(approved_parent, db, monkeypatch, tmp_path):
    monkeypatch.setattr(weekly_email, "OUT_DIR", tmp_path)
    monkeypatch.setattr(weekly_email.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setenv("SMTP_HOST", "smtp.test.vn")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "bot@test.vn")
    monkeypatch.setenv("SMTP_PASS", "secret")
    FakeSMTP.sent = []
    FakeSMTP.instances = []

    result = weekly_email.run_weekly(send=True)

    assert result["smtp"] is True
    assert result["created"] == 1
    assert result["failed"] == []
    assert len(FakeSMTP.sent) == 1
    msg = FakeSMTP.sent[0]
    assert msg["To"] == approved_parent.email
    assert "báo cáo tuần" in str(msg["Subject"]).lower()
    assert FakeSMTP.instances[0].logged_in == ("bot@test.vn", "secret")


def test_smtp_loi_thi_ghi_failed_chu_khong_chet(approved_parent, db, monkeypatch, tmp_path):
    monkeypatch.setattr(weekly_email, "OUT_DIR", tmp_path)
    monkeypatch.setattr(weekly_email.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setenv("SMTP_HOST", "smtp.hong.vn")
    FakeSMTP.sent = []
    FakeSMTP.raise_on_send = OSError("Không kết nối được SMTP")

    result = weekly_email.run_weekly(send=True)
    FakeSMTP.raise_on_send = None

    assert result["created"] == 1              # thư vẫn được ghi ra .eml
    assert len(result["failed"]) == 1
    assert "Không kết nối" in result["failed"][0]["error"]
    # chạy lại không gửi lặp (idempotent theo tuần)
    again = weekly_email.run_weekly(send=True)
    assert again["created"] == 0 and again["skipped"] == 1


def test_khong_co_smtp_thi_ghi_file_va_noi_that(approved_parent, db, monkeypatch, tmp_path):
    monkeypatch.setattr(weekly_email, "OUT_DIR", tmp_path)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    FakeSMTP.sent = []

    result = weekly_email.run_weekly(send=True)
    assert result["smtp"] is False        # không giả vờ đã gửi
    assert result["created"] == 1
    assert FakeSMTP.sent == []
    assert len(list(tmp_path.glob("*.eml"))) == 1
