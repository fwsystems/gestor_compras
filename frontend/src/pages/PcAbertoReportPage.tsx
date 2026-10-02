import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { EnvironmentSelector } from '../components/gestor/EnvironmentSelector'
import { GranularitySelector } from '../components/gestor/GranularitySelector'
import { NatureFilter } from '../components/gestor/NatureFilter'
import { PeriodSelector } from '../components/gestor/PeriodSelector'
import { DEFAULT_GESTOR_BRANCH } from '../config/gestor'
import { useGestorEnvironment } from '../context/GestorEnvironmentContext'
import { useGestor } from '../hooks/useGestor'
import { getGestorDetails } from '../services/gestorService'
import type { GestorDataEnvironment, GestorPeriod, GestorPcAbertoDetailRecord, GestorRow } from '../types/gestor'
import { formatCurrency } from '../utils/currency'
import { filterGestorRows } from '../utils/natureFilter'
import { getGestorDateInterval, isMonthlyGranularity, navigateGestorGranularity, type GestorGranularity } from '../utils/granularity'
import { resolveGestorEnvironmentSelection } from '../utils/environment'
import { getCurrentGestorPeriod, getGestorPeriodNavigation, resolvePeriodForEnvironment } from '../utils/period'
import { exportPcAbertoCsv, exportPcAbertoXlsx, type PcAbertoReportLine } from '../utils/pcAbertoReportExport'

type SortField = keyof Pick<PcAbertoReportLine, 'naturezaCodigo' | 'naturezaDescricao' | 'pedido' | 'fornecedor' | 'vencimento' | 'valor'>
type Sort = { field: SortField; direction: 'ascending' | 'descending' }
type LoadedLine = PcAbertoReportLine

const columns: { label: string; field: SortField; monetary?: boolean }[] = [
  { label: 'Natureza', field: 'naturezaCodigo' },
  { label: 'Descri\u00e7\u00e3o da Natureza', field: 'naturezaDescricao' },
  { label: 'Pedido', field: 'pedido' },
  { label: 'Fornecedor', field: 'fornecedor' },
  { label: 'Nome do Fornecedor', field: 'fornecedor' },
  { label: 'Vencimento', field: 'vencimento' },
  { label: 'Valor em Aberto', field: 'valor', monetary: true },
]

function formatDate(value: string): string {
  return /^\d{8}$/.test(value) ? `${value.slice(6, 8)}/${value.slice(4, 6)}/${value.slice(0, 4)}` : value
}

function loadLine(row: GestorRow, record: GestorPcAbertoDetailRecord): LoadedLine {
  if (!Number.isFinite(record.valor)) throw new Error(`Valor inválido no PC ${record.pedido}.`)
  return { naturezaCodigo: row.naturezaCodigo, naturezaDescricao: row.naturezaDescricao, pedido: record.pedido, fornecedor: record.fornecedor, fornecedorNome: record.fornecedorNome, vencimento: record.vencimento, valor: record.valor }
}

function sortLines(rows: readonly LoadedLine[], sort: Sort | null): LoadedLine[] {
  if (!sort) return [...rows]
  const factor = sort.direction === 'ascending' ? 1 : -1
  return [...rows].sort((left, right) => typeof left[sort.field] === 'string' && typeof right[sort.field] === 'string'
    ? factor * String(left[sort.field]).localeCompare(String(right[sort.field]), 'pt-BR', { numeric: true })
    : factor * (Number(left[sort.field]) - Number(right[sort.field])))
}

