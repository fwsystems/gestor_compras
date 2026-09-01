import { useEffect, useState } from 'react'

import { getAppInfo } from '../services/appService'
import type { AppInfo } from '../types/appInfo'

interface UseAppInfoResult {
  data: AppInfo | null
  error: Error | null
  isLoading: boolean
}

export function useAppInfo(): UseAppInfoResult {
  const [data, setData] = useState<AppInfo | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const controller = new AbortController()

    getAppInfo(controller.signal)
      .then((appInfo) => {
        setData(appInfo)
        setError(null)
      })
      .catch((requestError: unknown) => {
        if (requestError instanceof DOMException && requestError.name === 'AbortError') {
          return
        }
        setError(
          requestError instanceof Error
            ? requestError
            : new Error('Falha desconhecida ao consultar a API.'),
        )
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      })

    return () => controller.abort()
  }, [])

  return { data, error, isLoading }
}
