import type {
  AIStatus,
  BuildOutcome,
  Catalog,
  ExtractResponse,
  Issue,
  Pricing,
  ProjectListEntry,
  ProjectSpec,
  StatusInfo,
  SystemDef,
  SystemSummary,
  ValidateResult,
} from '@/types/api'
import type { BookResult, GroupCost, PricingBook } from '@/types/pricing-book'

export class ApiError extends Error {
  readonly status: number
  readonly issues?: Issue[]

  constructor(message: string, status: number, issues?: Issue[]) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.issues = issues
  }
}

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
  headers?: Record<string, string>
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, headers } = options
  const response = await fetch(path, {
    method,
    headers: { 'Content-Type': 'application/json', ...(headers ?? {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) {
    let detail: unknown = response.statusText
    try {
      detail = (await response.json())?.detail ?? detail
    } catch {
      /* body không phải JSON */
    }
    const record = detail as { message?: string; issues?: Issue[] } | string | undefined
    const message =
      typeof record === 'string'
        ? record
        : record?.message ?? (record ? JSON.stringify(record) : `HTTP ${response.status}`)
    const issues = typeof record === 'object' && record ? record.issues : undefined
    throw new ApiError(message || `HTTP ${response.status}`, response.status, issues)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  status: () => request<StatusInfo>('/api/status'),

  systems: () => request<SystemSummary[]>('/api/systems'),
  system: (code: string) => request<SystemDef>(`/api/systems/${encodeURIComponent(code)}`),
  saveSystem: (system: SystemDef) =>
    request<{ ok: boolean; code: string; path: string }>('/api/systems', { method: 'POST', body: system }),
  deleteSystem: (code: string) =>
    request<{ ok: boolean }>(`/api/systems/${encodeURIComponent(code)}`, { method: 'DELETE' }),
  duplicateSystem: (code: string, newCode: string) =>
    request<{ ok: boolean; code: string }>(`/api/systems/${encodeURIComponent(code)}/duplicate`, {
      method: 'POST',
      body: { new_code: newCode },
    }),

  catalog: () => request<Catalog>('/api/catalog'),
  saveCatalog: (catalog: Catalog) => request<{ ok: boolean }>('/api/catalog', { method: 'PUT', body: catalog }),
  pricing: () => request<Pricing>('/api/pricing'),
  savePricing: (pricing: Pricing) =>
    request<{ ok: boolean; pricing: Pricing }>('/api/pricing', { method: 'PUT', body: pricing }),
  importPricing: (fileBase64: string) =>
    request<{ ok: boolean; updated: Record<string, number>; pricing: Pricing }>('/api/pricing/import', {
      method: 'POST',
      body: { file_base64: fileBase64 },
    }),

  pricingBook: () => request<{ book: PricingBook; result: BookResult }>('/api/pricing-book'),
  savePricingBook: (book: PricingBook) =>
    request<{ ok: boolean; book: PricingBook; result: BookResult }>('/api/pricing-book', {
      method: 'PUT',
      body: book,
    }),
  deriveGroupCost: (code: string) =>
    request<{ ok: boolean; code: string; cost: GroupCost }>(
      `/api/pricing-book/derive/${encodeURIComponent(code)}`,
      { method: 'POST' },
    ),

  demo: () => request<ProjectSpec>('/api/demo'),
  projects: () => request<ProjectListEntry[]>('/api/projects'),
  project: (code: string) => request<ProjectSpec>(`/api/projects/${encodeURIComponent(code)}`),
  deleteProject: (code: string) =>
    request<{ ok: boolean }>(`/api/projects/${encodeURIComponent(code)}`, { method: 'DELETE' }),

  validate: (project: ProjectSpec) => request<ValidateResult>('/api/validate', { method: 'POST', body: project }),
  build: (project: ProjectSpec, with3d: boolean, pricingMode: 'bom' | 'book' = 'bom', priceLevel = 'le') =>
    request<BuildOutcome>('/api/build', {
      method: 'POST',
      body: { project, with_3d: with3d, with_drawings: true, pricing_mode: pricingMode, price_level: priceLevel },
    }),
  regenerateQuote: (project: ProjectSpec, pricingMode: 'bom' | 'book' = 'bom', priceLevel = 'le') =>
    request<{
      ok: boolean
      artifacts: BuildOutcome['artifacts']
      issues: Issue[]
      summary: Record<string, number | string>
    }>('/api/quote', {
      method: 'POST',
      body: { project, pricing_mode: pricingMode, price_level: priceLevel },
    }),

  prompt: async (): Promise<string> => {
    const response = await fetch('/api/prompt')
    if (!response.ok) throw new ApiError('Không tải được prompt', response.status)
    return response.text()
  },
  extract: (imageBase64: string, provider?: string, model?: string) =>
    request<ExtractResponse>('/api/extract', {
      method: 'POST',
      body: { image_base64: imageBase64, provider, model },
    }),
  aiStatus: () => request<AIStatus>('/api/ai'),
}
