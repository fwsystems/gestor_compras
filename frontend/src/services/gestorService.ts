import { apiRequest } from './httpClient'
import type {
  GestorDataEnvironment,
  GestorDetailResponse,
  GestorDetailType,
  GestorEnvironmentsResponse,
  GestorPeriod,
  GestorResponse,
  GestorTimelinePoint,
} from '../types/gestor'

export async function getGestor(
  period: GestorPeriod,
  branch: string,
  environment: GestorDataEnvironment,
  interval?: { inicio: string; fim: string } | null,
  signal?: AbortSignal,
): Promise<GestorResponse> {
  const query = new URLSearchParams({
    ano: String(period.ano),
    mes: String(period.mes),
    filial: branch,
    ambiente: environment,
  })
  if (interval) {
    query.set('inicio', interval.inicio)
    query.set('fim', interval.fim)
  }
  const response = await apiRequest<GestorResponse>(`/api/gestor?${query}`, {
    signal,
  })

  if (response.quantidade !== response.linhas.length) {
    throw new Error('A API retornou uma quantidade incompatível com as linhas.')
  }

  if (!Number.isFinite(response.pago) || !Number.isFinite(response.aPagar) || !Number.isFinite(response.total)) {
    throw new Error('A API não retornou os campos de pagamentos no contrato do Gestor.')
  }
  const invalidPaymentRow = response.linhas.find(
    (row) => !Number.isFinite(row.pago) || !Number.isFinite(row.aPagar) || !Number.isFinite(row.total)
      || Math.abs(row.total - (row.pago + row.aPagar)) > 0.005,
  )
  if (invalidPaymentRow) {
    throw new Error(
      `A API não retornou pagamento válido para a Natureza ${invalidPaymentRow.naturezaCodigo}.`,
    )
  }

  const rowPaymentTotals = response.linhas.reduce(
    (totals, row) => ({
      pago: totals.pago + row.pago,
      aPagar: totals.aPagar + row.aPagar,
      total: totals.total + row.total,
    }),
    { pago: 0, aPagar: 0, total: 0 },
  )
  if (
    Math.abs(rowPaymentTotals.pago - response.pago) > 0.005
    || Math.abs(rowPaymentTotals.aPagar - response.aPagar) > 0.005
    || Math.abs(rowPaymentTotals.total - response.total) > 0.005
    || Math.abs(response.total - (response.pago + response.aPagar)) > 0.005
  ) {
    throw new Error('A API retornou totais de pagamentos inconsistentes com as rows do Gestor.')
  }

  return response
}

export async function getGestorEnvironments(
  signal?: AbortSignal,
): Promise<GestorEnvironmentsResponse> {
  return apiRequest<GestorEnvironmentsResponse>('/api/gestor/environments', {
    signal,
  })
}

export async function getGestorTimeline(
  period: GestorPeriod,
  branch: string,
  environment: GestorDataEnvironment,
  signal?: AbortSignal,
): Promise<GestorTimelinePoint[]> {
  const query = new URLSearchParams({ ano: String(period.ano), mes: String(period.mes), filial: branch, ambiente: environment })
  return apiRequest<GestorTimelinePoint[]>(`/api/gestor/timeline?${query}`, { signal })
}

export async function getGestorDetails(
  period: GestorPeriod,
  branch: string,
  environment: GestorDataEnvironment,
  nature: string,
  type: GestorDetailType,
  interval?: { inicio: string; fim: string } | null,
  signal?: AbortSignal,
): Promise<GestorDetailResponse> {
  const query = new URLSearchParams({
    ano: String(period.ano),
    mes: String(period.mes),
    filial: branch,
    ambiente: environment,
    natureza: nature,
    tipo: type,
  })
  if (interval) {
    query.set('inicio', interval.inicio)
    query.set('fim', interval.fim)
  }
  const response = await apiRequest<GestorDetailResponse>(
    `/api/gestor/details?${query}`,
    { signal },
  )
  const calculatedTotal = response.registros.reduce(
    (total, record) => total + record.valor,
    0,
  )
  if (
    response.quantidade !== response.registros.length ||
    Math.abs(calculatedTotal - response.total) > 0.005
  ) {
    throw new Error('O detalhamento retornado pela API estÃ¡ inconsistente.')
  }
  return response
}
