import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { describe, expect, it } from 'vitest'
import type { SectionItem } from '@/api/types'
import { ServiceEvidence } from '../ServiceEvidence'
import { ServiceRoutes } from '../ServiceRoutes'

const base: SectionItem = { section_id: 'b4_route_frequency', dimension: 'service_quality', suppressed: false, narrative: '', stats: {}, chart_data: {} }
function Location() { return <output data-testid='location'>{useLocation().search}</output> }
function wrapper(child: React.ReactNode) { return <MemoryRouter initialEntries={['/app/england/service?view=b4_route_frequency&region=E12000005&pack=2026-08-01']}><Routes><Route path='/app/:country/service' element={<>{child}<Location /></>} /></Routes></MemoryRouter> }

describe('Service evidence controls', () => {
  it('switches to actual lowest routes while preserving selected context', async () => {
    render(wrapper(<ServiceRoutes section={{ ...base, stats: { top_routes: [{ route_short_name: 'A1', agency_name: 'Actual operator', n_trips_per_day: 120 }], bottom_routes: [{ route_short_name: '875', n_trips_per_day: 1 }], n_routes: 40 } }} />))
    expect(within(screen.getByRole('table')).getByText('A1')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Lowest frequency' }))
    expect(within(screen.getByRole('table')).getByText('875')).toBeInTheDocument()
    expect(within(screen.getByRole('table')).queryByText('A1')).toBeNull()
    expect(screen.getByTestId('location')).toHaveTextContent('rank=lowest')
    expect(screen.getByTestId('location')).toHaveTextContent('region=E12000005')
    expect(screen.getByTestId('location')).toHaveTextContent('pack=2026-08-01')
  })
  it('pages only actual sample rows, retains zero, and keeps missing values unavailable', () => {
    const rows = Array.from({ length: 26 }, (_, index) => ({ id: `E${String(index).padStart(4, '0')}`, x: index === 0 ? null : index, y: index === 0 ? 0 : index }))
    render(wrapper(<ServiceEvidence table section={{ ...base, section_id: 'b5_frequency_deprivation', stats: { n: 33755 }, chart_data: { data: rows, sample_size: 33755, x_label: 'IMD score', y_label: 'SQI points' } }} />))
    const table = screen.getByRole('table', { name: 'Small-area service sample' })
    expect(within(table).getAllByRole('row')).toHaveLength(26)
    const first = within(table).getByRole('row', { name: /E0000/ })
    expect(within(first).getByText('—')).toBeInTheDocument()
    expect(within(first).getByText('0.000')).toBeInTheDocument()
    expect(screen.getByText(/26 supplied sample rows from 33,755/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Next sample page' }))
    expect(within(table).getAllByRole('row')).toHaveLength(2)
    expect(within(table).getByText('E0025')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next sample page' })).toBeDisabled()
  })
})
