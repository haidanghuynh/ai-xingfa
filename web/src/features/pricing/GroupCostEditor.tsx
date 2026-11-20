import { Plus, Sparkles, Trash2 } from 'lucide-react'
import { Badge, Button, Input, Label, Select } from '@/components/ui/primitives'
import { Table } from '@/components/ui/layout'
import { money } from '@/lib/format'
import type { Catalog, StatusInfo, SystemSummary } from '@/types/api'
import type { GroupCost, ProductGroup } from '@/types/pricing-book'

interface GroupCostEditorProps {
  group: ProductGroup
  result?: { cost_per_m2: number; cost_per_set: number; norm_area_m2: number } | null
  systems: SystemSummary[]
  catalog: Catalog | null
  status: StatusInfo | null
  deriving: boolean
  onChange: (group: ProductGroup) => void
  onDerive: () => void
}

const COST_FIELDS: { key: keyof GroupCost; label: string; step: number; unit: string }[] = [
  { key: 'alum_kg_per_m2', label: 'Nhôm / m²', step: 0.05, unit: 'kg' },
  { key: 'alum_price_per_kg', label: 'Đơn giá nhôm', step: 1000, unit: 'đ/kg' },
  { key: 'alum_waste_percent', label: 'Hao hụt nhôm', step: 0.5, unit: '%' },
  { key: 'glass_m2_per_m2', label: 'Kính / m² cửa', step: 0.01, unit: 'm²' },
  { key: 'glass_price_per_m2', label: 'Đơn giá kính', step: 1000, unit: 'đ/m²' },
  { key: 'glass_waste_percent', label: 'Hao hụt kính', step: 0.5, unit: '%' },
  { key: 'hardware_waste_percent', label: 'Hao hụt phụ kiện', step: 0.5, unit: '%' },
  { key: 'consumables_per_m2', label: 'Vật tư phụ', step: 1000, unit: 'đ/m²' },
  { key: 'labor_production_per_m2', label: 'Nhân công sản xuất', step: 1000, unit: 'đ/m²' },
  { key: 'labor_install_per_m2', label: 'Nhân công lắp đặt', step: 1000, unit: 'đ/m²' },
  { key: 'factory_per_m2', label: 'Chi phí xưởng / khấu hao', step: 1000, unit: 'đ/m²' },
  { key: 'packaging_per_m2', label: 'Đóng gói', step: 1000, unit: 'đ/m²' },
  { key: 'transport_per_m2', label: 'Vận chuyển', step: 1000, unit: 'đ/m²' },
  { key: 'warranty_percent', label: 'Bảo hành trích trước', step: 0.1, unit: '%' },
  { key: 'management_percent', label: 'Quản lý – kinh doanh', step: 0.5, unit: '%' },
  { key: 'finance_percent', label: 'Lãi vay / tài chính', step: 0.1, unit: '%' },
]

