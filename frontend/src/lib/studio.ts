export interface StudioOp {
  op: 'add_stop' | 'remove_stop' | 'add_trips' | 'frequency_uplift'
  lat?: number
  lon?: number
  name?: string
  factor?: number
  extra_trips?: number
  line?: number[][]
  source?: 'drawn' | 'upload'
}
export interface StudioPatch {
  country: string
  region: string
  urban_rural: string
  ops: StudioOp[]
  source: string
}
export interface StudioJob {
  id: string
  status: 'running' | 'done' | 'error'
  stage?: 'validated' | 'baseline' | 'coverage' | 'results'
  patch?: StudioPatch
  error?: string | null
  result?: StudioResult | null
}
export interface StudioResult {
  ok: boolean
  mode: string
  note: string
  patch: StudioPatch
  score_before: number | null
  score_after: number | null
  people_gained: number
  people_lost: number
  n_areas: number
  deciles: { imd_decile: number; people_gained: number; people_lost: number }[]
  areas: {
    area: string; name?: string; lat?: number; lon?: number; pop: number
    imd_decile: number | null; covered_before: boolean; covered_after: boolean; delta_people: number
  }[]
  reach_available: boolean
  needs_r5py: boolean
  narrative: string
  default_region_note?: string | null
}
export const studioViews = ['edit', 'upload', 'job', 'results', 'gains', 'export'] as const
export type StudioView = typeof studioViews[number]
export const studioViewNames: Record<StudioView, string> = {
  edit: 'Edit', upload: 'Upload', job: 'Job stages', results: 'Results', gains: 'Who gains', export: 'Export',
}
export function operationLabel(op: StudioOp) {
  if (op.op === 'frequency_uplift') return `Frequency ×${op.factor ?? '—'} / +${op.extra_trips ?? 0} trips`
  if (op.op === 'add_trips') return `New corridor (${op.line?.length ?? 0} vertices)`
  return `${op.op === 'add_stop' ? 'Add' : 'Remove'} stop ${op.name ?? ''} ${op.lat?.toFixed(4)}, ${op.lon?.toFixed(4)}`
}
export function hasStudioImpact(result: StudioResult | null) {
  return Boolean(result?.ok && result.n_areas > 0 && result.areas.length > 0)
}
export function downloadStudioPatch(patch: StudioPatch) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(patch, null, 2)], { type: 'application/json' }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'studio-patch.json'
  anchor.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
