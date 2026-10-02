import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { EnvironmentSelector } from '../components/gestor/EnvironmentSelector'
import { NatureFilter } from '../components/gestor/NatureFilter'
import { DEFAULT_GESTOR_BRANCH } from '../config/gestor'
import { useGestorEnvironment } from '../context/GestorEnvironmentContext'
import { useGestorMonthlyEvolution, type GestorMonthlyEvolutionPoint } from '../hooks/useGestorMonthlyEvolution'
import type { GestorDataEnvironment, GestorPeriod } from '../types/gestor'
import { formatCurrency } from '../utils/currency'
import { formatGestorPeriod, getCurrentGestorPeriod, nextGestorPeriod, parseGestorPeriodInput, periodInputValue, previousGestorPeriod, resolvePeriodForEnvironment } from '../utils/period'
import { resolveGestorEnvironmentSelection } from '../utils/environment'
import { exportMonthlyEvolutionCsv, exportMonthlyEvolutionXlsx, type MonthlyEvolutionExportRow } from '../utils/monthlyEvolutionExport'

type SortField = keyof Pick<MonthlyEvolutionExportRow, 'mes' | 'limiteOriginal' | 'pcAberto' | 'nfEntrada' | 'gastoPrevisto' | 'saldoPrevisto' | 'saldoReal' | 'percentualConsumido'>
type Sort = { field: SortField; direction: 'ascending' | 'descending' }

const columns: { label: string; field: SortField; monetary?: boolean }[] = [
  { label: 'M\u00eas', field: 'mes' },
  { label: 'Limite Original', field: 'limiteOriginal', monetary: true },
  { label: 'PC em Aberto', field: 'pcAberto', monetary: true },
  { label: 'NF Entrada', field: 'nfEntrada', monetary: true },
  { label: 'Gasto Previsto', field: 'gastoPrevisto', monetary: true },
  { label: 'Saldo Previsto', field: 'saldoPrevisto', monetary: true },
  { label: 'Saldo Real', field: 'saldoReal', monetary: true },
  { label: '% Consumido', field: 'percentualConsumido' },
]

function comparePeriods(left: GestorPeriod, right: GestorPeriod): number {
  return left.ano - right.ano || left.mes - right.mes
}

function monthsBetween(start: GestorPeriod, end: GestorPeriod): number {
  return (end.ano - start.ano) * 12 + end.mes - start.mes + 1
}

function periodRange(start: GestorPeriod, end: GestorPeriod): GestorPeriod[] {
  const result: GestorPeriod[] = []
  let current: GestorPeriod | null = start
  while (current && comparePeriods(current, end) <= 0) {
    result.push(current)
    current = nextGestorPeriod(current)
  }
  return result
}

function initialStart(end: GestorPeriod): GestorPeriod {
  let current = end
  for (let index = 1; index < 6; index += 1) current = previousGestorPeriod(current) ?? current
  return current
}

function aggregateSelectedNature(point: GestorMonthlyEvolutionPoint, natureCodes: ReadonlySet<string>): MonthlyEvolutionExportRow {
  const rows = point.naturezas.filter((row) => natureCodes.has(row.naturezaCodigo))
  const totals = rows.reduce((current, row) => ({
    limiteOriginal: current.limiteOriginal + row.limiteOriginal,
    pcAberto: current.pcAberto + row.pcAberto,
    nfEntrada: current.nfEntrada + row.nfEntrada,
    saldoPrevisto: current.saldoPrevisto + row.saldoPrevisto,
    saldoReal: current.saldoReal + row.saldoReal,
  }), { limiteOriginal: 0, pcAberto: 0, nfEntrada: 0, saldoPrevisto: 0, saldoReal: 0 })
  return {
    mes: formatGestorPeriod(point.periodo),
    ...totals,
    gastoPrevisto: totals.pcAberto + totals.nfEntrada,
    percentualConsumido: totals.limiteOriginal > 0 ? totals.nfEntrada / totals.limiteOriginal * 100 : null,
  }
}

