"""Xuất bảng chi phí giá thành (Excel nội bộ) và bảng giá đến tay khách (PDF)."""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .pdf_quote import _register_fonts
from .pricing_book import BookResult, PricingBook

NAVY = "1F3864"
TEAL = "0F766E"
LIGHT = "EEF2F8"
TOTAL = "FCE4D6"
THIN = Side(style="thin", color="B7C0CC")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
MONEY = "#,##0"
REAL = "#,##0.00"


def _title(ws, text: str, last_col: str, size: int = 14) -> None:
    ws["A1"] = text
    ws["A1"].font = Font(bold=True, size=size, color=NAVY)
    ws.merge_cells(f"A1:{last_col}1")
    ws["A1"].alignment = Alignment(horizontal="center")


def _header(ws, row: int, values: list[str], widths: list[float]) -> None:
    for index, (value, width) in enumerate(zip(values, widths), start=1):
        cell = ws.cell(row=row, column=index, value=value)
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.fill = PatternFill("solid", fgColor=NAVY)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER
        ws.column_dimensions[cell.column_letter].width = width
    ws.row_dimensions[row].height = 32


def build_book_xlsx(book: PricingBook, result: BookResult, company: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()

    ws = wb.active
    ws.title = "01_ChiPhiDauVao"
    last_col = chr(ord("A") + 1 + len(result.groups))
    _title(ws, "BẢNG CHI PHÍ GIÁ THÀNH ĐẦU VÀO (đ/m², chưa VAT)", last_col)
    ws["A2"] = (
        f"{company.get('name', '')} — {company.get('phone', '')} | Hiệu lực: {result.effective_date} | "
        "Cột = nhóm sản phẩm; dòng = khoản chi phí. Định mức chi tiết ở sheet 03_CauHinh."
    )
    ws["A2"].font = Font(italic=True, size=9, color="5B6570")
    ws.merge_cells(f"A2:{last_col}2")

    headers = ["Khoản chi phí", "Cách tính"] + [f"{group.code}\n{group.name}" for group in result.groups]
    widths = [34, 38] + [18] * len(result.groups)
    header_row = 4
    _header(ws, header_row, headers, widths)

    basis = {
        "alum": "kg/m² × đ/kg × (1+hao hụt)",
        "glass": "m² kính/m² × đ/m² × (1+hao hụt)",
        "hardware": "Σ(định mức/bộ × đơn giá) ÷ diện tích",
        "consumables": "đ/m²",
        "labor_production": "đ/m²",
        "labor_install": "đ/m²",
        "factory": "đ/m²",
        "packaging": "đ/m²",
        "transport": "đ/m²",
    }
    row = header_row + 1
    for line in result.groups[0].lines if result.groups else []:
        ws.cell(row=row, column=1, value=line.label).font = Font(bold=True)
        ws.cell(row=row, column=2, value=basis.get(line.key, ""))
        for offset, group in enumerate(result.groups):
            amount = next((item.amount_per_m2 for item in group.lines if item.key == line.key), 0)
            cell = ws.cell(row=row, column=3 + offset, value=round(amount, 0))
            cell.number_format = MONEY
        for column in range(1, 3 + len(result.groups)):
            ws.cell(row=row, column=column).border = BORDER
        row += 1

    extra_rows = [
        ("Cộng trực tiếp", "Σ 9 khoản trên", [group.direct_per_m2 for group in result.groups], True, MONEY),
        ("Bảo hành trích trước", "% cộng trực tiếp", [group.warranty_per_m2 for group in result.groups], False, MONEY),
        (
            "Chi phí quản lý – kinh doanh",
            "% cộng trực tiếp",
            [group.management_per_m2 for group in result.groups],
            False,
            MONEY,
        ),
        ("Lãi vay / tài chính", "% cộng trực tiếp", [group.finance_per_m2 for group in result.groups], False, MONEY),
        ("GIÁ THÀNH TOÀN BỘ (đ/m²)", "đ/m²", [group.cost_per_m2 for group in result.groups], True, MONEY),
        (
            "GIÁ THÀNH / BỘ MẪU",
            "đ/m² × diện tích mẫu",
            [group.cost_per_set for group in result.groups],
            True,
            MONEY,
        ),
        ("Diện tích mẫu (m²)", "Rộng × Cao", [group.norm_area_m2 for group in result.groups], False, REAL),
    ]
    for label, formula, values, strong, number_format in extra_rows:
        cell = ws.cell(row=row, column=1, value=label)
        cell.font = Font(bold=True, color=NAVY if strong else "000000")
        ws.cell(row=row, column=2, value=formula)
        for offset, value in enumerate(values):
            target = ws.cell(row=row, column=3 + offset, value=round(value, 2))
            target.number_format = number_format
            if strong:
                target.font = Font(bold=True)
        for column in range(1, 3 + len(result.groups)):
            ws.cell(row=row, column=column).border = BORDER
            if strong:
                ws.cell(row=row, column=column).fill = PatternFill("solid", fgColor=TOTAL)
        row += 1

    ws.cell(
        row=row + 1,
        column=1,
        value=f"VAT {result.vat_percent:g}% cộng ngoài khi báo giá · làm tròn {result.round_to:,.0f} đ",
    )
    ws.freeze_panes = "C5"

    # ---- Sheet 2: giá đến tay khách ----
    ws2 = wb.create_sheet("02_GiaDenKhach")
    levels = [level for level in (result.groups[0].levels if result.groups else []) if level.show_in_quote]
    headers2 = ["Nhóm sản phẩm", "Kích thước mẫu", "Giá vốn/m²"]
    for level in levels:
        headers2.append(f"{level.name}\nchưa VAT")
        if result.show_inc_vat:
            headers2.append(f"{level.name}\nđã VAT {result.vat_percent:g}%")
    widths2 = [26, 18, 16] + [20] * (len(headers2) - 3)
    last_col2 = chr(ord("A") + len(headers2) - 1)
    _title(ws2, "BẢNG GIÁ ĐẾN TAY KHÁCH (đ/m²)", last_col2, 14)
    ws2["A2"] = (
        "Giá công bố CHƯA VAT; VAT cộng khi thanh toán. "
        f"Làm tròn {result.round_to:,.0f} đ. Giá/bộ mẫu = giá/m² × diện tích mẫu."
        + ("" if levels else " Chưa chọn cấp giá nào để hiển thị trong bảng giá.")
    )
    ws2["A2"].font = Font(italic=True, size=9, color="5B6570")
    ws2.merge_cells(f"A2:{last_col2}2")
    _header(ws2, 4, headers2, widths2)
    row2 = 5
    for group in result.groups:
        values: list[object] = [
            f"{group.code} — {group.name}",
            f"{group.norm_width_mm:.0f}×{group.norm_height_mm:.0f}",
            group.cost_per_m2,
        ]
        for level in group.levels:
            if not level.show_in_quote:
                continue
            values.append(level.price_ex_vat_m2)
            if result.show_inc_vat:
                values.append(level.price_inc_vat_m2)
        for column, value in enumerate(values, start=1):
            cell = ws2.cell(row=row2, column=column, value=value)
            cell.border = BORDER
            if column >= 3:
                cell.number_format = MONEY
        row2 += 1

    row2 += 1
    ws2.cell(row=row2, column=1, value="Giá trọn bộ theo kích thước mẫu (đ/bộ)").font = Font(
        bold=True, size=12, color=NAVY
    )
    row2 += 1
    headers3 = ["Nhóm sản phẩm"] + [f"{level.name}" for level in levels]
    _header(ws2, row2, headers3, [26] + [22] * len(levels))
    row2 += 1
    for group in result.groups:
        ws2.cell(row=row2, column=1, value=f"{group.code} — {group.name}").border = BORDER
        visible = [level for level in group.levels if level.show_in_quote]
        for offset, level in enumerate(visible):
            cell = ws2.cell(row=row2, column=2 + offset, value=level.price_ex_vat_set)
            cell.number_format = MONEY
            cell.border = BORDER
        row2 += 1
    ws2.freeze_panes = "C5"

    # ---- Sheet 3: cấu hình ----
    ws3 = wb.create_sheet("03_CauHinh")
    _title(ws3, "CẤU HÌNH ĐỊNH MỨC & CẤP GIÁ", "E", 14)
    _header(ws3, 3, ["Nhóm", "Thông số", "Giá trị", "Đơn vị", "Ghi chú"], [14, 34, 16, 12, 40])
    row3 = 4
    for group in book.groups:
        cost = group.cost
        norm = group.norm
        entries: list[tuple[str, str, object, str, str]] = [
            ("norm", "Kích thước mẫu", f"{norm.width_mm:.0f}×{norm.height_mm:.0f}", "mm", norm.system),
            ("alum_kg_per_m2", "Nhôm / m²", cost.alum_kg_per_m2, "kg/m²", ""),
            ("alum_price_per_kg", "Đơn giá nhôm", cost.alum_price_per_kg, "đ/kg", ""),
            ("alum_waste_percent", "Hao hụt nhôm", cost.alum_waste_percent, "%", ""),
            ("glass_m2_per_m2", "Kính / m² cửa", cost.glass_m2_per_m2, "m²/m²", ""),
            ("glass_price_per_m2", "Đơn giá kính", cost.glass_price_per_m2, "đ/m²", ""),
            ("glass_waste_percent", "Hao hụt kính", cost.glass_waste_percent, "%", ""),
            (
                "hardware",
                "Phụ kiện / bộ",
                " + ".join(f"{item.key}×{item.qty_per_set:g}" for item in cost.hardware_items),
                "bộ",
                "",
            ),
            ("consumables_per_m2", "Vật tư phụ", cost.consumables_per_m2, "đ/m²", ""),
            ("labor_production_per_m2", "Nhân công sản xuất", cost.labor_production_per_m2, "đ/m²", ""),
            ("labor_install_per_m2", "Nhân công lắp đặt", cost.labor_install_per_m2, "đ/m²", ""),
            ("factory_per_m2", "Chi phí xưởng", cost.factory_per_m2, "đ/m²", ""),
            ("packaging_per_m2", "Đóng gói", cost.packaging_per_m2, "đ/m²", ""),
            ("transport_per_m2", "Vận chuyển", cost.transport_per_m2, "đ/m²", ""),
            ("warranty_percent", "Bảo hành", cost.warranty_percent, "%", ""),
            ("management_percent", "Quản lý – kinh doanh", cost.management_percent, "%", ""),
            ("finance_percent", "Lãi vay", cost.finance_percent, "%", ""),
        ]
        for _key, label, value, unit, note in entries:
            ws3.cell(row=row3, column=1, value=group.code).font = Font(bold=True)
            ws3.cell(row=row3, column=2, value=label)
            cell = ws3.cell(row=row3, column=3, value=value)
            if isinstance(value, (int, float)) and unit.startswith("đ"):
                cell.number_format = MONEY
            ws3.cell(row=row3, column=4, value=unit)
            ws3.cell(row=row3, column=5, value=note)
            for column in range(1, 6):
                ws3.cell(row=row3, column=column).border = BORDER
            row3 += 1

    row3 += 1
    ws3.cell(row=row3, column=1, value="CẤP GIÁ").font = Font(bold=True, size=12, color=NAVY)
    row3 += 1
    _header(ws3, row3, ["Mã", "Tên cấp", "% lãi", "% chiết khấu", "Gồm lắp đặt"], [14, 34, 16, 16, 16])
    row3 += 1
    for level in book.levels:
        ws3.cell(row=row3, column=1, value=level.code)
        ws3.cell(row=row3, column=2, value=level.name)
        ws3.cell(row=row3, column=3, value=level.margin_percent)
        ws3.cell(row=row3, column=4, value=level.discount_percent)
        ws3.cell(row=row3, column=5, value="Có" if level.include_install else "Không")
        for column in range(1, 6):
            ws3.cell(row=row3, column=column).border = BORDER
        row3 += 1

    wb.active = 0
    wb.save(path)
    return path


def build_book_pdf(
    book: PricingBook,
    result: BookResult,
    company: dict,
    path: str | Path,
    title_suffix: str = "",
) -> Path:
    """Bảng giá gửi khách (không hiển thị chi phí)."""
    regular, bold = _register_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(path),
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=10 * mm,
        bottomMargin=12 * mm,
        title="Bang gia ban",
        author=str(company.get("name", "XingfaCAD")),
    )

    def style(name: str, size: float, font: str, **kwargs) -> ParagraphStyle:
        defaults = {"fontName": font, "fontSize": size, "leading": size * 1.3, "textColor": colors.black}
        defaults.update(kwargs)
        return ParagraphStyle(name, **defaults)

    company_style = style("company", 12.5, bold, textColor=colors.HexColor(f"#{NAVY}"))
    small = style("small", 8, regular, textColor=colors.HexColor("#5B6570"))
    head = style("head", 8, bold, textColor=colors.white, alignment=TA_CENTER)
    cell = style("cell", 8.4, regular)
    cell_b = style("cell_b", 8.6, bold)
    cell_r = style("cell_r", 8.4, regular, alignment=TA_RIGHT)
    cell_c = style("cell_c", 8.4, regular, alignment=TA_CENTER)
    note = style("note", 8.2, regular, leading=11)

    levels = [level for level in (result.groups[0].levels if result.groups else []) if level.show_in_quote]
    story: list = []

    left = [
        Paragraph(str(company.get("name", "XINGFACAD")), company_style),
        Paragraph(str(company.get("address", "")), small),
        Paragraph(f"ĐT: {company.get('phone', '')}   MST: {company.get('tax_code', '')}", small),
    ]
    right = [
        Paragraph("BẢNG GIÁ BÁN", style("t", 15, bold, alignment=TA_RIGHT, textColor=colors.HexColor(f"#{TEAL}"))),
        Paragraph(f"Hiệu lực: {result.effective_date}", style("d", 8.6, regular, alignment=TA_RIGHT)),
        Paragraph(title_suffix or "Áp dụng cho cửa nhôm Xingfa", style("d2", 8.6, regular, alignment=TA_RIGHT)),
    ]
    header = Table([[left, right]], colWidths=[150 * mm, 123 * mm])
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -1), 1.1, colors.HexColor(f"#{NAVY}")),
            ]
        )
    )
    story += [header, Spacer(1, 6)]

    story.append(
        Paragraph(
            f"Đơn giá tính theo m² cửa hoàn thiện, <b>chưa bao gồm VAT {result.vat_percent:g}%</b>"
            + (f"; cột <i>đã VAT</i> chỉ để tham khảo." if result.show_inc_vat else ".")
            + " Giá đã gồm nhôm, kính, phụ kiện, nhân công và vận chuyển theo từng cấp giá.",
            note,
        )
    )
    story.append(Spacer(1, 4))

    header_row = [Paragraph("Nhóm sản phẩm", head), Paragraph("Kích thước mẫu", head)]
    for level in levels:
        header_row.append(Paragraph(f"{level.name}\nchưa VAT", head))
        if result.show_inc_vat:
            header_row.append(Paragraph(f"{level.name}\nđã VAT {result.vat_percent:g}%", head))
    rows: list[list] = [header_row]
    for group in result.groups:
        row: list = [
            Paragraph(f"<b>{group.code}</b> — {group.name}", cell_b),
            Paragraph(f"{group.norm_width_mm:.0f}×{group.norm_height_mm:.0f} mm", cell_c),
        ]
        for level in group.levels:
            if not level.show_in_quote:
                continue
            row.append(Paragraph(f"{level.price_ex_vat_m2:,.0f}".replace(",", "."), cell_r))
            if result.show_inc_vat:
                row.append(Paragraph(f"{level.price_inc_vat_m2:,.0f}".replace(",", "."), cell_r))
        rows.append(row)

    widths = [58 * mm, 30 * mm] + [27 * mm] * (len(header_row) - 2)
    price_table = Table(rows, colWidths=widths, repeatRows=1)
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(f"#{NAVY}")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D3E0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for index in range(1, len(rows)):
        if index % 2 == 0:
            commands.append(("BACKGROUND", (0, index), (-1, index), colors.HexColor(f"#{LIGHT}")))
    price_table.setStyle(TableStyle(commands))
    story += [price_table, Spacer(1, 8)]

    story.append(
        Paragraph(
            "Giá trọn bộ theo kích thước mẫu (chưa VAT)",
            style("h", 9.5, bold, textColor=colors.HexColor(f"#{NAVY}")),
        )
    )
    story.append(Spacer(1, 3))
    set_header = [Paragraph("Nhóm sản phẩm", head)] + [Paragraph(level.name, head) for level in levels]
    set_rows: list[list] = [set_header]
    for group in result.groups:
        row: list = [Paragraph(f"{group.code} — {group.name}", cell)]
        for level in group.levels:
            if level.show_in_quote:
                row.append(Paragraph(f"{level.price_ex_vat_set:,.0f}".replace(",", ".") + " đ", cell_r))
        set_rows.append(row)
    set_table = Table(set_rows, colWidths=[70 * mm] + [30 * mm] * len(levels), repeatRows=1)
    set_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(f"#{NAVY}")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D3E0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story += [set_table, Spacer(1, 6)]

    defaults = [
        "Giá chưa bao gồm VAT; VAT được cộng vào khi thanh toán.",
        "Giá đã bao gồm công lắp đặt và vận chuyển trong nội thành (trừ cấp giá không gồm lắp đặt).",
        "Bảo hành 24 tháng phần nhôm và phụ kiện, 12 tháng phần kính.",
        "Kích thước thực tế sẽ được đo lại trước khi sản xuất; sai lệch lớn sẽ điều chỉnh giá theo m².",
        "Bảng giá có hiệu lực đến khi có bảng giá mới.",
    ]
    notes = [line.strip() for line in (book.note or "").splitlines() if line.strip()]
    story.append(Paragraph("Ghi chú", style("h2", 9.5, bold, textColor=colors.HexColor(f"#{NAVY}"))))
    for line in notes + defaults:
        story.append(Paragraph(f"• {line}", note))

    def footer(canvas, doc_obj) -> None:
        canvas.saveState()
        canvas.setFont(regular, 7.5)
        canvas.setFillColor(colors.HexColor("#5B6570"))
        canvas.drawString(12 * mm, 6 * mm, f"{company.get('name', 'XingfaCAD')} — Bảng giá bán")
        canvas.drawRightString(A4[1] - 12 * mm, 6 * mm, f"Trang {doc_obj.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return path
