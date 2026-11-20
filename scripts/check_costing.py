"""Kiểm tra file tính giá thành + template + đọc lại giá (dev tool)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from openpyxl import load_workbook  # noqa: E402

from xingfacad import catalog  # noqa: E402
from xingfacad.costing import build_costing_template, read_pricing_from_workbook  # noqa: E402

book = ROOT / "out" / "DEMO-001" / "gia_thanh_DEMO-001.xlsx"
wb = load_workbook(book)
print("sheets:", wb.sheetnames)
print("defined names:", sorted(wb.defined_names.keys()))

ws = wb["02_GiaThanh"]
print("header:", [ws.cell(row=4, column=c).value for c in (1, 2, 3, 7, 8, 10, 18, 20)])
print("row5:", [ws.cell(row=5, column=c).value for c in (2, 4, 5, 6, 7, 8, 9, 10, 18, 20)])
print("total row:", [ws.cell(row=10, column=c).value for c in (1, 7, 8, 10, 18, 20)])

alum = wb["03_Nhom"]
print("alum rows:", [(alum.cell(row=r, column=1).value, alum.cell(row=r, column=5).value) for r in range(4, 8)])

pricing = read_pricing_from_workbook(book)
print("read pricing:", pricing)

template = ROOT / "out" / "_templates" / "bang_tinh_gia_thanh.xlsx"
build_costing_template(template, catalog.load_pricing(), catalog.load_catalog())
twb = load_workbook(template)
print("template sheets:", twb.sheetnames)
tws = twb["02_GiaThanh"]
print("template row5:", [tws.cell(row=5, column=c).value for c in (1, 2, 7, 9, 10, 18)])
print("template pricing:", read_pricing_from_workbook(template))
