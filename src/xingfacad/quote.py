"""Xuất báo giá + bảng cắt + tối ưu cắt ra Excel (openpyxl)."""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName

from .models import ItemResult, ProjectInfo
from .optimizer import BarGroup
from .pricing import ProjectCost

THIN = Side(style="thin", color="B7C0CC")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEAD_FILL = PatternFill("solid", fgColor="1F3864")
SUB_FILL = PatternFill("solid", fgColor="DCE6F1")
TOTAL_FILL = PatternFill("solid", fgColor="FFF2CC")
HEAD_FONT = Font(bold=True, color="FFFFFF", size=10)
BOLD = Font(bold=True)
MONEY = "#,##0"
REAL = "#,##0.00"


def _style_header(ws, row: int, headers: list[str], widths: list[float]) -> None:
    for index, (header, width) in enumerate(zip(headers, widths), start=1):
        cell = ws.cell(row=row, column=index, value=header)
        cell.fill = HEAD_FILL
        cell.font = HEAD_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER
        ws.column_dimensions[get_column_letter(index)].width = width
    ws.row_dimensions[row].height = 42


def _box(ws, r1: int, r2: int, c1: int, c2: int) -> None:
    for row in ws.iter_rows(min_row=r1, max_row=r2, min_col=c1, max_col=c2):
        for cell in row:
            cell.border = BORDER


def _title(ws, text: str, last_col: str, size: int = 15) -> None:
    ws["A1"] = text
    ws["A1"].font = Font(bold=True, size=size, color="1F3864")
    ws.merge_cells(f"A1:{last_col}1")
    ws["A1"].alignment = Alignment(horizontal="center")


def build_quote(
    project: ProjectInfo,
    results: list[ItemResult],
    cost: ProjectCost,
    pricing: dict,
    catalog: dict,
    cut_plan: list[BarGroup],
    out_path: str | Path,
) -> Path:
    out_path = Path(out_path)
    wb = Workbook()
    profile_kg: dict[str, float] = {}
    for result in results:
        for piece in result.pieces:
            profile_kg.setdefault(piece.profile_code, piece.kg_per_m)
    total_row = _sheet_quote(wb, project, results, cost, pricing)
    _sheet_cutlist(wb, results)
    _sheet_optimizer(wb, cut_plan, pricing, profile_kg)
    _sheet_materials(wb, results)
    _sheet_summary(wb, cost, pricing, catalog, results, total_row)
    _sheet_config(wb, pricing, catalog)
    wb.active = 0
    wb.save(out_path)
    return out_path


