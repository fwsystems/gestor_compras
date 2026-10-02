import { BrowserRouter, Route, Routes } from 'react-router-dom'

import { AppShell } from './components/layout/AppShell'
import { GestorPage } from './pages/GestorPage'
import { DashboardPage } from './pages/DashboardPage'
import { HomePage } from './pages/HomePage'
import { NotFoundPage } from './pages/NotFoundPage'
import { ReportsPage } from './pages/ReportsPage'
import { ConsumptionByNaturePage } from './pages/ConsumptionByNaturePage'
import { PcAbertoReportPage } from './pages/PcAbertoReportPage'
import { NfEntradaReportPage } from './pages/NfEntradaReportPage'
import { CriticalNaturesReportPage } from './pages/CriticalNaturesReportPage'
import { MonthlyEvolutionReportPage } from './pages/MonthlyEvolutionReportPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<HomePage />} />
          <Route path="gestor" element={<GestorPage />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="relatorios" element={<ReportsPage />} />
          <Route path="relatorios/consumo-por-natureza" element={<ConsumptionByNaturePage />} />
          <Route path="relatorios/pc-em-aberto" element={<PcAbertoReportPage />} />
          <Route path="relatorios/nf-entrada" element={<NfEntradaReportPage />} />
          <Route path="relatorios/naturezas-criticas" element={<CriticalNaturesReportPage />} />
          <Route path="relatorios/evolucao-mensal" element={<MonthlyEvolutionReportPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
