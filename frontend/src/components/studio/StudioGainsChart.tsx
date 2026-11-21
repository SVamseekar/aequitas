import { useEffect, useRef } from 'react'
import * as Plot from '@observablehq/plot'
import { useChartWidth } from '@/hooks/useChartWidth'

export interface DecileRow { decile: number; gained: number | null; lost: number | null }
export default function StudioGainsChart({ rows }: { rows: DecileRow[] }) {
  const container = useRef<HTMLDivElement>(null)
  const plot = useRef<HTMLDivElement>(null)
  const width = useChartWidth(container, 500)
  useEffect(() => {
    if (!plot.current) return
    const data = rows.flatMap(row => row.gained === null || row.lost === null ? [] : [
      { decile: String(row.decile), people: row.gained, change: 'Gained access' },
      { decile: String(row.decile), people: -row.lost, change: 'Lost access' },
    ])
    if (!data.length) { plot.current.replaceChildren(); return }
    const chart = Plot.plot({
      width, height: 310, marginLeft: 35, marginBottom: 50,
      x: { label: 'People gaining (right) / losing (left) access', grid: true },
      y: { label: 'Decile', domain: rows.map(row => String(row.decile)) },
      color: { domain: ['Lost access', 'Gained access'], range: ['#cf7759', '#70965e'], legend: true },
      marks: [Plot.barX(data, { x: 'people', y: 'decile', fill: 'change', tip: true }), Plot.ruleX([0])],
    })
    plot.current.replaceChildren(chart)
    return () => chart.remove()
  }, [rows, width])
  return <div ref={container}>{rows.some(row => row.gained !== null) ? <div ref={plot} role='img' aria-label='People gaining and losing stop access by in-country decile' /> : <div className='studio-empty studio-chart-empty'>Values populate after calculation.<br />No computed decile comparison yet.</div>}</div>
}
