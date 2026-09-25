export interface GestorRow {
  naturezaCodigo: string
  naturezaDescricao: string
  pcAberto: number
  nfEntrada: number
  contingenciaOk: number
  contingenciaEmAprovacao: number
  limiteOriginal: number
  saldoPrevisto: number
  saldoReal: number
}

export interface GestorPeriod {
  ano: number
  mes: number
}

export interface GestorResponse {
  periodo: GestorPeriod
  filial: string
  linhas: GestorRow[]
  quantidade: number
}

export interface GestorTimelinePoint {
  ano: number
  mes: number
  limiteOriginal: number
  nfEntrada: number
  saldoPrevisto: number
}

export type GestorDetailType =
  | 'pc_aberto'
  | 'nf_entrada'
  | 'contingencia_ok'
  | 'contingencia_aprovacao'

export interface GestorPcAbertoDetailRecord {
  pedido: string
  fornecedor: string
  fornecedorNome: string
  vencimento: string
  valor: number
}

export interface GestorNfEntradaDetailRecord {
  documento: string
  prefixo: string
  parcela: string
  fornecedor: string
  fornecedorNome: string
  loja: string
  emissao: string
  vencimento: string
  valor: number
}

export interface GestorContingenciaDetailRecord {
  pedido: string
  item: string
  vencimento: string
  usuario: string
  status: string
  valor: number
}

export interface GestorDetailResponse {
  ambiente: GestorDataEnvironment
  filial: string
  periodo: GestorPeriod
  naturezaCodigo: string
  naturezaDescricao: string
  tipo: GestorDetailType
  quantidade: number
  total: number
  registros: (
    | GestorPcAbertoDetailRecord
    | GestorNfEntradaDetailRecord
    | GestorContingenciaDetailRecord
  )[]
}

export interface GestorDetailSelection {
  row: GestorRow
  type: GestorDetailType
}

export type GestorDataEnvironment = 'dev' | 'hml' | 'prd'

export interface GestorEnvironmentOption {
  id: GestorDataEnvironment
  label: string
  available: boolean
}

export interface GestorEnvironmentsResponse {
  default: GestorDataEnvironment
  environments: GestorEnvironmentOption[]
}
