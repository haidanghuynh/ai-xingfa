"""Render thử PNG để kiểm tra trực quan (dev only, dùng PIL)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import math  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from xingfacad import catalog  # noqa: E402
from xingfacad.drawing import build_sheet  # noqa: E402
from xingfacad.layout import build_item  # noqa: E402
from xingfacad.models import ProjectSpec  # noqa: E402
from xingfacad.preview3d import _collect_faces, _normal, _shade  # noqa: E402
from xingfacad.sheet import LAYERS  # noqa: E402

OUT = ROOT / "out" / "_preview"
OUT.mkdir(parents=True, exist_ok=True)
spec = ProjectSpec.model_validate(json.loads((ROOT / "data/specs/demo_nha_a.json").read_text(encoding="utf-8")))
item = spec.items[0]
system = catalog.load_system(item.system)
result = build_item(item, system, spec.defaults.glass)


def font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("arial.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def render_3d(path: Path, width: int = 900, height: int = 720) -> None:
    az, el = math.radians(32), math.radians(20)
    ca, sa, ce, se = math.cos(az), math.sin(az), math.cos(el), math.sin(el)
    items = []
    min_x = min_y = 1e18
    max_x = max_y = -1e18
    for face, color, alpha in _collect_faces(result):
        pts = []
        depth = 0.0
        for x, y, z in face:
            px = x * ca - y * sa
            py = -((x * sa + y * ca) * se + z * ce)
            depth += -(x * sa * ce) - (y * ca * ce) + z * se
            pts.append((px, py))
            min_x, max_x = min(min_x, px), max(max_x, px)
            min_y, max_y = min(min_y, py), max(max_y, py)
        normal = _normal(face)
        dot = abs(normal[0] * -0.35 + normal[1] * -0.75 + normal[2] * 0.55)
        items.append((pts, _shade(color, 0.62 + 0.38 * min(1, dot)), alpha, depth / len(face)))

    span_x, span_y = max(max_x - min_x, 1), max(max_y - min_y, 1)
    scale = min((width - 80) / span_x, (height - 100) / span_y)
    ox = 40 + ((width - 80) - span_x * scale) / 2 - min_x * scale
    oy = 70 + ((height - 100) - span_y * scale) / 2 - min_y * scale
    image = Image.new("RGB", (width, height), "#f7f9fb")
    draw = ImageDraw.Draw(image)
    for pts, color, alpha, _depth in sorted(items, key=lambda i: i[3]):
        screen = [(p[0] * scale + ox, p[1] * scale + oy) for p in pts]
        draw.polygon(screen, fill=color, outline="#5b6570")
    draw.text((16, 12), f"{item.tag} 3D preview", fill="#111", font=font(18))
    image.save(path)


def render_sheet(path: Path, width: int = 1700) -> None:
    sheet = build_sheet(result, spec.project, catalog.load_pricing(), system)
    k = width / sheet.width
    height = int(sheet.height * k)
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    for prim in sheet.primitives:
        info = LAYERS.get(prim.layer, LAYERS["text"])
        color = info["color"]
        w = max(1, int(info["width"] * k))
        if prim.kind == "line":
            (x1, y1), (x2, y2) = prim.points
            draw.line((x1 * k, height - y1 * k, x2 * k, height - y2 * k), fill=color, width=w)
        elif prim.kind in ("rect", "poly"):
            pts = [(p[0] * k, height - p[1] * k) for p in prim.points]
            if prim.kind == "rect":
                (x, y), (x2, y2) = prim.points[0], prim.points[2]
                pts = [(x * k, height - y * k), (x2 * k, height - y * k), (x2 * k, height - y2 * k), (x * k, height - y2 * k)]
            fill = prim.fill
            draw.polygon(pts, fill=fill, outline=color)
        elif prim.kind == "text":
            x, y = prim.points[0]
            size = max(6, int(prim.height * k * 0.9))
            text = prim.text
            anchor = {"left": "ls", "center": "ms", "right": "rs"}.get(prim.align, "ls")
            if prim.valign == "middle":
                anchor = {"left": "lm", "center": "mm", "right": "rm"}.get(prim.align, "lm")
            draw.text((x * k, height - y * k), text, fill=color, font=font(size), anchor=anchor)
    image.save(path)


render_3d(OUT / "preview3d_C1.png")
sliding_item = next(item for item in spec.items if item.type == "sliding")
sliding_result = build_item(sliding_item, catalog.load_system(sliding_item.system), spec.defaults.glass)
result_backup = result
result = sliding_result
render_3d(OUT / "preview3d_C3.png")
result = result_backup
render_sheet(OUT / "sheet_C1.png")
print("saved:", sorted(p.name for p in OUT.iterdir()))
