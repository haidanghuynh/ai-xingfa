/**
 * Kiểu dữ liệu dùng trong UI — phản chiếu 1-1 với src/xingfacad/models.py.
 * File `types/openapi.d.ts` (sinh bằng `npm run gen:types`) dùng để đối chiếu khi backend đổi.
 */

export type ItemType =
  | 'casement'
  | 'sliding'
  | 'fixed'
  | 'awning'
  | 'door_swing'
  | 'door_sliding'
  | 'tilt_turn'

export type PanelKind = 'sash' | 'fixed'
export type Joint = 'miter45' | 'butt90'
export type PanelOpen = 'in' | 'out' | 'slide' | 'none'
export type PanelDir = 'left' | 'right' | 'up' | 'down' | 'none'
export type IssueLevel = 'error' | 'warning' | 'info'

export interface GlassSpec {
  key: string
  name: string
  thickness_mm: number
  price_per_m2?: number | null
}

export interface PanelSpec {
  kind: PanelKind
  open: PanelOpen
  dir: PanelDir
  ratio: number
  note?: string
}

export interface TransomSpec {
  orientation: 'h' | 'v'
  at_mm: number
  profile: string
  band_above?: PanelKind | null
  band_below?: PanelKind | null
  note?: string
}

export interface ItemSpec {
  tag: string
  room: string
  qty: number
  type: ItemType
  width_mm: number
  height_mm: number
  sill_mm: number
  system?: string | null
  glass: GlassSpec
  color?: string
  hardware?: string
  hinge_type?: string | null
  hinge_count?: number | null
  lock_type?: string | null
  panels: PanelSpec[]
  transoms: TransomSpec[]
  notes: string
  source?: string
  confidence?: number
  needs_review?: string[]
}

export interface ProjectInfo {
  code: string
  name: string
  customer: string
  address: string
  request_org?: string
  request_contact?: string
  request_phone?: string
  quoted_by?: string
  quoted_by_phone?: string
  date: string
  currency: string
  note?: string
}

export interface DefaultsSpec {
  system: string
  glass: GlassSpec
  color: string
  hardware: string
}

export interface ProjectSpec {
  project: ProjectInfo
  defaults: DefaultsSpec
  items: ItemSpec[]
}

export interface ProfileDef {
  key: string
  code: string
  name: string
  width_mm: number
  depth_mm: number
  wall_mm: number
  kg_per_m: number
  glass_groove_mm: number
  price_per_kg?: number | null
}

export interface Rules {
  gap_frame_sash_mm: number
  sash_overlap_mm: number
  glass_rebate_mm: number
  glass_clearance_mm: number
  min_panel_width_mm: number
  max_panel_area_m2: number
  track_offset_mm: number
  sash_inset_mm?: number | null
  [key: string]: number | null | undefined
}

export interface SystemDef {
  code: string
  name: string
  brand: string
  kind: string
  joint: Joint
  bar_length_mm: number
  kerf_mm: number
  end_trim_mm: number
  verified: boolean
  source: string
  notes: string
  rules: Rules
  profiles: Record<string, ProfileDef>
}

export interface SystemSummary {
  code: string
  name: string
  kind: string
  joint: Joint
  verified: boolean
  profiles: number
  bar_length_mm: number
}

export interface FreecadStatus {
  available: boolean
  path: string
  hint: string
  app_version?: string
}

export interface StatusInfo {
  app: string
  version: string
  freecad: FreecadStatus
  dxf: boolean
  excel: boolean
  openai: boolean
  ai?: Record<string, boolean>
  out_dir: string
  item_types: Record<string, string>
  panel_kinds: Record<string, string>
  profile_keys: Record<string, string>
}

export interface GlassCatalogEntry {
  name: string
  thickness_mm: number
  price_per_m2: number
}

export interface HardwareComponent {
  name: string
  unit: string
  price: number
}

