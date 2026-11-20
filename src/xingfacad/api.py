"""FastAPI: API + phục vụ GUI web nhập liệu."""
from __future__ import annotations

import base64
import importlib.util
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from . import APP_NAME, __version__, ai_vision, catalog, freecad, paths, pipeline
from .costing import build_costing_template, read_pricing_from_workbook
from .price_book_export import build_book_pdf, build_book_xlsx
from .pricing_book import PricingBook, compute_book, derive_group_cost, load_book, save_book
from .models import (
    ITEM_TYPE_LABELS,
    PANEL_KINDS,
    PROFILE_KEYS,
    ProjectSpec,
    SystemDef,
)
from .pipeline import BuildError

app = FastAPI(title=APP_NAME, version=__version__, description="Tự động hoá 3D FreeCAD + bản vẽ 2D + báo giá Excel")

STATIC = paths.static_dir()
if STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

WEB_DIST = paths.root() / "web" / "dist"
WEB_ASSETS = WEB_DIST / "assets"
if WEB_ASSETS.exists():
    app.mount("/assets", StaticFiles(directory=str(WEB_ASSETS)), name="assets")

_SYSTEM_CODE = re.compile(r"^[A-Za-z0-9._-]{1,32}$")
_FILE_NAME = re.compile(r"^[A-Za-z0-9._-]{1,120}$")


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


@app.get("/")
def index():
    """Ưu tiên giao diện React (web/dist), fallback giao diện vanilla trong static/."""
    react_index = WEB_DIST / "index.html"
    if react_index.exists():
        return FileResponse(react_index)
    page = STATIC / "index.html"
    if not page.exists():
        return PlainTextResponse("Chưa có giao diện. Chạy `cd web && npm run build`", status_code=404)
    return FileResponse(page)


@app.get("/favicon.svg", include_in_schema=False)
def favicon():
    for candidate in (WEB_DIST / "favicon.svg", STATIC / "favicon.svg"):
        if candidate.exists():
            return FileResponse(candidate, media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Không có favicon")


@app.get("/api/status")
def api_status() -> dict[str, Any]:
    return {
        "app": APP_NAME,
        "version": __version__,
        "freecad": freecad.status(),
        "dxf": _module_available("ezdxf"),
        "excel": _module_available("openpyxl"),
        "openai": bool(os.environ.get("OPENAI_API_KEY")),
        "ai": {entry["name"]: entry["available"] for entry in ai_vision.provider_status()},
        "out_dir": str(paths.out_dir()),
        "item_types": ITEM_TYPE_LABELS,
        "panel_kinds": PANEL_KINDS,
        "profile_keys": PROFILE_KEYS,
    }


# --------------------------------------------------------------------------- #
# Catalogue hệ nhôm
# --------------------------------------------------------------------------- #
@app.get("/api/systems")
def list_systems() -> list[dict]:
    systems = catalog.list_systems()
    return [
        {
            "code": system.code,
            "name": system.name,
            "kind": system.kind,
            "joint": system.joint,
            "verified": system.verified,
            "profiles": len(system.profiles),
            "bar_length_mm": system.bar_length_mm,
        }
        for system in systems
    ]


@app.get("/api/systems/{code}", response_model=SystemDef)
def get_system(code: str) -> SystemDef:
    try:
        return catalog.load_system(code)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/systems")
def save_system(payload: dict = Body(...)) -> dict:
    try:
        system = SystemDef.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=json.loads(exc.json())) from exc
    if not _SYSTEM_CODE.match(system.code):
        raise HTTPException(status_code=422, detail="Mã hệ chỉ gồm chữ, số, dấu . _ - (tối đa 32 ký tự)")
    path = catalog.save_system(system)
    return {"ok": True, "code": system.code, "path": str(path)}


@app.delete("/api/systems/{code}")
def delete_system(code: str) -> dict:
    deleted = catalog.delete_system(code)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hệ {code}")
    return {"ok": True, "deleted": code}


@app.post("/api/systems/{code}/duplicate")
def duplicate_system(code: str, payload: dict = Body(default={})) -> dict:
    try:
        source = catalog.load_system(code)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    new_code = str(payload.get("new_code") or f"{source.code}COPY")[:32]
    if not _SYSTEM_CODE.match(new_code):
        raise HTTPException(status_code=422, detail="new_code không hợp lệ")
    clone = source.model_copy(deep=True)
    clone.code = new_code.upper()
    clone.name = f"{source.name} (bản sao)"
    clone.verified = False
    for profile in clone.profiles.values():
        profile.code = profile.code.replace(source.code, clone.code)
    catalog.save_system(clone)
    return {"ok": True, "code": clone.code}


