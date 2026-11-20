"""Đường dẫn dùng chung. Có thể override thư mục gốc bằng biến môi trường XFCAD_HOME."""
from __future__ import annotations

import os
from pathlib import Path


def root() -> Path:
    env = os.environ.get("XFCAD_HOME")
    if env:
        return Path(env).expanduser().resolve()
    # src/xingfacad/paths.py -> cad/
    return Path(__file__).resolve().parents[2]


def config_dir() -> Path:
    return root() / "config"


def systems_dir() -> Path:
    return config_dir() / "systems"


def catalog_file() -> Path:
    return config_dir() / "catalog.json"


def pricing_file() -> Path:
    return config_dir() / "pricing.json"


def data_dir() -> Path:
    return root() / "data"


def specs_dir() -> Path:
    return data_dir() / "specs"


def static_dir() -> Path:
    return root() / "static"


def out_dir() -> Path:
    return root() / "out"


def project_out_dir(code: str) -> Path:
    safe = "".join(ch for ch in code if ch.isalnum() or ch in "-_.") or "project"
    path = out_dir() / safe
    path.mkdir(parents=True, exist_ok=True)
    return path
