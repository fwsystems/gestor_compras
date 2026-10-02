import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { EnvironmentSelector } from '../components/gestor/EnvironmentSelector'
import { GranularitySelector } from '../components/gestor/GranularitySelector'
import { NatureFilter } from '../components/gestor/NatureFilter'
import { PeriodSelector } from '../components/gestor/PeriodSelector'
import { DEFAULT_GESTOR_BRANCH } from '../config/gestor'
import { useGestorEnvironment } from '../context/GestorEnvironmentContext'
import { useGestor } from '../hooks/useGestor'
import type { GestorDataEnvironment, GestorPeriod, GestorRow } from '../types/gestor'
import { calculateBudgetUsage, isCriticalGestorRow } from '../utils/budgetUsage'
import { formatCurrency } from '../utils/currency'
import { filterGestorRows, hasNatureSearch } from '../utils/natureFilter'
import { getGestorDateInterval, isMonthlyGranularity, navigateGestorGranularity, type GestorGranularity } from '../utils/granularity'
import { resolveGestorEnvironmentSelection } from '../utils/environment'
import { getCurrentGestorPeriod, getGestorPeriodNavigation, resolvePeriodForEnvironment } from '../utils/period'
import { exportConsumptionReportCsv, exportConsumptionReportXlsx, type ConsumptionReportRow } from '../utils/consumptionReportExport'

type ReportSortField = 'naturezaCodigo' | 'naturezaDescricao' | 'limiteOriginal' | 'pcAberto' | 'nfEntrada' | 'pago' | 'aPagar' | 'total' | 'saldoPrevisto' | 'saldoReal' | 'percentualConsumido'
type ReportSort = { field: ReportSortField; direction: 'ascending' | 'descending' }

const columns: { label: string; field: ReportSortField; monetary?: boolean }[] = [
  { label: 'Natureza', field: 'naturezaCodigo' },
  { label: 'Descrição', field: 'naturezaDescricao' },
  { label: 'Limite Original', field: 'limiteOriginal', monetary: true },
  { label: 'PC em Aberto', field: 'pcAberto', monetary: true },
  { label: 'NF Entrada', field: 'nfEntrada', monetary: true },
  { label: 'Pago', field: 'pago', monetary: true },
  { label: 'A Pagar', field: 'aPagar', monetary: true },
  { label: 'Total', field: 'total', monetary: true },
  { label: 'Saldo Previsto', field: 'saldoPrevisto', monetary: true },
  { label: 'Saldo Real', field: 'saldoReal', monetary: true },
  { label: '% Consumido', field: 'percentualConsumido', monetary: true },
]

function reportRow(row: GestorRow): ConsumptionReportRow {
  return {
    naturezaCodigo: row.naturezaCodigo,
    naturezaDescricao: row.naturezaDescricao,
    pcAberto: row.pcAberto,
    nfEntrada: row.nfEntrada,
    contingenciaOk: row.contingenciaOk,
    contingenciaEmAprovacao: row.contingenciaEmAprovacao,
    limiteOriginal: row.limiteOriginal,
    saldoPrevisto: row.saldoPrevisto,
    saldoReal: row.saldoReal,
    pago: row.pago,
    aPagar: row.aPagar,
    total: row.total,
    percentualConsumido: calculateBudgetUsage(row.pcAberto, row.nfEntrada, row.limiteOriginal).percentage,
  }
}

function toggleSort(current: ReportSort | null, field: ReportSortField): ReportSort {
  return current?.field === field
    ? { field, direction: current.direction === 'ascending' ? 'descending' : 'ascending' }
    : { field, direction: 'ascending' }
}

function sortRows(rows: readonly ConsumptionReportRow[], sort: ReportSort | null): ConsumptionReportRow[] {
  if (!sort) return [...rows]
  const direction = sort.direction === 'ascending' ? 1 : -1
  return [...rows].sort((left, right) => {
    const leftValue = left[sort.field]
    const rightValue = right[sort.field]
    if (typeof leftValue === 'string' && typeof rightValue === 'string') return direction * leftValue.localeCompare(rightValue, 'pt-BR', { numeric: true })
    return direction * ((leftValue ?? -Infinity) as number - ((rightValue ?? -Infinity) as number))
  })
}

