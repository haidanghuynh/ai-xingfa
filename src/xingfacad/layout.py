"""Bóc tách kích thước: ItemSpec + SystemDef -> bảng cắt, kính, phụ kiện, hình học 3D."""
from __future__ import annotations

import math

from .catalog import hardware_config, resolve_glass
from .models import (
    Bar3D,
    CutPiece,
    GlassPiece,
    GlassSpec,
    Hardware3D,
    HardwareLine,
    ItemResult,
    ItemSpec,
    Pane3D,
    PanelSpec,
    ProfileDef,
    SystemDef,
    TransomSpec,
)

SLIDING_TYPES = {"sliding", "door_sliding"}
HINGE_LEN = 80.0


# --------------------------------------------------------------------------- #
# Hình học cơ bản (mặt phẳng XZ, ép theo trục Y)
# --------------------------------------------------------------------------- #
def rect(x: float, z: float, w: float, h: float) -> list[list[float]]:
    return [[x, z], [x + w, z], [x + w, z + h], [x, z + h]]


def miter_frame(x: float, z: float, w: float, h: float, t: float) -> dict[str, list[list[float]]]:
    """4 thanh của khung hàn góc 45°. `t` là mặt cắt nhìn thấy của thanh."""
    return {
        "top": [[x + t, z + h - t], [x + w - t, z + h - t], [x + w, z + h], [x, z + h]],
        "bottom": [[x, z], [x + w, z], [x + w - t, z + t], [x + t, z + t]],
        "left": [[x, z], [x + t, z + t], [x + t, z + h - t], [x, z + h]],
        "right": [[x + w, z], [x + w, z + h], [x + w - t, z + h - t], [x + w - t, z + t]],
    }


def butt_frame(x: float, z: float, w: float, h: float, t: float) -> dict[str, list[list[float]]]:
    """Khung ghép vuông góc: thanh đứng chạy suốt, thanh ngang nằm giữa."""
    return {
        "top": rect(x + t, z + h - t, w - 2 * t, t),
        "bottom": rect(x + t, z, w - 2 * t, t),
        "left": rect(x, z, t, h),
        "right": rect(x + w - t, z, t, h),
    }


def frame_geometry(
    x: float, z: float, w: float, h: float, t: float, joint: str
) -> tuple[dict[str, list[list[float]]], dict[str, float]]:
    """Trả về (polygon từng thanh, chiều dài cắt từng thanh)."""
    if joint == "miter45":
        return miter_frame(x, z, w, h, t), {"top": w, "bottom": w, "left": h, "right": h}
    return butt_frame(x, z, w, h, t), {
        "top": w - 2 * t,
        "bottom": w - 2 * t,
        "left": h,
        "right": h,
    }


def default_panels(item: ItemSpec, system: SystemDef) -> list[PanelSpec]:
    """Chia cánh mặc định theo loại cửa và chiều rộng (người dùng có thể ghi đè)."""
    width = item.width_mm
    if item.type == "fixed":
        return [PanelSpec(kind="fixed", open="none", dir="none", ratio=1)]
    if item.type in SLIDING_TYPES:
        count = 2 if width <= 1800 else 3 if width <= 3000 else 4
        return [PanelSpec(kind="sash", open="slide", dir="none", ratio=1) for _ in range(count)]
    count = 1 if width <= 900 else 2 if width <= 2100 else 3
    panels: list[PanelSpec] = []
    for index in range(count):
        side = "left" if index % 2 == 0 else "right"
        panels.append(PanelSpec(kind="sash", open="out", dir=side, ratio=1))
    return panels


def _cut_angles(joint: str) -> tuple[str, str]:
    return ("45", "45") if joint == "miter45" else ("90", "90")


def hinge_positions(count: int) -> list[float]:
    """Vị trí bản lề theo tỷ lệ chiều cao cánh (0..1)."""
    if count <= 0:
        return []
    if count == 1:
        return [0.5]
    if count == 2:
        return [0.12, 0.88]
    if count == 3:
        return [0.12, 0.5, 0.88]
    if count == 4:
        return [0.1, 0.37, 0.63, 0.9]
    step = 0.8 / (count - 1)
    return [round(0.1 + step * index, 4) for index in range(count)]


