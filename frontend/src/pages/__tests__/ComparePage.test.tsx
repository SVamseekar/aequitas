import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ComparePage from '../ComparePage'

const request = vi.hoisted(() => vi.fn())
vi.mock('@/api/client', () => ({ fetchJson: request }))
vi.mock('@/components/shared/SelectedRegionsMap', () => ({ default: () => <div>Country boundary fixture</div> }))
function renderAt(route: string) {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[route]}><Routes><Route path='/app/:country/compare' element={<ComparePage />} /></Routes></MemoryRouter></QueryClientProvider>)
}
describe('Country-scoped region comparison', () => {
  beforeEach(() => {
    request.mockReset()
    request.mockImplementation((path: string, params: Record<string, string>) => {
      const left = ['E12000002', 'groningen'].includes(params.region)
      if (path === '/score') return Promise.resolve({ score: left ? 83.7 : 90.8 })
      if (path === '/reach') return Promise.resolve({ available: false, median: null })
      if (params.dimension === 'equity') return Promise.resolve({ sections: [{ section_id: 'f1_gini', stats: { gini: left ? 0.5117 : 0.5258 } }] })
      if (params.dimension === 'accessibility') return Promise.resolve({ sections: [{ section_id: 'a3_walking_distance', stats: { pct_covered: left ? 83.1 : 95.7 } }] })
      return Promise.resolve({ sections: [{ section_id: 'b2_operating_hours', stats: { pct_evening_isolated: left ? 10.4 : 11.6 } }] })
    })
  })
  it('aligns genuine values and denominators in a five-row table and leaves missing reach unplotted', async () => {
    renderAt('/app/england/compare')
    const table = await screen.findByRole('table')
    expect(within(table).getByText('83.7')).toBeTruthy()
    expect(within(table).getByText('95.7%')).toBeTruthy()
    expect(within(table).getAllByText('—')).toHaveLength(2)
    expect(within(table).getByText(/% of LSOAs/)).toBeTruthy()
    expect(within(table).queryByText(/% of population/)).toBeNull()
    expect(within(table).getByText(/% of areas/)).toBeTruthy()
    expect(within(table).getAllByRole('row')).toHaveLength(6)
    expect(screen.queryByRole('img', { name: /Destination points/ })).toBeNull()
  })
  it('keeps both selectors and avoids data requests for same-region and London rural states', () => {
    const result = renderAt('/app/england/compare?a=E12000007&b=E12000007')
    expect(screen.getByText(/Choose two different regions to compare/)).toBeTruthy()
    expect(screen.getByRole('combobox', { name: 'Region A' })).toHaveValue('E12000007')
    expect(request).not.toHaveBeenCalled()
    result.unmount()
    renderAt('/app/england/compare?a=E12000002&b=E12000007&urban_rural=rural')
    expect(screen.getByText(/no rural LSOAs/)).toBeTruthy()
    expect(request).not.toHaveBeenCalled()
  })
  it('keeps dated analytical measures when historical travel-time caches are unavailable', async () => {
    const regular = request.getMockImplementation()!
    request.mockImplementation((path: string, params: Record<string, string>) => path === '/reach'
      ? Promise.reject(Object.assign(new Error('Current network only'), { status: 400 }))
      : regular(path, params))
    renderAt('/app/england/compare?pack=2026-09-25')
    const table = await screen.findByRole('table')
    expect(within(table).getByText('83.7')).toBeTruthy()
    expect(within(table).getAllByText('—')).toHaveLength(2)
  })
  it('does not borrow selectors from another country', () => {
    renderAt('/app/ireland/compare?a=E12000002&b=E12000007')
    expect(screen.getByText(/Select valid regions within Ireland/)).toBeTruthy()
    expect(screen.queryByRole('table')).toBeNull()
    expect(request).not.toHaveBeenCalled()
  })
  it('retains network date, Dutch mode and selection when switching evidence views', async () => {
    renderAt('/app/netherlands/compare?a=groningen&b=noord-holland&pack=2026-08-13&mode=all')
    await screen.findByRole('table')
    expect(request.mock.calls.every(call => call[1].country === 'netherlands' && call[1].pack === '2026-08-13' && call[1].mode === 'all')).toBe(true)
    fireEvent.click(screen.getByRole('link', { name: 'Access to jobs' }))
    await waitFor(() => expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(2))
    expect(screen.getByRole('combobox', { name: 'Region B' })).toHaveValue('noord-holland')
    expect(screen.getByRole('link', { name: 'Coverage' }).getAttribute('href')).toContain('mode=all')
    expect(screen.getByRole('link', { name: 'Coverage' }).getAttribute('href')).toContain('pack=2026-08-13')
  })
})
