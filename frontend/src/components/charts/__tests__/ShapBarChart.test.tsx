import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ShapBarChart from '../ShapBarChart'
describe('Feature importance measure boundaries', () => {
  it('retains observed zero importance, omits missing observations and tolerates missing model fit', () => {
    render(<ShapBarChart chartData={{ model_r2: null, features: [{ name: 'nocar_pct', importance: 0.083 }, { name: 'urban_enc', importance: 0 }, { name: 'Missing', importance: null }] }} />)
    const plot = screen.getByRole('img')
    expect(plot).toHaveTextContent('Car-free households')
    expect(plot.querySelectorAll('[aria-label="bar"] rect')).toHaveLength(2)
    expect(plot).not.toHaveTextContent('Missing')
    expect(plot).not.toHaveTextContent('R²')
  })
  it('shows stored country correlations without relabelling them as SHAP importance', () => {
    render(<ShapBarChart chartData={{ features: [{ name: 'fedi_score', r: 0.0634 }, { name: 'INSEE density', r: null }] }} />)
    const table = screen.getByRole('table', { name: 'Stored feature associations' })
    expect(within(table).getByText('0.0634')).toBeInTheDocument()
    const missing = within(table).getByRole('row', { name: /INSEE density/ })
    expect(within(missing).getAllByRole('cell')[0]).toHaveTextContent('—')
    expect(screen.getByText(/correlations, rather than SHAP/)).toBeInTheDocument()
    expect(screen.queryByRole('img')).toBeNull()
  })
})
