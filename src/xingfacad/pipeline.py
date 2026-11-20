"""Pipeline: dự án -> bóc tách -> DXF/SVG/OBJ -> Excel -> FreeCAD."""
from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path

from pydantic import BaseModel, Field

from . import catalog, freecad, paths
from .costing import build_costing_workbook
from .drawing import build_sheet
from .dxf_out import write_dxf
from .freecad_plan import build_plan
from .layout import build_item
from .models import ItemResult, ProjectInfo, ProjectSpec, SystemDef
from .optimizer import BarGroup, optimize, pieces_from_results
from .pdf_quote import build_quote_pdf
from .pricing import ProjectCost, compute_project_cost
from .preview3d import render_preview_svg, write_obj
from .quote import build_quote
from .svg_out import write_svg
from .validate import Issue, has_errors, validate_project


class BuildError(Exception):
    def __init__(self, issues: list[Issue]):
        self.issues = issues
        message = "; ".join(issue.message for issue in issues if issue.level == "error")
        super().__init__(message or "Dữ liệu không hợp lệ")


class Artifact(BaseModel):
    name: str
    kind: str
    tag: str = ""
    size: int = 0
    url: str = ""


class BuildOutcome(BaseModel):
    project: ProjectInfo
    items: list[dict] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    cut_plan: list[dict] = Field(default_factory=list)
    freecad: dict = Field(default_factory=dict)
    results: list[ItemResult] = Field(default_factory=list, exclude=True)
    cost: ProjectCost | None = Field(default=None, exclude=True)
    out_dir: str = ""


def _resolve_systems(project: ProjectSpec) -> dict[str, SystemDef]:
    codes = {(item.system or project.defaults.system or "").upper() for item in project.items}
    systems: dict[str, SystemDef] = {}
    for code in codes:
        if not code:
            continue
        try:
            systems[code] = catalog.load_system(code)
        except KeyError as exc:
            raise BuildError([Issue(level="error", code="system.missing", message=str(exc))]) from exc
    return systems


