"""Kiểm tra bảng chi phí giá thành & giá bán (dev tool)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from xingfacad import pricing_book as pb  # noqa: E402

book = pb.load_book()
result = pb.compute_book(book)
print(f"VAT {result.vat_percent}% | làm tròn {result.round_to}")
for group in result.groups:
    print(
        f"{group.code:5} {group.name:24} mẫu {group.norm_width_mm:.0f}x{group.norm_height_mm:.0f} "
        f"({group.norm_area_m2} m²) | giá vốn {group.cost_per_m2:,.0f} đ/m² | {group.cost_per_set:,.0f} đ/bộ"
    )
    for level in group.levels:
        print(
            f"      {level.code:4} {level.name:14} lãi {level.margin_percent:>4.0f}% CK {level.discount_percent:>4.0f}%"
            f" | chưa VAT {level.price_ex_vat_m2:>12,.0f} | đã VAT {level.price_inc_vat_m2:>12,.0f}"
            f" | bộ {level.price_ex_vat_set:>12,.0f}"
        )

for code in ("CSMQ", "CD"):
    derived = pb.derive_group_cost(book, code)
    print(
        f"derive {code}: nhôm {derived.alum_kg_per_m2} kg/m², kính {derived.glass_m2_per_m2} m²/m², "
        f"phụ kiện {[(item.key, item.qty_per_set) for item in derived.hardware_items]}"
    )
