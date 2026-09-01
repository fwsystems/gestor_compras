import { useCallback, useEffect, useState } from 'react'

import { getGestorDetails } from '../services/gestorService'
import type {
  GestorDataEnvironment,
  GestorDetailResponse,
  GestorDetailSelection,
  GestorPeriod,
} from '../types/gestor'

interface DetailState {
  requestKey: string
  data: GestorDetailResponse | null
  error: Error | null
  isLoading: boolean
}

const idleState: DetailState = {
  requestKey: '',
  data: null,
  error: null,
  isLoading: false,
}

export function useGestorDetail(
  selection: GestorDetailSelection | null,
  period: GestorPeriod,
  branch: string,
  environment: GestorDataEnvironment,
  interval?: { inicio: string; fim: string } | null,
) {
  const inicio = interval?.inicio
  const fim = interval?.fim
  const [requestVersion, setRequestVersion] = useState(0)
  const [state, setState] = useState<DetailState>(idleState)
  const expectedTotal = selection
    ? {
        pc_aberto: selection.row.pcAberto,
        nf_entrada: selection.row.nfEntrada,
        contingencia_ok: selection.row.contingenciaOk,
        contingencia_aprovacao: selection.row.contingenciaEmAprovacao,
      }[selection.type]
    : 0
  const requestKey = selection
    ? `${environment}-${period.ano}-${period.mes}-${branch}-${inicio ?? ''}-${fim ?? ''}-${selection.row.naturezaCodigo}-${selection.type}-${requestVersion}`
    : ''

  const retry = useCallback(() => {
    setRequestVersion((version) => version + 1)
  }, [])

  useEffect(() => {
    if (!selection) {
      setState(idleState)
      return
    }
    const controller = new AbortController()
    setState({ requestKey, data: null, error: null, isLoading: true })
    getGestorDetails(
      period,
      branch,
      environment,
      selection.row.naturezaCodigo,
      selection.type,
      inicio && fim ? { inicio, fim } : null,
      controller.signal,
    )
      .then((response) => {
        if (controller.signal.aborted) return
        if (
          (expectedTotal !== 0 && response.quantidade === 0) ||
          Math.abs(response.total - expectedTotal) > 0.005
        ) {
          throw new Error(
            'InconsistÃªncia: o detalhe nÃ£o confere com o valor consolidado.',
          )
        }
        setState({ requestKey, data: response, error: null, isLoading: false })
      })
      .catch((requestError: unknown) => {
        if (
          controller.signal.aborted ||
          (requestError instanceof DOMException && requestError.name === 'AbortError')
        ) return
        setState({
          requestKey,
          data: null,
          error: requestError instanceof Error
            ? requestError
            : new Error('Falha desconhecida ao consultar o detalhamento.'),
          isLoading: false,
        })
      })
    return () => controller.abort()
  }, [branch, environment, expectedTotal, fim, inicio, period, requestKey, selection])

  if (!selection) return { ...idleState, retry }
  if (state.requestKey !== requestKey) {
    return { requestKey, data: null, error: null, isLoading: true, retry }
  }
  return { ...state, retry }
}
