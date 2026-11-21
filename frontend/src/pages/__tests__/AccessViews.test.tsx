import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DimensionPage } from '@/components/dimension/DimensionPage'
const request = vi.hoisted(() => vi.fn())
vi.mock('@/api/client', () => ({ fetchJson: request }))
vi.mock('@/components/charts/ChoroplethMap', () => ({ default: () => <div>Stored district map</div> }))
function renderAccess(view: string) {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[`/app/england/access?view=${view}`]}><Routes><Route path='/app/:country/:dimensionSlug' element={<DimensionPage />} /></Routes></MemoryRouter></QueryClientProvider>)
}
beforeEach(() => { request.mockReset() })
describe('Access measure boundaries', () => {
  it('shows a single unavailable state with a scoped next action instead of empty result cards', async () => {
    request.mockImplementation((path: string) => Promise.resolve(path === '/reach' ? { available: false, median: null, n_areas: 0, histogram: [], note: 'No stored origins for this selection.' } : { sections: [{ section_id: 'a3_walking_distance', dimension: 'accessibility', stats: { pct_covered: 79.3 }, chart_data: {}, narrative: 'Stored access', suppressed: false }] }))
    renderAccess('destinations&region=E12000005&pack=current&dest=gp&cutoff=30')
    await screen.findByRole('heading', { name: 'Not available in this pack' })
    expect(screen.getByText('No stored origins for this selection.')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Destination points (median origin)' })).not.toBeInTheDocument()
    const href = screen.getByRole('link', { name: 'View service bands' }).getAttribute('href')!
    expect(href).toContain('region=E12000005')
    expect(href).toContain('view=bands')
    expect(href).toContain('dest=gp')
    expect(href).toContain('cutoff=30')
  })
  it('separates the selected-filter settlement means from the regional detail and preserves observed zero', async () => {
    request.mockResolvedValue({ sections: [{ section_id: 'a6_urban_rural_gap', dimension: 'accessibility', stats: { urban_value: 0.28, rural_value: 0, gap_pct: 100, n_urban: 12, n_rural: 3 }, chart_data: { type: 'grouped_bar', categories: ['London'], series: [{ name: 'Urban', values: [0.53] }, { name: 'Rural', values: [0] }] }, narrative: '', suppressed: false }] })
    renderAccess('a6_urban_rural_gap')
    const chart = await screen.findByRole('img', { name: 'Urban and rural mean trips per capita' })
    expect(chart.querySelectorAll('[aria-label="bar"] rect')).toHaveLength(2)
    expect(chart).toHaveTextContent('0.00')
    expect(chart).not.toHaveTextContent('London')
    expect(screen.getByText('Regional settlement detail').closest('details')).not.toHaveAttribute('open')
  })
  it('draws both settlement means from the same zero baseline', async () => {
    request.mockResolvedValue({ sections: [{ section_id: 'a6_urban_rural_gap', dimension: 'accessibility', stats: { urban_value: 0.28, rural_value: 0.12 }, chart_data: {}, narrative: '', suppressed: false }] })
    renderAccess('a6_urban_rural_gap')
    const chart = await screen.findByRole('img', { name: 'Urban and rural mean trips per capita' })
    const bars = chart.querySelectorAll('[aria-label="bar"] rect')
    expect(bars).toHaveLength(2)
    const bottom = (bar: Element) => Number(bar.getAttribute('y')) + Number(bar.getAttribute('height'))
    expect(bottom(bars[0])).toBeCloseTo(bottom(bars[1]))
    expect(Number(bars[1].getAttribute('height'))).toBeGreaterThan(0)
    expect(Number(bars[0].getAttribute('height')) / Number(bars[1].getAttribute('height'))).toBeCloseTo(0.28 / 0.12)
  })
  it('uses Sunday-service statistics beside the Sunday map and keeps zero-stop population separate', async () => {
    request.mockImplementation((_path: string, params: Record<string, string>) => Promise.resolve({ sections: params.dimension === 'service_quality' ? [{ section_id: 'b3_weekend_penalty', dimension: 'service_quality', stats: { n_sunday_desert: 6745, pct_sunday_desert: 20 }, chart_data: {}, narrative: '', suppressed: false }] : [{ section_id: 'a5_service_deserts', dimension: 'accessibility', stats: { n_desert_lsoas: 4245, pop_affected: 7071109, mean_imd_score: 24.3 }, chart_data: { type: 'choropleth', geography: 'lad', metric: 'pct_sunday_desert', data: [{ area_code: 'E06000001', area_name: 'Hartlepool', value: 14 }] }, narrative: 'Zero-stop analysis', suppressed: false }] }))
    renderAccess('a5_service_deserts')
    expect((await screen.findAllByText('6,745')).length).toBeGreaterThan(0)
    expect(screen.getByText('20.0%')).toBeInTheDocument()
    expect(screen.getByText(/Sunday-desert population is not stored/)).toBeInTheDocument()
    expect(screen.getByText(/Separate zero-stop analysis/)).toHaveTextContent('7,071,109')
  })
  it('retains the selected travel-time configuration when opening Reach and keeps observed zero', async () => {
    request.mockImplementation((path: string) => Promise.resolve(path === '/reach' ? { available: true, median: 0, n_areas: 3, histogram: [{ bin: '0', n: 3 }], geographies: ['E12000005'] } : { sections: [{ section_id: 'a3_walking_distance', dimension: 'accessibility', stats: { pct_covered: 79.3 }, chart_data: {}, narrative: 'Stored access', suppressed: false }] }))
    renderAccess('destinations&region=E12000005&pack=current&dest=gp&cutoff=30')
    const link = await screen.findByRole('link', { name: 'Open all nine configurations in Reach' })
    const href = link.getAttribute('href')!
    expect(href).toContain('view=travel-time')
    expect(href).toContain('dest=gp')
    expect(href).toContain('cutoff=30')
    expect(href).toContain('pack=current')
    expect(screen.getByRole('button', { name: /^GP$/ })).toHaveAttribute('aria-pressed','true')
  })
})
