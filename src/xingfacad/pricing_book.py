"""Bảng chi phí giá thành đầu vào & giá bán đến tay khách (theo nhóm sản phẩm)."""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from . import catalog, paths
from .layout import build_item
from .models import GlassSpec, ItemResult, ItemSpec, PanelSpec
from .pricing import ProjectCost, round_money

COST_LABELS: list[tuple[str, str]] = [
    ("alum", "Nhôm thanh"),
    ("glass", "Kính"),
    ("hardware", "Phụ kiện (bản lề, khóa, tay nắm…)"),
    ("consumables", "Vật tư phụ (gioăng, keo, vít)"),
    ("labor_production", "Nhân công sản xuất"),
    ("labor_install", "Nhân công lắp đặt"),
    ("factory", "Chi phí xưởng / khấu hao"),
    ("packaging", "Đóng gói"),
    ("transport", "Vận chuyển"),
]

CONSUMABLE_KEYS = {"gasket", "silicone", "screw", "tube", "sealant"}


class NormSpec(BaseModel):
    """Cửa mẫu dùng để suy ra định mức /m² và quy ra giá/bộ."""

    model_config = ConfigDict(extra="allow")

    item_type: str = "casement"
    width_mm: float = 1800
    height_mm: float = 2200
    system: str = "XF65"
    panels: int = 2
    glass_key: str = "cuong_luc_8"
    hinge_type: str | None = "hinge_3d"
    hinge_count: int | None = 3
    lock_type: str | None = "lock_single"


class HardwareCostItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    key: str
    qty_per_set: float = 0
    price: float = 0


class GroupCost(BaseModel):
    model_config = ConfigDict(extra="allow")

    alum_kg_per_m2: float = 7.65
    alum_price_per_kg: float = 95000
    alum_waste_percent: float = 3
    glass_m2_per_m2: float = 0.71
    glass_price_per_m2: float = 420000
    glass_waste_percent: float = 5
    hardware_items: list[HardwareCostItem] = Field(default_factory=list)
    hardware_waste_percent: float = 0
    consumables_per_m2: float = 35000
    labor_production_per_m2: float = 120000
    labor_install_per_m2: float = 80000
    factory_per_m2: float = 60000
    packaging_per_m2: float = 15000
    transport_per_m2: float = 25000
    warranty_percent: float = 1.5
    management_percent: float = 3
    finance_percent: float = 0.5


