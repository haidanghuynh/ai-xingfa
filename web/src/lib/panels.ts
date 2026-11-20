import type { ItemType, PanelDir, PanelKind, PanelSpec, TransomSpec } from '@/types/api'

const DIRS: Record<string, PanelDir> = {
  l: 'left',
  left: 'left',
  trai: 'left',
  'trái': 'left',
  r: 'right',
  right: 'right',
  phai: 'right',
  'phải': 'right',
  u: 'up',
  up: 'up',
  tren: 'up',
  'trên': 'up',
  d: 'down',
  down: 'down',
  duoi: 'down',
  'dưới': 'down',
  s: 'none',
  slide: 'none',
  lua: 'none',
  'lùa': 'none',
  none: 'none',
}

const FIXED_WORDS = new Set(['fixed', 'fix', 'f', 'cd', 'codinh', 'cốđịnh', 'cố định', 'kinh', 'kính'])

export const isSliding = (type: ItemType): boolean => type === 'sliding' || type === 'door_sliding'

/** "sash:L, sash:R:0.6, fixed" -> PanelSpec[] */
export function textToPanels(text: string, type: ItemType): PanelSpec[] {
  if (!text || !text.trim()) return []
  const sliding = isSliding(type)
  return text
    .split(',')
    .map((segment) => {
      const tokens = segment
        .split(':')
        .map((token) => token.trim())
        .filter(Boolean)
      if (!tokens.length) return null
      const first = tokens[0].toLowerCase().replace(/\s+/g, '')
      const kind: PanelKind = FIXED_WORDS.has(first) ? 'fixed' : 'sash'
      const panel: PanelSpec = {
        kind,
        open: kind === 'fixed' ? 'none' : sliding ? 'slide' : 'out',
        dir: kind === 'fixed' || sliding ? 'none' : 'left',
        ratio: 1,
      }
      tokens.slice(1).forEach((token) => {
        const low = token.toLowerCase()
        if (/^[0-9]+(\.[0-9]+)?$/.test(low)) {
          panel.ratio = Number(low)
          return
        }
        if (low === 'slide' || low === 'lua' || low === 'lùa' || low === 's') {
          panel.open = 'slide'
          panel.dir = 'none'
          return
        }
        const dir = DIRS[low] ?? DIRS[low[0] ?? '']
        if (dir) panel.dir = dir
      })
      return panel
    })
    .filter((panel): panel is PanelSpec => panel !== null)
}

export function panelsToText(panels: PanelSpec[] | undefined): string {
  return (panels ?? [])
    .map((panel) => {
      const parts = [panel.kind === 'fixed' ? 'fixed' : 'sash']
      if (panel.open === 'slide') parts.push('slide')
      else if (panel.dir && panel.dir !== 'none') parts.push(panel.dir[0].toUpperCase())
      if (panel.ratio && panel.ratio !== 1) parts.push(String(panel.ratio))
      return parts.join(':')
    })
    .join(', ')
}

/** "h@500:fixed; h@1500" -> TransomSpec[] */
export function textToTransoms(text: string): TransomSpec[] {
  if (!text || !text.trim()) return []
  return text
    .split(';')
    .map((segment) => {
      const raw = segment.trim()
      if (!raw) return null
      const [head, band] = raw.split(':')
      const clean = head.trim().toLowerCase()
      const orientation = clean.startsWith('v') ? 'v' : 'h'
      const at = Number(clean.replace(/^[a-z]/, '').replace('@', ''))
      if (!at || at <= 0) return null
      const transom: TransomSpec = { orientation, at_mm: at, profile: 'transom' }
      const kind = (band ?? '').trim()
      if (kind === 'fixed' || kind === 'sash') transom.band_above = kind
      return transom
    })
    .filter((transom): transom is TransomSpec => transom !== null)
}

export function transomsToText(transoms: TransomSpec[] | undefined): string {
  return (transoms ?? [])
    .map((transom) => {
      let text = `${transom.orientation || 'h'}@${Math.round(transom.at_mm)}`
      if (transom.band_above) text += `:${transom.band_above}`
      return text
    })
    .join('; ')
}
