import * as XLSX from 'xlsx'

import type { GestorRow } from '../types/gestor'

export interface ConsumptionReportRow extends Pick<GestorRow, 'naturezaCodigo' | 'naturezaDescricao' | 'pcAberto' | 'nfEntrada' | 'contingenciaOk' | 'contingenciaEmAprovacao' | 'limiteOriginal' | 'saldoPrevisto' | 'saldoReal' | 'pago' | 'aPagar' | 'total'> {
  percentualConsumido: number | null
}

const headers = ['Natureza', 'Descri\u00e7\u00e3o da Natureza', 'Limite Original', 'PC em Aberto', 'NF Entrada', 'Pago', 'A Pagar', 'Total', 'Saldo Previsto', 'Saldo Real', '% Consumido']

function rowsForExport(rows: readonly ConsumptionReportRow[]): (string | number)[][] {
  return rows.map((row) => [row.naturezaCodigo, row.naturezaDescricao, row.limiteOriginal, row.pcAberto, row.nfEntrada, row.pago, row.aPagar, row.total, row.saldoPrevisto, row.saldoReal, row.percentualConsumido ?? 'Sem limite'])
}

function csvValue(value: string | number): string {
  if (typeof value === 'number') return value.toFixed(2).replace('.', ',')
  return /[;"\r\n]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value
}

export function createConsumptionReportCsv(rows: readonly ConsumptionReportRow[]): string {
  return `\uFEFF${[headers, ...rowsForExport(rows)].map((row) => row.map(csvValue).join(';')).join('\r\n')}`
}

function download(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export function exportConsumptionReportCsv(rows: readonly ConsumptionReportRow[], filename: string): void {
  download(new Blob([createConsumptionReportCsv(rows)], { type: 'text/csv;charset=utf-8' }), filename)
}

export function exportConsumptionReportXlsx(rows: readonly ConsumptionReportRow[], filename: string): void {
  const worksheet = XLSX.utils.aoa_to_sheet([headers, ...rowsForExport(rows)])
  for (let column = 2; column <= 9; column += 1) {
    for (let row = 1; row <= rows.length; row += 1) {
      const cell = worksheet[XLSX.utils.encode_cell({ r: row, c: column })]
      if (cell) cell.z = '#,##0.00'
    }
  }
  worksheet['!cols'] = [{ wch: 16 }, { wch: 34 }, ...headers.slice(2).map(() => ({ wch: 16 }))]
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Consumo por Natureza')
  XLSX.writeFile(workbook, filename)
}
