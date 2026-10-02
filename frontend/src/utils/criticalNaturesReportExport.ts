import * as XLSX from 'xlsx'

export interface CriticalNaturesReportLine {
  naturezaCodigo: string
  naturezaDescricao: string
  situacao: string
  limiteOriginal: number
  pcAberto: number
  nfEntrada: number
  gastoPrevisto: number
  saldoPrevisto: number
  saldoReal: number
  percentualConsumido: number | null
}

const headers = ['Natureza', 'Descri\u00e7\u00e3o da Natureza', 'Situa\u00e7\u00e3o', 'Limite Original', 'PC em Aberto', 'NF Entrada', 'Gasto Previsto', 'Saldo Previsto', 'Saldo Real', '% Consumido']

function rowsForExport(rows: readonly CriticalNaturesReportLine[]): (string | number | null)[][] {
  return rows.map((row) => [row.naturezaCodigo, row.naturezaDescricao, row.situacao, row.limiteOriginal, row.pcAberto, row.nfEntrada, row.gastoPrevisto, row.saldoPrevisto, row.saldoReal, row.percentualConsumido])
}

function csvValue(value: string | number | null): string {
  if (value === null) return ''
  if (typeof value === 'number') return value.toFixed(2).replace('.', ',')
  return /[;"\r\n]/.test(value) ? '"' + value.replaceAll('"', '""') + '"' : value
}

export function createCriticalNaturesCsv(rows: readonly CriticalNaturesReportLine[]): string {
  return '\uFEFF' + [headers, ...rowsForExport(rows)].map((row) => row.map(csvValue).join(';')).join('\r\n')
}

function download(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export function exportCriticalNaturesCsv(rows: readonly CriticalNaturesReportLine[], filename: string): void {
  download(new Blob([createCriticalNaturesCsv(rows)], { type: 'text/csv;charset=utf-8' }), filename)
}

export function exportCriticalNaturesXlsx(rows: readonly CriticalNaturesReportLine[], filename: string): void {
  const worksheet = XLSX.utils.aoa_to_sheet([headers, ...rowsForExport(rows)])
  for (let row = 1; row <= rows.length; row += 1) {
    for (const column of [3, 4, 5, 6, 7, 8]) {
      const cell = worksheet[XLSX.utils.encode_cell({ r: row, c: column })]
      if (cell) cell.z = '#,##0.00'
    }
    const percentage = worksheet[XLSX.utils.encode_cell({ r: row, c: 9 })]
    if (percentage && percentage.v !== null) percentage.z = '0.00'
  }
  worksheet['!cols'] = [{ wch: 16 }, { wch: 32 }, { wch: 44 }, { wch: 18 }, { wch: 18 }, { wch: 16 }, { wch: 18 }, { wch: 18 }, { wch: 18 }, { wch: 16 }]
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Naturezas Críticas')
  XLSX.writeFile(workbook, filename)
}
