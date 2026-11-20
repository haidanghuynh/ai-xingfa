import * as React from 'react'
import { Copy, FileJson, FolderOpen, Hammer, Loader2, Pencil, Plus, RotateCcw, Sparkles, Trash2 } from 'lucide-react'
import { Badge, Button, CheckField, Input, Label, Select } from '@/components/ui/primitives'
import { EmptyRow, SectionCard, Table } from '@/components/ui/layout'
import { useToast } from '@/components/ui/overlays'
import { ItemDialog } from '@/features/project/ItemDialog'
import { num } from '@/lib/format'
import { hardwareSummary } from '@/lib/hardware'
import { panelsToText, transomsToText } from '@/lib/panels'
import { emptyItem, glassFromCatalog, normalizeProject } from '@/lib/project'
import { cn } from '@/lib/utils'
import type { Catalog, Issue, ItemSpec, ProjectSpec, StatusInfo, SystemSummary } from '@/types/api'

export interface ProjectTabProps {
  project: ProjectSpec
  systems: SystemSummary[]
  catalog: Catalog | null
  status: StatusInfo | null
  busy: boolean
  with3d: boolean
  pricingMode: 'bom' | 'book'
  priceLevel: string
  priceLevels: { code: string; name: string; show_in_quote?: boolean }[]
  issues: Issue[] | null
  issueTitle: string
  onChange: (project: ProjectSpec) => void
  onWith3dChange: (value: boolean) => void
  onPricingModeChange: (mode: 'bom' | 'book') => void
  onPriceLevelChange: (code: string) => void
  onValidate: () => void
  onBuild: () => void
  onLoadDemo: () => void
  onReset: () => void
}

