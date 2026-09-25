import type { GestorRow } from '../types/gestor'

export interface GestorDashboardTotals {
  limiteOriginal: number
  pcAberto: number
  nfEntrada: number
  contingenciaOk: number
  contingenciaEmAprovacao: number
  saldoPrevisto: number
  saldoReal: number
  percentualConsumido: number | null
}

export function summarizeGestorRows(rows: readonly GestorRow[]): GestorDashboardTotals {
  const totals = rows.reduce((current, row) => ({
    limiteOriginal: current.limiteOriginal + row.limiteOriginal,
    pcAberto: current.pcAberto + row.pcAberto,
    nfEntrada: current.nfEntrada + row.nfEntrada,
    contingenciaOk: current.contingenciaOk + row.contingenciaOk,
    contingenciaEmAprovacao: current.contingenciaEmAprovacao + row.contingenciaEmAprovacao,
    saldoPrevisto: current.saldoPrevisto + row.saldoPrevisto,
    saldoReal: current.saldoReal + row.saldoReal,
  }), { limiteOriginal: 0, pcAberto: 0, nfEntrada: 0, contingenciaOk: 0, contingenciaEmAprovacao: 0, saldoPrevisto: 0, saldoReal: 0 })
  return {
    ...totals,
    percentualConsumido: totals.limiteOriginal > 0 ? totals.nfEntrada / totals.limiteOriginal * 100 : null,
  }
}

export function dashboardCommitmentChart(totals: GestorDashboardTotals) {
  return [
    { label: 'Limite Original', valor: totals.limiteOriginal },
    { label: 'PC em aberto', valor: totals.pcAberto },
    { label: 'NF Entrada', valor: totals.nfEntrada },
  ]
}

export function topConsumptionRows(rows: readonly GestorRow[]) {
  return rows
    .filter((row) => row.limiteOriginal > 0 || row.nfEntrada > 0)
    .map((row) => ({ ...row, consumo: row.limiteOriginal > 0 ? row.nfEntrada / row.limiteOriginal * 100 : 100 }))
    .sort((left, right) => right.consumo - left.consumo)
    .slice(0, 10)
}

export function lowestSaldoPrevistoRows(rows: readonly GestorRow[]) {
  return [...rows].sort((left, right) => left.saldoPrevisto - right.saldoPrevisto).slice(0, 10)
}

export function countOverLimitRows(rows: readonly GestorRow[]) {
  return rows.filter((row) => row.limiteOriginal > 0 && row.nfEntrada / row.limiteOriginal > 1).length
}

export interface ConsumptionCriticalRow {
  row: GestorRow
  consumption: number | null
}

export function criticalConsumptionRows(rows: readonly GestorRow[]): ConsumptionCriticalRow[] {
  return rows
    .filter((row) => (row.limiteOriginal > 0 && row.nfEntrada / row.limiteOriginal > 1) || (row.limiteOriginal === 0 && row.nfEntrada > 0))
    .map((row) => ({ row, consumption: row.limiteOriginal > 0 ? row.nfEntrada / row.limiteOriginal * 100 : null }))
    .sort((left, right) => {
      if (left.consumption === null && right.consumption !== null) return -1
      if (left.consumption !== null && right.consumption === null) return 1
      if (left.consumption === null && right.consumption === null) return left.row.naturezaCodigo.localeCompare(right.row.naturezaCodigo)
      return (right.consumption ?? 0) - (left.consumption ?? 0) || left.row.naturezaCodigo.localeCompare(right.row.naturezaCodigo)
    })
}

export function negativeSaldoPrevistoRows(rows: readonly GestorRow[]) {
  return rows.filter((row) => row.saldoPrevisto < 0).sort((left, right) => left.saldoPrevisto - right.saldoPrevisto)
}

export function pcAbertoRows(rows: readonly GestorRow[]) {
  return rows.filter((row) => row.pcAberto > 0).sort((left, right) => right.pcAberto - left.pcAberto)
}

export function contingencyApprovalRows(rows: readonly GestorRow[]) {
  return rows.filter((row) => row.contingenciaEmAprovacao > 0).sort((left, right) => right.contingenciaEmAprovacao - left.contingenciaEmAprovacao)
}

export function negativeSaldoPrevistoTotal(rows: readonly GestorRow[]) {
  return negativeSaldoPrevistoRows(rows).reduce((total, row) => total + row.saldoPrevisto, 0)
}
