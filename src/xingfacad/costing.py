"""Bảng tính giá thành (Excel): file đầu vào + giá thành chi tiết + template trống + đọc lại giá."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.workbook.defined_name import DefinedName

from .models import ItemResult, ProjectInfo
from .pricing import ProjectCost

NAVY = "1F3864"
TEAL = "0F766E"
LIGHT = "EEF2F8"
INPUT_FILL = "FFF2CC"
TOTAL_FILL = "FCE4D6"
THIN = Side(style="thin", color="B7C0CC")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEAD_FONT = Font(bold=True, color="FFFFFF", size=10)
MONEY = "#,##0"
REAL = "#,##0.00"
PERCENT = "0.0%"

INPUT_FIELDS: list[tuple[str, str, str, str, float]] = [
    ("GIA_NHOM", "Đơn giá nhôm (đ/kg)", "đ/kg", "Giá thanh nhôm theo kg của NCC", 95000),
    ("HAO_HUT_PCT", "Hao hụt nhôm (%)", "%", "Bù phế cắt + đầu cây", 3),
    ("NHAN_CONG_PCT", "Nhân công (% vật tư)", "%", "Tính trên nhôm + kính + phụ kiện", 10),
    ("LOI_NHUAN_PCT", "Lợi nhuận (% giá vốn)", "%", "Biên lợi nhuận mong muốn", 18),
    ("VAT_PCT", "VAT (%)", "%", "Thuế GTGT", 8),
    ("VATTU_M2", "Vật tư phụ (đ/m²)", "đ/m²", "Keo, gioăng, vít, bảo hộ", 30000),
    ("VAN_CHUYEN", "Vận chuyển (đ/bộ)", "đ", "Chi phí giao lắp mỗi hạng mục", 200000),
]

PRICING_KEYS = {
    "GIA_NHOM": "aluminum_price_per_kg",
    "HAO_HUT_PCT": "waste_percent",
    "NHAN_CONG_PCT": "labor_percent_of_material",
    "LOI_NHUAN_PCT": "profit_percent",
    "VAT_PCT": "vat_percent",
    "VATTU_M2": "consumables_per_m2",
    "VAN_CHUYEN": "transport_per_item",
}


def _header(ws, row: int, values: list[str], widths: list[float]) -> None:
    for index, (value, width) in enumerate(zip(values, widths), start=1):
        cell = ws.cell(row=row, column=index, value=value)
        cell.font = HEAD_FONT
        cell.fill = PatternFill("solid", fgColor=NAVY)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER
        ws.column_dimensions[cell.column_letter].width = width
    ws.row_dimensions[row].height = 30


def _title(ws, text: str, last_col: str = "H", size: int = 14) -> None:
    ws["A1"] = text
    ws["A1"].font = Font(bold=True, size=size, color=NAVY)
    ws.merge_cells(f"A1:{last_col}1")
    ws["A1"].alignment = Alignment(horizontal="center")


def _input_sheet(wb: Workbook, pricing: dict, catalog: dict) -> None:
    ws = wb.active
    ws.title = "01_DauVao"
    _title(ws, "BẢNG GIÁ ĐẦU VÀO — SỬA CÁC Ô MÀU VÀNG RỒI LƯU", "E")
    ws["A2"] = (
        "Điền giá của nhà cung cấp vào cột 'Giá trị'. Sau đó có thể tải file này lên lại "
        "XingfaCAD (tab Catalogue → Nhập giá từ Excel) để cập nhật bảng giá."
    )
    ws["A2"].font = Font(italic=True, size=9, color="5B6570")
    ws.merge_cells("A2:E2")

    _header(ws, 4, ["Mã", "Nội dung", "Giá trị", "Đơn vị", "Ghi chú"], [16, 34, 16, 10, 46])
    row = 5
    for code, label, unit, note, default in INPUT_FIELDS:
        ws.cell(row=row, column=1, value=code).font = Font(bold=True)
        ws.cell(row=row, column=2, value=label)
        value = pricing.get(PRICING_KEYS[code], default)
        cell = ws.cell(row=row, column=3, value=value)
        cell.fill = PatternFill("solid", fgColor=INPUT_FILL)
        cell.font = Font(bold=True)
        cell.number_format = MONEY
        ws.cell(row=row, column=4, value=unit)
        ws.cell(row=row, column=5, value=note)
        for column in range(1, 6):
            ws.cell(row=row, column=column).border = BORDER
        try:
            wb.defined_names[code] = DefinedName(code, attr_text=f"'01_DauVao'!$C${row}")
        except Exception:
            wb.defined_names.add(DefinedName(code, attr_text=f"'01_DauVao'!$C${row}"))
        row += 1

    row += 1
    ws.cell(row=row, column=1, value="BẢNG GIÁ KÍNH (đơn giá theo m²)").font = Font(bold=True, size=12, color=NAVY)
    row += 1
    _header(ws, row, ["Mã kính", "Tên", "Dày (mm)", "Đơn giá (đ/m²)", ""], [16, 34, 16, 16, 46])
    row += 1
    for key, glass in (catalog.get("glass") or {}).items():
        ws.cell(row=row, column=1, value=key)
        ws.cell(row=row, column=2, value=glass.get("name", ""))
        ws.cell(row=row, column=3, value=glass.get("thickness_mm", 0))
        cell = ws.cell(row=row, column=4, value=glass.get("price_per_m2", 0))
        cell.number_format = MONEY
        for column in range(1, 5):
            ws.cell(row=row, column=column).border = BORDER
        row += 1

    row += 1
    ws.cell(row=row, column=1, value="BẢNG GIÁ PHỤ KIỆN (đơn giá theo cái/bộ)").font = Font(
        bold=True, size=12, color=NAVY
    )
    row += 1
    _header(ws, row, ["Mã VT", "Tên", "ĐVT", "Đơn giá", ""], [16, 34, 16, 16, 46])
    row += 1
    hardware = catalog.get("hardware") or {}
    for key, comp in (hardware.get("components") or {}).items():
        ws.cell(row=row, column=1, value=key.upper())
        ws.cell(row=row, column=2, value=comp.get("name", ""))
        ws.cell(row=row, column=3, value=comp.get("unit", ""))
        cell = ws.cell(row=row, column=4, value=comp.get("price", 0))
        cell.number_format = MONEY
        for column in range(1, 5):
            ws.cell(row=row, column=column).border = BORDER
        row += 1

def _cost_sheet(wb: Workbook, results: list[ItemResult], cost: ProjectCost | None, template_rows: int = 0) -> None:
    ws = wb.create_sheet("02_GiaThanh")
    _title(ws, "BẢNG TÍNH GIÁ THÀNH & GIÁ BÁN", "U", size=14)
    ws["A2"] = (
        "Ô vàng = nhập tay (Rộng, Cao, SL, Nhôm kg, Kính m², ĐG kính, Phụ kiện). "
        "Các cột còn lại tự tính theo bảng giá ở sheet 01_DauVao."
    )
    ws["A2"].font = Font(italic=True, size=9, color="5B6570")
    ws.merge_cells("A2:U2")

    headers = [
        "STT", "Mã", "Loại cửa", "Rộng (mm)", "Cao (mm)", "SL", "DT (m²)", "Nhôm (kg)",
        "ĐG nhôm", "Tiền nhôm", "Kính (m²)", "ĐG kính", "Tiền kính", "Phụ kiện", "Nhân công",
        "Vật tư", "Vận chuyển", "Giá vốn", "Lãi", "Giá bán", "ĐG/m²",
    ]
    widths = [5, 8, 18, 9, 9, 6, 9, 9, 11, 12, 9, 11, 12, 12, 12, 11, 11, 13, 11, 13, 12]
    _header(ws, 4, headers, widths)

    row = 5
    if results and cost is not None:
        for index, (result, item_cost) in enumerate(zip(results, cost.items), start=1):
            values: list[Any] = [
                index,
                result.item.tag,
                result.item.type_label,
                result.item.width_mm,
                result.item.height_mm,
                result.item.qty,
                f"=ROUND(D{row}*E{row}/1000000*F{row},3)",
                item_cost.alum_kg,
                f"=ROUND(GIA_NHOM*(1+HAO_HUT_PCT/100),0)",
                f"=ROUND(H{row}*I{row},0)",
                item_cost.glass_m2,
                round(result.item.glass.price_per_m2 or 0, 0),
                f"=ROUND(K{row}*L{row},0)",
                item_cost.hardware_cost,
                f"=ROUND((J{row}+M{row}+N{row})*NHAN_CONG_PCT/100,0)",
                f"=ROUND(G{row}*VATTU_M2,0)",
                f"=ROUND(F{row}*VAN_CHUYEN,0)",
                f"=J{row}+M{row}+N{row}+O{row}+P{row}+Q{row}",
                f"=ROUND(R{row}*LOI_NHUAN_PCT/100,0)",
                f"=ROUND(R{row}+S{row},-3)",
                f"=IF(G{row}=0,0,ROUND(T{row}/G{row},0))",
            ]
            for column, value in enumerate(values, start=1):
                ws.cell(row=row, column=column, value=value)
            row += 1
    else:
        for index in range(1, template_rows + 1):
            values = [
                index,
                f"CT{index}",
                "Cửa sổ mở quay",
                None,
                None,
                None,
                f"=ROUND(D{row}*E{row}/1000000*F{row},3)",
                None,
                f"=ROUND(GIA_NHOM*(1+HAO_HUT_PCT/100),0)",
                f"=ROUND(H{row}*I{row},0)",
                None,
                None,
                f"=ROUND(K{row}*L{row},0)",
                None,
                f"=ROUND((J{row}+M{row}+N{row})*NHAN_CONG_PCT/100,0)",
                f"=ROUND(G{row}*VATTU_M2,0)",
                f"=ROUND(F{row}*VAN_CHUYEN,0)",
                f"=J{row}+M{row}+N{row}+O{row}+P{row}+Q{row}",
                f"=ROUND(R{row}*LOI_NHUAN_PCT/100,0)",
                f"=ROUND(R{row}+S{row},-3)",
                f"=IF(G{row}=0,0,ROUND(T{row}/G{row},0))",
            ]
            for column, value in enumerate(values, start=1):
                ws.cell(row=row, column=column, value=value)
            row += 1

    first_row = 5
    last_row = row - 1
    for data_row in range(first_row, last_row + 1):
        for column in range(1, 22):
            cell = ws.cell(row=data_row, column=column)
            cell.border = BORDER
            if column in (7, 8, 11):
                cell.number_format = REAL
            elif column >= 9:
                cell.number_format = MONEY
        for column in (4, 5, 6, 8, 11, 12, 14):
            ws.cell(row=data_row, column=column).fill = PatternFill("solid", fgColor=INPUT_FILL)

    total_row = last_row + 1
    ws.cell(row=total_row, column=1, value="TỔNG")
    ws.merge_cells(start_row=total_row, start_column=1, end_row=total_row, end_column=5)
    for column in (7, 8, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20):
        letter = ws.cell(row=total_row, column=column).column_letter
        cell = ws.cell(row=total_row, column=column, value=f"=SUM({letter}{first_row}:{letter}{last_row})")
        cell.number_format = REAL if column in (7, 8, 11) else MONEY
    ws.cell(
        row=total_row, column=21, value=f"=IF(G{total_row}=0,0,ROUND(T{total_row}/G{total_row},0))"
    ).number_format = MONEY
    for column in range(1, 22):
        cell = ws.cell(row=total_row, column=column)
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor=TOTAL_FILL)
        cell.border = BORDER

    vat_row = total_row + 2
    ws.cell(row=vat_row, column=17, value="VAT (%)").font = Font(bold=True)
    ws.cell(row=vat_row, column=18, value="=VAT_PCT").number_format = "0.0"
    ws.cell(row=vat_row + 1, column=17, value="Tiền VAT").font = Font(bold=True)
    ws.cell(row=vat_row + 1, column=18, value=f"=ROUND(T{total_row}*VAT_PCT/100,0)").number_format = MONEY
    ws.cell(row=vat_row + 2, column=17, value="TỔNG THANH TOÁN").font = Font(bold=True, color=NAVY)
    grand = ws.cell(row=vat_row + 2, column=18, value=f"=T{total_row}+R{vat_row + 1}")
    grand.number_format = MONEY
    grand.font = Font(bold=True, size=11, color=TEAL)
    grand.fill = PatternFill("solid", fgColor=TOTAL_FILL)

def _alum_sheet(wb: Workbook, results: list[ItemResult]) -> None:
    ws = wb.create_sheet("03_Nhom")
    _title(ws, "CHI TIẾT NHÔM THEO MÃ THANH", "H")
    _header(
        ws,
        3,
        ["Mã thanh", "Tên", "kg/m", "Tổng dài (m)", "Tổng kg", "ĐG/kg (đã hao hụt)", "Thành tiền", "Tỷ trọng"],
        [16, 28, 10, 14, 12, 20, 16, 12],
    )

    aggregated: dict[str, dict[str, float]] = {}
    for result in results:
        for piece in result.pieces:
            length_m = piece.total_length_mm * result.item.qty / 1000
            bucket = aggregated.setdefault(
                piece.profile_code,
                {"name": piece.profile_name, "kg_per_m": piece.kg_per_m, "length": 0.0, "kg": 0.0},
            )
            bucket["length"] += length_m
            bucket["kg"] += length_m * piece.kg_per_m

    total_row = 4 + len(aggregated)
    row = 4
    for code, data in sorted(aggregated.items()):
        ws.cell(row=row, column=1, value=code).font = Font(bold=True)
        ws.cell(row=row, column=2, value=data["name"])
        ws.cell(row=row, column=3, value=data["kg_per_m"]).number_format = REAL
        ws.cell(row=row, column=4, value=round(data["length"], 2)).number_format = REAL
        ws.cell(row=row, column=5, value=round(data["kg"], 2)).number_format = REAL
        ws.cell(row=row, column=6, value="=ROUND(GIA_NHOM*(1+HAO_HUT_PCT/100),0)").number_format = MONEY
        ws.cell(row=row, column=7, value=f"=ROUND(E{row}*F{row},0)").number_format = MONEY
        ws.cell(row=row, column=8, value=f"=IF($E${total_row}=0,0,E{row}/$E${total_row})").number_format = PERCENT
        for column in range(1, 9):
            ws.cell(row=row, column=column).border = BORDER
        row += 1

    if aggregated:
        ws.cell(row=total_row, column=1, value="TỔNG")
        ws.merge_cells(start_row=total_row, start_column=1, end_row=total_row, end_column=3)
        for column in (4, 5, 7):
            letter = ws.cell(row=total_row, column=column).column_letter
            cell = ws.cell(row=total_row, column=column, value=f"=SUM({letter}4:{letter}{total_row - 1})")
            cell.number_format = REAL if column != 7 else MONEY
        for column in range(1, 9):
            cell = ws.cell(row=total_row, column=column)
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor=TOTAL_FILL)
            cell.border = BORDER
    ws.freeze_panes = "A4"


def _glass_sheet(wb: Workbook, results: list[ItemResult]) -> None:
    ws = wb.create_sheet("04_Kinh")
    _title(ws, "CHI TIẾT KÍNH", "J")
    _header(
        ws,
        3,
        ["Mã cửa", "Vị trí", "Loại kính", "Dày (mm)", "Rộng (mm)", "Cao (mm)", "SL", "DT (m²)", "ĐG (đ/m²)", "Thành tiền"],
        [12, 20, 26, 10, 12, 12, 8, 10, 14, 16],
    )
    row = 4
    for result in results:
        for piece in result.glass:
            quantity = piece.qty * result.item.qty
            area = piece.area_m2 * result.item.qty
            ws.cell(row=row, column=1, value=result.item.tag).font = Font(bold=True)
            ws.cell(row=row, column=2, value=piece.note)
            ws.cell(row=row, column=3, value=piece.name)
            ws.cell(row=row, column=4, value=piece.thickness_mm)
            ws.cell(row=row, column=5, value=piece.width_mm).number_format = MONEY
            ws.cell(row=row, column=6, value=piece.height_mm).number_format = MONEY
            ws.cell(row=row, column=7, value=quantity)
            ws.cell(row=row, column=8, value=round(area, 3)).number_format = REAL
            ws.cell(row=row, column=9, value=piece.price_per_m2).number_format = MONEY
            ws.cell(row=row, column=10, value=f"=ROUND(H{row}*I{row},0)").number_format = MONEY
            for column in range(1, 11):
                ws.cell(row=row, column=column).border = BORDER
            row += 1

    if row > 4:
        ws.cell(row=row, column=1, value="TỔNG")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=7)
        ws.cell(row=row, column=8, value=f"=SUM(H4:H{row - 1})").number_format = REAL
        ws.cell(row=row, column=10, value=f"=SUM(J4:J{row - 1})").number_format = MONEY
        for column in range(1, 11):
            cell = ws.cell(row=row, column=column)
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor=TOTAL_FILL)
            cell.border = BORDER
    ws.freeze_panes = "A4"


def _hardware_sheet(wb: Workbook, results: list[ItemResult]) -> None:
    ws = wb.create_sheet("05_PhuKien")
    _title(ws, "CHI TIẾT PHỤ KIỆN", "G")
    _header(
        ws,
        3,
        ["Mã cửa", "Mã VT", "Tên vật tư", "ĐVT", "SL", "ĐG (đ)", "Thành tiền"],
        [12, 18, 30, 8, 10, 14, 16],
    )
    row = 4
    for result in results:
        for line in result.hardware:
            quantity = line.qty * result.item.qty
            ws.cell(row=row, column=1, value=result.item.tag).font = Font(bold=True)
            ws.cell(row=row, column=2, value=line.key.upper())
            ws.cell(row=row, column=3, value=line.name)
            ws.cell(row=row, column=4, value=line.unit)
            ws.cell(row=row, column=5, value=round(quantity, 2))
            ws.cell(row=row, column=6, value=line.price).number_format = MONEY
            ws.cell(row=row, column=7, value=f"=ROUND(E{row}*F{row},0)").number_format = MONEY
            for column in range(1, 8):
                ws.cell(row=row, column=column).border = BORDER
            row += 1

    if row > 4:
        ws.cell(row=row, column=1, value="TỔNG")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
        ws.cell(row=row, column=7, value=f"=SUM(G4:G{row - 1})").number_format = MONEY
        for column in range(1, 8):
            cell = ws.cell(row=row, column=column)
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor=TOTAL_FILL)
            cell.border = BORDER
    ws.freeze_panes = "A4"


def _help_sheet(wb: Workbook, project: ProjectInfo | None, template: bool) -> None:
    ws = wb.create_sheet("06_HuongDan")
    _title(ws, "HƯỚNG DẪN SỬ DỤNG FILE TÍNH GIÁ THÀNH", "C", size=14)
    lines = [
        "",
        "1. Mở sheet 01_DauVao và điền giá nhà cung cấp vào các ô MÀU VÀNG:",
        "   - GIA_NHOM: đơn giá nhôm thanh (đ/kg)",
        "   - HAO_HUT_PCT: % hao hụt nhôm (bù phế cắt, đầu cây)",
        "   - NHAN_CONG_PCT: % nhân công tính trên vật tư (nhôm + kính + phụ kiện)",
        "   - LOI_NHUAN_PCT: % lợi nhuận mong muốn",
        "   - VAT_PCT: thuế GTGT",
        "   - VATTU_M2: vật tư phụ (keo, gioăng, vít...) theo m² cửa",
        "   - VAN_CHUYEN: chi phí giao lắp mỗi bộ cửa",
        "",
        "2. Sheet 02_GiaThanh: mỗi dòng là 1 hạng mục cửa.",
        "   Ô vàng là nhập tay (Rộng, Cao, SL, Nhôm kg, Kính m², ĐG kính, Phụ kiện).",
        "   Các cột Tiền nhôm / Nhân công / Vật tư / Vận chuyển / Giá vốn / Lãi / Giá bán tự tính.",
        "",
        "3. Sheet 03_Nhom, 04_Kinh, 05_PhuKien: bóc tách chi tiết để kiểm tra và đặt hàng.",
        "",
        "4. Đưa giá vào XingfaCAD: tab Catalogue → 'Nhập giá từ Excel' → chọn file này.",
        "   App sẽ đọc 7 thông số ở sheet 01_DauVao và cập nhật bảng giá, sau đó Build lại",
        "   để báo giá Excel/PDF dùng đúng giá mới.",
        "",
        "5. Lưu ý: sửa giá trong file này KHÔNG tự đổi giá trong app cho tới khi bạn nhập lại.",
        f"6. File mẫu cho: {project.code if project else 'dự án mới'} — tạo bởi XingfaCAD.",
    ]
    if template:
        lines.insert(1, "Đây là file MẪU: nhập kích thước và giá vào các ô vàng để tính thử giá thành.")
    row = 3
    for line in lines:
        cell = ws.cell(row=row, column=1, value=line)
        cell.alignment = Alignment(vertical="top", wrap_text=False)
        if line and not line.startswith(" "):
            cell.font = Font(bold=True, color=NAVY)
        row += 1
    ws.column_dimensions["A"].width = 110


def build_costing_workbook(
    path: str | Path,
    pricing: dict,
    catalog: dict,
    project: ProjectInfo | None = None,
    results: list[ItemResult] | None = None,
    cost: ProjectCost | None = None,
    template_rows: int = 0,
) -> Path:
    """Tạo file Excel tính giá thành (có dữ liệu dự án hoặc template trống)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    results = results or []
    wb = Workbook()
    _input_sheet(wb, pricing, catalog)
    _cost_sheet(wb, results, cost, template_rows=template_rows or 8)
    _alum_sheet(wb, results)
    _glass_sheet(wb, results)
    _hardware_sheet(wb, results)
    _help_sheet(wb, project, template=not results)
    wb.active = 0
    wb.save(path)
    return path


def build_costing_template(path: str | Path, pricing: dict, catalog: dict, rows: int = 8) -> Path:
    """File mẫu trống (chỉ có bảng giá đầu vào + công thức) để tính giá thành dự án mới."""
    return build_costing_workbook(path, pricing, catalog, project=None, results=None, cost=None, template_rows=rows)


def read_pricing_from_workbook(path: str | Path) -> dict[str, float]:
    """Đọc 7 thông số giá từ sheet 01_DauVao (cột A = mã, cột C = giá trị)."""
    workbook = load_workbook(path, data_only=True, read_only=True)
    sheet = workbook["01_DauVao"] if "01_DauVao" in workbook.sheetnames else workbook.active
    found: dict[str, float] = {}
    for row in sheet.iter_rows(min_row=1, max_col=3, values_only=True):
        if not row:
            continue
        code, _label, value = (list(row) + [None, None, None])[:3]
        if not isinstance(code, str):
            continue
        key = PRICING_KEYS.get(code.strip().upper())
        if key and isinstance(value, (int, float)):
            found[key] = float(value)
    workbook.close()
    return found
