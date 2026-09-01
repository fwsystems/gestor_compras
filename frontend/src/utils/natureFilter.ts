import type { GestorRow } from '../types/gestor'

function normalizeSearch(value: string): string {
  return value.trim().toLocaleLowerCase('pt-BR')
}

export function filterGestorRows(
  rows: readonly GestorRow[],
  search: string,
): GestorRow[] {
  const normalizedSearch = normalizeSearch(search)
  if (!normalizedSearch) {
    return [...rows]
  }

  return rows.filter(
    (row) =>
      row.naturezaCodigo.toLocaleLowerCase('pt-BR').includes(normalizedSearch) ||
      row.naturezaDescricao
        .toLocaleLowerCase('pt-BR')
        .includes(normalizedSearch),
  )
}

export function hasNatureSearch(search: string): boolean {
  return normalizeSearch(search).length > 0
}
