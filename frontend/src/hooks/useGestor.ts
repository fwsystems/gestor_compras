import { useCallback, useEffect, useState } from 'react'

import { getGestor } from '../services/gestorService'
import type {
  GestorDataEnvironment,
  GestorPeriod,
  GestorResponse,
} from '../types/gestor'

interface UseGestorResult {
  data: GestorResponse | null
  error: Error | null
  isLoading: boolean
  reload: () => void
}

interface GestorRequestState {
  requestKey: string
  data: GestorResponse | null
  error: Error | null
  isLoading: boolean
}

export function useGestor(
  period: GestorPeriod,
  branch: string,
  environment: GestorDataEnvironment,
  interval?: { inicio: string; fim: string } | null,
): UseGestorResult {
  const { ano, mes } = period
  const inicio = interval?.inicio
  const fim = interval?.fim
  const [requestVersion, setRequestVersion] = useState(0)
  const requestKey = `${environment}-${ano}-${mes}-${branch}-${inicio ?? ''}-${fim ?? ''}-${requestVersion}`
  const [requestState, setRequestState] = useState<GestorRequestState>({
    requestKey,
    data: null,
    error: null,
    isLoading: true,
  })

  const reload = useCallback(() => {
    setRequestVersion((currentVersion) => currentVersion + 1)
  }, [])

  useEffect(() => {
    const controller = new AbortController()

    setRequestState({
      requestKey,
      data: null,
      error: null,
      isLoading: true,
    })

    getGestor(
      { ano, mes },
      branch,
      environment,
      inicio && fim ? { inicio, fim } : null,
      controller.signal,
    )
      .then((response) => {
        if (!controller.signal.aborted) {
          setRequestState({
            requestKey,
            data: response,
            error: null,
            isLoading: false,
          })
        }
      })
      .catch((requestError: unknown) => {
        if (
          controller.signal.aborted ||
          (requestError instanceof DOMException &&
            requestError.name === 'AbortError')
        ) {
          return
        }

        setRequestState({
          requestKey,
          data: null,
          error:
            requestError instanceof Error
              ? requestError
              : new Error('Falha desconhecida ao consultar a API.'),
          isLoading: false,
        })
      })

    return () => controller.abort()
  }, [ano, branch, environment, fim, inicio, mes, requestKey])

  if (requestState.requestKey !== requestKey) {
    return { data: null, error: null, isLoading: true, reload }
  }

  return { ...requestState, reload }
}
