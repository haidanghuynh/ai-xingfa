import * as React from 'react'
import { CheckCircle2, CopyPlus, FileSpreadsheet, Plus, Save, Trash2, TriangleAlert, Upload } from 'lucide-react'
import { Badge, Button, CheckField, Input, Label, Select, Textarea } from '@/components/ui/primitives'
import { Card, SectionCard } from '@/components/ui/layout'
import { useToast } from '@/components/ui/overlays'
import { ProfilesEditor } from '@/features/catalog/ProfilesEditor'
import { RULE_FIELDS, SYSTEM_KINDS, newSystemTemplate } from '@/features/catalog/templates'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import type { Catalog, Pricing, ProfileDef, Rules, SystemDef, SystemSummary } from '@/types/api'

interface CatalogTabProps {
  systems: SystemSummary[]
  catalog: Catalog | null
  pricing: Pricing | null
  onReloadSystems: () => Promise<void>
  onCatalogSaved: (catalog: Catalog) => void
  onPricingSaved: (pricing: Pricing) => void
}

export function CatalogTab({
  systems,
  catalog,
  pricing,
  onReloadSystems,
  onCatalogSaved,
  onPricingSaved,
}: CatalogTabProps) {
  const toast = useToast()
  const [activeCode, setActiveCode] = React.useState<string | null>(null)
  const [draft, setDraft] = React.useState<SystemDef | null>(null)
  const [profiles, setProfiles] = React.useState<ProfileDef[]>([])
  const [saving, setSaving] = React.useState(false)
  const [pricingText, setPricingText] = React.useState('')
  const [catalogText, setCatalogText] = React.useState('')

  React.useEffect(() => {
    setPricingText(JSON.stringify(pricing ?? {}, null, 2))
  }, [pricing])

  React.useEffect(() => {
    setCatalogText(JSON.stringify(catalog ?? {}, null, 2))
  }, [catalog])

  React.useEffect(() => {
    if (activeCode || systems.length === 0) return
    setActiveCode(systems[0].code)
  }, [activeCode, systems])

  React.useEffect(() => {
    if (!activeCode) return undefined
    let cancelled = false
    api
      .system(activeCode)
      .then((system) => {
        if (cancelled) return
        setDraft(structuredClone(system))
        setProfiles(Object.values(system.profiles).map((profile) => ({ ...profile })))
      })
      .catch((error: Error) => toast.push(error.message, 'error'))
    return () => {
      cancelled = true
    }
  }, [activeCode, toast])

  const patchDraft = (values: Partial<SystemDef>) => setDraft((prev) => (prev ? { ...prev, ...values } : prev))
  const patchRule = (key: keyof Rules, value: string) =>
    setDraft((prev) =>
      prev ? { ...prev, rules: { ...prev.rules, [key]: value === '' ? null : Number(value) } } : prev,
    )

  const handleSave = async () => {
    if (!draft) return
    const record: Record<string, ProfileDef> = {}
    profiles.forEach((profile) => {
      record[profile.key] = { ...profile, key: profile.key }
    })
    const payload: SystemDef = { ...draft, code: draft.code.trim().toUpperCase(), profiles: record }
    setSaving(true)
    try {
      await api.saveSystem(payload)
      await onReloadSystems()
      setActiveCode(payload.code)
      toast.push(`Đã lưu hệ ${payload.code}`, 'success')
    } catch (error) {
      toast.push((error as Error).message, 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleNew = () => {
    const template = newSystemTemplate()
    setDraft(template)
    setProfiles(Object.values(template.profiles).map((profile) => ({ ...profile })))
    setActiveCode(null)
    toast.push('Nhập thông số hệ mới rồi bấm Lưu hệ')
  }

  const handleDuplicate = async () => {
    if (!draft) return
    const newCode = window.prompt(`Mã hệ mới (sao chép từ ${draft.code})`, `${draft.code}X`)
    if (!newCode) return
    const code = newCode.trim().toUpperCase()
    try {
      await api.duplicateSystem(draft.code, code)
      await onReloadSystems()
      setActiveCode(code)
      toast.push(`Đã nhân bản thành ${code}`, 'success')
    } catch (error) {
      toast.push((error as Error).message, 'error')
    }
  }

  const handleDelete = async () => {
    if (!draft) return
    if (!window.confirm(`Xóa hệ ${draft.code}? Hành động không thể hoàn tác.`)) return
    try {
      await api.deleteSystem(draft.code)
      setDraft(null)
      setProfiles([])
      setActiveCode(null)
      await onReloadSystems()
      toast.push('Đã xóa hệ nhôm', 'success')
    } catch (error) {
      toast.push((error as Error).message, 'error')
    }
  }

  const handleSavePricing = async () => {
    try {
      const parsed = JSON.parse(pricingText) as Pricing
      const result = await api.savePricing(parsed)
      onPricingSaved(result.pricing ?? parsed)
      toast.push('Đã lưu bảng giá', 'success')
    } catch (error) {
      toast.push(`Bảng giá JSON lỗi: ${(error as Error).message}`, 'error')
    }
  }

  const handleSaveCatalog = async () => {
    try {
      const parsed = JSON.parse(catalogText) as Catalog
      await api.saveCatalog(parsed)
      onCatalogSaved(parsed)
      toast.push('Đã lưu catalogue kính & phụ kiện', 'success')
    } catch (error) {
      toast.push(`Catalogue JSON lỗi: ${(error as Error).message}`, 'error')
    }
  }

  const handleImportPricing = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    const reader = new FileReader()
    reader.onload = async () => {
      try {
        const dataUrl = String(reader.result ?? '')
        const result = await api.importPricing(dataUrl)
        onPricingSaved(result.pricing)
        toast.push(`Đã cập nhật ${Object.keys(result.updated).length} thông số giá từ Excel`, 'success')
      } catch (error) {
        toast.push((error as Error).message, 'error')
      }
    }
    reader.readAsDataURL(file)
  }

  return (
    <div className="grid items-start gap-4 lg:grid-cols-[300px_minmax(0,1fr)]">
      <div className="space-y-4">
        <SectionCard
          title="Hệ nhôm"
          actions={
            <Button size="sm" variant="outline" onClick={handleNew}>
              <Plus className="h-3.5 w-3.5" /> Mới
            </Button>
          }
        >
          <ul className="space-y-1.5">
            {systems.map((system) => (
              <li key={system.code}>
                <button
                  type="button"
                  onClick={() => setActiveCode(system.code)}
                  className={cn(
                    'flex w-full items-center justify-between gap-2 rounded-lg border px-3 py-2 text-left transition-colors',
                    system.code === activeCode
                      ? 'border-primary bg-secondary'
                      : 'border-border hover:border-primary/60',
                  )}
                >
                  <div className="min-w-0">
                    <div className="text-[13px] font-bold text-primary">{system.code}</div>
                    <div className="truncate text-[11px] text-muted-foreground">{system.name}</div>
                  </div>
                  {system.verified ? (
                    <Badge variant="ok">đã xác nhận</Badge>
                  ) : (
                    <Badge variant="warn">chưa xác nhận</Badge>
                  )}
                </button>
              </li>
            ))}
            {systems.length === 0 ? <li className="text-xs text-muted-foreground">Chưa có hệ nhôm</li> : null}
          </ul>
        </SectionCard>

        <SectionCard title="Bảng giá &amp; chi phí" description="Sửa JSON hoặc nhập từ file tính giá thành">
          <Textarea
            className="mono min-h-[220px]"
            spellCheck={false}
            value={pricingText}
            onChange={(event) => setPricingText(event.target.value)}
          />
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Button size="sm" onClick={() => void handleSavePricing()}>
              <Save className="h-3.5 w-3.5" /> Lưu bảng giá
            </Button>
            <a
              href="/api/template/costing.xlsx"
              className="inline-flex h-8 items-center gap-1.5 rounded-md border border-input bg-card px-3 text-xs font-semibold text-foreground transition-colors hover:bg-secondary"
            >
              <FileSpreadsheet className="h-3.5 w-3.5" /> File tính giá thành
            </a>
            <label className="inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-md border border-input bg-card px-3 text-xs font-semibold text-foreground transition-colors hover:bg-secondary">
              <Upload className="h-3.5 w-3.5" /> Nhập giá từ Excel
              <input type="file" accept=".xlsx" className="hidden" onChange={handleImportPricing} />
            </label>
          </div>
          <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
            Tải file mẫu → điền giá NCC vào sheet <b>01_DauVao</b> → lưu → bấm <b>Nhập giá từ Excel</b> để cập nhật
            bảng giá, rồi Build lại để báo giá PDF/Excel dùng giá mới.
          </p>
        </SectionCard>

        <SectionCard title="Kính &amp; phụ kiện" description="Catalogue giá kính và vật tư">
          <Textarea
            className="mono min-h-[220px]"
            spellCheck={false}
            value={catalogText}
            onChange={(event) => setCatalogText(event.target.value)}
          />
          <Button size="sm" className="mt-2" onClick={() => void handleSaveCatalog()}>
            <Save className="h-3.5 w-3.5" /> Lưu catalogue
          </Button>
        </SectionCard>
      </div>

      <Card>
        {draft ? (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-5 py-4">
              <div>
                <h2 className="text-[15px] font-semibold text-primary">
                  {draft.code} — {draft.name}
                </h2>
                <p className="text-xs text-muted-foreground">
                  {Object.keys(draft.profiles).length} thanh · cây {draft.bar_length_mm} mm · {draft.joint === 'miter45' ? 'hàn 45°' : 'ghép 90°'}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <CheckField
                  label="Đã xác nhận"
                  checked={draft.verified}
                  onChange={(event) => patchDraft({ verified: event.target.checked })}
                />
                <Button size="sm" variant="outline" onClick={() => void handleDuplicate()}>
                  <CopyPlus className="h-3.5 w-3.5" /> Nhân bản
                </Button>
                <Button size="sm" variant="destructive" onClick={() => void handleDelete()}>
                  <Trash2 className="h-3.5 w-3.5" /> Xóa
                </Button>
                <Button size="sm" onClick={() => void handleSave()} disabled={saving}>
                  <Save className="h-3.5 w-3.5" /> Lưu hệ
                </Button>
              </div>
            </div>

            <div className="space-y-4 px-5 py-4">
              <div
                className={cn(
                  'flex items-start gap-2 rounded-lg px-3 py-2 text-xs',
                  draft.verified ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-800',
                )}
              >
                {draft.verified ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                ) : (
                  <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
                )}
                {draft.verified
                  ? 'Số liệu đã được xác nhận từ catalogue nhà cung cấp.'
                  : 'Số liệu chưa xác nhận — hãy đối chiếu catalogue thật (mặt cắt, chiều sâu, vách, kg/m) rồi tick xác nhận.'}
              </div>

              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                <Label>
                  Mã hệ
                  <Input value={draft.code} onChange={(event) => patchDraft({ code: event.target.value })} />
                </Label>
                <Label className="col-span-2">
                  Tên hệ
                  <Input value={draft.name} onChange={(event) => patchDraft({ name: event.target.value })} />
                </Label>
                <Label>
                  Kiểu
                  <Select value={draft.kind} onChange={(event) => patchDraft({ kind: event.target.value })}>
                    {SYSTEM_KINDS.map((kind) => (
                      <option key={kind.value} value={kind.value}>
                        {kind.label}
                      </option>
                    ))}
                  </Select>
                </Label>
                <Label>
                  Ghép góc
                  <Select
                    value={draft.joint}
                    onChange={(event) => patchDraft({ joint: event.target.value as SystemDef['joint'] })}
                  >
                    <option value="miter45">Hàn 45°</option>
                    <option value="butt90">Vuông 90°</option>
                  </Select>
                </Label>
                <Label>
                  Cây nhôm (mm)
                  <Input
                    type="number"
                    step={10}
                    value={draft.bar_length_mm}
                    onChange={(event) => patchDraft({ bar_length_mm: Number(event.target.value) })}
                  />
                </Label>
                <Label>
                  Mạch cắt (mm)
                  <Input
                    type="number"
                    step={0.5}
                    value={draft.kerf_mm}
                    onChange={(event) => patchDraft({ kerf_mm: Number(event.target.value) })}
                  />
                </Label>
                <Label>
                  Đầu kẹp (mm)
                  <Input
                    type="number"
                    step={5}
                    value={draft.end_trim_mm}
                    onChange={(event) => patchDraft({ end_trim_mm: Number(event.target.value) })}
                  />
                </Label>
                <Label>
                  Nguồn số liệu
                  <Input
                    value={draft.source}
                    placeholder="Catalogue NCC 2025"
                    onChange={(event) => patchDraft({ source: event.target.value })}
                  />
                </Label>
              </div>

              <Label>
                Ghi chú hệ
                <Input value={draft.notes} onChange={(event) => patchDraft({ notes: event.target.value })} />
              </Label>

              <div>
                <h3 className="mb-2 text-[13px] font-semibold text-primary">Thông số công nghệ</h3>
                <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                  {RULE_FIELDS.map((rule) => (
                    <Label key={String(rule.key)}>
                      {rule.label}
                      <Input
                        type="number"
                        step={0.5}
                        value={draft.rules[rule.key] ?? ''}
                        onChange={(event) => patchRule(rule.key, event.target.value)}
                      />
                    </Label>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="mb-2 text-[13px] font-semibold text-primary">Thanh profile</h3>
                <ProfilesEditor profiles={profiles} systemCode={draft.code} onChange={setProfiles} />
              </div>
            </div>
          </>
        ) : (
          <div className="px-5 py-20 text-center text-sm text-muted-foreground">
            Chọn một hệ nhôm bên trái, hoặc bấm <b>Mới</b> để tạo hệ mới.
          </div>
        )}
      </Card>
    </div>
  )
}
