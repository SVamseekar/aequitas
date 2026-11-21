import { useFilters, useOps } from "@/api/hooks"
import { AREA_TYPES, COUNTRIES, regionsForCountry } from "@/lib/constants"
import { filterSentence } from "@/lib/scoreFormat"
import { Link, useSearchParams } from 'react-router'
import { OpsEvidence } from '@/components/ops/OpsEvidence'
import { OpsCountryScope } from '@/components/ops/OpsCountryScope'
import { BriefingActions } from '@/components/shared/BriefingActions'

function feedNoun(country: string): string {
  if (country === "ireland") {
    return "NTA TripUpdates via TFI. Dublin Bus, Bus Éireann, and Go-Ahead Ireland only. Small Area nouns stay on the static pack"
  }
  if (country === "netherlands") {
    return "OVapi GTFS-RT (mixed mode; briefing default stays bus). SES / buurten stay on the static pack"
  }
  if (country === "france") {
    return "NAP gtfs-rt sample. Not a national AOM figure. DOM out. F-EDI / IRIS stay on the static pack"
  }
  return "BODS GTFS-RT / SIRI-VM (OGL). Joined to existing stop → LSOA only — no Census re-download"
}

export default function OpsPage() {
  const { country, region, urbanRural, pack } = useFilters()
  const countryName = COUNTRIES.find((c) => c.code === country)?.name ?? country
  const regionName = regionsForCountry(country).find((r) => r.code === region)?.name ?? region
  const areaName = AREA_TYPES.find((a) => a.code === urbanRural)?.name ?? urbanRural
  const place = filterSentence(regionName, areaName)
  const ops = useOps(country, pack)
  const [params] = useSearchParams()
  const view = ['snapshot', 'regional', 'deprivation', 'sources'].includes(params.get('view') ?? '') ? params.get('view')! : 'snapshot'

  const errStatus = (ops.error as { status?: number } | null)?.status
  const unknownPack =
    errStatus === 404 && Boolean(pack) && String(ops.error?.message ?? "").includes("Unknown pack")

  return (
    <div data-testid="ops-page" className="ops-page pb-10">
      <div className='ops-heading'><h1 className="text-2xl sm:text-3xl font-semibold tracking-tight mb-1">
        Operations — {country !== 'england' ? countryName : view === 'regional' ? 'regional feed coverage' : view === 'deprivation' ? 'deprivation join' : view === 'sources' ? 'sources' : place}
      </h1><BriefingActions /></div>
      <p className="text-sm text-muted-foreground mb-4 max-w-2xl" title={feedNoun(country)}>
        {countryName} · {country==='england'?'collected feed snapshot and update counts':'real-time public transport data availability'}. Separate from the static equity score.
      </p>
      <nav className='evidence-tabs' aria-label='Operations views'>{[['snapshot','Snapshot'], ['regional','Regional join'], ['deprivation','Deprivation join'], ['sources','Sources']].map(([id,label]) => { const next = new URLSearchParams(params); next.set('view',id); return <Link key={id} to={{search:`?${next}`}} aria-current={view===id?'page':undefined}>{label}</Link> })}</nav>
      <p className='text-xs text-muted-foreground mb-4'>Collector snapshot scope is independent of the static region and area filters.</p>

      {ops.isLoading ? (
        <div className="h-64 app-glass animate-pulse rounded-2xl" />
      ) : unknownPack ? (
        <p className="text-sm text-muted-foreground max-w-xl" data-testid="unknown-pack">
          Unknown pack {pack} for {countryName}. Ops is not time-travelled to a date we did not store.
        </p>
      ) : errStatus === 404 ? (
        <><p className="text-sm text-muted-foreground max-w-xl" data-testid="ops-empty">No ops rollup for {countryName} yet. We do not invent 0% on-time.</p><OpsCountryScope country={country} /></>
      ) : ops.error ? <div role='alert' className='app-panel'><p>Collector observations could not be loaded.</p><button type='button' className='app-panel-button' onClick={() => void ops.refetch()}>Retry operations</button></div> : ops.data?.empty ? (
        <div className="space-y-3">
          <OpsCountryScope country={country} data={ops.data} />
          <details className='ops-collector-note'><summary>Collector availability details</summary><p className="text-sm text-muted-foreground max-w-xl" data-testid="ops-empty">{ops.data.empty_reason}</p></details>
        </div>
      ) : ops.data ? (
        <OpsEvidence data={ops.data} country={country} view={view} />
      ) : (
        <p className="text-sm text-muted-foreground">Ops snapshot could not be loaded.</p>
      )}
    </div>
  )
}
