import {
  gestorGranularityOptions,
  type GestorGranularity,
} from '../../utils/granularity'

interface GranularitySelectorProps {
  value: GestorGranularity
  onChange: (granularity: GestorGranularity) => void
}

export function GranularitySelector({
  value,
  onChange,
}: GranularitySelectorProps) {
  return (
    <fieldset className="granularity-selector">
      <legend className="control-label">Visualização</legend>
      <div className="granularity-options">
        {gestorGranularityOptions.map((option) => (
          <label key={option.value}>
            <input
              type="radio"
              name="gestor-granularity"
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
            />
            <span>{option.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  )
}
