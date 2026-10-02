import * as XLSX from 'xlsx'

export interface PcAbertoReportLine {
  naturezaCodigo: string
  naturezaDescricao: string
  pedido: string
  fornecedor: string
  fornecedorNome: string
  vencimento: string
  valor: number
}

const headers = ['Natureza', 'Descri\u00e7\u00e3o da Natureza', 'Pedido', 'Fornecedor', 'Nome do Fornecedor', 'Vencimento', 'Valor em Aberto']

function rowsForExport(rows: readonly PcAbertoReportLine[]): (string | number)[][] {
  return rows.map((row) => [row.naturezaCodigo, row.naturezaDescricao, row.pedido, row.fornecedor, row.fornecedorNome, row.vencimento, row.valor])
}

function csvValue(value: string | number): string {
  if (typeof value === 'number') return value.toFixed(2).replace('.', ',')
  return /[;"\r\n]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value
}

export function createPcAbertoCsv(rows: readonly PcAbertoReportLine[]): string {
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

export function exportPcAbertoCsv(rows: readonly PcAbertoReportLine[], filename: string): void {
  download(new Blob([createPcAbertoCsv(rows)], { type: 'text/csv;charset=utf-8' }), filename)
}

export function exportPcAbertoXlsx(rows: readonly PcAbertoReportLine[], filename: string): void {
  const worksheet = XLSX.utils.aoa_to_sheet([headers, ...rowsForExport(rows)])
  for (let row = 1; row <= rows.length; row += 1) {
    const cell = worksheet[XLSX.utils.encode_cell({ r: row, c: 6 })]
    if (cell) cell.z = '#,##0.00'
  }
  worksheet['!cols'] = [{ wch: 16 }, { wch: 32 }, { wch: 16 }, { wch: 16 }, { wch: 32 }, { wch: 16 }, { wch: 18 }]
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, 'PC em Aberto')
  XLSX.writeFile(workbook, filename)
}