export function GroupCostEditor({
  group,
  result,
  systems,
  catalog,
  status,
  deriving,
  onChange,
  onDerive,
}: GroupCostEditorProps) {
  const patchNorm = (values: Partial<ProductGroup['norm']>) =>
    onChange({ ...group, norm: { ...group.norm, ...values } })
  const patchCost = (key: keyof GroupCost, value: number) =>
    onChange({ ...group, cost: { ...group.cost, [key]: value } })

  const glassOptions = Object.entries(catalog?.glass ?? {})
  const hardwareComponents = catalog?.hardware?.components ?? {}
  const hingeOptions = catalog?.hardware?.hinge_options ?? []
  const lockOptions = catalog?.hardware?.lock_options ?? []
  const itemTypes = status?.item_types ?? {}

  const updateHardware = (index: number, values: Partial<GroupCost['hardware_items'][number]>) =>
    onChange({
      ...group,
      cost: {
        ...group.cost,
        hardware_items: group.cost.hardware_items.map((item, position) =>
          position === index ? { ...item, ...values } : item,
        ),
      },
    })

  const addHardware = () => {
    const used = new Set(group.cost.hardware_items.map((item) => item.key))
    const next =
      hingeOptions.concat(lockOptions, ['handle', 'wheel', 'stopper']).find((key) => !used.has(key)) ?? 'hinge_3d'
    onChange({
      ...group,
      cost: {
        ...group.cost,
        hardware_items: [
          ...group.cost.hardware_items,
          { key: next, qty_per_set: 1, price: hardwareComponents[next]?.price ?? 0 },
        ],
      },
    })
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-secondary/40 p-3">
        <div>
          <h3 className="text-[13px] font-semibold text-primary">
            {group.code} — {group.name}
          </h3>
          <p className="text-[11px] text-muted-foreground">
            Cửa mẫu {group.norm.width_mm}×{group.norm.height_mm} mm
            {result ? ` · ${result.norm_area_m2} m² · giá vốn ${money(result.cost_per_m2)} đ/m²` : ''}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {result ? <Badge variant="outline">{money(result.cost_per_set)} đ/bộ</Badge> : null}
          <Button size="sm" variant="outline" onClick={onDerive} disabled={deriving}>
            <Sparkles className="h-3.5 w-3.5" /> {deriving ? 'Đang tính…' : 'Lấy định mức từ BOM mẫu'}
          </Button>
        </div>
      </div>

      <div>
        <span className="field-label">Cửa mẫu (quy đổi ra /m² và /bộ)</span>
        <div className="mt-1.5 grid grid-cols-2 gap-3 md:grid-cols-4">
          <Label>
            Loại cửa
            <Select value={group.norm.item_type} onChange={(event) => patchNorm({ item_type: event.target.value })}>
              {Object.entries(itemTypes).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
          </Label>
          <Label>
            Hệ nhôm
            <Select value={group.norm.system} onChange={(event) => patchNorm({ system: event.target.value })}>
              {systems.map((system) => (
                <option key={system.code} value={system.code}>
                  {system.code}
                </option>
              ))}
            </Select>
          </Label>
          <Label>
            Rộng (mm)
            <Input
              type="number"
              step={50}
              value={group.norm.width_mm}
              onChange={(event) => patchNorm({ width_mm: Number(event.target.value) })}
            />
          </Label>
          <Label>
            Cao (mm)
            <Input
              type="number"
              step={50}
              value={group.norm.height_mm}
              onChange={(event) => patchNorm({ height_mm: Number(event.target.value) })}
            />
          </Label>
          <Label>
            Số cánh / ô
            <Input
              type="number"
              min={1}
              value={group.norm.panels}
              onChange={(event) => patchNorm({ panels: Number(event.target.value) })}
            />
          </Label>
          <Label>
            Kính
            <Select value={group.norm.glass_key} onChange={(event) => patchNorm({ glass_key: event.target.value })}>
              {glassOptions.map(([key, glass]) => (
                <option key={key} value={key}>
                  {glass.name}
                </option>
              ))}
            </Select>
          </Label>
          <Label>
            Loại bản lề
            <Select
              value={group.norm.hinge_type ?? ''}
              onChange={(event) => patchNorm({ hinge_type: event.target.value || null })}
            >
              <option value="">Không bản lề</option>
              {hingeOptions.map((key) => (
                <option key={key} value={key}>
                  {hardwareComponents[key]?.name ?? key}
                </option>
              ))}
            </Select>
          </Label>
          <Label>
            Số bản lề / cánh
            <Input
              type="number"
              min={0}
              max={8}
              value={group.norm.hinge_count ?? 0}
              onChange={(event) => patchNorm({ hinge_count: Number(event.target.value) })}
            />
          </Label>
          <Label>
            Loại khóa
            <Select
              value={group.norm.lock_type ?? ''}
              onChange={(event) => patchNorm({ lock_type: event.target.value || null })}
            >
              <option value="">Không khóa</option>
              {lockOptions.map((key) => (
                <option key={key} value={key}>
                  {hardwareComponents[key]?.name ?? key}
                </option>
              ))}
            </Select>
          </Label>
        </div>
      </div>

      <div>
        <span className="field-label">Chi phí theo m²</span>
        <div className="mt-1.5 grid grid-cols-2 gap-3 md:grid-cols-4">
          {COST_FIELDS.map((field) => (
            <Label key={String(field.key)}>
              {field.label} ({field.unit})
              <Input
                type="number"
                step={field.step}
                value={String(group.cost[field.key])}
                onChange={(event) => patchCost(field.key, Number(event.target.value))}
              />
            </Label>
          ))}
        </div>
      </div>

      <div>
        <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
          <span className="field-label">Phụ kiện / bộ cửa mẫu</span>
          <Button size="sm" variant="outline" onClick={addHardware}>
            <Plus className="h-3.5 w-3.5" /> Thêm phụ kiện
          </Button>
        </div>
        <Table>
          <thead>
            <tr>
              <th className="w-56">Mã phụ kiện</th>
              <th className="w-32 text-right">SL / bộ</th>
              <th className="w-36 text-right">Đơn giá</th>
              <th className="w-36 text-right">Thành tiền / bộ</th>
              <th className="w-10" />
            </tr>
          </thead>
          <tbody>
            {group.cost.hardware_items.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-4 text-center text-xs text-muted-foreground">
                  Nhóm này chưa có phụ kiện (ví dụ vách kính cố định).
                </td>
              </tr>
            ) : (
              group.cost.hardware_items.map((item, index) => (
                <tr key={`${item.key}-${index}`}>
                  <td>
                    <Select
                      value={item.key}
                      onChange={(event) =>
                        updateHardware(index, {
                          key: event.target.value,
                          price: hardwareComponents[event.target.value]?.price ?? item.price,
                        })
                      }
                    >
                      {Object.entries(hardwareComponents).map(([key, component]) => (
                        <option key={key} value={key}>
                          {component.name}
                        </option>
                      ))}
                    </Select>
                  </td>
                  <td>
                    <Input
                      type="number"
                      step={0.5}
                      value={item.qty_per_set}
                      onChange={(event) => updateHardware(index, { qty_per_set: Number(event.target.value) })}
                    />
                  </td>
                  <td>
                    <Input
                      type="number"
                      step={1000}
                      value={item.price}
                      onChange={(event) => updateHardware(index, { price: Number(event.target.value) })}
                    />
                  </td>
                  <td className="text-right tabular-nums">{money(item.qty_per_set * item.price)}</td>
                  <td>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-destructive hover:bg-destructive/10"
                      onClick={() =>
                        onChange({
                          ...group,
                          cost: {
                            ...group.cost,
                            hardware_items: group.cost.hardware_items.filter((_, position) => position !== index),
                          },
                        })
                      }
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </Table>
        <p className="mt-1.5 text-[11px] text-muted-foreground">
          Định mức phụ kiện tính cho <b>1 bộ cửa mẫu</b>; app tự chia cho diện tích để ra đ/m².
        </p>
      </div>
    </div>
  )
}
