import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import HeatmapChart from '../HeatmapChart'

describe('HeatmapChart observation boundaries', () => {
  beforeEach(() => {
    // jsdom lacks canvas; only the colour-ramp image needs it. Plot marks stay real.
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({ fillRect() {}, fillStyle: '' } as unknown as CanvasRenderingContext2D)
    vi.spyOn(HTMLCanvasElement.prototype, 'toDataURL').mockReturnValue('data:image/png;base64,')
  })
  afterEach(() => vi.restoreAllMocks())
  it('draws observed zero and positive values while omitting missing cells', () => {
    render(<HeatmapChart chartData={{ measure: 'population_400m_pct', x_labels: ['Urban', 'Rural'], y_labels: ['Decile 1', 'Decile 2'], values: [[0, 15], [null, undefined]] }} />)
    expect(screen.getByRole('img').querySelectorAll('[aria-label="cell"] rect')).toHaveLength(2)
    expect(screen.getByRole('img')).toHaveTextContent('0.0')
    expect(screen.getByRole('img')).toHaveTextContent('15.0')
    expect(screen.getByRole('img')).not.toHaveTextContent('−100')
  })
  it('reports unavailable when every cell is missing', () => {
    render(<HeatmapChart chartData={{ x_labels: ['Urban'], y_labels: ['Decile 1'], values: [[null]] }} />)
    expect(screen.getByText('No observations available for this heatmap.')).toBeInTheDocument()
    expect(screen.getByRole('img').querySelectorAll('[aria-label="cell"] rect')).toHaveLength(0)
  })
})
