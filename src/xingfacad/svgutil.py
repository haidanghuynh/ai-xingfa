"""Sinh SVG thuần Python (không phụ thuộc thư viện ngoài)."""
from __future__ import annotations

from xml.sax.saxutils import escape


def fmt(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


class Svg:
    """Canvas SVG đơn giản. flip_y=True dùng cho bản vẽ kỹ thuật (trục Y hướng lên)."""

    def __init__(
        self,
        width: float,
        height: float,
        flip_y: bool = False,
        background: str = "#ffffff",
        display: tuple[float, float] | None = None,
    ):
        self.width = width
        self.height = height
        self.flip_y = flip_y
        self.background = background
        self.display = display
        self.items: list[str] = []

    def _y(self, y: float) -> float:
        return self.height - y if self.flip_y else y

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        stroke: str = "#111111",
        width: float = 1.0,
        dash: str | None = None,
        opacity: float = 1.0,
    ) -> None:
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        self.items.append(
            f'<line x1="{fmt(x1)}" y1="{fmt(self._y(y1))}" x2="{fmt(x2)}" y2="{fmt(self._y(y2))}"'
            f' stroke="{stroke}" stroke-width="{fmt(width)}"{dash_attr} stroke-opacity="{fmt(opacity)}"/>'
        )

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        stroke: str = "none",
        fill: str = "none",
        width: float = 1.0,
        dash: str | None = None,
        opacity: float = 1.0,
        fill_opacity: float = 1.0,
    ) -> None:
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        top = self._y(y + h)
        self.items.append(
            f'<rect x="{fmt(x)}" y="{fmt(top)}" width="{fmt(w)}" height="{fmt(h)}"'
            f' stroke="{stroke}" fill="{fill}" stroke-width="{fmt(width)}"{dash_attr}'
            f' fill-opacity="{fmt(fill_opacity)}" stroke-opacity="{fmt(opacity)}"/>'
        )

    def poly(
        self,
        points: list[tuple[float, float]] | list[list[float]],
        stroke: str = "none",
        fill: str = "#ffffff",
        width: float = 1.0,
        opacity: float = 1.0,
        fill_opacity: float = 1.0,
        close: bool = True,
    ) -> None:
        coords = " ".join(f"{fmt(p[0])},{fmt(self._y(p[1]))}" for p in points)
        tag = "polygon" if close else "polyline"
        self.items.append(
            f'<{tag} points="{coords}" stroke="{stroke}" fill="{fill}" stroke-width="{fmt(width)}"'
            f' fill-opacity="{fmt(fill_opacity)}" stroke-opacity="{fmt(opacity)}" stroke-linejoin="round"/>'
        )

    def text(
        self,
        x: float,
        y: float,
        value: str,
        size: float = 12,
        anchor: str = "start",
        fill: str = "#111111",
        weight: str = "normal",
        rotate: float | None = None,
    ) -> None:
        transform = f' transform="rotate({fmt(rotate)} {fmt(x)} {fmt(self._y(y))})"' if rotate else ""
        self.items.append(
            f'<text x="{fmt(x)}" y="{fmt(self._y(y))}" font-family="Arial, Helvetica, sans-serif"'
            f' font-size="{fmt(size)}" font-weight="{weight}" text-anchor="{anchor}"'
            f' fill="{fill}"{transform}>{escape(value)}</text>'
        )

    def render(self) -> str:
        body = "\n  ".join(self.items)
        out_w, out_h = self.display or (self.width, self.height)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{fmt(out_w)}" height="{fmt(out_h)}"'
            f' viewBox="0 0 {fmt(self.width)} {fmt(self.height)}">\n'
            f'  <rect width="100%" height="100%" fill="{self.background}"/>\n'
            f"  {body}\n</svg>\n"
        )

    def save(self, path) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self.render())
