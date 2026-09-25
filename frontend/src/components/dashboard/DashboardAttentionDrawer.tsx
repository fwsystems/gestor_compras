import { useEffect, useRef } from 'react'

import type { GestorRow } from '../../types/gestor'
import { formatCurrency } from '../../utils/currency'
import type { ConsumptionCriticalRow } from '../../utils/dashboard'

export type DashboardAttentionType = 'consumption' | 'negativeBalance' | 'openOrders' | 'approval'

interface DashboardAttentionDrawerProps {
  type: DashboardAttentionType
  rows: readonly GestorRow[] | readonly ConsumptionCriticalRow[]
  onClose: () => void
}

const titles: Record<DashboardAttentionType, { title: string; description: string }> = {
  consumption: { title: 'Consumo crítico', description: 'Naturezas com NF Entrada acima do limite original ou sem limite disponível.' },
  negativeBalance: { title: 'Saldo previsto negativo', description: 'Naturezas cujo saldo previsto do período está negativo.' },
  openOrders: { title: 'PC em aberto', description: 'Naturezas com pedidos de compra em aberto.' },
  approval: { title: 'Em aprovação', description: 'Naturezas com contingências aguardando aprovação.' },
}

function isConsumptionRow(row: GestorRow | ConsumptionCriticalRow): row is ConsumptionCriticalRow {
  return 'row' in row
}

export function DashboardAttentionDrawer({ type, rows, onClose }: DashboardAttentionDrawerProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    closeButtonRef.current?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
      previousFocus?.focus()
    }
  }, [onClose])

  const { title, description } = titles[type]
  return (
    <div className="detail-overlay" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <aside className="detail-drawer attention-drawer" role="dialog" aria-modal="true" aria-labelledby="attention-title" aria-describedby="attention-description">
        <header className="detail-header">
          <div className="detail-heading">
            <p className="control-label">Atenção gerencial</p>
            <h3 id="attention-title">{title}</h3>
            <p className="detail-context" id="attention-description">{description}</p>
          </div>
          <button ref={closeButtonRef} className="detail-close" type="button" onClick={onClose} aria-label="Fechar atenção gerencial">×</button>
        </header>
        <div className="detail-content">
          <div className="detail-table-scroll" tabIndex={0} aria-label={`Tabela de ${title}`}>
            <table className="detail-table attention-table">
              <thead>
                <tr>
                  <th scope="col">Natureza</th>
                  <th scope="col">Descrição</th>
                  <th scope="col">Lim. Original</th>
                  {type === 'consumption' ? <><th scope="col">NF Entrada</th><th scope="col">% Consumido</th></> : type === 'negativeBalance' ? <><th scope="col">PC aberto</th><th scope="col">NF Entrada</th><th scope="col">Saldo previsto</th></> : type === 'openOrders' ? <><th scope="col">PC aberto</th><th scope="col">Saldo previsto</th></> : <><th scope="col">Em aprovação</th><th scope="col">Saldo previsto</th></>}
                </tr>
              </thead>
              <tbody>
                {rows.map((entry) => {
                  const consumption = isConsumptionRow(entry) ? entry : null
                  const row = consumption?.row ?? entry as GestorRow
                  return (
                    <tr key={row.naturezaCodigo}>
                      <td>{row.naturezaCodigo}</td>
                      <td>{row.naturezaDescricao}</td>
                      <td className="money-cell">{formatCurrency(row.limiteOriginal)}</td>
                      {type === 'consumption' ? <>
                        <td className="money-cell">{formatCurrency(row.nfEntrada)}</td>
                        <td>{consumption?.consumption === null ? 'Sem limite' : `${consumption?.consumption.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`}</td>
                      </> : type === 'negativeBalance' ? <>
                        <td className="money-cell">{formatCurrency(row.pcAberto)}</td>
                        <td className="money-cell">{formatCurrency(row.nfEntrada)}</td>
                        <td className="money-cell money-negative">{formatCurrency(row.saldoPrevisto)}</td>
                      </> : type === 'openOrders' ? <>
                        <td className="money-cell">{formatCurrency(row.pcAberto)}</td>
                        <td className={`money-cell${row.saldoPrevisto < 0 ? ' money-negative' : ''}`}>{formatCurrency(row.saldoPrevisto)}</td>
                      </> : <>
                        <td className="money-cell">{formatCurrency(row.contingenciaEmAprovacao)}</td>
                        <td className={`money-cell${row.saldoPrevisto < 0 ? ' money-negative' : ''}`}>{formatCurrency(row.saldoPrevisto)}</td>
                      </>}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </aside>
    </div>
  )
}
