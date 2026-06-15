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