def _sheet_quote(
    wb: Workbook, project: ProjectInfo, results: list[ItemResult], cost: ProjectCost, pricing: dict
) -> int:
    ws = wb.active
    ws.title = "01_BaoGia"
    company = pricing.get("company", {}) or {}
    ws["A1"] = str(company.get("name", "XINGFACAD"))
    ws["A1"].font = Font(bold=True, size=14, color="1F3864")
    ws.merge_cells("A1:F1")
    ws["A2"] = (
        f"Địa chỉ: {company.get('address', '')} - ĐT: {company.get('phone', '')} "
        f"- MST: {company.get('tax_code', '')}"
    )
    ws.merge_cells("A2:L2")
    ws["A4"] = "BẢNG BÁO GIÁ CỬA NHÔM XINGFA"
    ws["A4"].font = Font(bold=True, size=18, color="1F3864")
    ws.merge_cells("A4:V4")
    ws["A4"].alignment = Alignment(horizontal="center")

    info_rows = [
        ("Dự án", f"{project.code} - {project.name}"),
        ("Đơn vị yêu cầu", project.request_org or project.customer),
        ("Khách hàng", project.customer),
        ("Địa chỉ", project.address),
        ("Người báo giá", project.quoted_by),
        ("ĐT người báo giá", project.quoted_by_phone),
        ("Ngày báo giá", project.date),
        ("Đơn vị tính", cost.currency),
    ]
    for index, (label, value) in enumerate(info_rows):
        row = 6 + index
        ws.cell(row=row, column=1, value=label).font = BOLD
        ws.cell(row=row, column=2, value=value)
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=8)

    headers = [
        "STT", "Mã", "Vị trí", "Loại cửa", "Hệ", "Rộng\n(mm)", "Cao\n(mm)", "SL", "DT\n(m²)",
        "Nhôm\n(kg)", "Tiền nhôm", "Kính\n(m²)", "ĐG kính", "Tiền kính", "Phụ kiện", "Nhân công",
        "Vật tư phụ", "Vận chuyển", "Giá vốn", "Lãi", "Giá bán", "Đơn giá/m²",
    ]
    widths = [5, 8, 18, 16, 8, 8, 8, 6, 9, 9, 13, 9, 11, 13, 12, 12, 12, 12, 13, 12, 14, 13]
    header_row = 6 + len(info_rows) + 1
    _style_header(ws, header_row, headers, widths)

    row = header_row + 1
    first_data_row = row
    for index, (result, item_cost) in enumerate(zip(results, cost.items), start=1):
        values = [
            index,
            result.item.tag,
            result.item.room,
            result.item.type_label,
            result.system_code,
            result.item.width_mm,
            result.item.height_mm,
            result.item.qty,
            f"=ROUND(F{row}*G{row}/1000000*H{row},3)",
            item_cost.alum_kg,
            f"=ROUND(J{row}*GIA_NHOM*(1+HAO_HUT_PCT/100),0)",
            item_cost.glass_m2,
            round(result.item.glass.price_per_m2 or 0, 0),
            f"=ROUND(L{row}*M{row},0)",
            item_cost.hardware_cost,
            f"=ROUND((K{row}+N{row}+O{row})*NHAN_CONG_PCT/100,0)",
            f"=ROUND(I{row}*VATTU_M2,0)",
            f"=ROUND(H{row}*VAN_CHUYEN,0)",
            f"=K{row}+N{row}+O{row}+P{row}+Q{row}+R{row}",
            f"=ROUND(S{row}*LOI_NHUAN_PCT/100,0)",
            f"=ROUND(S{row}+T{row},-3)",
            f"=IF(I{row}=0,0,ROUND(U{row}/I{row},0))",
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col, value=value)
            if col >= 9:
                cell.number_format = REAL if col == 9 else MONEY
            if col in (1, 2, 5, 8):
                cell.alignment = Alignment(horizontal="center")
        row += 1
    last_data_row = row - 1

    total_row = row
    ws.cell(row=total_row, column=1, value="TỔNG")
    ws.merge_cells(start_row=total_row, start_column=1, end_row=total_row, end_column=8)
    for col in (9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21):
        letter = get_column_letter(col)
        ws.cell(row=total_row, column=col, value=f"=SUM({letter}{first_data_row}:{letter}{last_data_row})")
    ws.cell(row=total_row, column=22, value=f"=IF(I{total_row}=0,0,ROUND(U{total_row}/I{total_row},0))")
    for col in range(1, 23):
        cell = ws.cell(row=total_row, column=col)
        cell.font = BOLD
        cell.fill = TOTAL_FILL
        if col >= 9:
            cell.number_format = MONEY
    _box(ws, header_row, total_row, 1, 22)

    note_row = total_row + 2
    ws.cell(
        row=note_row,
        column=1,
        value=(
            f"Ghi chú: đơn giá nhôm {pricing.get('aluminum_price_per_kg', 0):,.0f} đ/kg (hao hụt "
            f"{pricing.get('waste_percent', 0)}%), nhân công {pricing.get('labor_percent_of_material', 0)}% "
            f"vật tư, lãi {pricing.get('profit_percent', 0)}%. VAT {pricing.get('vat_percent', 0)}% "
            f"tính tại sheet 05_TongHop."
        ),
    )
    ws.merge_cells(start_row=note_row, start_column=1, end_row=note_row, end_column=22)
    ws.freeze_panes = f"C{header_row + 1}"
    ws.sheet_view.zoomScale = 85
    return total_row


