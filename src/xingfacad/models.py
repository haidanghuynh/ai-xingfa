"""Model dữ liệu (pydantic v2): dự án, hệ nhôm Xingfa, kết quả bóc tách."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ItemType = Literal[
    "casement",
    "sliding",
    "fixed",
    "awning",
    "door_swing",
    "door_sliding",
    "tilt_turn",
]
JointType = Literal["miter45", "butt90"]
PanelKind = Literal["sash", "fixed"]

ITEM_TYPE_LABELS: dict[str, str] = {
    "casement": "Cửa sổ mở quay",
    "sliding": "Cửa sổ lùa",
    "fixed": "Cửa sổ cố định",
    "awning": "Cửa sổ mở hất",
    "door_swing": "Cửa đi mở quay",
    "door_sliding": "Cửa đi lùa",
    "tilt_turn": "Cửa quay - hất",
}

PANEL_KINDS: dict[str, str] = {"sash": "Cánh mở", "fixed": "Cố định"}

PROFILE_KEYS: dict[str, str] = {
    "frame": "Khung bao",
    "sash": "Cánh cửa",
    "mullion": "Đố đứng",
    "transom": "Đố ngang",
    "track_top": "Ray trên",
    "track_bottom": "Ray dưới",
    "bead": "Nẹp kính",
}


class ProfileDef(BaseModel):
    """Một thanh nhôm trong hệ (mô hình envelope: đúng width/depth/khối lượng)."""

    model_config = ConfigDict(extra="allow")

    key: str
    code: str
    name: str = ""
    width_mm: float = Field(gt=0, description="Mặt cắt nhìn thấy (mm)")
    depth_mm: float = Field(gt=0, description="Chiều sâu profile (mm)")
    wall_mm: float = Field(default=1.4, gt=0)
    kg_per_m: float = Field(gt=0)
    glass_groove_mm: float = 24
    price_per_kg: float | None = None
    color: str = ""
    note: str = ""

    @field_validator("key", "code")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError("không được để trống")
        return value


class Rules(BaseModel):
    """Thông số công nghệ của hệ nhôm."""

    model_config = ConfigDict(extra="allow")

    gap_frame_sash_mm: float = 6
    sash_overlap_mm: float = 0
    glass_rebate_mm: float = 12
    glass_clearance_mm: float = 4
    min_panel_width_mm: float = 350
    max_panel_area_m2: float = 2.2
    track_offset_mm: float = 30
    sash_inset_mm: float | None = None
    note: str = ""


class SystemDef(BaseModel):
    """Hệ nhôm Xingfa (dữ liệu người dùng nhập/sửa trên UI)."""

    model_config = ConfigDict(extra="allow")

    code: str
    name: str
    brand: str = "Xingfa"
    kind: str = "casement"
    joint: JointType = "miter45"
    bar_length_mm: float = Field(default=6500, gt=0)
    kerf_mm: float = Field(default=5, ge=0)
    end_trim_mm: float = Field(default=30, ge=0)
    verified: bool = False
    source: str = ""
    notes: str = ""
    rules: Rules = Field(default_factory=Rules)
    profiles: dict[str, ProfileDef] = Field(default_factory=dict)

    @field_validator("code")
    @classmethod
    def _code_ok(cls, value: str) -> str:
        value = (value or "").strip().upper()
        if not value:
            raise ValueError("mã hệ không được để trống")
        if any(ch.isspace() for ch in value):
            raise ValueError("mã hệ không được có khoảng trắng")
        return value

    @model_validator(mode="after")
    def _check_profiles(self) -> "SystemDef":
        if not self.profiles:
            raise ValueError("hệ nhôm phải có ít nhất 1 profile")
        for key, profile in self.profiles.items():
            profile.key = key
        if "frame" not in self.profiles:
            raise ValueError("thiếu profile 'frame' (khung bao)")
        if "sash" not in self.profiles:
            raise ValueError("thiếu profile 'sash' (cánh cửa)")
        return self

    def profile(self, key: str) -> ProfileDef:
        """Lấy profile theo key, fallback hợp lý nếu hệ không khai báo."""
        if key in self.profiles:
            return self.profiles[key]
        if key in ("mullion", "transom", "bead") and "frame" in self.profiles:
            return self.profiles["frame"]
        if key == "sash" and "frame" in self.profiles:
            return self.profiles["frame"]
        raise KeyError(f"Hệ {self.code} không có profile '{key}'")


class GlassSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    key: str = "cuong_luc_8"
    name: str = "Kính cường lực 8mm"
    thickness_mm: float = Field(default=8, gt=0)
    price_per_m2: float | None = None


# --------------------------------------------------------------------------- #
# Cấu hình cửa (người dùng nhập / AI trích xuất từ ảnh)
# --------------------------------------------------------------------------- #
class PanelSpec(BaseModel):
    """Một cột cánh của cửa (chia theo chiều rộng)."""

    model_config = ConfigDict(extra="allow")

    kind: PanelKind = "sash"
    open: Literal["in", "out", "slide", "none"] = "out"
    dir: Literal["left", "right", "up", "down", "none"] = "left"
    ratio: float = Field(default=1, gt=0, description="Tỷ lệ chia chiều rộng")
    note: str = ""


class TransomSpec(BaseModel):
    """Đố ngang (hoặc đố đứng) chia ô kính."""

    model_config = ConfigDict(extra="allow")

    orientation: Literal["h", "v"] = "h"
    at_mm: float = Field(gt=0, description="Cách mép ngoài phía trên (h) hoặc bên trái (v)")
    profile: str = "transom"
    band_above: PanelKind | None = None
    band_below: PanelKind | None = None
    note: str = ""


class ItemSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    tag: str
    room: str = ""
    qty: int = Field(default=1, ge=1)
    type: ItemType = "casement"
    width_mm: float = Field(gt=100, le=12000)
    height_mm: float = Field(gt=100, le=12000)
    sill_mm: float = Field(default=900, ge=0)
    system: str | None = None
    glass: GlassSpec = Field(default_factory=GlassSpec)
    color: str = ""
    hardware: str = ""
    hinge_type: str | None = Field(default=None, description="Mã loại bản lề trong catalogue")
    hinge_count: int | None = Field(default=None, ge=0, le=8, description="Số bản lề mỗi cánh")
    lock_type: str | None = Field(default=None, description="Mã loại khóa trong catalogue")
    panels: list[PanelSpec] = Field(default_factory=list)
    transoms: list[TransomSpec] = Field(default_factory=list)
    notes: str = ""
    source: str = "manual"
    confidence: float = 1.0
    needs_review: list[str] = Field(default_factory=list)

    @field_validator("tag")
    @classmethod
    def _tag_ok(cls, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError("mã cửa (tag) không được để trống")
        return value

    @property
    def area_m2(self) -> float:
        return self.width_mm * self.height_mm / 1_000_000

    @property
    def size_label(self) -> str:
        return f"{self.width_mm:,.0f} x {self.height_mm:,.0f}"

    @property
    def type_label(self) -> str:
        return ITEM_TYPE_LABELS.get(self.type, self.type)


class DefaultsSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    system: str = "XF65"
    glass: GlassSpec = Field(default_factory=GlassSpec)
    color: str = ""
    hardware: str = "Kinlong"


class ProjectInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: str = "DU-AN-001"
    name: str = ""
    customer: str = ""
    address: str = ""
    request_org: str = ""
    request_contact: str = ""
    request_phone: str = ""
    quoted_by: str = ""
    quoted_by_phone: str = ""
    date: str = Field(default_factory=lambda: date.today().isoformat())
    currency: str = "VND"
    note: str = ""

    @field_validator("code")
    @classmethod
    def _code_ok(cls, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError("mã dự án không được để trống")
        return value


class ProjectSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    project: ProjectInfo = Field(default_factory=ProjectInfo)
    defaults: DefaultsSpec = Field(default_factory=DefaultsSpec)
    items: list[ItemSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_tags(self) -> "ProjectSpec":
        seen: set[str] = set()
        for item in self.items:
            if item.tag in seen:
                raise ValueError(f"mã cửa bị trùng: {item.tag}")
            seen.add(item.tag)
        return self

    @property
    def total_area_m2(self) -> float:
        return sum(item.area_m2 * item.qty for item in self.items)


# --------------------------------------------------------------------------- #
# Kết quả bóc tách
# --------------------------------------------------------------------------- #
class CutPiece(BaseModel):
    tag: str
    group: str
    profile_key: str
    profile_code: str
    profile_name: str
    length_mm: float
    qty: int = 1
    cut_a: str = "45"
    cut_b: str = "45"
    kg_per_m: float = 0.0
    note: str = ""
    source_ends: str = ""

    @property
    def total_length_mm(self) -> float:
        return self.length_mm * self.qty

    @property
    def weight_kg(self) -> float:
        return self.total_length_mm / 1000 * self.kg_per_m


class GlassPiece(BaseModel):
    tag: str
    key: str
    name: str
    thickness_mm: float
    width_mm: float
    height_mm: float
    qty: int = 1
    note: str = ""
    price_per_m2: float = 0.0

    @property
    def area_m2(self) -> float:
        return self.width_mm * self.height_mm / 1_000_000 * self.qty

    @property
    def amount(self) -> float:
        return self.area_m2 * self.price_per_m2


class HardwareLine(BaseModel):
    tag: str
    key: str
    name: str
    unit: str
    qty: float
    price: float = 0.0

    @property
    def amount(self) -> float:
        return self.qty * self.price


class Bar3D(BaseModel):
    """Thanh nhôm trong không gian: polygon tiết diện (mặt phẳng XZ), ép theo trục Y."""

    group: str
    profile_code: str
    polygon: list[list[float]]
    y0: float
    y1: float
    label: str = ""


class Pane3D(BaseModel):
    """Tấm kính (hộp chữ nhật) đặt tại góc (x, y, z)."""

    x: float
    y: float
    z: float
    w: float
    h: float
    t: float
    label: str = "glass"


class Hardware3D(BaseModel):
    """Phụ kiện dạng hộp (bản lề, tay nắm/khóa, bánh xe) để hiển thị 3D."""

    kind: str  # hinge | lock | handle | wheel
    x: float
    y: float
    z: float
    w: float
    h: float
    d: float
    label: str = ""


class ItemResult(BaseModel):
    item: ItemSpec
    system_code: str
    system_name: str
    joint: str = "miter45"
    width_mm: float
    height_mm: float
    cols: int = 1
    leaves: int = 0
    cells: int = 0
    pieces: list[CutPiece] = Field(default_factory=list)
    glass: list[GlassPiece] = Field(default_factory=list)
    hardware: list[HardwareLine] = Field(default_factory=list)
    bars3d: list[Bar3D] = Field(default_factory=list)
    panes3d: list[Pane3D] = Field(default_factory=list)
    hardware3d: list[Hardware3D] = Field(default_factory=list)
    leaf_rects: list[list[float]] = Field(default_factory=list)
    leaf_dirs: list[str] = Field(default_factory=list)
    cell_rects: list[list[float]] = Field(default_factory=list)
    gasket_m: float = 0.0
    warnings: list[str] = Field(default_factory=list)

    @property
    def alum_kg(self) -> float:
        return sum(piece.weight_kg for piece in self.pieces)

    @property
    def alum_length_m(self) -> float:
        return sum(piece.total_length_mm for piece in self.pieces) / 1000

    @property
    def glass_m2(self) -> float:
        return sum(piece.area_m2 for piece in self.glass)

    @property
    def hardware_amount(self) -> float:
        return sum(line.amount for line in self.hardware)

    @property
    def area_m2(self) -> float:
        return self.item.area_m2 * self.item.qty

    @property
    def alum_kg_total(self) -> float:
        return self.alum_kg * self.item.qty

    @property
    def glass_m2_total(self) -> float:
        return self.glass_m2 * self.item.qty

    @property
    def hardware_amount_total(self) -> float:
        return self.hardware_amount * self.item.qty
