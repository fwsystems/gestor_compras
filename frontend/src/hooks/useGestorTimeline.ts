import { useCallback, useEffect, useState } from 'react'

import { getGestorTimeline } from '../services/gestorService'
import type { GestorDataEnvironment, GestorPeriod, GestorTimelinePoint } from '../types/gestor'

export function useGestorTimeline(period: GestorPeriod, branch: string, environment: GestorDataEnvironment) {
  const [version, setVersion] = useState(0)
  const [state, setState] = useState<{ key: string; data: GestorTimelinePoint[] | null; error: Error | null; isLoading: boolean }>({ key: '', data: null, error: null, isLoading: true })
  const key = `${environment}-${period.ano}-${period.mes}-${branch}-${version}`
  const reload = useCallback(() => setVersion((current) => current + 1), [])
  useEffect(() => {
    const controller = new AbortController()
    setState({ key, data: null, error: null, isLoading: true })
    getGestorTimeline(period, branch, environment, controller.signal).then((data) => {
      if (!controller.signal.aborted) setState({ key, data, error: null, isLoading: false })
    }).catch((reason: unknown) => {
      if (controller.signal.aborted || (reason instanceof DOMException && reason.name === 'AbortError')) return
      setState({ key, data: null, error: reason instanceof Error ? reason : new Error('Falha ao carregar evolução temporal.'), isLoading: false })
    })
    return () => controller.abort()
  }, [branch, environment, key, period])
  return state.key === key ? { ...state, reload } : { data: null, error: null, isLoading: true, reload }
}
