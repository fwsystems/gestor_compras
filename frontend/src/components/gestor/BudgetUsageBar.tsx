import { calculateBudgetUsage } from '../../utils/budgetUsage'

interface BudgetUsageBarProps {
  pcAberto: number
  nfEntrada: number
  limiteOriginal: number
}

export function BudgetUsageBar({
  pcAberto,
  nfEntrada,
  limiteOriginal,
}: BudgetUsageBarProps) {
  const usage = calculateBudgetUsage(pcAberto, nfEntrada, limiteOriginal)

  return (
    <div className={`budget-usage usage-${usage.level}`}>
      <div
        className="budget-usage-track"
        role="progressbar"
        aria-label="Consumo do limite original"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={usage.visualPercentage}
        aria-valuetext={usage.accessibleLabel}
      >
        <span
          className="budget-usage-fill"
          style={{ width: `${usage.visualPercentage}%` }}
        />
      </div>
      <span className="budget-usage-label">{usage.label}</span>
    </div>
  )
}