function pointToRow(point: GestorMonthlyEvolutionPoint): MonthlyEvolutionExportRow {
  return {
    mes: formatGestorPeriod(point.periodo),
    limiteOriginal: point.limiteOriginal,
    pcAberto: point.pcAberto,
    nfEntrada: point.nfEntrada,
    gastoPrevisto: point.gastoPrevisto,
    saldoPrevisto: point.saldoPrevisto,
    saldoReal: point.saldoReal,
    percentualConsumido: point.percentualConsumido,
  }
}

function sortRows(rows: readonly MonthlyEvolutionExportRow[], sort: Sort): MonthlyEvolutionExportRow[] {
  const factor = sort.direction === 'ascending' ? 1 : -1
  return [...rows].sort((left, right) => {
    const leftValue = left[sort.field]
    const rightValue = right[sort.field]
    if (typeof leftValue === 'string' && typeof rightValue === 'string') return factor * leftValue.localeCompare(rightValue, 'pt-BR', { numeric: true })
    return factor * ((leftValue ?? -Infinity) as number - ((rightValue ?? -Infinity) as number))
  })
}

function compactCurrency(value: unknown): string {
  const numeric = Number(value)
  if (Math.abs(numeric) >= 1_000_000) return 'R$ ' + (numeric / 1_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + ' mi'
  return 'R$ ' + (numeric / 1_000).toLocaleString('pt-BR', { maximumFractionDigits: 0 }) + ' mil'
}

function EvolutionTooltip({ active, payload, label }: { active?: boolean; label?: string; payload?: { name: string; value: number }[] }) {
  if (!active || !payload?.length) return null
  return <div className="chart-tooltip"><strong>{label}</strong>{payload.map((item) => <span key={item.name}>{item.name}: {formatCurrency(item.value)}</span>)}</div>
}

export function MonthlyEvolutionReportPage() {
  const current = getCurrentGestorPeriod()
  const [start, setStart] = useState<GestorPeriod>(() => initialStart(current))
  const [end, setEnd] = useState<GestorPeriod>(() => current)
  const [natureSearch, setNatureSearch] = useState('')
  const [selectedNature, setSelectedNature] = useState('')
  const [sort, setSort] = useState<Sort>({ field: 'mes', direction: 'ascending' })
  const { environment, environments, setEnvironment } = useGestorEnvironment()
  const invalidRange = comparePeriods(start, end) > 0 || monthsBetween(start, end) > 24
  const periods = useMemo(() => invalidRange ? [] : periodRange(start, end), [end, invalidRange, start])
  const { data, error, isLoading, reload } = useGestorMonthlyEvolution(periods, DEFAULT_GESTOR_BRANCH, environment)
  const natureOptions = useMemo(() => {
    const byCode = new Map<string, { code: string; description: string }>()
    data.flatMap((point) => point.naturezas).forEach((row) => byCode.set(row.naturezaCodigo, { code: row.naturezaCodigo, description: row.naturezaDescricao }))
    return [...byCode.values()].sort((left, right) => left.code.localeCompare(right.code, 'pt-BR', { numeric: true }))
  }, [data])
  const matchingNatureCodes = useMemo(() => {
    const query = natureSearch.trim().toLocaleLowerCase()
    const matches = natureOptions.filter((option) => !query || (option.code + ' ' + option.description).toLocaleLowerCase().includes(query))
    return new Set(selectedNature ? [selectedNature] : matches.map((option) => option.code))
  }, [natureOptions, natureSearch, selectedNature])
  const rows = useMemo(() => data.map((point) => selectedNature || natureSearch ? aggregateSelectedNature(point, matchingNatureCodes) : pointToRow(point)), [data, matchingNatureCodes, natureSearch, selectedNature])
  const sortedRows = useMemo(() => sortRows(rows, sort), [rows, sort])
  const latest = rows[rows.length - 1]
  const disabled = isLoading || !!error || sortedRows.length === 0
  const filename = (extension: 'csv' | 'xlsx') => 'evolucao-mensal-' + environment + '-' + periodInputValue(start) + '_a_' + periodInputValue(end) + '.' + extension

  const changeEnvironment = (next: GestorDataEnvironment) => {
    const confirmed = next !== 'prd' || window.confirm('Consultar dados de PRODU\u00c7\u00c3O?\n\nA consulta ser\u00e1 somente leitura.')
    if (!confirmed) return
    const resolved = resolveGestorEnvironmentSelection(environment, next, confirmed)
    setEnvironment(resolved)
    setStart((value) => resolvePeriodForEnvironment(value, resolved))
    setEnd((value) => resolvePeriodForEnvironment(value, resolved))
  }
  const changePeriod = (setter: (period: GestorPeriod) => void, value: string) => {
    const parsed = parseGestorPeriodInput(value, environment)
    if (parsed) setter(parsed)
  }
  const toggleSort = (field: SortField) => setSort((current) => current.field === field ? { field, direction: current.direction === 'ascending' ? 'descending' : 'ascending' } : { field, direction: 'ascending' })

  return <div className="reports-page">
    <header className="gestor-header"><p className="eyebrow">Relat&oacute;rios / Evolu&ccedil;&atilde;o Mensal</p><h2>Evolu&ccedil;&atilde;o Mensal</h2><p>Evolu&ccedil;&atilde;o mensal de limite, compras, notas fiscais e saldos.</p></header>
    <div className="report-toolbar report-monthly-toolbar"><EnvironmentSelector environment={environment} environments={environments} onChange={changeEnvironment} /><label className="nature-filter"><span className="control-label">M&ecirc;s inicial</span><input type="month" value={periodInputValue(start)} onChange={(event) => changePeriod(setStart, event.target.value)} /></label><label className="nature-filter"><span className="control-label">M&ecirc;s final</span><input type="month" value={periodInputValue(end)} onChange={(event) => changePeriod(setEnd, event.target.value)} /></label></div>
    <div className="report-filters report-monthly-filters"><NatureFilter value={natureSearch} onChange={setNatureSearch} onClear={() => { setNatureSearch(''); setSelectedNature('') }} /><label className="nature-filter"><span className="control-label">Natureza selecionada</span><select value={selectedNature} onChange={(event) => setSelectedNature(event.target.value)}><option value="">Todas</option>{natureOptions.filter((option) => !natureSearch.trim() || (option.code + ' ' + option.description).toLocaleLowerCase().includes(natureSearch.trim().toLocaleLowerCase())).map((option) => <option value={option.code} key={option.code}>{option.code} - {option.description}</option>)}</select></label></div>
    {invalidRange ? <p className="report-validation-error" role="alert">{comparePeriods(start, end) > 0 ? 'O m\u00eas inicial deve ser anterior ou igual ao m\u00eas final.' : 'Selecione um per\u00edodo de at\u00e9 24 meses.'}</p> : null}
    <div className="report-summary report-monthly-summary" aria-label="Resumo do &uacute;ltimo m&ecirc;s"><article><span>Limite Original</span><strong>{latest ? formatCurrency(latest.limiteOriginal) : '—'}</strong></article><article><span>PC em Aberto</span><strong>{latest ? formatCurrency(latest.pcAberto) : '—'}</strong></article><article><span>NF Entrada</span><strong>{latest ? formatCurrency(latest.nfEntrada) : '—'}</strong></article><article><span>Saldo Previsto</span><strong>{latest ? formatCurrency(latest.saldoPrevisto) : '—'}</strong></article><article><span>Saldo Real</span><strong>{latest ? formatCurrency(latest.saldoReal) : '—'}</strong></article></div>
    <p className="report-reference">Refer&ecirc;ncia: {latest?.mes ?? '—'}</p>
    <section className="monthly-evolution-chart report-table-section"><div className="table-heading"><div><p className="control-label">Evolu&ccedil;&atilde;o</p><h3>Indicadores mensais</h3></div><p>{isLoading ? 'Consultando meses' : error ? 'Dados indispon&iacute;veis' : periods.length + ' meses'}</p></div><div className="monthly-evolution-viewport"><ResponsiveContainer width="100%" height="100%"><LineChart data={sortedRows} margin={{ top: 12, right: 16, left: 8, bottom: 4 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="mes" tick={{ fontSize: 11 }} /><YAxis tickFormatter={compactCurrency} width={68} tick={{ fontSize: 10 }} /><Tooltip content={<EvolutionTooltip />} /><Legend wrapperStyle={{ fontSize: 12 }} /><Line type="monotone" dataKey="limiteOriginal" name="Limite Original" stroke="#23618b" strokeWidth={2.5} dot={{ r: 3 }} /><Line type="monotone" dataKey="pcAberto" name="PC em Aberto" stroke="#b56d16" strokeWidth={2.5} dot={{ r: 3 }} /><Line type="monotone" dataKey="nfEntrada" name="NF Entrada" stroke="#27805d" strokeWidth={2.5} dot={{ r: 3 }} /><Line type="monotone" dataKey="saldoPrevisto" name="Saldo Previsto" stroke="#c15c5c" strokeWidth={2.5} dot={{ r: 3 }} /><Line type="monotone" dataKey="saldoReal" name="Saldo Real" stroke="#7762b5" strokeWidth={2.5} dot={{ r: 3 }} /></LineChart></ResponsiveContainer></div></section>
    <section className="report-table-section"><div className="table-heading"><div><p className="control-label">Detalhamento</p><h3>Dados mensais</h3></div><p>{isLoading ? 'Consultando meses' : error ? 'Dados indispon&iacute;veis' : sortedRows.length + ' linhas'}</p><div className="table-export-actions"><button type="button" disabled={disabled} onClick={() => exportMonthlyEvolutionCsv(sortedRows, filename('csv'))}>Exportar CSV</button><button type="button" disabled={disabled} onClick={() => exportMonthlyEvolutionXlsx(sortedRows, filename('xlsx'))}>Exportar Excel</button></div></div><div className="table-scroll report-table-scroll" tabIndex={0}><table className="gestor-table report-table"><thead><tr>{columns.map((column) => <th className={column.monetary ? 'monetary-column' : undefined} key={column.label}><button className="table-sort-trigger" type="button" onClick={() => toggleSort(column.field)}>{column.label}{sort.field === column.field ? (sort.direction === 'ascending' ? ' \u2191' : ' \u2193') : ''}</button></th>)}</tr></thead><tbody>{isLoading ? <tr><td className="empty-table" colSpan={columns.length}>Carregando evolu&ccedil;&atilde;o mensal...</td></tr> : error ? <tr><td className="empty-table" colSpan={columns.length}>N&atilde;o foi poss&iacute;vel carregar a evolu&ccedil;&atilde;o mensal. <button className="table-retry" type="button" onClick={reload}>Tentar novamente</button></td></tr> : invalidRange ? <tr><td className="empty-table" colSpan={columns.length}>Ajuste o intervalo para continuar.</td></tr> : sortedRows.length === 0 ? <tr><td className="empty-table" colSpan={columns.length}>Nenhum dado encontrado para os filtros selecionados.</td></tr> : sortedRows.map((row) => <tr key={row.mes}><th scope="row">{row.mes}</th><td className="money-cell">{formatCurrency(row.limiteOriginal)}</td><td className="money-cell">{formatCurrency(row.pcAberto)}</td><td className="money-cell">{formatCurrency(row.nfEntrada)}</td><td className="money-cell">{formatCurrency(row.gastoPrevisto)}</td><td className={'money-cell' + (row.saldoPrevisto < 0 ? ' money-negative' : '')}>{formatCurrency(row.saldoPrevisto)}</td><td className={'money-cell' + (row.saldoReal < 0 ? ' money-negative' : '')}>{formatCurrency(row.saldoReal)}</td><td>{row.percentualConsumido === null ? 'Sem limite' : row.percentualConsumido.toFixed(2).replace('.', ',') + '%'}</td></tr>)}</tbody></table></div></section>
    <Link className="report-back-link" to="/relatorios">&larr; Voltar para Relat&oacute;rios</Link>
  </div>
}
