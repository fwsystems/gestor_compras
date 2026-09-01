import * as XLSX from 'xlsx'

import type { GestorDataEnvironment, GestorPeriod, GestorRow } from '../types/gestor'
import type { GestorGranularity } from './granularity'

const headers = ['Natureza Financeira', '(a) PC aberto', '(b) NF entrada', '(c) Contingência OK', '(d) Contingência em aprovação', '(e) Lim Original', 'Lim Total', 'Saldo previsto', 'Saldo real']

function formatCsvNumber(value: number): string {
  return value.toFixed(2).replace('.', ',')
}

function escapeCsv(value: string): string {
  return /[;"\r\n]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value
}

export function gestorExportRows(rows: readonly GestorRow[]): (string | number)[][] {
  return rows.map((row) => [
    `${row.naturezaCodigo} - ${row.naturezaDescricao}`,
    row.pcAberto, row.nfEntrada, row.contingenciaOk, row.contingenciaEmAprovacao,
    row.limiteOriginal, row.limiteTotal, row.saldoPrevisto, row.saldoReal,
  ])
}

export function createGestorCsv(rows: readonly GestorRow[]): string {
  const lines = [headers, ...gestorExportRows(rows)].map((row) =>
    row.map((value, index) => index === 0 ? escapeCsv(String(value)) : formatCsvNumber(Number(value))).join(';'),
  )
  return `\uFEFF${lines.join('\r\n')}`
}

export function gestorExportFilename(environment: GestorDataEnvironment, granularity: GestorGranularity, period: GestorPeriod, interval: { inicio: string; fim: string } | null, extension: 'csv' | 'xlsx'): string {
  const month = `${period.ano}-${String(period.mes).padStart(2, '0')}`
  const range = granularity === 'monthly' ? month : granularity === 'daily' ? interval?.inicio ?? month : `${interval?.inicio ?? month}_a_${interval?.fim ?? month}`
  return `gestor-compras-${environment}-${range}.${extension}`
}

function download(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export function exportGestorCsv(rows: readonly GestorRow[], filename: string): void {
  download(new Blob([createGestorCsv(rows)], { type: 'text/csv;charset=utf-8' }), filename)
}

export function exportGestorXlsx(rows: readonly GestorRow[], filename: string): void {
  const worksheet = XLSX.utils.aoa_to_sheet([headers, ...gestorExportRows(rows)])
  for (let column = 1; column < headers.length; column += 1) {
    for (let row = 1; row <= rows.length; row += 1) {
      const cell = worksheet[XLSX.utils.encode_cell({ r: row, c: column })]
      if (cell) cell.z = '#,##0.00'
    }
  }
  worksheet['!cols'] = [{ wch: 42 }, ...headers.slice(1).map(() => ({ wch: 16 }))]
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Gestor de Compras')
  XLSX.writeFile(workbook, filename)
}
