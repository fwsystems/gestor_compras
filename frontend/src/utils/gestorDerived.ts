import type { GestorRow } from '../types/gestor'

export function getGastoPrevisto(row: Pick<GestorRow, 'pcAberto' | 'nfEntrada'>): number {
  return row.pcAberto + row.nfEntrada
}
