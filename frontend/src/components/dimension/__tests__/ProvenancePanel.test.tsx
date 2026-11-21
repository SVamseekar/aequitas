import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ProvenancePanel } from '../ProvenancePanel'
const request = vi.hoisted(() => vi.fn().mockResolvedValue({ metric_id: 'gini_national', value: 0.2, formula: 'Country fixture formula', inputs: { weighting: 'Country population' }, source_files: ['Ireland source'] }))
vi.mock('@/api/client', () => ({ fetchJson: request }))
describe('Provenance scope', () => {
  it('focuses an accessible drawer, closes with Escape and returns focus to the trigger', async () => {
    function Harness() {
      const [open, setOpen] = useState(false)
      return <><button onClick={() => setOpen(true)}>Open evidence</button>{open && <ProvenancePanel metricId='gini_national' onClose={() => setOpen(false)} />}</>
    }
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter initialEntries={['/app/ireland/equity']}><Routes><Route path='/app/:country/equity' element={<Harness />} /></Routes></MemoryRouter></QueryClientProvider>)
    const opener = screen.getByRole('button', { name: 'Open evidence' })
    opener.focus(); fireEvent.click(opener)
    expect(await screen.findByRole('dialog', { name: 'Data provenance' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Close provenance panel' })).toHaveFocus()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(opener).toHaveFocus()
  })
  it('requests country and pack provenance and identifies its national scope', async () => {
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter initialEntries={['/app/ireland/equity?pack=2026-08-13&region=cork']}><Routes><Route path='/app/:country/equity' element={<ProvenancePanel metricId='gini_national' onClose={() => {}} />} /></Routes></MemoryRouter></QueryClientProvider>)
    await screen.findByText('Ireland source')
    expect(screen.getByText('0.2000')).toBeInTheDocument()
    expect(screen.getByText('Country population')).toBeInTheDocument()
    expect(request.mock.calls.at(-1)![1]).toEqual({ country: 'ireland', pack: '2026-08-13' })
    expect(screen.getByText(/national metric provenance/i)).toBeTruthy()
  })
})
