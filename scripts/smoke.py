"""Smoke test nhanh: build đầy đủ 1 dự án demo (dev only)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from xingfacad.pipeline import build_project  # noqa: E402
from xingfacad.models import ProjectSpec  # noqa: E402

spec = ProjectSpec.model_validate(json.loads((ROOT / "data/specs/demo_nha_a.json").read_text(encoding="utf-8")))
outcome = build_project(spec, with_3d=True)

print("== SUMMARY ==")
for key, value in outcome.summary.items():
    if key == "freecad":
        print(f"{key:18}: ok={value.get('ok')} available={value.get('available')} msg={value.get('message', '')[:80]}")
    else:
        print(f"{key:18}: {value}")

print("\n== ITEMS ==")
for item in outcome.items:
    print(
        f"{item['tag']:>3} {item['type_label']:<20} {item['width_mm']:.0f}x{item['height_mm']:.0f}"
        f" kg={item['alum_kg']:.2f} glass={item['glass_m2']:.2f} price={item['price']:,.0f}"
        f" files={list(item['files'])}"
    )

print("\n== ISSUES ==")
for issue in outcome.issues:
    print(f"[{issue.level}] {issue.tag}: {issue.message}")

print("\n== ARTIFACTS ==")
for artifact in outcome.artifacts:
    print(f"{artifact.kind:7} {artifact.size:>9,} {artifact.name}")

print("\n== CUT PLAN ==")
for group in outcome.cut_plan:
    print(f"{group['profile_code']:10} bars={group['bars']:3} waste={group['waste_m']:6.2f}m ({group['waste_percent']}%)")
