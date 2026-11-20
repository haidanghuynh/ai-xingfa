"""Kiểm tra cập nhật thông tin báo giá (đơn vị yêu cầu, người báo giá) + xem trước PDF."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import fitz  # noqa: E402

from xingfacad.models import ProjectSpec  # noqa: E402
from xingfacad.pipeline import regenerate_quote_docs  # noqa: E402

raw = json.loads((ROOT / "data/specs/demo_nha_a.json").read_text(encoding="utf-8"))
raw["project"].update(
    {
        "request_org": "CÔNG TY TNHH XÂY DỰNG ABC",
        "request_contact": "Anh Nguyễn Văn A",
        "request_phone": "0903 123 456",
        "quoted_by": "Trần Thị B",
        "quoted_by_phone": "0912 345 678",
    }
)
project = ProjectSpec.model_validate(raw)
result = regenerate_quote_docs(project, pricing_mode="book", price_level="le")
print("ok:", result["ok"], "| artifacts:", [(a["kind"], a["size"]) for a in result["artifacts"]])
print("summary:", {key: result["summary"][key] for key in ("items", "price", "vat", "price_with_vat", "price_level")})

# Đọc lại project.json để chắc thông tin báo giá đã lưu
saved = json.loads((ROOT / "out/DEMO-001/project.json").read_text(encoding="utf-8"))
print("saved quoted_by:", saved["project"]["quoted_by"], "| request_org:", saved["project"]["request_org"])

pdf = ROOT / "out/DEMO-001/bao_gia_DEMO-001.pdf"
document = fitz.open(pdf)
print("pdf pages:", document.page_count)
target = ROOT / "out/_book/quote_edit_p1.png"
document[0].get_pixmap(dpi=110).save(target)
print("preview:", target)
