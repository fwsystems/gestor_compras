import type {
  GestorDataEnvironment,
  GestorEnvironmentOption,
} from '../../types/gestor'

interface EnvironmentSelectorProps {
  environment: GestorDataEnvironment
  environments: readonly GestorEnvironmentOption[]
  onChange: (environment: GestorDataEnvironment) => void
}

export function EnvironmentSelector({
  environment,
  environments,
  onChange,
}: EnvironmentSelectorProps) {
  return (
    <section
      className={`data-environment-selector data-environment-${environment}`}
      aria-labelledby="data-environment-label"
    >
      <div>
        <label
          className="control-label"
          id="data-environment-label"
          htmlFor="data-environment-select"
        >
          Ambiente de dados
        </label>
        <p>Dados {environment.toUpperCase()}</p>
      </div>
      <select
        id="data-environment-select"
        value={environment}
        onChange={(event) =>
          onChange(event.target.value as GestorDataEnvironment)
        }
      >
        {environments.map((option) => (
          <option
            disabled={!option.available}
            key={option.id}
            value={option.id}
          >
            {option.label}{option.available ? '' : ' — indisponível'}
          </option>
        ))}
      </select>
    </section>
  )
}
