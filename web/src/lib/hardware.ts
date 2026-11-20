import type { Catalog, ItemSpec } from '@/types/api'

export const DEFAULT_HINGES_PER_LEAF = 3

/** Gợi ý số bản lề theo chiều cao cánh (kinh nghiệm xưởng: 2 / 3 / 4). */
export function recommendedHingeCount(leafHeightMm: number): number {
  if (leafHeightMm <= 1200) return 2
  if (leafHeightMm <= 1800) return 3
  return 4
}

export function componentOf(catalog: Catalog | null, key?: string | null) {
  if (!key) return null
  const hardware = catalog?.hardware
  if (!hardware) return null
  return hardware.components[key] ?? null
}

export function componentName(catalog: Catalog | null, key?: string | null): string {
  if (!key) return ''
  if (key === 'none') return 'Không dùng'
  return componentOf(catalog, key)?.name ?? key
}

export function componentPrice(catalog: Catalog | null, key?: string | null): number {
  return componentOf(catalog, key)?.price ?? 0
}

/** Tóm tắt phụ kiện của 1 hạng mục để hiện trên bảng. */
export function hardwareSummary(item: ItemSpec, catalog: Catalog | null): string {
  const parts: string[] = []
  if (item.hinge_type || item.hinge_count != null) {
    const count = item.hinge_count != null ? `${item.hinge_count}×` : ''
    parts.push(`${count}${item.hinge_type ? componentName(catalog, item.hinge_type) : 'bản lề'}`)
  }
  if (item.lock_type) parts.push(componentName(catalog, item.lock_type))
  return parts.join(' · ')
}
