import type { AppInfo } from '../types/appInfo'
import { apiRequest } from './httpClient'

export function getAppInfo(signal?: AbortSignal): Promise<AppInfo> {
  return apiRequest<AppInfo>('/api/info', { signal })
}