def _sheet_cutlist(wb: Workbook, results: list[ItemResult]) -> None:
    ws = wb.create_sheet("02_BangCat")
    _title(ws, "BẢNG CẮT NHÔM THEO TỪNG HẠNG MỤC", "I", size=15)
    headers = ["Mã thanh", "Tên profile", "Dài (mm)", "SL", "Tổng dài (mm)", "kg/m", "Kg", "Góc cắt", "Ghi chú"]
    widths = [16, 24, 12, 7, 15, 9, 10, 12, 34]
    row = 3
    summary: dict[str, dict[str, float]] = {}
    for result in results:
        ws.cell(
            row=row,
            column=1,
            value=(
                f"{result.item.tag} - {result.item.type_label} - "
                f"{result.item.width_mm:.0f}x{result.item.height_mm:.0f} "
                f"(SL {result.item.qty}) - {result.system_code}"
            ),
        )
        ws.cell(row=row, column=1).font = BOLD
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=9)
        ws.cell(row=row, column=1).fill = SUB_FILL
        row += 1
        _style_header(ws, row, headers, widths)
        row += 1
        first = row
        for piece in result.pieces:
            total_mm = piece.total_length_mm * result.item.qty
            kg = total_mm / 1000 * piece.kg_per_m
            values = [
                piece.profile_code,
                piece.profile_name,
                piece.length_mm,
                piece.qty * result.item.qty,
                total_mm,
                piece.kg_per_m,
                round(kg, 3),
                f"{piece.cut_a}/{piece.cut_b}",
                piece.note,
            ]
            for col, value in enumerate(values, start=1):
                cell = ws.cell(row=row, column=col, value=value)
                if col in (3, 5):
                    cell.number_format = "#,##0"
                if col in (6, 7):
                    cell.number_format = REAL
            bucket = summary.setdefault(
                piece.profile_code,
                {
                    "name": piece.profile_name,
                    "length": 0.0,
                    "kg": 0.0,
                    "qty": 0.0,
                    "kg_per_m": piece.kg_per_m,
                },
            )
            bucket["length"] += total_mm
            bucket["kg"] += kg
            bucket["qty"] += piece.qty * result.item.qty
            row += 1
        last = row - 1
        ws.cell(row=row, column=1, value="Cộng")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        ws.cell(row=row, column=5, value=f"=SUM(E{first}:E{last})").number_format = "#,##0"
        ws.cell(row=row, column=7, value=f"=SUM(G{first}:G{last})").number_format = REAL
        for col in range(1, 10):
            ws.cell(row=row, column=col).font = BOLD
            ws.cell(row=row, column=col).fill = TOTAL_FILL
        _box(ws, first - 1, row, 1, 9)
        row += 2

    ws.cell(row=row, column=1, value="TỔNG HỢP TOÀN DỰ ÁN THEO MÃ THANH")
    ws.cell(row=row, column=1).font = Font(bold=True, size=13, color="1F3864")
    row += 1
    sum_headers = ["Mã thanh", "Tên profile", "Tổng SL", "Tổng dài (m)", "kg/m", "Tổng kg", "Tiền nhôm (đ)"]
    sum_widths = [16, 26, 10, 14, 9, 12, 16]
    _style_header(ws, row, sum_headers, sum_widths)
    row += 1
    first = row
    for code, data in sorted(summary.items()):
        values = [
            code,
            data["name"],
            data["qty"],
            round(data["length"] / 1000, 2),
            data["kg_per_m"],
            round(data["kg"], 2),
            f"=ROUND(F{row}*GIA_NHOM*(1+HAO_HUT_PCT/100),0)",
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col, value=value)
            if col == 7:
                cell.number_format = MONEY
            if col in (5, 6):
                cell.number_format = REAL
        row += 1
    ws.cell(row=row, column=1, value="TỔNG")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
    ws.cell(row=row, column=3, value=f"=SUM(C{first}:C{row - 1})")
    ws.cell(row=row, column=4, value=f"=SUM(D{first}:D{row - 1})").number_format = REAL
    ws.cell(row=row, column=6, value=f"=SUM(F{first}:F{row - 1})").number_format = REAL
    ws.cell(row=row, column=7, value=f"=SUM(G{first}:G{row - 1})").number_format = MONEY
    for col in range(1, 8):
        cell = ws.cell(row=row, column=col)
        cell.font = BOLD
        cell.fill = TOTAL_FILL
    _box(ws, first - 1, row, 1, 7)
    ws.freeze_panes = "A3"


