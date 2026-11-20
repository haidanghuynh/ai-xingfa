"""Test model dữ liệu và catalogue."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from xingfacad import catalog
from xingfacad.models import ItemSpec, ProfileDef, ProjectSpec, SystemDef


def test_duplicate_tags_rejected():
    with pytest.raises(ValidationError):
        ProjectSpec.model_validate(
            {
                "project": {"code": "P1"},
                "items": [
                    {"tag": "C1", "type": "fixed", "width_mm": 1000, "height_mm": 1000},
                    {"tag": "C1", "type": "fixed", "width_mm": 1000, "height_mm": 1000},
                ],
            }
        )


def test_system_requires_frame_and_sash():
    profile = ProfileDef(key="frame", code="X", width_mm=50, depth_mm=50, kg_per_m=1)
    with pytest.raises(ValidationError):
        SystemDef(code="T1", name="test", profiles={"frame": profile})
    system = SystemDef(code="t2", name="test", profiles={"frame": profile, "sash": profile.model_copy()})
    assert system.code == "T2"
    assert system.profiles["frame"].key == "frame"


def test_profile_requires_positive_dims():
    with pytest.raises(ValidationError):
        ProfileDef(key="frame", code="X", width_mm=0, depth_mm=50, kg_per_m=1)


def test_item_requires_min_size():
    with pytest.raises(ValidationError):
        ItemSpec(tag="C1", width_mm=100, height_mm=1000)


def test_system_roundtrip(sandbox):
    system = catalog.load_system("xf65")
    system.code = "RT65"
    catalog.save_system(system)
    loaded = catalog.load_system("RT65")
    assert loaded.joint == system.joint
    assert loaded.profiles["sash"].kg_per_m == system.profiles["sash"].kg_per_m
    assert catalog.delete_system("RT65") is True
    with pytest.raises(KeyError):
        catalog.load_system("RT65")


def test_pricing_defaults(sandbox):
    pricing = catalog.load_pricing()
    assert pricing["aluminum_price_per_kg"] > 0
    assert pricing["vat_percent"] >= 0


def test_glass_resolution(sandbox):
    glass = catalog.glass_spec("cuong_luc_8")
    assert glass.thickness_mm == 8
    assert glass.price_per_m2 > 0
    resolved = catalog.resolve_glass(None, glass)
    assert resolved.name
    fallback = catalog.resolve_glass(None, None)
    assert fallback.key


def test_list_systems_sorted(sandbox):
    systems = catalog.list_systems()
    codes = [system.code for system in systems]
    assert codes == sorted(codes)
    assert all(system.profiles for system in systems)


def test_hardware_catalogue_options(sandbox):
    hardware = catalog.hardware_config()
    components = hardware["components"]
    assert {"hinge", "lock", "hinge_3d", "hinge_6in", "lock_multi2", "lock_multi3"} <= set(components)
    assert set(hardware["hinge_options"]) <= set(components)
    assert set(hardware["lock_options"]) <= set(components)
    for key in hardware["hinge_options"] + hardware["lock_options"]:
        assert components[key]["price"] > 0
