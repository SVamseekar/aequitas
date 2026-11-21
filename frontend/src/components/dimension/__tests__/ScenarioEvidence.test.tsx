import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ScenarioBuilder } from '../ScenarioBuilder'
import { SectionCard } from '../SectionCard'
import { ScenarioComparison } from '../ScenarioComparison'
import { ScenarioOverview } from '../ScenarioOverview'
const request = vi.hoisted(() => vi.fn().mockResolvedValue({ sections: [] }))
vi.mock('@/api/client', () => ({ fetchJson: request }))
vi.mock('@/components/charts/ChartRenderer', () => ({ ChartRenderer: ({ chartData }: { chartData: Record<string, unknown> }) => <pre data-testid='actual-chart'>{JSON.stringify(chartData)}</pre> }))
vi.mock('@/components/shared/SelectedRegionsMap', () => ({ default: () => <div>Selected geographic boundary</div> }))
function Location() { return <output data-testid='location'>{useLocation().search}</output> }
function renderAt(child: React.ReactNode) {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={['/app/england/scenarios?region=E12000005&pack=current&view=custom']}><Routes><Route path='/app/:country/scenarios' element={<>{child}<Location /></>} /></Routes></MemoryRouter></QueryClientProvider>)
}
describe('Scenario reference and source boundaries', () => {
  it('retains shareable controls while leaving unsupported model outputs unavailable', () => {
    renderAt(<ScenarioBuilder />)
    expect(screen.getByText('Illustrative control state; model outputs require selected assumptions.')).toBeTruthy()
    expect(screen.queryByText('BCR')).toBeNull()
    fireEvent.change(screen.getByRole('slider', { name: 'Frequency uplift' }), { target: { value: '25' } })
    expect(screen.getByTestId('location').textContent).toContain('freq_pct=25')
    expect(screen.getByTestId('location').textContent).toContain('region=E12000005')
    expect(screen.getAllByText('—')).toHaveLength(3)
  })
  it('does not insert a synthetic scenario or per-beneficiary value into stored comparison rows', () => {
    const rows = [{ Scenario: 'Frequency restoration', 'Population affected': 5689818 }, { Scenario: 'Evening', 'Population affected': 8392662 }, { Scenario: 'Rural DRT', 'Population affected': 5243877 }, { Scenario: 'Combined', 'Population affected': 760008 }]
    renderAt(<SectionCard featured section={{ section_id: 'ps5_scenario_comparison', dimension: 'scenarios', suppressed: false, stats: {}, narrative: 'Stored indicative target populations, not new access gains.', chart_data: { type: 'table', data: rows } }} />)
    const payload = JSON.parse(screen.getByTestId('actual-chart').textContent!)
    expect(payload.data).toHaveLength(4)
    expect(JSON.stringify(payload)).not.toContain('Cost/beneficiary')
    expect(JSON.stringify(payload)).not.toContain('My Custom Scenario')
  })
  it('reads country-specific stored comparison rows without supplying England costs', () => {
    const rows = [{ id: 'ps1', title: 'Restore TFI frequency', people: 2538351 }, { id: 'ps2', title: 'Evening TFI', people: 2433930 }, { id: 'ps3', title: 'Rural RTP', people: 1473648 }, { id: 'ps4', title: 'Combined Connecting Ireland', people: 2314347 }]
    renderAt(<ScenarioComparison country='ireland' section={{ section_id: 'ps5_scenario_comparison', dimension: 'scenarios', suppressed: false, stats: { rows }, chart_data: {}, narrative: '' }} />)
    expect(screen.getByRole('table', { name: 'Stored scenario comparison' })).toHaveTextContent('Restore TFI frequency')
    expect(screen.getByRole('table', { name: 'Stored scenario comparison' })).toHaveTextContent('2,538,351')
    expect(screen.getAllByText('—')).toHaveLength(8)
    expect(screen.getAllByText('No stored values for this measure.')).toHaveLength(2)
  })
  it('renders stored target population and unavailable estimates without unsupported narrative claims', () => {
    renderAt(<ScenarioOverview section={{ section_id: 'ps4_franchise', dimension: 'scenarios', suppressed: false,
      stats: { scenario: { name: 'Bus Services Act — franchise top-5 LADs', scope: '5 LADs (highest readiness scores)', population_affected: 760008, estimated_annual_cost_m: null, co2_saving_t_yr: null } },
      chart_data: {}, narrative: 'The recommended priority has the highest BCR.' }} />)
    expect(screen.getAllByText('760,008').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Not modelled')).toHaveLength(2)
    expect(screen.getAllByText('—')).toHaveLength(2)
    expect(screen.getByText(/does not represent newly gained stop access/)).toBeInTheDocument()
    expect(screen.queryByText(/recommended priority/)).toBeNull()
    expect(screen.getByRole('link', { name: 'Open in network Studio' }).getAttribute('href')).toContain('region=E12000005')
    expect(screen.getByRole('link', { name: 'Open in network Studio' }).getAttribute('href')).toContain('pack=current')
  })
  it('exposes conflicting stored scenario populations without silently replacing either observation', () => {
    const source = { section_id: 'ps1_freq_restoration', dimension: 'scenarios', suppressed: false, stats: { scenario: { population_affected: 28704121.48854992 } }, chart_data: {}, narrative: '' }
    renderAt(<ScenarioComparison country='france' sources={[source]} section={{ ...source, section_id: 'ps5_scenario_comparison', stats: { rows: [{ id: 'ps1', title: 'Restore NAP weekday frequency', people: 0 }] } }} />)
    expect(screen.getByRole('alert')).toHaveTextContent('comparison stores 0 people')
    expect(screen.getByRole('alert')).toHaveTextContent('28,704,121.5')
    expect(within(screen.getByRole('table', { name: 'Stored scenario comparison' })).getByText('0', { exact: true })).toBeInTheDocument()
  })
})