def _band_kind(band_index: int, cut_transoms: list[tuple[float, TransomSpec, float]], panel_kind: str) -> str:
    above = cut_transoms[band_index][1] if band_index < len(cut_transoms) else None
    below = cut_transoms[band_index - 1][1] if band_index - 1 >= 0 else None
    if below is not None and below.band_below:
        return below.band_below
    if above is not None and above.band_above:
        return above.band_above
    return panel_kind


def build_item(
    item: ItemSpec, system: SystemDef, project_glass: GlassSpec | None = None
) -> ItemResult:
    """Bóc tách 1 hạng mục cửa thành bảng cắt + kính + phụ kiện + hình học 3D."""
    rules = system.rules
    frame_p = system.profiles["frame"]
    sash_p = system.profile("sash")
    mull_p = system.profile("mullion")
    transom_p = system.profile("transom")
    glass = resolve_glass(project_glass, item.glass)

    fw, fd = frame_p.width_mm, frame_p.depth_mm
    sw, sd = sash_p.width_mm, sash_p.depth_mm
    mw = mull_p.width_mm
    joint = system.joint
    W, H = item.width_mm, item.height_mm
    gt = glass.thickness_mm
    rebate = rules.glass_rebate_mm
    clearance = rules.glass_clearance_mm

    pieces: list[CutPiece] = []
    bars: list[Bar3D] = []
    panes: list[Pane3D] = []
    hardware3d: list[Hardware3D] = []
    glass_pieces: list[GlassPiece] = []
    hw_counts: dict[str, float] = {}
    warnings: list[str] = []
    gasket_mm = 0.0
    miter_bars = 0

    def add_piece(
        profile: ProfileDef,
        length: float,
        qty: int = 1,
        cut: tuple[str, str] = ("45", "45"),
        note: str = "",
    ) -> None:
        nonlocal miter_bars
        if length <= 1:
            warnings.append(f"{item.tag}: thanh {profile.code} có chiều dài {length:.0f}mm không hợp lệ")
            return
        pieces.append(
            CutPiece(
                tag=item.tag,
                group=profile.key,
                profile_key=profile.key,
                profile_code=profile.code,
                profile_name=profile.name or profile.code,
                length_mm=round(length, 1),
                qty=qty,
                cut_a=cut[0],
                cut_b=cut[1],
                kg_per_m=profile.kg_per_m,
                note=note,
            )
        )
        if cut == ("45", "45"):
            miter_bars += qty

    def add_bar(
        profile: ProfileDef, polygon: list[list[float]], y0: float, y1: float, label: str = ""
    ) -> None:
        bars.append(
            Bar3D(
                group=profile.key,
                profile_code=profile.code,
                polygon=polygon,
                y0=y0,
                y1=y1,
                label=label,
            )
        )

    is_sliding = item.type in SLIDING_TYPES
    if is_sliding:
        head = system.profile("track_top")
        sill = system.profile("track_bottom")
        head_h, sill_h = head.width_mm, sill.width_mm
        add_piece(frame_p, H, 2, ("90", "90"), "Khung bao đứng")
        add_bar(frame_p, rect(0, 0, fw, H), 0, fd, "Khung bao trái")
        add_bar(frame_p, rect(W - fw, 0, fw, H), 0, fd, "Khung bao phải")
        add_piece(head, W - 2 * fw, 1, ("90", "90"), "Ray trên")
        add_bar(head, rect(fw, H - head_h, W - 2 * fw, head_h), 0, fd, "Ray trên")
        add_piece(sill, W - 2 * fw, 1, ("90", "90"), "Ray dưới")
        add_bar(sill, rect(fw, 0, W - 2 * fw, sill_h), 0, fd, "Ray dưới")
        Wi = W - 2 * fw
        Hi = H - head_h - sill_h
        z_base = sill_h
    else:
        polys, lengths = frame_geometry(0, 0, W, H, fw, joint)
        cut = _cut_angles(joint)
        add_piece(frame_p, lengths["top"], 1, cut, "Khung bao trên")
        add_piece(frame_p, lengths["bottom"], 1, cut, "Khung bao dưới")
        add_piece(frame_p, lengths["left"], 1, cut, "Khung bao trái")
        add_piece(frame_p, lengths["right"], 1, cut, "Khung bao phải")
        for name, label in (("top", "trên"), ("bottom", "dưới"), ("left", "trái"), ("right", "phải")):
            add_bar(frame_p, polys[name], 0, fd, f"Khung bao {label}")
        Wi, Hi = W - 2 * fw, H - 2 * fw
        z_base = fw

    if Wi <= 50 or Hi <= 50:
        raise ValueError(f"{item.tag}: kích thước {W:.0f}x{H:.0f} quá nhỏ so với tiết diện khung")

    panels = item.panels or default_panels(item, system)
    count = len(panels)
    ratio_sum = sum(panel.ratio for panel in panels)
    if ratio_sum <= 0:
        raise ValueError(f"{item.tag}: tổng tỷ lệ chia cánh phải > 0")

    overlap = max(rules.sash_overlap_mm, 0.0) if is_sliding else 0.0
    if is_sliding:
        total_w = Wi + (count - 1) * overlap
        col_ws = [total_w * panel.ratio / ratio_sum for panel in panels]
    else:
        available = Wi - (count - 1) * mw
        if available <= mw:
            raise ValueError(f"{item.tag}: quá nhiều đố cho chiều rộng khung {Wi:.0f}mm")
        col_ws = [available * panel.ratio / ratio_sum for panel in panels]

    col_xs: list[float] = []
    cursor = fw
    for index, col_w in enumerate(col_ws):
        col_xs.append(cursor)
        cursor += col_w + (mw if (not is_sliding and index < count - 1) else -overlap)

    if not is_sliding and count > 1:
        for index in range(count - 1):
            mx = col_xs[index] + col_ws[index]
            add_piece(mull_p, Hi, 1, ("90", "90"), "Đố đứng")
            add_bar(mull_p, rect(mx, z_base, mw, Hi), 0, fd, "Đố đứng")

    cut_transoms: list[tuple[float, TransomSpec, float]] = []
    for spec in sorted([t for t in item.transoms if t.orientation == "h"], key=lambda t: t.at_mm):
        profile = system.profiles.get(spec.profile) or transom_p
        thickness = profile.width_mm
        z_top = H - spec.at_mm - z_base
        if z_top - thickness <= 1 or z_top >= Hi - 1:
            warnings.append(f"{item.tag}: đố ngang tại {spec.at_mm:.0f}mm nằm ngoài vùng kính, đã bỏ qua")
            continue
        cut_transoms.append((z_top, spec, thickness))
        add_piece(profile, Wi, 1, ("90", "90"), "Đố ngang")
        add_bar(profile, rect(fw, z_base + z_top - thickness, Wi, thickness), 0, fd, "Đố ngang")
    if any(t.orientation == "v" for t in item.transoms):
        warnings.append(f"{item.tag}: đố đứng tự do chưa hỗ trợ, hãy chia bằng 'panels'")

    bands: list[tuple[float, float]] = []
    previous = 0.0
    for z_top, _spec, thickness in cut_transoms:
        bands.append((previous, z_top - thickness))
        previous = z_top
    bands.append((previous, Hi))

    hardware_map = hardware_config()
    per_leaf = hardware_map.get("per_leaf_by_type", {}).get(item.type, {})
    leaves = 0
    cells = 0
    leaf_rects: list[list[float]] = []
    leaf_dirs: list[str] = []
    cell_rects: list[list[float]] = []
    for col_index, (px, col_w) in enumerate(zip(col_xs, col_ws)):
        panel = panels[col_index]
        for band_index, (z0, z1) in enumerate(bands):
            cell_w = col_w
            cell_h = z1 - z0
            if cell_w <= 1 or cell_h <= 1:
                continue
            cells += 1
            kind = _band_kind(band_index, cut_transoms, panel.kind)
            if cell_w < rules.min_panel_width_mm:
                warnings.append(
                    f"{item.tag}: ô {col_index + 1} rộng {cell_w:.0f}mm dưới mức tối thiểu "
                    f"{rules.min_panel_width_mm:.0f}mm"
                )
            if cell_w * cell_h / 1_000_000 > rules.max_panel_area_m2:
                warnings.append(
                    f"{item.tag}: ô {col_index + 1} diện tích {cell_w * cell_h / 1_000_000:.2f}m2 > "
                    f"{rules.max_panel_area_m2:.2f}m2, nên chia thêm đố"
                )

            if kind == "sash":
                leaves += 1
                gap = rules.gap_frame_sash_mm
                leaf_w = cell_w - 2 * gap
                leaf_h = cell_h - 2 * gap
                if leaf_w <= 100 or leaf_h <= 100:
                    warnings.append(f"{item.tag}: cánh {col_index + 1} quá nhỏ ({leaf_w:.0f}x{leaf_h:.0f})")
                    continue
                leaf_x = px + gap
                leaf_z = z_base + z0 + gap
                sash_polys, sash_lengths = frame_geometry(leaf_x, leaf_z, leaf_w, leaf_h, sw, joint)
                sash_cut = _cut_angles(joint)
                if is_sliding:
                    y0 = 0.0 if col_index % 2 == 0 else min(max(rules.track_offset_mm, 1.0), max(fd - sd, 0.0))
                else:
                    inset = rules.sash_inset_mm
                    y0 = float(inset) if inset is not None else max((fd - sd) / 2, 0.0)
                for name, label in (("top", "trên"), ("bottom", "dưới"), ("left", "trái"), ("right", "phải")):
                    add_piece(sash_p, sash_lengths[name], 1, sash_cut, f"Cánh {col_index + 1} {label}")
                    add_bar(sash_p, sash_polys[name], y0, y0 + sd, f"Cánh {col_index + 1}")
                gw = leaf_w - 2 * sw + 2 * rebate - clearance
                gh = leaf_h - 2 * sw + 2 * rebate - clearance
                gx = leaf_x + sw - rebate + clearance / 2
                gz = leaf_z + sw - rebate + clearance / 2
                glass_y = y0 + max((sd - gt) / 2, 0.0)
                glass_note = f"Cánh {col_index + 1}"
                leaf_rects.append([leaf_x, leaf_z, leaf_w, leaf_h])
                leaf_dirs.append(panel.dir)

                hinge_key_leaf = (item.hinge_type or "hinge").strip().lower()
                if hinge_key_leaf in ("none", "khong", "không"):
                    hinge_qty_leaf = 0
                elif item.hinge_count is not None:
                    hinge_qty_leaf = int(item.hinge_count)
                else:
                    hinge_qty_leaf = int(per_leaf.get("hinge", 0) or 0)
                if hinge_qty_leaf > 0:
                    for fraction in hinge_positions(hinge_qty_leaf):
                        if panel.dir == "up":
                            hardware3d.append(
                                Hardware3D(
                                    kind="hinge",
                                    x=leaf_x + leaf_w * fraction - 40,
                                    y=y0 - 6,
                                    z=leaf_z + leaf_h - 26,
                                    w=80,
                                    h=26,
                                    d=12,
                                    label=hinge_key_leaf,
                                )
                            )
                        else:
                            hx = leaf_x + leaf_w - 14 if panel.dir == "right" else leaf_x - 12
                            hardware3d.append(
                                Hardware3D(
                                    kind="hinge",
                                    x=hx,
                                    y=y0 - 6,
                                    z=leaf_z + leaf_h * fraction - HINGE_LEN / 2,
                                    w=26,
                                    h=HINGE_LEN,
                                    d=12,
                                    label=hinge_key_leaf,
                                )
                            )

                lock_key_leaf = (item.lock_type or "lock").strip().lower()
                if lock_key_leaf not in ("none", "khong", "không") and float(per_leaf.get("lock", 0) or 0) > 0:
                    if is_sliding:
                        handle_x = leaf_x + leaf_w - 18 if col_index % 2 == 0 else leaf_x - 8
                    elif panel.dir == "right":
                        handle_x = leaf_x - 8
                    else:
                        handle_x = leaf_x + leaf_w - 18
                    hardware3d.append(
                        Hardware3D(
                            kind="lock",
                            x=handle_x,
                            y=y0 - 14,
                            z=leaf_z + leaf_h * 0.45,
                            w=26,
                            h=150,
                            d=16,
                            label=lock_key_leaf,
                        )
                    )

                if is_sliding:
                    for fraction in (0.18, 0.82):
                        hardware3d.append(
                            Hardware3D(
                                kind="wheel",
                                x=leaf_x + leaf_w * fraction - 20,
                                y=y0 + 4,
                                z=max(leaf_z - 18, 0),
                                w=40,
                                h=24,
                                d=24,
                                label="wheel",
                            )
                        )
            else:
                gw = cell_w + 2 * rebate - clearance
                gh = cell_h + 2 * rebate - clearance
                gx = px - rebate + clearance / 2
                gz = z_base + z0 - rebate + clearance / 2
                glass_y = max((fd - gt) / 2, 0.0)
                glass_note = f"Ô cố định {col_index + 1}"
                cell_rects.append([px, z_base + z0, cell_w, cell_h])

            if gw <= 50 or gh <= 50:
                warnings.append(f"{item.tag}: ô kính {col_index + 1} có kích thước không hợp lệ")
                continue
            panes.append(Pane3D(x=gx, y=glass_y, z=gz, w=gw, h=gh, t=gt, label=glass_note))
            glass_pieces.append(
                GlassPiece(
                    tag=item.tag,
                    key=glass.key,
                    name=glass.name,
                    thickness_mm=gt,
                    width_mm=round(gw, 1),
                    height_mm=round(gh, 1),
                    qty=1,
                    note=glass_note,
                    price_per_m2=float(glass.price_per_m2 or 0),
                )
            )
            gasket_mm += 2 * (gw + gh)
            if kind == "sash":
                for key, value in per_leaf.items():
                    if key in ("hinge", "lock") or not value:
                        continue
                    hw_counts[key] = hw_counts.get(key, 0) + float(value)

                hinge_key = (item.hinge_type or "").strip().lower() or "hinge"
                if hinge_key not in ("none", "khong", "không"):
                    hinge_qty = (
                        float(item.hinge_count)
                        if item.hinge_count is not None
                        else float(per_leaf.get("hinge", 0) or 0)
                    )
                    if hinge_qty > 0:
                        hw_counts[hinge_key] = hw_counts.get(hinge_key, 0) + hinge_qty

                lock_key = (item.lock_type or "").strip().lower() or "lock"
                if lock_key not in ("none", "khong", "không"):
                    lock_qty = float(per_leaf.get("lock", 0) or 0)
                    if lock_qty > 0:
                        hw_counts[lock_key] = hw_counts.get(lock_key, 0) + lock_qty

    components = hardware_map.get("components", {})
    gasket_m = gasket_mm / 1000 * (1 + float(hardware_map.get("gasket_waste_percent", 5)) / 100)
    if gasket_m > 0:
        hw_counts["gasket"] = hw_counts.get("gasket", 0) + gasket_m
        per_tube = max(float(hardware_map.get("silicone_m_per_tube", 8)), 1.0)
        hw_counts["silicone"] = hw_counts.get("silicone", 0) + max(1, math.ceil(gasket_m / per_tube))
    screw_per_bar = float(hardware_map.get("screw_per_bar", 1) or 0)
    if miter_bars and screw_per_bar:
        hw_counts["screw"] = hw_counts.get("screw", 0) + miter_bars * screw_per_bar

    hardware: list[HardwareLine] = []
    for key, qty in hw_counts.items():
        comp = components.get(key)
        if comp is None:
            warnings.append(
                f"{item.tag}: phụ kiện '{key}' không có trong catalogue (giá 0) — kiểm tra tab Catalogue"
            )
            comp = {}
        hardware.append(
            HardwareLine(
                tag=item.tag,
                key=key,
                name=str(comp.get("name", key)),
                unit=str(comp.get("unit", "cái")),
                qty=round(qty, 2),
                price=float(comp.get("price", 0) or 0),
            )
        )

    groove = min(frame_p.glass_groove_mm or 0, sash_p.glass_groove_mm or 0)
    if groove and gt + 6 > groove:
        warnings.append(
            f"{item.tag}: kính {gt}mm + gioăng có thể vượt rãnh kính {groove}mm của hệ {system.code}"
        )
    if not system.verified:
        warnings.append(f"Hệ {system.code} chưa xác nhận catalogue (verified = false), hãy kiểm tra số liệu")
    if not pieces:
        warnings.append(f"{item.tag}: không sinh được thanh nhôm nào")

    return ItemResult(
        item=item,
        system_code=system.code,
        system_name=system.name,
        joint=joint,
        width_mm=W,
        height_mm=H,
        cols=count,
        leaves=leaves,
        cells=cells,
        pieces=pieces,
        glass=glass_pieces,
        hardware=hardware,
        bars3d=bars,
        panes3d=panes,
        hardware3d=hardware3d,
        leaf_rects=leaf_rects,
        leaf_dirs=leaf_dirs,
        cell_rects=cell_rects,
        gasket_m=round(gasket_m, 2),
        warnings=warnings,
    )

