"""Kiểm tra bật/tắt cột giá trên bảng giá qua API thật rồi khôi phục cấu hình."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "http://127.0.0.1:8010"
OUT = ROOT / "out" / "_book"
OUT.mkdir(parents=True, exist_ok=True)

book = httpx.get(f"{BASE}/api/pricing-book", timeout=30).json()["book"]
original = json.dumps(book, ensure_ascii=False)

book["settings"]["show_inc_vat"] = False
for level in book["levels"]:
    level["show_in_quote"] = level["code"] != "dl1"

saved = httpx.put(f"{BASE}/api/pricing-book", json=book, timeout=30)
result = saved.json()["result"]
print("put", saved.status_code, "show_inc_vat =", result["show_inc_vat"])
print("flags:", [(l["code"], l["show_in_quote"]) for l in result["groups"][0]["levels"]])

xlsx = httpx.get(f"{BASE}/api/pricing-book/export.xlsx", timeout=60)
(OUT / "bang_gia_an_dl1.xlsx").write_bytes(xlsx.content)
ws = load_workbook(OUT / "bang_gia_an_dl1.xlsx")["02_GiaDenKhach"]
print("headers:", [cell.value for cell in ws[4] if cell.value])

pdf = httpx.get(f"{BASE}/api/pricing-book/export.pdf", timeout=60)
(OUT / "bang_gia_an_dl1.pdf").write_bytes(pdf.content)
print("pdf bytes:", len(pdf.content))

restored = httpx.put(f"{BASE}/api/pricing-book", json=json.loads(original), timeout=30)
print("restore", restored.status_code, [l["show_in_quote"] for l in restored.json()["result"]["groups"][0]["levels"]])

import fitz  # noqa: E402

document = fitz.open(OUT / "bang_gia_an_dl1.pdf")
document[0].get_pixmap(dpi=100).save(OUT / "bang_gia_an_dl1.png")
print("pages:", document.page_count)
