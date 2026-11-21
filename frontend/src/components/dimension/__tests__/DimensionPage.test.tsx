import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, expect, it, vi, afterEach } from 'vitest'
import { DimensionPage } from '../DimensionPage'

vi.mock('@/api/hooks', async () => ({
  ...await vi.importActual<typeof import('@/api/hooks')>('@/api/hooks'),
  useSections: () => ({ isLoading: false, error: null, data: { sections: [
    { section_id: 'f1_gini', stats: { gini: 0.5741 }, chart_data: {}, narrative: 'Distribution evidence' },
    { section_id: 'f2_disparity_ratio', stats: { ratio: 0.45 }, chart_data: {}, narrative: 'Deprivation evidence' },
  ] } }),
}))
vi.mock('../EquityEvidence', () => ({ EquityEvidence: ({ section }: { section: { section_id: string } }) => <div data-testid='selected-exhibit'>{section.section_id}</div> }))
vi.mock('../SectionCard', () => ({ SectionCard: ({ section }: { section: { section_id: string } }) => <div data-testid='selected-exhibit'>{section.section_id}</div> }))
afterEach(() => vi.unstubAllGlobals())

function renderAt(route: string) {
  return render(<MemoryRouter initialEntries={[route]}><Routes><Route path='/app/:country/:dimensionSlug' element={<DimensionPage />} /></Routes></MemoryRouter>)
}

describe('focused analytical views and export scope', () => {
  it('renders only the chosen actual exhibit and lets the analyst change views', () => {
    renderAt('/app/england/equity?view=f2_disparity_ratio&region=E12000002')
    expect(screen.getByTestId('selected-exhibit').textContent).toBe('f2_disparity_ratio')
    fireEvent.click(screen.getByRole('link', { name: 'Distribution' }))
    expect(screen.getByTestId('selected-exhibit').textContent).toBe('f1_gini')
    expect(screen.getByRole('link', { name: 'Distribution' }).getAttribute('href')).toContain('region=E12000002')
  })
  it('reports an unavailable extended exhibit without substituting another chart', () => {
    renderAt('/app/ireland/equity?view=f6_equitable_regions')
    expect(screen.queryByTestId('selected-exhibit')).toBeNull()
    expect(screen.getByText(/This exhibit is unavailable/)).toBeTruthy()
  })
  it('prevents an England-only PDF endpoint from exporting a different country', () => {
    renderAt('/app/france/equity')
    expect(screen.getByRole('button', { name: 'Export PDF' }).hasAttribute('disabled')).toBe(true)
  })
  it('prevents a current-warehouse PDF endpoint from silently exporting another date', () => {
    renderAt('/app/england/equity?pack=2026-09-25')
    expect(screen.getByRole('button', { name: 'Export PDF' }).hasAttribute('disabled')).toBe(true)
  })
  it('makes an unauthorized export failure visible to the user', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401 }))
    renderAt('/app/england/equity')
    fireEvent.click(screen.getByRole('button', { name: 'Export PDF' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Export failed (401)')
  })
})
