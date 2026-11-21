export const REACH_DESTINATIONS = [{ id: 'jobs', label: 'Jobs', unit: 'Employment destination points (proxy)' }, { id: 'gp', label: 'GP', unit: 'GP destinations' }, { id: 'school', label: 'School', unit: 'School destinations' }] as const
export const REACH_CUTOFFS = [15, 30, 45] as const
export function reachSelection(params: URLSearchParams) {
  const dest = REACH_DESTINATIONS.find(item => item.id === params.get('dest')) ?? REACH_DESTINATIONS[0]
  const raw = Number(params.get('cutoff') ?? 45)
  return { dest, cutoff: REACH_CUTOFFS.includes(raw as 15 | 30 | 45) ? raw : 45 }
}
export function downloadReachCsv(filename: string, columns: string[], rows: (string | number | null | undefined)[][]) {
  const quote = (value: string | number | null | undefined) => `"${String(value ?? '').replace(/"/g, '""')}"`
  const body = [columns, ...rows].map(row => row.map(quote).join(',')).join('\n')
  const href = URL.createObjectURL(new Blob([body], { type: 'text/csv;charset=utf-8' }))
  const anchor = document.createElement('a'); anchor.href = href; anchor.download = filename; anchor.click()
  window.setTimeout(() => URL.revokeObjectURL(href), 1000)
}
