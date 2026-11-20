import * as React from 'react'
import { ClipboardCopy, FileJson, ImagePlus, Sparkles, Wand2 } from 'lucide-react'
import { Badge, Button, Input, Label, Select, Textarea } from '@/components/ui/primitives'
import { SectionCard, Table } from '@/components/ui/layout'
import { useToast } from '@/components/ui/overlays'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import type { AIStatus, ExtractedItem, ItemSpec, ItemType, StatusInfo } from '@/types/api'

interface ImageTabProps {
  status: StatusInfo | null
  onApplyItems: (items: Partial<ItemSpec>[]) => void
}

const REVIEW_LABELS: Record<string, string> = {
  kich_thuoc: 'thiếu kích thước',
  loai_cua: 'loại cửa?',
  chia_canh: 'chia cánh?',
  do_tin_cay_thap: 'AI không chắc',
  trung_ma: 'trùng mã',
  so_canh: 'số cánh?',
  huong_mo: 'hướng mở?',
  vat_lieu: 'vật liệu?',
  room: 'vị trí?',
  sill_mm: 'cao độ?',
}

function panelsSummary(item: ExtractedItem): string {
  const panels = item.panels ?? []
  if (!panels.length) return '—'
  const sash = panels.filter((panel) => panel.kind === 'sash').length
  const fixed = panels.length - sash
  const slide = panels.some((panel) => panel.open === 'slide')
  const parts = [`${panels.length} ô`, `${sash} cánh ${slide ? 'lùa' : 'mở'}`]
  if (fixed) parts.push(`${fixed} cố định`)
  return parts.join(' · ')
}

const emptyItem = (index: number): ExtractedItem => ({
  tag: `C${index + 1}`,
  room: '',
  qty: 1,
  type: 'casement',
  width_mm: null,
  height_mm: null,
  sill_mm: 900,
  panels: [],
  transoms: [],
  glass: { key: 'cuong_luc_8', name: 'Kính cường lực 8mm', thickness_mm: 8 },
  notes: '',
  confidence: 1,
  needs_review: [],
})

