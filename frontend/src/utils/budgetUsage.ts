import type { GestorRow } from '../types/gestor'

export type UsageLevel =
  | 'comfortable'
  | 'attention'
  | 'near-limit'
  | 'committed'
  | 'exceeded'

const PERCENTAGE_EQUALITY_TOLERANCE = 1e-9

export interface BudgetUsage {
  consumption: number
  percentage: number | null
  roundedPercentage: number | null
  visualPercentage: number
  label: string
  accessibleLabel: string
  level: UsageLevel
}

export function getUsageLevel(percentage: number): UsageLevel {
  if (percentage > 100 + PERCENTAGE_EQUALITY_TOLERANCE) return 'exceeded'
  if (
    Math.abs(percentage - 100) <= PERCENTAGE_EQUALITY_TOLERANCE
  ) return 'committed'
  if (percentage >= 90) return 'near-limit'
  if (percentage >= 70) return 'attention'
  return 'comfortable'
}

export function calculateBudgetUsage(
  pcAberto: number,
  nfEntrada: number,
  limiteTotal: number,
): BudgetUsage {
  const consumption = pcAberto + nfEntrada

  if (limiteTotal <= 0) {
    if (limiteTotal === 0 && consumption === 0) {
      return {
        consumption,
        percentage: 0,
        roundedPercentage: 0,
        visualPercentage: 0,
        label: '0% utilizado',
        accessibleLabel: '0% utilizado — faixa confortável',
        level: 'comfortable',
      }
    }

    return {
      consumption,
      percentage: null,
      roundedPercentage: null,
      visualPercentage: 100,
      label: '100%+ utilizado',
      accessibleLabel: '100%+ utilizado — limite excedido',
      level: 'exceeded',
    }
  }

  const percentage = (consumption / limiteTotal) * 100
  const roundedPercentage = Math.round(percentage)
  const level = getUsageLevel(percentage)
  const statusLabels: Record<UsageLevel, string> = {
    comfortable: 'faixa confortável',
    attention: 'atenção ao consumo',
    'near-limit': 'próximo do limite',
    committed: 'limite comprometido',
    exceeded: 'limite excedido',
  }
  const label = `${roundedPercentage}% utilizado`

  return {
    consumption,
    percentage,
    roundedPercentage,
    visualPercentage: Math.min(Math.max(percentage, 0), 100),
    label,
    accessibleLabel: `${label} — ${statusLabels[level]}`,
    level,
  }
}

export function isCriticalGestorRow(
  row: Pick<GestorRow, 'saldoPrevisto' | 'limiteTotal'>,
): boolean {
  return row.saldoPrevisto < 0 || row.limiteTotal < 0
}
