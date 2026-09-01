import { env } from '../config/env'
import { useAppInfo } from '../hooks/useAppInfo'

export function HomePage() {
  const { data, error, isLoading } = useAppInfo()

  return (
    <div className="home-page">
      <section className="page-intro" aria-labelledby="welcome-title">
        <p className="eyebrow">Visão geral</p>
        <h2 id="welcome-title">Bem-vindo ao Gestor de Compras</h2>
        <p>Acompanhamento de orçamento e compromissos de compras.</p>
      </section>

      <section className="system-status" aria-labelledby="status-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Infraestrutura</p>
            <h2 id="status-title">Status do sistema</h2>
          </div>
          <span
            className={`status-pill ${error ? 'status-error' : isLoading ? 'status-loading' : 'status-success'}`}
            aria-live="polite"
          >
            {isLoading
              ? 'Verificando API...'
              : error
                ? 'API indisponível'
                : 'API disponível'}
          </span>
        </div>

        <dl className="system-details">
          <div>
            <dt>API</dt>
            <dd>{data?.application ?? env.appName}</dd>
          </div>
          <div>
            <dt>Ambiente</dt>
            <dd>{(data?.environment ?? env.appEnvironment).toUpperCase()}</dd>
          </div>
          <div>
            <dt>Versão</dt>
            <dd>{data?.version ?? env.appVersion}</dd>
          </div>
        </dl>
      </section>
    </div>
  )
}
