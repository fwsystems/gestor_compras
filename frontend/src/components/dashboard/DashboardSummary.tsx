import { useEffect, useMemo, useState } from 'react'

import type { GestorRow } from '../../types/gestor'
import { formatCurrency } from '../../utils/currency'
import { contingencyApprovalRows, criticalConsumptionRows, negativeSaldoPrevistoRows, negativeSaldoPrevistoTotal, pcAbertoRows } from '../../utils/dashboard'
import { DashboardAttentionDrawer, type DashboardAttentionType } from './DashboardAttentionDrawer'
import { DashboardIcon } from './DashboardIcon'

export function DashboardSummary({ rows }: { rows: readonly GestorRow[] }) {
  const [selection, setSelection] = useState<DashboardAttentionType | null>(null)
  const indicators = useMemo(() => {
    const critical = criticalConsumptionRows(rows)
    const negative = negativeSaldoPrevistoRows(rows)
    const openOrders = pcAbertoRows(rows)
    const approval = contingencyApprovalRows(rows)
    return { critical, negative, openOrders, approval, negativeTotal: negativeSaldoPrevistoTotal(rows), openOrdersTotal: openOrders.reduce((total, row) => total + row.pcAberto, 0), approvalTotal: approval.reduce((total, row) => total + row.contingenciaEmAprovacao, 0) }
  }, [rows])
  useEffect(() => { setSelection(null) }, [rows])
  const selectedRows = selection === 'consumption' ? indicators.critical : selection === 'negativeBalance' ? indicators.negative : selection === 'openOrders' ? indicators.openOrders : indicators.approval
  const choices = [
    { id: 'consumption' as const, icon: 'gauge' as const, tone: '', title: 'Consumo crítico', value: `${indicators.critical.length} Natureza${indicators.critical.length === 1 ? '' : 's'} requerem atenção`, subtitle: 'NF Entrada acima do limite ou sem limite', enabled: indicators.critical.length > 0 },
    { id: 'negativeBalance' as const, icon: 'trend' as const, tone: 'dashboard-icon-coral', title: 'Saldo previsto negativo', value: `${indicators.negative.length} Natureza${indicators.negative.length === 1 ? '' : 's'} · ${formatCurrency(indicators.negativeTotal)}`, subtitle: 'Soma somente dos saldos negativos', enabled: indicators.negative.length > 0 },
    { id: 'openOrders' as const, icon: 'clipboard' as const, tone: 'dashboard-icon-amber', title: 'PC em aberto', value: formatCurrency(indicators.openOrdersTotal), subtitle: `${indicators.openOrders.length} Natureza${indicators.openOrders.length === 1 ? '' : 's'} com valor em aberto`, enabled: indicators.openOrders.length > 0 },
    { id: 'approval' as const, icon: 'hourglass' as const, tone: 'dashboard-icon-purple', title: 'Em aprovação', value: formatCurrency(indicators.approvalTotal), subtitle: `${indicators.approval.length} Natureza${indicators.approval.length === 1 ? '' : 's'} aguardando aprovação`, enabled: indicators.approval.length > 0 },
  ]
  return <><section className="dashboard-summary" aria-label="Atenção gerencial"><h3>Atenção gerencial</h3>{choices.map((choice) => <button type="button" key={choice.id} disabled={!choice.enabled} onClick={() => setSelection(choice.id)}><span className={`dashboard-icon ${choice.tone}`}><DashboardIcon name={choice.icon} /></span><span><strong>{choice.title}</strong><b>{choice.value}</b><small>{choice.subtitle}</small></span><em>{choice.enabled ? 'Ver detalhes' : 'Sem registros'}</em></button>)}</section>{selection && selectedRows.length > 0 ? <DashboardAttentionDrawer type={selection} rows={selectedRows} onClose={() => setSelection(null)} /> : null}</>
}
