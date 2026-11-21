import { useEffect, useRef } from 'react'
import * as Plot from '@observablehq/plot'
import { useChartWidth } from '@/hooks/useChartWidth'
import { CATEGORICAL } from '@/lib/colours'

interface Row { name: string; population: number | null; cost: number | null; co2: number | null }
type Metric = 'population' | 'cost' | 'co2'

function shortName(name: string) {
  if (name.startsWith('Frequency restoration')) return 'Frequency\nrestoration'
  if (name.startsWith('Last bus')) return 'Evening service'
  if (name.startsWith('DRT')) return 'Rural DRT'
  if (name.startsWith('Bus Services Act')) return 'Franchise'
  return name.length > 20 ? `${name.slice(0, 19)}…` : name
}

export function ScenarioPlot({ rows, metric, unit }: { rows: Row[]; metric: Metric; unit: string }) {
  const container = useRef<HTMLDivElement>(null)
  const target = useRef<HTMLDivElement>(null)
  const width = useChartWidth(container, 260)
  useEffect(() => {
    if (!target.current) return
    const data = rows.flatMap(row => row[metric] === null ? [] : [{
      ...row, value: row[metric], position: row[metric] / (metric === 'population' ? 1_000_000 : 1),
    }])
    const chart = Plot.plot({
      width, height: 220, marginLeft: 86, marginRight: 42, marginTop: 12, marginBottom: 40,
      x: { zero: true, label: unit, ticks: 3 },
      y: { domain: rows.map(row => row.name), label: null, tickFormat: shortName, tickSize: 0 },
      color: { domain: rows.map(row => row.name), range: [...CATEGORICAL] },
      marks: [
        Plot.ruleX([0], { stroke: '#c5c0b8' }),
        Plot.barX(data, { x: 'position', y: 'name', fill: metric === 'co2' ? '#dd7138' : 'name',
          tip: true, title: row => `${row.name}\n${row.value.toLocaleString('en-GB', { maximumFractionDigits: 1 })} ${metric === 'population' ? 'people' : unit}` }),
        Plot.text(data, { x: 'position', y: 'name', text: row => metric === 'population' ? `${row.position.toFixed(2)}m` : row.value.toLocaleString('en-GB', { maximumFractionDigits: 1 }), dx: 4, textAnchor: 'start', fontSize: 10 }),
      ],
    })
    target.current.replaceChildren(chart)
    return () => chart.remove()
  }, [rows, metric, unit, width])
  return <div ref={container}><div ref={target} role='img' aria-label={`Scenario ${metric} comparison`} /></div>
}
