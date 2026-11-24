"""Test giữ theme Meadowbell đồng bộ và không phụ thuộc ảnh ngoài.

Bối cảnh: theme bị chép tay sang hai nơi (Next + template Jinja) và hero từng trỏ vào CDN
của bên thứ ba — buổi demo mà CDN đổi link là hero trắng.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_sync():
    spec = importlib.util.spec_from_file_location(
        "sync_meadow_css", ROOT / "scripts" / "sync_meadow_css.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ban_jinja_khop_voi_ban_next():
    mod = _load_sync()
    expected = mod.render()
    current = mod.DST.read_text(encoding="utf-8")
    assert current == expected, (
        "app/static/css/meadow.css lệch với frontend/app/meadow.css — "
        "chạy: .venv/bin/python scripts/sync_meadow_css.py")


def test_css_khong_hotlink_anh_ngoai():
    for path in (ROOT / "frontend/app/meadow.css", ROOT / "app/static/css/meadow.css"):
        text = path.read_text(encoding="utf-8")
        assert "http://" not in text and "https://" not in text, f"{path} còn URL ngoài"


def test_anh_theme_ton_tai_o_ca_hai_ban():
    for base in (ROOT / "frontend/public/meadow", ROOT / "app/static/img/meadow"):
        for name in ("hero.jpg", "step-1.webp", "step-2.webp", "step-3.webp"):
            f = base / name
            assert f.exists(), f"thiếu ảnh {f}"
            assert f.stat().st_size > 20_000, f"ảnh {f} quá nhỏ, có thể tải lỗi"


def test_hero_da_duoc_toi_uu_dung_luong():
    hero = ROOT / "frontend/public/meadow/hero.jpg"
    assert hero.stat().st_size < 400_000, "hero.jpg nên < 400 KB để tải nhanh trên wifi trường"
