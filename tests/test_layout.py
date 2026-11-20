"""Test engine bóc tách kích thước."""
from __future__ import annotations

import pytest

from xingfacad.catalog import load_system
from xingfacad.layout import build_item, default_panels
from xingfacad.models import ItemSpec, PanelSpec, TransomSpec


@pytest.fixture()
def system_65(sandbox):
    return load_system("XF65")


@pytest.fixture()
def system_93(sandbox):
    return load_system("XF93")


def casement(width=1800, height=2200):
    return ItemSpec(
        tag="C1",
        type="casement",
        width_mm=width,
        height_mm=height,
        panels=[
            PanelSpec(kind="sash", open="out", dir="left", ratio=1),
            PanelSpec(kind="sash", open="out", dir="right", ratio=1),
        ],
    )


def test_frame_lengths_miter45(system_65):
    result = build_item(casement(), system_65)
    frame_lengths = sorted(piece.length_mm for piece in result.pieces if piece.profile_key == "frame")
    assert frame_lengths == [1800.0, 1800.0, 2200.0, 2200.0]
    assert all(piece.cut_a == "45" for piece in result.pieces if piece.profile_key == "frame")
    mullion = [piece for piece in result.pieces if piece.profile_key == "mullion"]
    assert len(mullion) == 1
    assert mullion[0].length_mm == 2200 - 2 * 55
    assert mullion[0].cut_a == "90"


def test_leaf_and_glass_sizes(system_65):
    result = build_item(casement(), system_65)
    assert result.leaves == 2
    leaf_w = (1800 - 2 * 55 - 45) / 2 - 2 * 6
    leaf_h = 2200 - 2 * 55 - 2 * 6
    sash_lengths = [piece.length_mm for piece in result.pieces if piece.profile_key == "sash"]
    assert sash_lengths.count(round(leaf_w, 1)) == 4
    assert sash_lengths.count(round(leaf_h, 1)) == 4
    glass = result.glass[0]
    assert glass.width_mm == round(leaf_w - 2 * 60 + 2 * 12 - 4, 1)
    assert glass.height_mm == round(leaf_h - 2 * 60 + 2 * 12 - 4, 1)
    assert len(result.panes3d) == 2


def test_weight_matches_manual_sum(system_65):
    result = build_item(casement(), system_65)
    manual = sum(piece.length_mm * piece.qty / 1000 * piece.kg_per_m for piece in result.pieces)
    assert result.alum_kg == pytest.approx(manual, rel=1e-9)
    assert result.alum_kg == pytest.approx(30.30, abs=0.05)


def test_transom_creates_fixed_band(system_65):
    item = casement(1400, 2200)
    item.transoms = [TransomSpec(orientation="h", at_mm=500, band_above="fixed")]
    result = build_item(item, system_65)
    assert result.cells == 4
    assert result.leaves == 2
    assert len(result.cell_rects) == 2
    transoms = [piece for piece in result.pieces if piece.profile_key == "transom"]
    assert len(transoms) == 1
    assert transoms[0].length_mm == 1400 - 2 * 55


def test_butt90_frame(sandbox):
    system = load_system("XF65").model_copy(deep=True)
    system.joint = "butt90"
    result = build_item(casement(1000, 1200), system)
    horizontals = [p.length_mm for p in result.pieces if p.profile_key == "frame" and p.cut_a == "90"]
    assert sorted(horizontals) == [1000 - 2 * 55, 1000 - 2 * 55, 1200, 1200]


def test_sliding_overlap(system_93):
    item = ItemSpec(
        tag="C3",
        type="sliding",
        width_mm=2400,
        height_mm=1800,
        panels=[PanelSpec(kind="sash", open="slide", dir="none", ratio=1) for _ in range(2)],
    )
    result = build_item(item, system_93)
    opening = 2400 - 2 * 60
    gap = 5
    leaf_w = (opening + 30) / 2 - 2 * gap
    leaf_h = 1800 - 40 - 45 - 2 * gap
    assert result.leaves == 2
    sash_lengths = {round(p.length_mm, 1) for p in result.pieces if p.profile_key == "sash"}
    assert sash_lengths == {round(leaf_w, 1), round(leaf_h, 1)}
    tracks = [p for p in result.pieces if p.profile_key in ("track_top", "track_bottom")]
    assert len(tracks) == 2
    assert all(p.length_mm == 2400 - 2 * 60 for p in tracks)