class ProductGroup(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: str
    name: str
    item_types: list[str] = Field(default_factory=list)
    norm: NormSpec = Field(default_factory=NormSpec)
    cost: GroupCost = Field(default_factory=GroupCost)

    @property
    def norm_area_m2(self) -> float:
        return max(self.norm.width_mm * self.norm.height_mm / 1_000_000, 0.01)


class PriceLevel(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: str
    name: str
    margin_percent: float = 20
    discount_percent: float = 0
    include_install: bool = True
    show_in_quote: bool = True


class BookSettings(BaseModel):
    model_config = ConfigDict(extra="allow")

    vat_percent: float = 8
    round_to: float = 1000
    show_inc_vat: bool = True


class PricingBook(BaseModel):
    model_config = ConfigDict(extra="allow")

    currency: str = "VND"
    effective_date: str = ""
    settings: BookSettings = Field(default_factory=BookSettings)
    groups: list[ProductGroup] = Field(default_factory=list)
    levels: list[PriceLevel] = Field(default_factory=list)
    note: str = ""


class CostLine(BaseModel):
    key: str
    label: str
    amount_per_m2: float


class LevelPrice(BaseModel):
    code: str
    name: str
    margin_percent: float
    discount_percent: float
    include_install: bool
    show_in_quote: bool
    base_per_m2: float
    listed_per_m2: float
    price_ex_vat_m2: float
    price_inc_vat_m2: float
    price_ex_vat_set: float
    price_inc_vat_set: float


class GroupResult(BaseModel):
    code: str
    name: str
    item_types: list[str]
    norm_width_mm: float
    norm_height_mm: float
    norm_system: str
    norm_area_m2: float
    lines: list[CostLine]
    direct_per_m2: float
    warranty_per_m2: float
    management_per_m2: float
    finance_per_m2: float
    cost_per_m2: float
    cost_per_set: float
    levels: list[LevelPrice]


class BookResult(BaseModel):
    currency: str
    effective_date: str
    vat_percent: float
    round_to: float
    show_inc_vat: bool
    groups: list[GroupResult]
    note: str = ""


def book_path() -> Path:
    return paths.config_dir() / "pricing_book.json"


def load_book() -> PricingBook:
    path = book_path()
    if not path.exists():
        return PricingBook()
    return PricingBook.model_validate(json.loads(path.read_text(encoding="utf-8")))


def save_book(book: PricingBook) -> Path:
    path = book_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(book.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return path


def compute_group(group: ProductGroup, book: PricingBook) -> GroupResult:
    cost = group.cost
    area = group.norm_area_m2
    hardware_per_set = sum(item.qty_per_set * item.price for item in cost.hardware_items) * (
        1 + cost.hardware_waste_percent / 100
    )
    amounts = {
        "alum": cost.alum_kg_per_m2 * cost.alum_price_per_kg * (1 + cost.alum_waste_percent / 100),
        "glass": cost.glass_m2_per_m2 * cost.glass_price_per_m2 * (1 + cost.glass_waste_percent / 100),
        "hardware": hardware_per_set / area,
        "consumables": cost.consumables_per_m2,
        "labor_production": cost.labor_production_per_m2,
        "labor_install": cost.labor_install_per_m2,
        "factory": cost.factory_per_m2,
        "packaging": cost.packaging_per_m2,
        "transport": cost.transport_per_m2,
    }
    lines = [
        CostLine(key=key, label=label, amount_per_m2=round(amounts[key], 0)) for key, label in COST_LABELS
    ]
    direct = sum(amounts.values())
    warranty = direct * cost.warranty_percent / 100
    management = direct * cost.management_percent / 100
    finance = direct * cost.finance_percent / 100
    full_cost = direct + warranty + management + finance

    step = book.settings.round_to
    levels: list[LevelPrice] = []
    for level in book.levels:
        base = full_cost - (0 if level.include_install else cost.labor_install_per_m2)
        listed = base * (1 + level.margin_percent / 100)
        after_discount = listed * (1 - level.discount_percent / 100)
        price_ex = round_money(after_discount, step)
        price_inc = round_money(price_ex * (1 + book.settings.vat_percent / 100), step)
        levels.append(
            LevelPrice(
                code=level.code,
                name=level.name,
                margin_percent=level.margin_percent,
                discount_percent=level.discount_percent,
                include_install=level.include_install,
                show_in_quote=level.show_in_quote,
                base_per_m2=round(base, 0),
                listed_per_m2=round(listed, 0),
                price_ex_vat_m2=price_ex,
                price_inc_vat_m2=price_inc,
                price_ex_vat_set=round_money(price_ex * area, step),
                price_inc_vat_set=round_money(price_inc * area, step),
            )
        )

    return GroupResult(
        code=group.code,
        name=group.name,
        item_types=group.item_types,
        norm_width_mm=group.norm.width_mm,
        norm_height_mm=group.norm.height_mm,
        norm_system=group.norm.system,
        norm_area_m2=round(area, 3),
        lines=lines,
        direct_per_m2=round(direct, 0),
        warranty_per_m2=round(warranty, 0),
        management_per_m2=round(management, 0),
        finance_per_m2=round(finance, 0),
        cost_per_m2=round(full_cost, 0),
        cost_per_set=round_money(full_cost * area, step),
        levels=levels,
    )


def compute_book(book: PricingBook) -> BookResult:
    return BookResult(
        currency=book.currency,
        effective_date=book.effective_date,
        vat_percent=book.settings.vat_percent,
        round_to=book.settings.round_to,
        show_inc_vat=book.settings.show_inc_vat,
        groups=[compute_group(group, book) for group in book.groups],
        note=book.note,
    )


def match_group(book: PricingBook, item_type: str) -> ProductGroup | None:
    for group in book.groups:
        if item_type in group.item_types:
            return group
    return None


def _norm_item(group: ProductGroup) -> ItemSpec:
    norm = group.norm
    count = max(1, int(norm.panels))
    if norm.item_type == "fixed":
        panels = [PanelSpec(kind="fixed", open="none", dir="none", ratio=1) for _ in range(count)]
    elif norm.item_type in ("sliding", "door_sliding"):
        panels = [PanelSpec(kind="sash", open="slide", dir="none", ratio=1) for _ in range(count)]
    else:
        panels = [
            PanelSpec(kind="sash", open="out", dir="left" if index % 2 == 0 else "right", ratio=1)
            for index in range(count)
        ]
    item = ItemSpec(
        tag="MAU",
        type=norm.item_type,
        width_mm=norm.width_mm,
        height_mm=norm.height_mm,
        sill_mm=900,
        system=norm.system,
        glass=catalog.glass_spec(norm.glass_key),
        panels=panels,
        transoms=[],
        notes="Cửa mẫu để lấy định mức",
    )
    item.hinge_type = norm.hinge_type
    item.hinge_count = norm.hinge_count
    item.lock_type = norm.lock_type
    return item


def derive_group_cost(book: PricingBook, code: str) -> GroupCost:
    """Tính lại định mức nhôm/kính/phụ kiện /m² từ BOM của cửa mẫu."""
    group = next((entry for entry in book.groups if entry.code.upper() == code.upper()), None)
    if group is None:
        raise KeyError(f"Không tìm thấy nhóm {code}")
    system = catalog.load_system(group.norm.system)
    item = _norm_item(group)
    result = build_item(item, system, item.glass)
    area = max(item.area_m2, 0.01)
    pricing = catalog.load_pricing()
    cost = group.cost.model_copy(deep=True)
    cost.alum_kg_per_m2 = round(result.alum_kg / area, 2)
    cost.alum_price_per_kg = float(pricing.get("aluminum_price_per_kg", cost.alum_price_per_kg))
    cost.alum_waste_percent = float(pricing.get("waste_percent", cost.alum_waste_percent))
    cost.glass_m2_per_m2 = round(result.glass_m2 / area, 3)
    glass_price = next((piece.price_per_m2 for piece in result.glass if piece.price_per_m2), None)
    if glass_price:
        cost.glass_price_per_m2 = float(glass_price)
    cost.hardware_items = [
        HardwareCostItem(key=line.key, qty_per_set=round(line.qty, 2), price=line.price)
        for line in result.hardware
        if line.key not in CONSUMABLE_KEYS
    ]
    cost.consumables_per_m2 = float(pricing.get("consumables_per_m2", cost.consumables_per_m2))
    return cost


def quote_prices(
    results: list[ItemResult], book: PricingBook, level_code: str
) -> dict[str, dict[str, float | str]]:
    """Giá bán theo bảng giá (chưa VAT) cho từng hạng mục."""
    computed = {group.code: group for group in compute_book(book).groups}
    prices: dict[str, dict[str, float | str]] = {}
    for result in results:
        group = match_group(book, result.item.type)
        if group is None:
            continue
        group_result = computed.get(group.code)
        if group_result is None or not group_result.levels:
            continue
        level = next((entry for entry in group_result.levels if entry.code == level_code), group_result.levels[0])
        quantity_area = result.item.area_m2 * result.item.qty
        price = round_money(level.price_ex_vat_m2 * quantity_area, book.settings.round_to)
        prices[result.item.tag] = {
            "group": group.code,
            "level": level.code,
            "price": price,
            "unit_price_m2": round(price / quantity_area, 0) if quantity_area else 0.0,
        }
    return prices


def apply_to_cost(
    cost: ProjectCost, results: list[ItemResult], book: PricingBook, level_code: str
) -> ProjectCost:
    """Ghi đè giá bán từ bảng giá ban hành (giữ nguyên giá vốn BOM để đối chiếu)."""
    prices = quote_prices(results, book, level_code)
    total = 0.0
    for item_cost in cost.items:
        info = prices.get(item_cost.tag)
        if info is None:
            total += item_cost.price
            continue
        item_cost.price = float(info["price"])
        item_cost.unit_price_m2 = float(info["unit_price_m2"])
        item_cost.profit = round(item_cost.price - item_cost.cost_total, 0)
        total += item_cost.price
    cost.price = round(total, 0)
    cost.vat_percent = book.settings.vat_percent
    cost.vat = round_money(cost.price * cost.vat_percent / 100, book.settings.round_to)
    cost.price_with_vat = round(cost.price + cost.vat, 0)
    cost.avg_unit_price_m2 = round(cost.price / cost.area_m2, 0) if cost.area_m2 else 0.0
    return cost
