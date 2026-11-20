"""Dựng bản vẽ 2D sản xuất (mặt đứng + chi tiết + bảng cắt + khung tên) thành Sheet."""
from __future__ import annotations

from .models import ITEM_TYPE_LABELS, ItemResult, ProjectInfo, SystemDef
from .sheet import Sheet

MARGIN = 100.0
TITLE_H = 280.0
ROW_H = 70.0
HEAD_H = 80.0
COL_WIDTHS = [520.0, 480.0, 220.0, 110.0, 200.0, 640.0]
HEADERS = ["MÃ THANH", "TÊN THANH", "DÀI (mm)", "SL", "GÓC CẮT", "GHI CHÚ"]


def _table(
    sheet: Sheet,
    x: float,
    y_top: float,
    headers: list[str],
    rows: list[list[str]],
    widths: list[float],
    row_h: float = ROW_H,
    head_h: float = HEAD_H,
    layer: str = "table",
) -> float:
    total_w = sum(widths)
    y = y_top
    sheet.rect(x, y - head_h, total_w, head_h, layer)
    cursor = x
    for header, width in zip(headers, widths):
        sheet.text(cursor + 20, y - head_h + 18, header, height=34, layer=layer)
        cursor += width
        sheet.line(cursor, y - head_h, cursor, y, layer)
    sheet.line(x, y - head_h, x + total_w, y - head_h, layer)
    y -= head_h
    for row in rows:
        sheet.rect(x, y - row_h, total_w, row_h, layer)
        cursor = x
        for value, width in zip(row, widths):
            sheet.text(cursor + 20, y - row_h + 18, value, height=32, layer=layer)
            cursor += width
            sheet.line(cursor, y - row_h, cursor, y, layer)
        y -= row_h
    sheet.line(x, y, x + total_w, y, layer)
    return y


