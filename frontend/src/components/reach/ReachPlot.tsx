import { useEffect, useRef } from 'react'
import * as Plot from '@observablehq/plot'
import { useChartWidth } from '@/hooks/useChartWidth'
import type { ReachBandRow, ReachResponse } from '@/api/types'

export function ReachHistogram({ rows, unit, areaNoun }: { rows: ReachResponse['histogram']; unit: string; areaNoun: string }) {
  const container = useRef<HTMLDivElement>(null), target = useRef<HTMLDivElement>(null)
  const width = useChartWidth(container, 450)
  useEffect(() => {
    if (!target.current || !rows.length) return
    const chart = Plot.plot({ width, height: 265, marginLeft: 58, marginBottom: 72, x: { label: unit, tickRotate: -25 }, y: { label: `Number of ${areaNoun}`, grid: true }, marks: [Plot.barY(rows, { x: 'bin', y: 'n', fill: '#7d9967', tip: true, title: row => `${row.bin} destinations: ${row.n.toLocaleString('en-GB')} ${areaNoun}` }), Plot.ruleY([0])] })
    target.current.replaceChildren(chart)
    return () => chart.remove()
  }, [rows, unit, areaNoun, width])
  return <div ref={container}><div ref={target} role='img' aria-label={`Distribution of ${unit.toLowerCase()} across ${areaNoun}`} /></div>
}

export function ReachHeatmap({ rows, indexLabel }: { rows: ReachBandRow[]; indexLabel: string }) {
  const container = useRef<HTMLDivElement>(null), target = useRef<HTMLDivElement>(null)
  const width = useChartWidth(container, 700)
  useEffect(() => {
    if (!target.current) return
    const linked = rows.filter(row => row.imd_decile >= 1 && row.imd_decile <= 10)
    const chart = Plot.plot({ width, height: 245, marginLeft: 65, marginBottom: 46,
      x: { label: `${indexLabel} decile (1 = most deprived)`, domain: [1,2,3,4,5,6,7,8,9,10] }, y: { label: 'Reach band', domain: [1,2,3,4,5,6] },
      color: { scheme: 'YlOrRd', legend: true, label: 'People', domain: [0, Math.max(1, ...linked.map(row => row.people))] },
      marks: [Plot.cell(linked, { x: 'imd_decile', y: 'band', fill: 'people', inset: 1, tip: true, title: row => `Band ${row.band} · decile ${row.imd_decile}\n${row.people.toLocaleString('en-GB')} people · ${row.n_areas.toLocaleString('en-GB')} areas` })] })
    target.current.replaceChildren(chart)
    return () => chart.remove()
  }, [rows, indexLabel, width]) // rows are the stable API payload
  return <div ref={container} data-testid='band-decile-heatmap'><div ref={target} role='img' aria-label={`Population by reach band and ${indexLabel} decile`} /></div>
}
