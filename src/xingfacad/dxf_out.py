"""Xuất Sheet ra DXF bằng ezdxf (đơn vị mm, mở được trong AutoCAD/Zalo CAD)."""
from __future__ import annotations

from pathlib import Path

from .sheet import LAYERS, Sheet

FILL_ACI = {"#bfe3f6": 140, "#e5e7eb": 9, "#f3f4f6": 254, "#ffffff": 7}
ALIGN = {
    ("left", "baseline"): "BOTTOM_LEFT",
    ("center", "baseline"): "BOTTOM_CENTER",
    ("right", "baseline"): "BOTTOM_RIGHT",
    ("left", "middle"): "MIDDLE_LEFT",
    ("center", "middle"): "MIDDLE_CENTER",
    ("right", "middle"): "MIDDLE_RIGHT",
}


def write_dxf(sheet: Sheet, path: str | Path) -> Path:
    import ezdxf
    from ezdxf.enums import TextEntityAlignment

    path = Path(path)
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LUNITS"] = 2
    try:
        doc.styles.add("VI", font="arial.ttf")
    except Exception:
        pass
    for name, info in LAYERS.items():
        if name not in doc.layers:
            doc.layers.add(name, color=info["dxf"])
    msp = doc.modelspace()

    def add_hatch(points, fill: str | None, layer: str) -> None:
        if not fill:
            return
        aci = FILL_ACI.get(fill.lower(), 8)
        hatch = msp.add_hatch(color=aci, dxfattribs={"layer": layer})
        hatch.paths.add_polyline_path([(float(p[0]), float(p[1])) for p in points], is_closed=True)

    for prim in sheet.primitives:
        layer = prim.layer if prim.layer in LAYERS else "text"
        if prim.kind == "line":
            msp.add_line((prim.points[0][0], prim.points[0][1]), (prim.points[1][0], prim.points[1][1]), dxfattribs={"layer": layer})
        elif prim.kind == "rect":
            (x, y), (x2, y2) = prim.points[0], prim.points[2]
            points = [(x, y), (x2, y), (x2, y2), (x, y2)]
            msp.add_lwpolyline(points, close=True, dxfattribs={"layer": layer})
            add_hatch(points, prim.fill, layer)
        elif prim.kind == "poly":
            msp.add_lwpolyline(
                [(float(p[0]), float(p[1])) for p in prim.points],
                close=prim.closed,
                dxfattribs={"layer": layer},
            )
            add_hatch(prim.points, prim.fill, layer)
        elif prim.kind == "text":
            x, y = prim.points[0]
            text = msp.add_text(
                prim.text,
                height=prim.height,
                dxfattribs={"layer": layer, "style": "VI"},
            )
            align_name = ALIGN.get((prim.align, prim.valign), "BOTTOM_LEFT")
            text.set_placement((x, y), align=getattr(TextEntityAlignment, align_name))

    doc.saveas(path)
    return path