export function PcAbertoReportPage() {
  const [period, setPeriod] = useState<GestorPeriod>(() => getCurrentGestorPeriod())
  const [granularity, setGranularity] = useState<GestorGranularity>('monthly')
  const [selectedDate, setSelectedDate] = useState(() => new Date(period.ano, period.mes - 1, 1))
  const [natureSearch, setNatureSearch] = useState('')
  const [supplierSearch, setSupplierSearch] = useState('')
  const [orderSearch, setOrderSearch] = useState('')
  const [sort, setSort] = useState<Sort | null>(null)
  const [detailLines, setDetailLines] = useState<LoadedLine[]>([])
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState<Error | null>(null)
  const { environment, environments, setEnvironment } = useGestorEnvironment()
  const interval = useMemo(() => getGestorDateInterval(granularity, period, selectedDate), [granularity, period, selectedDate])
  const { data, error, isLoading, reload } = useGestor(period, DEFAULT_GESTOR_BRANCH, environment, interval)
  const navigation = getGestorPeriodNavigation(period, environment)

  useEffect(() => {
    let active = true
    const rows = data?.linhas ?? []
    setDetailLines([])
    setDetailError(null)
    if (!data || rows.every((row) => row.pcAberto === 0)) return () => { active = false }
    setDetailLoading(true)
    Promise.all(rows.filter((row) => row.pcAberto !== 0).map(async (row) => {
      const response = await getGestorDetails(period, DEFAULT_GESTOR_BRANCH, environment, row.naturezaCodigo, 'pc_aberto', interval ? { inicio: interval.inicio, fim: interval.fim } : null)
      return response.registros.filter((record): record is GestorPcAbertoDetailRecord => 'pedido' in record).map((record) => loadLine(row, record))
    })).then((groups) => { if (active) setDetailLines(groups.flat()) }).catch((requestError: unknown) => { if (active) setDetailError(requestError instanceof Error ? requestError : new Error('Falha ao carregar PCs em aberto.')) }).finally(() => { if (active) setDetailLoading(false) })
    return () => { active = false }
  }, [data, environment, interval, period])

  const filteredRows = useMemo(() => {
    const codes = new Set(filterGestorRows(data?.linhas ?? [], natureSearch).map((row) => row.naturezaCodigo))
    const supplier = supplierSearch.trim().toLocaleLowerCase()
    const order = orderSearch.trim().toLocaleLowerCase()
    return detailLines.filter((line) => codes.has(line.naturezaCodigo) && (!supplier || `${line.fornecedor} ${line.fornecedorNome}`.toLocaleLowerCase().includes(supplier)) && (!order || line.pedido.toLocaleLowerCase().includes(order)))
  }, [data?.linhas, detailLines, natureSearch, orderSearch, supplierSearch])
  const rows = useMemo(() => sortLines(filteredRows, sort), [filteredRows, sort])
  const total = rows.reduce((sum, row) => sum + row.valor, 0)
  const orders = new Set(rows.map((row) => row.pedido)).size
  const navigationMove = (direction: -1 | 1) => {
    if (isMonthlyGranularity(granularity)) { const next = direction === -1 ? navigation.previous : navigation.next; if (next) { setPeriod(next); setSelectedDate(new Date(next.ano, next.mes - 1, 1)) } } else { const next = navigateGestorGranularity(granularity, period, interval?.selectedDate ?? selectedDate, direction); if (next) setSelectedDate(next) }
  }
  const canMove = (direction: -1 | 1) => isMonthlyGranularity(granularity) ? (direction === -1 ? navigation.previous : navigation.next) !== null : navigateGestorGranularity(granularity, period, interval?.selectedDate ?? selectedDate, direction) !== null
  const changeEnvironment = (next: GestorDataEnvironment) => { const confirmed = next !== 'prd' || window.confirm('Consultar dados de PRODUÇÃO?\n\nA consulta será somente leitura.'); if (!confirmed) return; setEnvironment(resolveGestorEnvironmentSelection(environment, next, confirmed)); setPeriod((current) => resolvePeriodForEnvironment(current, next)) }
  const toggleSort = (field: SortField) => setSort((current) => current?.field === field ? { field, direction: current.direction === 'ascending' ? 'descending' : 'ascending' } : { field, direction: 'ascending' })
  const disabled = isLoading || detailLoading || !!error || !!detailError || rows.length === 0
  const filename = (extension: 'csv' | 'xlsx') => `pc-em-aberto-${environment}-${period.ano}-${String(period.mes).padStart(2, '0')}.${extension}`

  return <div className="reports-page">
    <header className="gestor-header"><p className="eyebrow">Relat&oacute;rios / PC em Aberto</p><h2>PC em Aberto</h2><p>Pedidos de compra em aberto por Natureza, fornecedor e pedido.</p></header>
    <div className="report-toolbar"><EnvironmentSelector environment={environment} environments={environments} onChange={changeEnvironment} /><PeriodSelector period={period} onPrevious={() => navigationMove(-1)} onNext={() => navigationMove(1)} canPrevious={canMove(-1)} canNext={canMove(1)} environment={environment} onPeriodChange={(next) => { setPeriod(next); setSelectedDate(new Date(next.ano, next.mes - 1, 1)) }} contextLabel={interval?.label} /><GranularitySelector value={granularity} onChange={(next) => { setGranularity(next); setSelectedDate(new Date(period.ano, period.mes - 1, 1)) }} /></div>
    <div className="report-filters"><NatureFilter value={natureSearch} onChange={setNatureSearch} onClear={() => setNatureSearch('')} /><label className="nature-filter"><span className="control-label">Fornecedor</span><input type="search" value={supplierSearch} onChange={(event) => setSupplierSearch(event.target.value)} placeholder="Código ou nome" /></label><label className="nature-filter"><span className="control-label">Pedido</span><input type="search" value={orderSearch} onChange={(event) => setOrderSearch(event.target.value)} placeholder="Número do pedido" /></label></div>
    <div className="report-summary" aria-label="Resumo de PC em aberto"><article><span>PCs em Aberto</span><strong>{orders}</strong></article><article><span>Total em Aberto</span><strong>{formatCurrency(total)}</strong></article></div>
    <section className="report-table-section"><div className="table-heading"><div><p className="control-label">Detalhamento</p><h3>Pedidos de compra em aberto</h3></div><p>{isLoading || detailLoading ? 'Consultando período' : error || detailError ? 'Dados indisponíveis' : `${rows.length} linhas`}</p><div className="table-export-actions"><button type="button" disabled={disabled} onClick={() => exportPcAbertoCsv(rows, filename('csv'))}>Exportar CSV</button><button type="button" disabled={disabled} onClick={() => exportPcAbertoXlsx(rows, filename('xlsx'))}>Exportar Excel</button></div></div><div className="table-scroll report-table-scroll" tabIndex={0}><table className="gestor-table report-table"><thead><tr>{columns.map((column) => <th className={column.monetary ? 'monetary-column' : undefined} key={column.label}><button className="table-sort-trigger" type="button" onClick={() => toggleSort(column.field)}>{column.label}{sort?.field === column.field ? (sort.direction === 'ascending' ? ' ↑' : ' ↓') : ''}</button></th>)}</tr></thead><tbody>{isLoading || detailLoading ? <tr><td className="empty-table" colSpan={columns.length}>Carregando PCs em aberto...</td></tr> : error || detailError ? <tr><td className="empty-table" colSpan={columns.length}>Não foi possível carregar os PCs em aberto. <button className="table-retry" type="button" onClick={reload}>Tentar novamente</button></td></tr> : rows.length === 0 ? <tr><td className="empty-table" colSpan={columns.length}>Nenhum PC em aberto encontrado para os filtros selecionados.</td></tr> : rows.map((row) => <tr key={`${row.naturezaCodigo}-${row.pedido}-${row.vencimento}-${row.valor}`}><th className="nature-cell" scope="row"><span className="nature-code">{row.naturezaCodigo}</span></th><td>{row.naturezaDescricao}</td><td>{row.pedido}</td><td>{row.fornecedor}</td><td>{row.fornecedorNome || '—'}</td><td>{formatDate(row.vencimento)}</td><td className={`money-cell${row.valor < 0 ? ' money-negative' : ''}`}>{formatCurrency(row.valor)}</td></tr>)}</tbody></table></div></section>
    <p className="report-note">Campos de item, produto, descri&ccedil;&atilde;o do produto, emiss&atilde;o e quantidade n&atilde;o est&atilde;o dispon&iacute;veis no contrato homologado atual de PC em aberto.</p>
    <Link className="report-back-link" to="/relatorios">← Voltar para Relatórios</Link>
  </div>
}
