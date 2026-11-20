"""Xuất thử bảng giá thành/bảng giá bán + build demo theo bảng giá (dev tool)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import fitz  # PyMuPDF

from xingfacad import catalog  # noqa: E402
from xingfacad.models import ProjectSpec  # noqa: E402
from xingfacad.pipeline import build_project  # noqa: E402
from xingfacad.price_book_export import build_book_pdf, build_book_xlsx  # noqa: E402
from xingfacad import pricing_book as pb  # noqa: E402

out = ROOT / "out" / "_book"
out.mkdir(parents=True, exist_ok=True)

book = pb.load_book()
result = pb.compute_book(book)
company = catalog.load_pricing().get("company", {})
xlsx = build_book_xlsx(book, result, company, out / "bang_gia_thanh_va_gia_ban.xlsx")
pdf = build_book_pdf(book, result, company, out / "bang_gia_ban.pdf")
print("xlsx:", xlsx.stat().st_size, "bytes |", "pdf:", pdf.stat().st_size, "bytes")

document = fitz.open(pdf)
print("pdf pages:", document.page_count)
for index, page in enumerate(document):
    page.get_pixmap(dpi=100).save(out / f"bang_gia_p{index + 1}.png")

spec = ProjectSpec.model_validate(json.loads((ROOT / "data/specs/demo_nha_a.json").read_text(encoding="utf-8")))
bom = build_project(spec, with_3d=False, with_drawings=False)
book_build = build_project(spec, with_3d=False, with_drawings=False, pricing_mode="book", price_level="le")
print("BOM  price:", f"{bom.summary['price']:,.0f}", "| VAT:", f"{bom.summary['vat']:,.0f}")
print("BOOK price:", f"{book_build.summary['price']:,.0f}", "| VAT:", f"{book_build.summary['vat']:,.0f}")
print("mode/level:", book_build.summary["pricing_mode"], book_build.summary["price_level"])
for item in book_build.items:
    print(f"  {item['tag']}: {item['area_m2']:.2f} m² → {item['price']:,.0f} đ (bảng giá) | đ/m² {item['unit_price_m2']:,.0f}")
