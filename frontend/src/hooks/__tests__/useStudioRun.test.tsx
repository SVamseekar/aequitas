import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useStudioRun } from '../useStudioRun'
import type { StudioPatch, StudioResult } from '@/lib/studio'

const request = vi.hoisted(() => vi.fn())
vi.mock('@/api/client', () => ({ fetchJson: request }))
const patch: StudioPatch = { country: 'england', region: 'E12000005', urban_rural: 'rural', source: 'drawn', ops: [{ op: 'add_stop', lat: 52.48, lon: -1.9 }] }
const fixture: StudioResult = { ok: true, mode: 'walk_to_stop', note: 'Fixture only', patch, score_before: 20, score_after: 21, people_gained: 100, people_lost: 0, n_areas: 1, deciles: [{ imd_decile: 1, people_gained: 100, people_lost: 0 }], areas: [{ area: 'fixture', pop: 100, imd_decile: 1, covered_before: false, covered_after: true, delta_people: 100 }], reach_available: false, needs_r5py: false, narrative: '' }

describe('Studio request lifecycle', () => {
  afterEach(() => { vi.useRealTimers(); request.mockReset() })
  it('retries polling without submitting duplicate calculations', async () => {
    vi.useFakeTimers()
    request.mockResolvedValueOnce({ id: 'fixture', status: 'running', stage: 'baseline' })
      .mockRejectedValueOnce(new Error('Offline'))
      .mockResolvedValueOnce({ id: 'fixture', status: 'done' })
      .mockResolvedValueOnce(fixture)
    const { result } = renderHook(useStudioRun)
    await act(async () => { await result.current.start(patch) })
    expect(result.current.running).toBe(true)
    await act(async () => { await vi.advanceTimersByTimeAsync(1200) })
    expect(result.current.error).toBe('Offline')
    await act(async () => { result.current.retryStatus() })
    expect(result.current.result).toEqual(fixture)
    expect(result.current.submitted).toEqual(patch)
    expect(result.current.running).toBe(false)
    expect(request.mock.calls.filter(call => call[0] === '/studio/jobs')).toHaveLength(1)
  })
  it('shows immediate server failures and permits retrying the submitted patch', async () => {
    request.mockResolvedValueOnce({ id: 'failed', status: 'error', stage: 'coverage', error: 'Coverage failed' })
      .mockResolvedValueOnce({ id: 'retry', status: 'done', result: fixture })
    const { result } = renderHook(useStudioRun)
    await act(async () => { await result.current.start(patch) })
    expect(result.current.error).toBe('Coverage failed')
    expect(result.current.result).toBeNull()
    await act(async () => { await result.current.start(patch) })
    expect(result.current.result).toEqual(fixture)
    expect(result.current.error).toBeNull()
  })
  it('aborts observation on unmount without promising to cancel the server job', async () => {
    vi.useFakeTimers()
    request.mockResolvedValue({ id: 'fixture', status: 'running' })
    const { result, unmount } = renderHook(useStudioRun)
    await act(async () => { await result.current.start(patch) })
    const signal = request.mock.calls[0][2].signal as AbortSignal
    unmount()
    expect(signal.aborted).toBe(true)
    await vi.advanceTimersByTimeAsync(5000)
    expect(request).toHaveBeenCalledTimes(1)
  })
})
