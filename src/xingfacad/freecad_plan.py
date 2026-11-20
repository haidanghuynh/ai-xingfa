"""Sinh build_plan.json (hợp đồng giữa core Python và script chạy trong FreeCAD)."""
from __future__ import annotations

from .models import ItemResult, SystemDef
from .preview3d import GROUP_COLORS, DEFAULT_COLOR


def build_plan(results: list[ItemResult], systems: dict[str, SystemDef], project_code: str) -> dict:
    items = []
    for result in results:
        system = systems.get(result.system_code)
        bars = []
        for bar in result.bars3d:
            bars.append(
                {
                    "group": bar.group,
                    "profile_code": bar.profile_code,
                    "polygon": [[round(float(p[0]), 3), round(float(p[1]), 3)] for p in bar.polygon],
                    "y0": round(bar.y0, 3),
                    "y1": round(bar.y1, 3),
                    "label": bar.label,
                    "color": GROUP_COLORS.get(bar.group, DEFAULT_COLOR),
                }
            )
        panes = [
            {
                "x": round(pane.x, 3),
                "y": round(pane.y, 3),
                "z": round(pane.z, 3),
                "w": round(pane.w, 3),
                "h": round(pane.h, 3),
                "t": round(pane.t, 3),
                "label": pane.label,
            }
            for pane in result.panes3d
        ]
        hardware = [
            {
                "kind": item.kind,
                "x": round(item.x, 3),
                "y": round(item.y, 3),
                "z": round(item.z, 3),
                "w": round(item.w, 3),
                "h": round(item.h, 3),
                "d": round(item.d, 3),
                "label": item.label,
            }
            for item in result.hardware3d
        ]
        items.append(
            {
                "tag": result.item.tag,
                "system": result.system_code,
                "system_name": result.system_name,
                "type": result.item.type,
                "width_mm": result.width_mm,
                "height_mm": result.height_mm,
                "sill_mm": result.item.sill_mm,
                "joint": result.joint,
                "bars": bars,
                "panes": panes,
                "hardware": hardware,
                "aluminum_kg_expected": round(result.alum_kg, 3),
                "glass_m2": round(result.glass_m2, 3),
                "depth_mm": (
                    system.profiles["frame"].depth_mm if system and "frame" in system.profiles else 0
                ),
                "frame_width_mm": (
                    system.profiles["frame"].width_mm if system and "frame" in system.profiles else 0
                ),
            }
        )
    return {
        "schema": "xingfacad.build_plan/1",
        "units": "mm",
        "project": {"code": project_code},
        "items": items,
    }