def _sheet_optimizer(
    wb: Workbook, cut_plan: list[BarGroup], pricing: dict, profile_kg: dict[str, float]
) -> None:
    ws = wb.create_sheet("03_ToiUuCat")
    _title(ws, "TỐI ƯU CẮT CÂY NHÔM (giảm phế liệu)", "E", size=15)
    headers = ["Cây số", "Chiều dài dùng (mm)", "Phế (mm)", "Tỷ lệ dùng (%)", "Sơ đồ cắt"]
    widths = [10, 20, 12, 14, 90]
    row = 3
    price_per_kg = float(pricing.get("aluminum_price_per_kg", 0) or 0)
    total_bars = 0
    total_waste = 0.0
    total_stock = 0.0
    waste_value = 0.0
    for group in cut_plan:
        ws.cell(
            row=row,
            column=1,
            value=(
                f"{group.profile_code} - {group.profile_name} | cây {group.stock_mm:.0f}mm | "
                f"{len(group.bars)} cây | phế {group.total_waste_mm / 1000:.2f}m ({group.waste_percent:.1f}%)"
            ),
        )
        ws.cell(row=row, column=1).font = BOLD
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
        ws.cell(row=row, column=1).fill = SUB_FILL
        row += 1
        _style_header(ws, row, headers, widths)
        row += 1
        for bar in group.bars:
            values = [
                bar.index,
                round(bar.used_mm, 1),
                round(bar.waste_mm, 1),
                round(bar.fill_percent, 1),
                bar.pattern(),
            ]
            for col, value in enumerate(values, start=1):
                cell = ws.cell(row=row, column=col, value=value)
                if col in (2, 3):
                    cell.number_format = "#,##0"
                if col == 4:
                    cell.number_format = "0.0"
            row += 1
        total_bars += len(group.bars)
        total_waste += group.total_waste_mm
        total_stock += group.stock_total_mm
        waste_value += group.total_waste_mm / 1000 * profile_kg.get(group.profile_code, 0) * price_per_kg
        row += 1

    ws.cell(
        row=row,
        column=1,
        value=(
            f"TỔNG: {total_bars} cây | phế {total_waste / 1000:.2f} m | "
            f"{100 * total_waste / total_stock if total_stock else 0:.1f}% | "
            f"giá trị phế ~{waste_value:,.0f} đ"
        ),
    )
    ws.cell(row=row, column=1).font = BOLD
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
    ws.cell(row=row, column=1).fill = TOTAL_FILL
    ws.cell(
        row=row + 2,
        column=1,
        value=(
            "Sơ đồ cắt tính cả mạch cắt (kerf) và đầu kẹp, ưu tiên thanh dài trước. "
            "Đầu thừa (phế) có thể dùng lại cho hạng mục khác nên giá trị phế chỉ là tham khảo."
        ),
    )
    ws.freeze_panes = "A3"


