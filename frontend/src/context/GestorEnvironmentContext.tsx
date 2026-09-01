/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { getGestorEnvironments } from '../services/gestorService'
import type {
  GestorDataEnvironment,
  GestorEnvironmentOption,
} from '../types/gestor'
import { resolveInitialGestorEnvironment } from '../utils/environment'

interface GestorEnvironmentContextValue {
  environment: GestorDataEnvironment
  environments: readonly GestorEnvironmentOption[]
  setEnvironment: (environment: GestorDataEnvironment) => void
}

const GestorEnvironmentContext = createContext<
  GestorEnvironmentContextValue | undefined
>(undefined)

export function GestorEnvironmentProvider({ children }: { children: ReactNode }) {
  const [environment, setEnvironment] =
    useState<GestorDataEnvironment | null>(null)
  const [environments, setEnvironments] =
    useState<readonly GestorEnvironmentOption[]>([])
  const [discoveryError, setDiscoveryError] = useState(false)
  const [discoveryVersion, setDiscoveryVersion] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setDiscoveryError(false)
    getGestorEnvironments(controller.signal)
      .then((response) => {
        if (!controller.signal.aborted) {
          const initialEnvironment = resolveInitialGestorEnvironment(response)
          if (!initialEnvironment) {
            throw new Error('No available Gestor data environment.')
          }
          setEnvironments(response.environments)
          setEnvironment(initialEnvironment)
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setDiscoveryError(true)
        }
      })
    return () => controller.abort()
  }, [discoveryVersion])

  const value = useMemo(
    () =>
      environment ? { environment, environments, setEnvironment } : null,
    [environment, environments],
  )

  if (!value) {
    return (
      <main className="environment-discovery-state">
        {discoveryError ? (
          <>
            <h1>Ambientes indisponíveis</h1>
            <p>Não foi possível determinar uma fonte de dados segura.</p>
            <button
              type="button"
              onClick={() => setDiscoveryVersion((version) => version + 1)}
            >
              Tentar novamente
            </button>
          </>
        ) : (
          <>
            <h1>Gestor de Compras</h1>
            <p role="status">Verificando ambientes disponíveis...</p>
          </>
        )}
      </main>
    )
  }

  return (
    <GestorEnvironmentContext.Provider value={value}>
      {children}
    </GestorEnvironmentContext.Provider>
  )
}

export function useGestorEnvironment(): GestorEnvironmentContextValue {
  const context = useContext(GestorEnvironmentContext)
  if (!context) {
    throw new Error('GestorEnvironmentProvider is required.')
  }
  return context
}
