"""Test xuất PDF báo giá + file tính giá thành + template/import giá."""
from __future__ import annotations

from openpyxl import load_workbook

from xingfacad import catalog
from xingfacad.costing import build_costing_template, read_pricing_from_workbook
from xingfacad.pdf_quote import money_to_words
from xingfacad.pipeline import build_project


def test_money_to_words():
    assert money_to_words(0) == "Không đồng"
    assert money_to_words(4_588_600).lower().startswith("bốn triệu năm trăm tám mươi tám nghìn")
    assert money_to_words(49_557_000).startswith("Bốn mươi chín triệu năm trăm năm mươi bảy nghìn")


def test_build_creates_pdf_and_costing_workbook(sandbox, demo_project):
    outcome = build_project(demo_project, with_3d=False)
    folder = sandbox / "out" / demo_project.project.code

    pdf_path = folder / f"bao_gia_{demo_project.project.code}.pdf"
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 20_000
    assert pdf_path.read_bytes()[:5] == b"%PDF-"

    costing_path = folder / f"gia_thanh_{demo_project.project.code}.xlsx"
    assert costing_path.exists()
    workbook = load_workbook(costing_path)
    assert workbook.sheetnames == [
        "01_DauVao", "02_GiaThanh", "03_Nhom", "04_Kinh", "05_PhuKien", "06_HuongDan",
    ]
    assert "GIA_NHOM" in workbook.defined_names
    assert "VAT_PCT" in workbook.defined_names

    cost_sheet = workbook["02_GiaThanh"]
    assert cost_sheet["B5"].value == demo_project.items[0].tag
    assert str(cost_sheet["G5"].value).startswith("=ROUND(")
    assert str(cost_sheet["J5"].value).startswith("=ROUND(H5*I5")
    assert str(cost_sheet["T5"].value).startswith("=ROUND(")
    assert cost_sheet["H5"].value > 0
    assert cost_sheet["A10"].value == "TỔNG"

    kinds = {artifact.kind for artifact in outcome.artifacts}
    assert {"pdf", "xlsx"} <= kinds
    names = {artifact.name for artifact in outcome.artifacts}
    assert f"bao_gia_{demo_project.project.code}.pdf" in names
    assert f"gia_thanh_{demo_project.project.code}.xlsx" in names


def test_costing_template_roundtrip(sandbox, tmp_path):
    pricing = catalog.load_pricing()
    template = tmp_path / "bang_tinh_gia_thanh.xlsx"
    build_costing_template(template, pricing, catalog.load_catalog())

    workbook = load_workbook(template)
    assert workbook.sheetnames[0] == "01_DauVao"
    assert str(workbook["02_GiaThanh"]["G5"].value).startswith("=ROUND(")

    found = read_pricing_from_workbook(template)
    assert found["aluminum_price_per_kg"] == pricing["aluminum_price_per_kg"]
    assert found["vat_percent"] == pricing["vat_percent"]

    sheet = workbook["01_DauVao"]
    for row in range(1, sheet.max_row + 1):
        if sheet.cell(row=row, column=1).value == "GIA_NHOM":
            sheet.cell(row=row, column=3, value=123000)
        if sheet.cell(row=row, column=1).value == "LOI_NHUAN_PCT":
            sheet.cell(row=row, column=3, value=25)
    workbook.save(template)

    updated = read_pricing_from_workbook(template)
    assert updated["aluminum_price_per_kg"] == 123000
    assert updated["profit_percent"] == 25
