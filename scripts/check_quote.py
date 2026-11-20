"""Kiểm tra PDF báo giá: số trang, text tiếng Việt, render PNG (dev tool)."""
from __future__ import annotations

import sys
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "out" / "DEMO-001" / "bao_gia_DEMO-001.pdf"
out_dir = ROOT / "out" / "_ui"
out_dir.mkdir(parents=True, exist_ok=True)

document = fitz.open(pdf_path)
print("pages:", document.page_count)
for index, page in enumerate(document):
    pixmap = page.get_pixmap(dpi=105)
    target = out_dir / f"quote_p{index + 1}.png"
    pixmap.save(target)
    print("rendered:", target.name, pixmap.width, "x", pixmap.height)

text = document[0].get_text()
for keyword in ("BẢNG BÁO GIÁ", "Khách hàng", "TỔNG THANH TOÁN", "Bằng chữ", "Điều khoản"):
    print(f"{keyword!r}:", keyword in text)
print("page2 has appendix:", "PHỤ LỤC" in document[-1].get_text())
