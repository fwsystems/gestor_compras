import { useGestorEnvironment } from '../../context/GestorEnvironmentContext'

interface TopbarProps {
  pageTitle: string
}

export function Topbar({ pageTitle }: TopbarProps) {
  const { environment } = useGestorEnvironment()
  return (
    <header className="topbar">
      <h1 className="topbar-title">{pageTitle}</h1>
      <span
        className={`environment-badge environment-${environment}`}
        aria-label={`Ambiente dos dados ${environment.toUpperCase()}`}
      >
        Dados {environment.toUpperCase()}
      </span>
    </header>
  )
}
