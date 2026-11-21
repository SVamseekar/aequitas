import { useEffect, useRef } from 'react'
import * as Plot from '@observablehq/plot'
import { useChartWidth } from '@/hooks/useChartWidth'

/** A single, labelled proportion; the denominator remains country-specific. */
export function CoverageProportion({ covered, country, labels, values, colors }: { covered: number; country: string; labels?: [string,string]; values?: [string,string]; colors?: [string,string] }) {
  const container = useRef<HTMLDivElement>(null)
  const output = useRef<HTMLDivElement>(null)
  const width = useChartWidth(container, 600)
  const within = labels?.[0] ?? (country === 'england' ? 'Non-zero access score' : 'Within 400 m')
  const beyond = labels?.[1] ?? (country === 'england' ? 'Zero access score' : 'Beyond 400 m')
  const firstColor=colors?.[0]??'#64885d',secondColor=colors?.[1]??'#d65b2d'
  useEffect(() => {
    if (!output.current) return
    const rows = [{ label: within, from: 0, to: covered }, { label: beyond, from: covered, to: 100 }]
    const plot = Plot.plot({ width, height: 66, margin: 0, x: { domain: [0, 100], axis: null }, y: { axis: null },
      color: { domain: [within, beyond], range: [firstColor,secondColor] },
      marks: [Plot.rectX(rows, { x1: 'from', x2: 'to', y1: 0, y2: 1, fill: 'label', inset: 1, rx: 4,
        tip: true, title: row => `${row.label}: ${(row.to-row.from).toFixed(1)}%` }),
      Plot.text(rows.filter(row => row.to-row.from >= 8), { x: row => (row.to+row.from)/2, y: .5,
        text: row => `${(row.to-row.from).toFixed(1)}%`, fill: 'white', fontSize: 16, fontWeight: 600 })] })
    output.current.replaceChildren(plot)
    return () => plot.remove()
  }, [covered, width, within, beyond,firstColor,secondColor])
  return <div ref={container} className='coverage-proportion'><div ref={output} role='img' aria-label={`${within}: ${covered.toFixed(1)}%; ${beyond}: ${(100-covered).toFixed(1)}%`} /><div className='coverage-proportion-labels'><span>{within}<strong>{values?.[0]??`${covered.toFixed(1)}%`}</strong></span><span>{beyond}<strong>{values?.[1]??`${(100-covered).toFixed(1)}%`}</strong></span></div></div>
}
