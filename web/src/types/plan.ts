export interface PlanBar {
  group: string
  profile_code: string
  polygon: [number, number][]
  y0: number
  y1: number
  label?: string
  color?: string
}

export interface PlanPane {
  x: number
  y: number
  z: number
  w: number
  h: number
  t: number
  label?: string
}

export interface PlanHardware {
  kind: string
  x: number
  y: number
  z: number
  w: number
  h: number
  d: number
  label?: string
}

export interface PlanItem {
  tag: string
  system: string
  system_name?: string
  type: string
  width_mm: number
  height_mm: number
  sill_mm: number
  joint: string
  bars: PlanBar[]
  panes: PlanPane[]
  hardware?: PlanHardware[]
  aluminum_kg_expected?: number
  glass_m2?: number
  depth_mm?: number
  frame_width_mm?: number
}

export interface BuildPlan {
  schema: string
  units: string
  project: { code: string }
  items: PlanItem[]
}
