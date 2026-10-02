import { Link } from 'react-router-dom'

export function ReportsPage() {
  return (
    <div className="reports-page">
      <header className="gestor-header">
        <p className="eyebrow">Relat&oacute;rios</p>
        <h2>Relat&oacute;rios</h2>
        <p>Relat&oacute;rios gerenciais do Gestor de Compras.</p>
      </header>
      <section className="report-cards" aria-label="Relat&oacute;rios dispon&iacute;veis">
        <article className="report-card">
          <p className="eyebrow">Relat&oacute;rio gerencial</p>
          <h3>Consumo por Natureza</h3>
          <p>Vis&atilde;o consolidada de limite, compras, notas, pagamentos e saldos.</p>
          <Link className="primary-action" to="/relatorios/consumo-por-natureza">Abrir relat&oacute;rio</Link>
        </article>
        <article className="report-card">
          <p className="eyebrow">Relat&oacute;rio gerencial</p>
          <h3>PC em Aberto</h3>
          <p>Pedidos de compra em aberto por Natureza, fornecedor e pedido.</p>
          <Link className="primary-action" to="/relatorios/pc-em-aberto">Abrir relat&oacute;rio</Link>
        </article>
        <article className="report-card">
          <p className="eyebrow">Relat&oacute;rio gerencial</p>
          <h3>NF Entrada</h3>
          <p>Notas fiscais de entrada por Natureza, fornecedor e documento.</p>
          <Link className="primary-action" to="/relatorios/nf-entrada">Abrir relat&oacute;rio</Link>
        </article>
        <article className="report-card">
          <p className="eyebrow">Relat&oacute;rio gerencial</p>
          <h3>Naturezas Cr&iacute;ticas</h3>
          <p>Naturezas com consumo cr&iacute;tico, saldo previsto negativo ou movimenta&ccedil;&atilde;o sem limite.</p>
          <Link className="primary-action" to="/relatorios/naturezas-criticas">Abrir relat&oacute;rio</Link>
        </article>
        <article className="report-card">
          <p className="eyebrow">Relat&oacute;rio gerencial</p>
          <h3>Evolu&ccedil;&atilde;o Mensal</h3>
          <p>Evolu&ccedil;&atilde;o mensal de limite, compras, notas fiscais e saldos.</p>
          <Link className="primary-action" to="/relatorios/evolucao-mensal">Abrir relat&oacute;rio</Link>
        </article>
      </section>
    </div>
  )
}