def build_sheet(
    result: ItemResult,
    project: ProjectInfo,
    pricing: dict | None = None,
    system: SystemDef | None = None,
) -> Sheet:
    item = result.item
    pricing = pricing or {}
    width = max(result.width_mm, 900)
    table_w = sum(COL_WIDTHS)
    rows = [
        [
            piece.profile_code,
            piece.profile_name,
            f"{piece.length_mm:,.0f}".replace(",", "."),
            str(piece.qty),
            f"{piece.cut_a}/{piece.cut_b}",
            piece.note,
        ]
        for piece in result.pieces
    ]
    rows.append(
        [
            "TỔNG",
            f"{len(result.pieces)} mã thanh",
            f"{result.alum_length_m * 1000:,.0f}".replace(",", "."),
            "",
            "",
            f"{result.alum_kg:.2f} kg",
        ]
    )
    table_h = HEAD_H + len(rows) * ROW_H
    content_h = max(result.height_mm + 380, table_h + 1400)
    base_y = MARGIN + TITLE_H + 280
    elev_x = MARGIN + 260
    table_x = elev_x + width + 420
    sheet_w = table_x + table_w + MARGIN
    sheet_h = base_y + content_h + 240
    sheet = Sheet(sheet_w, sheet_h, title=f"{project.code} - {item.tag}")

    _title_block(sheet, project, result, pricing)
    for pane in result.panes3d:
        sheet.poly(
            [
                [elev_x + pane.x, base_y + pane.z],
                [elev_x + pane.x + pane.w, base_y + pane.z],
                [elev_x + pane.x + pane.w, base_y + pane.z + pane.h],
                [elev_x + pane.x, base_y + pane.z + pane.h],
            ],
            layer="glass",
            fill="#bfe3f6",
        )
    for bar in result.bars3d:
        layer = "sash" if bar.group == "sash" else "frame"
        sheet.poly(
            [(elev_x + point[0], base_y + point[1]) for point in bar.polygon],
            layer=layer,
            fill="#e5e7eb",
        )

    for index, rect in enumerate(result.leaf_rects):
        lx, lz, lw, lh = rect
        direction = result.leaf_dirs[index] if index < len(result.leaf_dirs) else "left"
        x0, z0 = elev_x + lx, base_y + lz
        if direction == "right":
            hinge_x, arrow_from, arrow_to = x0 + lw, x0 + lw * 0.72, x0 + lw * 0.28
            sheet.line(hinge_x, z0 + lh * 0.05, hinge_x, z0 + lh * 0.95, "hidden")
            sheet.arrow(arrow_from, z0 + lh * 0.5, arrow_to, z0 + lh * 0.5)
        elif direction == "left":
            hinge_x, arrow_from, arrow_to = x0, x0 + lw * 0.28, x0 + lw * 0.72
            sheet.line(hinge_x, z0 + lh * 0.05, hinge_x, z0 + lh * 0.95, "hidden")
            sheet.arrow(arrow_from, z0 + lh * 0.5, arrow_to, z0 + lh * 0.5)
        elif direction == "up":
            sheet.line(x0 + lw * 0.05, z0 + lh, x0 + lw * 0.95, z0 + lh, "hidden")
            sheet.arrow(x0 + lw * 0.5, z0 + lh * 0.72, x0 + lw * 0.5, z0 + lh * 0.28)
        else:
            sheet.arrow(x0 + lw / 2, z0 + lh * 0.2, x0 + lw / 2, z0 + lh * 0.8)
        sheet.text(x0 + lw / 2, z0 + lh * 0.62, f"{item.tag}-{index + 1}", height=46, align="center")

    for rect in result.cell_rects:
        cx, cz, cw, ch = rect
        sheet.text(
            elev_x + cx + cw / 2,
            base_y + cz + ch / 2,
            "FIX",
            height=42,
            layer="note",
            align="center",
            valign="middle",
        )

    sheet.dim_h(elev_x, elev_x + result.width_mm, base_y, offset=150)
    sheet.dim_v(elev_x, base_y, base_y + result.height_mm, offset=150)
    for rect in result.leaf_rects:
        lx, _lz, lw, _lh = rect
        sheet.dim_h(elev_x + lx, elev_x + lx + lw, base_y + result.height_mm, offset=-150, height=30)
    sheet.text(
        elev_x,
        base_y + result.height_mm + 300,
        f"CỬA {item.tag} - {ITEM_TYPE_LABELS.get(item.type, item.type)}",
        height=70,
    )
    sheet.text(
        elev_x,
        base_y + result.height_mm + 220,
        f"{item.width_mm:.0f} x {item.height_mm:.0f} mm | SL {item.qty} | hệ {result.system_code} | "
        f"kính {item.glass.thickness_mm:g}mm | TL 1:20",
        height=38,
        layer="note",
    )
    if item.sill_mm:
        sheet.text(
            elev_x, base_y - 240, f"Cao độ đặt: {item.sill_mm:.0f} mm", height=34, layer="note"
        )

    table_top = base_y + content_h
    bottom = _table(sheet, table_x, table_top, HEADERS, rows, COL_WIDTHS)
    _section_detail(sheet, table_x, bottom - 140, result, system)
    _notes(sheet, table_x, bottom - 760, result)
    _hardware_table(sheet, table_x, bottom - 1080, result)
    return sheet


def _title_block(sheet: Sheet, project: ProjectInfo, result: ItemResult, pricing: dict) -> None:
    x, y = MARGIN, MARGIN
    width = sheet.width - 2 * MARGIN
    sheet.rect(x, y, width, TITLE_H, "title")
    sheet.line(x + 1900, y, x + 1900, y + TITLE_H, "title")
    sheet.line(x, y + TITLE_H - 90, x + 1900, y + TITLE_H - 90, "title")
    company = (pricing.get("company") or {}).get("name", "XINGFACAD")
    sheet.text(x + 24, y + TITLE_H - 58, str(company), height=46)
    sheet.text(x + 24, y + 150, f"Dự án: {project.code} - {project.name}", height=32)
    sheet.text(
        x + 24, y + 92, f"Khách hàng: {project.customer} | Địa chỉ: {project.address}", height=26, layer="note"
    )
    sheet.text(x + 24, y + 42, f"Ngày: {project.date} | Người vẽ: XingfaCAD", height=26, layer="note")
    sheet.text(x + 1940, y + 150, f"MÃ: {result.item.tag}", height=78, layer="title")
    sheet.text(x + 1940, y + 85, f"{result.system_code} | {result.item.type_label}", height=32)
    sheet.text(
        x + 1940,
        y + 32,
        f"{result.width_mm:.0f} x {result.height_mm:.0f} mm | SL: {result.item.qty}",
        height=28,
        layer="note",
    )
    sheet.text(x + width - 40, y + 30, "BẢN VẼ SẢN XUẤT", height=50, align="right", layer="title")
    sheet.text(
        x + width - 40,
        y + 112,
        f"Nhôm {result.alum_kg:.2f} kg | Kính {result.glass_m2:.2f} m² | TL 1:20",
        height=30,
        align="right",
        layer="note",
    )


