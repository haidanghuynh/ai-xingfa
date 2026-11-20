"""Script chạy BÊN TRONG FreeCAD (FreeCADCmd.exe). Chỉ dùng thư viện chuẩn + FreeCAD API.

Cách chạy:
    FreeCADCmd.exe freecad_build.py --plan build_plan.json --out out_dir
hoặc dùng biến môi trường XFCAD_PLAN / XFCAD_OUT.
"""
from __future__ import annotations

import json
import os
import sys

import FreeCAD as App  # type: ignore
import Part  # type: ignore


def _args():
    plan = os.environ.get("XFCAD_PLAN")
    out = os.environ.get("XFCAD_OUT")
    args = sys.argv[1:]
    if args and args[0].lower().endswith(".py"):
        args = args[1:]
    index = 0
    while index < len(args):
        if args[index] == "--plan" and index + 1 < len(args):
            plan = args[index + 1]
            index += 2
        elif args[index] == "--out" and index + 1 < len(args):
            out = args[index + 1]
            index += 2
        else:
            index += 1
    return plan, out


def _bar_solid(bar: dict) -> Part.Shape:
    points = [App.Vector(float(x), float(bar["y0"]), float(z)) for x, z in bar["polygon"]]
    if len(points) < 3:
        raise ValueError("polygon không hợp lệ")
    points.append(points[0])
    wire = Part.makePolygon(points)
    face = Part.Face(wire)
    depth = float(bar["y1"]) - float(bar["y0"])
    return face.extrude(App.Vector(0, depth, 0))


def build(plan_path: str, out_dir: str) -> dict:
    with open(plan_path, "r", encoding="utf-8") as handle:
        plan = json.load(handle)
    os.makedirs(out_dir, exist_ok=True)
    code = plan.get("project", {}).get("code", "project")
    doc = App.newDocument(f"XFCAD_{code}")

    report = {"schema": "xingfacad.freecad_report/1", "items": [], "errors": [], "warnings": []}
    all_objects = []
    total_density_volume = 0.0

    for item in plan.get("items", []):
        group = doc.addObject("App::Part", f"ITEM_{item['tag']}")
        item_objects = []
        volume = 0.0
        for index, bar in enumerate(item.get("bars", [])):
            try:
                solid = _bar_solid(bar)
            except Exception as exc:  # noqa: BLE001
                report["errors"].append(f"{item['tag']} bar {index} ({bar.get('profile_code')}): {exc}")
                continue
            obj = doc.addObject("Part::Feature", f"{item['tag']}_{bar.get('profile_code', 'P')}_{index}")
            obj.Shape = solid
            try:
                obj.Label = f"{bar.get('label') or bar.get('profile_code', '')} {index}"
            except Exception:
                pass
            group.addObject(obj)
            item_objects.append(obj)
            volume += solid.Volume

        for index, pane in enumerate(item.get("panes", [])):
            try:
                box = Part.makeBox(
                    float(pane["w"]),
                    float(pane["t"]),
                    float(pane["h"]),
                    App.Vector(float(pane["x"]), float(pane["y"]), float(pane["z"])),
                )
            except Exception as exc:  # noqa: BLE001
                report["errors"].append(f"{item['tag']} glass {index}: {exc}")
                continue
            obj = doc.addObject("Part::Feature", f"{item['tag']}_GLASS_{index}")
            obj.Shape = box
            group.addObject(obj)
            item_objects.append(obj)
            volume += box.Volume

        for index, hardware in enumerate(item.get("hardware", [])):
            try:
                solid = Part.makeBox(
                    float(hardware["w"]),
                    float(hardware["d"]),
                    float(hardware["h"]),
                    App.Vector(float(hardware["x"]), float(hardware["y"]), float(hardware["z"])),
                )
            except Exception as exc:  # noqa: BLE001
                report["errors"].append(f"{item['tag']} hardware {index}: {exc}")
                continue
            kind = str(hardware.get("kind", "hw"))
            obj = doc.addObject("Part::Feature", f"{item['tag']}_HW_{kind.upper()}_{index}")
            obj.Shape = solid
            try:
                obj.Label = f"{hardware.get('label') or kind} {index}"
            except Exception:
                pass
            group.addObject(obj)
            item_objects.append(obj)
            volume += solid.Volume

        all_objects.extend(item_objects)
        expected_kg = float(item.get("aluminum_kg_expected", 0) or 0)
        envelope_kg = volume / 1_000_000_000 * 2700.0
        report["items"].append(
            {
                "tag": item["tag"],
                "objects": len(item_objects),
                "bars": len(item.get("bars", [])),
                "panes": len(item.get("panes", [])),
                "hardware": len(item.get("hardware", [])),
                "volume_mm3": round(volume, 1),
                "envelope_kg": round(envelope_kg, 2),
                "expected_kg": expected_kg,
            }
        )
        total_density_volume += volume
        if expected_kg > 0 and envelope_kg < expected_kg * 0.9:
            report["warnings"].append(
                f"{item['tag']}: thể tích mô hình ({envelope_kg:.1f} kg) nhỏ hơn khối lượng BOM "
                f"({expected_kg:.1f} kg) - kiểm tra lại hình học"
            )

    doc.recompute()

    fcstd_path = os.path.join(out_dir, f"{code}.FCStd")
    doc.saveAs(fcstd_path)
    report["fcstd"] = fcstd_path

    if all_objects:
        try:
            import Import  # type: ignore

            step_path = os.path.join(out_dir, f"{code}.step")
            Import.export(all_objects, step_path)
            report["step"] = step_path
        except Exception as exc:  # noqa: BLE001
            report["warnings"].append(f"Không xuất được STEP: {exc}")
        try:
            import Mesh  # type: ignore

            stl_path = os.path.join(out_dir, f"{code}.stl")
            Mesh.export(all_objects, stl_path)
            report["stl"] = stl_path
        except Exception as exc:  # noqa: BLE001
            report["warnings"].append(f"Không xuất được STL: {exc}")

    report["total_volume_mm3"] = round(total_density_volume, 1)
    report["objects"] = len(all_objects)
    report_path = os.path.join(out_dir, "freecad_report.json")
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    report["report"] = report_path
    doc.save()
    return report


def main() -> int:
    plan_path, out_dir = _args()
    if not plan_path or not out_dir:
        print("Thieu tham so --plan / --out")
        return 2
    try:
        report = build(plan_path, out_dir)
    except Exception as exc:  # noqa: BLE001
        print(f"LOI: {exc}")
        import traceback

        traceback.print_exc()
        return 1
    print(f"OK: {report.get('objects', 0)} objects, FCStd={report.get('fcstd')}")
    for warning in report.get("warnings", []):
        print(f"CANH BAO: {warning}")
    for error in report.get("errors", []):
        print(f"LOI: {error}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
