"""Test cho services/scoring.py — viết TRƯỚC khi nối vào router.

Mỗi assert ứng với một quy tắc nghiệp vụ có mã: BR5, BR6, BR8, mục 3.9.
"""
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.services.scoring import (
    adjust_level,
    auto_score,
    cefr_from_score,
    days_late,
    final_score,
    grade_mcq,
    placement_total,
    rubric_total,
    with_late_penalty,
)


def test_br5_diem_tu_dong_lam_tron_mot_chu_so():
    assert auto_score(7, 10) == 7.0
    assert auto_score(2, 3) == 6.7  # 6.666… → 6,7
    assert auto_score(10, 25) == 4.0
    assert auto_score(0, 10) == 0.0


def test_br5_khong_chia_cho_khong():
    assert auto_score(0, 0) == 0.0


def test_cham_trac_nghiem_khop_dap_an_khong_phan_biet_hoa_thuong():
    qs = [
        SimpleNamespace(id=1, correct_key="A"),
        SimpleNamespace(id=2, correct_key="C"),
        SimpleNamespace(id=3, correct_key="B"),
    ]
    correct, detail = grade_mcq({1: "a", 2: "D", 3: ""}, qs)
    assert correct == 1
    assert [d["is_correct"] for d in detail] == [True, False, False]


def test_br6_thieu_mot_phan_thi_khong_tra_diem_cuoi():
    assert final_score(None, 7.0) is None
    assert final_score(8.0, None) is None
    assert final_score(None, None) is None


def test_br6_cong_thuc_07_03():
    assert final_score(8.0, 6.0) == 7.4
    assert final_score(10.0, 10.0) == 10.0
    assert final_score(0.0, 5.0) == 1.5


def test_br8_tru_muon_10_phan_tram_moi_ngay_toi_da_ba_ngay():
    assert with_late_penalty(8.0, 0) == 8.0
    assert with_late_penalty(8.0, 1) == 7.2
    assert with_late_penalty(8.0, 3) == 5.6
    assert with_late_penalty(8.0, 4) == 0.0  # quá ba ngày → 0


def test_dem_so_ngay_tre():
    deadline = datetime(2026, 3, 1, 23, 59)
    assert days_late(deadline - timedelta(minutes=1), deadline) == 0
    assert days_late(deadline + timedelta(minutes=1), deadline) == 1
    assert days_late(deadline + timedelta(days=2), deadline) == 2
    assert days_late(None, deadline) == 0


@pytest.mark.parametrize(
    "score,level",
    [(0.0, "A1"), (3.9, "A1"), (4.0, "A2"), (5.9, "A2"), (6.0, "B1"), (7.9, "B1"), (8.0, "B2"), (10.0, "B2")],
)
def test_nguong_cefr_muc_3_9(score, level):
    assert cefr_from_score(score) == level


def test_xep_trinh_do_cho_toi_khi_co_bai_viet():
    assert placement_total(8.0, None) is None  # chờ chấm
    assert placement_total(8.0, 6.0) == 7.4


def test_giao_vien_dieu_chinh_toi_da_mot_bac_va_khong_vuot_khung():
    assert adjust_level("B1", -1) == "A2"
    assert adjust_level("B1", 1) == "B2"
    assert adjust_level("A1", -1) == "A1"
    assert adjust_level("B2", 1) == "B2"


def test_rubric_bon_tieu_chi_thang_10():
    assert rubric_total([2.5, 2.5, 2.5, 2.5]) == 10.0
    assert rubric_total([2.0, 1.5, 2.0, 0.0]) == 5.5
    assert rubric_total([3.0, 3.0, 3.0, 3.0]) == 10.0  # kẹp trần
