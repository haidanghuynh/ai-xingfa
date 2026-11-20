import * as React from 'react'
import { Boxes, Image as ImageIcon, LayoutList, Ruler, Tags } from 'lucide-react'
import { Tabs } from '@/components/ui/layout'
import { useToast } from '@/components/ui/overlays'
import { CatalogTab } from '@/features/catalog/CatalogTab'
import { ImageTab } from '@/features/image/ImageTab'
import { PricingBookTab } from '@/features/pricing/PricingBookTab'
import { ProjectTab } from '@/features/project/ProjectTab'
import { ResultsTab } from '@/features/results/ResultsTab'
import { ApiError, api } from '@/lib/api'
import { num } from '@/lib/format'
import { collectProject, defaultProject, normalizeProject } from '@/lib/project'
import { cn } from '@/lib/utils'
import type {
  BuildOutcome,
  Catalog,
  Issue,
  ItemSpec,
  Pricing,
  ProjectSpec,
  StatusInfo,
  SystemSummary,
} from '@/types/api'
import type { BookResult, PricingBook } from '@/types/pricing-book'

const STORAGE_KEY = 'xfcad.project.web'

type TabValue = 'project' | 'catalog' | 'pricing' | 'image' | 'results'

function StatusPill({ ok, warn, label }: { ok: boolean; warn?: boolean; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-900/25 px-2.5 py-1 text-[11px] font-medium text-white/90">
      <span
        className={cn('h-1.5 w-1.5 rounded-full', ok ? 'bg-emerald-400' : warn ? 'bg-amber-400' : 'bg-red-400')}
      />
      {label}
    </span>
  )
}

