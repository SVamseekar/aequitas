import { useRef, useEffect, useMemo } from "react"
import * as Plot from "@observablehq/plot"
import { CATEGORICAL } from "@/lib/colours"
import { useChartWidth } from '@/hooks/useChartWidth'

interface BarDatum {
  label: string
  value: number
}

interface GroupedDatum {
  label: string
  group: string
  value: unknown
}

interface Props {
  chartData: Record<string, unknown>
}

/** Transform categories/series format to flat GroupedDatum[] */
function normalizeGroupedData(chartData: Record<string, unknown>): GroupedDatum[] {
  // Already flat format
  if (Array.isArray(chartData.data) && chartData.data.length > 0 && "group" in (chartData.data[0] as Record<string, unknown>)) {
    return chartData.data as GroupedDatum[]
  }
  // categories/series format → flatten
  const categories = chartData.categories as string[] | undefined
  const series = chartData.series as { name: string; values?: unknown[]; data?: unknown[] }[] | undefined
  if (categories && series) {
    const flat: GroupedDatum[] = []
    for (const s of series) {
      const values = s.values ?? s.data ?? []
      for (let i = 0; i < categories.length; i++) {
        flat.push({ label: categories[i], group: s.name, value: values[i] })
      }
    }
    return flat
  }
  return (chartData.data ?? []) as GroupedDatum[]
}