# --------------------------------------------------------------------------- #
# Kính / phụ kiện / bảng giá
# --------------------------------------------------------------------------- #
@app.get("/api/catalog")
def get_catalog() -> dict:
    return catalog.load_catalog()


@app.put("/api/catalog")
def put_catalog(payload: dict = Body(...)) -> dict:
    if not isinstance(payload.get("glass"), dict) or not isinstance(payload.get("hardware"), dict):
        raise HTTPException(status_code=422, detail="catalog phải có 'glass' và 'hardware' là object")
    catalog.save_catalog(payload)
    return {"ok": True}


@app.get("/api/pricing")
def get_pricing() -> dict:
    return catalog.load_pricing()


@app.put("/api/pricing")
def put_pricing(payload: dict = Body(...)) -> dict:
    defaults = catalog.load_pricing()
    merged = {**defaults, **payload}
    for key in (
        "aluminum_price_per_kg",
        "waste_percent",
        "labor_percent_of_material",
        "profit_percent",
        "vat_percent",
        "consumables_per_m2",
        "transport_per_item",
    ):
        try:
            merged[key] = float(merged.get(key, defaults.get(key, 0)) or 0)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=f"Giá trị {key} không phải số") from exc
    catalog.save_pricing(merged)
    return {"ok": True, "pricing": merged}


@app.get("/api/template/costing.xlsx", include_in_schema=False)
def api_costing_template():
    """Tải file Excel mẫu để tính giá thành (bảng giá đầu vào + công thức)."""
    folder = paths.out_dir() / "_templates"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "bang_tinh_gia_thanh.xlsx"
    build_costing_template(target, catalog.load_pricing(), catalog.load_catalog())
    return FileResponse(
        target,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="bang_tinh_gia_thanh.xlsx",
    )


@app.post("/api/pricing/import")
def api_import_pricing(payload: dict = Body(...)) -> dict:
    """Đọc 7 thông số giá từ file tính giá thành (sheet 01_DauVao) và cập nhật bảng giá."""
    raw = str(payload.get("file_base64", "") or payload.get("file", "")).strip()
    if not raw:
        raise HTTPException(status_code=422, detail="Thiếu file_base64")
    if raw.startswith("data:") and "," in raw:
        raw = raw.split(",", 1)[1]
    try:
        data = base64.b64decode(raw + "===", validate=False)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Base64 không hợp lệ: {exc}") from exc
    temp_path = Path(tempfile.gettempdir()) / f"xfcad_pricing_{os.getpid()}.xlsx"
    temp_path.write_bytes(data)
    try:
        found = read_pricing_from_workbook(temp_path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Không đọc được file Excel: {exc}") from exc
    finally:
        temp_path.unlink(missing_ok=True)
    if not found:
        raise HTTPException(
            status_code=422,
            detail="Không thấy 7 thông số giá (GIA_NHOM, HAO_HUT_PCT...) ở sheet 01_DauVao",
        )
    pricing = catalog.load_pricing()
    pricing.update(found)
    catalog.save_pricing(pricing)
    return {"ok": True, "updated": found, "pricing": pricing}


# --------------------------------------------------------------------------- #
# Bảng chi phí giá thành & giá bán đến tay khách
# --------------------------------------------------------------------------- #
@app.get("/api/pricing-book")
def api_pricing_book() -> dict:
    book = load_book()
    return {"book": book.model_dump(mode="json"), "result": compute_book(book).model_dump(mode="json")}


@app.put("/api/pricing-book")
def api_save_pricing_book(payload: dict = Body(...)) -> dict:
    try:
        book = PricingBook.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=json.loads(exc.json())) from exc
    if not book.groups:
        raise HTTPException(status_code=422, detail="Bảng giá phải có ít nhất 1 nhóm sản phẩm")
    if not book.levels:
        raise HTTPException(status_code=422, detail="Cần ít nhất 1 cấp giá")
    save_book(book)
    return {"ok": True, "book": book.model_dump(mode="json"), "result": compute_book(book).model_dump(mode="json")}


@app.post("/api/pricing-book/derive/{code}")
def api_derive_group_cost(code: str) -> dict:
    book = load_book()
    try:
        cost = derive_group_cost(book, code)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Không tính được định mức: {exc}") from exc
    return {"ok": True, "code": code.upper(), "cost": cost.model_dump(mode="json")}


