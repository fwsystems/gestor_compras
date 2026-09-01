const references = [
  ['(a)', 'PC aberto'],
  ['(b)', 'NF entrada'],
  ['(c)', 'Contingência OK'],
  ['(d)', 'Contingência em aprovação'],
  ['(e)', 'Lim Original'],
] as const

export function GestorLegend() {
  return (
    <aside className="gestor-legend" aria-labelledby="legend-title">
      <div className="legend-references">
        <p className="control-label" id="legend-title">
          Referências
        </p>
        <ul>
          {references.map(([reference, label]) => (
            <li key={reference}>
              <strong>{reference}</strong> {label}
            </li>
          ))}
        </ul>
      </div>

      <div className="formula-summary">
        <p className="control-label">Fórmulas de referência</p>
        <ul>
          <li>Lim Total = (e) + (c)</li>
          <li>Saldo previsto = (e) + (c) - (a) - (b)</li>
          <li>Saldo real = (e) + (c) - (b)</li>
        </ul>
      </div>

      <div className="usage-legend">
        <p className="control-label">Consumo: PC aberto + NF entrada</p>
        <ul>
          <li><span className="legend-dot usage-comfortable" />0–69% confortável</li>
          <li><span className="legend-dot usage-attention" />70–89% atenção</li>
          <li><span className="legend-dot usage-near-limit" />90–99% próximo do limite</li>
          <li><span className="legend-dot usage-committed" />100% limite comprometido</li>
          <li><span className="legend-dot usage-exceeded" />Acima de 100% limite excedido</li>
        </ul>
      </div>
    </aside>
  )
}