function reportFilename(environment: GestorDataEnvironment, period: GestorPeriod, extension: 'csv' | 'xlsx'): string {
  return `consumo-por-natureza-${environment}-${period.ano}-${String(period.mes).padStart(2, '0')}.${extension}`
}

export function ConsumptionByNaturePage() {
  const [period, setPeriod] = useState<GestorPeriod>(() => getCurrentGestorPeriod())
  const [granularity, setGranularity] = useState<GestorGranularity>('monthly')
  const [selectedDate, setSelectedDate] = useState(() => new Date(period.ano, period.mes - 1, 1))
  const [natureSearch, setNatureSearch] = useState('')
  const [sort, setSort] = useState<ReportSort | null>(null)
  const { environment, environments, setEnvironment } = useGestorEnvironment()
  const interval = useMemo(() => getGestorDateInterval(granularity, period, selectedDate), [granularity, period, selectedDate])
  const { data, error, isLoading, reload } = useGestor(period, DEFAULT_GESTOR_BRANCH, environment, interval)
  const navigation = getGestorPeriodNavigation(period, environment)
  const isFiltered = hasNatureSearch(natureSearch)
  const rows = useMemo(() => sortRows(filterGestorRows(data?.linhas ?? [], natureSearch).map(reportRow), sort), [data?.linhas, natureSearch, sort])
  const totals = useMemo(() => {
    const paymentTotals = isFiltered
      ? rows.reduce((current, row) => ({ pago: current.pago + row.pago, aPagar: current.aPagar + row.aPagar, total: current.total + row.total }), { pago: 0, aPagar: 0, total: 0 })
      : { pago: data?.pago ?? 0, aPagar: data?.aPagar ?? 0, total: data?.total ?? 0 }
    return {
      limiteOriginal: rows.reduce((total, row) => total + row.limiteOriginal, 0),
      nfEntrada: rows.reduce((total, row) => total + row.nfEntrada, 0),
      ...paymentTotals,
    }
  }, [data?.aPagar, data?.pago, data?.total, isFiltered, rows])
  const changeEnvironment = (next: GestorDataEnvironment) => {
    const confirmed = next !== 'prd' || window.confirm('Consultar dados de PRODUÇÃO?\n\nA consulta será somente leitura.')
    if (!confirmed) return
    setEnvironment(resolveGestorEnvironmentSelection(environment, next, confirmed))
    setPeriod((current) => resolvePeriodForEnvironment(current, next))
  }
  const changePeriod = (next: GestorPeriod) => { setPeriod(next); setSelectedDate(new Date(next.ano, next.mes - 1, 1)) }
  const move = (direction: -1 | 1) => {
    if (isMonthlyGranularity(granularity)) {
      const next = direction === -1 ? navigation.previous : navigation.next
      if (next) changePeriod(next)
    } else {
      const next = navigateGestorGranularity(granularity, period, interval?.selectedDate ?? selectedDate, direction)
      if (next) setSelectedDate(next)
    }
  }
  const canMove = (direction: -1 | 1) => isMonthlyGranularity(granularity)
    ? (direction === -1 ? navigation.previous : navigation.next) !== null
    : navigateGestorGranularity(granularity, period, interval?.selectedDate ?? selectedDate, direction) !== null
  return <div className="reports-page">
    <header className="gestor-header">
      <p className="eyebrow">Relat&oacute;rios / Consumo por Natureza</p>
      <h2>Consumo por Natureza</h2>
      <p>Vis&atilde;o consolidada de limite, compras, notas, pagamentos e saldos.</p>
    </header>
    <div className="report-toolbar"><EnvironmentSelector environment={environment} environments={environments} onChange={changeEnvironment} /><PeriodSelector period={period} onPrevious={() => move(-1)} onNext={() => move(1)} canPrevious={canMove(-1)} canNext={canMove(1)} environment={environment} onPeriodChange={changePeriod} contextLabel={interval?.label} /><GranularitySelector value={granularity} onChange={(next) => { setGranularity(next); setSelectedDate(new Date(period.ano, period.mes - 1, 1)) }} /></div>
    <NatureFilter value={natureSearch} onChange={setNatureSearch} onClear={() => setNatureSearch('')} />
    <div className="report-summary" aria-label="Resumo do relatório">
      <article><span>Total Limite</span><strong>{formatCurrency(totals.limiteOriginal)}</strong></article>
      <article><span>Total NF Entrada</span><strong>{formatCurrency(totals.nfEntrada)}</strong></article>
      <article><span>Total Pago</span><strong>{formatCurrency(totals.pago)}</strong></article>
      <article><span>Total A Pagar</span><strong>{formatCurrency(totals.aPagar)}</strong></article>
      <article><span>Total Pagamentos</span><strong>{formatCurrency(totals.total)}</strong></article>
    </div>
    <section className="report-table-section" aria-labelledby="consumption-table-title">
      <div className="table-heading"><div><p className="control-label">Detalhamento</p><h3 id="consumption-table-title">Consumo por Natureza</h3></div><p>{isLoading ? 'Consultando período' : error ? 'Quantidade indisponível' : `${rows.length}${isFiltered ? ` de ${data?.quantidade ?? 0}` : ''} naturezas`}</p><div className="table-export-actions"><button type="button" disabled={isLoading || !!error || rows.length === 0} onClick={() => exportConsumptionReportCsv(rows, reportFilename(environment, period, 'csv'))}>Exportar CSV</button><button type="button" disabled={isLoading || !!error || rows.length === 0} onClick={() => exportConsumptionReportXlsx(rows, reportFilename(environment, period, 'xlsx'))}>Exportar Excel</button></div></div>
      <div className="table-scroll report-table-scroll" tabIndex={0} aria-label="Tabela de consumo por Natureza"><table className="gestor-table report-table"><thead><tr>{columns.map((column) => <th className={column.monetary ? 'monetary-column' : undefined} key={column.field}><button className="table-sort-trigger" type="button" onClick={() => setSort((current) => toggleSort(current, column.field))}>{column.label}{sort?.field === column.field ? (sort.direction === 'ascending' ? ' ↑' : ' ↓') : ''}</button></th>)}</tr></thead><tbody>{isLoading ? <tr><td className="empty-table" colSpan={columns.length}>Carregando dados...</td></tr> : error ? <tr><td className="empty-table" colSpan={columns.length}>Não foi possível carregar os dados. <button className="table-retry" type="button" onClick={reload}>Tentar novamente</button></td></tr> : rows.length === 0 ? <tr><td className="empty-table" colSpan={columns.length}>{isFiltered ? 'Nenhuma Natureza encontrada para o filtro.' : 'Nenhum dado disponível para este período.'}</td></tr> : rows.map((row) => { const usage = calculateBudgetUsage(row.pcAberto, row.nfEntrada, row.limiteOriginal); return <tr className={isCriticalGestorRow(row) ? 'critical-row' : undefined} key={row.naturezaCodigo}><th className="nature-cell" scope="row"><span className="nature-code">{row.naturezaCodigo}</span></th><td>{row.naturezaDescricao}</td><td className="money-cell">{formatCurrency(row.limiteOriginal)}</td><td className="money-cell">{formatCurrency(row.pcAberto)}</td><td className="money-cell">{formatCurrency(row.nfEntrada)}</td><td className={`money-cell${row.pago < 0 ? ' money-negative' : ''}`}>{formatCurrency(row.pago)}</td><td className="money-cell">{formatCurrency(row.aPagar)}</td><td className="money-cell">{formatCurrency(row.total)}</td><td className={`money-cell${row.saldoPrevisto < 0 ? ' money-negative' : ''}`}>{formatCurrency(row.saldoPrevisto)}</td><td className={`money-cell${row.saldoReal < 0 ? ' money-negative' : ''}`}>{formatCurrency(row.saldoReal)}</td><td className="money-cell">{usage.percentage === null ? 'Sem limite' : `${usage.percentage.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`}</td></tr> })}</tbody></table></div>
    </section>
    <Link className="report-back-link" to="/relatorios">← Voltar para Relatórios</Link>
  </div>
}
