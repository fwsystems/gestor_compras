import type { GestorRow } from '../types/gestor'
import { getGastoPrevisto } from './gestorDerived'

export type GestorSortField =
  | 'natureza'
  | 'pcAberto'
  | 'nfEntrada'
  | 'contingenciaOk'
  | 'contingenciaEmAprovacao'
  | 'limiteOriginal'
  | 'gastoPrevisto'
  | 'saldoPrevisto'
  | 'saldoReal'

export type GestorSortDirection = 'ascending' | 'descending'

export interface GestorSort {
  field: GestorSortField
  direction: GestorSortDirection
}

export function sortGestorRows(
  rows: readonly GestorRow[],
  sort: GestorSort | null,
): GestorRow[] {
  if (!sort) return [...rows]
  const multiplier = sort.direction === 'ascending' ? 1 : -1
  return [...rows].sort((left, right) => {
    if (sort.field === 'natureza') {
      const byCode = left.naturezaCodigo.localeCompare(right.naturezaCodigo, 'pt-BR', {
        numeric: true,
      })
      return multiplier * (byCode || left.naturezaDescricao.localeCompare(right.naturezaDescricao, 'pt-BR'))
    }
    const leftValue = sort.field === 'gastoPrevisto' ? getGastoPrevisto(left) : left[sort.field]
    const rightValue = sort.field === 'gastoPrevisto' ? getGastoPrevisto(right) : right[sort.field]
    return multiplier * (leftValue - rightValue)
  })
}

export function toggleGestorSort(
  current: GestorSort | null,
  field: GestorSortField,
): GestorSort {
  return current?.field === field
    ? { field, direction: current.direction === 'ascending' ? 'descending' : 'ascending' }
    : { field, direction: 'ascending' }
}
