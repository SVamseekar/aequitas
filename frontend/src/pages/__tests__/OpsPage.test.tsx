import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import OpsPage from '../OpsPage'
const request = vi.hoisted(() => vi.fn())
vi.mock('@/api/client', () => ({ fetchJson: request }))
function renderAt(url: string) {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[url]}><Routes><Route path='/app/:country/ops' element={<OpsPage />} /></Routes></MemoryRouter></QueryClientProvider>)
}
const fixture = { country: 'england', empty: false, n_updates: 100, n_with_delay: 0, n_skipped: 2, n_cancelled: 1, n_static_routes: 20, n_routes_with_update: 5, coverage_pct: 25, pct_late: null, late_threshold_seconds: 300, vintage: '2026-09-24T20:15:53Z', window_note: 'Collected snapshot only.', coverage_sentence: '5 of 20 static routes.', by_region: [{ code: 'E12000005', name: 'West Midlands', n_updates: 75, n_with_delay: 0, pct_late: null }], by_imd_decile: [], feeds: [{ provider: 'BODS', status: 'stored' }] }
beforeEach(() => { request.mockReset(); request.mockResolvedValue(fixture) })
describe('Operations evidence views', () => {
  it('shows real regional counts in a table without inventing per-region route coverage', async () => {
    renderAt('/app/england/ops?view=regional')
    const table = await screen.findByRole('table', { name: 'Regional update summary' })
    expect(within(table).getByText('75')).toBeTruthy()
    expect(within(table).getAllByText('—').length).toBeGreaterThan(0)
    expect(screen.getByTestId('ops-late-rule').textContent).toMatch(/n_with_delay = 0/)
  })
  it('keeps a missing deprivation join empty and never draws zero-height bars', async () => {
    renderAt('/app/england/ops?view=deprivation')
    await screen.findByText(/No IMD-decile join in this snapshot/)
    expect(screen.queryByRole('img', { name: /Updates by deprivation/ })).toBeNull()
    expect(screen.getByText(/National collector scope/)).toBeTruthy()
  })
  it('exposes actual feed metadata in the Sources view', async () => {
    renderAt('/app/england/ops?view=sources')
    await screen.findByText('BODS')
    expect(screen.getByText('stored')).toBeTruthy()
  })
  it('keeps missing collector measures unavailable and exposes diagnostics on request',async()=>{
    request.mockResolvedValue({...fixture,country:'ireland',empty:true,empty_reason:'No stored delay observations',n_updates:0})
    const {container}=renderAt('/app/ireland/ops')
    await screen.findByText('No stored observations')
    const values=container.querySelectorAll('.ops-country-stat-grid strong')
    expect(values).toHaveLength(6)
    for(const value of values)expect(value).toHaveTextContent('—')
    const details=screen.getByText('No stored delay observations').closest('details')
    expect(details).not.toHaveAttribute('open')
    fireEvent.click(screen.getByText('Collector availability details'))
    expect(details).toHaveAttribute('open')
  })
})
