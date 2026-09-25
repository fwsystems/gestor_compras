import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { GestorTimelinePoint } from '../../types/gestor'
import { formatCurrency } from '../../utils/currency'
import { DashboardIcon } from './DashboardIcon'

const monthFormatter = new Intl.DateTimeFormat('pt-BR', { month: 'short' })
const compactCurrency = (value: unknown) => {
  const numeric = Number(value)
  return Math.abs(numeric) >= 1_000_000 ? `R$ ${(numeric / 1_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mi` : `R$ ${(numeric / 1_000).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} mil`
}

function TimelineTooltip({ active, payload, label }: { active?: boolean; label?: string; payload?: { name: string; value: number }[] }) {
  if (!active || !payload?.length) return null
  return <div className="chart-tooltip"><strong>{label}</strong>{payload.map((item) => <span key={item.name}>{item.name}: {formatCurrency(item.value)}</span>)}</div>
}

export function DashboardTimeline({ data, error, isLoading, onRetry }: { data: readonly GestorTimelinePoint[] | null; error: Error | null; isLoading: boolean; onRetry: () => void }) {
  if (isLoading) return <section className="dashboard-timeline dashboard-timeline-state" aria-live="polite">Carregando evolução temporal...</section>
  if (error) return <section className="dashboard-timeline dashboard-timeline-state" role="alert">Não foi possível carregar a evolução temporal.<button type="button" onClick={onRetry}>Tentar novamente</button></section>
  const chartData = (data ?? []).map((point) => ({ ...point, label: `${monthFormatter.format(new Date(point.ano, point.mes - 1, 1)).replace('.', '')}/${point.ano}` }))
  return <section className="dashboard-timeline" aria-labelledby="timeline-title"><header><h3 id="timeline-title">Evolução Temporal</h3><p>Comparativo mensal de Limite Original, NF Entrada e Saldo Previsto.</p></header><div className="dashboard-timeline-viewport"><ResponsiveContainer width="100%" height="100%"><LineChart data={chartData} margin={{ top: 12, right: 16, left: 8, bottom: 4 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="label" tick={{ fontSize: 11 }} /><YAxis tickFormatter={compactCurrency} width={62} tick={{ fontSize: 10 }} /><Tooltip content={<TimelineTooltip />} /><Legend wrapperStyle={{ fontSize: 12 }} /><Line type="monotone" dataKey="limiteOriginal" name="Limite Original" stroke="#23618b" strokeWidth={2.5} dot={{ r: 3 }} /><Line type="monotone" dataKey="nfEntrada" name="NF Entrada" stroke="#27805d" strokeWidth={2.5} dot={{ r: 3 }} /><Line type="monotone" dataKey="saldoPrevisto" name="Saldo Previsto" stroke="#c15c5c" strokeWidth={2.5} dot={{ r: 3 }} /></LineChart></ResponsiveContainer></div><div className="timeline-explanation" aria-label="Como interpretar a evolução temporal"><article><span className="dashboard-icon"><DashboardIcon name="wallet" /></span><div><strong>Limite Original</strong><p>Representa o orçamento original disponível no período.</p></div></article><article><span className="dashboard-icon dashboard-icon-green"><DashboardIcon name="cart" /></span><div><strong>NF Entrada</strong><p>Representa o valor realizado no período por meio das notas fiscais de entrada.</p></div></article><article><span className="dashboard-icon dashboard-icon-coral"><DashboardIcon name="trend" /></span><div><strong>Saldo Previsto</strong><p>Limite Original - PC aberto - NF Entrada. Contingência OK permanece informativa e não compõe o saldo.</p></div></article></div><small className="timeline-note">Valores consolidados conforme as mesmas regras do modo Mensal do Gestor.</small></section>
}
