/** English labels for the compare slope — never snake_case keys. */

export const COMPARE_METRICS = [
  { id: "pct_within_400m", label: "People within 400 m of a stop" },
  { id: "evening_isolated", label: "Evening isolated" },
  { id: "in_country_score", label: "In-country score" },
  { id: "jobs_45", label: "45-minute jobs (median destinations)" },
] as const

export type CompareMetricId = (typeof COMPARE_METRICS)[number]["id"]

export function compareMetricLabel(id: string): string {
  return COMPARE_METRICS.find((m) => m.id === id)?.label ?? id.replace(/_/g, " ")
}
