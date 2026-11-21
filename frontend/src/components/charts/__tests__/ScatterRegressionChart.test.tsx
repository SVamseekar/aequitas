import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ScatterRegressionChart from '../ScatterRegressionChart'
describe('ScatterRegressionChart source precision', () => {
  it('retains coefficient precision and omits missing regression coefficients', () => {
    render(<ScatterRegressionChart chartData={{ r: -0.3127, p_value: 0,
      regression_line: { slope: null, intercept: null },
      data: [{ id: 'Observed', x: 10, y: 2 }, { id: 'Observed zero', x: 20, y: 0 }, { id: 'Missing', x: null, y: null }],
    }} />)
    const plot = screen.getByRole('img')
    expect(plot).toHaveTextContent('r = -0.3127')
    expect(plot).toHaveTextContent('p < 0.0001')
    expect(plot.querySelectorAll('[aria-label="dot"] circle')).toHaveLength(2)
    expect(plot.querySelectorAll('[aria-label="line"] path')).toHaveLength(0)
  })
  it('reports unavailable rather than drawing an empty relationship plot', () => {
    render(<ScatterRegressionChart chartData={{ data: [{ x: null, y: null }] }} />)
    expect(screen.getByText('No paired observations available for this plot.')).toBeInTheDocument()
  })
})
