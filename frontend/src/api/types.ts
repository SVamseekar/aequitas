export interface HeadlineStat {
  value: number
  label: string
  severity: "high" | "medium" | "low"
}

export interface DimensionOverview {
  id: string
  name: string
  headline_stat: HeadlineStat
  summary: string
  route: string
}

export interface OverviewResponse {
  dimensions: DimensionOverview[]
  built_at?: string
  score?: number | null
  score_note?: string | null
  score_n_areas?: number | null
  score_dropped?: string[]
}

export interface ScoreComponent {
  id: string
  label: string
  design_weight: number
  weight_used: number
  value: number | null
  missing: boolean
}

export interface TimePoint {
  pack_id: string
  as_of: string
  value: number | null
  n_areas: number | null
  current?: boolean
}

export interface TimeSeriesResponse {
  country: string
  region: string
  urban_rural: string
  metric: string
  area_noun: string
  points: TimePoint[]
  one_date: boolean
  empty: boolean
  empty_reason: string | null
  note: string
  current?: string
}

export interface PackDateRow {
  pack_id: string
  as_of: string
  current?: boolean
  score?: number | null
  pct_400m?: number | null
  n_areas?: number | null
}

export interface PacksResponse {
  england: { packReady: boolean; dates?: PackDateRow[] }
  ireland: { packReady: boolean; dates?: PackDateRow[] }
  netherlands: { packReady: boolean }
  france: { packReady: boolean }
}

export interface ScoreResponse {
  score: number | null
  components: ScoreComponent[]
  dropped: string[]
  n_areas: number | null
  note: string | null
  formula: string
  filter: { region: string; urban_rural: string }
}

export interface MapArea {
  area_code: string
  area_name: string
  value: number
}

export interface MapResponse {
  geography: string
  metric_label: string
  data: MapArea[]
  empty: boolean
  empty_reason: string | null
  title_count?: number
}

export interface ReachResponse {
  available: boolean
  geographies: string[]
  dest_type: string
  cutoff: number
  median: number | null
  n_areas: number
  histogram: { bin: string; n: number }[]
  ranked: { lsoa: string; value: number }[]
  note: string | null
  region_name?: string
  unit?: string
}

export interface ReachBandRow {
  band: number
  imd_decile: number
  people: number
  n_areas: number
}

export interface ReachBandsResponse {
  empty: boolean
  empty_reason: string | null
  mode: string
  label?: string
  not_tfl_ptal: boolean
  hansen_available: boolean
  hansen_note?: string
  map: {
    geography: string
    metric_label?: string
    color_mode?: string
    data: {
      area_code: string
      area_name: string
      value: number
      people?: number
      imd_decile?: number | null
      why?: string
      hover?: string
    }[]
  }
  people_by_band_decile: ReachBandRow[]
  band_totals: { band: number; label: string; people: number; n_areas: number }[]
  n_areas: number
  people: number
  pct_worst_two: number | null
  narrative: string
  formula: string
  geographies_with_times: string[]
  coverage_400m_share?: number | null
  map_aggregation?: string | null
  unmatched_people?: number
  unmatched_areas?: number
  unmatched_note?: string | null
}

export interface SectionItem {
  section_id: string
  dimension: string
  stats: Record<string, unknown>
  chart_data: Record<string, unknown>
  narrative: string
  suppressed: boolean
}

export interface SectionsResponse {
  dimension: string
  sections: SectionItem[]
}

export interface ProvenanceResponse {
  metric_id: string
  value: number
  formula: string
  inputs: Record<string, string>
  source_files: string[]
  description?: string
  notebook?: string
  input_values?: Record<string, unknown>
}

export interface LsoaResponse {
  rows: Record<string, unknown>[]
  total: number
}

export interface ChatChunkEvent {
  text: string
}

export interface ChatDoneEvent {
  conversation_id: string
  sources: string[]
}

export interface ChatErrorEvent {
  message: string
  code: string
}
