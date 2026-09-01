import type { GestorPeriod } from '../types/gestor'

export const DEFAULT_GESTOR_BRANCH = '0101'
export const MIN_GESTOR_YEAR = 2000
export const MAX_GESTOR_YEAR = 2100

export const mockGestorPeriods: readonly GestorPeriod[] = [
  { ano: 2025, mes: 8 },
  { ano: 2025, mes: 9 },
  { ano: 2025, mes: 10 },
]
export const defaultDevGestorPeriod: GestorPeriod = { ano: 2025, mes: 9 }
