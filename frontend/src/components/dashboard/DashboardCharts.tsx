import { Bar, BarChart, CartesianGrid, Cell, LabelList, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { GestorRow } from '../../types/gestor'
import { formatCurrency } from '../../utils/currency'
import { dashboardCommitmentChart, lowestSaldoPrevistoRows, topConsumptionRows, type GestorDashboardTotals } from '../../utils/dashboard'

function compactCurrency(value: unknown) {
  const numericValue = Number(value)
  const absolute = Math.abs(numericValue)
  if (absolute >= 1_000_000) return `R$ ${(numericValue / 1_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mi`
  if (absolute >= 1_000) return `R$ ${(numericValue / 1_000).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} mil`
  return `R$ ${numericValue.toLocaleString('pt-BR')}`
}

function MoneyTooltip({ active, payload }: { active?: boolean; payload?: { payload: Record<string, unknown>; value: number }[] }) {
  if (!active || !payload?.[0]) return null
  const item = payload[0]
  return <div className="chart-tooltip"><strong>{String(item.payload.label ?? item.payload.naturezaCodigo)}</strong>{item.payload.naturezaDescricao ? <small>{String(item.payload.naturezaDescricao)}</small> : null}<span>{formatCurrency(item.value)}</span></div>
}

function ConsumptionTooltip({ active, payload }: { active?: boolean; payload?: { payload: GestorRow & { consumo: number }; value: number }[] }) {
  if (!active || !payload?.[0]) return null
  const item = payload[0].payload
  return <div className="chart-tooltip"><strong>{item.naturezaCodigo}</strong><small>{item.naturezaDescricao}</small><span>{item.consumo.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}% consumido</span><span>NF: {formatCurrency(item.nfEntrada)}</span><span>Limite original: {formatCurrency(item.limiteOriginal)}</span></div>
}

export function DashboardCharts({ rows, totals }: { rows: readonly GestorRow[]; totals: GestorDashboardTotals }) {
  const commitments = dashboardCommitmentChart(totals)
  const consumption = topConsumptionRows(rows)
  const balances = lowestSaldoPrevistoRows(rows)
  const commitmentsTotal = commitments.reduce((total, item) => total + item.valor, 0)
  const commitmentColors = ['#23618b', '#b56d16', '#27805d']
  return <section className="dashboard-charts" aria-label="Gráficos gerenciais">
    <article className="dashboard-chart"><header><h3>Limite Original x PC em aberto x NF Entrada</h3><p>Comparativo dos principais valores</p></header><div className="dashboard-donut-layout"><div className="dashboard-chart-viewport dashboard-donut-viewport"><ResponsiveContainer width="100%" height="100%"><PieChart><Tooltip content={<MoneyTooltip />} /><Pie data={commitments} dataKey="valor" nameKey="label" innerRadius="45%" outerRadius="82%" paddingAngle={1}>{commitments.map((item, index) => <Cell key={item.label} fill={commitmentColors[index]} />)}</Pie></PieChart></ResponsiveContainer></div><ul className="dashboard-donut-legend">{commitments.map((item, index) => <li key={item.label}><i style={{ backgroundColor: commitmentColors[index] }} /><div><strong>{item.label}</strong><span>{formatCurrency(item.valor)}</span></div><b>{commitmentsTotal > 0 ? `${(item.valor / commitmentsTotal * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%` : '—'}</b></li>)}</ul></div><small className="dashboard-chart-caption">Valores em R$</small></article>
    <article className="dashboard-chart"><header><h3>Top 10 Naturezas por % de consumo</h3><p>Ranking das Naturezas com maior percentual de consumo</p></header><div className="dashboard-chart-viewport"><ResponsiveContainer width="100%" height="100%"><BarChart data={consumption} margin={{ top: 28, right: 4, left: 4, bottom: 56 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="naturezaCodigo" interval={0} angle={-40} textAnchor="end" height={58} tick={{ fontSize: 10 }} /><YAxis tickFormatter={(value) => `${value}%`} width={42} tick={{ fontSize: 10 }} /><Tooltip content={<ConsumptionTooltip />} /><Bar dataKey="consumo" fill="#7762b5" radius={[5, 5, 0, 0]}><LabelList dataKey="consumo" position="top" formatter={(value) => `${Number(value).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`} style={{ fontSize: 9, fill: '#526472' }} /></Bar></BarChart></ResponsiveContainer></div></article>
    <article className="dashboard-chart"><header><h3>Top 10 Naturezas com menores Saldos Previstos</h3><p>Ranking das Naturezas com menor saldo previsto</p></header><div className="dashboard-chart-viewport"><ResponsiveContainer width="100%" height="100%"><BarChart data={balances} margin={{ top: 28, right: 4, left: 4, bottom: 56 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="naturezaCodigo" interval={0} angle={-40} textAnchor="end" height={58} tick={{ fontSize: 10 }} /><YAxis tickFormatter={compactCurrency} width={58} tick={{ fontSize: 10 }} /><Tooltip content={<MoneyTooltip />} /><Bar dataKey="saldoPrevisto" fill="#c15c5c" radius={[5, 5, 0, 0]}><LabelList dataKey="saldoPrevisto" position="bottom" formatter={compactCurrency} style={{ fontSize: 9, fill: '#526472' }} /></Bar></BarChart></ResponsiveContainer></div></article>
  </section>
}
