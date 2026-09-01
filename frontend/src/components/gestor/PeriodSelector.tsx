import { MAX_GESTOR_YEAR, MIN_GESTOR_YEAR, mockGestorPeriods } from '../../config/gestor'
import type { GestorDataEnvironment, GestorPeriod } from '../../types/gestor'
import { formatGestorPeriod, parseGestorPeriodInput, periodInputValue } from '../../utils/period'

interface PeriodSelectorProps {
  period: GestorPeriod
  onPrevious: () => void
  onNext: () => void
  canPrevious: boolean
  canNext: boolean
  environment: GestorDataEnvironment
  onPeriodChange: (period: GestorPeriod) => void
  contextLabel?: string
  previousLabel?: string
  nextLabel?: string
}

export function PeriodSelector({
  period,
  onPrevious,
  onNext,
  canPrevious,
  canNext,
  environment,
  onPeriodChange,
  contextLabel,
  previousLabel = 'Mês anterior',
  nextLabel = 'Próximo mês',
}: PeriodSelectorProps) {
  return (
    <section className="period-selector" aria-labelledby="period-title">
      <button
        type="button"
        disabled={!canPrevious}
        aria-disabled={!canPrevious}
        onClick={onPrevious}
      >
        {previousLabel}
      </button>
      <div className="period-current">
        <label className="control-label" id="period-title" htmlFor="period-direct-select">
          Período
        </label>
        <p className="selected-period">{contextLabel ?? formatGestorPeriod(period)}</p>
        {environment === 'dev' ? (
          <select
            id="period-direct-select"
            value={periodInputValue(period)}
            onChange={(event) => {
              const selected = parseGestorPeriodInput(event.target.value, environment)
              if (selected) onPeriodChange(selected)
            }}
          >
            {mockGestorPeriods.map((availablePeriod) => (
              <option key={periodInputValue(availablePeriod)} value={periodInputValue(availablePeriod)}>
                {formatGestorPeriod(availablePeriod)}
              </option>
            ))}
          </select>
        ) : (
          <input
            id="period-direct-select"
            type="month"
            min={`${MIN_GESTOR_YEAR}-01`}
            max={`${MAX_GESTOR_YEAR}-12`}
            value={periodInputValue(period)}
            onChange={(event) => {
              const selected = parseGestorPeriodInput(event.target.value, environment)
              if (selected) onPeriodChange(selected)
            }}
          />
        )}
      </div>
      <button
        type="button"
        disabled={!canNext}
        aria-disabled={!canNext}
        onClick={onNext}
      >
        {nextLabel}
      </button>
    </section>
  )
}
