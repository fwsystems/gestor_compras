import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { EnvironmentSelector } from '../components/gestor/EnvironmentSelector'
import { GranularitySelector } from '../components/gestor/GranularitySelector'
import { NatureFilter } from '../components/gestor/NatureFilter'
import { PeriodSelector } from '../components/gestor/PeriodSelector'
import { DEFAULT_GESTOR_BRANCH } from '../config/gestor'
import { useGestorEnvironment } from '../context/GestorEnvironmentContext'
import { useGestor } from '../hooks/useGestor'
import type { GestorDataEnvironment, GestorPeriod } from '../types/gestor'
import { formatCurrency } from '../utils/currency'
import { classifyCriticalNature, type Criticality } from '../utils/criticalNatures'
import { filterGestorRows } from '../utils/natureFilter'
import { getGestorDateInterval, isMonthlyGranularity, navigateGestorGranularity, type GestorGranularity } from '../utils/granularity'
import { resolveGestorEnvironmentSelection } from '../utils/environment'
import { getCurrentGestorPeriod, getGestorPeriodNavigation, resolvePeriodForEnvironment } from '../utils/period'
import { exportCriticalNaturesCsv, exportCriticalNaturesXlsx, type CriticalNaturesReportLine } from '../utils/criticalNaturesReportExport'

type SortField = keyof Pick<CriticalNaturesReportLine, 'naturezaCodigo' | 'naturezaDescricao' | 'situacao' | 'limiteOriginal' | 'pcAberto' | 'nfEntrada' | 'gastoPrevisto' | 'saldoPrevisto' | 'saldoReal' | 'percentualConsumido'>
type Sort = { field: SortField; direction: 'ascending' | 'descending' }

const columns: { label: string; field: SortField; monetary?: boolean }[] = [
  { label: 'Natureza', field: 'naturezaCodigo' },
  { label: 'Descri\u00e7\u00e3o da Natureza', field: 'naturezaDescricao' },
  { label: 'Situa\u00e7\u00e3o', field: 'situacao' },
  { label: 'Limite Original', field: 'limiteOriginal', monetary: true },
  { label: 'PC em Aberto', field: 'pcAberto', monetary: true },
  { label: 'NF Entrada', field: 'nfEntrada', monetary: true },
  { label: 'Gasto Previsto', field: 'gastoPrevisto', monetary: true },
  { label: 'Saldo Previsto', field: 'saldoPrevisto', monetary: true },
  { label: 'Saldo Real', field: 'saldoReal', monetary: true },
  { label: '% Consumido', field: 'percentualConsumido' },
]

function sortLines(rows: readonly CriticalNaturesReportLine[], sort: Sort): CriticalNaturesReportLine[] {
  const factor = sort.direction === 'ascending' ? 1 : -1
  return [...rows].sort((left, right) => {
    const leftValue = left[sort.field]
    const rightValue = right[sort.field]
    if (typeof leftValue === 'string' && typeof rightValue === 'string') return factor * leftValue.localeCompare(rightValue, 'pt-BR', { numeric: true })
    return factor * ((leftValue ?? -Infinity) as number - ((rightValue ?? -Infinity) as number))
  })
}

