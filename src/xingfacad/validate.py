"""Kiểm tra dữ liệu trước khi xuất bản vẽ / báo giá."""
from __future__ import annotations

from pydantic import BaseModel

from .models import ITEM_TYPE_LABELS, ProjectSpec, SystemDef

ITEM_MIN_MM = 300.0
ITEM_MAX_MM = 6000.0
BIG_MM = 3500.0


class Issue(BaseModel):
    level: str = "warning"  # error | warning | info
    code: str = ""
    tag: str = ""
    message: str = ""


def validate_system(system: SystemDef) -> list[Issue]:
    issues: list[Issue] = []
    if not system.verified:
        issues.append(
            Issue(
                level="warning",
                code="system.unverified",
                tag=system.code,
                message=f"Hệ {system.code}: số liệu chưa được xác nhận từ catalogue nhà cung cấp",
            )
        )
    frame = system.profiles["frame"]
    if frame.width_mm >= frame.depth_mm and system.kind != "sliding":
        issues.append(
            Issue(
                level="warning",
                code="system.frame_ratio",
                tag=system.code,
                message=f"Hệ {system.code}: mặt cắt khung {frame.width_mm}mm >= chiều sâu {frame.depth_mm}mm",
            )
        )
    for key, profile in system.profiles.items():
        if profile.wall_mm < 1.0:
            issues.append(
                Issue(
                    level="error",
                    code="profile.wall",
                    tag=f"{system.code}/{key}",
                    message=f"{profile.code}: vách {profile.wall_mm}mm quá mỏng (< 1.0mm)",
                )
            )
        if profile.kg_per_m <= 0.2:
            issues.append(
                Issue(
                    level="warning",
                    code="profile.kg",
                    tag=f"{system.code}/{key}",
                    message=f"{profile.code}: khối lượng {profile.kg_per_m} kg/m có vẻ không đúng",
                )
            )
    if "track_top" not in system.profiles and system.kind == "sliding":
        issues.append(
            Issue(
                level="warning",
                code="system.sliding_track",
                tag=system.code,
                message=f"Hệ {system.code} là cửa lùa nhưng thiếu profile 'track_top'/'track_bottom'",
            )
        )
    return issues


