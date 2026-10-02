import * as XLSX from 'xlsx'

export interface NfEntradaReportLine {
  naturezaCodigo: string
  naturezaDescricao: string
  documento: string
  parcela: string
  fornecedor: string
  fornecedorNome: string
  emissao: string
  vencimento: string
  valor: number
}

const headers = ['Natureza', 'Descri\u00e7\u00e3o da Natureza', 'Documento', 'Parcela', 'Fornecedor', 'Nome do Fornecedor', 'Emiss\u00e3o', 'Vencimento', 'Valor']

function rowsForExport(rows: readonly NfEntradaReportLine[]): (string | number)[][] {
  return rows.map((row) => [row.naturezaCodigo, row.naturezaDescricao, row.documento, row.parcela, row.fornecedor, row.fornecedorNome, row.emissao, row.vencimento, row.valor])
}

function csvValue(value: string | number): string {
  if (typeof value === 'number') return value.toFixed(2).replace('.', ',')
  return /[;"\r\n]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value
}

export function createNfEntradaCsv(rows: readonly NfEntradaReportLine[]): string {
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

export function exportNfEntradaCsv(rows: readonly NfEntradaReportLine[], filename: string): void {
  download(new Blob([createNfEntradaCsv(rows)], { type: 'text/csv;charset=utf-8' }), filename)
}

export function exportNfEntradaXlsx(rows: readonly NfEntradaReportLine[], filename: string): void {
  const worksheet = XLSX.utils.aoa_to_sheet([headers, ...rowsForExport(rows)])
  for (let row = 1; row <= rows.length; row += 1) {
    const cell = worksheet[XLSX.utils.encode_cell({ r: row, c: 8 })]
    if (cell) cell.z = '#,##0.00'
  }
  worksheet['!cols'] = [{ wch: 16 }, { wch: 32 }, { wch: 18 }, { wch: 12 }, { wch: 16 }, { wch: 32 }, { wch: 16 }, { wch: 16 }, { wch: 18 }]
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, 'NF Entrada')
  XLSX.writeFile(workbook, filename)
}