def _book_export_folder() -> Path:
    folder = paths.out_dir() / "_templates"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


@app.get("/api/pricing-book/export.xlsx", include_in_schema=False)
def api_export_book_xlsx():
    book = load_book()
    result = compute_book(book)
    company = catalog.load_pricing().get("company", {})
    target = _book_export_folder() / "bang_gia_thanh_va_gia_ban.xlsx"
    build_book_xlsx(book, result, company, target)
    return FileResponse(
        target,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="bang_gia_thanh_va_gia_ban.xlsx",
    )


@app.get("/api/pricing-book/export.pdf", include_in_schema=False)
def api_export_book_pdf():
    book = load_book()
    result = compute_book(book)
    company = catalog.load_pricing().get("company", {})
    target = _book_export_folder() / "bang_gia_ban.pdf"
    build_book_pdf(book, result, company, target)
    return FileResponse(target, media_type="application/pdf", filename="bang_gia_ban.pdf")


# --------------------------------------------------------------------------- #
# Dự án
# --------------------------------------------------------------------------- #
def _parse_project(payload: dict) -> ProjectSpec:
    if "project" not in payload and "items" not in payload:
        raise HTTPException(status_code=422, detail="Body phải là project spec (có 'project' và 'items')")
    try:
        return ProjectSpec.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=json.loads(exc.json())) from exc


def _systems_for(project: ProjectSpec) -> dict[str, SystemDef]:
    systems: dict[str, SystemDef] = {}
    errors: list[str] = []
    for code in {(item.system or project.defaults.system or "").upper() for item in project.items}:
        if not code:
            continue
        try:
            systems[code] = catalog.load_system(code)
        except KeyError as exc:
            errors.append(str(exc))
    if errors:
        raise HTTPException(status_code=422, detail="; ".join(errors))
    return systems


@app.get("/api/demo", response_model=ProjectSpec)
def api_demo() -> ProjectSpec:
    demo = paths.specs_dir() / "demo_nha_a.json"
    if not demo.exists():
        raise HTTPException(status_code=404, detail="Chưa có file demo")
    return ProjectSpec.model_validate(json.loads(demo.read_text(encoding="utf-8")))


@app.get("/api/projects")
def api_projects() -> list[dict]:
    return pipeline.list_projects()


@app.get("/api/projects/{code}", response_model=ProjectSpec)
def api_project(code: str) -> ProjectSpec:
    try:
        return pipeline.load_project(code)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/api/projects/{code}")
