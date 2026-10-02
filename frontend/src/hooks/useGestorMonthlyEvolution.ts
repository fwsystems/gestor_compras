import { useCallback, useEffect, useMemo, useState } from 'react'

import { getGestor } from '../services/gestorService'
import type { GestorDataEnvironment, GestorPeriod, GestorResponse, GestorRow } from '../types/gestor'

export interface GestorMonthlyEvolutionPoint {
  periodo: GestorPeriod
  limiteOriginal: number
  pcAberto: number
  nfEntrada: number
  gastoPrevisto: number
  saldoPrevisto: number
  saldoReal: number
  percentualConsumido: number | null
  naturezas: GestorRow[]
}

interface MonthlyEvolutionState {
  key: string
  data: GestorMonthlyEvolutionPoint[]
  error: Error | null
  isLoading: boolean
}

const monthlyResponseCache = new Map<string, Promise<GestorResponse>>()

function cachedMonth(period: GestorPeriod, branch: string, environment: GestorDataEnvironment): Promise<GestorResponse> {
  const cacheKey = environment + '-' + branch + '-' + period.ano + '-' + period.mes
  const cached = monthlyResponseCache.get(cacheKey)
  if (cached) return cached
  const request = getGestor(period, branch, environment)
  monthlyResponseCache.set(cacheKey, request)
  return request
}

function aggregate(period: GestorPeriod, rows: GestorRow[]): GestorMonthlyEvolutionPoint {
  const totals = rows.reduce((current, row) => ({
    limiteOriginal: current.limiteOriginal + row.limiteOriginal,
    pcAberto: current.pcAberto + row.pcAberto,
    nfEntrada: current.nfEntrada + row.nfEntrada,
    saldoPrevisto: current.saldoPrevisto + row.saldoPrevisto,
    saldoReal: current.saldoReal + row.saldoReal,
  }), { limiteOriginal: 0, pcAberto: 0, nfEntrada: 0, saldoPrevisto: 0, saldoReal: 0 })
  return {
    periodo: period,
    ...totals,
    gastoPrevisto: totals.pcAberto + totals.nfEntrada,
    percentualConsumido: totals.limiteOriginal > 0 ? totals.nfEntrada / totals.limiteOriginal * 100 : null,
    naturezas: rows,
  }
}

export function useGestorMonthlyEvolution(
  periods: readonly GestorPeriod[],
  branch: string,
  environment: GestorDataEnvironment,
): { data: GestorMonthlyEvolutionPoint[]; error: Error | null; isLoading: boolean; reload: () => void } {
  const [requestVersion, setRequestVersion] = useState(0)
  const key = environment + '-' + branch + '-' + periods.map((period) => period.ano + '-' + period.mes).join(',') + '-' + requestVersion
  const [state, setState] = useState<MonthlyEvolutionState>({ key, data: [], error: null, isLoading: true })
  const reload = useCallback(() => setRequestVersion((version) => version + 1), [])
  const uniquePeriods = useMemo(() => {
    const seen = new Set<string>()
    return periods.filter((period) => {
      const periodKey = period.ano + '-' + period.mes
      if (seen.has(periodKey)) return false
      seen.add(periodKey)
      return true
    })
  }, [periods])

  useEffect(() => {
    const controller = new AbortController()
    setState({ key, data: [], error: null, isLoading: true })
    if (requestVersion > 0) uniquePeriods.forEach((period) => monthlyResponseCache.delete(environment + '-' + branch + '-' + period.ano + '-' + period.mes))
    Promise.all(uniquePeriods.map(async (period) => {
      const response = await cachedMonth(period, branch, environment)
      return aggregate(period, response.linhas)
    })).then((data) => {
      if (!controller.signal.aborted) setState({ key, data, error: null, isLoading: false })
    }).catch((requestError: unknown) => {
      if (controller.signal.aborted) return
      setState({ key, data: [], error: requestError instanceof Error ? requestError : new Error('Falha ao carregar a evolu\u00e7\u00e3o mensal.'), isLoading: false })
    })
    return () => controller.abort()
  }, [branch, environment, key, requestVersion, uniquePeriods])

  if (state.key !== key) return { data: [], error: null, isLoading: true, reload }
  return { ...state, reload }
}
