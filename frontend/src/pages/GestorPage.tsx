import { useCallback, useMemo, useState } from 'react'

import { GestorLegend } from '../components/gestor/GestorLegend'
import { GestorTable } from '../components/gestor/GestorTable'
import { GestorDetailDrawer } from '../components/gestor/GestorDetailDrawer'
import { EnvironmentSelector } from '../components/gestor/EnvironmentSelector'
import { GranularitySelector } from '../components/gestor/GranularitySelector'
import { NatureFilter } from '../components/gestor/NatureFilter'
import { PeriodSelector } from '../components/gestor/PeriodSelector'
import {
  DEFAULT_GESTOR_BRANCH,
} from '../config/gestor'
import { useGestorEnvironment } from '../context/GestorEnvironmentContext'
import { useGestor } from '../hooks/useGestor'
import { useGestorDetail } from '../hooks/useGestorDetail'
import type { GestorDetailSelection, GestorPeriod } from '../types/gestor'
import { filterGestorRows, hasNatureSearch } from '../utils/natureFilter'
import { resolveGestorEnvironmentSelection } from '../utils/environment'
import {
  getCurrentGestorPeriod,
  getGestorPeriodNavigation,
  resolvePeriodForEnvironment,
} from '../utils/period'
import {
  getGestorDateInterval,
  isMonthlyGranularity,
  navigateGestorGranularity,
  type GestorGranularity,
} from '../utils/granularity'
import {
  sortGestorRows,
  toggleGestorSort,
  type GestorSort,
} from '../utils/gestorSort'
import {
  exportGestorCsv,
  exportGestorXlsx,
  gestorExportFilename,
} from '../utils/gestorExport'