def _sheet_materials(wb: Workbook, results: list[ItemResult]) -> None:
    ws = wb.create_sheet("04_Kinh_PhuKien")
    _title(ws, "BẢNG KÍNH VÀ PHỤ KIỆN", "I", size=15)

    glass_headers = ["Mã cửa", "Vị trí", "Loại kính", "Dày (mm)", "Rộng (mm)", "Cao (mm)", "SL", "DT (m²)", "Tiền (đ)"]
    glass_widths = [10, 20, 24, 10, 12, 12, 7, 10, 14]
    row = 3
    ws.cell(row=row, column=1, value="1. KÍNH").font = Font(bold=True, size=12, color="1F3864")
    row += 1
    _style_header(ws, row, glass_headers, glass_widths)
    row += 1
    glass_first = row
    glass_total_area = 0.0
    glass_total_amount = 0.0
    for result in results:
        for piece in result.glass:
            qty = piece.qty * result.item.qty
            area = piece.area_m2 * result.item.qty
            amount = area * piece.price_per_m2
            values = [
                result.item.tag,
                piece.note,
                piece.name,
                piece.thickness_mm,
                piece.width_mm,
                piece.height_mm,
                qty,
                round(area, 3),
                round(amount, 0),
            ]
            for col, value in enumerate(values, start=1):
                cell = ws.cell(row=row, column=col, value=value)
                if col == 8:
                    cell.number_format = REAL
                if col == 9:
                    cell.number_format = MONEY
            glass_total_area += area
            glass_total_amount += amount
            row += 1
    ws.cell(row=row, column=1, value="TỔNG KÍNH")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=7)
    ws.cell(row=row, column=8, value=f"=SUM(H{glass_first}:H{row - 1})").number_format = REAL
    ws.cell(row=row, column=9, value=f"=SUM(I{glass_first}:I{row - 1})").number_format = MONEY
    for col in range(1, 10):
        cell = ws.cell(row=row, column=col)
        cell.font = BOLD
        cell.fill = TOTAL_FILL
    _box(ws, glass_first - 1, row, 1, 9)
    row += 3

    hw_headers = ["Mã cửa", "Mã VT", "Tên vật tư", "ĐVT", "SL", "ĐG (đ)", "Tiền (đ)"]
    hw_widths = [10, 14, 26, 8, 10, 12, 14]
    ws.cell(row=row, column=1, value="2. PHỤ KIỆN / VẬT TƯ").font = Font(bold=True, size=12, color="1F3864")
    row += 1
    _style_header(ws, row, hw_headers, hw_widths)
    row += 1
    hw_first = row
    for result in results:
        for line in result.hardware:
            qty = round(line.qty * result.item.qty, 2)
            amount = qty * line.price
            values = [
                result.item.tag,
                line.key.upper(),
                line.name,
                line.unit,
                qty,
                line.price,
                round(amount, 0),
            ]
            for col, value in enumerate(values, start=1):
                cell = ws.cell(row=row, column=col, value=value)
                if col in (6, 7):
                    cell.number_format = MONEY
            row += 1
    ws.cell(row=row, column=1, value="TỔNG PHỤ KIỆN")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    ws.cell(row=row, column=7, value=f"=SUM(G{hw_first}:G{row - 1})").number_format = MONEY
    for col in range(1, 8):
        cell = ws.cell(row=row, column=col)
        cell.font = BOLD
        cell.fill = TOTAL_FILL
    _box(ws, hw_first - 1, row, 1, 7)
    ws.cell(
        row=row + 2,
        column=1,
        value=(
            f"Tổng kính {glass_total_area:.2f} m² - {glass_total_amount:,.0f} đ. "
            "Cột SL đã nhân với số lượng cửa."
        ),
    )
    ws.freeze_panes = "A4"


