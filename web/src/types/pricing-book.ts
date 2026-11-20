/** Bảng chi phí giá thành & giá bán đến tay khách (khớp src/xingfacad/pricing_book.py). */

export interface NormSpec {
  item_type: string
  width_mm: number
  height_mm: number
  system: string
  panels: number
  glass_key: string
  hinge_type?: string | null
  hinge_count?: number | null
  lock_type?: string | null
}

export interface HardwareCostItem {
  key: string
  qty_per_set: number
  price: number
}

export interface GroupCost {
  alum_kg_per_m2: number
  alum_price_per_kg: number
  alum_waste_percent: number
  glass_m2_per_m2: number
  glass_price_per_m2: number
  glass_waste_percent: number
  hardware_items: HardwareCostItem[]
  hardware_waste_percent: number
  consumables_per_m2: number
  labor_production_per_m2: number
  labor_install_per_m2: number
  factory_per_m2: number
  packaging_per_m2: number
  transport_per_m2: number
  warranty_percent: number
  management_percent: number
  finance_percent: number
}

export interface ProductGroup {
  code: string
  name: string
  item_types: string[]
  norm: NormSpec
  cost: GroupCost
}

export interface PriceLevel {
  code: string
  name: string
  margin_percent: number
  discount_percent: number
  include_install: boolean
  show_in_quote: boolean
}

export interface BookSettings {
  vat_percent: number
  round_to: number
  show_inc_vat: boolean
}

export interface PricingBook {
  currency: string
  effective_date: string
  settings: BookSettings
  groups: ProductGroup[]
  levels: PriceLevel[]
  note: string
}

export interface CostLine {
  key: string
  label: string
  amount_per_m2: number
}

export interface LevelPrice {
  code: string
  name: string
  margin_percent: number
  discount_percent: number
  include_install: boolean
  show_in_quote: boolean
  base_per_m2: number
  listed_per_m2: number
  price_ex_vat_m2: number
  price_inc_vat_m2: number
  price_ex_vat_set: number
  price_inc_vat_set: number
}

export interface GroupResult {
  code: string
  name: string
  item_types: string[]
  norm_width_mm: number
  norm_height_mm: number
  norm_system: string
  norm_area_m2: number
  lines: CostLine[]
  direct_per_m2: number
  warranty_per_m2: number
  management_per_m2: number
  finance_per_m2: number
  cost_per_m2: number
  cost_per_set: number
  levels: LevelPrice[]
}

export interface BookResult {
  currency: string
  effective_date: string
  vat_percent: number
  round_to: number
  show_inc_vat: boolean
  groups: GroupResult[]
  note: string
}
