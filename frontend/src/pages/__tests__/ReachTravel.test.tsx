import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ReachPage from '../ReachPage'

const request = vi.hoisted(() => vi.fn())
vi.mock('@/api/client', () => ({ fetchJson: request }))
function renderAt(url: string) {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[url]}><Routes><Route path='/app/:country/reach' element={<ReachPage />} /></Routes></MemoryRouter></QueryClientProvider>)
}
beforeEach(() => {
  request.mockReset()
  request.mockImplementation((path: string, params: Record<string, string>) => {
    if (path === '/reach') return Promise.resolve({ available: params.dest_type !== 'school', median: params.dest_type === 'school' ? null : Number(params.cutoff), n_areas: params.dest_type === 'school' ? 0 : 3, dest_type: params.dest_type, cutoff: Number(params.cutoff), histogram: [{ bin: '0–10', n: 3 }], ranked: [], geographies: ['E12000005'], note: 'Not computed' })
    if (path === '/export/pack.json') return Promise.resolve({ country: 'england', place: 'West Midlands', filter: { region: 'E12000005', urban_rural: 'all', dest_type: 'jobs', cutoff: 45 }, vintages: { network: 'Actual network vintage', census: 'Actual census vintage' }, caveats: ['Research pack, not a statutory submission.'], score: { score: 80, components: [] }, bands: { empty: true }, reach: { available: false }, studio: null })
    if (path === '/score') return Promise.resolve({ score: 80 })
    return Promise.resolve({ empty: true, empty_reason: 'No bands fixture' })
  })
})
describe('Reach selected evidence', () => {
  it('shows all nine actual configurations and keeps selected context', async () => {
    renderAt('/app/england/reach?view=travel-time&region=E12000005&pack=current&urban_rural=urban&dest=jobs&cutoff=45')
    const table = await screen.findByRole('table', { name: 'Destination availability' })
    await waitFor(() => expect(within(table).getAllByRole('button')).toHaveLength(9))
    await waitFor(() => expect(within(table).getAllByText('Unavailable')).toHaveLength(3))
    fireEvent.click(within(table).getByRole('button', { name: /GP.*30 minutes/ }))
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Travel time cutoff' })).toHaveValue('30'))
    expect(screen.getByRole('button', { name: 'GP' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('link', { name: 'Export' }).getAttribute('href')).toContain('dest=gp')
    expect(request.mock.calls.filter(call => call[0] === '/reach').every(call => call[1].pack === 'current' && call[1].urban_rural === 'urban')).toBe(true)
  })
  it('reviews actual export sources and shares exact scope with downloads', async () => {
    renderAt('/app/england/reach?view=export&region=E12000005&pack=current&dest=jobs&cutoff=45')
    await screen.findByText('Actual network vintage')
    const csv = screen.getByRole('link', { name: /Download CSV/ })
    expect(csv.getAttribute('href')).toContain('pack=current')
    expect(csv.getAttribute('href')).toContain('dest_type=jobs')
    expect(screen.getByText('Actual census vintage')).toBeTruthy()
    expect(screen.queryByText(/Download PDF/)).toBeNull()
  })
  it('exposes a recoverable API error without displaying absent values as zero', async () => {
    request.mockRejectedValue(new Error('Current network only'))
    renderAt('/app/england/reach?view=travel-time')
    await screen.findByRole('alert')
    expect(screen.getByRole('button', { name: /Retry travel times/ })).toBeTruthy()
    expect(screen.queryByText(/Covered origins: 0/)).toBeNull()
  })
})
