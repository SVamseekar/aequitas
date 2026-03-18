interface Props {
  chartData: Record<string, unknown>
}

export function DataTable({ chartData }: Props) {
  const rawData = chartData.data ?? chartData.groups ?? chartData.features ?? []
  const data = Array.isArray(rawData) ? (rawData as Record<string, unknown>[]) : []

  if (data.length === 0) {
    return <p className="text-muted-foreground text-sm">No data available</p>
  }

  const columns = Object.keys(data[0])

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm border border-border">
        <thead>
          <tr className="bg-muted">
            {columns.map((col) => (
              <th key={col} className="px-3 py-2 text-left font-medium text-foreground border-b border-border">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.slice(0, 100).map((row, i) => (
            <tr key={i} className="border-b border-border hover:bg-muted/50 transition-colors">
              {columns.map((col) => (
                <td key={col} className="px-3 py-2 text-muted-foreground">
                  {String(row[col] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length > 100 && (
        <p className="text-xs text-muted-foreground mt-1">Showing first 100 of {data.length} rows</p>
      )}
    </div>
  )
}
