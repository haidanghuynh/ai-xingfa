"""CLI: xfcad serve | build | validate | systems | demo | status."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import APP_NAME, __version__, catalog, freecad, paths, pipeline
from .models import ProjectSpec


def _print(message: str = "") -> None:
    print(message)


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    _print(f"{APP_NAME} {__version__} - GUI: http://{args.host}:{args.port}")
    uvicorn.run("xingfacad.api:app", host=args.host, port=args.port, reload=args.reload, log_level="info")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec)
    if not spec_path.exists():
        _print(f"Không tìm thấy file: {spec_path}")
        return 2
    project = ProjectSpec.model_validate(json.loads(spec_path.read_text(encoding="utf-8")))
    outcome = pipeline.build_project(
        project,
        with_3d=not args.no_3d,
        with_drawings=not args.no_drawings,
        pricing_mode=args.pricing_mode,
        price_level=args.price_level,
    )
    _print(f"== {outcome.project.code} - {outcome.project.name} ==")
    for key in ("area_m2", "alum_kg", "glass_m2", "cost_total", "price", "vat", "price_with_vat"):
        _print(f"{key:16}: {outcome.summary.get(key)}")
    _print(f"Thư mục xuất      : {outcome.out_dir}")
    _print(f"Số file           : {len(outcome.artifacts)}")
    issues = outcome.issues
    if issues:
        _print(f"\nCảnh báo ({len(issues)}):")
        for issue in issues[:20]:
            _print(f"  [{issue.level}] {issue.message}")
    freecad_info = outcome.freecad or {}
    _print(
        f"\nFreeCAD: available={freecad_info.get('available')} ok={freecad_info.get('ok')} "
        f"{freecad_info.get('message', '')}"
    )
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec)
    project = ProjectSpec.model_validate(json.loads(spec_path.read_text(encoding="utf-8")))
    try:
        outcome = pipeline.build_project(project, with_3d=False, with_drawings=False)
    except pipeline.BuildError as exc:
        for issue in exc.issues:
            _print(f"[{issue.level}] {issue.tag}: {issue.message}")
        return 1
    errors = [issue for issue in outcome.issues if issue.level == "error"]
    _print(f"Hợp lệ: {'KHÔNG' if errors else 'CÓ'} | cảnh báo: {len(outcome.issues) - len(errors)}")
    for issue in outcome.issues:
        _print(f"[{issue.level}] {issue.tag}: {issue.message}")
    return 0 if not errors else 1


def cmd_systems(args: argparse.Namespace) -> int:
    systems = catalog.list_systems()
    if not systems:
        _print("Chưa có hệ nhôm nào trong config/systems")
        return 0
    _print(f"{'Mã':8} {'Tên':34} {'Kiểu':8} {'Ghép':8} {'Profile':8} Verified")
    for system in systems:
        _print(
            f"{system.code:8} {system.name[:34]:34} {system.kind:8} {system.joint:8} "
            f"{len(system.profiles):<8} {system.verified}"
        )
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    target = Path(args.out or (paths.specs_dir() / "demo_nha_a.json"))
    source = paths.specs_dir() / "demo_nha_a.json"
    if not source.exists():
        _print("Không có file demo")
        return 2
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    _print(f"Đã tạo: {target}")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    info = freecad.status()
    _print(f"{APP_NAME} {__version__}")
    _print(f"Thư mục dự án : {paths.root()}")
    _print(f"FreeCAD       : {info['path'] or 'chưa cài'}")
    _print(f"Gợi ý         : {info['hint']}")
    _print(f"Số hệ nhôm    : {len(catalog.list_systems())}")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = argparse.ArgumentParser(prog="xfcad", description=f"{APP_NAME} - cửa nhôm Xingfa tự động")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Chạy GUI web")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8010)
    serve.add_argument("--reload", action="store_true")
    serve.set_defaults(func=cmd_serve)

    build = sub.add_parser("build", help="Build dự án từ file JSON")
    build.add_argument("--spec", required=True)
    build.add_argument("--no-3d", action="store_true", help="Không gọi FreeCAD")
    build.add_argument("--no-drawings", action="store_true", help="Không xuất DXF/SVG")
    build.add_argument("--pricing-mode", choices=["bom", "book"], default="bom", help="Cách tính giá bán")
    build.add_argument("--price-level", default="le", help="Mã cấp giá khi dùng bảng giá (le/dl1/ct)")
    build.set_defaults(func=cmd_build)

    validate = sub.add_parser("validate", help="Kiểm tra file spec")
    validate.add_argument("--spec", required=True)
    validate.set_defaults(func=cmd_validate)

    systems = sub.add_parser("systems", help="Liệt kê hệ nhôm")
    systems.set_defaults(func=cmd_systems)

    demo = sub.add_parser("demo", help="Tạo file spec demo")
    demo.add_argument("--out")
    demo.set_defaults(func=cmd_demo)

    status = sub.add_parser("status", help="Trạng thái môi trường")
    status.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
