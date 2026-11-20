"""Xuất báo giá PDF (reportlab) — bản gửi khách, in A4, có số tiền bằng chữ."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .models import ItemResult, ProjectInfo
from .pricing import ProjectCost

NAVY = colors.HexColor("#1F3864")
TEAL = colors.HexColor("#0F766E")
LIGHT = colors.HexColor("#EEF2F8")
LIGHT_2 = colors.HexColor("#F7F9FC")
GREY = colors.HexColor("#5B6570")

_DIGITS = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def _read_triple(value: int, force_full: bool) -> str:
    hundreds, remainder = divmod(value, 100)
    tens, units = divmod(remainder, 10)
    parts: list[str] = []
    if hundreds or force_full:
        parts.append(f"{_DIGITS[hundreds]} trăm")
    if tens == 0 and units == 0:
        return " ".join(parts)
    if tens == 1:
        parts.append("mười")
    elif tens > 1:
        parts.append(f"{_DIGITS[tens]} mươi")
    if units:
        if units == 1 and tens > 1:
            parts.append("mốt")
        elif units == 5 and tens:
            parts.append("lăm")
        elif units == 4 and tens > 1:
            parts.append("tư")
        else:
            if tens == 0 and (hundreds or force_full):
                parts.append("linh")
            parts.append(_DIGITS[units])
    return " ".join(parts)


def money_to_words(amount: float) -> str:
    """4.588.600 -> 'Bốn triệu năm trăm tám mươi tám nghìn sáu trăm đồng'."""
    number = int(round(amount))
    if number <= 0:
        return "Không đồng"
    units = ["", "nghìn", "triệu", "tỷ"]
    chunks: list[str] = []
    index = 0
    while number > 0:
        triple = number % 1000
        number //= 1000
        if triple:
            text = _read_triple(triple, force_full=number > 0)
            unit = units[index] if index < len(units) else ""
            chunks.insert(0, f"{text} {unit}".strip())
        index += 1
    sentence = " ".join(chunks).strip()
    sentence = sentence[:1].upper() + sentence[1:]
    return f"{sentence} đồng"


def _register_fonts() -> tuple[str, str]:
    candidates = [
        ("ArialVI", "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("ArialVI2", "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
        ("DejaVuVI", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("LiberationVI", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ]
    for name, regular, bold in candidates:
        if Path(regular).exists() and Path(bold).exists():
            try:
                pdfmetrics.registerFont(TTFont(name, regular))
                pdfmetrics.registerFont(TTFont(f"{name}-Bold", bold))
                pdfmetrics.registerFontFamily(name, normal=name, bold=f"{name}-Bold", italic=name, boldItalic=f"{name}-Bold")
                return name, f"{name}-Bold"
            except Exception:
                continue
    return "Helvetica", "Helvetica-Bold"


def _style(name: str, size: float, font: str, **kwargs) -> ParagraphStyle:
    defaults = {"fontName": font, "fontSize": size, "leading": size * 1.35, "textColor": colors.black}
    defaults.update(kwargs)
    return ParagraphStyle(name, **defaults)


def _money(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def _item_description(result: ItemResult) -> str:
    item = result.item
    parts = [
        f"{item.type_label} {item.width_mm:.0f}×{item.height_mm:.0f}mm",
        f"hệ {result.system_code}",
        f"kính {item.glass.thickness_mm:g}mm",
    ]
    hardware = [line.name for line in result.hardware if line.key.startswith(("hinge", "lock"))]
    if hardware:
        parts.append("phụ kiện: " + ", ".join(hardware[:3]))
    if item.notes:
        parts.append(item.notes.strip())
    return ", ".join(parts)


def build_quote_pdf(
    project: ProjectInfo,
    results: list[ItemResult],
    cost: ProjectCost,
    pricing: dict,
    out_path: str | Path,
    catalog: dict | None = None,
) -> Path:
    from xml.sax.saxutils import escape

    regular, bold = _register_fonts()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    company = pricing.get("company", {}) or {}
    today = dt.date.today().strftime("%d/%m/%Y")
    quote_no = f"{project.code}/BG-{dt.date.today():%Y%m%d}"

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=15 * mm,
        title=f"Bao gia {project.code}",
        author=str(company.get("name", "XingfaCAD")),
        subject="Bao gia cua nhom Xingfa",
    )

    company_style = _style("company", 12.5, bold, textColor=NAVY)
    small = _style("small", 8, regular, textColor=GREY)
    note = _style("note", 8.2, regular, leading=11.5, textColor=colors.HexColor("#333333"))
    meta = _style("meta", 8.8, regular)
    meta_b = _style("meta_b", 8.8, bold)
    head_cell = _style("head_cell", 7.8, bold, textColor=colors.white, alignment=TA_CENTER)
    cell = _style("cell", 7.8, regular)
    cell_r = _style("cell_r", 7.8, regular, alignment=TA_RIGHT)
    cell_c = _style("cell_c", 7.8, regular, alignment=TA_CENTER)
    cell_b = _style("cell_b", 8, bold)
    total_label = _style("total_label", 9, regular, alignment=TA_RIGHT)
    total_value = _style("total_value", 9, regular, alignment=TA_RIGHT)
    grand_label = _style("grand_label", 9.5, bold, alignment=TA_RIGHT, textColor=NAVY)
    grand_value = _style("grand_value", 10, bold, alignment=TA_RIGHT, textColor=TEAL)

    story: list = []

    header_left = [
        Paragraph(escape(str(company.get("name", "XINGFACAD"))), company_style),
        Paragraph(escape(str(company.get("address", ""))), small),
        Paragraph(
            escape(f"ĐT: {company.get('phone', '')}   MST: {company.get('tax_code', '')}"),
            small,
        ),
    ]
    header_right = [
        Paragraph("BẢNG BÁO GIÁ", _style("bg", 13, bold, alignment=TA_RIGHT, textColor=TEAL)),
        Paragraph(escape(f"Số: {quote_no}"), _style("no", 8.5, regular, alignment=TA_RIGHT)),
        Paragraph(escape(f"Ngày: {today}"), _style("date", 8.5, regular, alignment=TA_RIGHT)),
    ]
    header = Table([[header_left, header_right]], colWidths=[110 * mm, 72 * mm])
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -1), 1.1, NAVY),
            ]
        )
    )
    story += [header, Spacer(1, 7)]

    request_org = project.request_org or project.customer or "—"
    request_contact = " – ".join(
        part for part in (project.request_contact, project.request_phone) if part
    )
    if request_contact:
        request_org = f"{request_org} ({request_contact})"
    info_rows = [
        [
            Paragraph("Đơn vị yêu cầu:", meta_b),
            Paragraph(escape(request_org), meta),
            Paragraph("Mã dự án:", meta_b),
            Paragraph(escape(project.code), meta),
        ],
        [
            Paragraph("Khách hàng:", meta_b),
            Paragraph(escape(project.customer or "—"), meta),
            Paragraph("Ngày báo giá:", meta_b),
            Paragraph(escape(project.date), meta),
        ],
        [
            Paragraph("Công trình:", meta_b),
            Paragraph(escape(project.name or "—"), meta),
            Paragraph("Hiệu lực:", meta_b),
            Paragraph("15 ngày", meta),
        ],
        [
            Paragraph("Địa chỉ:", meta_b),
            Paragraph(escape(project.address or "—"), meta),
            Paragraph("Người báo giá:", meta_b),
            Paragraph(escape(project.quoted_by or "—"), meta),
        ],
        [
            Paragraph("Số báo giá:", meta_b),
            Paragraph(escape(quote_no), meta),
            Paragraph("ĐT người báo giá:", meta_b),
            Paragraph(escape(project.quoted_by_phone or "—"), meta),
        ],
    ]
    info = Table(info_rows, colWidths=[24 * mm, 92 * mm, 26 * mm, 40 * mm])
    info.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_2),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#C9D3E0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DCE4EE")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story += [info, Spacer(1, 8)]

    headers = ["STT", "Mã", "Mô tả", "ĐVT", "SL", "DT (m²)", "Đơn giá/m²", "Thành tiền"]
    data: list[list] = [[Paragraph(text, head_cell) for text in headers]]
    for index, (result, item_cost) in enumerate(zip(results, cost.items), start=1):
        data.append(
            [
                Paragraph(str(index), cell_c),
                Paragraph(escape(result.item.tag), cell_b),
                Paragraph(escape(_item_description(result)), cell),
                Paragraph("bộ", cell_c),
                Paragraph(str(result.item.qty), cell_c),
                Paragraph(f"{item_cost.area_m2:.2f}", cell_r),
                Paragraph(_money(item_cost.unit_price_m2), cell_r),
                Paragraph(_money(item_cost.price), cell_r),
            ]
        )

    widths = [10 * mm, 15 * mm, 72 * mm, 11 * mm, 9 * mm, 15 * mm, 22 * mm, 28 * mm]
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D3E0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    for row_index in range(1, len(data)):
        if row_index % 2 == 0:
            table_style.append(("BACKGROUND", (0, row_index), (-1, row_index), LIGHT_2))
    items_table = Table(data, colWidths=widths, repeatRows=1)
    items_table.setStyle(TableStyle(table_style))
    story += [items_table, Spacer(1, 6)]

    totals_rows = [
        [Paragraph("Cộng tiền hàng:", total_label), Paragraph(f"{_money(cost.price)} đ", total_value)],
        [
            Paragraph(f"Thuế GTGT ({cost.vat_percent:g}%):", total_label),
            Paragraph(f"{_money(cost.vat)} đ", total_value),
        ],
        [Paragraph("TỔNG THANH TOÁN:", grand_label), Paragraph(f"{_money(cost.price_with_vat)} đ", grand_value)],
    ]
    totals = Table(totals_rows, colWidths=[52 * mm, 34 * mm])
    totals.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 2), (-1, 2), 0.8, NAVY),
                ("BACKGROUND", (0, 2), (-1, 2), LIGHT),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(totals)
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            escape(f"Bằng chữ: {money_to_words(cost.price_with_vat)}."),
            _style("words", 8.6, bold, textColor=colors.HexColor("#333333")),
        )
    )

    terms = pricing.get("quote_terms") or [
        "Giá đã bao gồm nhôm, kính, phụ kiện, nhân công lắp đặt và vận chuyển trong nội thành.",
        "Thời gian sản xuất và lắp đặt: 12 – 15 ngày kể từ ngày xác nhận đơn hàng và tạm ứng.",
        "Thanh toán: tạm ứng 50% khi ký hợp đồng, 45% khi giao hàng, 5% sau nghiệm thu.",
        "Bảo hành: 24 tháng phần nhôm và phụ kiện, 12 tháng phần kính; bảo trì miễn phí 12 tháng.",
        "Báo giá có hiệu lực 15 ngày; kích thước sẽ được đo lại thực tế trước khi sản xuất.",
    ]
    story.append(Paragraph("Điều khoản báo giá", _style("h2", 10.5, bold, textColor=NAVY, spaceBefore=10, spaceAfter=4)))
    for term in terms:
        story.append(Paragraph(f"• {escape(str(term))}", note))

    sig_style = _style("sig", 9, bold, alignment=TA_CENTER)
    sig_note = _style("sig_note", 7.5, regular, alignment=TA_CENTER, textColor=GREY)
    signature = Table(
        [
            [Paragraph("ĐẠI DIỆN KHÁCH HÀNG", sig_style), Paragraph("ĐẠI DIỆN CÔNG TY", sig_style)],
            [Paragraph("(Ký, ghi rõ họ tên)", sig_note), Paragraph("(Ký, ghi rõ họ tên)", sig_note)],
            [Spacer(1, 18 * mm), Spacer(1, 18 * mm)],
            [
                Paragraph(escape(project.customer or ""), sig_note),
                Paragraph(escape(project.quoted_by or ""), sig_note),
            ],
        ],
        colWidths=[91 * mm, 91 * mm],
    )
    story.append(KeepTogether([Spacer(1, 8), signature]))

    def grid_style(row_count: int) -> TableStyle:
        commands = [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D3E0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]
        for row_index in range(1, row_count):
            if row_index % 2 == 0:
                commands.append(("BACKGROUND", (0, row_index), (-1, row_index), LIGHT_2))
        return TableStyle(commands)

    if results:
        story.append(PageBreak())
        story.append(
            Paragraph(
                "PHỤ LỤC: QUY CÁCH KÍNH & PHỤ KIỆN",
                _style("appendix", 12, bold, textColor=NAVY, alignment=TA_CENTER),
            )
        )
        story.append(Spacer(1, 5))

        glass_header = ["Mã cửa", "Vị trí", "Loại kính", "Dày (mm)", "Rộng (mm)", "Cao (mm)", "SL", "DT (m²)"]
        glass_rows: list[list] = [[Paragraph(text, head_cell) for text in glass_header]]
        for result in results:
            for piece in result.glass:
                glass_rows.append(
                    [
                        Paragraph(escape(result.item.tag), cell_b),
                        Paragraph(escape(piece.note), cell),
                        Paragraph(escape(piece.name), cell),
                        Paragraph(f"{piece.thickness_mm:g}", cell_c),
                        Paragraph(f"{piece.width_mm:.0f}", cell_r),
                        Paragraph(f"{piece.height_mm:.0f}", cell_r),
                        Paragraph(str(piece.qty * result.item.qty), cell_c),
                        Paragraph(f"{piece.area_m2 * result.item.qty:.3f}", cell_r),
                    ]
                )
        glass_table = Table(
            glass_rows,
            colWidths=[16 * mm, 24 * mm, 42 * mm, 14 * mm, 16 * mm, 16 * mm, 10 * mm, 18 * mm],
            repeatRows=1,
        )
        glass_table.setStyle(grid_style(len(glass_rows)))
        story += [glass_table, Spacer(1, 9)]

        hw_header = ["Mã cửa", "Mã VT", "Tên vật tư", "ĐVT", "SL", "Đơn giá", "Thành tiền"]
        hw_rows: list[list] = [[Paragraph(text, head_cell) for text in hw_header]]
        consumables = {"gasket", "silicone", "screw"}
        for result in results:
            for line in result.hardware:
                if line.key in consumables:
                    continue
                quantity = line.qty * result.item.qty
                hw_rows.append(
                    [
                        Paragraph(escape(result.item.tag), cell_b),
                        Paragraph(escape(line.key.upper()), cell),
                        Paragraph(escape(line.name), cell),
                        Paragraph(escape(line.unit), cell_c),
                        Paragraph(f"{quantity:g}", cell_r),
                        Paragraph(_money(line.price), cell_r),
                        Paragraph(_money(quantity * line.price), cell_r),
                    ]
                )
        hw_table = Table(
            hw_rows,
            colWidths=[16 * mm, 24 * mm, 70 * mm, 12 * mm, 14 * mm, 22 * mm, 24 * mm],
            repeatRows=1,
        )
        hw_table.setStyle(grid_style(len(hw_rows)))
        story.append(hw_table)

    def _page_footer(canvas, doc_obj) -> None:
        canvas.saveState()
        canvas.setFont(regular, 7.5)
        canvas.setFillColor(GREY)
        canvas.drawString(14 * mm, 8 * mm, f"{company.get('name', 'XingfaCAD')} · Báo giá {project.code}")
        canvas.drawRightString(A4[0] - 14 * mm, 8 * mm, f"Trang {doc_obj.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return out_path