export function GestorPage() {
  const [currentPeriod, setCurrentPeriod] =
    useState<GestorPeriod>(() => getCurrentGestorPeriod())
  const [natureSearch, setNatureSearch] = useState('')
  const [sort, setSort] = useState<GestorSort | null>(null)
  const [granularity, setGranularity] =
    useState<GestorGranularity>('monthly')
  const [selectedDate, setSelectedDate] = useState(
    () => new Date(currentPeriod.ano, currentPeriod.mes - 1, 1),
  )
  const [detailSelection, setDetailSelection] =
    useState<GestorDetailSelection | null>(null)
  const { environment, environments, setEnvironment } =
    useGestorEnvironment()
  const monthlyNavigation = getGestorPeriodNavigation(
    currentPeriod,
    environment,
  )
  const interval = useMemo(
    () => getGestorDateInterval(
      granularity,
      { ano: currentPeriod.ano, mes: currentPeriod.mes },
      selectedDate,
    ),
    [currentPeriod.ano, currentPeriod.mes, granularity, selectedDate],
  )
  const { data, error, isLoading, reload } = useGestor(
    currentPeriod,
    DEFAULT_GESTOR_BRANCH,
    environment,
    interval,
  )
  const filteredRows = useMemo(
    () => filterGestorRows(data?.linhas ?? [], natureSearch),
    [data?.linhas, natureSearch],
  )
  const isNatureFiltered = hasNatureSearch(natureSearch)
  const sortedRows = useMemo(
    () => sortGestorRows(filteredRows, sort),
    [filteredRows, sort],
  )
  const detail = useGestorDetail(
    detailSelection,
    currentPeriod,
    DEFAULT_GESTOR_BRANCH,
    environment,
    interval,
  )
  const closeDetail = useCallback(() => setDetailSelection(null), [])

  const changePeriod = (period: GestorPeriod) => {
    setDetailSelection(null)
    setCurrentPeriod(period)
    setSelectedDate(new Date(period.ano, period.mes - 1, 1))
  }

  const changeGranularity = (nextGranularity: GestorGranularity) => {
    setDetailSelection(null)
    setGranularity(nextGranularity)
    setSelectedDate(new Date(currentPeriod.ano, currentPeriod.mes - 1, 1))
  }

  const changeEnvironment = (requestedEnvironment: typeof environment) => {
    const confirmed =
      requestedEnvironment !== 'prd' ||
      window.confirm(
        'Consultar dados de PRODUÇÃO?\n\nA consulta será somente leitura.',
      )
    const nextEnvironment = resolveGestorEnvironmentSelection(
      environment,
      requestedEnvironment,
      confirmed,
    )
    if (nextEnvironment === environment) return
    setDetailSelection(null)
    setCurrentPeriod((period) =>
      resolvePeriodForEnvironment(period, nextEnvironment),
    )
    setEnvironment(nextEnvironment)
    setSelectedDate(new Date(currentPeriod.ano, currentPeriod.mes - 1, 1))
  }

  const changeTemporalSelection = (direction: -1 | 1) => {
    const next = navigateGestorGranularity(
      granularity,
      currentPeriod,
      interval?.selectedDate ?? selectedDate,
      direction,
    )
    if (next) {
      setDetailSelection(null)
      setSelectedDate(next)
    }
  }

  const canPrevious = isMonthlyGranularity(granularity)
    ? monthlyNavigation.previous !== null
    : navigateGestorGranularity(granularity, currentPeriod, interval?.selectedDate ?? selectedDate, -1) !== null
  const canNext = isMonthlyGranularity(granularity)
    ? monthlyNavigation.next !== null
    : navigateGestorGranularity(granularity, currentPeriod, interval?.selectedDate ?? selectedDate, 1) !== null
  const exportInterval = interval
    ? { inicio: interval.inicio, fim: interval.fim }
    : null
  const exportDisabled = isLoading || error !== null || sortedRows.length === 0

  return (
    <div className="gestor-page">
      <header className="gestor-header">
        <p className="eyebrow">Acompanhamento de compras</p>
        <h2>Gestor de Compras</h2>
        <p>Acompanhamento do orçamento e dos compromissos de compras.</p>
      </header>

      <div className="gestor-controls">
        <EnvironmentSelector
          environment={environment}
          environments={environments}
          onChange={changeEnvironment}
        />
        <PeriodSelector
          period={currentPeriod}
          onPrevious={() =>
            isMonthlyGranularity(granularity)
              ? monthlyNavigation.previous && changePeriod(monthlyNavigation.previous)
              : changeTemporalSelection(-1)
          }
          onNext={() => isMonthlyGranularity(granularity)
            ? monthlyNavigation.next && changePeriod(monthlyNavigation.next)
            : changeTemporalSelection(1)}
          canPrevious={canPrevious}
          canNext={canNext}
          environment={environment}
          onPeriodChange={changePeriod}
          contextLabel={interval?.label}
          previousLabel={isMonthlyGranularity(granularity) ? undefined : granularity === 'weekly' ? 'Semana anterior' : 'Dia anterior'}
          nextLabel={isMonthlyGranularity(granularity) ? undefined : granularity === 'weekly' ? 'Próxima semana' : 'Próximo dia'}
        />
        <GranularitySelector
          value={granularity}
          onChange={changeGranularity}
        />
      </div>
      <>
          <GestorLegend />
          <NatureFilter
            value={natureSearch}
            onChange={(value) => {
              setDetailSelection(null)
              setNatureSearch(value)
            }}
            onClear={() => {
              setDetailSelection(null)
              setNatureSearch('')
            }}
          />
          <GestorTable
            rows={sortedRows}
            count={data?.quantidade ?? 0}
            isFiltered={isNatureFiltered}
            isLoading={isLoading}
            hasError={error !== null}
            onRetry={reload}
            onOpenDetail={(row, type) => setDetailSelection({ row, type })}
            sort={sort}
            onSort={(field) => setSort((current) => toggleGestorSort(current, field))}
            exportDisabled={exportDisabled}
            onExportCsv={() => exportGestorCsv(
              sortedRows,
              gestorExportFilename(environment, granularity, currentPeriod, exportInterval, 'csv'),
            )}
            onExportXlsx={() => exportGestorXlsx(
              sortedRows,
              gestorExportFilename(environment, granularity, currentPeriod, exportInterval, 'xlsx'),
            )}
          />
      </>
      {detailSelection && (
        <GestorDetailDrawer
          selection={detailSelection}
          period={currentPeriod}
          environment={environment}
          data={detail.data}
          isLoading={detail.isLoading}
          error={detail.error}
          onRetry={detail.retry}
          onClose={closeDetail}
        />
      )}
    </div>
  )
}
