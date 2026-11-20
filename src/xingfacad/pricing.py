"""Tính giá vốn / giá bán cho từng hạng mục và cho toàn dự án."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .models import ItemResult


def round_money(value: float, step: float) -> float:
    if not step:
        return round(value, 0)
    return round(value / step) * step


class ItemCost(BaseModel):
    tag: str
    qty: int
    area_m2: float
    alum_kg: float
    alum_cost: float
    glass_m2: float
    glass_cost: float
    hardware_cost: float
    material_cost: float
    labor_cost: float
    consumables_cost: float
    transport_cost: float
    cost_total: float
    profit: float
    price: float
    unit_price_m2: float


class ProjectCost(BaseModel):
    currency: str = "VND"
    items: list[ItemCost] = Field(default_factory=list)
    area_m2: float = 0.0
    alum_kg: float = 0.0
    glass_m2: float = 0.0
    alum_cost: float = 0.0
    glass_cost: float = 0.0
    hardware_cost: float = 0.0
    material_cost: float = 0.0
    labor_cost: float = 0.0
    consumables_cost: float = 0.0
    transport_cost: float = 0.0
    cost_total: float = 0.0
    profit: float = 0.0
    price: float = 0.0
    vat_percent: float = 0.0
    vat: float = 0.0
    price_with_vat: float = 0.0
    avg_unit_price_m2: float = 0.0


def compute_item_cost(result: ItemResult, pricing: dict) -> ItemCost:
    qty = result.item.qty
    area = result.area_m2
    waste = 1 + float(pricing.get("waste_percent", 0)) / 100
    alum_kg = result.alum_kg_total
    alum_cost = alum_kg * float(pricing.get("aluminum_price_per_kg", 0)) * waste
    glass_cost = sum(piece.amount for piece in result.glass) * qty
    hardware_cost = result.hardware_amount_total
    material = alum_cost + glass_cost + hardware_cost
    labor = material * float(pricing.get("labor_percent_of_material", 0)) / 100
    consumables = area * float(pricing.get("consumables_per_m2", 0))
    transport = float(pricing.get("transport_per_item", 0)) * qty
    cost_total = material + labor + consumables + transport
    profit = cost_total * float(pricing.get("profit_percent", 0)) / 100
    price = round_money(cost_total + profit, float(pricing.get("round_to", 1000)))
    return ItemCost(
        tag=result.item.tag,
        qty=qty,
        area_m2=round(area, 3),
        alum_kg=round(alum_kg, 2),
        alum_cost=round(alum_cost, 0),
        glass_m2=round(result.glass_m2_total, 3),
        glass_cost=round(glass_cost, 0),
        hardware_cost=round(hardware_cost, 0),
        material_cost=round(material, 0),
        labor_cost=round(labor, 0),
        consumables_cost=round(consumables, 0),
        transport_cost=round(transport, 0),
        cost_total=round(cost_total, 0),
        profit=round(price - cost_total, 0),
        price=round(price, 0),
        unit_price_m2=round(price / area, 0) if area else 0.0,
    )


def compute_project_cost(results: list[ItemResult], pricing: dict) -> ProjectCost:
    items = [compute_item_cost(result, pricing) for result in results]
    cost = ProjectCost(
        currency=str(pricing.get("currency", "VND")),
        items=items,
        area_m2=round(sum(item.area_m2 for item in items), 3),
        alum_kg=round(sum(item.alum_kg for item in items), 2),
        glass_m2=round(sum(item.glass_m2 for item in items), 3),
        alum_cost=round(sum(item.alum_cost for item in items), 0),
        glass_cost=round(sum(item.glass_cost for item in items), 0),
        hardware_cost=round(sum(item.hardware_cost for item in items), 0),
        material_cost=round(sum(item.material_cost for item in items), 0),
        labor_cost=round(sum(item.labor_cost for item in items), 0),
        consumables_cost=round(sum(item.consumables_cost for item in items), 0),
        transport_cost=round(sum(item.transport_cost for item in items), 0),
        cost_total=round(sum(item.cost_total for item in items), 0),
        price=round(sum(item.price for item in items), 0),
    )
    cost.profit = round(cost.price - cost.cost_total, 0)
    cost.vat_percent = float(pricing.get("vat_percent", 0))
    cost.vat = round_money(cost.price * cost.vat_percent / 100, float(pricing.get("round_to", 1000)))
    cost.price_with_vat = round(cost.price + cost.vat, 0)
    cost.avg_unit_price_m2 = round(cost.price / cost.area_m2, 0) if cost.area_m2 else 0.0
    return cost
