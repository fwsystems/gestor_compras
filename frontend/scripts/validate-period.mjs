import { createServer } from 'vite'
import { readFile } from 'node:fs/promises'

const vite = await createServer({
  server: { middlewareMode: true },
  appType: 'custom',
})

const equal = (actual, expected) =>
  JSON.stringify(actual) === JSON.stringify(expected)

try {
  const period = await vite.ssrLoadModule('/src/utils/period.ts')
  const environment = await vite.ssrLoadModule('/src/utils/environment.ts')
  const nature = await vite.ssrLoadModule('/src/utils/natureFilter.ts')
  const granularity = await vite.ssrLoadModule('/src/utils/granularity.ts')
  const gestorSort = await vite.ssrLoadModule('/src/utils/gestorSort.ts')
  const gestorExport = await vite.ssrLoadModule('/src/utils/gestorExport.ts')
  const gestorDerived = await vite.ssrLoadModule('/src/utils/gestorDerived.ts')
  const dashboard = await vite.ssrLoadModule('/src/utils/dashboard.ts')
  const budgetUsage = await vite.ssrLoadModule('/src/utils/budgetUsage.ts')
  const allAvailable = {
    default: 'prd',
    environments: [
      { id: 'dev', label: 'DEV', available: true },
      { id: 'hml', label: 'HML', available: true },
      { id: 'prd', label: 'PRD', available: true },
    ],
  }
  const prdUnavailable = {
    ...allAvailable,
    default: 'hml',
    environments: allAvailable.environments.map((option) =>
      option.id === 'prd' ? { ...option, available: false } : option,
    ),
  }
  const sqlUnavailable = {
    ...allAvailable,
    default: 'dev',
    environments: allAvailable.environments.map((option) => ({
      ...option,
      available: option.id === 'dev',
    })),
  }
  const checks = [
    ['período atual 27/08/2026', period.getCurrentGestorPeriod(new Date(2026, 7, 27)), { ano: 2026, mes: 8 }],
    ['período atual 01/08/2026', period.getCurrentGestorPeriod(new Date(2026, 7, 1)), { ano: 2026, mes: 8 }],
    ['período atual 31/08/2026', period.getCurrentGestorPeriod(new Date(2026, 7, 31)), { ano: 2026, mes: 8 }],
    ['período atual 31/12/2026', period.getCurrentGestorPeriod(new Date(2026, 11, 31)), { ano: 2026, mes: 12 }],
    ['período atual 01/01/2027', period.getCurrentGestorPeriod(new Date(2027, 0, 1)), { ano: 2027, mes: 1 }],
    ['período atual cruza o ano civil', [period.getCurrentGestorPeriod(new Date(2026, 11, 31)), period.getCurrentGestorPeriod(new Date(2027, 0, 1))], [{ ano: 2026, mes: 12 }, { ano: 2027, mes: 1 }]],
    ['PRD disponível inicia PRD no período civil atual', { environment: environment.resolveInitialGestorEnvironment(allAvailable), period: period.getCurrentGestorPeriod(new Date(2026, 7, 27)) }, { environment: 'prd', period: { ano: 2026, mes: 8 } }],
    ['refresh conceitual recalcula PRD e período atual', { environment: environment.resolveInitialGestorEnvironment(allAvailable), period: period.getCurrentGestorPeriod(new Date(2027, 0, 1)) }, { environment: 'prd', period: { ano: 2027, mes: 1 } }],
    ['PRD inicial não exige confirmação manual', environment.resolveInitialGestorEnvironment(allAvailable), 'prd'],
    ['PRD indisponível inicia HML', environment.resolveInitialGestorEnvironment(prdUnavailable), 'hml'],
    ['PRD e HML indisponíveis iniciam DEV', environment.resolveInitialGestorEnvironment(sqlUnavailable), 'dev'],
    ['default indisponível não inicia datasource', environment.resolveInitialGestorEnvironment({ ...allAvailable, environments: allAvailable.environments.map((option) => option.id === 'prd' ? { ...option, available: false } : option) }), null],
    ['seleção manual HML não é sobrescrita', period.resolvePeriodForEnvironment({ ano: 2024, mes: 4 }, 'hml'), { ano: 2024, mes: 4 }],
    ['HML para PRD preserva período manual', period.resolvePeriodForEnvironment({ ano: 2024, mes: 4 }, 'prd'), { ano: 2024, mes: 4 }],
    ['PRD para HML preserva período manual', period.resolvePeriodForEnvironment({ ano: 2024, mes: 4 }, 'hml'), { ano: 2024, mes: 4 }],
    ['HML mês atual para DEV usa setembro/2025', period.resolvePeriodForEnvironment({ ano: 2026, mes: 8 }, 'dev'), { ano: 2025, mes: 9 }],
    ['DEV preserva setembro/2025 válido', period.resolvePeriodForEnvironment({ ano: 2025, mes: 9 }, 'dev'), { ano: 2025, mes: 9 }],
    ['período inicial usa getters locais', period.getCurrentGestorPeriod.toString().includes('getFullYear') && period.getCurrentGestorPeriod.toString().includes('getMonth'), true],
    ['período inicial não usa UTC', period.getCurrentGestorPeriod.toString().includes('UTC'), false],
    ['período atual aplica limite inferior', period.getCurrentGestorPeriod(new Date(1999, 6, 1)), { ano: 2000, mes: 1 }],
    ['período atual aplica limite superior', period.getCurrentGestorPeriod(new Date(2101, 6, 1)), { ano: 2100, mes: 12 }],
    ['DEV agosto sem anterior', period.getGestorPeriodNavigation({ ano: 2025, mes: 8 }, 'dev').previous, null],
    ['DEV outubro sem próximo', period.getGestorPeriodNavigation({ ano: 2025, mes: 10 }, 'dev').next, null],
    ['HML outubro para novembro', period.getGestorPeriodNavigation({ ano: 2025, mes: 10 }, 'hml').next, { ano: 2025, mes: 11 }],
    ['HML dezembro para janeiro', period.nextGestorPeriod({ ano: 2025, mes: 12 }), { ano: 2026, mes: 1 }],
    ['HML janeiro para dezembro', period.previousGestorPeriod({ ano: 2026, mes: 1 }), { ano: 2025, mes: 12 }],
    ['limite inicial', period.previousGestorPeriod({ ano: 2000, mes: 1 }), null],
    ['limite final', period.nextGestorPeriod({ ano: 2100, mes: 12 }), null],
    ['rótulo', period.formatGestorPeriod({ ano: 2026, mes: 1 }), 'Janeiro / 2026'],
    ['DEV seleção direta válida', period.parseGestorPeriodInput('2025-09', 'dev'), { ano: 2025, mes: 9 }],
    ['DEV seleção direta inválida', period.parseGestorPeriodInput('2025-11', 'dev'), null],
    ['HML seleção direta', period.parseGestorPeriodInput('2026-08', 'hml'), { ano: 2026, mes: 8 }],
    ['PRD seleção direta', period.parseGestorPeriodInput('2026-07', 'prd'), { ano: 2026, mes: 7 }],
    ['PRD julho para agosto', period.getGestorPeriodNavigation({ ano: 2026, mes: 7 }, 'prd').next, { ano: 2026, mes: 8 }],
    ['HML abaixo do limite', period.parseGestorPeriodInput('1999-12', 'hml'), null],
    ['HML acima do limite', period.parseGestorPeriodInput('2101-01', 'hml'), null],
    ['HML para PRD preserva período', period.resolvePeriodForEnvironment({ ano: 2026, mes: 7 }, 'prd'), { ano: 2026, mes: 7 }],
    ['PRD para HML preserva período', period.resolvePeriodForEnvironment({ ano: 2026, mes: 7 }, 'hml'), { ano: 2026, mes: 7 }],
    ['DEV preserva período válido', period.resolvePeriodForEnvironment({ ano: 2025, mes: 8 }, 'dev'), { ano: 2025, mes: 8 }],
    ['DEV corrige período inválido', period.resolvePeriodForEnvironment({ ano: 2026, mes: 7 }, 'dev'), { ano: 2025, mes: 9 }],
    ['ambiente inicial informado pelo backend', environment.resolveInitialGestorEnvironment(allAvailable), 'prd'],
    ['cancelar PRD preserva HML', environment.resolveGestorEnvironmentSelection('hml', 'prd', false), 'hml'],
    ['confirmar PRD seleciona PRD', environment.resolveGestorEnvironmentSelection('hml', 'prd', true), 'prd'],
    ['selecionar DEV dispensa confirmação', environment.resolveGestorEnvironmentSelection('hml', 'dev', false), 'dev'],
    ['selecionar HML dispensa confirmação', environment.resolveGestorEnvironmentSelection('prd', 'hml', false), 'hml'],
  ]

  for (const [name, actual, expected] of checks) {
    if (!equal(actual, expected)) {
      throw new Error(`${name}: ${JSON.stringify(actual)}`)
    }
    console.log(`OK ${name}`)
  }

  const rows = [
    { naturezaCodigo: '5.000-350', naturezaDescricao: 'PUBLICIDADES' },
    { naturezaCodigo: '6.000-010', naturezaDescricao: 'MAQUINAS E EQUIPAMENTOS' },
    { naturezaCodigo: '7.000-020', naturezaDescricao: 'RETROFITTING' },
  ]
  const filterChecks = [
    ['filtro vazio', nature.filterGestorRows(rows, '').length, 3],
    ['código exato', nature.filterGestorRows(rows, '5.000-350').length, 1],
    ['código parcial', nature.filterGestorRows(rows, '5.000').length, 1],
    ['descrição exata', nature.filterGestorRows(rows, 'PUBLICIDADES').length, 1],
    ['descrição parcial case-insensitive', nature.filterGestorRows(rows, 'maquinas').length, 1],
    ['espaços externos', nature.filterGestorRows(rows, '  retrofitting  ').length, 1],
    ['sem resultado', nature.filterGestorRows(rows, 'inexistente').length, 0],
    ['ordem preservada', nature.filterGestorRows(rows, '000').map((row) => row.naturezaCodigo), rows.map((row) => row.naturezaCodigo)],
  ]

  for (const [name, actual, expected] of filterChecks) {
    if (!equal(actual, expected)) {
      throw new Error(`${name}: ${JSON.stringify(actual)}`)
    }
    console.log(`OK ${name}`)
  }

  const granularityChecks = [
    ['granularidades permitidas', granularity.gestorGranularityOptions.map((option) => option.value), ['monthly', 'weekly', 'daily']],
    ['Mensal é o modo com dados consolidados', granularity.isMonthlyGranularity('monthly'), true],
    ['Semanal não usa dados consolidados', granularity.isMonthlyGranularity('weekly'), false],
    ['Diário não usa dados consolidados', granularity.isMonthlyGranularity('daily'), false],
    ['semana segunda a domingo', granularity.getGestorDateInterval('weekly', { ano: 2026, mes: 8 }, new Date(2026, 7, 27)).label, '24/08/2026 a 30/08/2026'],
    ['semana cruzando mês filtra agosto', { inicio: granularity.getGestorDateInterval('weekly', { ano: 2026, mes: 8 }, new Date(2026, 7, 31)).inicio, fim: granularity.getGestorDateInterval('weekly', { ano: 2026, mes: 8 }, new Date(2026, 7, 31)).fim }, { inicio: '2026-08-31', fim: '2026-08-31' }],
    ['dia selecionado', granularity.getGestorDateInterval('daily', { ano: 2026, mes: 8 }, new Date(2026, 7, 31)).inicio, '2026-08-31'],
  ]

  for (const [name, actual, expected] of granularityChecks) {
    if (!equal(actual, expected)) {
      throw new Error(`${name}: ${JSON.stringify(actual)}`)
    }
    console.log(`OK ${name}`)
  }

  const useGestorSource = await readFile(new URL('../src/hooks/useGestor.ts', import.meta.url), 'utf8')
  if (!useGestorSource.includes('const inicio = interval?.inicio') || !useGestorSource.includes('[ano, branch, environment, fim, inicio, mes, requestKey]')) {
    throw new Error('hook do Gestor não usa dependências primitivas de intervalo')
  }
  console.log('OK intervalo do hook usa dependências primitivas estáveis')

  const gestorTableSource = await readFile(new URL('../src/components/gestor/GestorTable.tsx', import.meta.url), 'utf8')
  if (gestorTableSource.includes("label: 'Lim Total'") || gestorTableSource.includes("field: 'limiteTotal'") || gestorTableSource.includes('row.limiteTotal')) {
    throw new Error('tabela principal ainda renderiza Lim Total')
  }
  console.log('OK tabela principal não renderiza Lim Total')

  const timelineHookSource = await readFile(new URL('../src/hooks/useGestorTimeline.ts', import.meta.url), 'utf8')
  const timelineServiceSource = await readFile(new URL('../src/services/gestorService.ts', import.meta.url), 'utf8')
  const timelineChartSource = await readFile(new URL('../src/components/dashboard/DashboardTimeline.tsx', import.meta.url), 'utf8')
  if (!timelineHookSource.includes('new AbortController()') || !timelineHookSource.includes('controller.abort()') || !timelineServiceSource.includes('/api/gestor/timeline?${query}') || !timelineChartSource.includes('LineChart') || !timelineChartSource.includes('limiteOriginal') || !timelineChartSource.includes('nfEntrada') || !timelineChartSource.includes('saldoPrevisto')) {
    throw new Error('timeline não preserva contrato, cancelamento ou três linhas mensais')
  }
  console.log('OK timeline mensal usa endpoint dedicado, abortamento e três séries esperadas')

  const sortableRows = [
    { naturezaCodigo: '4.000-460', naturezaDescricao: 'Z', pcAberto: 10, nfEntrada: 2, contingenciaOk: 3, contingenciaEmAprovacao: 4, limiteOriginal: 5, saldoPrevisto: -7, saldoReal: 3 },
    { naturezaCodigo: '1.000-050', naturezaDescricao: 'A', pcAberto: -5, nfEntrada: 9, contingenciaOk: 1, contingenciaEmAprovacao: 8, limiteOriginal: 7, saldoPrevisto: 3, saldoReal: -2 },
  ]
  for (const field of ['natureza', 'pcAberto', 'nfEntrada', 'contingenciaOk', 'contingenciaEmAprovacao', 'limiteOriginal', 'gastoPrevisto', 'saldoPrevisto', 'saldoReal']) {
    const asc = gestorSort.sortGestorRows(sortableRows, { field, direction: 'ascending' })
    const desc = gestorSort.sortGestorRows(sortableRows, { field, direction: 'descending' })
    if (asc[0] === desc[0]) throw new Error(`ordenação ${field} não alterna direção`)
    console.log(`OK ordenação crescente/decrescente ${field}`)
  }
  if (gestorSort.toggleGestorSort(null, 'pcAberto').direction !== 'ascending' || gestorSort.toggleGestorSort({ field: 'pcAberto', direction: 'ascending' }, 'pcAberto').direction !== 'descending') {
    throw new Error('alternância de ordenação inválida')
  }
  console.log('OK ordenação numérica, filtro preservado e sem API')

  const csv = gestorExport.createGestorCsv(sortableRows)
  const exportedRows = gestorExport.gestorExportRows(sortableRows)
  if (!csv.includes(';Gasto Previsto;') || exportedRows[0][6] !== 12) {
    throw new Error('Gasto Previsto não foi exportado na posição esperada')
  }
  console.log('OK Gasto Previsto exportado após Lim Original')
  if (!csv.startsWith('\uFEFFNatureza Financeira;') || !csv.includes('1.000-050 - A;-5,00;9,00') || !gestorExport.gestorExportRows(sortableRows)[0].every((value, index) => index === 0 || typeof value === 'number')) {
    throw new Error('exportação CSV/XLSX não preserva formato ou números')
  }
  if (gestorExport.gestorExportFilename('prd', 'weekly', { ano: 2026, mes: 8 }, { inicio: '2026-08-31', fim: '2026-09-06' }, 'xlsx') !== 'gestor-compras-prd-2026-08-31_a_2026-09-06.xlsx') {
    throw new Error('nome de exportação semanal inválido')
  }
  console.log('OK exportação CSV pt-BR, células XLSX numéricas e nomes de arquivo')

  const gastoCases = [[10, 20, 30], [0, 20, 20], [10, 0, 10], [0, 0, 0]]
  for (const [pcAberto, nfEntrada, expected] of gastoCases) {
    if (gestorDerived.getGastoPrevisto({ pcAberto, nfEntrada }) !== expected) throw new Error('Gasto Previsto inválido')
  }
  if (gestorDerived.getGastoPrevisto({ pcAberto: 10, nfEntrada: 20, contingenciaOk: 999, contingenciaEmAprovacao: 999 }) !== 30) {
    throw new Error('Gasto Previsto inclui contingência')
  }
  console.log('OK Gasto Previsto soma somente PC aberto e NF entrada')

  const dashboardTotals = dashboard.summarizeGestorRows(sortableRows)
  if (dashboardTotals.limiteOriginal !== 12 || dashboardTotals.nfEntrada !== 11 || dashboardTotals.percentualConsumido !== 11 / 12 * 100 || dashboard.summarizeGestorRows([]).percentualConsumido !== null) {
    throw new Error('indicadores do dashboard inválidos')
  }
  console.log('OK indicadores do dashboard reutilizam consolidados e evitam divisão por zero')
  const semLimite = budgetUsage.calculateBudgetUsage(30, 5, 0)
  const limiteZerado = budgetUsage.calculateBudgetUsage(0, 0, 0)
  if (semLimite.label !== 'Sem limite' || semLimite.percentage !== null || !Number.isFinite(semLimite.visualPercentage) || limiteZerado.percentage !== 0) {
    throw new Error('percentual consumido não trata Limite Original zero corretamente')
  }
  console.log('OK percentual consumido usa Limite Original e evita NaN/Infinity')
  if (dashboard.topConsumptionRows(sortableRows)[0].naturezaCodigo !== '1.000-050' || dashboard.lowestSaldoPrevistoRows(sortableRows)[0].saldoPrevisto !== -7 || dashboard.dashboardCommitmentChart(dashboardTotals).length !== 3 || dashboard.countOverLimitRows(sortableRows) !== 1) {
    throw new Error('rankings dos gráficos inválidos')
  }
  console.log('OK gráficos usam top 10 local e menor saldo previsto primeiro')
  const attentionRows = [
    { naturezaCodigo: '2.000-100', naturezaDescricao: 'Sem limite', pcAberto: 30, nfEntrada: 5, contingenciaOk: 0, contingenciaEmAprovacao: 7, limiteOriginal: 0, saldoPrevisto: -35, saldoReal: -5 },
    { naturezaCodigo: '2.000-200', naturezaDescricao: 'Acima do limite', pcAberto: 80, nfEntrada: 150, contingenciaOk: 0, contingenciaEmAprovacao: 20, limiteOriginal: 100, saldoPrevisto: -130, saldoReal: -50 },
    { naturezaCodigo: '2.000-300', naturezaDescricao: 'Regular', pcAberto: 0, nfEntrada: 0, contingenciaOk: 0, contingenciaEmAprovacao: 0, limiteOriginal: 50, saldoPrevisto: 50, saldoReal: 50 },
    { naturezaCodigo: '2.000-400', naturezaDescricao: 'Zero sem NF', pcAberto: 0, nfEntrada: 0, contingenciaOk: 0, contingenciaEmAprovacao: 0, limiteOriginal: 0, saldoPrevisto: 0, saldoReal: 0 },
  ]
  const critical = dashboard.criticalConsumptionRows(attentionRows)
  if (critical.length !== 2 || critical[0].consumption !== null || critical[1].consumption !== 150 || dashboard.negativeSaldoPrevistoTotal(attentionRows) !== -165 || dashboard.negativeSaldoPrevistoRows(attentionRows)[0].naturezaCodigo !== '2.000-200' || dashboard.pcAbertoRows(attentionRows)[0].pcAberto !== 80 || dashboard.contingencyApprovalRows(attentionRows)[0].contingenciaEmAprovacao !== 20) {
    throw new Error('indicadores de atenção inválidos')
  }
  console.log('OK atenção gerencial trata Sem limite, negativos, filtros e ordenações localmente')
} finally {
  await vite.close()
}
