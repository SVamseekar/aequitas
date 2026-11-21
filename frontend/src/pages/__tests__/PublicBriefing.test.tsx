import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import CountryBriefingPage from '../briefing/CountryBriefingPage'
import TopicBriefingPage from '../briefing/TopicBriefingPage'

const request = vi.hoisted(() => vi.fn())
vi.mock('@/api/client', () => ({ fetchJson: request }))
vi.mock('@/components/shared/Seo', () => ({ Seo: () => null }))
vi.mock('@/components/charts/ChoroplethMap', () => ({ default: () => <div>Actual boundary map</div> }))
function renderCountry() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><CountryBriefingPage code='england' /></MemoryRouter></QueryClientProvider>)
}
beforeEach(() => {
  request.mockReset()
  request.mockImplementation((path: string) => {
    if (path === '/score') return Promise.resolve({ score: 80, n_areas: 33755, components: [{ id: 'pop_within_400m', value: 0.79274 }] })
    if (path === '/packs') return Promise.resolve({ england: { dates: [{ current: true, as_of: '2026-08-01' }] } })
    return Promise.resolve({ empty: true, data: [], empty_reason: 'No map for this scope' })
  })
})
describe('Public country evidence', () => {
  it('shows actual country coverage and its network date', async () => {
    renderCountry()
    await screen.findByText('79.3%')
    expect(screen.getByRole('heading', { name: 'LSOAs with non-zero access score' })).toBeInTheDocument()
    expect(screen.getByText(/2026-08-01/)).toBeTruthy()
    expect(request.mock.calls.filter(call => call[0] === '/score' || call[0] === '/map').every(call => call[1].country === 'england')).toBe(true)
  })
  it('shows unavailable coverage without borrowing catalogue figures', async () => {
    request.mockImplementation((path: string) => Promise.resolve(path === '/score' ? { score: null, components: [] } : { empty: true, data: [] }))
    renderCountry()
    await screen.findByText('Coverage unavailable')
    expect(screen.queryByText('79.3%')).toBeNull()
  })
  it('switches topic evidence within one country and retains absent statistics', async () => {
    request.mockImplementation((path: string, params: Record<string, string>) => Promise.resolve(path === '/sections' ? { sections: [{ section_id: 'f1_gini', stats: { gini: params.country === 'ireland' ? 0.2345 : 0.1234, palma: null }, chart_data: {}, narrative: 'Country-specific observations.' }] } : {}))
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><TopicBriefingPage slug='equity' /></MemoryRouter></QueryClientProvider>)
    await screen.findByText('0.1234')
    fireEvent.click(screen.getByRole('link', { name: 'Ireland' }))
    await screen.findByText('0.2345')
    expect(screen.queryByText('0.1234')).toBeNull()
    expect(screen.getByRole('link', { name: 'Open selected evidence' }).getAttribute('href')).toContain('/app/ireland/equity')
  })
})
