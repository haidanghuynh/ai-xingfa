import * as React from 'react'
import { Box, Download, FileSpreadsheet, FileText, Image as ImageIcon, Info, RefreshCw } from 'lucide-react'
import { Badge, Button, Input, Label } from '@/components/ui/primitives'
import { EmptyRow, Metric, SectionCard, Table, Tabs } from '@/components/ui/layout'
import { useToast } from '@/components/ui/overlays'
import { api } from '@/lib/api'
import { fileSize, money, num } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { BuildOutcome, FreecadInfo, ProjectSpec } from '@/types/api'
import type { BuildPlan } from '@/types/plan'

const ModelViewer3D = React.lazy(() => import('@/features/results/ModelViewer3D'))

interface ResultsTabProps {
  outcome: BuildOutcome | null
  project: ProjectSpec | null
  pricingMode: 'bom' | 'book'
  priceLevel: string
  onProjectChange: (project: ProjectSpec) => void
  onGoProject: () => void
}

const FILE_ICONS: Record<string, React.ReactNode> = {
  dxf: <FileText className="h-3 w-3" />,
  drawing: <FileText className="h-3 w-3" />,
  preview: <ImageIcon className="h-3 w-3" />,
  obj: <Box className="h-3 w-3" />,
  xlsx: <FileSpreadsheet className="h-3 w-3" />,
}

const ARTIFACT_LABEL: Record<string, string> = {
  json: 'JSON',
  csv: 'CSV',
  dxf: 'DXF',
  svg: 'SVG',
  svg3d: '3D',
  obj: 'OBJ',
  xlsx: 'XLSX',
  pdf: 'PDF',
  json3d: 'PLAN',
  fcstd: 'FCStd',
  step: 'STEP',
  stl: 'STL',
}

function QuickLink({
  href,
  icon,
  children,
  download,
}: {
  href: string
  icon: React.ReactNode
  children: React.ReactNode
  download?: boolean
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      download={download || undefined}
      className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-3 text-xs font-semibold text-primary transition-colors hover:bg-secondary"
    >
      {icon}
      {children}
    </a>
  )
}

function FileLink({ href, kind }: { href: string; kind: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="inline-flex items-center gap-1 rounded-md border border-border px-1.5 py-0.5 text-[10px] font-semibold uppercase text-primary transition-colors hover:bg-secondary"
      title={kind}
    >
      {FILE_ICONS[kind] ?? <Download className="h-3 w-3" />}
      {kind === 'preview' ? '3D' : kind === 'drawing' ? '2D' : kind.toUpperCase()}
    </a>
  )
}

function FreecadBox({ info }: { info: FreecadInfo }) {
  const available = Boolean(info.available)
  const ok = Boolean(info.ok)
  return (
    <div className="rounded-lg border border-border bg-secondary/40 p-3 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold">FreeCAD</span>
        {available ? <Badge variant="ok">đã cài</Badge> : <Badge variant="warn">chưa cài</Badge>}
        {ok ? <Badge variant="ok">xuất 3D OK</Badge> : <Badge variant="outline">chưa xuất 3D</Badge>}
      </div>
      {info.report ? (
        <p className="mt-1.5 text-muted-foreground">
          Objects: <b>{info.report.objects ?? 0}</b> · Thể tích:{' '}
          <b>{num(info.report.total_volume_mm3 ?? 0)}</b> mm³
        </p>
      ) : null}
      {info.message ? <p className="mt-1.5 text-amber-700">{info.message}</p> : null}
      {info.path ? <p className="mt-1 break-all text-muted-foreground">{info.path}</p> : null}
    </div>
  )
}

