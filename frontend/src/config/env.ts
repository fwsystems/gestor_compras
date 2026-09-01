export type AppEnvironment = 'dev' | 'hml' | 'prd'

const allowedEnvironments: readonly AppEnvironment[] = ['dev', 'hml', 'prd']

function requiredValue(value: string | undefined, fallback: string, name: string) {
  const resolved = value?.trim() || fallback
  if (!resolved) {
    throw new Error(`A variável ${name} é obrigatória.`)
  }
  return resolved
}

function parseEnvironment(value: string | undefined): AppEnvironment {
  const resolved = requiredValue(value, 'dev', 'VITE_APP_ENV')
  if (!allowedEnvironments.includes(resolved as AppEnvironment)) {
    throw new Error(
      `VITE_APP_ENV inválido: "${resolved}". Use dev, hml ou prd.`,
    )
  }
  return resolved as AppEnvironment
}

function parseApiBaseUrl(value: string | undefined): string {
  const resolved = value?.trim()
  if (!resolved) return ''
  const url = new URL(resolved)
  if (!['http:', 'https:'].includes(url.protocol)) {
    throw new Error('VITE_API_BASE_URL deve usar HTTP ou HTTPS.')
  }
  return resolved.replace(/\/$/, '')
}

export const env = Object.freeze({
  appName: requiredValue(
    import.meta.env.VITE_APP_NAME,
    'Gestor de Compras Web',
    'VITE_APP_NAME',
  ),
  appVersion: requiredValue(
    import.meta.env.VITE_APP_VERSION,
    '0.1.0',
    'VITE_APP_VERSION',
  ),
  appEnvironment: parseEnvironment(import.meta.env.VITE_APP_ENV),
  apiBaseUrl: parseApiBaseUrl(import.meta.env.VITE_API_BASE_URL),
})