def test_default_panels_by_width(system_65):
    wide = ItemSpec(tag="C9", type="casement", width_mm=3000, height_mm=2200)
    panels = default_panels(wide, system_65)
    assert len(panels) == 3
    fixed_item = ItemSpec(tag="F9", type="fixed", width_mm=1200, height_mm=1500)
    assert default_panels(fixed_item, system_65)[0].kind == "fixed"


def test_warning_when_panel_too_wide(system_65):
    item = casement(4000, 2400)
    result = build_item(item, system_65)
    assert any("diện tích" in warning for warning in result.warnings)


def test_default_hinge_and_lock_counts(system_65):
    result = build_item(casement(), system_65)
    counts = {line.key: line.qty for line in result.hardware}
    assert counts["hinge"] == 6  # 3 bản lề × 2 cánh
    assert counts["lock"] == 2


def test_hinge_and_lock_override(system_65):
    item = casement()
    item.hinge_type = "hinge_6in"
    item.hinge_count = 4
    item.lock_type = "lock_multi2"
    result = build_item(item, system_65)
    counts = {line.key: line.qty for line in result.hardware}
    assert counts["hinge_6in"] == 8  # 4 × 2 cánh
    assert counts["lock_multi2"] == 2
    assert "hinge" not in counts
    assert "lock" not in counts
    hinge_line = next(line for line in result.hardware if line.key == "hinge_6in")
    assert hinge_line.price == 75000
    assert "6 inch" in hinge_line.name


def test_zero_hinges(system_65):
    item = casement()
    item.hinge_count = 0
    result = build_item(item, system_65)
    assert not any("hinge" in line.key for line in result.hardware)
    assert any(line.key == "lock" for line in result.hardware)


def test_no_lock_selected(system_65):
    item = casement()
    item.lock_type = "none"
    result = build_item(item, system_65)
    assert not any("lock" in line.key for line in result.hardware)


def test_unknown_hardware_key_warns(system_65):
    item = casement()
    item.hinge_type = "hinge_khong_co"
    result = build_item(item, system_65)
    assert any("không có trong catalogue" in warning for warning in result.warnings)


def test_hardware_3d_for_casement(system_65):
    item = casement()
    item.hinge_count = 3
    item.hinge_type = "hinge_3d"
    item.lock_type = "lock_multi2"
    result = build_item(item, system_65)
    hinges = [hw for hw in result.hardware3d if hw.kind == "hinge"]
    locks = [hw for hw in result.hardware3d if hw.kind == "lock"]
    assert len(hinges) == 6  # 3 × 2 cánh
    assert len(locks) == 2
    assert all(hw.label == "hinge_3d" for hw in hinges)
    # bản lề trái nằm ngoài mép trái cánh, bản lề phải nằm ngoài mép phải
    left_leaf_hinges = [hw for hw in hinges if hw.x < 900]
    assert left_leaf_hinges and min(hw.x for hw in left_leaf_hinges) < 120
    # khóa nằm trong khoảng chiều cao cánh
    assert all(0 < hw.z < 2200 for hw in locks)


def test_hardware_3d_sliding_wheels(system_93):
    item = ItemSpec(
        tag="C3",
        type="sliding",
        width_mm=2400,
        height_mm=1800,
        panels=[PanelSpec(kind="sash", open="slide", dir="none", ratio=1) for _ in range(2)],
    )
    result = build_item(item, system_93)
    wheels = [hw for hw in result.hardware3d if hw.kind == "wheel"]
    locks = [hw for hw in result.hardware3d if hw.kind == "lock"]
    assert len(wheels) == 4  # 2 bánh × 2 cánh
    assert len(locks) == 2
    assert all(hw.z < 200 for hw in wheels)


def test_hardware_3d_can_be_disabled(system_65):
    item = casement()
    item.hinge_count = 0
    item.lock_type = "none"
    result = build_item(item, system_65)
    assert result.hardware3d == []


def test_too_small_raises(system_65):
    item = ItemSpec(tag="X1", type="casement", width_mm=150, height_mm=150)
    with pytest.raises(ValueError):
        build_item(item, system_65)