def _write_cutlist_csv(results: list[ItemResult], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(
            ["Mã cửa", "Loại cửa", "Hệ", "Vị trí", "Mã thanh", "Tên profile", "Dài (mm)", "SL",
             "Tổng dài (mm)", "kg/m", "Tổng kg", "Góc A", "Góc B", "Ghi chú"]
        )
        for result in results:
            for piece in result.pieces:
                writer.writerow(
                    [
                        result.item.tag,
                        result.item.type_label,
                        result.system_code,
                        piece.note,
                        piece.profile_code,
                        piece.profile_name,
                        f"{piece.length_mm:.1f}",
                        piece.qty * result.item.qty,
                        f"{piece.total_length_mm * result.item.qty:.1f}",
                        piece.kg_per_m,
                        f"{piece.weight_kg * result.item.qty:.3f}",
                        piece.cut_a,
                        piece.cut_b,
                        piece.note,
                    ]
                )


def _file_url(code: str, name: str) -> str:
    return f"/api/files/{code}/{name}"


def _artifact(path: Path, kind: str, code: str, tag: str = "") -> Artifact:
    return Artifact(
        name=path.name,
        kind=kind,
        tag=tag,
        size=path.stat().st_size if path.exists() else 0,
        url=_file_url(code, path.name),
    )


def _apply_pricing_mode(
    cost: ProjectCost, results: list[ItemResult], pricing_mode: str, price_level: str
) -> tuple[ProjectCost, str, str]:
    """Áp giá bán theo bảng giá ban hành (nếu chọn) — trả về cost + chế độ + cấp giá thực dùng."""
    pricing_mode = (pricing_mode or "bom").lower()
    price_level = (price_level or "le").lower()
    if pricing_mode == "book":
        from .pricing_book import apply_to_cost, load_book

        book = load_book()
        level_codes = [level.code for level in book.levels]
        if book.groups and level_codes:
            chosen = price_level if price_level in level_codes else level_codes[0]
            return apply_to_cost(cost, results, book, chosen), pricing_mode, chosen
        return cost, "bom", ""
    return cost, "bom", ""


def build_project(
    project: ProjectSpec,
    with_3d: bool = True,
    with_drawings: bool = True,
    timeout: int = 420,
    pricing_mode: str = "bom",
    price_level: str = "le",
) -> BuildOutcome:
    systems = _resolve_systems(project)
    issues = validate_project(project, systems)
    if has_errors(issues):
        raise BuildError(issues)

    results: list[ItemResult] = []
    seen_messages = {issue.message for issue in issues}
    for item in project.items:
        code = (item.system or project.defaults.system or "").upper()
        result = build_item(item, systems[code], project.defaults.glass)
        results.append(result)
        for warning in result.warnings:
            if warning not in seen_messages:
                issues.append(Issue(level="warning", code="layout", tag=item.tag, message=warning))
                seen_messages.add(warning)

    pricing = catalog.load_pricing()
    full_catalog = catalog.load_catalog()
    stocks = sorted({system.bar_length_mm for system in systems.values()}) or [6500.0]
    kerf = max((system.kerf_mm for system in systems.values()), default=5.0)
    end_trim = max((system.end_trim_mm for system in systems.values()), default=30.0)
    profile_names: dict[str, str] = {}
    for result in results:
        for piece in result.pieces:
            profile_names.setdefault(piece.profile_code, piece.profile_name)
    cut_plan: list[BarGroup] = optimize(
        pieces_from_results(results),
        stock_lengths=stocks,
        kerf_mm=kerf,
        end_trim_mm=end_trim,
        profile_names=profile_names,
    )
    cost = compute_project_cost(results, pricing)
    cost, pricing_mode, price_level = _apply_pricing_mode(cost, results, pricing_mode, price_level)

    project_code = project.project.code
    out = paths.project_out_dir(project_code)
    for stale in out.glob("*"):
        if stale.is_file() and stale.suffix.lower() in {".dxf", ".svg", ".obj", ".mtl", ".csv", ".xlsx", ".pdf"}:
            stale.unlink()

    artifacts: list[Artifact] = []
    spec_path = out / "project.json"
    spec_path.write_text(
        json.dumps(project.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    artifacts.append(_artifact(spec_path, "json", project_code))

    cutlist_path = out / "cutlist.csv"
    _write_cutlist_csv(results, cutlist_path)
    artifacts.append(_artifact(cutlist_path, "csv", project_code))

    item_payload: list[dict] = []
    for result, item_cost in zip(results, cost.items):
        system = systems[result.system_code]
        files: dict[str, str] = {}
        if with_drawings:
            sheet = build_sheet(result, project.project, pricing, system)
            dxf_path = out / f"{result.item.tag}.dxf"
            write_dxf(sheet, dxf_path)
            sheet_svg = out / f"{result.item.tag}_banve.svg"
            write_svg(sheet, sheet_svg)
            preview_svg = out / f"{result.item.tag}_3d.svg"
            preview_svg.write_text(render_preview_svg(result), encoding="utf-8")
            obj_path = write_obj(result, out / f"{result.item.tag}.obj")
            for path, kind in ((dxf_path, "dxf"), (sheet_svg, "svg"), (preview_svg, "svg3d"), (obj_path, "obj")):
                artifacts.append(_artifact(path, kind, project_code, result.item.tag))
            files = {
                "dxf": _file_url(project_code, dxf_path.name),
                "drawing": _file_url(project_code, sheet_svg.name),
                "preview": _file_url(project_code, preview_svg.name),
                "obj": _file_url(project_code, obj_path.name),
            }
        item_payload.append(
            {
                "tag": result.item.tag,
                "room": result.item.room,
                "type": result.item.type,
                "type_label": result.item.type_label,
                "system": result.system_code,
                "width_mm": result.width_mm,
                "height_mm": result.height_mm,
                "qty": result.item.qty,
                "area_m2": round(result.area_m2, 3),
                "alum_kg": round(result.alum_kg_total, 2),
                "glass_m2": round(result.glass_m2_total, 3),
                "leaves": result.leaves,
                "cells": result.cells,
                "height_sill_mm": result.item.sill_mm,
                "price": item_cost.price,
                "unit_price_m2": item_cost.unit_price_m2,
                "files": files,
                "warnings": [issue.message for issue in issues if issue.tag == result.item.tag],
            }
        )

    excel_path = build_quote(
        project.project,
        results,
        cost,
        pricing,
        full_catalog,
        cut_plan,
        out / f"bao_gia_{project_code}.xlsx",
    )
    artifacts.append(_artifact(excel_path, "xlsx", project_code))

    costing_path = build_costing_workbook(
        out / f"gia_thanh_{project_code}.xlsx",
        pricing,
        full_catalog,
        project.project,
        results,
        cost,
    )
    artifacts.append(_artifact(costing_path, "xlsx", project_code))

    pdf_path = build_quote_pdf(
        project.project,
        results,
        cost,
        pricing,
        out / f"bao_gia_{project_code}.pdf",
        full_catalog,
    )
    artifacts.append(_artifact(pdf_path, "pdf", project_code))

    plan = build_plan(results, systems, project_code)
    plan_path = out / "build_plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    artifacts.append(_artifact(plan_path, "json3d", project_code))

    fc_status = freecad.status()
    fc_result: dict = {"available": fc_status["available"], "path": fc_status["path"], "ok": False}
    if with_3d:
        if fc_status["available"]:
            fc_result = freecad.run(plan_path, out, timeout=timeout)
            report = fc_result.get("report") or {}
            for key, kind in (("fcstd", "fcstd"), ("step", "step"), ("stl", "stl")):
                raw = report.get(key)
                if raw and Path(raw).exists():
                    artifacts.append(_artifact(Path(raw), kind, project_code))
        else:
            fc_result["message"] = fc_status["hint"]
    else:
        fc_result["message"] = "Bỏ qua dựng 3D theo yêu cầu"

    summary = {
        "project_code": project_code,
        "project_name": project.project.name,
        "customer": project.project.customer,
        "currency": cost.currency,
        "items": len(results),
        "total_leaves": sum(result.leaves for result in results),
        "area_m2": cost.area_m2,
        "alum_kg": cost.alum_kg,
        "glass_m2": cost.glass_m2,
        "cost_total": cost.cost_total,
        "price": cost.price,
        "vat": cost.vat,
        "price_with_vat": cost.price_with_vat,
        "avg_unit_price_m2": cost.avg_unit_price_m2,
        "pricing_mode": pricing_mode,
        "price_level": price_level,
        "bars": sum(len(group.bars) for group in cut_plan),
        "waste_m": round(sum(group.total_waste_mm for group in cut_plan) / 1000, 2),
        "errors": sum(1 for issue in issues if issue.level == "error"),
        "warnings": sum(1 for issue in issues if issue.level == "warning"),
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "freecad": fc_result,
    }
    summary_path = out / "build_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    return BuildOutcome(
        project=project.project,
        items=item_payload,
        issues=issues,
        artifacts=artifacts,
        summary=summary,
        cut_plan=[
            {
                "profile_code": group.profile_code,
                "profile_name": group.profile_name,
                "stock_mm": group.stock_mm,
                "bars": len(group.bars),
                "waste_m": round(group.total_waste_mm / 1000, 2),
                "waste_percent": round(group.waste_percent, 1),
                "patterns": [bar.pattern() for bar in group.bars],
            }
            for group in cut_plan
        ],
        freecad=fc_result,
        results=results,
        cost=cost,
        out_dir=str(out),
    )


def load_project(code: str) -> ProjectSpec:
    path = paths.out_dir() / code / "project.json"
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy dự án {code}")
    return ProjectSpec.model_validate(json.loads(path.read_text(encoding="utf-8")))


def list_projects() -> list[dict]:
    base = paths.out_dir()
    if not base.exists():
        return []
    projects = []
    for folder in sorted(base.iterdir(), reverse=True):
        if not folder.is_dir():
            continue
        spec_file = folder / "project.json"
        summary_file = folder / "build_summary.json"
        if not spec_file.exists():
            continue
        entry = {"code": folder.name, "name": "", "customer": "", "date": "", "price": 0, "files": 0}
        try:
            raw = json.loads(spec_file.read_text(encoding="utf-8"))
            entry["name"] = raw.get("project", {}).get("name", "")
            entry["customer"] = raw.get("project", {}).get("customer", "")
            entry["date"] = raw.get("project", {}).get("date", "")
        except Exception:
            pass
        if summary_file.exists():
            try:
                summary = json.loads(summary_file.read_text(encoding="utf-8"))
                entry["price"] = summary.get("price", 0)
                entry["area_m2"] = summary.get("area_m2", 0)
            except Exception:
                pass
        entry["files"] = len([p for p in folder.iterdir() if p.is_file()])
        projects.append(entry)
    return projects


def regenerate_quote_docs(
    project: ProjectSpec,
    pricing_mode: str = "bom",
    price_level: str = "le",
) -> dict:
    """Sinh lại project.json + Excel/PDF báo giá theo thông tin mới (giữ nguyên bản vẽ/3D đã có)."""
    systems = _resolve_systems(project)
    issues = validate_project(project, systems)
    if has_errors(issues):
        raise BuildError(issues)

    results: list[ItemResult] = []
    seen = {issue.message for issue in issues}
    for item in project.items:
        code = (item.system or project.defaults.system or "").upper()
        result = build_item(item, systems[code], project.defaults.glass)
        results.append(result)
        for warning in result.warnings:
            if warning not in seen:
                issues.append(Issue(level="warning", code="layout", tag=item.tag, message=warning))
                seen.add(warning)

    pricing = catalog.load_pricing()
    full_catalog = catalog.load_catalog()
    stocks = sorted({system.bar_length_mm for system in systems.values()}) or [6500.0]
    kerf = max((system.kerf_mm for system in systems.values()), default=5.0)
    end_trim = max((system.end_trim_mm for system in systems.values()), default=30.0)
    profile_names: dict[str, str] = {}
    for result in results:
        for piece in result.pieces:
            profile_names.setdefault(piece.profile_code, piece.profile_name)
    cut_plan = optimize(
        pieces_from_results(results),
        stock_lengths=stocks,
        kerf_mm=kerf,
        end_trim_mm=end_trim,
        profile_names=profile_names,
    )
    cost = compute_project_cost(results, pricing)
    cost, pricing_mode, price_level = _apply_pricing_mode(cost, results, pricing_mode, price_level)

    project_code = project.project.code
    out = paths.project_out_dir(project_code)
    out.mkdir(parents=True, exist_ok=True)
    spec_path = out / "project.json"
    spec_path.write_text(
        json.dumps(project.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    excel_path = build_quote(
        project.project,
        results,
        cost,
        pricing,
        full_catalog,
        cut_plan,
        out / f"bao_gia_{project_code}.xlsx",
    )
    pdf_path = build_quote_pdf(
        project.project,
        results,
        cost,
        pricing,
        out / f"bao_gia_{project_code}.pdf",
        full_catalog,
    )
    artifacts = [
        _artifact(spec_path, "json", project_code),
        _artifact(excel_path, "xlsx", project_code),
        _artifact(pdf_path, "pdf", project_code),
    ]
    return {
        "ok": True,
        "artifacts": [artifact.model_dump(mode="json") for artifact in artifacts],
        "issues": [issue.model_dump(mode="json") for issue in issues],
        "summary": {
            "project_code": project_code,
            "items": len(results),
            "area_m2": cost.area_m2,
            "price": cost.price,
            "vat": cost.vat,
            "price_with_vat": cost.price_with_vat,
            "pricing_mode": pricing_mode,
            "price_level": price_level,
            "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        },
    }
