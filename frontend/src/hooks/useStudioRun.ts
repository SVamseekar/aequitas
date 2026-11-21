import { useEffect, useRef, useState } from 'react'
import { fetchJson } from '@/api/client'
import type { StudioJob, StudioPatch, StudioResult } from '@/lib/studio'

export function useStudioRun() {
  const [job, setJob] = useState<StudioJob | null>(null)
  const [result, setResult] = useState<StudioResult | null>(null)
  const [submitted, setSubmitted] = useState<StudioPatch | null>(null)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const request = useRef<AbortController | null>(null)
  const timer = useRef<number | null>(null)
  const busy = useRef(false)
  const cancel = () => {
    request.current?.abort()
    if (timer.current !== null) window.clearTimeout(timer.current)
    timer.current = null
  }
  useEffect(() => () => {
    request.current?.abort()
    if (timer.current !== null) window.clearTimeout(timer.current)
  }, [])

  const observe = async (snapshot: StudioJob, signal: AbortSignal) => {
    if (signal.aborted) return
    setJob(snapshot)
    if (snapshot.status === 'error') {
      busy.current = false
      setError(snapshot.error ?? 'The calculation failed. Review your patch and retry.')
    } else if (snapshot.status === 'done') {
      const body = snapshot.result ?? await fetchJson<StudioResult>(`/studio/jobs/${snapshot.id}/result`, undefined, { signal })
      if (!signal.aborted) { setResult(body); busy.current = false }
    } else {
      timer.current = window.setTimeout(() => { void poll(snapshot.id, signal) }, 1200)
    }
  }
  const poll = async (id: string, signal: AbortSignal) => {
    try {
      await observe(await fetchJson<StudioJob>(`/studio/jobs/${id}`, undefined, { signal }), signal)
    } catch (err) {
      if (!signal.aborted) setError(err instanceof Error ? err.message : 'Could not check the calculation status.')
    }
  }
  const start = async (patch: StudioPatch, pack = '') => {
    if (busy.current) return
    cancel()
    const controller = new AbortController()
    request.current = controller
    busy.current = true
    setStarting(true); setError(null); setJob(null); setResult(null); setSubmitted(patch)
    try {
      const snapshot = await fetchJson<StudioJob>('/studio/jobs', undefined, {
        method: 'POST', body: JSON.stringify({ ...patch, pack }), signal: controller.signal,
      })
      await observe(snapshot, controller.signal)
    } catch (err) {
      if (!controller.signal.aborted) {
        busy.current = false
        setError(err instanceof Error ? err.message : 'Could not start the calculation.')
      }
    } finally {
      if (!controller.signal.aborted) setStarting(false)
    }
  }
  const retryStatus = () => {
    if (!job || !request.current) return
    setError(null)
    void poll(job.id, request.current.signal)
  }
  const reset = () => {
    cancel(); busy.current = false
    setJob(null); setResult(null); setSubmitted(null); setError(null); setStarting(false)
  }
  return { job, result, submitted, error, starting, running: starting || job?.status === 'running', start, retryStatus, reset }
}
