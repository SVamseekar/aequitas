interface Props {
  chartData: Record<string, unknown>
}

export function DataTable({ chartData }: Props) {
  const rawData = chartData.data ?? chartData.groups ?? chartData.features ?? []
  const data = Array.isArray(rawData) ? (rawData as Record<string, unknown>[]) : []

  if (data.length === 0) {
    return <p className="text-gray-400 text-sm">No data available</p>
  }

  const columns = Object.keys(data[0])

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm border border-gray-200">
        <thead>
          <tr className="bg-gray-50">
            {columns.map((col) => (
              <th key={col} className="px-3 py-2 text-left font-medium text-gray-700 border-b">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.slice(0, 100).map((row, i) => (
            <tr key={i} className="border-b">
              {columns.map((col) => (
                <td key={col} className="px-3 py-2 text-gray-600">
                  {String(row[col] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length > 100 && (
        <p className="text-xs text-gray-400 mt-1">Showing first 100 of {data.length} rows</p>
      )}
    </div>
  )
}
