"""Kiểm tra các id mà app.js dùng có tồn tại trong index.html (dev only)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

html_ids = set(re.findall(r'id="([\w-]+)"', html))
js_ids = set(re.findall(r"\$\('#([\w-]+)'\)", js))
# các id được tạo động
dynamic = {"validate-panel"}

missing = sorted(js_ids - html_ids - dynamic)
print("html ids:", len(html_ids), "| js ids:", len(js_ids))
print("missing:", missing or "none")

unused = sorted(html_ids - js_ids - {"main-tabs"})
print("unused html ids:", unused or "none")
