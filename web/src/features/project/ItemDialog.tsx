import * as React from 'react'
import { Badge, Button, Input, Label, Select, Textarea } from '@/components/ui/primitives'
import { Dialog } from '@/components/ui/overlays'
import { panelsToText, textToPanels, textToTransoms, transomsToText } from '@/lib/panels'
import { glassFromCatalog } from '@/lib/project'
import { money } from '@/lib/format'
import { componentName, componentOf, componentPrice, recommendedHingeCount } from '@/lib/hardware'
import type { Catalog, ItemSpec, SystemSummary } from '@/types/api'

interface ItemDialogProps {
  open: boolean
  item: ItemSpec | null
  systems: SystemSummary[]
  catalog: Catalog | null
  itemTypes: Record<string, string>
  onClose: () => void
  onSave: (item: ItemSpec) => void
}

const PANEL_PRESETS: { label: string; text: string }[] = [
  { label: '2 cánh quay', text: 'sash:L, sash:R' },
  { label: '1 cánh quay', text: 'sash:L' },
  { label: '2 cánh lùa', text: 'sash:slide, sash:slide' },
  { label: 'Cố định', text: 'fixed' },
  { label: 'Chia 60/40', text: 'sash:L:0.6, sash:R:0.4' },
]

export function ItemDialog({ open, item, systems, catalog, itemTypes, onClose, onSave }: ItemDialogProps) {
  const [draft, setDraft] = React.useState<ItemSpec | null>(item)
  const [panelText, setPanelText] = React.useState('')
  const [transomText, setTransomText] = React.useState('')

  React.useEffect(() => {
    if (!open || !item) return
    setDraft({ ...item })
    setPanelText(panelsToText(item.panels))
    setTransomText(transomsToText(item.transoms))
  }, [open, item])

  if (!draft) return null

  const patch = (values: Partial<ItemSpec>) => setDraft((prev) => (prev ? { ...prev, ...values } : prev))

  const handleSave = () => {
    onSave({
      ...draft,
      tag: draft.tag.trim(),
      width_mm: Number(draft.width_mm) || 0,
      height_mm: Number(draft.height_mm) || 0,
      qty: Math.max(1, Number(draft.qty) || 1),
      sill_mm: Number(draft.sill_mm) || 0,
      panels: textToPanels(panelText, draft.type),
      transoms: textToTransoms(transomText),
      glass: glassFromCatalog(catalog, draft.glass.key),
    })
  }

  const glassOptions = Object.entries(catalog?.glass ?? {})
  const hingeOptions =
    catalog?.hardware?.hinge_options ??
    Object.keys(catalog?.hardware?.components ?? {}).filter((key) => key.startsWith('hinge_'))
  const lockOptions =
    catalog?.hardware?.lock_options ??
    Object.keys(catalog?.hardware?.components ?? {}).filter((key) => key.startsWith('lock_'))
  const hingeChoice = componentOf(catalog, draft.hinge_type ?? 'hinge')
  const lockChoice = componentOf(catalog, draft.lock_type ?? 'lock')
  const suggestedHinges = recommendedHingeCount(draft.height_mm)

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={`Cửa ${draft.tag || '(chưa có mã)'}`}
      description={`${draft.width_mm} × ${draft.height_mm} mm — sửa thông số rồi bấm Lưu`}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Hủy
          </Button>
          <Button onClick={handleSave}>Lưu cửa</Button>
        </>
      }
      className="max-w-3xl"
    >
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Label>
          Mã cửa
          <Input value={draft.tag} onChange={(event) => patch({ tag: event.target.value })} placeholder="C1" />
        </Label>
        <Label className="col-span-2">
          Vị trí
          <Input value={draft.room} onChange={(event) => patch({ room: event.target.value })} placeholder="Phòng khách" />
        </Label>
        <Label>
          SL
          <Input type="number" min={1} value={draft.qty} onChange={(event) => patch({ qty: Number(event.target.value) })} />
        </Label>

        <Label className="col-span-2">
          Loại cửa
          <Select value={draft.type} onChange={(event) => patch({ type: event.target.value as ItemSpec['type'] })}>
            {Object.entries(itemTypes).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
        </Label>
        <Label className="col-span-2">
          Hệ nhôm
          <Select value={draft.system ?? ''} onChange={(event) => patch({ system: event.target.value || null })}>
            {systems.map((system) => (
              <option key={system.code} value={system.code}>
                {system.code} — {system.name}
              </option>
            ))}
          </Select>
        </Label>

        <Label>
          Rộng (mm)
          <Input
            type="number"
            step={10}
            value={draft.width_mm}
            onChange={(event) => patch({ width_mm: Number(event.target.value) })}
          />
        </Label>
        <Label>
          Cao (mm)
          <Input
            type="number"
            step={10}
            value={draft.height_mm}
            onChange={(event) => patch({ height_mm: Number(event.target.value) })}
          />
        </Label>
        <Label>
          Cao độ đặt (mm)
          <Input
            type="number"
            step={50}
            value={draft.sill_mm}
            onChange={(event) => patch({ sill_mm: Number(event.target.value) })}
          />
        </Label>
        <Label>
          Kính
          <Select
            value={draft.glass.key}
            onChange={(event) => patch({ glass: glassFromCatalog(catalog, event.target.value) })}
          >
            {glassOptions.map(([key, glass]) => (
              <option key={key} value={key}>
                {glass.name}
              </option>
            ))}
          </Select>
        </Label>
      </div>

      <div className="mt-4 rounded-lg border border-border bg-secondary/40 p-3">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <span className="text-[13px] font-semibold text-primary">Bản lề &amp; khóa</span>
          <span className="text-[11px] text-muted-foreground">
            Gợi ý: <b>{suggestedHinges}</b> bản lề cho cánh cao {draft.height_mm}mm
          </span>
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          <Label>
            Số bản lề / cánh
            <Select
              value={draft.hinge_count ?? ''}
              onChange={(event) =>
                patch({ hinge_count: event.target.value === '' ? null : Number(event.target.value) })
              }
            >
              <option value="">Tự động (theo hệ)</option>
              <option value="0">Không bản lề</option>
              {[2, 3, 4, 5, 6].map((count) => (
                <option key={count} value={count}>
                  {count} cái{count === suggestedHinges ? ' (gợi ý)' : ''}
                </option>
              ))}
            </Select>
          </Label>
          <Label>
            Loại bản lề
            <Select
              value={draft.hinge_type ?? ''}
              onChange={(event) => patch({ hinge_type: event.target.value || null })}
            >
              <option value="">Mặc định ({componentName(catalog, 'hinge')})</option>
              {hingeOptions.map((key) => (
                <option key={key} value={key}>
                  {componentName(catalog, key)} — {money(componentPrice(catalog, key))}đ
                </option>
              ))}
            </Select>
          </Label>
          <Label>
            Loại khóa
            <Select
              value={draft.lock_type ?? ''}
              onChange={(event) => patch({ lock_type: event.target.value || null })}
            >
              <option value="">Mặc định ({componentName(catalog, 'lock')})</option>
              <option value="none">Không khóa</option>
              {lockOptions.map((key) => (
                <option key={key} value={key}>
                  {componentName(catalog, key)} — {money(componentPrice(catalog, key))}đ
                </option>
              ))}
            </Select>
          </Label>
        </div>
        <p className="mt-1.5 text-[11px] leading-relaxed text-muted-foreground">
          {hingeChoice ? (
            <>
              Bản lề: <b>{hingeChoice.name}</b> · {money(hingeChoice.price)} đ/{hingeChoice.unit}
              {hingeChoice.note ? ` · ${hingeChoice.note}` : ''}.{' '}
            </>
          ) : null}
          {lockChoice ? (
            <>
              Khóa: <b>{lockChoice.name}</b> · {money(lockChoice.price)} đ/{lockChoice.unit}
              {lockChoice.note ? ` · ${lockChoice.note}` : ''}.
            </>
          ) : null}
          {' '}Giá lấy từ tab Catalogue → sửa theo nhà cung cấp của bạn.
        </p>
      </div>

      <div className="mt-4 space-y-3">
        <div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="field-label">Chia cánh</span>
            <div className="flex flex-wrap gap-1">
              {PANEL_PRESETS.map((preset) => (
                <button
                  key={preset.label}
                  type="button"
                  onClick={() => setPanelText(preset.text)}
                  className="rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground transition-colors hover:border-primary hover:text-primary"
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>
          <Input
            className="mt-1.5"
            value={panelText}
            onChange={(event) => setPanelText(event.target.value)}
            placeholder="sash:L, sash:R hoặc fixed hoặc sash:slide"
          />
          <p className="mt-1 text-[11px] text-muted-foreground">
            Để trống = tự chia theo kích thước. Cú pháp: <code>sash:L</code>, <code>sash:R:0.6</code>,{' '}
            <code>fixed</code>, <code>sash:slide</code>.
            {panelText ? (
              <Badge variant="outline" className="ml-2 normal-case">
                {textToPanels(panelText, draft.type).length} cột
              </Badge>
            ) : null}
          </p>
        </div>

        <div>
          <span className="field-label">Đố ngang</span>
          <Input
            className="mt-1.5"
            value={transomText}
            onChange={(event) => setTransomText(event.target.value)}
            placeholder="h@500:fixed; h@1500"
          />
          <p className="mt-1 text-[11px] text-muted-foreground">
            Đo từ mép trên. <code>:fixed</code> = ô phía trên là kính cố định.
          </p>
        </div>

        <Label>
          Ghi chú
          <Textarea
            className="min-h-[70px]"
            value={draft.notes}
            onChange={(event) => patch({ notes: event.target.value })}
            placeholder="Có lam chắn nắng, tay nắm Kinlong..."
          />
        </Label>
      </div>
    </Dialog>
  )
}
