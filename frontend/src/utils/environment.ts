import type {
  GestorDataEnvironment,
  GestorEnvironmentsResponse,
} from '../types/gestor'

export function resolveInitialGestorEnvironment(
  response: GestorEnvironmentsResponse,
): GestorDataEnvironment | null {
  const selected = response.environments.find(
    (option) => option.id === response.default && option.available,
  )
  return selected?.id ?? null
}

export function resolveGestorEnvironmentSelection(
  current: GestorDataEnvironment,
  requested: GestorDataEnvironment,
  productionConfirmed: boolean,
): GestorDataEnvironment {
  if (requested === 'prd' && !productionConfirmed) return current
  return requested
}
