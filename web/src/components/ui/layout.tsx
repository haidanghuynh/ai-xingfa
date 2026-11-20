import * as React from 'react'
import { cn } from '@/lib/utils'

/* -------------------------------------------------------------------------- */
/* Card                                                                      */
/* -------------------------------------------------------------------------- */
export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('rounded-xl border border-border bg-card text-card-foreground shadow-card', className)}
      {...props}
    />
  )
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('flex flex-wrap items-center justify-between gap-3 px-5 py-4', className)} {...props} />
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn('text-[15px] font-semibold text-primary', className)} {...props} />
}

export function CardDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('text-xs text-muted-foreground', className)} {...props} />
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('px-5 pb-5', className)} {...props} />
}

export interface SectionCardProps {
  title: React.ReactNode
  description?: React.ReactNode
  actions?: React.ReactNode
  children: React.ReactNode
  className?: string
  contentClassName?: string
}

export function SectionCard({ title, description, actions, children, className, contentClassName }: SectionCardProps) {
  return (
    <Card className={className}>
      <CardHeader className="border-b border-border/70">
        <div className="space-y-0.5">
          <CardTitle>{title}</CardTitle>
          {description ? <CardDescription>{description}</CardDescription> : null}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </CardHeader>
      <CardContent className={cn('pt-4', contentClassName)}>{children}</CardContent>
    </Card>
  )
}

/* -------------------------------------------------------------------------- */
/* Table                                                                     */
/* -------------------------------------------------------------------------- */
export function Table({ className, ...props }: React.TableHTMLAttributes<HTMLTableElement>) {
  return (
    <div className="overflow-auto rounded-lg border border-border">
      <table className={cn('data-table', className)} {...props} />
    </div>
  )
}

export function EmptyRow({ colSpan, children }: { colSpan: number; children: React.ReactNode }) {
  return (
    <tr>
      <td colSpan={colSpan} className="py-8 text-center text-xs text-muted-foreground">
        {children}
      </td>
    </tr>
  )
}

/* -------------------------------------------------------------------------- */
/* Tabs                                                                      */
/* -------------------------------------------------------------------------- */
export interface TabItem {
  value: string
  label: React.ReactNode
  badge?: React.ReactNode
}

export interface TabsProps {
  items: TabItem[]
  value: string
  onChange: (value: string) => void
  variant?: 'underline' | 'segmented'
  className?: string
}

export function Tabs({ items, value, onChange, variant = 'underline', className }: TabsProps) {
  if (variant === 'segmented') {
    return (
      <div className={cn('inline-flex flex-wrap gap-1 rounded-lg bg-secondary p-1', className)} role="tablist">
        {items.map((item) => (
          <button
            key={item.value}
            type="button"
            role="tab"
            aria-selected={value === item.value}
            onClick={() => onChange(item.value)}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors',
              value === item.value ? 'bg-card text-primary shadow-sm' : 'text-muted-foreground hover:text-primary',
            )}
          >
            {item.label}
            {item.badge ?? null}
          </button>
        ))}
      </div>
    )
  }
  return (
    <div className={cn('flex flex-wrap gap-1 border-b border-border', className)} role="tablist">
      {items.map((item) => (
        <button
          key={item.value}
          type="button"
          role="tab"
          aria-selected={value === item.value}
          onClick={() => onChange(item.value)}
          className={cn(
            '-mb-px inline-flex items-center gap-1.5 border-b-2 px-4 py-2.5 text-[13px] font-semibold transition-colors',
            value === item.value
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-primary',
          )}
        >
          {item.label}
          {item.badge ?? null}
        </button>
      ))}
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/* Metric                                                                    */
/* -------------------------------------------------------------------------- */
export interface MetricProps {
  label: string
  value: React.ReactNode
  unit?: string
  accent?: boolean
  hint?: string
}

export function Metric({ label, value, unit, accent, hint }: MetricProps) {
  return (
    <div
      className={cn(
        'rounded-xl border bg-card px-4 py-3 shadow-card',
        accent ? 'border-accent/30 bg-accent/5' : 'border-border',
      )}
    >
      <div className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className={cn('mt-1 text-xl font-bold tabular-nums', accent ? 'text-accent' : 'text-primary')}>
        {value}
        {unit ? <span className="ml-1 text-xs font-medium text-muted-foreground">{unit}</span> : null}
      </div>
      {hint ? <div className="mt-0.5 text-[11px] text-muted-foreground">{hint}</div> : null}
    </div>
  )
}
