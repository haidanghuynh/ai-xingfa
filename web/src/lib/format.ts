const numberFormat = new Intl.NumberFormat('vi-VN')

export const money = (value: number | null | undefined): string =>
  numberFormat.format(Math.round(Number(value) || 0))

export const num = (value: number | null | undefined, digits = 0): string =>
  (Number(value) || 0).toLocaleString('vi-VN', { maximumFractionDigits: digits })

export const fileSize = (bytes: number | null | undefined): string => {
  const size = Number(bytes) || 0
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(2)} MB`
}

export const today = (): string => new Date().toISOString().slice(0, 10)
