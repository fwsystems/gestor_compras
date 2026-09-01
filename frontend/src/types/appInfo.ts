import type { AppEnvironment } from '../config/env'

export interface AppInfo {
  application: string
  environment: AppEnvironment
  version: string
}