def _sheet_summary(
    wb: Workbook,
    cost: ProjectCost,
    pricing: dict,
    catalog: dict,
    results: list[ItemResult],
    total_row: int,
) -> None:
    ws = wb.create_sheet("05_TongHop")
    _title(ws, "TỔNG HỢP GIÁ TRỊ DỰ ÁN", "E", size=16)
    src = "'01_BaoGia'"
    first_data = total_row - len(cost.items)
    last_data = total_row - 1

    entries = [
        ("Tổng diện tích cửa (m²)", f"={src}!I{total_row}", REAL, False),
        ("Tổng khối lượng nhôm (kg)", f"={src}!J{total_row}", REAL, False),
        ("Tổng diện tích kính (m²)", f"={src}!L{total_row}", REAL, False),
        ("Chi phí nhôm", f"={src}!K{total_row}", MONEY, False),
        ("Chi phí kính", f"={src}!N{total_row}", MONEY, False),
        ("Chi phí phụ kiện", f"={src}!O{total_row}", MONEY, False),
        ("Nhân công", f"={src}!P{total_row}", MONEY, False),
        ("Vật tư phụ", f"={src}!Q{total_row}", MONEY, False),
        ("Vận chuyển", f"={src}!R{total_row}", MONEY, False),
        ("GIÁ VỐN", f"={src}!S{total_row}", MONEY, True),
        ("Lợi nhuận", f"={src}!T{total_row}", MONEY, False),
        ("DOANH THU (chưa VAT)", f"={src}!U{total_row}", MONEY, True),
    ]
    row = 3
    cells: dict[str, str] = {}
    for label, formula, number_format, bold in entries:
        ws.cell(row=row, column=1, value=label).font = BOLD if bold else Font()
        cell = ws.cell(row=row, column=2, value=formula)
        cell.number_format = number_format
        if bold:
            cell.fill = SUB_FILL
        cells[label] = f"B{row}"
        row += 1

    revenue = cells["DOANH THU (chưa VAT)"]
    cost_total = cells["GIÁ VỐN"]
    profit = cells["Lợi nhuận"]
    area = cells["Tổng diện tích cửa (m²)"]

    ws.cell(row=row, column=1, value="Chiết khấu (%)").font = BOLD
    ws.cell(row=row, column=2, value=0).number_format = "0.0"
    discount_pct = f"B{row}"
    row += 1
    ws.cell(row=row, column=1, value="Tiền chiết khấu")
    ws.cell(row=row, column=2, value=f"=ROUND({revenue}*{discount_pct}/100,0)").number_format = MONEY
    discount_amount = f"B{row}"
    row += 1
    ws.cell(row=row, column=1, value="VAT (%)").font = BOLD
    ws.cell(row=row, column=2, value="=VAT_PCT").number_format = "0.0"
    vat_pct = f"B{row}"
    row += 1
    ws.cell(row=row, column=1, value="Tiền VAT")
    ws.cell(row=row, column=2, value=f"=ROUND(({revenue}-{discount_amount})*{vat_pct}/100,0)").number_format = MONEY
    vat_amount = f"B{row}"
    row += 1
    ws.cell(row=row, column=1, value="TỔNG THANH TOÁN").font = Font(bold=True, size=12, color="1F3864")
    total_cell = ws.cell(row=row, column=2, value=f"={revenue}-{discount_amount}+{vat_amount}")
    total_cell.number_format = MONEY
    total_cell.font = Font(bold=True, size=12)
    total_cell.fill = TOTAL_FILL
    grand_total = f"B{row}"
    row += 1
    ws.cell(row=row, column=1, value="Đơn giá bình quân (đ/m²)")
    ws.cell(row=row, column=2, value=f"=IF({area}=0,0,ROUND({grand_total}/{area},0))").number_format = MONEY
    row += 1
    ws.cell(row=row, column=1, value="Tỷ suất lãi gộp (%)")
    ws.cell(row=row, column=2, value=f"=IF({revenue}=0,0,ROUND({profit}/{revenue}*100,1))").number_format = "0.0"
    last_summary_row = row

    for r in range(3, last_summary_row + 1):
        ws.cell(row=r, column=1).border = BORDER
        ws.cell(row=r, column=2).border = BORDER
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 18

    # thống kê theo loại cửa / hệ nhôm
    start = 3
    ws.cell(row=start, column=4, value="Theo loại cửa").font = Font(bold=True, color="1F3864")
    ws.cell(row=start, column=5, value="Doanh thu (đ)").font = Font(bold=True, color="1F3864")
    ws.cell(row=start, column=6, value="DT (m²)").font = Font(bold=True, color="1F3864")
    row = start + 1
    for label in sorted({result.item.type_label for result in results}):
        ws.cell(row=row, column=4, value=label)
        ws.cell(
            row=row,
            column=5,
            value=f"=SUMIF({src}!$D${first_data}:$D${last_data},D{row},{src}!$U${first_data}:$U${last_data})",
        ).number_format = MONEY
        ws.cell(
            row=row,
            column=6,
            value=f"=SUMIF({src}!$D${first_data}:$D${last_data},D{row},{src}!$I${first_data}:$I${last_data})",
        ).number_format = REAL
        row += 1
    row += 1
    ws.cell(row=row, column=4, value="Theo hệ nhôm").font = Font(bold=True, color="1F3864")
    ws.cell(row=row, column=5, value="Doanh thu (đ)").font = Font(bold=True, color="1F3864")
    ws.cell(row=row, column=6, value="Nhôm (kg)").font = Font(bold=True, color="1F3864")
    row += 1
    for label in sorted({result.system_code for result in results}):
        ws.cell(row=row, column=4, value=label)
        ws.cell(
            row=row,
            column=5,
            value=f"=SUMIF({src}!$E${first_data}:$E${last_data},D{row},{src}!$U${first_data}:$U${last_data})",
        ).number_format = MONEY
        ws.cell(
            row=row,
            column=6,
            value=f"=SUMIF({src}!$E${first_data}:$E${last_data},D{row},{src}!$J${first_data}:$J${last_data})",
        ).number_format = REAL
        row += 1
    for column, width in (("D", 22), ("E", 16), ("F", 12)):
        ws.column_dimensions[column].width = width
    ws.freeze_panes = "A3"