export function CriticalNaturesReportPage() {
  const [period, setPeriod] = useState<GestorPeriod>(() => getCurrentGestorPeriod())
  const [granularity, setGranularity] = useState<GestorGranularity>('monthly')
  const [selectedDate, setSelectedDate] = useState(() => new Date(period.ano, period.mes - 1, 1))
  const [natureSearch, setNatureSearch] = useState('')
  const [criticality, setCriticality] = useState<Criticality>('all')
  const [sort, setSort] = useState<Sort>({ field: 'saldoPrevisto', direction: 'ascending' })
  const { environment, environments, setEnvironment } = useGestorEnvironment()
  const interval = useMemo(() => getGestorDateInterval(granularity, period, selectedDate), [granularity, period, selectedDate])
  const { data, error, isLoading, reload } = useGestor(period, DEFAULT_GESTOR_BRANCH, environment, interval)
  const navigation = getGestorPeriodNavigation(period, environment)

  const classified = useMemo(() => filterGestorRows(data?.linhas ?? [], natureSearch).map(classifyCriticalNature).filter((item): item is NonNullable<typeof item> => item !== null), [data?.linhas, natureSearch])
  const filteredRows = useMemo(() => classified.filter((item) => criticality === 'all' || item.types.includes(criticality)).map((item) => item.line), [classified, criticality])
  const rows = useMemo(() => sortLines(filteredRows, sort), [filteredRows, sort])
  const count = (type: Criticality) => classified.filter((item) => (criticality === 'all' || item.types.includes(criticality)) && (type === 'all' || item.types.includes(type))).length
  const changePeriod = (next: GestorPeriod) => { setPeriod(next); setSelectedDate(new Date(next.ano, next.mes - 1, 1)) }
  const navigationMove = (direction: -1 | 1) => { if (isMonthlyGranularity(granularity)) { const next = direction === -1 ? navigation.previous : navigation.next; if (next) changePeriod(next) } else { const next = navigateGestorGranularity(granularity, period, interval?.selectedDate ?? selectedDate, direction); if (next) setSelectedDate(next) } }
  const canMove = (direction: -1 | 1) => isMonthlyGranularity(granularity) ? (direction === -1 ? navigation.previous : navigation.next) !== null : navigateGestorGranularity(granularity, period, interval?.selectedDate ?? selectedDate, direction) !== null
  const changeEnvironment = (next: GestorDataEnvironment) => { const confirmed = next !== 'prd' || window.confirm('Consultar dados de PRODU\u00c7\u00c3O?\n\nA consulta ser\u00e1 somente leitura.'); if (!confirmed) return; setEnvironment(resolveGestorEnvironmentSelection(environment, next, confirmed)); setPeriod((current) => resolvePeriodForEnvironment(current, next)) }
  const toggleSort = (field: SortField) => setSort((current) => current.field === field ? { field, direction: current.direction === 'ascending' ? 'descending' : 'ascending' } : { field, direction: 'ascending' })
  const disabled = isLoading || !!error || rows.length === 0
  const filename = (extension: 'csv' | 'xlsx') => 'naturezas-criticas-' + environment + '-' + period.ano + '-' + String(period.mes).padStart(2, '0') + '.' + extension

  return <div className="reports-page">
    <header className="gestor-header"><p className="eyebrow">Relat&oacute;rios / Naturezas Cr&iacute;ticas</p><h2>Naturezas Cr&iacute;ticas</h2><p>Naturezas com consumo cr&iacute;tico, saldo previsto negativo ou movimenta&ccedil;&atilde;o sem limite.</p></header>
    <div className="report-toolbar"><EnvironmentSelector environment={environment} environments={environments} onChange={changeEnvironment} /><PeriodSelector period={period} onPrevious={() => navigationMove(-1)} onNext={() => navigationMove(1)} canPrevious={canMove(-1)} canNext={canMove(1)} environment={environment} onPeriodChange={changePeriod} contextLabel={interval?.label} /><GranularitySelector value={granularity} onChange={(next) => { setGranularity(next); setSelectedDate(new Date(period.ano, period.mes - 1, 1)) }} /></div>
    <div className="report-filters"><NatureFilter value={natureSearch} onChange={setNatureSearch} onClear={() => setNatureSearch('')} /><label className="nature-filter"><span className="control-label">Tipo de criticidade</span><select value={criticality} onChange={(event) => setCriticality(event.target.value as Criticality)}><option value="all">Todas</option><option value="consumo">Consumo cr&iacute;tico</option><option value="saldo">Saldo previsto negativo</option><option value="sem-limite">Sem limite</option></select></label></div>
    <div className="report-summary" aria-label="Resumo de Naturezas Cr&iacute;ticas"><article><span>Naturezas Cr&iacute;ticas</span><strong>{rows.length}</strong></article><article><span>Consumo Cr&iacute;tico</span><strong>{count('consumo')}</strong></article><article><span>Saldo Negativo</span><strong>{count('saldo')}</strong></article><article><span>Sem Limite</span><strong>{count('sem-limite')}</strong></article></div>
    <section className="report-table-section"><div className="table-heading"><div><p className="control-label">Detalhamento</p><h3>Naturezas que exigem aten&ccedil;&atilde;o</h3></div><p>{isLoading ? 'Consultando per&iacute;odo' : error ? 'Dados indispon&iacute;veis' : rows.length + ' linhas'}</p><div className="table-export-actions"><button type="button" disabled={disabled} onClick={() => exportCriticalNaturesCsv(rows, filename('csv'))}>Exportar CSV</button><button type="button" disabled={disabled} onClick={() => exportCriticalNaturesXlsx(rows, filename('xlsx'))}>Exportar Excel</button></div></div><div className="table-scroll report-table-scroll" tabIndex={0}><table className="gestor-table report-table"><thead><tr>{columns.map((column) => <th className={column.monetary ? 'monetary-column' : undefined} key={column.label}><button className="table-sort-trigger" type="button" onClick={() => toggleSort(column.field)}>{column.label}{sort.field === column.field ? (sort.direction === 'ascending' ? ' \u2191' : ' \u2193') : ''}</button></th>)}</tr></thead><tbody>{isLoading ? <tr><td className="empty-table" colSpan={columns.length}>Carregando Naturezas Cr&iacute;ticas...</td></tr> : error ? <tr><td className="empty-table" colSpan={columns.length}>N&atilde;o foi poss&iacute;vel carregar o relat&oacute;rio. <button className="table-retry" type="button" onClick={reload}>Tentar novamente</button></td></tr> : rows.length === 0 ? <tr><td className="empty-table" colSpan={columns.length}>Nenhuma Natureza Cr&iacute;tica encontrada para os filtros selecionados.</td></tr> : rows.map((row) => <tr key={row.naturezaCodigo}><th className="nature-cell" scope="row"><span className="nature-code">{row.naturezaCodigo}</span></th><td>{row.naturezaDescricao}</td><td>{row.situacao}</td><td className="money-cell">{formatCurrency(row.limiteOriginal)}</td><td className="money-cell">{formatCurrency(row.pcAberto)}</td><td className="money-cell">{formatCurrency(row.nfEntrada)}</td><td className="money-cell">{formatCurrency(row.gastoPrevisto)}</td><td className={'money-cell' + (row.saldoPrevisto < 0 ? ' money-negative' : '')}>{formatCurrency(row.saldoPrevisto)}</td><td className={'money-cell' + (row.saldoReal < 0 ? ' money-negative' : '')}>{formatCurrency(row.saldoReal)}</td><td>{row.percentualConsumido === null ? 'Sem limite' : row.percentualConsumido.toFixed(2).replace('.', ',') + '%'}</td></tr>)}</tbody></table></div></section>
    <Link className="report-back-link" to="/relatorios">&larr; Voltar para Relat&oacute;rios</Link>
  </div>
}
