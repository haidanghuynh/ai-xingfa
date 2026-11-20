"""Fixture dùng chung: sandbox copy config/data/out để test không sửa dữ liệu thật."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    home = tmp_path / "home"
    shutil.copytree(ROOT / "config", home / "config")
    shutil.copytree(ROOT / "data", home / "data")
    (home / "out").mkdir()
    monkeypatch.setenv("XFCAD_HOME", str(home))
    return home


@pytest.fixture()
def demo_project():
    import json

    from xingfacad.models import ProjectSpec

    raw = json.loads((ROOT / "data" / "specs" / "demo_nha_a.json").read_text(encoding="utf-8"))
    return ProjectSpec.model_validate(raw)