export function ProjectTab({
  project,
  systems,
  catalog,
  status,
  busy,
  with3d,
  pricingMode,
  priceLevel,
  priceLevels,
  issues,
  issueTitle,
  onChange,
  onWith3dChange,
  onPricingModeChange,
  onPriceLevelChange,
  onValidate,
  onBuild,
  onLoadDemo,
  onReset,
}: ProjectTabProps) {
  const toast = useToast()
  const [editing, setEditing] = React.useState<{ index: number; item: ItemSpec } | null>(null)
  const fileRef = React.useRef<HTMLInputElement>(null)
  const itemTypes = status?.item_types ?? {}

  const patchInfo = (values: Partial<ProjectSpec['project']>) =>
    onChange({ ...project, project: { ...project.project, ...values } })
  const patchDefaults = (values: Partial<ProjectSpec['defaults']>) =>
    onChange({ ...project, defaults: { ...project.defaults, ...values } })
  const setItems = (items: ItemSpec[]) => onChange({ ...project, items })

  const saveItem = (item: ItemSpec) => {
    if (!editing) return
    const items = [...project.items]
    if (editing.index < 0) items.push(item)
    else items[editing.index] = item
    setItems(items)
    setEditing(null)
  }

  const duplicateItem = (index: number) => {
    const clone: ItemSpec = JSON.parse(JSON.stringify(project.items[index]))
    const existing = new Set(project.items.map((item) => item.tag))
    let counter = project.items.length + 1
    while (existing.has(`C${counter}`)) counter += 1
    clone.tag = `C${counter}`
    const items = [...project.items]
    items.splice(index + 1, 0, clone)
    setItems(items)
  }

  const exportJson = () => {
    const blob = new Blob([JSON.stringify(project, null, 2)], { type: 'application/json' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `${project.project.code || 'du-an'}.json`
    link.click()
    URL.revokeObjectURL(link.href)
  }

  const importJson = async (file: File) => {
    try {
      const raw = JSON.parse(await file.text())
      onChange(normalizeProject(raw, project, catalog))
      toast.push('Đã mở file JSON', 'success')
    } catch (error) {
      toast.push(`JSON không hợp lệ: ${(error as Error).message}`, 'error')
    }
  }

  const totalQty = project.items.reduce((sum, item) => sum + (Number(item.qty) || 0), 0)
  const totalArea = project.items.reduce(
    (sum, item) =>
      sum + ((Number(item.width_mm) || 0) * (Number(item.height_mm) || 0) * (Number(item.qty) || 0)) / 1_000_000,
    0,
  )
  const errorCount = (issues ?? []).filter((issue) => issue.level === 'error').length

  return (
    <div className="space-y-4">
      <SectionCard
        title="Thông tin dự án"
        description="Mã, khách hàng và cấu hình mặc định cho toàn bộ hạng mục"
        actions={
          <>
            <Button variant="outline" size="sm" onClick={onLoadDemo}>
              <Sparkles className="h-3.5 w-3.5" /> Dự án mẫu
            </Button>
            <Button variant="outline" size="sm" onClick={exportJson}>
              <FileJson className="h-3.5 w-3.5" /> Xuất JSON
            </Button>
            <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
              <FolderOpen className="h-3.5 w-3.5" /> Mở JSON
            </Button>
            <Button variant="ghost" size="sm" onClick={onReset}>
              <RotateCcw className="h-3.5 w-3.5" /> Làm mới
            </Button>
            <input
              ref={fileRef}
              type="file"
              accept=".json,application/json"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0]
                if (file) void importJson(file)
                event.target.value = ''
              }}
            />
          </>
        }
      >
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Label>
            Mã dự án
            <Input value={project.project.code} onChange={(event) => patchInfo({ code: event.target.value })} />
          </Label>
          <Label>
            Tên dự án
            <Input value={project.project.name} onChange={(event) => patchInfo({ name: event.target.value })} />
          </Label>
          <Label>
            Khách hàng
            <Input value={project.project.customer} onChange={(event) => patchInfo({ customer: event.target.value })} />
          </Label>
          <Label>
            Địa chỉ
            <Input value={project.project.address} onChange={(event) => patchInfo({ address: event.target.value })} />
          </Label>
          <Label>
            Đơn vị yêu cầu báo giá
            <Input
              value={project.project.request_org ?? ''}
              onChange={(event) => patchInfo({ request_org: event.target.value })}
            />
          </Label>
          <Label>
            Người nhận / liên hệ
            <Input
              value={project.project.request_contact ?? ''}
              onChange={(event) => patchInfo({ request_contact: event.target.value })}
            />
          </Label>
          <Label>
            ĐT liên hệ
            <Input
              value={project.project.request_phone ?? ''}
              onChange={(event) => patchInfo({ request_phone: event.target.value })}
            />
          </Label>
          <Label>
            Người báo giá
            <Input
              value={project.project.quoted_by ?? ''}
              onChange={(event) => patchInfo({ quoted_by: event.target.value })}
            />
          </Label>
          <Label>
            ĐT người báo giá
            <Input
              value={project.project.quoted_by_phone ?? ''}
              onChange={(event) => patchInfo({ quoted_by_phone: event.target.value })}
            />
          </Label>
          <Label>
            Ngày
            <Input
              type="date"
              value={project.project.date}
              onChange={(event) => patchInfo({ date: event.target.value })}
            />
          </Label>
          <Label>
            Hệ nhôm mặc định
            <Select
              value={project.defaults.system}
              onChange={(event) => {
                const system = event.target.value
                patchDefaults({ system })
                setItems(project.items.map((item) => ({ ...item, system })))
              }}
            >
              {systems.map((system) => (
                <option key={system.code} value={system.code}>
                  {system.code} — {system.name}
                </option>
              ))}
            </Select>
          </Label>
          <Label>
            Kính mặc định
            <Select
              value={project.defaults.glass.key}
              onChange={(event) => {
                const glass = glassFromCatalog(catalog, event.target.value)
                patchDefaults({ glass })
                setItems(project.items.map((item) => ({ ...item, glass: { ...glass } })))
              }}
            >
              {Object.entries(catalog?.glass ?? {}).map(([key, glass]) => (
                <option key={key} value={key}>
                  {glass.name}
                </option>
              ))}
            </Select>
          </Label>
          <Label>
            Màu nhôm / phụ kiện
            <div className="grid grid-cols-2 gap-2">
              <Input value={project.defaults.color} onChange={(event) => patchDefaults({ color: event.target.value })} />
              <Input
                value={project.defaults.hardware}
                onChange={(event) => patchDefaults({ hardware: event.target.value })}
              />
            </div>
          </Label>
        </div>
      </SectionCard>

      <SectionCard
        title={
          <span className="flex items-center gap-2">
            Hạng mục cửa <Badge>{project.items.length}</Badge>
            <span className="text-xs font-normal text-muted-foreground">
              {num(totalQty)} bộ · {num(totalArea, 2)} m²
            </span>
          </span>
        }
        description="Mỗi dòng là một hạng mục; bấm Sửa để nhập chi tiết chia cánh / đố ngang"
        actions={
          <Button
            size="sm"
            onClick={() => setEditing({ index: -1, item: emptyItem(project.items.length, project) })}
          >
            <Plus className="h-3.5 w-3.5" /> Thêm cửa
          </Button>
        }
      >
        <Table>
          <thead>
            <tr>
              <th className="w-16">Mã</th>
              <th>Vị trí</th>
              <th>Loại cửa</th>
              <th>Hệ</th>
              <th className="w-24">R × C</th>
              <th className="w-12 text-right">SL</th>
              <th>Cánh</th>
              <th>Đố ngang</th>
              <th>Phụ kiện</th>
              <th>Kính</th>
              <th className="w-24 text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {project.items.length === 0 ? (
              <EmptyRow colSpan={11}>
                Chưa có cửa nào — bấm <b>Thêm cửa</b> hoặc <b>Dự án mẫu</b>.
              </EmptyRow>
            ) : (
              project.items.map((item, index) => (
                <tr key={`${item.tag}-${index}`}>
                  <td className="font-semibold text-primary">{item.tag}</td>
                  <td className="text-muted-foreground">{item.room || '—'}</td>
                  <td>{itemTypes[item.type] ?? item.type}</td>
                  <td>
                    <Badge variant="outline">{item.system ?? project.defaults.system}</Badge>
                  </td>
                  <td className="tabular-nums">
                    {num(item.width_mm)} × {num(item.height_mm)}
                  </td>
                  <td className="text-right tabular-nums">{item.qty}</td>
                  <td className="text-xs text-muted-foreground">{panelsToText(item.panels) || 'tự động'}</td>
                  <td className="text-xs text-muted-foreground">{transomsToText(item.transoms) || '—'}</td>
                  <td className="text-xs text-muted-foreground">{hardwareSummary(item, catalog) || '—'}</td>
                  <td className="text-xs text-muted-foreground">
                    {catalog?.glass?.[item.glass.key]?.name ?? item.glass.name}
                  </td>
                  <td>
                    <div className="flex justify-end">
                      <Button variant="ghost" size="icon" title="Sửa" onClick={() => setEditing({ index, item })}>
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon" title="Nhân bản" onClick={() => duplicateItem(index)}>
                        <Copy className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        title="Xóa"
                        className="text-destructive hover:bg-destructive/10"
                        onClick={() => setItems(project.items.filter((_, position) => position !== index))}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </Table>
        <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
          Cánh: <code>sash:L, sash:R</code> hoặc tỷ lệ <code>sash:L:0.6, sash:R:0.4</code>; cố định{' '}
          <code>fixed</code>; lùa <code>sash:slide</code>; để trống = tự động chia theo kích thước. Đố ngang:{' '}
          <code>h@500:fixed; h@1500</code> (đo từ mép trên).
        </p>
      </SectionCard>

      {issues ? (
        <SectionCard
          title={
            <span className="flex items-center gap-2">
              {issueTitle}
              {errorCount > 0 ? <Badge variant="danger">{errorCount} lỗi</Badge> : <Badge variant="ok">hợp lệ</Badge>}
            </span>
          }
          description="Kết quả kiểm tra dữ liệu — lỗi phải sửa trước khi build"
        >
          <ul className="space-y-1.5">
            {issues.length === 0 ? (
              <li className="text-xs text-muted-foreground">Không có cảnh báo nào.</li>
            ) : (
              issues.map((issue, index) => (
                <li
                  key={`${issue.code ?? 'issue'}-${index}`}
                  className={cn(
                    'rounded-md px-3 py-1.5 text-xs',
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
      ) : null}

      <ItemDialog
        open={editing !== null}
        item={editing?.item ?? null}
        systems={systems}
        catalog={catalog}
        itemTypes={itemTypes}
        onClose={() => setEditing(null)}
        onSave={saveItem}
      />

      <div className="sticky bottom-0 z-20 flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card/95 px-4 py-3 shadow-lg backdrop-blur">
        <Button variant="outline" onClick={onValidate} disabled={busy}>
          Kiểm tra dữ liệu
        </Button>
        <Button variant="accent" onClick={onBuild} disabled={busy}>
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Hammer className="h-4 w-4" />}
          Build: 3D + Bản vẽ 2D + Báo giá
        </Button>
        <CheckField
          label="Gọi FreeCAD (3D)"
          checked={with3d}
          onChange={(event) => onWith3dChange(event.target.checked)}
        />
        <span className="h-5 w-px bg-border" />
        <span className="text-[11px] font-semibold text-muted-foreground">Cách tính giá</span>
        <Select
          className="h-8 w-[200px]"
          value={pricingMode}
          onChange={(event) => onPricingModeChange(event.target.value as 'bom' | 'book')}
        >
          <option value="bom">Chi tiết BOM</option>
          <option value="book">Theo bảng giá ban hành</option>
        </Select>
        {pricingMode === 'book' ? (
          <Select
            className="h-8 w-[160px]"
            value={priceLevel}
            onChange={(event) => onPriceLevelChange(event.target.value)}
          >
            {priceLevels.map((level) => (
              <option key={level.code} value={level.code}>
                {level.name}
                {level.show_in_quote === false ? ' (ẩn bảng giá)' : ''}
              </option>
            ))}
          </Select>
        ) : null}
        <span className="text-xs text-muted-foreground">
          {busy ? 'Đang xử lý…' : `${project.items.length} cửa sẵn sàng build`}
        </span>
      </div>
    </div>
  )
}
