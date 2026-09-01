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
