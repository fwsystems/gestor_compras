import { readFile } from 'node:fs/promises'

const [drawer, table, hook, types, styles, packageJson] = await Promise.all([
  readFile(new URL('../src/components/gestor/GestorDetailDrawer.tsx', import.meta.url), 'utf8'),
  readFile(new URL('../src/components/gestor/GestorTable.tsx', import.meta.url), 'utf8'),
  readFile(new URL('../src/hooks/useGestorDetail.ts', import.meta.url), 'utf8'),
  readFile(new URL('../src/types/gestor.ts', import.meta.url), 'utf8'),
  readFile(new URL('../src/styles.css', import.meta.url), 'utf8'),
  readFile(new URL('../package.json', import.meta.url), 'utf8'),
])
const nfTable = drawer.match(/selection\.type === 'nf_entrada'[\s\S]*?<\/table>/)?.[0] ?? ''

const checks = [
  ['usa o drawer existente', drawer.includes('export function GestorDetailDrawer')],
  ['cabeçalho identifica detalhamento financeiro', drawer.includes('Detalhamento financeiro')],
  ['título usa tipo amigável', drawer.includes('<h3 id="detail-title">{title}</h3>')],
  ['quatro tipos possuem nomes amigáveis', ['PC aberto', 'NF entrada', 'Contingência OK', 'Contingência em aprovação'].every((label) => drawer.includes(label))],
  ['Natureza exibe código e descrição', drawer.includes('selection.row.naturezaCodigo') && drawer.includes('selection.row.naturezaDescricao')],
  ['contexto exibe mês e ano', drawer.includes("month: 'long'") && drawer.includes("year: 'numeric'")],
  ['contexto exibe ambiente', drawer.includes('environment.toUpperCase()')],
  ['resumo destaca registros', drawer.includes('<dt>Registros</dt>') && drawer.includes('{data.quantidade}')],
  ['resumo destaca total', drawer.includes('<dt>Total</dt>') && drawer.includes('formatCurrency(data.total)')],
  ['PC exibe pedido, fornecedor, vencimento e valor', ['Pedido', 'Fornecedor', 'Vencimento', 'Valor'].every((label) => drawer.includes(`scope="col">${label}</th>`)) && drawer.includes('record.fornecedorNome')],
  ['NF exibe somente os seis campos definidos', ['Documento', 'Parcela', 'Nome do fornecedor', 'Emissão', 'Vencimento', 'Valor'].every((label) => nfTable.includes(`scope="col">${label}</th>`)) && ['Prefixo', 'Fornecedor', 'Loja'].every((label) => !nfTable.includes(`scope="col">${label}</th>`))],
  ['contingências preservam seis campos', ['Pedido', 'Item', 'Vencimento', 'Usuário', 'Status', 'Valor'].every((label) => drawer.includes(`scope="col">${label}</th>`))],
  ['datas usam padrão brasileiro', drawer.includes("/${value.slice(4, 6)}/${value.slice(0, 4)}")],
  ['valores usam formatador monetário existente', drawer.includes('formatCurrency(record.valor)')],
  ['valores monetários ficam à direita', styles.includes('.money-cell') && styles.includes('text-align: right')],
  ['cabeçalho da tabela é sticky', styles.includes('.detail-table th') && styles.includes('position: sticky') && styles.includes('top: 0')],
  ['overflow vertical e horizontal é interno', styles.includes('.detail-table-scroll') && styles.includes('overflow: auto')],
  ['drawer permanece contido na viewport', styles.includes('max-width: 100vw') && styles.includes('height: 100dvh') && styles.includes('overflow: hidden')],
  ['loading, erro e retry permanecem', drawer.includes('isLoading ?') && drawer.includes('error ?') && drawer.includes('onClick={onRetry}')],
  ['fechar, Escape e foco permanecem', drawer.includes('onClick={onClose}') && drawer.includes("event.key === 'Escape'") && drawer.includes('previousFocus?.focus()')],
  ['AbortController e resposta obsoleta permanecem', hook.includes('new AbortController()') && hook.includes('controller.signal.aborted') && hook.includes('requestKey')],
  ['quatro totais preservam invariância', ['pcAberto', 'nfEntrada', 'contingenciaOk', 'contingenciaEmAprovacao'].every((field) => hook.includes(`selection.row.${field}`))],
  ['zero permanece não clicável', table.includes('detail && row[field] !== 0')],
  ['gatilho preserva hover, foco e cursor', styles.includes('.detail-trigger:hover') && styles.includes('.detail-trigger:focus-visible') && styles.includes('cursor: pointer')],
  ['contrato preserva os quatro tipos', ['pc_aberto', 'nf_entrada', 'contingencia_ok', 'contingencia_aprovacao'].every((type) => types.includes(`'${type}'`))],
  ['validação ET-027 registrada no npm', packageJson.includes('"validate:detail-interface"')],
]

for (const [name, valid] of checks) {
  if (!valid) throw new Error(`Falha: ${name}`)
  console.log(`OK ${name}`)
}