def validate_item_base(item, system: SystemDef) -> list[Issue]:
    issues: list[Issue] = []
    if item.width_mm < ITEM_MIN_MM or item.height_mm < ITEM_MIN_MM:
        issues.append(
            Issue(
                level="error",
                code="item.too_small",
                tag=item.tag,
                message=f"{item.tag}: kích thước {item.width_mm:.0f}x{item.height_mm:.0f} nhỏ hơn {ITEM_MIN_MM:.0f}mm",
            )
        )
    if item.width_mm > ITEM_MAX_MM or item.height_mm > ITEM_MAX_MM:
        issues.append(
            Issue(
                level="warning",
                code="item.too_large",
                tag=item.tag,
                message=f"{item.tag}: kích thước lớn hơn {ITEM_MAX_MM:.0f}mm, cần kiểm tra kết cấu",
            )
        )
    if max(item.width_mm, item.height_mm) > BIG_MM:
        issues.append(
            Issue(
                level="warning",
                code="item.big",
                tag=item.tag,
                message=f"{item.tag}: cạnh > {BIG_MM:.0f}mm, nên chia thêm đố để đảm bảo độ cứng",
            )
        )
    if item.type not in ITEM_TYPE_LABELS:
        issues.append(
            Issue(level="error", code="item.type", tag=item.tag, message=f"{item.tag}: loại cửa không hợp lệ")
        )
    if item.panels:
        if sum(panel.ratio for panel in item.panels) <= 0:
            issues.append(
                Issue(level="error", code="item.ratio", tag=item.tag, message=f"{item.tag}: tổng tỷ lệ chia cánh phải > 0")
            )
        if item.type == "fixed" and any(panel.kind == "sash" for panel in item.panels):
            issues.append(
                Issue(
                    level="warning",
                    code="item.fixed_sash",
                    tag=item.tag,
                    message=f"{item.tag}: cửa cố định nhưng có cánh mở",
                )
            )
    for transom in item.transoms:
        limit = item.height_mm if transom.orientation == "h" else item.width_mm
        if transom.at_mm >= limit:
            issues.append(
                Issue(
                    level="error",
                    code="item.transom",
                    tag=item.tag,
                    message=f"{item.tag}: đố tại {transom.at_mm:.0f}mm vượt kích thước {limit:.0f}mm",
                )
            )
        if system is not None and transom.profile not in system.profiles and transom.profile != "mullion":
            issues.append(
                Issue(
                    level="warning",
                    code="item.transom_profile",
                    tag=item.tag,
                    message=f"{item.tag}: hệ {system.code} không có profile '{transom.profile}', dùng đố mặc định",
                )
            )
    if system is not None:
        groove = min(
            system.profiles["frame"].glass_groove_mm or 0,
            (system.profiles.get("sash") or system.profiles["frame"]).glass_groove_mm or 0,
        )
        if groove and item.glass.thickness_mm + 6 > groove:
            issues.append(
                Issue(
                    level="warning",
                    code="item.glass_groove",
                    tag=item.tag,
                    message=f"{item.tag}: kính {item.glass.thickness_mm}mm có thể không vừa rãnh {groove}mm",
                )
            )
    sliding_types = {"sliding", "door_sliding"}
    if item.type == "fixed" and (item.hinge_type or item.hinge_count):
        issues.append(
            Issue(
                level="warning",
                code="item.hinge_fixed",
                tag=item.tag,
                message=f"{item.tag}: cửa cố định nhưng có chọn bản lề",
            )
        )
    if item.type in sliding_types and (item.hinge_type or item.hinge_count):
        issues.append(
            Issue(
                level="warning",
                code="item.hinge_sliding",
                tag=item.tag,
                message=f"{item.tag}: cửa lùa dùng bánh xe, không dùng bản lề",
            )
        )
    if item.hinge_count == 0 and item.type not in sliding_types and item.type != "fixed":
        issues.append(
            Issue(
                level="warning",
                code="item.hinge_zero",
                tag=item.tag,
                message=f"{item.tag}: cánh mở nhưng chọn 0 bản lề",
            )
        )
    if item.hinge_count is not None and item.height_mm > 1800 and item.hinge_count < 3:
        issues.append(
            Issue(
                level="warning",
                code="item.hinge_low",
                tag=item.tag,
                message=f"{item.tag}: cánh cao {item.height_mm:.0f}mm nên dùng từ 3 bản lề trở lên",
            )
        )
    if item.needs_review:
        issues.append(
            Issue(
                level="warning",
                code="item.review",
                tag=item.tag,
                message=f"{item.tag}: cần kiểm tra lại ({', '.join(item.needs_review)})",
            )
        )
    return issues


def validate_project(project: ProjectSpec, systems: dict[str, SystemDef]) -> list[Issue]:
    issues: list[Issue] = []
    if not project.items:
        issues.append(Issue(level="error", code="project.empty", message="Dự án chưa có hạng mục cửa nào"))
        return issues

    for system in systems.values():
        for issue in validate_system(system):
            if issue.code != "system.unverified":
                issues.append(issue)

    for item in project.items:
        system_code = (item.system or project.defaults.system or "").upper()
        system = systems.get(system_code)
        if system is None:
            issues.append(
                Issue(
                    level="error",
                    code="item.system_missing",
                    tag=item.tag,
                    message=f"{item.tag}: không tìm thấy hệ nhôm '{system_code}'",
                )
            )
            continue
        issues.extend(validate_item_base(item, system))
    return issues


def has_errors(issues: list[Issue]) -> bool:
    return any(issue.level == "error" for issue in issues)