def _define(wb: Workbook, name: str, sheet_title: str, cell: str) -> None:
    ref = f"'{sheet_title}'!${cell[0]}${cell[1:]}"
    try:
        wb.defined_names[name] = DefinedName(name, attr_text=ref)
    except Exception:
        wb.defined_names.add(DefinedName(name, attr_text=ref))


def _sheet_config(wb: Workbook, pricing: dict, catalog: dict) -> None:
    ws = wb.create_sheet("06_CauHinh")
    _title(ws, "CẤU HÌNH GIÁ - SỬA TRỰC TIẾP TẠI ĐÂY", "E", size=15)
    headers = ["Biến", "Nội dung", "Giá trị", "Ghi chú"]
    widths = [18, 34, 16, 56]
    row = 3
    _style_header(ws, row, headers, widths)
    entries = [
        ("GIA_NHOM", "Đơn giá nhôm (đ/kg)", pricing.get("aluminum_price_per_kg", 0), MONEY, "Giá nhôm thanh theo kg"),
        ("HAO_HUT_PCT", "Hao hụt nhôm (%)", pricing.get("waste_percent", 0), "0.0", "Bù phế cắt + đầu cây"),
        ("NHAN_CONG_PCT", "Nhân công (% vật tư)", pricing.get("labor_percent_of_material", 0), "0.0", "Tính trên nhôm + kính + phụ kiện"),
        ("LOI_NHUAN_PCT", "Lợi nhuận (% giá vốn)", pricing.get("profit_percent", 0), "0.0", "Biên lợi nhuận mong muốn"),
        ("VAT_PCT", "VAT (%)", pricing.get("vat_percent", 0), "0.0", "Thuế GTGT"),
        ("VATTU_M2", "Vật tư phụ (đ/m²)", pricing.get("consumables_per_m2", 0), MONEY, "Keo, gioăng, vít"),
        ("VAN_CHUYEN", "Vận chuyển (đ/cửa)", pricing.get("transport_per_item", 0), MONEY, "Chi phí giao lắp mỗi hạng mục"),
    ]
    row = 4
    for name, label, value, number_format, note in entries:
        ws.cell(row=row, column=1, value=name).font = BOLD
        ws.cell(row=row, column=2, value=label)
        cell = ws.cell(row=row, column=3, value=value)
        cell.number_format = number_format
        cell.fill = SUB_FILL
        ws.cell(row=row, column=4, value=note)
        _define(wb, name, "06_CauHinh", f"C{row}")
        row += 1
    _box(ws, 4, row - 1, 1, 4)

    row += 1
    ws.cell(row=row, column=1, value="BẢNG GIÁ KÍNH (catalogue)").font = Font(bold=True, size=12, color="1F3864")
    row += 1
    _style_header(ws, row, ["Mã kính", "Tên", "Dày (mm)", "Đơn giá (đ/m²)"], [18, 34, 14, 18])
    row += 1
    for key, glass in (catalog.get("glass") or {}).items():
        ws.cell(row=row, column=1, value=key)
        ws.cell(row=row, column=2, value=glass.get("name", ""))
        ws.cell(row=row, column=3, value=glass.get("thickness_mm", 0))
        ws.cell(row=row, column=4, value=glass.get("price_per_m2", 0)).number_format = MONEY
        _box(ws, row, row, 1, 4)
        row += 1

    row += 1
    ws.cell(row=row, column=1, value="PHỤ KIỆN (catalogue)").font = Font(bold=True, size=12, color="1F3864")
    row += 1
    _style_header(ws, row, ["Mã VT", "Tên", "ĐVT", "Đơn giá (đ)"], [18, 34, 14, 18])
    row += 1
    hardware = catalog.get("hardware") or {}
    for key, comp in (hardware.get("components") or {}).items():
        ws.cell(row=row, column=1, value=key.upper())
        ws.cell(row=row, column=2, value=comp.get("name", ""))
        ws.cell(row=row, column=3, value=comp.get("unit", ""))
        ws.cell(row=row, column=4, value=comp.get("price", 0)).number_format = MONEY
        _box(ws, row, row, 1, 4)
        row += 1

    row += 2
    ws.cell(row=row, column=1, value=f"Ngày hiệu lực bảng giá: {pricing.get('effective_date', '')}")
    ws.cell(row=row + 1, column=1, value=str(pricing.get("note", "")))