export default function App() {
  const toast = useToast()
  const [status, setStatus] = React.useState<StatusInfo | null>(null)
  const [systems, setSystems] = React.useState<SystemSummary[]>([])
  const [catalog, setCatalog] = React.useState<Catalog | null>(null)
  const [pricing, setPricing] = React.useState<Pricing | null>(null)
  const [project, setProject] = React.useState<ProjectSpec | null>(null)
  const [outcome, setOutcome] = React.useState<BuildOutcome | null>(null)
  const [issues, setIssues] = React.useState<Issue[] | null>(null)
  const [issueTitle, setIssueTitle] = React.useState('Kết quả kiểm tra')
  const [tab, setTab] = React.useState<TabValue>('project')
  const [busy, setBusy] = React.useState(false)
  const [with3d, setWith3d] = React.useState(true)
  const [priceBook, setPriceBook] = React.useState<PricingBook | null>(null)
  const [pricingMode, setPricingMode] = React.useState<'bom' | 'book'>('bom')
  const [priceLevel, setPriceLevel] = React.useState('le')

  React.useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const [statusInfo, catalogData, pricingData, systemList, bookData] = await Promise.all([
          api.status(),
          api.catalog(),
          api.pricing(),
          api.systems(),
          api.pricingBook(),
        ])
        if (cancelled) return
        setStatus(statusInfo)
        setCatalog(catalogData)
        setPricing(pricingData)
        setSystems(systemList)
        setPriceBook(bookData.book)
        setPriceLevel(bookData.book.levels[0]?.code ?? 'le')
        const base = defaultProject(systemList[0]?.code ?? 'XF65', catalogData)
        const saved = window.localStorage.getItem(STORAGE_KEY)
        if (saved) {
          try {
            setProject(normalizeProject(JSON.parse(saved), base, catalogData))
          } catch {
            setProject(base)
          }
        } else {
          setProject(base)
        }
      } catch (error) {
        toast.push(`Không kết nối được API: ${(error as Error).message}`, 'error')
        setProject(defaultProject('XF65', null))
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [toast])

  React.useEffect(() => {
    if (!project) return
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(project))
  }, [project])

  const reloadSystems = React.useCallback(async () => {
    const list = await api.systems()
    setSystems(list)
  }, [])

  const handleValidate = async () => {
    if (!project) return
    setBusy(true)
    try {
      const payload = collectProject(project, catalog)
      setProject(payload)
      const result = await api.validate(payload)
      setIssues(result.issues)
      setIssueTitle(result.ok ? 'Dữ liệu hợp lệ' : 'Có lỗi cần sửa')
      if (result.ok) {
        toast.push(
          `Hợp lệ: ${result.totals.items} cửa · ${num(result.totals.area_m2, 2)} m² · ${num(result.totals.alum_kg, 2)} kg nhôm`,
          'success',
        )
      } else {
        const errors = result.issues.filter((issue) => issue.level === 'error').length
        toast.push(`Có ${errors} lỗi cần sửa`, 'error')
      }
    } catch (error) {
      toast.push((error as Error).message, 'error')
    } finally {
      setBusy(false)
    }
  }

  const handleBuild = async () => {
    if (!project) return
    setBusy(true)
    setIssues(null)
    try {
      const payload = collectProject(project, catalog)
      setProject(payload)
      const result = await api.build(payload, with3d, pricingMode, priceLevel)
      setOutcome(result)
      setIssues(result.issues)
      setIssueTitle(`Cảnh báo của ${result.project.code}`)
      setTab('results')
      toast.push(`Build xong ${result.artifacts.length} file`, 'success')
    } catch (error) {
      const apiError = error as ApiError
      if (apiError.issues?.length) {
        setIssues(apiError.issues)
        setIssueTitle('Không build được')
      }
      toast.push(apiError.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  const handleDemo = async () => {
    if (!project) return
    try {
      const demo = await api.demo()
      setProject(normalizeProject(demo, project, catalog))
      setOutcome(null)
      setIssues(null)
      toast.push('Đã nạp dự án mẫu', 'success')
    } catch (error) {
      toast.push((error as Error).message, 'error')
    }
  }

  const handleReset = () => {
    if (!project) return
    if (!window.confirm('Xóa toàn bộ dữ liệu đang nhập và bắt đầu mới?')) return
    setProject(defaultProject(systems[0]?.code ?? 'XF65', catalog))
    setOutcome(null)
    setIssues(null)
    toast.push('Đã làm mới')
  }

  const handleApplyAiItems = (items: Partial<ItemSpec>[]) => {
    if (!project) return
    const normalized = normalizeProject({ items }, project, catalog).items
    const existing = new Set(project.items.map((item) => item.tag))
    const added = normalized.map((item, index) => {
      const baseTag = item.tag || `C${project.items.length + index + 1}`
      let tag = baseTag
      let suffix = 2
      while (existing.has(tag)) {
        tag = `${baseTag}-${suffix}`
        suffix += 1
      }
      existing.add(tag)
      const raw = items[index] ?? {}
      const missingDims = raw.width_mm == null || raw.height_mm == null
      return {
        ...item,
        tag,
        notes:
          missingDims && !item.notes.includes('Cần nhập kích thước')
            ? `${item.notes} [Cần nhập kích thước]`.trim()
            : item.notes,
      }
    })
    setProject({ ...project, items: [...project.items, ...added] })
    setTab('project')
    toast.push(`Đã thêm ${added.length} cửa — kiểm tra kích thước rồi Build`, 'success')
  }

  const freecad = status?.freecad
  const tabs = [
    { value: 'project', label: <><LayoutList className="h-3.5 w-3.5" /> Dự án</>, badge: project?.items.length ? <span className="text-[10px] text-muted-foreground">{project.items.length}</span> : null },
    { value: 'catalog', label: <><Ruler className="h-3.5 w-3.5" /> Catalogue Xingfa</> },
    { value: 'pricing', label: <><Tags className="h-3.5 w-3.5" /> Giá thành &amp; giá bán</> },
    { value: 'image', label: <><ImageIcon className="h-3.5 w-3.5" /> Ảnh &amp; AI</> },
    { value: 'results', label: <><Boxes className="h-3.5 w-3.5" /> Kết quả</>, badge: outcome ? <span className="text-[10px] text-muted-foreground">{outcome.artifacts.length}</span> : null },
  ]

  return (
    <div className="min-h-screen bg-background">
      <header className="bg-gradient-to-r from-primary via-[#274b86] to-accent">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-4 px-6 py-3.5">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl border border-white/30 bg-white/15 text-lg font-extrabold text-white">
              X
            </span>
            <div>
              <h1 className="text-lg font-bold tracking-wide text-white">XingfaCAD</h1>
              <p className="text-[11px] text-white/80">Kích thước → 3D FreeCAD · Bản vẽ 2D sản xuất · Báo giá Excel</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusPill ok={Boolean(freecad?.available)} label="FreeCAD" />
            <StatusPill ok={Boolean(status?.dxf)} label="DXF" />
            <StatusPill ok={Boolean(status?.openai)} warn label="OpenAI" />
            {status ? <span className="text-[11px] text-white/70">v{status.version}</span> : null}
          </div>
        </div>
      </header>

      <div className="sticky top-0 z-30 border-b border-border bg-card/95 backdrop-blur">
        <div className="mx-auto max-w-[1440px] px-6">
          <Tabs value={tab} onChange={(value) => setTab(value as TabValue)} items={tabs} />
        </div>
      </div>

      <main className="mx-auto max-w-[1440px] px-6 py-5 pb-16">
        {!project ? (
          <div className="grid place-items-center py-24 text-sm text-muted-foreground">Đang tải dữ liệu…</div>
        ) : (
          <div className="animate-fade-in">
            {tab === 'project' ? (
              <ProjectTab
                project={project}
                systems={systems}
                catalog={catalog}
                status={status}
                busy={busy}
                with3d={with3d}
                pricingMode={pricingMode}
                priceLevel={priceLevel}
                priceLevels={priceBook?.levels ?? []}
                issues={issues}
                issueTitle={issueTitle}
                onChange={setProject}
                onWith3dChange={setWith3d}
                onPricingModeChange={setPricingMode}
                onPriceLevelChange={setPriceLevel}
                onValidate={() => void handleValidate()}
                onBuild={() => void handleBuild()}
                onLoadDemo={() => void handleDemo()}
                onReset={handleReset}
              />
            ) : null}

            {tab === 'catalog' ? (
              <CatalogTab
                systems={systems}
                catalog={catalog}
                pricing={pricing}
                onReloadSystems={reloadSystems}
                onCatalogSaved={setCatalog}
                onPricingSaved={setPricing}
              />
            ) : null}

            {tab === 'pricing' ? (
              <PricingBookTab
                systems={systems}
                catalog={catalog}
                status={status}
                onBookSaved={(nextBook: PricingBook, _result: BookResult) => {
                  setPriceBook(nextBook)
                  if (!nextBook.levels.some((level) => level.code === priceLevel)) {
                    setPriceLevel(nextBook.levels[0]?.code ?? 'le')
                  }
                }}
              />
            ) : null}

            {tab === 'image' ? <ImageTab status={status} onApplyItems={handleApplyAiItems} /> : null}

            {tab === 'results' ? (
              <ResultsTab
                outcome={outcome}
                project={project}
                pricingMode={pricingMode}
                priceLevel={priceLevel}
                onProjectChange={setProject}
                onGoProject={() => setTab('project')}
              />
            ) : null}
          </div>
        )}
      </main>

      <footer className="border-t border-border py-4 text-center text-[11px] text-muted-foreground">
        XingfaCAD · FastAPI + Vite/React + FreeCAD · dữ liệu cửa nhôm Xingfa
      </footer>
    </div>
  )
}
