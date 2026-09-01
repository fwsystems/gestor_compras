import { readFile } from 'node:fs/promises'

const [drawer, hook, types, styles] = await Promise.all([
  readFile(new URL('../src/components/gestor/GestorDetailDrawer.tsx', import.meta.url), 'utf8'),
  readFile(new URL('../src/hooks/useGestorDetail.ts', import.meta.url), 'utf8'),
  readFile(new URL('../src/types/gestor.ts', import.meta.url), 'utf8'),
  readFile(new URL('../src/styles.css', import.meta.url), 'utf8'),
])

const checks = [
  ['contrato preserva código do fornecedor', types.includes('fornecedor: string')],
  ['contrato inclui nome do fornecedor', types.includes('fornecedorNome: string')],
  ['contrato inclui emissão', types.includes('emissao: string')],
  ['drawer exibe código do fornecedor', drawer.includes("record.fornecedor || '—'")],
  ['drawer exibe nome do fornecedor', drawer.includes('record.fornecedorNome')],
  ['nome ausente usa fallback neutro', drawer.includes("record.fornecedorNome || '—'")],
  ['drawer exibe emissão formatada', drawer.includes('formatProtheusDate(record.emissao)')],
  ['drawer preserva vencimento', drawer.includes('formatProtheusDate(record.vencimento)')],
  ['drawer preserva quantidade', drawer.includes('data.quantidade')],
  ['drawer preserva total', drawer.includes('formatCurrency(data.total)')],
  ['drawer preserva loading', drawer.includes('isLoading')],
  ['drawer preserva erro', drawer.includes('error ?')],
  ['drawer preserva retry', drawer.includes('onClick={onRetry}')],
  ['drawer preserva fechamento', drawer.includes('onClick={onClose}')],
  ['drawer preserva Escape', drawer.includes("event.key === 'Escape'")],
  ['drawer preserva overflow interno', styles.includes('.detail-table-scroll') && styles.includes('overflow: auto')],
  ['troca de ambiente invalida consulta', hook.includes('${environment}-${period.ano}-${period.mes}')],
  ['troca de período invalida consulta', hook.includes('period, requestKey, selection')],
  ['resposta obsoleta permanece abortável', hook.includes('new AbortController()') && hook.includes('controller.abort()')],
]

for (const [name, valid] of checks) {
  if (!valid) throw new Error(`Falha: ${name}`)
  console.log(`OK ${name}`)
}
