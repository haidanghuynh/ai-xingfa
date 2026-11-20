"""Đọc/ghi catalogue: hệ nhôm Xingfa, kính, phụ kiện, bảng giá."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import paths
from .models import GlassSpec, SystemDef


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    tmp.replace(path)
    return path


# --------------------------------------------------------------------------- #
# Hệ nhôm
# --------------------------------------------------------------------------- #
def system_files() -> list[Path]:
    folder = paths.systems_dir()
    if not folder.exists():
        return []
    return sorted(folder.glob("*.json"))


def list_systems() -> list[SystemDef]:
    systems: list[SystemDef] = []
    for path in system_files():
        try:
            raw = _read_json(path, None)
            if raw:
                systems.append(SystemDef.model_validate(raw))
        except Exception:
            continue
    return systems


def find_system_path(code: str) -> Path | None:
    code = (code or "").strip().lower()
    for path in system_files():
        if path.stem.lower() == code:
            return path
    # tìm theo trường code bên trong file
    for path in system_files():
        try:
            raw = _read_json(path, {})
        except Exception:
            continue
        if str(raw.get("code", "")).strip().lower() == code:
            return path
    return None


def load_system(code: str) -> SystemDef:
    path = find_system_path(code)
    if path is None:
        available = ", ".join(system.code for system in list_systems()) or "(trống)"
        raise KeyError(f"Không tìm thấy hệ nhôm '{code}'. Hiện có: {available}")
    return SystemDef.model_validate(_read_json(path, {}))


def save_system(system: SystemDef) -> Path:
    path = find_system_path(system.code) or (paths.systems_dir() / f"{system.code.lower()}.json")
    _write_json(path, system.model_dump(mode="json"))
    return path


def delete_system(code: str) -> bool:
    path = find_system_path(code)
    if path is None:
        return False
    path.unlink()
    return True


# --------------------------------------------------------------------------- #
# Kính / phụ kiện / bảng giá
# --------------------------------------------------------------------------- #
def load_catalog() -> dict[str, Any]:
    return _read_json(paths.catalog_file(), {"glass": {}, "hardware": {}})


def save_catalog(data: dict[str, Any]) -> Path:
    return _write_json(paths.catalog_file(), data)


def glass_options() -> dict[str, dict[str, Any]]:
    return load_catalog().get("glass", {})


def glass_spec(key: str) -> GlassSpec:
    options = glass_options()
    if key in options:
        raw = options[key]
        return GlassSpec(
            key=key,
            name=raw.get("name", key),
            thickness_mm=float(raw.get("thickness_mm", 8)),
            price_per_m2=raw.get("price_per_m2"),
        )
    return GlassSpec(key=key)


def hardware_config() -> dict[str, Any]:
    return load_catalog().get("hardware", {})


def load_pricing() -> dict[str, Any]:
    raw = _read_json(paths.pricing_file(), {})
    defaults: dict[str, Any] = {
        "currency": "VND",
        "effective_date": "",
        "aluminum_price_per_kg": 95000,
        "waste_percent": 3,
        "labor_percent_of_material": 10,
        "profit_percent": 18,
        "vat_percent": 8,
        "consumables_per_m2": 30000,
        "transport_per_item": 200000,
        "round_to": 1000,
        "company": {},
        "note": "",
    }
    defaults.update(raw)
    return defaults


def save_pricing(data: dict[str, Any]) -> Path:
    return _write_json(paths.pricing_file(), data)


def resolve_glass(project_default: GlassSpec | None, item_glass: GlassSpec | None) -> GlassSpec:
    """Ưu tiên kính của cửa, sau đó kính mặc định của dự án, cuối cùng là catalogue."""
    chosen = item_glass or project_default or GlassSpec()
    catalog_value = glass_options().get(chosen.key)
    if catalog_value:
        price = chosen.price_per_m2 if chosen.price_per_m2 is not None else catalog_value.get("price_per_m2")
        return GlassSpec(
            key=chosen.key,
            name=chosen.name or catalog_value.get("name", chosen.key),
            thickness_mm=chosen.thickness_mm or float(catalog_value.get("thickness_mm", 8)),
            price_per_m2=price,
        )
    return chosen
