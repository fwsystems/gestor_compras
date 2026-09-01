import { formatCurrency } from '../../utils/currency'
import type { GestorDashboardTotals } from '../../utils/dashboard'
import { DashboardIcon, type DashboardIconName } from './DashboardIcon'

const cards: { label: string; field: keyof Omit<GestorDashboardTotals, 'percentualConsumido'>; icon: DashboardIconName; tone: string }[] = [
  { label: 'Limite Total', field: 'limiteTotal', icon: 'wallet', tone: 'blue' },
  { label: 'PC em aberto', field: 'pcAberto', icon: 'clipboard', tone: 'orange' },
  { label: 'NF Entrada', field: 'nfEntrada', icon: 'cart', tone: 'green' },
  { label: 'Contingência OK', field: 'contingenciaOk', icon: 'shield', tone: 'purple' },
  { label: 'Em aprovação', field: 'contingenciaEmAprovacao', icon: 'hourglass', tone: 'amber' },
  { label: 'Saldo Previsto', field: 'saldoPrevisto', icon: 'trend', tone: 'coral' },
  { label: 'Saldo Real', field: 'saldoReal', icon: 'pie', tone: 'coral' },
]

export function DashboardCards({ totals }: { totals: GestorDashboardTotals }) {
  return <section className="dashboard-cards" aria-label="Indicadores consolidados">
    {cards.map((card) => <article className={`dashboard-card dashboard-card-${card.tone}${totals[card.field] < 0 ? ' dashboard-card-negative' : ''}`} key={card.field}>
      <span className="dashboard-icon"><DashboardIcon name={card.icon} /></span><div><p>{card.label}</p><strong>{formatCurrency(totals[card.field])}</strong></div>
    </article>)}
    <article className="dashboard-card dashboard-card-teal">
      <span className="dashboard-icon"><DashboardIcon name="gauge" /></span><div><p>% Consumido</p><strong>{totals.percentualConsumido === null ? '—' : `${totals.percentualConsumido.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`}</strong></div>
    </article>
  </section>
}
