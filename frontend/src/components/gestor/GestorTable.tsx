import type { GestorDetailType, GestorRow } from '../../types/gestor'
import type { GestorSort, GestorSortField } from '../../utils/gestorSort'
import { isCriticalGestorRow } from '../../utils/budgetUsage'
import { formatCurrency } from '../../utils/currency'
import { BudgetUsageBar } from './BudgetUsageBar'

const columns = [
  { label: 'Natureza Financeira', field: 'natureza', monetary: false },
  { label: '(a) PC aberto', field: 'pcAberto', monetary: true },
  { label: '(b) NF entrada', field: 'nfEntrada', monetary: true },
  { label: '(c) Contingência OK', field: 'contingenciaOk', monetary: true },
  { label: '(d) Contingência em aprovação', field: 'contingenciaEmAprovacao', monetary: true },
  { label: '(e) Lim Original', field: 'limiteOriginal', monetary: true },
  { label: 'Lim Total', field: 'limiteTotal', monetary: true },
  { label: 'Saldo previsto', field: 'saldoPrevisto', monetary: true },
  { label: 'Saldo real', field: 'saldoReal', monetary: true },
] as const

interface GestorTableProps {
  rows: readonly GestorRow[]
  count: number
  isFiltered: boolean
  isLoading: boolean
  hasError: boolean
  onRetry: () => void
  onOpenDetail: (row: GestorRow, type: GestorDetailType) => void
  sort: GestorSort | null
  onSort: (field: GestorSortField) => void
  onExportCsv: () => void
  onExportXlsx: () => void
  exportDisabled: boolean
}

const monetaryFields = [
  'pcAberto',
  'nfEntrada',
  'contingenciaOk',
  'contingenciaEmAprovacao',
  'limiteOriginal',
  'limiteTotal',
  'saldoPrevisto',
  'saldoReal',
] as const satisfies readonly (keyof GestorRow)[]

const detailConfig: Partial<Record<
  (typeof monetaryFields)[number],
  { type: GestorDetailType; label: string }
>> = {
  pcAberto: { type: 'pc_aberto', label: 'PC aberto' },
  nfEntrada: { type: 'nf_entrada', label: 'NF entrada' },
  contingenciaOk: { type: 'contingencia_ok', label: 'Contingência OK' },
  contingenciaEmAprovacao: {
    type: 'contingencia_aprovacao',
    label: 'Contingência em aprovação',
  },
}

export function GestorTable({
  rows,
  count,
  isFiltered,
  isLoading,
  hasError,
  onRetry,
  onOpenDetail,
  sort,
  onSort,
  onExportCsv,
  onExportXlsx,
  exportDisabled,
}: GestorTableProps) {
  const natureCountLabel = isFiltered
    ? `${rows.length} de ${count} ${count === 1 ? 'natureza' : 'naturezas'}`
    : `${count} ${count === 1 ? 'natureza' : 'naturezas'}`

  return (
    <section className="gestor-table-section" aria-labelledby="table-title">
      <div className="table-heading">
        <div>
          <p className="control-label">Detalhamento</p>
          <h3 id="table-title">Orçamento por natureza financeira</h3>
        </div>
        <p aria-live="polite">
          {isLoading
            ? 'Consultando período'
            : hasError
              ? 'Quantidade indisponível'
              : natureCountLabel}
        </p>
        <div className="table-export-actions">
          <button type="button" onClick={onExportCsv} disabled={exportDisabled}>
            Exportar CSV
          </button>
          <button type="button" onClick={onExportXlsx} disabled={exportDisabled}>
            Exportar Excel
          </button>
        </div>
      </div>

      <div className="table-scroll" tabIndex={0} aria-label="Grade do Gestor de Compras">
        <table className="gestor-table" aria-busy={isLoading}>
          <thead>
            <tr>
              {columns.map((column) => (
                <th
                  className={column.monetary ? 'monetary-column' : undefined}
                  key={column.label}
                  scope="col"
                  aria-sort={sort?.field === column.field ? sort.direction : 'none'}
                >
                  <button
                    className="table-sort-trigger"
                    type="button"
                    onClick={() => onSort(column.field)}
                  >
                    {column.label}
                    {sort?.field === column.field && (
                      <span aria-hidden="true">{sort.direction === 'ascending' ? ' ↑' : ' ↓'}</span>
                    )}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td className="empty-table" colSpan={columns.length}>
                  <div role="status" aria-live="polite">
                    <strong>Carregando dados...</strong>
                    <span>Aguarde enquanto consultamos este período.</span>
                  </div>
                </td>
              </tr>
            ) : hasError ? (
              <tr>
                <td className="empty-table" colSpan={columns.length}>
                  <div role="alert">
                    <strong>Não foi possível carregar os dados deste período.</strong>
                    <span>Verifique se a API está disponível e tente novamente.</span>
                    <button className="table-retry" type="button" onClick={onRetry}>
                      Tentar novamente
                    </button>
                  </div>
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td className="empty-table" colSpan={columns.length}>
                  {isFiltered && count > 0 ? (
                    <>
                      <strong>Nenhuma natureza encontrada para o filtro informado.</strong>
                      <span>Altere ou limpe o filtro para visualizar os dados do período.</span>
                    </>
                  ) : (
                    <>
                      <strong>Nenhum dado carregado para este período.</strong>
                      <span>Os dados do Gestor serão exibidos aqui.</span>
                    </>
                  )}
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr
                  className={
                    isCriticalGestorRow(row) ? 'critical-row' : undefined
                  }
                  key={row.naturezaCodigo}
                >
                  <th className="nature-cell" scope="row">
                    <span className="nature-code">{row.naturezaCodigo}</span>
                    <span className="nature-description">
                      {row.naturezaDescricao}
                    </span>
                    <BudgetUsageBar
                      pcAberto={row.pcAberto}
                      nfEntrada={row.nfEntrada}
                      limiteTotal={row.limiteTotal}
                    />
                    {isCriticalGestorRow(row) && (
                      <span className="sr-only">
                        Situação crítica: saldo previsto ou limite total
                        negativo.
                      </span>
                    )}
                  </th>
                  {monetaryFields.map((field) => {
                    const detail = detailConfig[field]
                    return (
                      <td
                        className={`money-cell${row[field] < 0 ? ' money-negative' : ''}`}
                        key={field}
                      >
                      {detail && row[field] !== 0 ? (
                        <button
                          className="detail-trigger"
                          type="button"
                          onClick={() => onOpenDetail(row, detail.type)}
                          aria-label={`Detalhar ${detail.label} da natureza ${row.naturezaCodigo}, ${formatCurrency(row[field])}`}
                        >
                          {formatCurrency(row[field])}
                        </button>
                      ) : formatCurrency(row[field])}
                      </td>
                    )
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