def _section_detail(
    sheet: Sheet, x: float, y_top: float, result: ItemResult, system: SystemDef | None, scale: float = 4.0
) -> None:
    sheet.text(x, y_top + 50, f"MẶT CẮT TIẾT DIỆN (TL {scale:.0f}:1)", height=40)
    frame_w, frame_d = 55.0, 65.0
    sash_w, sash_d = 60.0, 60.0
    if system is not None:
        frame = system.profiles["frame"]
        sash = system.profile("sash")
        frame_w, frame_d = frame.width_mm, frame.depth_mm
        sash_w, sash_d = sash.width_mm, sash.depth_mm
    glass_t = result.item.glass.thickness_mm

    box_h = frame_w * scale
    sheet.rect(x, y_top - box_h, frame_d * scale, box_h, "frame", fill="#e5e7eb")
    sash_x = x + max((frame_d - sash_d) / 2, 0) * scale
    sash_z = y_top - (frame_w * scale + sash_w * scale) / 2
    sheet.rect(sash_x, sash_z, sash_d * scale, sash_w * scale, "sash", fill="#f3f4f6")
    glass_x = sash_x + (sash_d * scale - glass_t * scale) / 2
    sheet.rect(glass_x, sash_z + 6 * scale, glass_t * scale, (sash_w - 12) * scale, "glass", fill="#bfe3f6")
    sheet.text(
        x,
        y_top - box_h - 170,
        f"Khung bao {frame_w:.0f}x{frame_d:.0f} | Cánh {sash_w:.0f}x{sash_d:.0f} | Kính {glass_t:g}mm",
        height=30,
        layer="note",
    )
    sheet.dim_h(x, x + frame_d * scale, y_top - box_h, offset=110, value=f"{frame_d:.0f}", height=30)
    sheet.dim_v(x, y_top - box_h, y_top, offset=110, value=f"{frame_w:.0f}", height=30)


def _notes(sheet: Sheet, x: float, y_top: float, result: ItemResult) -> None:
    sheet.text(x, y_top + 40, "GHI CHÚ:", height=38)
    lines = [
        f"1. Hệ nhôm {result.system_code}, ghép góc {result.joint}.",
        f"2. Kính tổng {result.glass_m2:.2f} m², gioăng {result.gasket_m:.2f} m.",
        f"3. Khối lượng nhôm {result.alum_kg:.2f} kg / hạng mục.",
        "4. Kích thước ghi bằng mm, sai số cắt ±1mm.",
    ]
    for index, line in enumerate(lines):
        sheet.text(x, y_top - index * 60, line, height=32)
    offset_x = 1000
    sheet.text(x + offset_x, y_top + 40, "BẢNG KÍNH:", height=38)
    for index, piece in enumerate(result.glass[:8]):
        sheet.text(
            x + offset_x,
            y_top - index * 60,
            f"{piece.note}: {piece.width_mm:.0f} x {piece.height_mm:.0f} x {piece.thickness_mm:g}mm",
            height=30,
            layer="note",
        )


def _hardware_table(sheet: Sheet, x: float, y_top: float, result: ItemResult) -> None:
    rows = [
        [line.key.upper(), line.name, line.unit, f"{line.qty:g}"]
        for line in result.hardware
    ]
    if not rows:
        return
    sheet.text(x, y_top + 40, "BẢNG PHỤ KIỆN:", height=38)
    _table(
        sheet,
        x,
        y_top,
        ["MÃ VT", "TÊN VẬT TƯ", "ĐVT", "SL"],
        rows,
        [260.0, 820.0, 160.0, 120.0],
        row_h=64,
        head_h=70,
    )
