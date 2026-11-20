"""Dựng ảnh phối cảnh 3D (axonometric) từ Bar3D/Pane3D -> SVG và xuất OBJ."""
from __future__ import annotations

import math
from pathlib import Path

from .models import Bar3D, ItemResult, Pane3D
from .svgutil import Svg

GROUP_COLORS: dict[str, str] = {
    "frame": "#cfd6dd",
    "sash": "#e6ebf0",
    "mullion": "#c3ccd6",
    "transom": "#cad3dc",
    "track_top": "#b8c2cc",
    "track_bottom": "#aeb9c4",
    "bead": "#dde3e9",
}
HARDWARE_COLORS: dict[str, str] = {
    "hinge": "#94a3b8",
    "lock": "#3f4a5a",
    "handle": "#1f2937",
    "wheel": "#111827",
}
GLASS_COLOR = "#8fc6e8"
DEFAULT_COLOR = "#d5dbe1"

Point = tuple[float, float, float]
Face = list[Point]


def _faces_for_bar(bar: Bar3D) -> list[Face]:
    pts = [(float(p[0]), float(p[1])) for p in bar.polygon]
    if len(pts) < 3:
        return []
    faces: list[Face] = [[(x, bar.y0, z) for x, z in pts], [(x, bar.y1, z) for x, z in reversed(pts)]]
    for index in range(len(pts)):
        x1, z1 = pts[index]
        x2, z2 = pts[(index + 1) % len(pts)]
        faces.append([(x1, bar.y0, z1), (x2, bar.y0, z2), (x2, bar.y1, z2), (x1, bar.y1, z1)])
    return faces


def _faces_for_pane(pane: Pane3D) -> list[Face]:
    return _box_faces(pane.x, pane.y, pane.z, pane.w, pane.t, pane.h)


def _box_faces(x0: float, y0: float, z0: float, w: float, t: float, h: float) -> list[Face]:
    x1, y1, z1 = x0 + w, y0 + t, z0 + h
    corners = [
        (x0, y0, z0),
        (x1, y0, z0),
        (x1, y0, z1),
        (x0, y0, z1),
        (x0, y1, z0),
        (x1, y1, z0),
        (x1, y1, z1),
        (x0, y1, z1),
    ]
    return [
        [corners[0], corners[1], corners[2], corners[3]],
        [corners[7], corners[6], corners[5], corners[4]],
        [corners[0], corners[4], corners[5], corners[1]],
        [corners[1], corners[5], corners[6], corners[2]],
        [corners[2], corners[6], corners[7], corners[3]],
        [corners[3], corners[7], corners[4], corners[0]],
    ]


def _faces_for_hardware(item) -> list[Face]:
    return _box_faces(item.x, item.y, item.z, item.w, item.d, item.h)


def _normal(face: Face) -> Point:
    ax, ay, az = face[1][0] - face[0][0], face[1][1] - face[0][1], face[1][2] - face[0][2]
    bx, by, bz = face[2][0] - face[0][0], face[2][1] - face[0][1], face[2][2] - face[0][2]
    nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return (nx / length, ny / length, nz / length)


def _shade(color: str, factor: float) -> str:
    red = int(color[1:3], 16)
    green = int(color[3:5], 16)
    blue = int(color[5:7], 16)
    values = [min(255, max(0, int(channel * factor))) for channel in (red, green, blue)]
    return "#" + "".join(f"{value:02x}" for value in values)


def _collect_faces(result: ItemResult) -> list[tuple[Face, str, float]]:
    faces: list[tuple[Face, str, float]] = []
    for bar in result.bars3d:
        color = GROUP_COLORS.get(bar.group, DEFAULT_COLOR)
        for face in _faces_for_bar(bar):
            faces.append((face, color, 1.0))
    for pane in result.panes3d:
        for face in _faces_for_pane(pane):
            faces.append((face, GLASS_COLOR, 0.42))
    for item in result.hardware3d:
        for face in _faces_for_hardware(item):
            faces.append((face, HARDWARE_COLORS.get(item.kind, "#475569"), 1.0))
    return faces


def shader_material(group: str) -> str:
    return f"profile_{group}"


