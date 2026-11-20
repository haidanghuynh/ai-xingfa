"""Test tối ưu cắt cây nhôm."""
from __future__ import annotations

import pytest

from xingfacad.optimizer import PieceRef, optimize


def test_all_pieces_placed_and_capacity_respected():
    pieces = [PieceRef(tag="C1", profile_code="XF65-KB", length_mm=1800) for _ in range(7)]
    groups = optimize(pieces, stock_lengths=[6500], kerf_mm=5, end_trim_mm=30)
    assert len(groups) == 1
    placed = [piece for bar in groups[0].bars for piece in bar.pieces]
    assert len(placed) == 7
    usable = 6500 - 2 * 30
    for bar in groups[0].bars:
        assert bar.used_mm + 5 * len(bar.pieces) <= usable + 1e-6
        assert bar.waste_mm == pytest.approx(6500 - bar.used_mm)


def test_bar_count_is_reasonable():
    pieces = [PieceRef(tag="C1", profile_code="XF65-C", length_mm=1800) for _ in range(7)]
    groups = optimize(pieces, stock_lengths=[6500], kerf_mm=5, end_trim_mm=30)
    assert len(groups[0].bars) == 3


def test_oversize_piece_gets_own_bar():
    pieces = [
        PieceRef(tag="C1", profile_code="XF93-RD", length_mm=7000),
        PieceRef(tag="C1", profile_code="XF93-RD", length_mm=1000),
    ]
    groups = optimize(pieces, stock_lengths=[6500], kerf_mm=5, end_trim_mm=30)
    bars = groups[0].bars
    assert len(bars) == 2
    assert bars[0].pieces[0].length_mm == 7000


def test_group_by_profile_and_waste_percent():
    pieces = [
        PieceRef(tag="C1", profile_code="A", length_mm=1000),
        PieceRef(tag="C2", profile_code="B", length_mm=2000),
    ]
    groups = optimize(pieces, stock_lengths=[6500], kerf_mm=5, end_trim_mm=30)
    assert {group.profile_code for group in groups} == {"A", "B"}
    for group in groups:
        assert 0 <= group.waste_percent < 100
        assert group.total_used_mm > 0


def test_choose_stock_with_less_waste():
    pieces = [PieceRef(tag="C1", profile_code="A", length_mm=2900) for _ in range(2)]
    groups = optimize(pieces, stock_lengths=[5800, 6500], kerf_mm=5, end_trim_mm=30)
    assert groups[0].stock_mm in {5800, 6500}
    assert groups[0].total_waste_mm <= 6500 - 2 * 2900
