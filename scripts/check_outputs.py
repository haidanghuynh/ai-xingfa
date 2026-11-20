"""Kiểm tra file sinh ra: DXF, SVG, OBJ, XLSX (dev only)."""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from openpyxl import load_workbook  # noqa: E402
import ezdxf  # noqa: E402

OUT = ROOT / "out" / "DEMO-001"
print("files:", sorted(p.name for p in OUT.iterdir()))

# --- XLSX ---
xlsx = next(OUT.glob("bao_gia_*.xlsx"))
wb = load_workbook(xlsx)
print("\nXLSX sheets:", wb.sheetnames)
print("defined names:", sorted(wb.defined_names.keys()))
ws = wb["01_BaoGia"]
for row in (12, 13, 18):
    print("row", row, [ws.cell(row=row, column=c).value for c in (1, 2, 5, 9, 10, 11, 19, 21, 22)])
print("Tổng hợp price formula:", wb["05_TongHop"]["B14"].value)

# --- DXF ---
dxf = OUT / "C1.dxf"
doc = ezdxf.readfile(dxf)
msp = doc.modelspace()
from collections import Counter

counts = Counter(entity.dxftype() for entity in msp)
print("\nDXF:", dxf.name, "entities:", dict(counts), "layers:", [layer.dxf.name for layer in doc.layers])
texts = [e.dxf.text for e in msp if e.dxftype() == "TEXT"][:8]
print("texts:", texts)

# --- SVG ---
for svg_file in sorted(OUT.glob("*.svg"))[:3]:
    tree = ET.parse(svg_file)
    root = tree.getroot()
    tags = Counter(child.tag.split("}")[-1] for child in root)
    print(f"SVG {svg_file.name}: {dict(tags)}")

# --- OBJ ---
obj = OUT / "C1.obj"
lines = obj.read_text(encoding="utf-8").splitlines()
print("OBJ:", obj.name, "v=", sum(1 for l in lines if l.startswith("v ")), "f=", sum(1 for l in lines if l.startswith("f ")))

# --- cut plan ---
plan = json.loads((OUT / "build_plan.json").read_text(encoding="utf-8"))
print("build_plan items:", len(plan["items"]), "bars:", sum(len(i["bars"]) for i in plan["items"]))
print("first bar:", json.dumps(plan["items"][0]["bars"][0], ensure_ascii=False)[:200])