def render_preview_svg(
    result: ItemResult,
    width: int = 760,
    height: int = 620,
    azimuth: float = 32.0,
    elevation: float = 20.0,
) -> str:
    azimuth_rad = math.radians(azimuth)
    elevation_rad = math.radians(elevation)
    ca, sa = math.cos(azimuth_rad), math.sin(azimuth_rad)
    ce, se = math.cos(elevation_rad), math.sin(elevation_rad)

    def project(point: Point) -> tuple[float, float, float]:
        x, y, z = point
        screen_x = x * ca - y * sa
        screen_y = -((x * sa + y * ca) * se + z * ce)
        depth = -(x * sa * ce) - (y * ca * ce) + z * se
        return screen_x, screen_y, depth

    items: list[tuple[list[tuple[float, float]], str, float, float]] = []
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    for face, color, alpha in _collect_faces(result):
        projected = [project(point) for point in face]
        screen_points = [(px, py) for px, py, _depth in projected]
        depth = sum(value for _px, _py, value in projected) / len(projected)
        normal = _normal(face)
        light = (-0.35, -0.75, 0.55)
        dot = abs(normal[0] * light[0] + normal[1] * light[1] + normal[2] * light[2])
        factor = 0.62 + 0.38 * min(1.0, dot)
        items.append((screen_points, _shade(color, factor), alpha, depth))
        for px, py in screen_points:
            min_x, max_x = min(min_x, px), max(max_x, px)
            min_y, max_y = min(min_y, py), max(max_y, py)

    canvas = Svg(width, height, flip_y=False, background="#f7f9fb")
    if not items:
        canvas.text(width / 2, height / 2, "Không có dữ liệu hình học", size=16, anchor="middle")
        return canvas.render()

    pad_left, pad_top, pad_right, pad_bottom = 40, 60, 40, 40
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    scale = min((width - pad_left - pad_right) / span_x, (height - pad_top - pad_bottom) / span_y)
    offset_x = pad_left + ((width - pad_left - pad_right) - span_x * scale) / 2 - min_x * scale
    offset_y = pad_top + ((height - pad_top - pad_bottom) - span_y * scale) / 2 - min_y * scale

    for screen_points, color, alpha, _depth in sorted(items, key=lambda item: item[3]):
        scaled = [(px * scale + offset_x, py * scale + offset_y) for px, py in screen_points]
        canvas.poly(scaled, stroke="#5b6570", fill=color, width=0.7, fill_opacity=alpha)

    canvas.text(16, 24, f"{result.item.tag} - {result.width_mm:.0f} x {result.height_mm:.0f} mm", size=15, weight="bold")
    canvas.text(
        16,
        42,
        f"{result.system_code} | nhom {result.alum_kg:.1f} kg | kinh {result.glass_m2:.2f} m2 | {result.leaves} canh",
        size=11,
        fill="#5b6570",
    )
    return canvas.render()


def write_obj(result: ItemResult, path: str | Path) -> Path:
    """Xuất OBJ (kèm MTL) để mở bằng mọi phần mềm 3D."""
    path = Path(path)
    mtl_path = path.with_suffix(".mtl")
    lines: list[str] = ["# XingfaCAD OBJ export", f"mtllib {mtl_path.name}"]
    vertices: list[Point] = []
    faces_by_material: dict[str, list[tuple[int, ...]]] = {}

    def add_face(face: Face, material: str) -> None:
        ids = []
        for point in face:
            vertices.append(point)
            ids.append(len(vertices))
        faces_by_material.setdefault(material, []).append(tuple(ids))

    for bar in result.bars3d:
        material = shader_material(bar.group)
        for face in _faces_for_bar(bar):
            add_face(face, material)
    for pane in result.panes3d:
        for face in _faces_for_pane(pane):
            add_face(face, "glass")
    for hardware in result.hardware3d:
        for face in _faces_for_hardware(hardware):
            add_face(face, f"hardware_{hardware.kind}")

    for point in vertices:
        lines.append(f"v {point[0]:.2f} {point[1]:.2f} {point[2]:.2f}")
    for material, faces in faces_by_material.items():
        lines.append(f"g {material}")
        lines.append(f"usemtl {material}")
        for face in faces:
            lines.append("f " + " ".join(str(index) for index in face))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    mtl_lines = ["# XingfaCAD materials"]
    for group, color in GROUP_COLORS.items():
        red = int(color[1:3], 16) / 255
        green = int(color[3:5], 16) / 255
        blue = int(color[5:7], 16) / 255
        mtl_lines += [
            f"newmtl {shader_material(group)}",
            f"Kd {red:.3f} {green:.3f} {blue:.3f}",
            "Ka 0.2 0.2 0.2",
            "",
        ]
    mtl_lines += ["newmtl glass", "Kd 0.561 0.776 0.910", "d 0.45", ""]
    for kind, color in HARDWARE_COLORS.items():
        red = int(color[1:3], 16) / 255
        green = int(color[3:5], 16) / 255
        blue = int(color[5:7], 16) / 255
        mtl_lines += [f"newmtl hardware_{kind}", f"Kd {red:.3f} {green:.3f} {blue:.3f}", "Ka 0.2 0.2 0.2", ""]
    mtl_path.write_text("\n".join(mtl_lines), encoding="utf-8")
    return path
