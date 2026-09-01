import type { ReactNode } from 'react'

export type DashboardIconName = 'wallet' | 'clipboard' | 'cart' | 'shield' | 'hourglass' | 'trend' | 'pie' | 'gauge'

export function DashboardIcon({ name }: { name: DashboardIconName }) {
  const paths: Record<DashboardIconName, ReactNode> = {
    wallet: <><path d="M3.5 7.5h15v10h-15z" /><path d="M5.5 7.5V5.75A1.75 1.75 0 0 1 7.25 4h9.25v3.5" /><path d="M15 12.5h3.5" /></>,
    clipboard: <><rect x="5" y="4" width="14" height="17" rx="2" /><path d="M9 4.5V3h6v1.5M9 10h6M9 14h6" /></>,
    cart: <><path d="M3 4h2l2 11h10l2-8H6" /><circle cx="9" cy="19" r="1" /><circle cx="17" cy="19" r="1" /></>,
    shield: <><path d="M12 3.5 19 6v5.25c0 4.2-2.8 7.3-7 9.25-4.2-1.95-7-5.05-7-9.25V6z" /><path d="m8.75 12 2 2 4.5-4.5" /></>,
    hourglass: <><path d="M6 3.5h12M6 20.5h12M7.5 3.5c0 4 1.5 5.5 4.5 8-3 2.5-4.5 4-4.5 9M16.5 3.5c0 4-1.5 5.5-4.5 8 3 2.5 4.5 4 4.5 9" /></>,
    trend: <><path d="M4 18.5V5.5M4 18.5h16" /><path d="m6.5 15 4-4 3 2 4.5-5" /><path d="M15 8h3v3" /></>,
    pie: <><path d="M12 3.5v8.5h8.5A8.5 8.5 0 0 0 12 3.5Z" /><path d="M10 5.75A8.5 8.5 0 1 0 18.25 14H10Z" /></>,
    gauge: <><path d="M4 16a8 8 0 1 1 16 0" /><path d="m12 16 4-5" /><path d="M6 16h.01M18 16h.01" /></>,
  }
  return <svg className="dashboard-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
}
