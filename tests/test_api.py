"""Test API web (FastAPI TestClient)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from xingfacad.api import app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def client(sandbox):
    return TestClient(app)


@pytest.fixture()
def demo_payload():
    return json.loads((ROOT / "data/specs/demo_nha_a.json").read_text(encoding="utf-8"))


def test_status(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert data["app"] == "XingfaCAD"
    assert "freecad" in data
    assert "casement" in data["item_types"]


def test_index_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "XingfaCAD" in res.text


def test_list_systems(client):
    res = client.get("/api/systems")
    assert res.status_code == 200
    codes = {item["code"] for item in res.json()}
    assert {"XF55", "XF60", "XF65", "XF93"} <= codes


def test_system_crud(client):
    payload = client.get("/api/systems/XF65").json()
    payload["code"] = "TEST1"
    payload["name"] = "Hệ test"
    payload["verified"] = True
    res = client.post("/api/systems", json=payload)
    assert res.status_code == 200, res.text
    got = client.get("/api/systems/TEST1")
    assert got.status_code == 200
    assert got.json()["rules"]["gap_frame_sash_mm"] == 6
    assert client.delete("/api/systems/TEST1").status_code == 200
    assert client.get("/api/systems/TEST1").status_code == 404


def test_system_validation_error(client):
    payload = client.get("/api/systems/XF65").json()
    payload["code"] = "BAD1"
    payload["profiles"].pop("sash")
    res = client.post("/api/systems", json=payload)
    assert res.status_code == 422


def test_demo_and_validate(client, demo_payload):
    demo = client.get("/api/demo")
    assert demo.status_code == 200
    assert len(demo.json()["items"]) == 5

    res = client.post("/api/validate", json=demo_payload)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert body["totals"]["items"] == 5
    assert body["totals"]["alum_kg"] > 100


def test_validate_detects_small_item(client, demo_payload):
    demo_payload["items"][0]["width_mm"] = 250
    res = client.post("/api/validate", json=demo_payload)
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False
    assert any(issue["level"] == "error" for issue in body["issues"])


def test_build_and_download(client, demo_payload):
    res = client.post("/api/build", json={"project": demo_payload, "with_3d": False})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["summary"]["items"] == 5
    assert any(file["kind"] == "xlsx" for file in body["artifacts"])
    code = demo_payload["project"]["code"]
    download = client.get(f"/api/files/{code}/project.json")
    assert download.status_code == 200
    assert download.json()["project"]["code"] == code


def test_file_guard(client, demo_payload):
    client.post("/api/build", json={"project": demo_payload, "with_3d": False})
    assert client.get("/api/files/..%2F..%2Fetc/passwd").status_code in (400, 404)
    assert client.get("/api/files/DEMO-001/missing.txt").status_code == 404


def test_quote_regenerate_with_info(client, demo_payload):
    project = {
        **demo_payload,
        "project": {
            **demo_payload["project"],
            "request_org": "CÔNG TY TNHH XÂY DỰNG ABC",
            "request_contact": "Anh Nguyễn Văn A",
            "request_phone": "0903 123 456",
            "quoted_by": "Trần Thị B",
            "quoted_by_phone": "0912 345 678",
        },
    }
    res = client.post("/api/quote", json={"project": project, "pricing_mode": "book", "price_level": "le"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert {"json", "pdf", "xlsx"} <= {artifact["kind"] for artifact in body["artifacts"]}
    assert body["summary"]["price"] > 0
    assert body["summary"]["price_level"] == "le"

    code = demo_payload["project"]["code"]
    saved = client.get(f"/api/files/{code}/project.json").json()
    assert saved["project"]["quoted_by"] == "Trần Thị B"
    assert saved["project"]["request_org"] == "CÔNG TY TNHH XÂY DỰNG ABC"

    pdf = client.get(f"/api/files/{code}/bao_gia_{code}.pdf?inline=1")
    assert pdf.status_code == 200
    assert pdf.headers["content-disposition"].startswith("inline")
    assert pdf.content[:4] == b"%PDF"


def test_quote_regenerate_rejects_invalid(client, demo_payload):
    bad = {**demo_payload, "items": [{**demo_payload["items"][0], "width_mm": 100}]}
    res = client.post("/api/quote", json={"project": bad})
    assert res.status_code in (400, 422)


def test_ai_status_and_extract(client, monkeypatch):
    import json as jsonlib

    from xingfacad import ai_vision

    status = client.get("/api/ai")
    assert status.status_code == 200
    names = {entry["name"] for entry in status.json()["providers"]}
    assert {"openai", "gemini"} <= names

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    missing = client.post("/api/extract", json={"image_base64": "AAAA"})
    assert missing.status_code == 400
    assert "OPENAI_API_KEY" in missing.json()["detail"]

    monkeypatch.setenv("OPENAI_API_KEY", "test")
    payload = {
        "items": [
            {
                "tag": "C1",
                "type": "casement",
                "width_mm": None,
                "height_mm": None,
                "panels": [{"kind": "sash", "open": "out", "dir": "left", "ratio": 1}],
                "confidence": 0.8,
            }
        ]
    }
    monkeypatch.setattr(
        ai_vision,
        "_post_json",
        lambda *args, **kwargs: {"choices": [{"message": {"content": jsonlib.dumps(payload)}}]},
    )
    res = client.post("/api/extract", json={"image_base64": "iVBORw0KGgo="})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["provider"] == "openai"
    assert body["items"][0]["tag"] == "C1"
    assert body["items"][0]["width_mm"] is None
    assert "kich_thuoc" in body["items"][0]["needs_review"]
    assert "data" in body


def test_pricing_roundtrip(client):
    pricing = client.get("/api/pricing").json()
    pricing["aluminum_price_per_kg"] = 100000
    res = client.put("/api/pricing", json=pricing)
    assert res.status_code == 200
    assert client.get("/api/pricing").json()["aluminum_price_per_kg"] == 100000


def test_costing_template_download_and_import(client, tmp_path):
    template = client.get("/api/template/costing.xlsx")
    assert template.status_code == 200
    assert len(template.content) > 5_000

    local = tmp_path / "template.xlsx"
    local.write_bytes(template.content)

    from openpyxl import load_workbook
    import base64

    workbook = load_workbook(local)
    sheet = workbook["01_DauVao"]
    for row in range(1, sheet.max_row + 1):
        if sheet.cell(row=row, column=1).value == "GIA_NHOM":
            sheet.cell(row=row, column=3, value=111000)
        if sheet.cell(row=row, column=1).value == "VAT_PCT":
            sheet.cell(row=row, column=3, value=10)
    workbook.save(local)

    payload = {"file_base64": "data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,"
                              + base64.b64encode(local.read_bytes()).decode("ascii")}
    response = client.post("/api/pricing/import", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["updated"]["aluminum_price_per_kg"] == 111000
    assert body["updated"]["vat_percent"] == 10

    pricing = client.get("/api/pricing").json()
    assert pricing["aluminum_price_per_kg"] == 111000
    assert pricing["vat_percent"] == 10


def test_catalog_roundtrip(client):
    catalog = client.get("/api/catalog").json()
    assert "cuong_luc_8" in catalog["glass"]
    res = client.put("/api/catalog", json=catalog)
    assert res.status_code == 200
    assert client.put("/api/catalog", json={"glass": {}}).status_code == 422


def test_prompt_endpoint(client):
    res = client.get("/api/prompt")
    assert res.status_code == 200
    assert "JSON" in res.text
