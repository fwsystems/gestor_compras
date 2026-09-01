interface NatureFilterProps {
  value: string
  onChange: (value: string) => void
  onClear: () => void
}

export function NatureFilter({ value, onChange, onClear }: NatureFilterProps) {
  return (
    <div className="nature-filter">
      <label className="control-label" htmlFor="nature-search">
        Natureza
      </label>
      <div className="nature-filter-control">
        <input
          id="nature-search"
          type="search"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Buscar código ou descrição"
          autoComplete="off"
        />
        {value.length > 0 && (
          <button type="button" onClick={onClear}>
            Limpar
          </button>
        )}
      </div>
    </div>
  )
}
