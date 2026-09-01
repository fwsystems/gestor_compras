import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="not-found-page">
      <section aria-labelledby="not-found-title">
        <p className="eyebrow">Erro 404</p>
        <h2 id="not-found-title">Página não encontrada</h2>
        <p>O endereço informado não corresponde a uma página disponível.</p>
        <Link className="home-link" to="/">
          Voltar ao início
        </Link>
      </section>
    </div>
  )
}
