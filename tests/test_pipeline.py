"""Test toàn pipeline: build dự án demo -> DXF/SVG/OBJ/XLSX."""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import ezdxf
import pytest
from openpyxl import load_workbook

from xingfacad.pipeline import BuildError, build_project
from xingfacad.models import ProjectSpec


def test_build_demo_project(sandbox, demo_project):
    outcome = build_project(demo_project, with_3d=False, with_drawings=True)
    assert outcome.summary["items"] == len(demo_project.items)
    assert outcome.summary["area_m2"] > 0
    assert outcome.summary["alum_kg"] > 0
    assert outcome.summary["price"] > outcome.summary["cost_total"]
    assert outcome.summary["errors"] == 0

    out = sandbox / "out" / demo_project.project.code
    assert (out / "project.json").exists()
    assert (out / "cutlist.csv").exists()
    assert (out / "build_plan.json").exists()
    assert (out / "build_summary.json").exists()

    for item in demo_project.items:
        assert (out / f"{item.tag}.dxf").exists()
        assert (out / f"{item.tag}_banve.svg").exists()
        assert (out / f"{item.tag}_3d.svg").exists()
        assert (out / f"{item.tag}.obj").exists()


def test_dxf_is_valid(sandbox, demo_project):
    build_project(demo_project, with_3d=False)
    path = sandbox / "out" / demo_project.project.code / "C1.dxf"
    doc = ezdxf.readfile(path)
    layers = {layer.dxf.name for layer in doc.layers}
    assert {"frame", "sash", "glass", "dim", "text", "table"} <= layers
    msp = doc.modelspace()
    kinds = {entity.dxftype() for entity in msp}
    assert {"LINE", "LWPOLYLINE", "TEXT"} <= kinds
    texts = [entity.dxf.text for entity in msp if entity.dxftype() == "TEXT"]
    assert any("C1" in text for text in texts)


def test_svg_files_are_well_formed(sandbox, demo_project):
    build_project(demo_project, with_3d=False)
    out = sandbox / "out" / demo_project.project.code
    for name in ("C1_banve.svg", "C1_3d.svg"):
        root = ET.parse(out / name).getroot()
        assert root.tag.endswith("svg")
        assert len(list(root)) > 3


def test_obj_has_faces(sandbox, demo_project):
    build_project(demo_project, with_3d=False)
    path = sandbox / "out" / demo_project.project.code / "C1.obj"
    lines = path.read_text(encoding="utf-8").splitlines()
    vertices = [line for line in lines if line.startswith("v ")]
    faces = [line for line in lines if line.startswith("f ")]
    assert len(vertices) > 30
    assert len(faces) > 10


def test_excel_workbook(sandbox, demo_project):
    build_project(demo_project, with_3d=False)
    path = sandbox / "out" / demo_project.project.code / f"bao_gia_{demo_project.project.code}.xlsx"
    wb = load_workbook(path)
    assert wb.sheetnames == [
        "01_BaoGia", "02_BangCat", "03_ToiUuCat", "04_Kinh_PhuKien", "05_TongHop", "06_CauHinh",
    ]
    assert set(wb.defined_names.keys()) >= {
        "GIA_NHOM", "HAO_HUT_PCT", "NHAN_CONG_PCT", "LOI_NHUAN_PCT", "VAT_PCT",
    }
    ws = wb["01_BaoGia"]
    header_row = next(row for row in range(1, 40) if ws.cell(row=row, column=1).value == "STT")
    first_row = header_row + 1
    total_row = header_row + 1 + len(demo_project.items)
    assert ws.cell(row=first_row, column=2).value == demo_project.items[0].tag
    assert str(ws.cell(row=first_row, column=9).value).startswith("=ROUND(")
    assert ws.cell(row=first_row, column=10).value > 0
    assert ws.cell(row=total_row, column=1).value == "TỔNG"
    assert str(ws.cell(row=total_row, column=21).value).startswith("=SUM(")

    summary = wb["05_TongHop"]
    assert str(summary["B14"].value) == f"='01_BaoGia'!U{total_row}"
    assert summary["A19"].value == "TỔNG THANH TOÁN"


def test_cutlist_csv_has_all_items(sandbox, demo_project):
    outcome = build_project(demo_project, with_3d=False)
    text = (sandbox / "out" / demo_project.project.code / "cutlist.csv").read_text(encoding="utf-8-sig")
    header = text.splitlines()[0]
    assert "Mã thanh" in header
    for item in demo_project.items:
        assert item.tag in text
    assert outcome.cut_plan


def test_build_error_on_unknown_system(sandbox):
    project = ProjectSpec.model_validate(
        {
            "project": {"code": "ERR-1"},
            "defaults": {"system": "KHONG-CO"},
            "items": [
                {"tag": "C1", "type": "casement", "width_mm": 1200, "height_mm": 1200, "system": "KHONG-CO"}
            ],
        }
    )
    with pytest.raises(BuildError):
        build_project(project, with_3d=False)


def test_build_plan_geometry_matches_bom(sandbox, demo_project):
    outcome = build_project(demo_project, with_3d=False)
    plan = json.loads((sandbox / "out" / demo_project.project.code / "build_plan.json").read_text(encoding="utf-8"))
    assert plan["units"] == "mm"
    total_bars = sum(len(item["bars"]) for item in plan["items"])
    assert total_bars == sum(len(result.bars3d) for result in outcome.results)
    for item in plan["items"]:
        for bar in item["bars"]:
            assert len(bar["polygon"]) >= 4
            assert bar["y1"] > bar["y0"]


def test_build_plan_includes_hardware(sandbox, demo_project):
    build_project(demo_project, with_3d=False)
    plan = json.loads((sandbox / "out" / demo_project.project.code / "build_plan.json").read_text(encoding="utf-8"))
    c1 = next(item for item in plan["items"] if item["tag"] == "C1")
    kinds = [hw["kind"] for hw in c1["hardware"]]
    assert kinds.count("hinge") == 6
    assert kinds.count("lock") == 2
    assert all(hw["w"] > 0 and hw["h"] > 0 and hw["d"] > 0 for hw in c1["hardware"])

    c3 = next(item for item in plan["items"] if item["tag"] == "C3")
    assert [hw["kind"] for hw in c3["hardware"]].count("wheel") == 4
