export function formatInCountryScore(score: number | null | undefined): string {
  if (score === null || score === undefined || Number.isNaN(score)) return "—"
  const rounded = Math.round(score * 10) / 10
  return rounded.toFixed(1)
}

export function filterSentence(regionName: string, areaName: string): string {
  const areaAll = !areaName || /^(all)(\s+areas)?$/i.test(areaName)
  if ((regionName === "All England" || regionName === "England") && areaAll) {
    return "England"
  }
  if ((regionName === "All Ireland" || regionName === "Ireland") && areaAll) {
    return "Ireland"
  }
  if ((regionName === "All Netherlands" || regionName === "Netherlands") && areaAll) {
    return "Netherlands"
  }
  const bits = [regionName]
  if (!areaAll) bits.push(areaName.toLowerCase())
  return bits.join(", ")
}
