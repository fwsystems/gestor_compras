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
import type { GestorDataEnvironment, GestorNfEntradaDetailRecord, GestorPeriod, GestorRow } from '../types/gestor'
import { formatCurrency } from '../utils/currency'
import { filterGestorRows } from '../utils/natureFilter'
import { getGestorDateInterval, isMonthlyGranularity, navigateGestorGranularity, type GestorGranularity } from '../utils/granularity'
import { resolveGestorEnvironmentSelection } from '../utils/environment'
import { getCurrentGestorPeriod, getGestorPeriodNavigation, resolvePeriodForEnvironment } from '../utils/period'
import { exportNfEntradaCsv, exportNfEntradaXlsx, type NfEntradaReportLine } from '../utils/nfEntradaReportExport'

type SortField = keyof Pick<NfEntradaReportLine, 'naturezaCodigo' | 'naturezaDescricao' | 'documento' | 'parcela' | 'fornecedor' | 'fornecedorNome' | 'emissao' | 'vencimento' | 'valor'>
type Sort = { field: SortField; direction: 'ascending' | 'descending' }

const columns: { label: string; field: SortField; monetary?: boolean }[] = [
  { label: 'Natureza', field: 'naturezaCodigo' },
  { label: 'Descri\u00e7\u00e3o da Natureza', field: 'naturezaDescricao' },
  { label: 'Documento', field: 'documento' },
  { label: 'Parcela', field: 'parcela' },
  { label: 'Fornecedor', field: 'fornecedor' },
  { label: 'Nome do Fornecedor', field: 'fornecedorNome' },
  { label: 'Emiss\u00e3o', field: 'emissao' },
  { label: 'Vencimento', field: 'vencimento' },
  { label: 'Valor', field: 'valor', monetary: true },
]

function formatDate(value: string): string {
  return /^\d{8}$/.test(value) ? value.slice(6, 8) + '/' + value.slice(4, 6) + '/' + value.slice(0, 4) : value
}

function loadLine(row: GestorRow, record: GestorNfEntradaDetailRecord): NfEntradaReportLine {
  if (!Number.isFinite(record.valor)) throw new Error('Valor inv\u00e1lido na NF ' + record.documento + '.')
  return { naturezaCodigo: row.naturezaCodigo, naturezaDescricao: row.naturezaDescricao, documento: record.documento, parcela: record.parcela, fornecedor: record.fornecedor, fornecedorNome: record.fornecedorNome, emissao: record.emissao, vencimento: record.vencimento, valor: record.valor }
}

function sortLines(rows: readonly NfEntradaReportLine[], sort: Sort | null): NfEntradaReportLine[] {
  if (!sort) return [...rows]
  const factor = sort.direction === 'ascending' ? 1 : -1
  return [...rows].sort((left, right) => typeof left[sort.field] === 'string' && typeof right[sort.field] === 'string'
    ? factor * String(left[sort.field]).localeCompare(String(right[sort.field]), 'pt-BR', { numeric: true })
    : factor * (Number(left[sort.field]) - Number(right[sort.field])))
}

