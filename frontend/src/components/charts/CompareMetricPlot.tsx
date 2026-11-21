import { useEffect, useRef } from 'react'
import * as Plot from '@observablehq/plot'
import { useChartWidth } from '@/hooks/useChartWidth'
import type { CompareMetricId } from '@/lib/compareLabels'
import { compareDefinitions } from '@/lib/compareData'

interface Props { id: CompareMetricId; left: number | null; right: number | null; nameA: string; nameB: string }
export default function CompareMetricPlot({ id, left, right, nameA, nameB }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const plot = useRef<HTMLDivElement>(null)
  const width = useChartWidth(container, 500)
  useEffect(() => {
    if (!plot.current) return
    const data = [{ value: left, region: nameA, color: '#c6582b' }, { value: right, region: nameB, color: '#759765' }].filter((item): item is { value: number; region: string; color: string } => item.value !== null && Number.isFinite(item.value))
    if (!data.length) { plot.current.replaceChildren(); return }
    const maximum = id === 'gini' ? 1 : id === 'jobs_45' ? Math.max(...data.map(item => item.value), 1) * 1.1 : 100
    const chart = Plot.plot({
      width, height: 52, marginTop: 8, marginBottom: 20, marginLeft: 18, marginRight: 18,
      x: { domain: [0, maximum], label: null, ticks: 5, grid: true }, y: { axis: null, domain: [-1, 1] },
      marks: [Plot.ruleY([0], { stroke: '#dbd7d0' }), Plot.dot(data, { x: 'value', y: 0, fill: 'color', r: 5, tip: true, title: item => `${item.region}: ${item.value}\n${compareDefinitions[id]}` })],
    })
    plot.current.replaceChildren(chart)
    return () => chart.remove()
  }, [id, left, right, nameA, nameB, width])
  return <div ref={container}>{left === null && right === null ? <p className='compare-missing'>Unavailable for both regions in this network.</p> : <div ref={plot} role='img' aria-label={`${compareDefinitions[id]} for ${nameA} and ${nameB}`} />}</div>
}
