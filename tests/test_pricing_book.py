"""Test bảng chi phí giá thành & bảng giá đến tay khách."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from xingfacad.api import app
from xingfacad.pricing_book import (
    BookSettings,
    GroupCost,
    HardwareCostItem,
    NormSpec,
    PriceLevel,
    PricingBook,
    ProductGroup,
    compute_book,
    derive_group_cost,
    load_book,
)

ROOT = Path(__file__).resolve().parents[1]


def _book(
    margin: float = 20,
    discount: float = 0,
    vat: float = 10,
    round_to: float = 1,
    include_install: bool = True,
    labor_install: float = 0,
) -> PricingBook:
    return PricingBook(
        settings=BookSettings(vat_percent=vat, round_to=round_to),
        groups=[
            ProductGroup(
                code="T1",
                name="Nhóm test",
                item_types=["casement"],
                norm=NormSpec(width_mm=1000, height_mm=1000, panels=1, system="XF65"),
                cost=GroupCost(
                    alum_kg_per_m2=1,
                    alum_price_per_kg=1000,
                    alum_waste_percent=0,
                    glass_m2_per_m2=0,
                    glass_price_per_m2=0,
                    glass_waste_percent=0,
                    hardware_items=[HardwareCostItem(key="hinge_3d", qty_per_set=2, price=50000)],
                    hardware_waste_percent=0,
                    consumables_per_m2=0,
                    labor_production_per_m2=0,
                    labor_install_per_m2=labor_install,
                    factory_per_m2=0,
                    packaging_per_m2=0,
                    transport_per_m2=0,
                    warranty_percent=0,
                    management_percent=0,
                    finance_percent=0,
                ),
            )
        ],
        levels=[
            PriceLevel(
                code="le",
                name="Lẻ",
                margin_percent=margin,
                discount_percent=discount,
                include_install=include_install,
            )
        ],
    )


def test_cost_and_price_ladder():
    result = compute_book(_book())
    group = result.groups[0]
    assert group.norm_area_m2 == 1.0
    assert group.direct_per_m2 == 101000  # 1 kg × 1.000 + 2 bản lề × 50.000
    assert group.cost_per_m2 == 101000
    assert group.cost_per_set == 101000
    level = group.levels[0]
    assert level.base_per_m2 == 101000
    assert level.listed_per_m2 == pytest.approx(121200)
    assert level.price_ex_vat_m2 == pytest.approx(121200)
    assert level.price_inc_vat_m2 == pytest.approx(133320)
    assert level.price_ex_vat_set == pytest.approx(121200)


def test_discount_lowers_price():
    level = compute_book(_book(discount=10)).groups[0].levels[0]
    assert level.price_ex_vat_m2 == pytest.approx(109080)
    assert level.price_inc_vat_m2 == pytest.approx(119988)


def test_exclude_install_removes_labor_install():
    result = compute_book(_book(include_install=False, labor_install=100000))
    level = result.groups[0].levels[0]
    assert result.groups[0].cost_per_m2 == pytest.approx(201000)
    assert level.base_per_m2 == pytest.approx(101000)
    assert level.price_ex_vat_m2 == pytest.approx(121200)


def test_rounding_step():
    level = compute_book(_book(round_to=1000)).groups[0].levels[0]
    assert level.price_ex_vat_m2 == 121000
    assert level.price_inc_vat_m2 == 133000


def test_load_book_from_config(sandbox):
    book = load_book()
    assert len(book.groups) == 4
    assert len(book.levels) == 3
    for group in compute_book(book).groups:
        assert group.cost_per_m2 > 0
        assert group.levels
        for level in group.levels:
            assert level.price_ex_vat_m2 > group.cost_per_m2
            assert level.price_inc_vat_m2 > level.price_ex_vat_m2
            assert level.price_ex_vat_m2 % book.settings.round_to == 0


def test_derive_group_cost_from_bom(sandbox):
    cost = derive_group_cost(load_book(), "CSMQ")
    assert 7.0 < cost.alum_kg_per_m2 < 8.5
    assert 0.6 < cost.glass_m2_per_m2 < 0.8
    keys = {item.key: item.qty_per_set for item in cost.hardware_items}
    assert keys["hinge_3d"] == 6
    assert keys["lock_single"] == 2
    assert "gasket" not in keys


@pytest.fixture()
def client(sandbox):
    return TestClient(app)


@pytest.fixture()
def demo_payload():
    return json.loads((ROOT / "data/specs/demo_nha_a.json").read_text(encoding="utf-8"))


def test_api_pricing_book(client):
    res = client.get("/api/pricing-book")
    assert res.status_code == 200
    data = res.json()
    assert len(data["book"]["groups"]) == 4
    assert data["result"]["groups"][0]["cost_per_m2"] > 0


def test_api_save_pricing_book(client):
    book = client.get("/api/pricing-book").json()["book"]
    book["levels"][0]["margin_percent"] = 30
    res = client.put("/api/pricing-book", json=book)
    assert res.status_code == 200, res.text
    assert res.json()["result"]["groups"][0]["levels"][0]["margin_percent"] == 30

    bad = client.put("/api/pricing-book", json={**book, "groups": []})
    assert bad.status_code == 422


def test_api_derive_group(client):
    ok = client.post("/api/pricing-book/derive/CSMQ")
    assert ok.status_code == 200, ok.text
    assert ok.json()["cost"]["hardware_items"]
    assert client.post("/api/pricing-book/derive/KHONGCO").status_code == 404


def test_api_exports(client):
    xlsx = client.get("/api/pricing-book/export.xlsx")
    assert xlsx.status_code == 200
    assert len(xlsx.content) > 5000
    pdf = client.get("/api/pricing-book/export.pdf")
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"


def test_build_with_price_book(client, demo_payload):
    body = {"project": demo_payload, "with_3d": False, "with_drawings": False}
    bom = client.post("/api/build", json=body).json()
    booked = client.post("/api/build", json={**body, "pricing_mode": "book", "price_level": "le"}).json()
    assert booked["summary"]["pricing_mode"] == "book"
    assert booked["summary"]["price_level"] == "le"
    assert booked["summary"]["price"] != bom["summary"]["price"]
    assert abs(booked["summary"]["vat"] - booked["summary"]["price"] * 0.08) <= 1000
    units = {item["tag"]: item["unit_price_m2"] for item in booked["items"]}
    assert abs(units["F1"] - 1451111) < 1000
    assert abs(units["C1"] - 2113005) < 1000


def test_level_visibility_and_vat_toggle(sandbox, tmp_path):
    from openpyxl import load_workbook

    from xingfacad.price_book_export import build_book_pdf, build_book_xlsx

    book = load_book()
    book.settings.show_inc_vat = False
    for level in book.levels:
        level.show_in_quote = level.code != "dl1"
    result = compute_book(book)

    assert result.show_inc_vat is False
    assert [level.show_in_quote for level in result.groups[0].levels] == [True, False, True]

    target = build_book_xlsx(book, result, {"name": "Test"}, tmp_path / "book.xlsx")
    sheet = load_workbook(target)["02_GiaDenKhach"]
    headers = " ".join(str(cell.value) for cell in sheet[4] if cell.value)
    assert "Khách lẻ" in headers
    assert "Công trình" in headers
    assert "Đại lý cấp 1" not in headers
    assert "đã VAT" not in headers

    pdf_path = build_book_pdf(book, result, {"name": "Test"}, tmp_path / "book.pdf")
    assert pdf_path.stat().st_size > 1000
