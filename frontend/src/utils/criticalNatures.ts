import type { GestorRow } from '../types/gestor'
import { calculateBudgetUsage } from './budgetUsage'
import type { CriticalNaturesReportLine } from './criticalNaturesReportExport'

export type Criticality = 'all' | 'consumo' | 'saldo' | 'sem-limite'

export interface ClassifiedCriticalNature {
  line: CriticalNaturesReportLine
  types: Exclude<Criticality, 'all'>[]
}

export function classifyCriticalNature(row: GestorRow): ClassifiedCriticalNature | null {
  const usage = calculateBudgetUsage(row.pcAberto, row.nfEntrada, row.limiteOriginal)
  const consumo = row.limiteOriginal > 0 && row.nfEntrada / row.limiteOriginal > 1
  const saldo = row.saldoPrevisto < 0
  const semLimite = row.limiteOriginal === 0 && row.nfEntrada > 0
  if (!consumo && !saldo && !semLimite) return null
  const types: Exclude<Criticality, 'all'>[] = []
  if (consumo) types.push('consumo')
  if (saldo) types.push('saldo')
  if (semLimite) types.push('sem-limite')
  const labels = types.map((type) => type === 'consumo' ? 'Consumo cr\u00edtico' : type === 'saldo' ? 'Saldo previsto negativo' : 'Sem limite')
  return {
    types,
    line: {
      naturezaCodigo: row.naturezaCodigo,
      naturezaDescricao: row.naturezaDescricao,
      situacao: labels.join(' | '),
      limiteOriginal: row.limiteOriginal,
      pcAberto: row.pcAberto,
      nfEntrada: row.nfEntrada,
      gastoPrevisto: row.pcAberto + row.nfEntrada,
      saldoPrevisto: row.saldoPrevisto,
      saldoReal: row.saldoReal,
      percentualConsumido: usage.percentage,
    },
  }
}