export function ResultsTab({ outcome, project, pricingMode, priceLevel, onProjectChange, onGoProject }: ResultsTabProps) {
  const toast = useToast()
  const [selectedTag, setSelectedTag] = React.useState<string | null>(null)
  const [view, setView] = React.useState<'3d' | 'drawing'>('3d')
  const [plan, setPlan] = React.useState<BuildPlan | null>(null)
  const [quoteBusy, setQuoteBusy] = React.useState(false)
  const [quoteArtifacts, setQuoteArtifacts] = React.useState<BuildOutcome['artifacts'] | null>(null)
  const [previewKey, setPreviewKey] = React.useState(() => Date.now())
  const [quoteInfo, setQuoteInfo] = React.useState({
    request_org: '',
    request_contact: '',
    request_phone: '',
    quoted_by: '',
    quoted_by_phone: '',
  })

  React.useEffect(() => {
    if (!project) return
    setQuoteInfo({
      request_org: project.project.request_org ?? '',
      request_contact: project.project.request_contact ?? '',
      request_phone: project.project.request_phone ?? '',
      quoted_by: project.project.quoted_by ?? '',
      quoted_by_phone: project.project.quoted_by_phone ?? '',
    })
  }, [project])

  const regenerateQuote = async () => {
    if (!project) return
    setQuoteBusy(true)
    try {
      const updated: ProjectSpec = { ...project, project: { ...project.project, ...quoteInfo } }
      onProjectChange(updated)
      const response = await api.regenerateQuote(updated, pricingMode, priceLevel)
      setQuoteArtifacts(response.artifacts)
      setPreviewKey(Date.now())
      toast.push('Đã cập nhật thông tin báo giá', 'success')
    } catch (error) {
      toast.push((error as Error).message, 'error')
    } finally {
      setQuoteBusy(false)
    }
  }

  React.useEffect(() => {
    if (!outcome?.items.length) return
    setSelectedTag((prev) => prev ?? outcome.items[0].tag)
  }, [outcome])

  React.useEffect(() => {
    if (!outcome) {
      setPlan(null)
      return undefined
    }
    const artifact = outcome.artifacts.find((entry) => entry.kind === 'json3d')
    if (!artifact) {
      setPlan(null)
      return undefined
    }
    let cancelled = false
    fetch(artifact.url)
      .then((response) => response.json())
      .then((data: BuildPlan) => {
        if (!cancelled) setPlan(data)
      })
      .catch(() => {
        if (!cancelled) setPlan(null)
      })
    return () => {
      cancelled = true
    }
  }, [outcome])

  if (!outcome) {
    return (
      <SectionCard
        title="Chưa có kết quả"
        description="Nhập dữ liệu rồi bấm Build để sinh 3D, bản vẽ 2D và báo giá Excel"
      >
        <div className="flex flex-col items-center gap-3 py-10 text-sm text-muted-foreground">
          <Info className="h-6 w-6" />
          <p>Chưa có lần build nào trong phiên này.</p>
          <Button variant="outline" onClick={onGoProject}>
            Về tab Dự án
          </Button>
        </div>
      </SectionCard>
    )
  }

  const summary = outcome.summary
  const active = outcome.items.find((item) => item.tag === selectedTag) ?? outcome.items[0]
  const planItem = plan?.items.find((entry) => entry.tag === active?.tag) ?? null
  const previewUrl = active?.files?.[view] ?? ''
  const quoteFiles = quoteArtifacts ?? outcome.artifacts
  const pdfFile = quoteFiles.find((entry) => entry.kind === 'pdf')
  const excelFile = quoteFiles.find((entry) => entry.kind === 'xlsx' && entry.name.startsWith('bao_gia'))
  const costingFile = outcome.artifacts.find((entry) => entry.kind === 'xlsx' && entry.name.startsWith('gia_thanh'))
  const quotePreviewSrc = pdfFile ? `${pdfFile.url}?inline=1&v=${previewKey}` : ''
  const totalBars = outcome.cut_plan.reduce((sum, group) => sum + group.bars, 0)
  const totalWaste = outcome.cut_plan.reduce((sum, group) => sum + group.waste_m, 0)

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Metric label="Hạng mục" value={summary.items} hint={`${summary.total_leaves} cánh`} />
        <Metric label="Diện tích" value={num(summary.area_m2, 2)} unit="m²" />
        <Metric label="Nhôm" value={num(summary.alum_kg, 1)} unit="kg" />
        <Metric label="Kính" value={num(summary.glass_m2, 1)} unit="m²" />
        <Metric label="Giá vốn" value={money(summary.cost_total)} unit="đ" />
        <Metric label="Doanh thu" value={money(summary.price)} unit="đ" />
        <Metric label="VAT" value={money(summary.vat)} unit="đ" />
        <Metric label="Tổng thanh toán" value={money(summary.price_with_vat)} unit="đ" accent />
      </div>

      <SectionCard
        title="Báo giá — xem trước trước khi gửi"
        description="Sửa thông tin trên báo giá rồi bấm Cập nhật; khung bên dưới là đúng bản PDF sẽ gửi khách"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" onClick={() => void regenerateQuote()} disabled={quoteBusy}>
              <RefreshCw className="h-3.5 w-3.5" /> {quoteBusy ? 'Đang cập nhật…' : 'Cập nhật & xem trước'}
            </Button>
            {pdfFile ? (
              <QuickLink href={pdfFile.url} download icon={<FileText className="h-3.5 w-3.5" />}>
                Tải PDF
              </QuickLink>
            ) : null}
            {excelFile ? (
              <QuickLink href={excelFile.url} download icon={<FileSpreadsheet className="h-3.5 w-3.5" />}>
                Tải Excel
              </QuickLink>
            ) : null}
          </div>
        }
      >
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          <Label>
            Đơn vị yêu cầu báo giá
            <Input
              value={quoteInfo.request_org}
              onChange={(event) => setQuoteInfo({ ...quoteInfo, request_org: event.target.value })}
              placeholder="Công ty / chủ đầu tư"
            />
          </Label>
          <Label>
            Người nhận / liên hệ
            <Input
              value={quoteInfo.request_contact}
              onChange={(event) => setQuoteInfo({ ...quoteInfo, request_contact: event.target.value })}
              placeholder="Anh/chị phụ trách"
            />
          </Label>
          <Label>
            ĐT liên hệ
            <Input
              value={quoteInfo.request_phone}
              onChange={(event) => setQuoteInfo({ ...quoteInfo, request_phone: event.target.value })}
              placeholder="09xx xxx xxx"
            />
          </Label>
          <Label>
            Người báo giá
            <Input
              value={quoteInfo.quoted_by}
              onChange={(event) => setQuoteInfo({ ...quoteInfo, quoted_by: event.target.value })}
              placeholder="Tên nhân viên báo giá"
            />
          </Label>
          <Label>
            ĐT người báo giá
            <Input
              value={quoteInfo.quoted_by_phone}
              onChange={(event) => setQuoteInfo({ ...quoteInfo, quoted_by_phone: event.target.value })}
              placeholder="09xx xxx xxx"
            />
          </Label>
        </div>
        <div className="mt-3 overflow-hidden rounded-lg border border-border bg-slate-100">
          {quotePreviewSrc ? (
            <iframe src={quotePreviewSrc} title="Xem trước báo giá PDF" className="h-[720px] w-full bg-white" />
          ) : (
            <div className="py-12 text-center text-xs text-muted-foreground">
              Chưa có PDF báo giá — bấm “Cập nhật &amp; xem trước” để sinh bản xem trước.
            </div>
          )}
        </div>
      </SectionCard>

      <SectionCard
        title="Hạng mục &amp; file tải về"
        description={`Xuất lúc ${summary.generated_at}`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {pdfFile ? (
              <QuickLink href={pdfFile.url} download icon={<FileText className="h-3.5 w-3.5" />}>
                Báo giá PDF
              </QuickLink>
            ) : null}
            {excelFile ? (
              <QuickLink href={excelFile.url} download icon={<FileSpreadsheet className="h-3.5 w-3.5" />}>
                Excel báo giá
              </QuickLink>
            ) : null}
            {costingFile ? (
              <QuickLink href={costingFile.url} icon={<FileSpreadsheet className="h-3.5 w-3.5" />}>
                Giá thành
              </QuickLink>
            ) : null}
          </div>
        }
      >
        <Table>
          <thead>
            <tr>
              <th>Mã</th>
              <th>Loại cửa</th>
              <th>Hệ</th>
              <th>R × C</th>
              <th className="text-right">SL</th>
              <th className="text-right">DT (m²)</th>
              <th className="text-right">Nhôm (kg)</th>
              <th className="text-right">Kính (m²)</th>
              <th className="text-right">Giá bán</th>
              <th>File</th>
            </tr>
          </thead>
          <tbody>
            {outcome.items.length === 0 ? (
              <EmptyRow colSpan={10}>Không có hạng mục.</EmptyRow>
            ) : (
              outcome.items.map((item) => (
                <tr key={item.tag}>
                  <td className="font-semibold text-primary">{item.tag}</td>
                  <td>{item.type_label}</td>
                  <td>
                    <Badge variant="outline">{item.system}</Badge>
                  </td>
                  <td className="tabular-nums">
                    {num(item.width_mm)} × {num(item.height_mm)}
                  </td>
                  <td className="text-right tabular-nums">{item.qty}</td>
                  <td className="text-right tabular-nums">{num(item.area_m2, 2)}</td>
                  <td className="text-right tabular-nums">{num(item.alum_kg, 2)}</td>
                  <td className="text-right tabular-nums">{num(item.glass_m2, 2)}</td>
                  <td className="text-right tabular-nums">{money(item.price)}</td>
                  <td>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(item.files).map(([kind, href]) => (
                        <FileLink key={kind} kind={kind} href={href} />
                      ))}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </Table>
      </SectionCard>

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <SectionCard
          title="Xem trước"
          description="Xoay mô hình 3D (bản lề/khóa hiển thị) hoặc xem bản vẽ 2D sản xuất"
          actions={
            <Tabs
              variant="segmented"
              value={view}
              onChange={(value) => setView(value as '3d' | 'drawing')}
              items={[
                { value: '3d', label: '3D (xoay)' },
                { value: 'drawing', label: 'Bản vẽ' },
              ]}
            />
          }
        >
          <Tabs
            variant="segmented"
            className="mb-3"
            value={active?.tag ?? ''}
            onChange={setSelectedTag}
            items={outcome.items.map((item) => ({ value: item.tag, label: item.tag }))}
          />
          {view === '3d' ? (
            <React.Suspense
              fallback={
                <div className="grid place-items-center rounded-lg border border-dashed border-input py-16 text-xs text-muted-foreground">
                  Đang tải trình xem 3D…
                </div>
              }
            >
              <ModelViewer3D item={planItem} fallbackUrl={active?.files?.preview} height={520} />
            </React.Suspense>
          ) : previewUrl ? (
            <img
              src={previewUrl}
              alt={`${active?.tag} bản vẽ`}
              className="w-full rounded-lg border border-border bg-white"
            />
          ) : (
            <div className="rounded-lg border border-dashed border-input py-10 text-center text-xs text-muted-foreground">
              Hạng mục này chưa có bản vẽ
            </div>
          )}
        </SectionCard>

        <div className="space-y-4">
          <SectionCard title="Cảnh báo / lỗi" description={`${summary.errors} lỗi · ${summary.warnings} cảnh báo`}>
            <ul className="space-y-1.5 text-xs">
              {outcome.issues.length === 0 ? (
                <li className="text-muted-foreground">Không có cảnh báo.</li>
              ) : (
                outcome.issues.map((issue, index) => (
                  <li
                    key={`${issue.code ?? 'issue'}-${index}`}
                    className={cn(
                      'rounded-md px-2.5 py-1.5',
                      issue.level === 'error' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-800',
                    )}
                  >
                    {issue.tag ? <b>[{issue.tag}] </b> : null}
                    {issue.message}
                  </li>
                ))
              )}
            </ul>
          </SectionCard>

          <SectionCard title="FreeCAD 3D">
            <FreecadBox info={outcome.freecad} />
          </SectionCard>

          <SectionCard title="Tối ưu cắt nhôm" description={`${totalBars} cây · phế ${num(totalWaste, 2)} m`}>
            <div className="max-h-[320px] space-y-3 overflow-auto pr-1">
              {outcome.cut_plan.length === 0 ? (
                <p className="text-xs text-muted-foreground">Không có dữ liệu cắt.</p>
              ) : (
                outcome.cut_plan.map((group) => (
                  <div key={group.profile_code} className="text-xs">
                    <div className="flex flex-wrap items-center gap-2">
                      <b className="text-primary">{group.profile_code}</b>
                      <span className="text-muted-foreground">{group.profile_name}</span>
                      <Badge variant="outline">
                        {group.bars} cây × {num(group.stock_mm)} mm
                      </Badge>
                      <Badge variant={group.waste_percent > 20 ? 'warn' : 'ok'}>
                        phế {num(group.waste_m, 2)} m ({num(group.waste_percent, 1)}%)
                      </Badge>
                    </div>
                    <div className="mt-1 space-y-0.5">
                      {group.patterns.slice(0, 5).map((pattern, index) => (
                        <div key={index} className="mono text-[11px] text-slate-600">
                          {pattern}
                        </div>
                      ))}
                      {group.patterns.length > 5 ? (
                        <div className="mono text-[11px] text-muted-foreground">
                          … +{group.patterns.length - 5} cây
                        </div>
                      ) : null}
                    </div>
                  </div>
                ))
              )}
            </div>
          </SectionCard>
        </div>
      </div>

      <SectionCard title="Tất cả file" description={`${outcome.artifacts.length} file trong ${outcome.out_dir}`}>
        <div className="flex flex-wrap gap-2">
          {outcome.artifacts.map((artifact) => (
            <a
              key={artifact.name}
              href={artifact.url}
              download
              className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs text-primary transition-colors hover:bg-secondary"
            >
              <span className="rounded bg-secondary px-1.5 py-0.5 text-[10px] font-semibold uppercase">
                {ARTIFACT_LABEL[artifact.kind] ?? artifact.kind}
              </span>
              {artifact.name}
              <span className="text-[10px] text-muted-foreground">{fileSize(artifact.size)}</span>
            </a>
          ))}
        </div>
      </SectionCard>
    </div>
  )
}
