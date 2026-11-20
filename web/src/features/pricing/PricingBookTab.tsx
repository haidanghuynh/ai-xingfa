import * as React from 'react'
import { FileSpreadsheet, Plus, Save, Trash2 } from 'lucide-react'
import { Badge, Button, CheckField, Input, Label } from '@/components/ui/primitives'
import { SectionCard, Table } from '@/components/ui/layout'
import { useToast } from '@/components/ui/overlays'
import { GroupCostEditor } from '@/features/pricing/GroupCostEditor'
import { api } from '@/lib/api'
import { money } from '@/lib/format'
import type { Catalog, StatusInfo, SystemSummary } from '@/types/api'
import type { BookResult, PriceLevel, PricingBook, ProductGroup } from '@/types/pricing-book'

interface PricingBookTabProps {
  systems: SystemSummary[]
  catalog: Catalog | null
  status: StatusInfo | null
  onBookSaved: (book: PricingBook, result: BookResult) => void
}

export function PricingBookTab({ systems, catalog, status, onBookSaved }: PricingBookTabProps) {
  const toast = useToast()
  const [book, setBook] = React.useState<PricingBook | null>(null)
  const [result, setResult] = React.useState<BookResult | null>(null)
  const [activeCode, setActiveCode] = React.useState<string | null>(null)
  const [saving, setSaving] = React.useState(false)
  const [deriving, setDeriving] = React.useState(false)

  React.useEffect(() => {
    let cancelled = false
    api
      .pricingBook()
      .then((data) => {
        if (cancelled) return
        setBook(data.book)
        setResult(data.result)
        setActiveCode((prev) => prev ?? data.book.groups[0]?.code ?? null)
      })
      .catch((error: Error) => toast.push(error.message, 'error'))
    return () => {
      cancelled = true
    }
  }, [toast])

  const activeGroup = book?.groups.find((group) => group.code === activeCode) ?? null
  const activeResult = result?.groups.find((group) => group.code === activeCode) ?? null

  const updateGroup = (group: ProductGroup) => {
    setBook((prev) =>
      prev ? { ...prev, groups: prev.groups.map((item) => (item.code === group.code ? group : item)) } : prev,
    )
  }

  const save = async () => {
    if (!book) return
    setSaving(true)
    try {
      const response = await api.savePricingBook(book)
      setBook(response.book)
      setResult(response.result)
      onBookSaved(response.book, response.result)
      toast.push('Đã lưu bảng chi phí & bảng giá', 'success')
    } catch (error) {
      toast.push((error as Error).message, 'error')
    } finally {
      setSaving(false)
    }
  }

  const derive = async () => {
    if (!activeGroup) return
    setDeriving(true)
    try {
      const response = await api.deriveGroupCost(activeGroup.code)
      updateGroup({ ...activeGroup, cost: response.cost })
      toast.push(`Đã lấy định mức từ BOM mẫu cho ${activeGroup.code} — bấm Lưu để áp dụng`, 'success')
    } catch (error) {
      toast.push((error as Error).message, 'error')
    } finally {
      setDeriving(false)
    }
  }

  const updateLevel = (index: number, values: Partial<PriceLevel>) => {
    setBook((prev) =>
      prev
        ? {
            ...prev,
            levels: prev.levels.map((level, position) =>
              position === index ? { ...level, ...values } : level,
            ),
          }
        : prev,
    )
  }

  const addLevel = () => {
    setBook((prev) =>
      prev
        ? {
            ...prev,
            levels: [
              ...prev.levels,
              {
                code: `cap${prev.levels.length + 1}`,
                name: 'Cấp giá mới',
                margin_percent: 20,
                discount_percent: 0,
                include_install: true,
                show_in_quote: true,
              },
            ],
          }
        : prev,
    )
  }

  if (!book || !result) {
    return (
      <SectionCard title="Bảng chi phí giá thành & giá bán" description="Đang tải…">
        <div className="py-16 text-center text-sm text-muted-foreground">Đang tải dữ liệu…</div>
      </SectionCard>
    )
  }

  const visibleLevels = book.levels.filter((level) => level.show_in_quote)

  return (
    <div className="space-y-4">
      <SectionCard
        title="Bảng chi phí giá thành & giá đến tay khách"
        description="Chia theo nhóm sản phẩm · giá công bố chưa VAT"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" onClick={() => void save()} disabled={saving}>
              <Save className="h-3.5 w-3.5" /> {saving ? 'Đang lưu…' : 'Lưu bảng giá'}
            </Button>
            <a
              href="/api/pricing-book/export.xlsx"
              className="inline-flex h-8 items-center gap-1.5 rounded-md border border-input bg-card px-3 text-xs font-semibold hover:bg-secondary"
            >
              <FileSpreadsheet className="h-3.5 w-3.5" /> Excel nội bộ
            </a>
            <a
              href="/api/pricing-book/export.pdf"
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-8 items-center gap-1.5 rounded-md border border-input bg-card px-3 text-xs font-semibold hover:bg-secondary"
            >
              <FileSpreadsheet className="h-3.5 w-3.5" /> PDF gửi khách
            </a>
          </div>
        }
      >
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          <Label>
            VAT (%)
            <Input
              type="number"
              step={0.5}
              value={book.settings.vat_percent}
              onChange={(event) =>
                setBook({ ...book, settings: { ...book.settings, vat_percent: Number(event.target.value) } })
              }
            />
          </Label>
          <Label>
            Làm tròn giá (đ)
            <Input
              type="number"
              step={1000}
              value={book.settings.round_to}
              onChange={(event) =>
                setBook({ ...book, settings: { ...book.settings, round_to: Number(event.target.value) } })
              }
            />
          </Label>
          <Label>
            Ngày hiệu lực
            <Input
              value={book.effective_date}
              onChange={(event) => setBook({ ...book, effective_date: event.target.value })}
            />
          </Label>
          <Label>
            Ghi chú in trên bảng giá
            <Input value={book.note} onChange={(event) => setBook({ ...book, note: event.target.value })} />
          </Label>
          <div className="flex items-end pb-1.5">
            <CheckField
              label="Hiện cột “đã VAT” trong bảng giá"
              checked={book.settings.show_inc_vat}
              onChange={(event) =>
                setBook({ ...book, settings: { ...book.settings, show_inc_vat: event.target.checked } })
              }
            />
          </div>
        </div>
      </SectionCard>

      <div className="grid items-start gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
        <SectionCard title="Nhóm sản phẩm" description={`${book.groups.length} nhóm`}>
          <ul className="space-y-1.5">
            {book.groups.map((group) => {
              const groupResult = result.groups.find((entry) => entry.code === group.code)
              const firstLevel = groupResult?.levels[0]
              return (
                <li key={group.code}>
                  <button
                    type="button"
                    onClick={() => setActiveCode(group.code)}
                    className={`w-full rounded-lg border px-3 py-2 text-left transition-colors ${
                      group.code === activeCode
                        ? 'border-primary bg-secondary'
                        : 'border-border hover:border-primary/60'
                    }`}
                  >
                    <div className="text-[13px] font-bold text-primary">
                      {group.code} — {group.name}
                    </div>
                    <div className="text-[11px] text-muted-foreground">
                      {groupResult ? `${money(groupResult.cost_per_m2)} đ/m²` : '—'}
                      {firstLevel ? ` · bán ${money(firstLevel.price_ex_vat_m2)}` : ''}
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
        </SectionCard>

        <SectionCard
          title="Chi phí đầu vào (giá vốn)"
          description="Định mức cho 1 m² / 1 bộ cửa mẫu"
          actions={activeResult ? <Badge variant="outline">{money(activeResult.cost_per_m2)} đ/m²</Badge> : null}
        >
          {activeGroup ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <Label>
                  Mã nhóm
                  <Input
                    value={activeGroup.code}
                    onChange={(event) => updateGroup({ ...activeGroup, code: event.target.value.toUpperCase() })}
                  />
                </Label>
                <Label>
                  Tên nhóm
                  <Input
                    value={activeGroup.name}
                    onChange={(event) => updateGroup({ ...activeGroup, name: event.target.value })}
                  />
                </Label>
              </div>
              <p className="text-[11px] text-muted-foreground">
                Áp dụng cho loại cửa: <b>{activeGroup.item_types.join(', ')}</b>
              </p>
              <GroupCostEditor
                group={activeGroup}
                result={activeResult}
                systems={systems}
                catalog={catalog}
                status={status}
                deriving={deriving}
                onChange={updateGroup}
                onDerive={() => void derive()}
              />
            </div>
          ) : null}
        </SectionCard>
      </div>

      <SectionCard
        title="Bảng giá đến tay khách (nội bộ)"
        description={`Giá vốn × (1 + % lãi) × (1 − % chiết khấu); VAT ${result.vat_percent}% cộng khi bán · làm tròn ${money(result.round_to)} đ`}
      >
        {visibleLevels.length === 0 ? (
          <p className="py-6 text-center text-xs text-muted-foreground">
            Chưa chọn cấp giá nào — bật “Hiện bảng giá” ở bảng Cấp giá bên dưới để đưa cột giá vào bảng.
          </p>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Nhóm sản phẩm</th>
                <th className="text-right">Giá vốn/m²</th>
                {visibleLevels.map((level) => (
                  <React.Fragment key={level.code}>
                    <th className="text-right">
                      {level.name}
                      <br />
                      <span className="text-[10px] font-normal normal-case">chưa VAT</span>
                    </th>
                    {result.show_inc_vat ? (
                      <th className="text-right">
                        {level.name}
                        <br />
                        <span className="text-[10px] font-normal normal-case">đã VAT {result.vat_percent}%</span>
                      </th>
                    ) : null}
                  </React.Fragment>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.groups.map((group) => (
                <tr key={group.code}>
                  <td>
                    <b className="text-primary">{group.code}</b> — {group.name}
                    <div className="text-[11px] text-muted-foreground">
                      mẫu {Math.round(group.norm_width_mm)}×{Math.round(group.norm_height_mm)} mm
                    </div>
                  </td>
                  <td className="text-right tabular-nums text-muted-foreground">{money(group.cost_per_m2)}</td>
                  {visibleLevels.map((level) => {
                    const price = group.levels.find((entry) => entry.code === level.code)
                    return (
                      <React.Fragment key={level.code}>
                        <td className="text-right font-semibold tabular-nums">
                          {price ? money(price.price_ex_vat_m2) : '—'}
                        </td>
                        {result.show_inc_vat ? (
                          <td className="text-right tabular-nums text-muted-foreground">
                            {price ? money(price.price_inc_vat_m2) : '—'}
                          </td>
                        ) : null}
                      </React.Fragment>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </Table>
        )}
        <p className="mt-2 text-[11px] text-muted-foreground">
          Bản PDF gửi khách chỉ hiển thị giá bán (không có cột giá vốn) và chỉ các cấp đang bật “Hiện bảng giá”.
          Giá/bộ mẫu = giá/m² × diện tích mẫu.
        </p>
      </SectionCard>

      <SectionCard
        title="Cấp giá"
        description="Giá bán = giá vốn × (1 + % lãi) × (1 − % chiết khấu); VAT cộng khi báo giá"
        actions={
          <Button size="sm" variant="outline" onClick={addLevel}>
            <Plus className="h-3.5 w-3.5" /> Thêm cấp
          </Button>
        }
      >
        <Table>
          <thead>
            <tr>
              <th className="w-28">Mã</th>
              <th>Tên cấp</th>
              <th className="w-28 text-right">% lãi</th>
              <th className="w-32 text-right">% chiết khấu</th>
              <th className="w-32">Hiện bảng giá</th>
              <th className="w-32">Gồm lắp đặt</th>
              <th className="w-10" />
            </tr>
          </thead>
          <tbody>
            {book.levels.map((level, index) => (
              <tr key={`${level.code}-${index}`}>
                <td>
                  <Input value={level.code} onChange={(event) => updateLevel(index, { code: event.target.value })} />
                </td>
                <td>
                  <Input value={level.name} onChange={(event) => updateLevel(index, { name: event.target.value })} />
                </td>
                <td>
                  <Input
                    type="number"
                    step={1}
                    value={level.margin_percent}
                    onChange={(event) => updateLevel(index, { margin_percent: Number(event.target.value) })}
                  />
                </td>
                <td>
                  <Input
                    type="number"
                    step={1}
                    value={level.discount_percent}
                    onChange={(event) => updateLevel(index, { discount_percent: Number(event.target.value) })}
                  />
                </td>
                <td>
                  <CheckField
                    label="Có"
                    checked={level.show_in_quote}
                    onChange={(event) => updateLevel(index, { show_in_quote: event.target.checked })}
                  />
                </td>
                <td>
                  <CheckField
                    label="Có"
                    checked={level.include_install}
                    onChange={(event) => updateLevel(index, { include_install: event.target.checked })}
                  />
                </td>
                <td>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-destructive hover:bg-destructive/10"
                    onClick={() =>
                      setBook({ ...book, levels: book.levels.filter((_, position) => position !== index) })
                    }
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </SectionCard>
    </div>
  )
}
