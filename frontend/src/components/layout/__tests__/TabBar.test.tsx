import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TabBar } from '../TabBar'

describe('grouped application navigation', () => {
  afterEach(() => vi.unstubAllGlobals())
  it('starts compact on mobile and opens the full navigation on demand', () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() }))
    vi.stubGlobal('scrollTo', vi.fn())
    const result = render(<MemoryRouter initialEntries={['/app/england']}><Routes><Route path='/app/:country' element={<TabBar />} /></Routes></MemoryRouter>)
    expect(result.container.querySelector('details')).not.toHaveAttribute('open')
    fireEvent.click(screen.getByRole('button', { name: 'More' }))
    expect(result.container.querySelector('details')).toHaveAttribute('open')
    expect(screen.getByRole('link', { name: 'Reach' })).toBeTruthy()
  })
  it('keeps the country, date and area context when navigating from the sidebar', () => {
    render(<MemoryRouter initialEntries={['/app/netherlands?region=utrecht&urban_rural=rural&mode=all&pack=2026-08-13']}>
      <Routes><Route path='/app/:country' element={<TabBar />} /></Routes>
    </MemoryRouter>)
    expect(screen.getByRole('navigation', { name: 'Application' })).toBeTruthy()
    for (const group of ['Explore', 'Plan', 'Observe', 'Workspace']) expect(screen.getByText(group)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Overview' }).getAttribute('aria-current')).toBe('page')
    const href = screen.getByRole('link', { name: 'Compare' }).getAttribute('href')!
    const url = new URL(href, 'http://localhost')
    expect(url.pathname).toBe('/app/netherlands/compare')
    expect(Object.fromEntries(url.searchParams)).toEqual({ region: 'utrecht', urban_rural: 'rural', pack: '2026-08-13', mode: 'all' })
    expect(screen.getByRole('link', { name: 'Saved work' }).getAttribute('href')).toBe('/saved')
  })
})
