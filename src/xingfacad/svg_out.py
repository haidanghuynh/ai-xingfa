"""Xuất Sheet ra SVG (bản vẽ 2D)."""
from __future__ import annotations

from pathlib import Path

from .sheet import LAYERS, Sheet
from .svgutil import Svg

ANCHOR = {"left": "start", "center": "middle", "right": "end"}


def sheet_to_svg(sheet: Sheet, display_scale: float = 0.28) -> str:
    canvas = Svg(
        sheet.width,
        sheet.height,
        flip_y=True,
        background="#ffffff",
        display=(sheet.width * display_scale, sheet.height * display_scale),
    )
    canvas.rect(20, 20, sheet.width - 40, sheet.height - 40, stroke="#94a3b8", width=8)
    for prim in sheet.primitives:
        info = LAYERS.get(prim.layer, LAYERS["text"])
        color = info["color"]
        stroke_w = info["width"]
        if prim.kind == "line":
            canvas.line(prim.points[0][0], prim.points[0][1], prim.points[1][0], prim.points[1][1], stroke=color, width=stroke_w)
        elif prim.kind == "rect":
            (x, y), (x2, y2) = prim.points[0], prim.points[2]
            canvas.rect(x, y, x2 - x, y2 - y, stroke=color, fill=prim.fill or "none", width=stroke_w)
        elif prim.kind == "poly":
            canvas.poly(prim.points, stroke=color, fill=prim.fill or "none", width=stroke_w, close=prim.closed)
        elif prim.kind == "text":
            x, y = prim.points[0]
            if prim.valign == "middle":
                y += prim.height * 0.34
            canvas.text(
                x,
                y,
                prim.text,
                size=prim.height,
                anchor=ANCHOR.get(prim.align, "start"),
                fill=color,
            )
    return canvas.render()


def write_svg(sheet: Sheet, path: str | Path, display_scale: float = 0.28) -> Path:
    path = Path(path)
    path.write_text(sheet_to_svg(sheet, display_scale), encoding="utf-8")
    return path
