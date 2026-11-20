import type { Catalog, DefaultsSpec, GlassSpec, ItemSpec, ProjectInfo, ProjectSpec } from '@/types/api'
import { today } from '@/lib/format'

export function glassFromCatalog(catalog: Catalog | null, key: string): GlassSpec {
  const entry = catalog?.glass?.[key]
  if (entry) {
    return { key, name: entry.name, thickness_mm: entry.thickness_mm, price_per_m2: entry.price_per_m2 }
  }
  return { key, name: key, thickness_mm: 8, price_per_m2: 0 }
}

export function defaultProject(system: string, catalog: Catalog | null): ProjectSpec {
  const glassKey = Object.keys(catalog?.glass ?? {})[0] ?? 'cuong_luc_8'
  return {
    project: {
      code: `DU-AN-${new Date().getFullYear()}`,
      name: '',
      customer: '',
      address: '',
      request_org: '',
      request_contact: '',
      request_phone: '',
      quoted_by: '',
      quoted_by_phone: '',
      date: today(),
      currency: 'VND',
    },
    defaults: {
      system,
      glass: glassFromCatalog(catalog, glassKey),
      color: 'Trắng sứ',
      hardware: 'Kinlong',
    },
    items: [],
  }
}

export function emptyItem(index: number, project: ProjectSpec): ItemSpec {
  return {
    tag: `C${index + 1}`,
    room: '',
    qty: 1,
    type: 'casement',
    width_mm: 1200,
    height_mm: 1500,
    sill_mm: 900,
    system: project.defaults.system,
    glass: { ...project.defaults.glass },
    panels: [],
    transoms: [],
    notes: '',
  }
}

const toNumber = (value: unknown, fallback: number): number => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

const toText = (value: unknown, fallback = ''): string =>
  typeof value === 'string' ? value : value == null ? fallback : String(value)

/** Chuẩn hoá dữ liệu từ API / file JSON / AI thành ProjectSpec đầy đủ. */
export function normalizeProject(raw: unknown, base: ProjectSpec, catalog: Catalog | null): ProjectSpec {
  const data = (raw ?? {}) as Partial<ProjectSpec> & { data?: { items?: unknown[] } }
  const source: Partial<ProjectInfo> = data.project ?? {}
  const defaults: Partial<DefaultsSpec> = data.defaults ?? {}
  const items = Array.isArray(data.items) ? data.items : Array.isArray(data.data?.items) ? data.data.items : []

  const glassKey = toText(defaults.glass?.key, base.defaults.glass.key)
  return {
    project: {
      code: toText(source.code, base.project.code),
      name: toText(source.name, base.project.name),
      customer: toText(source.customer, base.project.customer),
      address: toText(source.address, base.project.address),
      request_org: toText(source.request_org, base.project.request_org ?? ''),
      request_contact: toText(source.request_contact, base.project.request_contact ?? ''),
      request_phone: toText(source.request_phone, base.project.request_phone ?? ''),
      quoted_by: toText(source.quoted_by, base.project.quoted_by ?? ''),
      quoted_by_phone: toText(source.quoted_by_phone, base.project.quoted_by_phone ?? ''),
      date: toText(source.date, base.project.date),
      currency: toText(source.currency, base.project.currency),
    },
    defaults: {
      system: toText(defaults.system, base.defaults.system),
      glass: glassFromCatalog(catalog, glassKey),
      color: toText(defaults.color, base.defaults.color),
      hardware: toText(defaults.hardware, base.defaults.hardware),
    },
    items: items.map((entry, index) => {
      const item = (entry ?? {}) as Partial<ItemSpec>
      const width = toNumber(item.width_mm, 1200)
      const height = toNumber(item.height_mm, 1500)
      return {
        tag: toText(item.tag, `C${index + 1}`),
        room: toText(item.room),
        qty: Math.max(1, Math.round(toNumber(item.qty, 1))),
        type: (item.type ?? 'casement') as ItemSpec['type'],
        width_mm: width > 100 ? width : 1200,
        height_mm: height > 100 ? height : 1500,
        sill_mm: toNumber(item.sill_mm, 900),
        system: item.system ? toText(item.system) : null,
        glass: glassFromCatalog(catalog, toText(item.glass?.key, glassKey)),
        hinge_type: item.hinge_type ? toText(item.hinge_type) : null,
        hinge_count:
          item.hinge_count === null || item.hinge_count === undefined
            ? null
            : Math.max(0, Math.round(toNumber(item.hinge_count, 0))),
        lock_type: item.lock_type ? toText(item.lock_type) : null,
        panels: Array.isArray(item.panels) ? item.panels : [],
        transoms: Array.isArray(item.transoms) ? item.transoms : [],
        notes: toText(item.notes),
        source: toText(item.source, 'manual'),
        confidence: toNumber(item.confidence, 1),
        needs_review: Array.isArray(item.needs_review) ? item.needs_review : [],
      }
    }),
  }
}

/** Đảm bảo mọi hạng mục có hệ + kính trước khi gửi API. */
export function collectProject(project: ProjectSpec, catalog: Catalog | null): ProjectSpec {
  return {
    ...project,
    project: { ...project.project, code: project.project.code.trim() || 'DU-AN' },
    items: project.items.map((item, index) => ({
      ...item,
      tag: item.tag.trim() || `C${index + 1}`,
      system: item.system || project.defaults.system,
      glass: item.glass?.key ? glassFromCatalog(catalog, item.glass.key) : { ...project.defaults.glass },
      panels: item.panels ?? [],
      transoms: item.transoms ?? [],
    })),
  }
}
