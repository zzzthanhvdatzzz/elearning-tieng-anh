"""Jinja2 dùng chung cho mọi router + các hàm template cần (csrf, nhãn vai trò)."""
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.csrf import get_csrf
from app.services.security import ROLE_LABELS

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=TEMPLATE_DIR)
templates.env.globals["csrf_token"] = get_csrf
templates.env.globals["role_label"] = lambda role: ROLE_LABELS.get(role, role)
