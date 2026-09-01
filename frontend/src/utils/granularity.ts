export const gestorGranularityOptions = [
  { value: 'monthly', label: 'Mensal' },
  { value: 'weekly', label: 'Semanal' },
  { value: 'daily', label: 'Diário' },
] as const

export type GestorGranularity =
  (typeof gestorGranularityOptions)[number]['value']

export function isMonthlyGranularity(
  granularity: GestorGranularity,
): granularity is 'monthly' {
  return granularity === 'monthly'
}

export interface GestorDateInterval {
  inicio: string
  fim: string
  label: string
  selectedDate: Date
}

function toDateValue(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function formatDate(date: Date): string {
  return date.toLocaleDateString('pt-BR')
}

function inPeriod(date: Date, year: number, month: number): boolean {
  return date.getFullYear() === year && date.getMonth() + 1 === month
}

export function getGestorDateInterval(
  granularity: GestorGranularity,
  period: { ano: number; mes: number },
  selectedDate: Date,
): GestorDateInterval | null {
  if (granularity === 'monthly') return null
  const selected = inPeriod(selectedDate, period.ano, period.mes)
    ? selectedDate
    : new Date(period.ano, period.mes - 1, 1)
  if (granularity === 'daily') {
    const value = toDateValue(selected)
    return { inicio: value, fim: value, label: formatDate(selected), selectedDate: selected }
  }
  const monday = new Date(selected)
  monday.setDate(selected.getDate() - ((selected.getDay() + 6) % 7))
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  const monthStart = new Date(period.ano, period.mes - 1, 1)
  const monthEnd = new Date(period.ano, period.mes, 0)
  const inicio = monday < monthStart ? monthStart : monday
  const fim = sunday > monthEnd ? monthEnd : sunday
  return {
    inicio: toDateValue(inicio),
    fim: toDateValue(fim),
    label: `${formatDate(monday)} a ${formatDate(sunday)}`,
    selectedDate: selected,
  }
}

export function navigateGestorGranularity(
  granularity: GestorGranularity,
  period: { ano: number; mes: number },
  selectedDate: Date,
  direction: -1 | 1,
): Date | null {
  if (granularity === 'monthly') return null
  const next = new Date(selectedDate)
  next.setDate(next.getDate() + direction * (granularity === 'weekly' ? 7 : 1))
  return inPeriod(next, period.ano, period.mes) ? next : null
}