export function ImageTab({ status, onApplyItems }: ImageTabProps) {
  const toast = useToast()
  const [imageData, setImageData] = React.useState<string | null>(null)
  const [promptText, setPromptText] = React.useState('')
  const [jsonText, setJsonText] = React.useState('')
  const [note, setNote] = React.useState('')
  const [busy, setBusy] = React.useState(false)
  const [ai, setAi] = React.useState<AIStatus | null>(null)
  const [provider, setProvider] = React.useState('')
  const [model, setModel] = React.useState('')
  const [draft, setDraft] = React.useState<ExtractedItem[]>([])
  const [chosen, setChosen] = React.useState<Record<string, boolean>>({})
  const [warnings, setWarnings] = React.useState<string[]>([])
  const fileRef = React.useRef<HTMLInputElement>(null)
  const itemTypes = status?.item_types ?? {}

  React.useEffect(() => {
    api
      .aiStatus()
      .then((info) => {
        setAi(info)
        const preferred =
          info.providers.find(
            (entry) => entry.name === info.default_provider && entry.vision && entry.available,
          ) ??
          info.providers.find((entry) => entry.vision && entry.available) ??
          info.providers.find((entry) => entry.vision)
        if (preferred) {
          setProvider(preferred.name)
          setModel(preferred.model)
        }
      })
      .catch(() => undefined)
  }, [])

  const current = ai?.providers.find((entry) => entry.name === provider) ?? null

  const handleFile = (file: File) => {
    const reader = new FileReader()
    reader.onload = () => {
      setImageData(String(reader.result))
      setNote(`Đã nạp ảnh (${Math.round(file.size / 1024)} KB)`)
    }
    reader.readAsDataURL(file)
  }

  const loadPrompt = async () => {
    try {
      setPromptText(await api.prompt())
    } catch (error) {
      toast.push((error as Error).message, 'error')
    }
  }

  const copyPrompt = async () => {
    if (!promptText) {
      toast.push('Bấm "Sinh prompt" trước', 'error')
      return
    }
    try {
      await navigator.clipboard.writeText(promptText)
      toast.push('Đã copy prompt', 'success')
    } catch {
      toast.push('Trình duyệt chặn clipboard — hãy copy thủ công', 'error')
    }
  }

  const callAI = async () => {
    if (!imageData) {
      toast.push('Chọn ảnh trước', 'error')
      return
    }
    if (!current?.available) {
      toast.push(
        `Chưa cấu hình ${current?.api_key_env ?? 'API key'} — dùng cách dán JSON từ ChatGPT bên dưới`,
        'error',
      )
      return
    }
    setBusy(true)
    setNote(`Đang gọi ${current.label}…`)
    try {
      const result = await api.extract(imageData, provider, model || undefined)
      setDraft(result.items)
      setChosen(Object.fromEntries(result.items.map((_item, index) => [String(index), true])))
      setWarnings(result.warnings ?? [])
      setJsonText(JSON.stringify(result.data ?? { items: result.items }, null, 2))
      setNote(
        `${result.provider} · ${result.model} · ${result.items.length} cửa — kiểm tra rồi nhập vào dự án`,
      )
      toast.push('Đã trích xuất xong', 'success')
    } catch (error) {
      setNote('')
      toast.push((error as Error).message, 'error')
    } finally {
      setBusy(false)
    }
  }

  const parseJsonToDraft = () => {
    try {
      const parsed = JSON.parse(jsonText) as { items?: Partial<ItemSpec>[] } | Partial<ItemSpec>[]
      const items = Array.isArray(parsed) ? parsed : parsed.items ?? []
      if (!items.length) {
        toast.push('JSON không có danh sách cửa', 'error')
        return
      }
      const next = items.map((item, index) => ({
        ...emptyItem(index),
        ...item,
        type: (item.type ?? 'casement') as ItemType,
        width_mm: item.width_mm ?? null,
        height_mm: item.height_mm ?? null,
        panels: item.panels ?? [],
        transoms: item.transoms ?? [],
        confidence: 1,
        needs_review: item.width_mm == null || item.height_mm == null ? ['kich_thuoc'] : [],
      }))
      setDraft(next)
      setChosen(Object.fromEntries(next.map((_item, index) => [String(index), true])))
      setWarnings([])
      setNote(`Đã nạp ${next.length} cửa từ JSON — kiểm tra rồi nhập vào dự án`)
    } catch (error) {
      toast.push(`JSON lỗi: ${(error as Error).message}`, 'error')
    }
  }

  const patchItem = (index: number, values: Partial<ExtractedItem>) => {
    setDraft((prev) =>
      prev.map((item, position) => (position === index ? { ...item, ...values } : item)),
    )
  }

  const selected = draft.filter((_item, index) => chosen[String(index)] !== false)
  const missingDims = selected.filter((item) => item.width_mm == null || item.height_mm == null)

  const applyDraft = () => {
    if (!selected.length) {
      toast.push('Chọn ít nhất 1 cửa để nhập', 'error')
      return
    }
    onApplyItems(
      selected.map((item) => ({
        tag: item.tag,
        room: item.room,
        qty: item.qty,
        type: item.type,
        width_mm: item.width_mm ?? undefined,
        height_mm: item.height_mm ?? undefined,
        sill_mm: item.sill_mm ?? undefined,
        panels: item.panels,
        transoms: item.transoms,
        glass: item.glass,
        notes: item.notes,
      })),
    )
    toast.push(
      missingDims.length
        ? `Đã thêm ${selected.length} cửa — ${missingDims.length} cửa cần nhập kích thước`
        : `Đã thêm ${selected.length} cửa vào dự án`,
      'success',
    )
    setDraft([])
    setChosen({})
    setWarnings([])
    setJsonText('')
    setNote('')
  }

  return (
    <SectionCard
      title="Ảnh cửa → dữ liệu cho bảng vẽ"
      description="AI chỉ nhận diện loại cửa, số cánh, đố, hướng mở. Không suy ra mm — kích thước phải nhập tay và được duyệt trước khi áp vào dự án."
    >
      <div className="mb-4 rounded-lg border border-border bg-secondary/40 p-3">
        <div className="flex flex-wrap items-end gap-3">
          <Label className="w-56">
            AI đọc ảnh
            <Select
              value={provider}
              onChange={(event) => {
                const next = ai?.providers.find((entry) => entry.name === event.target.value)
                setProvider(event.target.value)
                setModel(next?.model ?? '')
              }}
            >
              {(ai?.providers ?? []).map((entry) => (
                <option key={entry.name} value={entry.name} disabled={!entry.vision}>
                  {entry.label}
                  {entry.vision ? '' : ' — không đọc ảnh'}
                  {entry.available ? '' : ' — chưa có key'}
                </option>
              ))}
            </Select>
          </Label>
          <Label className="w-48">
            Model
            <Input value={model} onChange={(event) => setModel(event.target.value)} />
          </Label>
          <Button size="sm" onClick={() => void callAI()} disabled={busy || !imageData}>
            <Wand2 className="h-3.5 w-3.5" /> {busy ? 'Đang đọc ảnh…' : 'Đọc ảnh bằng AI'}
          </Button>
          {current ? (
            <Badge variant={current.available ? 'ok' : 'warn'} title={current.api_key_env}>
              {current.available ? 'sẵn sàng' : 'thiếu key'}
            </Badge>
          ) : null}
        </div>
        {current && !current.available ? (
          <p className="mt-2 text-[11px] text-amber-700">
            Đặt biến môi trường <code>{current.api_key_env}</code> rồi khởi động lại server, hoặc dùng cách dán JSON
            (Bước 2) — kết quả vẫn qua màn hình duyệt bên dưới.
          </p>
        ) : null}
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <div>
          <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
            <ImagePlus className="h-3.5 w-3.5" /> Chọn ảnh từ máy
          </Button>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) handleFile(file)
              event.target.value = ''
            }}
          />
          <div className="mt-3 grid min-h-[240px] place-items-center rounded-lg border border-dashed border-input bg-secondary/30 p-3 text-xs text-muted-foreground">
            {imageData ? (
              <img src={imageData} alt="ảnh phối cảnh" className="max-h-[420px] w-full rounded-md object-contain" />
            ) : (
              'Chưa có ảnh'
            )}
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <span className="field-label">Bước 1 — Sinh prompt</span>
            <div className="mt-1.5 flex flex-wrap gap-2">
              <Button size="sm" onClick={() => void loadPrompt()}>
                <Sparkles className="h-3.5 w-3.5" /> Sinh prompt
              </Button>
              <Button variant="outline" size="sm" onClick={() => void copyPrompt()}>
                <ClipboardCopy className="h-3.5 w-3.5" /> Copy prompt
              </Button>
            </div>
            <Textarea
              className="mono mt-2 min-h-[180px]"
              readOnly
              value={promptText}
              placeholder="Bấm 'Sinh prompt' để lấy nội dung dán vào ChatGPT cùng ảnh."
            />
          </div>

          <div>
            <Label>
              Bước 2 — Dán JSON ChatGPT trả về
              <Textarea
                className="mono mt-1.5 min-h-[150px]"
                spellCheck={false}
                value={jsonText}
                onChange={(event) => setJsonText(event.target.value)}
                placeholder='{"items":[{"tag":"C1","type":"casement","panels":[]}]}'
              />
            </Label>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Button size="sm" variant="outline" onClick={parseJsonToDraft}>
                <FileJson className="h-3.5 w-3.5" /> Nạp JSON để duyệt
              </Button>
              {note ? <span className="text-xs text-muted-foreground">{note}</span> : null}
            </div>
          </div>
        </div>
      </div>

      {draft.length ? (
        <div className="mt-5 border-t border-border pt-4">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="text-[13px] font-semibold text-primary">
                Bước 3 — Duyệt kết quả ({selected.length}/{draft.length} cửa)
              </h3>
              <p className="text-[11px] text-muted-foreground">
                Sửa mã / loại cửa / kích thước nếu cần. Ô vàng = AI không đọc được số đo.
              </p>
            </div>
            <Button size="sm" onClick={applyDraft} disabled={!selected.length}>
              Nhập {selected.length || ''} cửa đã chọn
            </Button>
          </div>
          {warnings.length ? (
            <ul className="mb-2 space-y-1 text-[11px] text-amber-800">
              {warnings.map((warning) => (
                <li key={warning}>• {warning}</li>
              ))}
            </ul>
          ) : null}
          <Table>
            <thead>
              <tr>
                <th className="w-8" />
                <th className="w-20">Mã</th>
                <th>Loại cửa</th>
                <th className="w-24 text-right">Rộng</th>
                <th className="w-24 text-right">Cao</th>
                <th className="w-16 text-right">SL</th>
                <th>Cánh</th>
                <th className="w-20">Tin cậy</th>
                <th>Cần kiểm tra</th>
              </tr>
            </thead>
            <tbody>
              {draft.map((item, index) => {
                const key = String(index)
                const missingDimensions = item.width_mm == null || item.height_mm == null
                return (
                  <tr key={key} className={chosen[key] === false ? 'opacity-50' : ''}>
                    <td>
                      <input
                        type="checkbox"
                        className="h-4 w-4 accent-[hsl(var(--primary))]"
                        checked={chosen[key] !== false}
                        onChange={(event) => setChosen({ ...chosen, [key]: event.target.checked })}
                      />
                    </td>
                    <td>
                      <Input
                        className="h-8"
                        value={item.tag}
                        onChange={(event) => patchItem(index, { tag: event.target.value })}
                      />
                    </td>
                    <td>
                      <Select
                        className="h-8"
                        value={item.type}
                        onChange={(event) => patchItem(index, { type: event.target.value as ItemType })}
                      >
                        {Object.entries(itemTypes).map(([value, label]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </Select>
                    </td>
                    <td>
                      <Input
                        type="number"
                        className={cn('h-8', missingDimensions && 'border-amber-400 bg-amber-50')}
                        placeholder="mm"
                        value={item.width_mm ?? ''}
                        onChange={(event) =>
                          patchItem(index, {
                            width_mm: event.target.value ? Number(event.target.value) : null,
                          })
                        }
                      />
                    </td>
                    <td>
                      <Input
                        type="number"
                        className={cn('h-8', missingDimensions && 'border-amber-400 bg-amber-50')}
                        placeholder="mm"
                        value={item.height_mm ?? ''}
                        onChange={(event) =>
                          patchItem(index, {
                            height_mm: event.target.value ? Number(event.target.value) : null,
                          })
                        }
                      />
                    </td>
                    <td>
                      <Input
                        type="number"
                        min={1}
                        className="h-8"
                        value={item.qty ?? 1}
                        onChange={(event) =>
                          patchItem(index, { qty: Math.max(1, Number(event.target.value) || 1) })
                        }
                      />
                    </td>
                    <td className="text-[11px] text-muted-foreground">{panelsSummary(item)}</td>
                    <td>
                      <Badge variant={(item.confidence ?? 0) >= 0.75 ? 'ok' : 'warn'}>
                        {Math.round((item.confidence ?? 0) * 100)}%
                      </Badge>
                    </td>
                    <td>
                      <div className="flex flex-wrap gap-1">
                        {(item.needs_review ?? []).length === 0 ? (
                          <span className="text-[11px] text-muted-foreground">—</span>
                        ) : (
                          (item.needs_review ?? []).map((flag) => (
                            <span
                              key={flag}
                              className="rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-800"
                            >
                              {REVIEW_LABELS[flag] ?? flag}
                            </span>
                          ))
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </Table>
          <p className="mt-2 text-[11px] text-muted-foreground">
            Bảng vẽ + bảng cắt chỉ được sinh sau khi cửa có kích thước thật (nhập ở tab Dự án hoặc ngay tại đây).
          </p>
        </div>
      ) : null}
    </SectionCard>
  )
}