export function NfEntradaReportPage() {
  const [period, setPeriod] = useState<GestorPeriod>(() => getCurrentGestorPeriod())
  const [granularity, setGranularity] = useState<GestorGranularity>('monthly')
  const [selectedDate, setSelectedDate] = useState(() => new Date(period.ano, period.mes - 1, 1))
  const [natureSearch, setNatureSearch] = useState('')
  const [supplierSearch, setSupplierSearch] = useState('')
  const [documentSearch, setDocumentSearch] = useState('')
  const [sort, setSort] = useState<Sort | null>(null)
  const [detailLines, setDetailLines] = useState<NfEntradaReportLine[]>([])
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
    if (!data || rows.every((row) => row.nfEntrada === 0)) return () => { active = false }
    setDetailLoading(true)
    Promise.all(rows.filter((row) => row.nfEntrada !== 0).map(async (row) => {
      const response = await getGestorDetails(period, DEFAULT_GESTOR_BRANCH, environment, row.naturezaCodigo, 'nf_entrada', interval ? { inicio: interval.inicio, fim: interval.fim } : null)
      return response.registros.filter((record): record is GestorNfEntradaDetailRecord => 'documento' in record).map((record) => loadLine(row, record))
    })).then((groups) => { if (active) setDetailLines(groups.flat()) }).catch((requestError: unknown) => { if (active) setDetailError(requestError instanceof Error ? requestError : new Error('Falha ao carregar NFs de entrada.')) }).finally(() => { if (active) setDetailLoading(false) })
    return () => { active = false }
  }, [data, environment, interval, period])

  const filteredRows = useMemo(() => {
    const codes = new Set(filterGestorRows(data?.linhas ?? [], natureSearch).map((row) => row.naturezaCodigo))
    const supplier = supplierSearch.trim().toLocaleLowerCase()
    const document = documentSearch.trim().toLocaleLowerCase()
    return detailLines.filter((line) => codes.has(line.naturezaCodigo) && (!supplier || (line.fornecedor + ' ' + line.fornecedorNome).toLocaleLowerCase().includes(supplier)) && (!document || (line.documento + ' ' + line.parcela).toLocaleLowerCase().includes(document)))
  }, [data?.linhas, detailLines, documentSearch, natureSearch, supplierSearch])
  const rows = useMemo(() => sortLines(filteredRows, sort), [filteredRows, sort])
  const total = rows.reduce((sum, row) => sum + row.valor, 0)
  const navigationMove = (direction: -1 | 1) => { if (isMonthlyGranularity(granularity)) { const next = direction === -1 ? navigation.previous : navigation.next; if (next) { setPeriod(next); setSelectedDate(new Date(next.ano, next.mes - 1, 1)) } } else { const next = navigateGestorGranularity(granularity, period, interval?.selectedDate ?? selectedDate, direction); if (next) setSelectedDate(next) } }
  const canMove = (direction: -1 | 1) => isMonthlyGranularity(granularity) ? (direction === -1 ? navigation.previous : navigation.next) !== null : navigateGestorGranularity(granularity, period, interval?.selectedDate ?? selectedDate, direction) !== null
  const changeEnvironment = (next: GestorDataEnvironment) => { const confirmed = next !== 'prd' || window.confirm('Consultar dados de PRODU\u00c7\u00c3O?\n\nA consulta ser\u00e1 somente leitura.'); if (!confirmed) return; setEnvironment(resolveGestorEnvironmentSelection(environment, next, confirmed)); setPeriod((current) => resolvePeriodForEnvironment(current, next)) }
  const toggleSort = (field: SortField) => setSort((current) => current?.field === field ? { field, direction: current.direction === 'ascending' ? 'descending' : 'ascending' } : { field, direction: 'ascending' })
  const disabled = isLoading || detailLoading || !!error || !!detailError || rows.length === 0
  const filename = (extension: 'csv' | 'xlsx') => 'nf-entrada-' + environment + '-' + period.ano + '-' + String(period.mes).padStart(2, '0') + '.' + extension

  return <div className="reports-page">
    <header className="gestor-header"><p className="eyebrow">Relat&oacute;rios / NF Entrada</p><h2>NF Entrada</h2><p>Notas fiscais de entrada por Natureza, fornecedor e documento.</p></header>
    <div className="report-toolbar"><EnvironmentSelector environment={environment} environments={environments} onChange={changeEnvironment} /><PeriodSelector period={period} onPrevious={() => navigationMove(-1)} onNext={() => navigationMove(1)} canPrevious={canMove(-1)} canNext={canMove(1)} environment={environment} onPeriodChange={(next) => { setPeriod(next); setSelectedDate(new Date(next.ano, next.mes - 1, 1)) }} contextLabel={interval?.label} /><GranularitySelector value={granularity} onChange={(next) => { setGranularity(next); setSelectedDate(new Date(period.ano, period.mes - 1, 1)) }} /></div>
    <div className="report-filters"><NatureFilter value={natureSearch} onChange={setNatureSearch} onClear={() => setNatureSearch('')} /><label className="nature-filter"><span className="control-label">Fornecedor</span><input type="search" value={supplierSearch} onChange={(event) => setSupplierSearch(event.target.value)} placeholder="C&oacute;digo ou nome" /></label><label className="nature-filter"><span className="control-label">Documento</span><input type="search" value={documentSearch} onChange={(event) => setDocumentSearch(event.target.value)} placeholder="N&uacute;mero ou parcela" /></label></div>
    <div className="report-summary" aria-label="Resumo de NF Entrada"><article><span>NFs / T&iacute;tulos</span><strong>{rows.length}</strong></article><article><span>Total NF Entrada</span><strong>{formatCurrency(total)}</strong></article></div>
    <section className="report-table-section"><div className="table-heading"><div><p className="control-label">Detalhamento</p><h3>Notas fiscais de entrada</h3></div><p>{isLoading || detailLoading ? 'Consultando per&iacute;odo' : error || detailError ? 'Dados indispon&iacute;veis' : rows.length + ' linhas'}</p><div className="table-export-actions"><button type="button" disabled={disabled} onClick={() => exportNfEntradaCsv(rows, filename('csv'))}>Exportar CSV</button><button type="button" disabled={disabled} onClick={() => exportNfEntradaXlsx(rows, filename('xlsx'))}>Exportar Excel</button></div></div><div className="table-scroll report-table-scroll" tabIndex={0}><table className="gestor-table report-table"><thead><tr>{columns.map((column) => <th className={column.monetary ? 'monetary-column' : undefined} key={column.label}><button className="table-sort-trigger" type="button" onClick={() => toggleSort(column.field)}>{column.label}{sort?.field === column.field ? (sort.direction === 'ascending' ? ' \u2191' : ' \u2193') : ''}</button></th>)}</tr></thead><tbody>{isLoading || detailLoading ? <tr><td className="empty-table" colSpan={columns.length}>Carregando NFs de entrada...</td></tr> : error || detailError ? <tr><td className="empty-table" colSpan={columns.length}>N&atilde;o foi poss&iacute;vel carregar as NFs de entrada. <button className="table-retry" type="button" onClick={reload}>Tentar novamente</button></td></tr> : rows.length === 0 ? <tr><td className="empty-table" colSpan={columns.length}>Nenhuma NF de entrada encontrada para os filtros selecionados.</td></tr> : rows.map((row) => <tr key={row.naturezaCodigo + '-' + row.documento + '-' + row.parcela + '-' + row.fornecedor + '-' + row.valor}><th className="nature-cell" scope="row"><span className="nature-code">{row.naturezaCodigo}</span></th><td>{row.naturezaDescricao}</td><td>{row.documento}</td><td>{row.parcela}</td><td>{row.fornecedor}</td><td>{row.fornecedorNome || '\u2014'}</td><td>{formatDate(row.emissao)}</td><td>{formatDate(row.vencimento)}</td><td className={'money-cell' + (row.valor < 0 ? ' money-negative' : '')}>{formatCurrency(row.valor)}</td></tr>)}</tbody></table></div></section>
    <Link className="report-back-link" to="/relatorios">&larr; Voltar para Relat&oacute;rios</Link>
  </div>
}
