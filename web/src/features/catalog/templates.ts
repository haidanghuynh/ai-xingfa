import type { SystemDef } from '@/types/api'

/** Hệ nhôm trắng để người dùng điền số liệu catalogue thật. */
export function newSystemTemplate(): SystemDef {
  return {
    code: 'XFM',
    name: 'Hệ mới',
    brand: 'Xingfa',
    kind: 'casement',
    joint: 'miter45',
    bar_length_mm: 6500,
    kerf_mm: 5,
    end_trim_mm: 30,
    verified: false,
    source: '',
    notes: '',
    rules: {
      gap_frame_sash_mm: 6,
      sash_overlap_mm: 0,
      glass_rebate_mm: 12,
      glass_clearance_mm: 4,
      min_panel_width_mm: 350,
      max_panel_area_m2: 2.2,
      track_offset_mm: 30,
      sash_inset_mm: null,
    },
    profiles: {
      frame: {
        key: 'frame',
        code: 'KB',
        name: 'Khung bao',
        width_mm: 55,
        depth_mm: 65,
        wall_mm: 1.4,
        kg_per_m: 1.5,
        glass_groove_mm: 24,
      },
      sash: {
        key: 'sash',
        code: 'C',
        name: 'Cửa cánh',
        width_mm: 60,
        depth_mm: 60,
        wall_mm: 1.4,
        kg_per_m: 1.35,
        glass_groove_mm: 24,
      },
      mullion: {
        key: 'mullion',
        code: 'D',
        name: 'Đố đứng',
        width_mm: 45,
        depth_mm: 65,
        wall_mm: 1.4,
        kg_per_m: 1.1,
        glass_groove_mm: 24,
      },
    },
  }
}

export const RULE_FIELDS: { key: keyof SystemDef['rules']; label: string }[] = [
  { key: 'gap_frame_sash_mm', label: 'Khe khung – cánh (mm)' },
  { key: 'sash_overlap_mm', label: 'Cánh chồng khi lùa (mm)' },
  { key: 'glass_rebate_mm', label: 'Ngậm kính vào rãnh (mm)' },
  { key: 'glass_clearance_mm', label: 'Khe hở lắp kính (mm)' },
  { key: 'min_panel_width_mm', label: 'Cánh rộng tối thiểu (mm)' },
  { key: 'max_panel_area_m2', label: 'Diện tích ô tối đa (m²)' },
  { key: 'track_offset_mm', label: 'Lệch ray lùa (mm)' },
  { key: 'sash_inset_mm', label: 'Cánh thụt vào (mm, trống = tự tính)' },
]

export const SYSTEM_KINDS = [
  { value: 'casement', label: 'Mở quay' },
  { value: 'sliding', label: 'Lùa' },
  { value: 'fixed', label: 'Cố định' },
  { value: 'awning', label: 'Mở hất' },
  { value: 'door', label: 'Cửa đi' },
]
