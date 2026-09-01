import { useMemo, useState } from 'react'

import { DashboardCards } from '../components/dashboard/DashboardCards'
import { DashboardCharts } from '../components/dashboard/DashboardCharts'
import { DashboardSummary } from '../components/dashboard/DashboardSummary'
import { DashboardTimeline } from '../components/dashboard/DashboardTimeline'
import { EnvironmentSelector } from '../components/gestor/EnvironmentSelector'
import { GranularitySelector } from '../components/gestor/GranularitySelector'
import { PeriodSelector } from '../components/gestor/PeriodSelector'
import { DEFAULT_GESTOR_BRANCH } from '../config/gestor'
import { useGestorEnvironment } from '../context/GestorEnvironmentContext'
import { useGestor } from '../hooks/useGestor'
import { useGestorTimeline } from '../hooks/useGestorTimeline'
import type { GestorPeriod } from '../types/gestor'
import { summarizeGestorRows } from '../utils/dashboard'
import { resolveGestorEnvironmentSelection } from '../utils/environment'
import { getGestorDateInterval, isMonthlyGranularity, navigateGestorGranularity, type GestorGranularity } from '../utils/granularity'
import { getCurrentGestorPeriod, getGestorPeriodNavigation, resolvePeriodForEnvironment } from '../utils/period'

export function DashboardPage() {
  const [period, setPeriod] = useState<GestorPeriod>(() => getCurrentGestorPeriod())
  const [granularity, setGranularity] = useState<GestorGranularity>('monthly')
  const [selectedDate, setSelectedDate] = useState(() => new Date(period.ano, period.mes - 1, 1))
  const { environment, environments, setEnvironment } = useGestorEnvironment()
  const interval = useMemo(() => getGestorDateInterval(granularity, { ano: period.ano, mes: period.mes }, selectedDate), [granularity, period.ano, period.mes, selectedDate])
  const { data, error, isLoading, reload } = useGestor(period, DEFAULT_GESTOR_BRANCH, environment, interval)
  const timeline = useGestorTimeline(period, DEFAULT_GESTOR_BRANCH, environment)
  const navigation = getGestorPeriodNavigation(period, environment)
  const totals = summarizeGestorRows(data?.linhas ?? [])
  const move = (direction: -1 | 1) => {
    if (isMonthlyGranularity(granularity)) {
      const next = direction === -1 ? navigation.previous : navigation.next
      if (next) { setPeriod(next); setSelectedDate(new Date(next.ano, next.mes - 1, 1)) }
      return
    }
    const next = navigateGestorGranularity(granularity, period, interval?.selectedDate ?? selectedDate, direction)
    if (next) setSelectedDate(next)
  }
  const canMove = (direction: -1 | 1) => isMonthlyGranularity(granularity)
    ? (direction === -1 ? navigation.previous : navigation.next) !== null
    : navigateGestorGranularity(granularity, period, interval?.selectedDate ?? selectedDate, direction) !== null

  return <div className="dashboard-page">
    <header className="gestor-header"><p className="eyebrow">Visão gerencial</p><h2>Dashboard</h2><p>Indicadores consolidados do Gestor de Compras.</p></header>
    <div className="gestor-controls">
      <EnvironmentSelector environment={environment} environments={environments} onChange={(requested) => {
        const confirmed = requested !== 'prd' || window.confirm('Consultar dados de PRODUÇÃO?\n\nA consulta será somente leitura.')
        const next = resolveGestorEnvironmentSelection(environment, requested, confirmed)
        if (next !== environment) { setEnvironment(next); setPeriod((current) => resolvePeriodForEnvironment(current, next)) }
      }} />
      <PeriodSelector period={period} onPrevious={() => move(-1)} onNext={() => move(1)} canPrevious={canMove(-1)} canNext={canMove(1)} environment={environment} onPeriodChange={(next) => { setPeriod(next); setSelectedDate(new Date(next.ano, next.mes - 1, 1)) }} contextLabel={interval?.label} previousLabel={isMonthlyGranularity(granularity) ? undefined : granularity === 'weekly' ? 'Semana anterior' : 'Dia anterior'} nextLabel={isMonthlyGranularity(granularity) ? undefined : granularity === 'weekly' ? 'Próxima semana' : 'Próximo dia'} />
      <GranularitySelector value={granularity} onChange={(next) => { setGranularity(next); setSelectedDate(new Date(period.ano, period.mes - 1, 1)) }} />
    </div>
    {isLoading ? <section className="dashboard-state" role="status">Carregando indicadores...</section> : error ? <section className="dashboard-state" role="alert">Não foi possível carregar os indicadores.<button type="button" onClick={reload}>Tentar novamente</button></section> : data?.linhas.length ? <><DashboardCards totals={totals} /><DashboardCharts rows={data.linhas} totals={totals} /><DashboardSummary rows={data.linhas} /><DashboardTimeline data={timeline.data} error={timeline.error} isLoading={timeline.isLoading} onRetry={timeline.reload} /></> : <section className="dashboard-state">Nenhum dado disponível para este período.</section>}
  </div>
}