def api_delete_project(code: str) -> dict:
    if not _SYSTEM_CODE.match(code):
        raise HTTPException(status_code=422, detail="Mã dự án không hợp lệ")
    folder = paths.out_dir() / code
    if not folder.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy dự án")
    for path in sorted(folder.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            path.rmdir()
    folder.rmdir()
    return {"ok": True}


@app.post("/api/validate")
def api_validate(payload: dict = Body(...)) -> dict:
    from .layout import build_item
    from .validate import validate_project

    project = _parse_project(payload)
    systems = _systems_for(project)
    issues = [issue.model_dump() for issue in validate_project(project, systems)]
    totals = {"items": 0, "area_m2": 0.0, "alum_kg": 0.0, "glass_m2": 0.0, "leaves": 0, "bars": 0}
    seen = {issue["message"] for issue in issues}
    for item in project.items:
        code = (item.system or project.defaults.system or "").upper()
        try:
            result = build_item(item, systems[code], project.defaults.glass)
        except ValueError as exc:
            issues.append({"level": "error", "tag": item.tag, "code": "layout.error", "message": str(exc)})
            continue
        totals["items"] += 1
        totals["area_m2"] += result.area_m2
        totals["alum_kg"] += result.alum_kg_total
        totals["glass_m2"] += result.glass_m2_total
        totals["leaves"] += result.leaves
        totals["bars"] += len(result.pieces)
        for warning in result.warnings:
            if warning not in seen:
                issues.append({"level": "warning", "tag": item.tag, "code": "layout", "message": warning})
                seen.add(warning)
    totals = {key: (round(value, 3) if isinstance(value, float) else value) for key, value in totals.items()}
    return {
        "ok": not any(issue["level"] == "error" for issue in issues),
        "issues": issues,
        "totals": totals,
    }


@app.post("/api/build", response_model=pipeline.BuildOutcome)
def api_build(payload: dict = Body(...)) -> pipeline.BuildOutcome:
    project_payload = payload.get("project", payload)
    project = _parse_project(project_payload)
    with_3d = bool(payload.get("with_3d", True))
    with_drawings = bool(payload.get("with_drawings", True))
    try:
        outcome = pipeline.build_project(
            project,
            with_3d=with_3d,
            with_drawings=with_drawings,
            pricing_mode=str(payload.get("pricing_mode", "bom")),
            price_level=str(payload.get("price_level", "le")),
        )
    except BuildError as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": str(exc), "issues": [issue.model_dump() for issue in exc.issues]},
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return outcome.model_dump(mode="json")


@app.get("/api/files/{code}/{name}")
def api_file(code: str, name: str, inline: bool = False):
    if not _SYSTEM_CODE.match(code) or not _FILE_NAME.match(name):
        raise HTTPException(status_code=400, detail="Tên file không hợp lệ")
    folder = (paths.out_dir() / code).resolve()
    target = (folder / name).resolve()
    if folder not in target.parents or not target.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy file")
    suffix = target.suffix.lower()
    media = {
        ".svg": "image/svg+xml",
        ".json": "application/json",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pdf": "application/pdf",
        ".dxf": "image/vnd.dxf",
        ".csv": "text/csv; charset=utf-8",
        ".obj": "text/plain; charset=utf-8",
    }.get(suffix, "application/octet-stream")
    return FileResponse(
        target,
        media_type=media,
        filename=name,
        content_disposition_type="inline" if inline else "attachment",
    )


@app.post("/api/quote")
def api_regenerate_quote(payload: dict = Body(...)) -> dict:
    """Cập nhật thông tin báo giá (đơn vị yêu cầu, người báo giá…) và sinh lại PDF/Excel."""
    project = _parse_project(payload.get("project", payload))
    try:
        return pipeline.regenerate_quote_docs(
            project,
            pricing_mode=str(payload.get("pricing_mode", "bom")),
            price_level=str(payload.get("price_level", "le")),
        )
    except BuildError as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": str(exc), "issues": [issue.model_dump() for issue in exc.issues]},
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --------------------------------------------------------------------------- #
# Ảnh -> JSON (tuỳ chọn, cần OPENAI_API_KEY)
# --------------------------------------------------------------------------- #
def _prompt_text() -> str:
    prompt = paths.data_dir() / "prompts" / "extract_windows.md"
    if prompt.exists():
        return prompt.read_text(encoding="utf-8")
    return "Bạn là kỹ sư cửa nhôm. Đọc ảnh, trả về JSON danh sách cửa, không suy ra kích thước mm."


@app.get("/api/prompt")
def api_prompt() -> PlainTextResponse:
    return PlainTextResponse(_prompt_text(), media_type="text/markdown; charset=utf-8")


@app.get("/api/ai")
def api_ai_status() -> dict:
    """Danh sách provider AI đọc ảnh + trạng thái khoá API (không lộ key)."""
    config = ai_vision.load_config()
    return {
        "default_provider": ai_vision.default_provider(),
        "temperature": config.get("temperature", 0.1),
        "providers": ai_vision.provider_status(),
        "note": config.get("note", ""),
    }


@app.post("/api/extract")
def api_extract(payload: dict = Body(...)) -> dict:
    image_b64 = str(payload.get("image_base64", "")).strip()
    if not image_b64:
        raise HTTPException(status_code=422, detail="Thiếu image_base64")
    try:
        result = ai_vision.extract(
            image_b64,
            provider=payload.get("provider"),
            model=payload.get("model"),
            prompt=payload.get("prompt"),
        )
    except ai_vision.AIConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ai_vision.AIProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result["data"] = result.get("raw", {"items": result.get("items", [])})
    return result


@app.post("/api/decode-image")
def api_decode_image(payload: dict = Body(default={})) -> dict:
    raw = str(payload.get("image_base64", "") or payload.get("image", ""))
    if not raw:
        raise HTTPException(status_code=422, detail="Thiếu image_base64")
    if raw.startswith("data:") and "," in raw:
        header, raw = raw.split(",", 1)
        mime = header.split(";")[0].replace("data:", "") or "image/png"
    else:
        mime = "image/png"
    try:
        size = len(base64.b64decode(raw, validate=False))
    except Exception:
        size = 0
    return {"ok": True, "bytes": size, "mime": mime, "data_url": f"data:{mime};base64,{raw}"}
