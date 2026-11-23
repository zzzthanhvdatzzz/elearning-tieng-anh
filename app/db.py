"""Tầng dữ liệu — một engine duy nhất cho cả dev (SQLite) và production (PostgreSQL).

Chỉ có một chỗ tạo engine: nếu sau này đổi DATABASE_URL sang PostgreSQL thì không
phải sửa ở đâu khác.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")

# check_same_thread=False: FastAPI chạy endpoint `def` trong threadpool nên
# connection có thể bị dùng ở thread khác thread tạo ra nó.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Base cho toàn bộ model ở models/."""


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
