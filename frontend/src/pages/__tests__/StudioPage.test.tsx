import { beforeEach, describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter, Route, Routes, useNavigate } from "react-router"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import StudioPage from "../StudioPage"
import { withSearch } from "@/lib/appRoutes"

const request = vi.hoisted(() => vi.fn())
vi.mock('@/api/client', () => ({ fetchJson: request }))
vi.mock('@/api/hooks', async importOriginal => ({
  ...await importOriginal<typeof import('@/api/hooks')>(),
  usePackDates: () => ({ data: { england: { dates: [{ pack_id: '2026-08-01', as_of: '2026-08-01', current: true }] } } }),
}))

function NavigateContext() {
  const navigate = useNavigate()
  return <><button onClick={() => navigate('/app/ireland/studio')}>Switch Ireland</button><button onClick={() => navigate('/app/england/studio?region=E12000005')}>Return England</button></>
}

vi.mock("@/components/studio/StudioEditorMap", () => ({
  default: () => <div data-testid="studio-editor-map">editor</div>,
}))
vi.mock("@/components/studio/StudioResultMap", () => ({
  default: () => <div data-testid="studio-result-map">result</div>,
}))

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/app/:country/studio" element={<><NavigateContext /><StudioPage /></>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe("Studio routes", () => {
  beforeEach(() => {
    const values = new Map<string, string>()
    const storage: Storage = {
      get length() { return values.size },
      clear: () => values.clear(),
      getItem: key => values.get(key) ?? null,
      key: index => [...values.keys()][index] ?? null,
      removeItem: key => { values.delete(key) },
      setItem: (key, value) => { values.set(key, value) },
    }
    Object.defineProperty(window, 'localStorage', { value: storage, configurable: true })
    request.mockReset()
  })
  it('keeps the operations panel and download availability in sync when editing a draft', () => {
    renderAt('/app/england/studio?region=E12000005')
    fireEvent.click(screen.getByRole('button', { name: 'Add frequency uplift (needs r5py)' }))
    expect(screen.getByTestId('studio-patch-list').textContent).toContain('Frequency ×1.5')
    expect(screen.getByRole('button', { name: 'Download patch JSON' }).hasAttribute('disabled')).toBe(false)
    fireEvent.click(screen.getByRole('button', { name: 'Remove operation 1' }))
    expect(screen.getByRole('button', { name: 'Download patch JSON' }).hasAttribute('disabled')).toBe(true)
    expect(screen.getByRole('button', { name: 'Apply patch' }).hasAttribute('disabled')).toBe(true)
  })
  it("keeps studio as its own page, not a dimension slug", () => {
    renderAt("/app/england/studio?region=E12000005&urban_rural=rural")
    expect(screen.getByRole('heading', { name: /Studio/ })).toBeTruthy()
    expect(screen.getByTestId("studio-patch-list")).toBeTruthy()
  })

  it("Netherlands studio is not an empty-pack sentence", () => {
    renderAt("/app/netherlands/studio")
    expect(screen.queryByText(/Netherlands pack is not built yet/i)).toBeNull()
    expect(screen.getByText(/calculations are not available for Netherlands/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Add frequency uplift (needs r5py)' }))
    expect(screen.getByRole('button', { name: 'Apply patch' })).toBeDisabled()
  })

  it('restores separate country/filter drafts without importing the legacy unscoped patch', () => {
    window.localStorage.setItem('aequitas.studio.lastPatch', JSON.stringify({ ops: [{ op: 'add_stop', lat: 52, lon: -1 }] }))
    renderAt('/app/england/studio?region=E12000005')
    expect(screen.getByTestId('studio-patch-list').textContent).toContain('Draft edits (0)')
    fireEvent.click(screen.getByRole('button', { name: 'Add frequency uplift (needs r5py)' }))
    fireEvent.click(screen.getByRole('button', { name: 'Switch Ireland' }))
    expect(screen.getByTestId('studio-patch-list').textContent).toContain('Draft edits (0)')
    fireEvent.click(screen.getByRole('button', { name: 'Return England' }))
    expect(screen.getByTestId('studio-patch-list').textContent).toContain('Draft edits (1)')
    expect(window.localStorage.getItem('aequitas.studio.lastPatch')).toBeTruthy()
  })

  it('does not start calculations for historical warehouses', () => {
    renderAt('/app/england/studio?pack=2025-01-01')
    fireEvent.click(screen.getByRole('button', { name: 'Add frequency uplift (needs r5py)' }))
    expect(screen.getByRole('button', { name: 'Apply patch' })).toBeDisabled()
    expect(request).not.toHaveBeenCalled()
  })

  it('allows the explicitly selected current network date', () => {
    renderAt('/app/england/studio?pack=2026-08-01')
    fireEvent.click(screen.getByRole('button', { name: 'Add frequency uplift (needs r5py)' }))
    expect(screen.getByRole('button', { name: 'Apply patch' })).not.toBeDisabled()
  })

  it('displays missing impact values and disables impact exports before a run', () => {
    renderAt('/app/england/studio?view=gains')
    expect(screen.getByText(/Result layout preview/)).toBeTruthy()
    expect(screen.getAllByText('—')).toHaveLength(20)
    fireEvent.click(screen.getByRole('link', { name: 'Export' }))
    expect(screen.getByRole('checkbox', { name: /Winners/ })).toBeDisabled()
    expect(screen.getByRole('checkbox', { name: /Research/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Download selected files' })).toBeDisabled()
  })

  it('uses coverage colours rather than change colours for baseline and after legends', () => {
    renderAt('/app/england/studio?view=results')
    fireEvent.click(screen.getByRole('button', { name: 'Baseline' }))
    expect(screen.getByText('Outside 400 m')).toBeTruthy()
    expect(screen.getByText('Within 400 m')).toBeTruthy()
    expect(screen.queryByText('People lost')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Difference' }))
    expect(screen.getByText('People lost')).toBeTruthy()
    expect(screen.getByText('No change')).toBeTruthy()
  })

  it('holds submission state immediately and discards a late response after context changes', async () => {
    let resolve: (value: unknown) => void = () => {}
    request.mockImplementation(() => new Promise(done => { resolve = done }))
    renderAt('/app/england/studio?region=E12000005')
    fireEvent.click(screen.getByRole('button', { name: 'Add frequency uplift (needs r5py)' }))
    fireEvent.click(screen.getByRole('button', { name: 'Apply patch' }))
    expect(screen.getByRole('button', { name: 'Calculating…' })).toBeDisabled()
    expect(JSON.parse(request.mock.calls[0][2].body)).toMatchObject({ country: 'england', region: 'E12000005' })
    fireEvent.click(screen.getByRole('button', { name: 'Switch Ireland' }))
    resolve({ id: 'fixture-run', status: 'done', result: { patch: { country: 'england' } } })
    await waitFor(() => expect(screen.getByTestId('studio-patch-list').textContent).toContain('Draft edits (0)'))
    expect(screen.queryByRole('button', { name: 'View completed run' })).toBeNull()
  })

  it('reviews parsed uploads before adding operations to the draft', async () => {
    request.mockResolvedValue({ ok: true, error: null, ops: [{ op: 'add_stop', lat: 52.48, lon: -1.9 }] })
    renderAt('/app/england/studio?region=E12000005&view=upload')
    const file = new File(['lat,lon\n52.48,-1.9'], 'stops.csv', { type: 'text/csv' })
    Object.defineProperty(file, 'text', { value: () => Promise.resolve('lat,lon\n52.48,-1.9') })
    fireEvent.change(screen.getByLabelText('Upload network patch'), { target: { files: [file] } })
    await screen.findByRole('button', { name: 'Add reviewed operations' })
    expect(JSON.parse(request.mock.calls[0][2].body)).toMatchObject({ country: 'england', region: 'E12000005' })
    fireEvent.click(screen.getByRole('button', { name: 'Add reviewed operations' }))
    expect(screen.getByTestId('studio-patch-list').textContent).toContain('52.4800, -1.9000')
  })

  it("London × rural is one sentence", () => {
    renderAt("/app/england/studio?region=E12000007&urban_rural=rural")
    expect(screen.getByText(/no rural LSOAs/i)).toBeTruthy()
  })

  it("withSearch keeps filters on the studio path", () => {
    expect(withSearch("/app/england/studio", "region=E12000005&urban_rural=rural")).toEqual({
      pathname: "/app/england/studio",
      search: "?region=E12000005&urban_rural=rural",
    })
  })
})