export default function HorizontalBarChart({ chartData }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const width = useChartWidth(containerRef, 700)
  const ref = useRef<HTMLDivElement>(null)
  const variant = (chartData.type as string | undefined) ?? "horizontal_bar"
  const data = useMemo(() => {
    const raw = variant === 'grouped_bar' || variant === 'stacked_bar'
      ? normalizeGroupedData(chartData)
      : (chartData.data ?? []) as BarDatum[]
    return raw.flatMap(row => typeof row.value === 'number' && Number.isFinite(row.value)
      ? [{ ...row, value: row.value }]
      : [])
  }, [chartData, variant])

  useEffect(() => {
    if (!ref.current) return
    if (data.length === 0) { ref.current.replaceChildren(); return }
    const xLabel = (chartData.x_label as string | undefined) ?? "Value"
    const nationalAvg = chartData.national_avg as number | undefined

    const marks: Plot.Markish[] = []
    const vertical = variant === 'grouped_bar' && chartData.orientation === 'vertical' && width >= 500
    let x: Plot.PlotOptions['x'] = { label: xLabel,labelAnchor:'center',labelArrow:false,grid:true,line:true,ticks: width < 500 ? 3 : undefined }
    const valueLabel = (value:number) => value.toLocaleString('en-GB', { maximumFractionDigits: Math.abs(value) < 1 ? 3 : Math.abs(value) < 10 ? 2 : 1 })
    const labelSpace = Math.max(44,...data.map(row=>valueLabel(row.value).length*6.5+12))
    const wrapLabel = (value: unknown) => {
      const limit = width < 500 ? 18 : 26, lines: string[] = []
      for (const word of String(value).split(' ')) {
        if (lines.length && lines[lines.length - 1].length + word.length + 1 <= limit) lines[lines.length - 1] += ` ${word}`
        else lines.push(word)
      }
      return lines.join('\n')
    }
    let y: Plot.PlotOptions['y'] = { label: null, tickFormat: wrapLabel, ...(chartData.order === 'source' ? {domain:data.map(row=>row.label)} : {}) }
    const palette = Array.isArray(chartData.palette) && chartData.palette.every(value => typeof value === 'string') ? chartData.palette as string[] : [...CATEGORICAL]
    let color: Plot.PlotOptions['color'] = variant !== 'horizontal_bar' ? { legend: true, range: palette } : undefined
    let height = Math.max(220, new Set(data.map(row => row.label)).size * 28 + 60)

    if (variant === "grouped_bar") {
      const grouped = data as (BarDatum & { group: string })[]
      const groups = normalizeGroupedData(chartData).map(row => row.group)
      color = { domain: [...new Set(groups)], range: palette, legend: true }
      if (groups.includes('Urban') && groups.includes('Rural')) color = { domain: ['Urban','Rural'], range: ['#819d79','#6a98b6'], legend: true }
      const key = (row: BarDatum & { group: string }) => `${row.label}\u0000${row.group}`
      const labels = [...new Set(grouped.map(row => row.label))]
      const domain = labels.flatMap(label => grouped.filter(row => row.label === label).map(key))
      const first = new Set(labels.map(label => domain.find(value => value.startsWith(`${label}\u0000`))))
      const tickFormat = (value: unknown) => {
        const label = String(value).split('\u0000')[0]
        return first.has(String(value)) ? label.replace('Yorkshire and The Humber', 'Yorkshire and\nthe Humber').replace('East of England', 'East of\nEngland').replace(' Midlands', '\nMidlands').replace(' West', '\nWest').replace(' East', '\nEast') : ''
      }
      if (vertical) {
        x = { label: null, domain, tickSize: 0, tickFormat }
        y = { label: xLabel, zero: true, grid: true, ticks: 6, domain: chartData.sqi_scale === true ? [0,100] : undefined }
        height = 250
        marks.push(Plot.barY(grouped, { x: key, y1: 0, y2: 'value', fill: 'group', tip: true,
          title: (d: BarDatum & { group: string }) => `${d.label} — ${d.group}\n${xLabel}: ${d.value.toLocaleString()}` }))
      } else {
        y = { label: null, domain, tickSize: 0, tickFormat }
        height = Math.max(260, domain.length * 19 + 70)
        marks.push(Plot.barX(grouped, {
          y: key, x1: 0, x2: 'value', fill: 'group',
          tip: true,
          title: (d: BarDatum & { group: string }) => `${d.label} — ${d.group}\n${xLabel}: ${d.value.toLocaleString()}`,
        }))
      }
    } else if (variant === "stacked_bar") {
      color = { legend: true, range: palette, domain: [...new Set(normalizeGroupedData(chartData).map(row => row.group))] }
      marks.push(
        Plot.barX(data, Plot.stackX({
          y: "label", x: "value", fill: "group",
          sort: { y: "x", reverse: true },
          tip: true,
          title: (d: BarDatum & { group: string }) => `${d.label} — ${d.group}\n${xLabel}: ${d.value.toLocaleString()}`,
        })),
      )
    } else {
      marks.push(
        Plot.barX(data, {
          y: "label", x: "value", fill: chartData.color_by==='rank'?(row:BarDatum)=>{const ordered=[...data].sort((a,b)=>b.value-a.value);const rank=ordered.findIndex(item=>item.label===row.label);const position=ordered.length>1?rank/(ordered.length-1):0;return palette[Math.round((chartData.color_reverse?1-position:position)*(palette.length-1))]}:palette[0],
          ...(chartData.order==='source'?{}:{sort:{y:'x',reverse:chartData.order!=='ascending'}}),
          tip: true,
          title: (d: BarDatum) => `${d.label}\n${xLabel}: ${d.value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`,
        }),
        Plot.text(data, {
          y: "label", x: "value",
          text: (d: BarDatum) => valueLabel(d.value),
          dx: 4, textAnchor: "start", fontSize: 11,
        }),
      )
    }

    if (Array.isArray(chartData.reference_rules)) for (const value of chartData.reference_rules) {
      if (typeof value === 'number' && Number.isFinite(value)) marks.push(Plot.ruleX([value], {stroke:'#888',strokeDasharray:'4,3'}))
    }
    if (typeof nationalAvg === 'number' && Number.isFinite(nationalAvg)) {
      marks.push(
        Plot.ruleX([nationalAvg], { stroke: "#e15759", strokeWidth: 1.5, strokeDasharray: "4,3" }),
        Plot.text([nationalAvg], {
          x: (d: number) => d,
          frameAnchor: 'top',
          text: (d: number) => `Avg: ${d.toLocaleString('en-GB', { maximumFractionDigits: 2 })}`,
          dy: -8, fill: "#e15759", fontSize: 10,
        })
      )
    }

    const chart = Plot.plot({
      marginLeft: vertical ? 60 : Math.min(140, Math.max(72, Math.round(width * 0.35))),
      marginRight: vertical ? 20 : variant === 'horizontal_bar' ? Math.min(110,labelSpace) : 44,
      marginBottom: vertical ? 70 : undefined,
      width,
      height: typeof chartData.height === 'number' && Number.isFinite(chartData.height)
        ? Math.max(100, Math.min(1000, chartData.height))
        : height,
      x: Array.isArray(chartData.x_domain) && chartData.x_domain.length === 2 && chartData.x_domain.every(value => typeof value === 'number' && Number.isFinite(value)) ? { ...x, domain: chartData.x_domain as [number,number] } : x,
      y,
      color,
      marks,
    })

    ref.current.replaceChildren(chart)
    return () => chart.remove()
  }, [chartData, data, variant, width])

  const note = typeof chartData.note === "string" ? chartData.note : null
  return (
    <div ref={containerRef} data-bar-orientation={variant === 'grouped_bar' && chartData.orientation === 'vertical' && width >= 500 ? 'vertical' : 'horizontal'}>
      <div ref={ref} aria-label={(chartData.title as string | undefined) ?? "Bar chart"} role="img" />
      {data.length === 0 ? <p className="text-sm text-muted-foreground py-3">No observations available for this chart.</p> : null}
      {note ? (
        <p className="text-xs text-muted-foreground mt-2" data-testid="bar-chart-note">
          {note}
        </p>
      ) : null}
    </div>
  )
}