export interface HardwareConfig {
  components: Record<string, HardwareComponent & { note?: string }>
  per_leaf_by_type: Record<string, Record<string, number>>
  hinge_options?: string[]
  lock_options?: string[]
  screw_per_bar: number
  gasket_waste_percent: number
  silicone_m_per_tube: number
}

export interface Catalog {
  glass: Record<string, GlassCatalogEntry>
  hardware: HardwareConfig
}

export interface CompanyInfo {
  name?: string
  address?: string
  phone?: string
  tax_code?: string
}

export interface Pricing {
  currency: string
  effective_date: string
  aluminum_price_per_kg: number
  waste_percent: number
  labor_percent_of_material: number
  profit_percent: number
  vat_percent: number
  consumables_per_m2: number
  transport_per_item: number
  round_to: number
  company: CompanyInfo
  note?: string
}

export interface Issue {
  level: IssueLevel | string
  code?: string
  tag?: string
  message: string
}

export interface ValidateTotals {
  items: number
  area_m2: number
  alum_kg: number
  glass_m2: number
  leaves: number
  bars: number
}

export interface ValidateResult {
  ok: boolean
  issues: Issue[]
  totals: ValidateTotals
}

export interface Artifact {
  name: string
  kind: string
  tag?: string
  size: number
  url: string
}

export interface ResultItem {
  tag: string
  room: string
  type: ItemType
  type_label: string
  system: string
  width_mm: number
  height_mm: number
  qty: number
  area_m2: number
  alum_kg: number
  glass_m2: number
  leaves: number
  cells: number
  height_sill_mm: number
  price: number
  unit_price_m2: number
  files: Record<string, string>
  warnings: string[]
}

export interface CutGroup {
  profile_code: string
  profile_name: string
  stock_mm: number
  bars: number
  waste_m: number
  waste_percent: number
  patterns: string[]
}

export interface FreecadReport {
  objects?: number
  total_volume_mm3?: number
  warnings?: string[]
  errors?: string[]
  fcstd?: string
  step?: string
  stl?: string
}

export interface BuildSummary {
  project_code: string
  project_name: string
  customer: string
  currency: string
  items: number
  total_leaves: number
  area_m2: number
  alum_kg: number
  glass_m2: number
  cost_total: number
  price: number
  vat: number
  price_with_vat: number
  avg_unit_price_m2: number
  bars: number
  waste_m: number
  errors: number
  warnings: number
  generated_at: string
  freecad?: Record<string, unknown>
}

export interface FreecadInfo {
  available?: boolean
  ok?: boolean
  path?: string
  message?: string
  error?: string
  report?: FreecadReport
}

export interface BuildOutcome {
  project: ProjectInfo
  items: ResultItem[]
  issues: Issue[]
  artifacts: Artifact[]
  summary: BuildSummary
  cut_plan: CutGroup[]
  freecad: FreecadInfo
  out_dir: string
}

export interface ProjectListEntry {
  code: string
  name: string
  customer: string
  date: string
  price: number
  files: number
  area_m2?: number
}

export interface AIProvider {
  name: string
  label: string
  model: string
  vision: boolean
  available: boolean
  api_key_env: string
}

export interface AIStatus {
  default_provider: string
  temperature: number
  providers: AIProvider[]
  note?: string
}

export interface ExtractedItem
  extends Omit<Partial<ItemSpec>, 'type' | 'width_mm' | 'height_mm' | 'sill_mm' | 'panels' | 'transoms'> {
  tag: string
  type: ItemType
  width_mm: number | null
  height_mm: number | null
  sill_mm?: number | null
  panels: PanelSpec[]
  transoms: TransomSpec[]
  confidence: number
  needs_review: string[]
}

export interface ExtractResponse {
  ok: boolean
  provider: string
  model: string
  items: ExtractedItem[]
  warnings: string[]
  log?: string
  data?: { items?: Partial<ItemSpec>[] }
  raw?: unknown
}
