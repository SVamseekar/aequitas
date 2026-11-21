import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import HorizontalBarChart from '../HorizontalBarChart'

describe('HorizontalBarChart observations', () => {
  it('preserves supplied category order and zeroes when a reference uses geography order', () => {
    render(<HorizontalBarChart chartData={{type:'horizontal_bar',order:'source',color_by:'rank',palette:['#7ba17b','#db6139'],data:[{label:'Source first',value:0},{label:'Source second',value:12}]}} />)
    const labels=Array.from(screen.getByRole('img').querySelectorAll('[aria-label="y-axis tick label"] text')).map(node=>node.textContent)
    expect(labels).toEqual(['Source first','Source second'])
    expect(screen.getByRole('img')).toHaveTextContent('0')
  })
  it('maps grouped colors in supplied series order rather than alphabetic order', () => {
    render(<HorizontalBarChart chartData={{ type: 'grouped_bar', categories: ['Region'], palette: ['#6a98b6','#d65b2d'], series: [{ name: 'Weekday departures', values: [20] }, { name: 'Sunday departures', values: [10] }] }} />)
    const bars = screen.getByRole('img').querySelectorAll('[aria-label="bar"] rect')
    expect(bars[0]).toHaveAttribute('fill', '#6a98b6')
    expect(bars[1]).toHaveAttribute('fill', '#d65b2d')
  })
  it('keeps observed zero while omitting missing and non-finite observations', () => {
    render(<HorizontalBarChart chartData={{ data: [
      { label: 'Observed zero', value: 0 },
      { label: 'Observed positive', value: 12 },
      { label: 'Missing observation', value: null },
      { label: 'Invalid observation', value: Number.NaN },
      { label: 'Infinite observation', value: Number.POSITIVE_INFINITY },
    ] }} />)
    const plot = screen.getByRole('img')
    expect(plot).toHaveTextContent('Observed zero')
    expect(plot).toHaveTextContent('Observed positive')
    expect(plot).not.toHaveTextContent('Missing observation')
    expect(plot).not.toHaveTextContent('Invalid observation')
    expect(plot).not.toHaveTextContent('Infinite observation')
  })

  it('does not fill absent grouped series cells with zero', () => {
    render(<HorizontalBarChart chartData={{ type: 'grouped_bar',
      categories: ['Observed zero', 'Absent cell'],
      series: [{ name: 'Actual series', values: [0] }],
    }} />)
    expect(screen.getByRole('img')).toHaveTextContent('Observed zero')
    expect(screen.getByRole('img')).not.toHaveTextContent('Absent cell')
  })

  it('renders the stored scenario series data format without imputing missing cells', () => {
    render(<HorizontalBarChart chartData={{ type: 'stacked_bar',
      categories: ['England', 'Absent geography'],
      series: [{ name: 'Target population', data: [5689818] }, { name: 'Remaining population', data: [50800238] }],
    }} />)
    expect(screen.getByRole('img')).toHaveTextContent('England')
    expect(screen.getByRole('img')).not.toHaveTextContent('Absent geography')
    expect(screen.getByRole('img')).toHaveTextContent('Target population')
  })

  it('places grouped observations beside each other from a shared zero baseline', () => {
    render(<HorizontalBarChart chartData={{ type: 'grouped_bar', categories: ['West Midlands'],
      series: [{ name: 'Urban', values: [67.718] }, { name: 'Rural', values: [37.842] }],
    }} />)
    const bars = screen.getByRole('img').querySelectorAll('[aria-label="bar"] rect')
    expect(bars).toHaveLength(2)
    expect(bars[0].getAttribute('x')).toBe(bars[1].getAttribute('x'))
    expect(bars[0].getAttribute('y')).not.toBe(bars[1].getAttribute('y'))
  })

  it('shows unavailable when all observations are missing and ignores a missing average', () => {
    render(<HorizontalBarChart chartData={{ national_avg: null,
      data: [{ label: 'Missing', value: null }],
    }} />)
    expect(screen.getByText('No observations available for this chart.')).toBeInTheDocument()
    expect(screen.queryByText(/Avg:/)).not.toBeInTheDocument()
  })
})
