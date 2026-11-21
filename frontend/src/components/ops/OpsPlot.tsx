import { useEffect, useRef } from 'react'
import * as Plot from '@observablehq/plot'
import { useChartWidth } from '@/hooks/useChartWidth'

export function OpsPlot({ rows, label }: { rows: { name: string; n_updates: number }[]; label: string }) {
  const container = useRef<HTMLDivElement>(null), target = useRef<HTMLDivElement>(null)
  const width = useChartWidth(container, 650)
  useEffect(() => {
    if (!target.current || !rows.length) return
    const chart = Plot.plot({ width, height: 300, marginLeft: 56, marginBottom: 75, marginTop: 30,
      x: { label: null, tickRotate: -20 }, y: { label: 'Number of updates', grid: true },
      marks: [Plot.barY(rows, { x: 'name', y: 'n_updates', fill: '#76a4bb', tip: true, title: row => `${row.name}: ${row.n_updates.toLocaleString('en-GB')} updates` }), Plot.text(rows, { x: 'name', y: 'n_updates', text: row => row.n_updates.toLocaleString('en-GB'), dy: -8, fontSize: 10 }), Plot.ruleY([0])] })
    target.current.replaceChildren(chart)
    return () => chart.remove()
  }, [rows, width])
  return <div ref={container}><div role='img' aria-label={label} ref={target} /></div>
}
