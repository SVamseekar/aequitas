/** Download observed values locally; null fields remain empty. */
export function downloadCsv(filename: string, columns: string[], rows: (string | number | null | undefined)[][]) {
  const quote = (value: string | number | null | undefined) => `"${String(value ?? '').replace(/"/g, '""')}"`
  const body = [columns, ...rows].map(row => row.map(quote).join(',')).join('\n')
  const href = URL.createObjectURL(new Blob([body], { type: 'text/csv;charset=utf-8' }))
  const anchor = document.createElement('a'); anchor.href = href; anchor.download = filename; anchor.click()
  window.setTimeout(() => URL.revokeObjectURL(href), 1000)
}
