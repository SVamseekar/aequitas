import { render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FacilityAccessPanel } from '../FacilityAccessPanel'
const request = vi.hoisted(() => vi.fn())
vi.mock('@/api/client', () => ({ fetchJson: request }))
function renderPanel() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={['/app/england/access?view=facilities&region=E12000005&pack=2026-09-25']}><Routes><Route path='/app/:country/access' element={<FacilityAccessPanel />} /></Routes></MemoryRouter></QueryClientProvider>)
}
beforeEach(() => { request.mockReset() })
describe('Facility inventory scope', () => {
  it('identifies national inventory independently of selected region and network date', async () => {
    request.mockResolvedValue({ country: 'england', destinations: { jobs: { available: true, rows: 33755, source: 'BRES employment-centroid proxy' } }, facility_400m: { jobs: { available: true, people_share: 1, n_within_400m: 33755, n_areas: 33755, note: 'Every centroid matches itself; not workplace accessibility.' } }, official_distances: null })
    renderPanel()
    await screen.findAllByText('100.0%')
    expect(screen.getByText(/Inventory scope: national/)).toHaveTextContent('England')
    expect(screen.getByText(/region, area and network-date controls do not subset/)).toBeInTheDocument()
    expect(screen.getByText('Every centroid matches itself; not workplace accessibility.')).toBeInTheDocument()
    expect(request.mock.calls[0][1]).toEqual({ country: 'england' })
  })
  it('keeps all destination cards visible with unavailable values instead of zero', async () => {
    request.mockResolvedValue({ country: 'england', destinations: {}, facility_400m: {}, official_distances: null, note: 'No extracts stored.' })
    renderPanel()
    await screen.findByText('No extracts stored.')
    expect(screen.getAllByRole('article')).toHaveLength(3)
    for (const card of screen.getAllByRole('article')) expect(within(card).getByText('—')).toBeInTheDocument()
    expect(screen.queryByText('0.0%')).toBeNull()
  })
})
