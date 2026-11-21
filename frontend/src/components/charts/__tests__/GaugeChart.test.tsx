import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"

import GaugeChart from "../GaugeChart"

const BCR_BANDS = [
  { label: "Poor", min: 0.0, max: 1.0, color_hint: "red" },
  { label: "Low", min: 1.0, max: 1.5, color_hint: "orange" },
  { label: "Medium", min: 1.5, max: 2.0, color_hint: "yellow" },
  { label: "High", min: 2.0, max: 4.0, color_hint: "green" },
  { label: "Very High", min: 4.0, max: null, color_hint: "blue" },
]

describe("GaugeChart", () => {
  it('renders a circular concentration display from the actual value without losing zero',()=>{
    render(<GaugeChart chartData={{type:'gauge',variant:'ring',unit:'HHI',bands:[{label:'Low',min:0,max:1500,color_hint:'green'},{label:'High',min:1500,max:null,color_hint:'red'}],markers:[{label:'Observed zero',value:0}]}} />)
    expect(screen.getByRole('img')).toHaveTextContent('0')
    expect(screen.getByRole('img')).toHaveTextContent('/ 10,000')
    expect(screen.getByText('0 HHI')).toBeVisible()
    expect(screen.queryByText('High')).toBeNull()
  })
  it("renders bands, markers, and reference lines for j2_bcr", () => {
    render(
      <GaugeChart
        chartData={{
          type: "gauge",
          title: "BCR for coverage gaps",
          unit: "BCR",
          bands: BCR_BANDS,
          markers: [
            { label: "London", value: 1.6 },
            { label: "South East", value: 0.9 },
          ],
          reference_lines: [1.0, 2.0],
        }}
      />,
    )

    expect(screen.getByText("BCR for coverage gaps")).toBeTruthy()
    expect(screen.getByText("Poor")).toBeTruthy()
    expect(screen.getByText("Very High")).toBeTruthy()
    expect(screen.getByText("London")).toBeTruthy()
    expect(screen.getByText("South East")).toBeTruthy()
    expect(screen.getByText("1.6 BCR")).toBeTruthy()
    expect(screen.getByText("0.9 BCR")).toBeTruthy()
    expect(screen.getByRole('img').querySelectorAll('g[stroke-dasharray="3,3"] line')).toHaveLength(2)
  })

  it("renders open-ended HHI bands for bsa2_operator_concentration", () => {
    render(
      <GaugeChart
        chartData={{
          type: "gauge",
          title: "Operator concentration",
          unit: "HHI",
          bands: [
            { label: "Low", min: 0, max: 1500, color_hint: "green" },
            { label: "Moderate", min: 1500, max: 2500, color_hint: "yellow" },
            { label: "High", min: 2500, max: null, color_hint: "red" },
          ],
          markers: [{ label: "London", value: 2000 }],
          reference_lines: [1500, 2500],
        }}
      />,
    )

    expect(screen.getByText("Moderate")).toBeTruthy()
    expect(screen.getByText("2,000 HHI")).toBeTruthy()
    expect(screen.getByRole('img').querySelectorAll('g[stroke-dasharray="3,3"] line')).toHaveLength(2)
  })

  it("renders fallback message when markers are empty", () => {
    render(
      <GaugeChart
        chartData={{ type: "gauge", title: "Empty", unit: "BCR", bands: BCR_BANDS, markers: [] }}
      />,
    )
    expect(screen.getByText("No data available")).toBeTruthy()
  })

  it("synthesizes an HHI marker from value when markers were not persisted", () => {
    render(
      <GaugeChart
        chartData={{
          type: "gauge",
          title: "OVapi operator HHI",
          unit: "/ 10,000",
          value: 1333,
          bands: [
            { label: "Low", min: 0, max: 1500, color_hint: "green" },
            { label: "Moderate", min: 1500, max: 2500, color_hint: "orange" },
            { label: "High", min: 2500, max: 10000, color_hint: "red" },
          ],
          markers: [],
        }}
      />,
    )
    expect(screen.getByText("HHI")).toBeTruthy()
    expect(screen.getByText("1,333 / 10,000")).toBeTruthy()
  })
  it('retains observed zero, omits non-finite markers and keeps the HHI axis at 10,000',()=>{
    render(<GaugeChart chartData={{unit:'HHI',bands:[{label:'Low',min:0,max:1500,color_hint:'green'},{label:'High',min:1500,max:null,color_hint:'red'}],markers:[{label:'Observed zero',value:0},{label:'Missing',value:null}]}} />)
    expect(screen.getByText('0 HHI')).toBeInTheDocument()
    expect(screen.queryByText('Missing')).toBeNull()
    expect(screen.getByRole('img')).toHaveTextContent('10,000')
  })
})
