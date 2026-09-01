import {
  defaultDevGestorPeriod,
  MAX_GESTOR_YEAR,
  MIN_GESTOR_YEAR,
  mockGestorPeriods,
} from '../config/gestor'
import type { GestorDataEnvironment, GestorPeriod } from '../types/gestor'

const periodFormatter = new Intl.DateTimeFormat('pt-BR', {
  month: 'long',
  timeZone: 'UTC',
})

export function getCurrentGestorPeriod(date = new Date()): GestorPeriod {
  const year = date.getFullYear()
  if (year < MIN_GESTOR_YEAR) return { ano: MIN_GESTOR_YEAR, mes: 1 }
  if (year > MAX_GESTOR_YEAR) return { ano: MAX_GESTOR_YEAR, mes: 12 }
  return { ano: year, mes: date.getMonth() + 1 }
}

export function formatGestorPeriod(period: GestorPeriod): string {
  const formattedMonth = periodFormatter.format(
    new Date(Date.UTC(period.ano, period.mes - 1)),
  )
  const month =
    formattedMonth.charAt(0).toUpperCase() + formattedMonth.slice(1)
  return `${month} / ${period.ano}`
}

export function isSameGestorPeriod(
  left: GestorPeriod,
  right: GestorPeriod,
): boolean {
  return left.ano === right.ano && left.mes === right.mes
}

export function periodInputValue(period: GestorPeriod): string {
  return `${period.ano}-${String(period.mes).padStart(2, '0')}`
}

export function parseGestorPeriodInput(
  value: string,
  environment: GestorDataEnvironment,
): GestorPeriod | null {
  const match = /^(\d{4})-(\d{2})$/.exec(value)
  if (!match) return null

  const period = { ano: Number(match[1]), mes: Number(match[2]) }
  if (period.mes < 1 || period.mes > 12) {
    return null
  }
  if (environment === 'dev') {
    return mockGestorPeriods.find((candidate) =>
      isSameGestorPeriod(candidate, period),
    ) ?? null
  }
  return period.ano >= MIN_GESTOR_YEAR && period.ano <= MAX_GESTOR_YEAR
    ? period
    : null
}

export function previousGestorPeriod(
  period: GestorPeriod,
): GestorPeriod | null {
  if (period.ano === MIN_GESTOR_YEAR && period.mes === 1) {
    return null
  }
  return period.mes === 1
    ? { ano: period.ano - 1, mes: 12 }
    : { ano: period.ano, mes: period.mes - 1 }
}

export function nextGestorPeriod(period: GestorPeriod): GestorPeriod | null {
  if (period.ano === MAX_GESTOR_YEAR && period.mes === 12) {
    return null
  }
  return period.mes === 12
    ? { ano: period.ano + 1, mes: 1 }
    : { ano: period.ano, mes: period.mes + 1 }
}

interface GestorPeriodNavigation {
  previous: GestorPeriod | null
  next: GestorPeriod | null
}

export function getGestorPeriodNavigation(
  period: GestorPeriod,
  environment: GestorDataEnvironment,
): GestorPeriodNavigation {
  if (environment === 'hml' || environment === 'prd') {
    return {
      previous: previousGestorPeriod(period),
      next: nextGestorPeriod(period),
    }
  }
  const index = mockGestorPeriods.findIndex((candidate) =>
    isSameGestorPeriod(candidate, period),
  )
  return {
    previous: index > 0 ? mockGestorPeriods[index - 1] : null,
    next:
      index >= 0 && index < mockGestorPeriods.length - 1
        ? mockGestorPeriods[index + 1]
        : null,
  }
}

export function resolvePeriodForEnvironment(
  period: GestorPeriod,
  environment: GestorDataEnvironment,
): GestorPeriod {
  if (environment !== 'dev') return period
  return mockGestorPeriods.find((candidate) =>
    isSameGestorPeriod(candidate, period),
  ) ?? defaultDevGestorPeriod
}
