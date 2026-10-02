import { useLocation } from 'react-router-dom'

import { MainContent } from './MainContent'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import { GestorEnvironmentProvider } from '../../context/GestorEnvironmentContext'

export function AppShell() {
  const { pathname } = useLocation()
  const pageTitles: Record<string, string> = {
    '/': 'Início',
    '/gestor': 'Gestor de Compras',
    '/dashboard': 'Dashboard',
    '/relatorios': 'Relat\u00f3rios',
    '/relatorios/consumo-por-natureza': 'Consumo por Natureza',
    '/relatorios/pc-em-aberto': 'PC em Aberto',
    '/relatorios/nf-entrada': 'NF Entrada',
    '/relatorios/naturezas-criticas': 'Naturezas Críticas',
    '/relatorios/evolucao-mensal': 'Evolução Mensal',
  }
  const pageTitle = pageTitles[pathname] ?? 'Página não encontrada'

  return (
    <GestorEnvironmentProvider>
      <div className="app-shell">
        <Sidebar />
        <div className="app-workspace">
          <Topbar pageTitle={pageTitle} />
          <MainContent />
        </div>
      </div>
    </GestorEnvironmentProvider>
  )
}
