import { useEffect, useRef } from 'react'

import type {
  GestorDataEnvironment,
  GestorContingenciaDetailRecord,
  GestorDetailResponse,
  GestorDetailSelection,
  GestorNfEntradaDetailRecord,
  GestorPeriod,
} from '../../types/gestor'
import { formatCurrency } from '../../utils/currency'

interface GestorDetailDrawerProps {
  selection: GestorDetailSelection
  period: GestorPeriod
  environment: GestorDataEnvironment
  data: GestorDetailResponse | null
  isLoading: boolean
  error: Error | null
  onClose: () => void
  onRetry: () => void
}

function formatProtheusDate(value: string) {
  if (/^\d{8}$/.test(value)) {
    return `${value.slice(6, 8)}/${value.slice(4, 6)}/${value.slice(0, 4)}`
  }
  return value || '—'
}

function isNfRecord(
  record: GestorDetailResponse['registros'][number],
): record is GestorNfEntradaDetailRecord {
  return 'documento' in record
}

function isContingenciaRecord(
  record: GestorDetailResponse['registros'][number],
): record is GestorContingenciaDetailRecord {
  return 'item' in record
}

export function GestorDetailDrawer({
  selection,
  period,
  environment,
  data,
  isLoading,
  error,
  onClose,
  onRetry,
}: GestorDetailDrawerProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    closeButtonRef.current?.focus()
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = previousOverflow
      previousFocus?.focus()
    }
  }, [onClose])

  const title = {
    pc_aberto: 'PC aberto',
    nf_entrada: 'NF entrada',
    contingencia_ok: 'Contingência OK',
    contingencia_aprovacao: 'Contingência em aprovação',
  }[selection.type]
  const periodLabel = new Intl.DateTimeFormat('pt-BR', {
    month: 'long',
    year: 'numeric',
  }).format(new Date(period.ano, period.mes - 1, 1))

  return (
    <div
      className="detail-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <aside
        className="detail-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="detail-title"
        aria-describedby="detail-context"
      >
        <header className="detail-header">
          <div className="detail-heading">
            <p className="control-label">Detalhamento financeiro</p>
            <h3 id="detail-title">{title}</h3>
            <p className="detail-nature">
              {selection.row.naturezaCodigo} — {selection.row.naturezaDescricao}
            </p>
            <p className="detail-context" id="detail-context">
              <span>{periodLabel}</span>
              <span
                className={`detail-environment detail-environment-${environment}`}
              >
                {environment.toUpperCase()}
              </span>
            </p>
          </div>
          <button
            ref={closeButtonRef}
            className="detail-close"
            type="button"
            onClick={onClose}
            aria-label="Fechar detalhamento"
          >
            ×
          </button>
        </header>

        <div className="detail-content">
          {isLoading ? (
            <div className="detail-state" role="status" aria-live="polite">
              <strong>Carregando detalhamento...</strong>
              <span>A consulta estÃ¡ sendo feita sob demanda.</span>
            </div>
          ) : error ? (
            <div className="detail-state" role="alert">
              <strong>NÃ£o foi possÃ­vel carregar um detalhe consistente.</strong>
              <span>{error.message}</span>
              <button type="button" onClick={onRetry}>Tentar novamente</button>
            </div>
          ) : data && data.quantidade > 0 ? (
            <>
              <dl className="detail-summary" aria-live="polite">
                <div>
                  <dt>Registros</dt>
                  <dd>{data.quantidade}</dd>
                </div>
                <div>
                  <dt>Total</dt>
                  <dd>{formatCurrency(data.total)}</dd>
                </div>
              </dl>
              <div
                className="detail-table-scroll"
                tabIndex={0}
                aria-label={`Tabela de ${title}`}
              >
                {selection.type === 'pc_aberto' ? (
                  <table className="detail-table detail-table-pc">
                    <thead><tr><th scope="col">Pedido</th><th scope="col">Vencimento</th><th scope="col">Valor</th></tr></thead>
                    <tbody>
                      {data.registros.map((record, index) => !isNfRecord(record) && (
                        <tr key={`${record.pedido}-${record.vencimento}-${index}`}>
                          <td>{record.pedido || '—'}</td>
                          <td>{formatProtheusDate(record.vencimento)}</td>
                          <td className="money-cell">{formatCurrency(record.valor)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : selection.type === 'nf_entrada' ? (
                  <table className="detail-table detail-table-nf">
                    <thead><tr><th scope="col">Documento</th><th scope="col">Prefixo</th><th scope="col">Parcela</th><th scope="col">Fornecedor</th><th scope="col">Nome do fornecedor</th><th scope="col">Loja</th><th scope="col">Emissão</th><th scope="col">Vencimento</th><th scope="col">Valor</th></tr></thead>
                    <tbody>
                      {data.registros.map((record, index) => isNfRecord(record) && (
                        <tr key={`${record.documento}-${record.prefixo}-${record.parcela}-${index}`}>
                          <td>{record.documento || '—'}</td><td>{record.prefixo || '—'}</td>
                          <td>{record.parcela || '—'}</td><td>{record.fornecedor || '—'}</td>
                          <td>{record.fornecedorNome || '—'}</td><td>{record.loja || '—'}</td>
                          <td>{formatProtheusDate(record.emissao)}</td><td>{formatProtheusDate(record.vencimento)}</td>
                          <td className="money-cell">{formatCurrency(record.valor)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <table className="detail-table detail-table-contingency">
                    <thead><tr><th scope="col">Pedido</th><th scope="col">Item</th><th scope="col">Vencimento</th><th scope="col">Usuário</th><th scope="col">Status</th><th scope="col">Valor</th></tr></thead>
                    <tbody>
                      {data.registros.map((record, index) => isContingenciaRecord(record) && (
                        <tr key={`${record.pedido}-${record.item}-${record.vencimento}-${index}`}>
                          <td>{record.pedido || '—'}</td><td>{record.item || '—'}</td>
                          <td>{formatProtheusDate(record.vencimento)}</td><td>{record.usuario || '—'}</td>
                          <td>{record.status || '—'}</td>
                          <td className="money-cell">{formatCurrency(record.valor)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </>
          ) : (
            <div className="detail-state" role="alert">
              <strong>Detalhamento vazio ou inconsistente.</strong>
              <span>O valor consolidado nÃ£o possui registros compatÃ­veis.</span>
              <button type="button" onClick={onRetry}>Tentar novamente</button>
            </div>
          )}
        </div>
      </aside>
    </div>
  )
}
