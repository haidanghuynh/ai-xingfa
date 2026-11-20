import { Plus, Trash2 } from 'lucide-react'
import { Button, Input, Select } from '@/components/ui/primitives'
import { Table } from '@/components/ui/layout'
import type { ProfileDef } from '@/types/api'

export const PROFILE_KEYS: { value: string; label: string }[] = [
  { value: 'frame', label: 'Khung bao' },
  { value: 'sash', label: 'Cánh' },
  { value: 'mullion', label: 'Đố đứng' },
  { value: 'transom', label: 'Đố ngang' },
  { value: 'track_top', label: 'Ray trên' },
  { value: 'track_bottom', label: 'Ray dưới' },
  { value: 'bead', label: 'Nẹp kính' },
]

interface ProfilesEditorProps {
  profiles: ProfileDef[]
  systemCode: string
  onChange: (profiles: ProfileDef[]) => void
}

export function ProfilesEditor({ profiles, systemCode, onChange }: ProfilesEditorProps) {
  const update = (index: number, patch: Partial<ProfileDef>) =>
    onChange(profiles.map((profile, position) => (position === index ? { ...profile, ...patch } : profile)))

  const addProfile = () => {
    const used = new Set(profiles.map((profile) => profile.key))
    const next = PROFILE_KEYS.find((item) => !used.has(item.value)) ?? PROFILE_KEYS[PROFILE_KEYS.length - 1]
    onChange([
      ...profiles,
      {
        key: next.value,
        code: `${systemCode || 'HE'}-${next.value.toUpperCase()}`,
        name: next.label,
        width_mm: 50,
        depth_mm: 50,
        wall_mm: 1.4,
        kg_per_m: 1.2,
        glass_groove_mm: 24,
        price_per_kg: null,
      },
    ])
  }

  return (
    <div className="space-y-2">
      <Table>
        <thead>
          <tr>
            <th className="w-32">Loại</th>
            <th className="w-32">Mã thanh</th>
            <th>Tên</th>
            <th className="w-20">Mặt cắt</th>
            <th className="w-20">Sâu</th>
            <th className="w-20">Vách</th>
            <th className="w-20">kg/m</th>
            <th className="w-24">Rãnh kính</th>
            <th className="w-24">Giá/kg</th>
            <th className="w-10" />
          </tr>
        </thead>
        <tbody>
          {profiles.map((profile, index) => (
            <tr key={`${profile.key}-${index}`}>
              <td>
                <Select value={profile.key} onChange={(event) => update(index, { key: event.target.value })}>
                  {PROFILE_KEYS.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </Select>
              </td>
              <td>
                <Input value={profile.code} onChange={(event) => update(index, { code: event.target.value })} />
              </td>
              <td>
                <Input value={profile.name} onChange={(event) => update(index, { name: event.target.value })} />
              </td>
              <td>
                <Input
                  type="number"
                  step={0.5}
                  value={profile.width_mm}
                  onChange={(event) => update(index, { width_mm: Number(event.target.value) })}
                />
              </td>
              <td>
                <Input
                  type="number"
                  step={0.5}
                  value={profile.depth_mm}
                  onChange={(event) => update(index, { depth_mm: Number(event.target.value) })}
                />
              </td>
              <td>
                <Input
                  type="number"
                  step={0.1}
                  value={profile.wall_mm}
                  onChange={(event) => update(index, { wall_mm: Number(event.target.value) })}
                />
              </td>
              <td>
                <Input
                  type="number"
                  step={0.01}
                  value={profile.kg_per_m}
                  onChange={(event) => update(index, { kg_per_m: Number(event.target.value) })}
                />
              </td>
              <td>
                <Input
                  type="number"
                  step={1}
                  value={profile.glass_groove_mm}
                  onChange={(event) => update(index, { glass_groove_mm: Number(event.target.value) })}
                />
              </td>
              <td>
                <Input
                  type="number"
                  step={500}
                  value={profile.price_per_kg ?? ''}
                  placeholder="—"
                  onChange={(event) =>
                    update(index, {
                      price_per_kg: event.target.value === '' ? null : Number(event.target.value),
                    })
                  }
                />
              </td>
              <td>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-destructive hover:bg-destructive/10"
                  onClick={() => onChange(profiles.filter((_, position) => position !== index))}
                  title="Xóa thanh"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </td>
            </tr>
          ))}
          {profiles.length === 0 ? (
            <tr>
              <td colSpan={10} className="py-6 text-center text-xs text-muted-foreground">
                Chưa có thanh nào — hệ nhôm cần tối thiểu 1 thanh <b>frame</b> và 1 thanh <b>sash</b>.
              </td>
            </tr>
          ) : null}
        </tbody>
      </Table>
      <div className="flex items-center justify-between">
        <Button variant="outline" size="sm" onClick={addProfile}>
          <Plus className="h-3.5 w-3.5" /> Thêm thanh
        </Button>
        <p className="text-[11px] text-muted-foreground">
          Mặt cắt = chiều rộng nhìn thấy (mm) · Sâu = chiều sâu profile · kg/m dùng tính khối lượng &amp; tiền nhôm
        </p>
      </div>
    </div>
  )
}
