"""Lớp trung gian mô tả bản vẽ (mm, trục Y hướng lên) để xuất ra SVG hoặc DXF."""
from __future__ import annotations

from dataclasses import dataclass, field

LAYERS: dict[str, dict] = {
    "frame": {"color": "#111827", "dxf": 7, "width": 5.0},
    "sash": {"color": "#1f2937", "dxf": 7, "width": 3.0},
    "glass": {"color": "#0284c7", "dxf": 4, "width": 0.8},
    "hidden": {"color": "#9ca3af", "dxf": 8, "width": 0.8},
    "dim": {"color": "#b45309", "dxf": 2, "width": 0.8},
    "text": {"color": "#111827", "dxf": 7, "width": 0.8},
    "table": {"color": "#111827", "dxf": 7, "width": 1.2},
    "title": {"color": "#111827", "dxf": 7, "width": 2.5},
    "note": {"color": "#4b5563", "dxf": 8, "width": 0.8},
    "arrow": {"color": "#b91c1c", "dxf": 1, "width": 1.0},
}


@dataclass
class Primitive:
    kind: str
    layer: str = "text"
    points: list[tuple[float, float]] = field(default_factory=list)
    text: str = ""
    height: float = 40.0
    align: str = "left"
    valign: str = "baseline"
    closed: bool = True
    fill: str | None = None


class Sheet:
    def __init__(self, width: float, height: float, title: str = ""):
        self.width = width
        self.height = height
        self.title = title
        self.primitives: list[Primitive] = []

    # ---- hình học cơ bản ------------------------------------------------ #
    def line(self, x1: float, y1: float, x2: float, y2: float, layer: str = "frame") -> None:
        self.primitives.append(Primitive("line", layer, [(x1, y1), (x2, y2)]))

    def rect(self, x: float, y: float, w: float, h: float, layer: str = "frame", fill: str | None = None) -> None:
        self.primitives.append(
            Primitive("rect", layer, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill)
        )

    def poly(
        self,
        points: list[tuple[float, float]] | list[list[float]],
        layer: str = "frame",
        closed: bool = True,
        fill: str | None = None,
    ) -> None:
        pts = [(float(p[0]), float(p[1])) for p in points]
        self.primitives.append(Primitive("poly", layer, pts, closed=closed, fill=fill))

    def text(
        self,
        x: float,
        y: float,
        value: str,
        height: float = 40.0,
        layer: str = "text",
        align: str = "left",
        valign: str = "baseline",
    ) -> None:
        self.primitives.append(
            Primitive("text", layer, [(x, y)], text=str(value), height=height, align=align, valign=valign)
        )

    # ---- kích thước ----------------------------------------------------- #
    def dim_h(
        self,
        x1: float,
        x2: float,
        y: float,
        offset: float = 120.0,
        value: str | None = None,
        height: float = 38.0,
    ) -> None:
        y_dim = y - offset
        tick = 22.0
        self.line(x1, y, x1, y_dim - 30, "dim")
        self.line(x2, y, x2, y_dim - 30, "dim")
        self.line(x1, y_dim, x2, y_dim, "dim")
        self.line(x1 - tick, y_dim - tick, x1 + tick, y_dim + tick, "dim")
        self.line(x2 - tick, y_dim - tick, x2 + tick, y_dim + tick, "dim")
        label = value if value is not None else f"{abs(x2 - x1):,.0f}".replace(",", ".")
        self.text((x1 + x2) / 2, y_dim + 14, label, height=height, layer="dim", align="center")

    def dim_v(
        self,
        x: float,
        y1: float,
        y2: float,
        offset: float = 120.0,
        value: str | None = None,
        height: float = 38.0,
    ) -> None:
        x_dim = x - offset
        tick = 22.0
        self.line(x, y1, x_dim - 30, y1, "dim")
        self.line(x, y2, x_dim - 30, y2, "dim")
        self.line(x_dim, y1, x_dim, y2, "dim")
        self.line(x_dim - tick, y1 - tick, x_dim + tick, y1 + tick, "dim")
        self.line(x_dim - tick, y2 - tick, x_dim + tick, y2 + tick, "dim")
        label = value if value is not None else f"{abs(y2 - y1):,.0f}".replace(",", ".")
        self.text(x_dim - 14, (y1 + y2) / 2, label, height=height, layer="dim", align="right", valign="middle")

    def arrow(self, x1: float, y1: float, x2: float, y2: float, layer: str = "arrow") -> None:
        """Mũi tên đơn giản (dùng cho ký hiệu hướng mở)."""
        self.line(x1, y1, x2, y2, layer)
        import math

        angle = math.atan2(y2 - y1, x2 - x1)
        size = 35.0
        for delta in (math.radians(155), math.radians(-155)):
            self.line(
                x2,
                y2,
                x2 + size * math.cos(angle + delta),
                y2 + size * math.sin(angle + delta),
                layer,
            )
