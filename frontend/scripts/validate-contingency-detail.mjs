import { readFile } from 'node:fs/promises'

const [table, drawer, hook, service, types] = await Promise.all([
  readFile(new URL('../src/components/gestor/GestorTable.tsx', import.meta.url), 'utf8'),
  readFile(new URL('../src/components/gestor/GestorDetailDrawer.tsx', import.meta.url), 'utf8'),
  readFile(new URL('../src/hooks/useGestorDetail.ts', import.meta.url), 'utf8'),
  readFile(new URL('../src/services/gestorService.ts', import.meta.url), 'utf8'),
  readFile(new URL('../src/types/gestor.ts', import.meta.url), 'utf8'),
])

const checks = [
  ['tipo Contingência OK', types.includes("'contingencia_ok'")],
  ['tipo Contingência em aprovação', types.includes("'contingencia_aprovacao'")],
  ['Contingência OK possui gatilho', table.includes("contingenciaOk: { type: 'contingencia_ok'")],
  ['Contingência em aprovação possui gatilho', table.includes("type: 'contingencia_aprovacao'")],
  ['zero não é clicável', table.includes('detail && row[field] !== 0')],
  ['tipo correto enviado pelo serviço', service.includes('tipo: type')],
  ['contexto Contingência OK', drawer.includes("contingencia_ok: 'Contingência OK'")],
  ['contexto Contingência em aprovação', drawer.includes("contingencia_aprovacao: 'Contingência em aprovação'")],
  ['colunas operacionais do drawer', ['Pedido', 'Item', 'Vencimento', 'Usuário', 'Status', 'Valor'].every((label) => drawer.includes(`scope="col">${label}</th>`))],
  ['quantidade preservada', drawer.includes('data.quantidade')],
  ['total preservado', drawer.includes('formatCurrency(data.total)')],
  ['loading preservado', drawer.includes('isLoading')],
  ['erro preservado', drawer.includes('error ?')],
  ['retry preservado', drawer.includes('onClick={onRetry}')],
  ['fechamento preservado', drawer.includes('onClick={onClose}')],
  ['Escape preservado', drawer.includes("event.key === 'Escape'")],
  ['foco preservado', drawer.includes('closeButtonRef.current?.focus()') && drawer.includes('previousFocus?.focus()')],
  ['cancelamento preservado', hook.includes('new AbortController()') && hook.includes('controller.abort()')],
  ['resposta obsoleta preservada', hook.includes('requestKey') && hook.includes('controller.signal.aborted')],
  ['troca de ambiente invalida detalhe', hook.includes('${environment}-${period.ano}-${period.mes}')],
  ['invariância usa total correto por tipo', hook.includes('contingencia_ok: selection.row.contingenciaOk') && hook.includes('contingencia_aprovacao: selection.row.contingenciaEmAprovacao')],
  ['regressão NF e PC preservada', types.includes("'pc_aberto'") && types.includes("'nf_entrada'") && drawer.includes("selection.type === 'nf_entrada'")],
]

for (const [name, valid] of checks) {
  if (!valid) throw new Error(`Falha: ${name}`)
  console.log(`OK ${name}`)
}
