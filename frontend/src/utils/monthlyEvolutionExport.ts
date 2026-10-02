import * as XLSX from 'xlsx'

export interface MonthlyEvolutionExportRow {
  mes: string
  limiteOriginal: number
  pcAberto: number
  nfEntrada: number
  gastoPrevisto: number
  saldoPrevisto: number
  saldoReal: number
  percentualConsumido: number | null
}

const headers = ['M\u00eas', 'Limite Original', 'PC em Aberto', 'NF Entrada', 'Gasto Previsto', 'Saldo Previsto', 'Saldo Real', '% Consumido']

function rowsForExport(rows: readonly MonthlyEvolutionExportRow[]): (string | number | null)[][] {
  return rows.map((row) => [row.mes, row.limiteOriginal, row.pcAberto, row.nfEntrada, row.gastoPrevisto, row.saldoPrevisto, row.saldoReal, row.percentualConsumido])
}

function csvValue(value: string | number | null): string {
  if (value === null) return ''
  if (typeof value === 'number') return value.toFixed(2).replace('.', ',')
  return /[;"\r\n]/.test(value) ? '"' + value.replaceAll('"', '""') + '"' : value
}

export function createMonthlyEvolutionCsv(rows: readonly MonthlyEvolutionExportRow[]): string {
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

export function exportMonthlyEvolutionCsv(rows: readonly MonthlyEvolutionExportRow[], filename: string): void {
  download(new Blob([createMonthlyEvolutionCsv(rows)], { type: 'text/csv;charset=utf-8' }), filename)
}

export function exportMonthlyEvolutionXlsx(rows: readonly MonthlyEvolutionExportRow[], filename: string): void {
  const worksheet = XLSX.utils.aoa_to_sheet([headers, ...rowsForExport(rows)])
  for (let row = 1; row <= rows.length; row += 1) {
    for (const column of [1, 2, 3, 4, 5, 6]) {
      const cell = worksheet[XLSX.utils.encode_cell({ r: row, c: column })]
      if (cell) cell.z = '#,##0.00'
    }
    const percentage = worksheet[XLSX.utils.encode_cell({ r: row, c: 7 })]
    if (percentage && percentage.v !== null) percentage.z = '0.00'
  }
  worksheet['!cols'] = [{ wch: 18 }, { wch: 18 }, { wch: 18 }, { wch: 16 }, { wch: 18 }, { wch: 18 }, { wch: 18 }, { wch: 16 }]
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Evolu\u00e7\u00e3o Mensal')
  XLSX.writeFile(workbook, filename)
}
