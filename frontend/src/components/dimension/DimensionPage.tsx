import {AccessSupportingEvidence} from '@/components/access/AccessSupportingEvidence'
import {DensityEvidence} from '@/components/access/DensityEvidence'
import {EquityEvidence} from './EquityEvidence'
import { Component, type ReactNode } from "react"
import { Download, AlertTriangle } from "lucide-react"
import { Link,useParams, useSearchParams } from "react-router"
import { useState } from 'react'
import { useFilters, useSections } from "@/api/hooks"

import { DIMENSION_API_IDS, AREA_TYPES, regionsForCountry, dimensionsForCountry } from "@/lib/constants"
import { COUNTRIES } from "@/lib/constants"
import { filterImpossibleSections, isLondonRural } from "@/lib/uniqueExhibits"
import { evidenceView } from '@/lib/evidenceViews'
import { EvidenceNavigation } from './EvidenceNavigation'
import { filterSentence } from "@/lib/scoreFormat"
import { SectionCard } from "./SectionCard"
import { ScenarioBuilder } from "./ScenarioBuilder"
import { ScenarioComparison } from './ScenarioComparison'
import { ScenarioOverview } from './ScenarioOverview'
import { CountryCorrelations } from './CountryCorrelations'
import { AccessReachPanel } from "@/components/access/AccessReachPanel"
import { FacilityAccessPanel } from "@/components/access/FacilityAccessPanel"
import { AccessCoverage } from '@/components/access/AccessCoverage'
import { AccessDeserts } from '@/components/access/AccessDeserts'
import { AccessSettlement } from '@/components/access/AccessSettlement'
import { OperatingHours } from '@/components/service/OperatingHours'
import { ServiceRoutes } from '@/components/service/ServiceRoutes'
import { ServiceEvidence } from '@/components/service/ServiceEvidence'
import { ServiceSummary } from '@/components/service/ServiceSummary'
import { NetworkDistribution } from '@/components/network/NetworkDistribution'
import { NetworkMix } from '@/components/network/NetworkMix'
import { NetworkSummary } from '@/components/network/NetworkSummary'
import { NetworkArchetypes } from '@/components/network/NetworkArchetypes'
import { NetworkRelationship } from '@/components/network/NetworkRelationship'
import { CorrelationDomains } from './CorrelationDomains'
import { CorrelationModel } from './CorrelationModel'
import { CorrelationGroups } from './CorrelationGroups'
import { CorrelationRelationship } from './CorrelationRelationship'
import { CorrelationRural } from './CorrelationRural'
import { EconomicEvidence } from './EconomicEvidence'
import { PolicyEvidence } from './PolicyEvidence'
import {EvidenceState} from '@/components/shared/EvidenceState'
import { PackContext } from './PackContext'
import { ScenarioModel } from './ScenarioModel'
import { BriefingActions } from '@/components/shared/BriefingActions'

// Error boundary to catch rendering crashes in child components
interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

class DimensionErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <AlertTriangle className="w-8 h-8 text-red-400/60 mb-3" />
          <p className="text-sm text-foreground font-medium">Something went wrong rendering this page.</p>
          <p className="text-xs text-muted-foreground mt-1">{this.state.error?.message}</p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="mt-4 px-4 py-1.5 text-xs font-mono border border-border rounded hover:bg-muted transition-colors"
          >
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

function DimensionPageContent() {
  const { dimensionSlug } = useParams<{ dimensionSlug: string }>()
  const [params] = useSearchParams()
  const [exportError, setExportError] = useState<string | null>(null)
  const { country, region, urbanRural, pack, mode } = useFilters()
  const dim = dimensionsForCountry(country).find((d) => d.route === `/${dimensionSlug}` || d.id === dimensionSlug)
  const apiDimensionId = DIMENSION_API_IDS[dimensionSlug ?? ""] ?? dim?.id ?? dimensionSlug ?? ""
  const countryName = COUNTRIES.find((c) => c.code === country)?.name ?? country
  const { data, isLoading, error,refetch } = useSections(apiDimensionId, region, urbanRural, country, pack, mode)
  const regionName = regionsForCountry(country).find((r) => r.code === region)?.name ?? region
  const areaName = AREA_TYPES.find((a) => a.code === urbanRural)?.name ?? urbanRural

  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-48 app-glass animate-pulse rounded-2xl" />
        ))}
      </div>
    )
  }

  if (error) {
    const missing=(error as Error&{status?:number}).status===404
    return <EvidenceState kind={missing?'unavailable':'error'} title={missing?'Not available in this pack':'Could not load evidence'} description={missing?`No matching pack or evidence for ${countryName} · ${pack||'current network'}. No other country or date is substituted.`:'Your selected country and filters are retained. Please retry.'} retry={()=>void refetch()} />
  }

  // Show all sections that have any content (stats, chart, or narrative)
  const sections = data?.sections.filter(
    (s) =>
      Object.keys(s.stats ?? {}).length > 0 ||
      Object.keys(s.chart_data ?? {}).length > 0 ||
      (s.narrative?.trim().length ?? 0) > 0
  ) ?? []

  const unique = filterImpossibleSections(
    sections,
    urbanRural,
  )
  const londonRural = isLondonRural(region, urbanRural)
  const showUrbanDrtNote = apiDimensionId === "scenarios" && urbanRural === "urban"
  const packReady = COUNTRIES.find((c) => c.code === country)?.packReady ?? false
  const packMissing = !packReady
  const impossibleGeographyCopy = londonRural
    ? `London has no rural LSOAs under the official urban/rural classification — this ${countryName} filter is empty.`
    : packMissing
      ? `${countryName} pack is not built yet. England and Ireland are live; the method is the same.`
      : null

  if (unique.length === 0 || londonRural || packMissing) {
    const reset=new URLSearchParams(params);reset.set('urban_rural','all')
    return <EvidenceState kind={londonRural?'empty':'unavailable'} title={londonRural?'No areas match this filter':'Not available in this pack'} description={impossibleGeographyCopy??`No stored ${dim?.name??'analytical'} exhibits for ${countryName} · ${regionName} · ${areaName}. Missing results remain unavailable.`} action={londonRural?<Link className='app-panel-button' to={{search:`?${reset}`}}>Reset area filter</Link>:undefined} />
  }

  const exportParams = new URLSearchParams({ country,region, urban_rural: urbanRural,mode,...(pack?{pack}:{}) })
  const exportUrl = `/api/export/${encodeURIComponent(apiDimensionId)}?${exportParams}`
  const exportSupported = country === 'england' && ['', 'current','latest'].includes(pack.toLowerCase()) && mode !== 'all'
  const view = evidenceView(apiDimensionId,params.get('view'),params.get('exhibit'))
  const candidates = unique.filter(s => view?.sections.includes(s.section_id))
  const requestedExhibit = params.get('exhibit') ?? params.get('view')
  const selected = candidates.find(s => s.section_id === requestedExhibit) ?? candidates[0]
  const selectedScope = filterSentence(regionName, areaName)
  const scopeLabel = selectedScope === countryName ? countryName : `${countryName} · ${selectedScope}`
  const accessHeading=view?.id==='density'?'Access — density & distribution':view?.id==='a4_coverage_equity'?'Access — service distribution':['a3_walking_distance','a5_service_deserts'].includes(view?.id??'')?'Access to public transport':'Where the bus fails people'
  const equityHeading=view?.id==='f3_ethnic_access'||view?.id==='f5_rural_penalty'?'Equity — social access & rural gap':'Where the bus fails people'
  const pageHeading=apiDimensionId==='equity'?equityHeading:apiDimensionId==='economic'?`Economy — ${view?.label??'Annual value'}`:apiDimensionId==='bus_services_act'?`Policy — ${view?.label??'Readiness'}`:apiDimensionId==='service_quality'?'Service':apiDimensionId==='route_network'?'Network':null
  const correlationHeading=country!=='england'?`Correlations · ${countryName}`:view?.id==='domains'?'Correlations — deprivation domains':['g3_coverage_model','features'].includes(view?.id??'')?'Bus-service prediction':'Correlations'

  const handleExportPdf = async () => {
    setExportError(null)
    try {
    const resp = await fetch(exportUrl, { credentials: "include" })
    if (!resp.ok) throw new Error(`Export failed (${resp.status})`)
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement("a")
    anchor.href = url
    anchor.download = `aequitas_${apiDimensionId}_${region}_${urbanRural}.pdf`
    anchor.click()
    URL.revokeObjectURL(url)
    } catch (error) {
      setExportError(error instanceof Error ? error.message : 'Export could not be completed.')
    }
  }

  return (
    <div className='dimension-page' data-dimension={apiDimensionId} data-view={view?.id}>
      {showUrbanDrtNote && (
        <p role="status" className="mb-4 text-sm text-muted-foreground">
          Demand-responsive rural scenarios do not apply to an urban-only filter — that card is hidden.
        </p>
      )}
      <div className="app-page-heading">
        <div>
          <h1 className="text-xl font-semibold text-foreground tracking-tight">
            {apiDimensionId === 'accessibility'?accessHeading:apiDimensionId==='correlations'?correlationHeading:apiDimensionId === 'scenarios' ? `${dim?.name} — ${view?.label}` : pageHeading?(country==='england'?pageHeading:`${pageHeading} · ${countryName}`):`${dim?.name} — ${filterSentence(regionName, areaName)}`}
          </h1>
          <p className="text-muted-foreground text-sm mt-1">{apiDimensionId === 'accessibility'?`${scopeLabel} · official timetables × official need`:apiDimensionId==='correlations'?`${scopeLabel} · ${view?.label??'area-level evidence'}`:apiDimensionId === 'scenarios' ? `${scopeLabel} · indicative service scenarios` : ['equity','service_quality','route_network','bus_services_act'].includes(apiDimensionId)?`${scopeLabel} · official timetables × official need`:dim?.description}</p>
        </div>
        <div className='flex gap-3 items-center'><BriefingActions /><button
          type="button"
          onClick={() => void handleExportPdf()}
          disabled={!exportSupported}
          title={exportSupported ? 'Download this briefing' : 'PDF export supports the current England network only'}
          className="app-btn-primary flex items-center gap-2 px-3.5 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Download className="w-3.5 h-3.5" />
          Export PDF
        </button></div>
      </div>
      {exportError && <p role='alert' className='text-destructive text-sm mb-4'>{exportError}</p>}
      {!exportSupported && <p className='export-scope-note text-xs text-muted-foreground'>PDF requires the current England network.</p>}
      {apiDimensionId === 'correlations' && country !== 'england' ? <CountryCorrelations sections={unique} /> : <><EvidenceNavigation dimension={apiDimensionId} country={country} sections={unique} />

      {/* Scenario builder — only on scenarios dimension */}
      {view?.panel === 'custom' ? country === 'england' ? <ScenarioBuilder /> : <p className='app-panel'>Custom indicative controls are available for England only.</p>
        : view?.panel === 'facilities' ? <FacilityAccessPanel />
        : view?.panel === 'destinations' ? <AccessReachPanel />
        : view?.panel === 'density' ? <DensityEvidence sections={unique.filter(section=>view.sections.includes(section.section_id))} />
        : view?.panel === 'domains' ? <CorrelationDomains sections={unique.filter(section=>view.sections.includes(section.section_id))} />
        : view?.panel === 'assumptions' ? <PackContext sections={unique} />
        : view?.panel === 'policy-context' ? <PackContext sections={unique} policy />
        : view?.panel === 'table' ? <ServiceEvidence section={unique.find(section => section.section_id === 'b5_frequency_deprivation')} table />
        : selected?.section_id === 'ps5_scenario_comparison' ? <ScenarioComparison section={selected} country={country} sources={unique} />
        : selected && apiDimensionId === 'scenarios' && selected.stats.scenario ? <ScenarioOverview section={selected} />
        : selected?.section_id === 'a3_walking_distance' ? <AccessCoverage section={selected} />
        : selected?.section_id === 'a5_service_deserts' ? <AccessDeserts section={selected} />
        : selected?.section_id === 'a6_urban_rural_gap' && country === 'england' ? <AccessSettlement section={selected} />
        : selected && country==='england' && ['a7_investment_gap','a8_coverage_prediction'].includes(selected.section_id) ? <AccessSupportingEvidence section={selected} />
        : selected?.section_id === 'b5_frequency_deprivation' ? <ServiceEvidence section={selected} table={false} />
        : selected?.section_id === 'b2_operating_hours' && country === 'england' ? <OperatingHours section={selected} />
        : selected?.section_id === 'b4_route_frequency' && country === 'england' ? <ServiceRoutes section={selected} />
        : selected && country === 'england' && ['b1_frequency','b3_weekend_penalty'].includes(selected.section_id) ? <ServiceSummary section={selected} sections={unique} />
        : selected && country === 'england' && ['c1_route_length','c2_stops_per_route'].includes(selected.section_id) ? <NetworkDistribution section={selected} />
        : selected?.section_id === 'c4_urban_rural_routes' && country === 'england' ? <NetworkMix section={selected} />
        : selected && country === 'england' && ['c3_operator_hhi','c7_network_topology'].includes(selected.section_id) ? <NetworkSummary section={selected} />
        : selected?.section_id === 'c6_route_archetypes' && country === 'england' ? <NetworkArchetypes section={selected} />
        : selected?.section_id === 'c5_length_vs_frequency' && country === 'england' ? <NetworkRelationship section={selected} />
        : selected?.section_id === 'g1_route_clusters' && country === 'england' ? <NetworkArchetypes section={selected} />
        : selected && country === 'england' && ['d1_coverage_deprivation','d2_coverage_unemployment','d3_coverage_car','d4_coverage_elderly'].includes(selected.section_id) ? <CorrelationRelationship section={selected} />
        : selected && country === 'england' && ['g3_coverage_model','d8_feature_importance','g4_shap'].includes(selected.section_id) ? <CorrelationModel section={selected} />
        : selected && country === 'england' && ['d6_transport_poverty','g2_anomalies'].includes(selected.section_id) ? <CorrelationGroups section={selected} />
        : selected?.section_id==='d7_deprivation_urban_rural'&&country==='england'?<CorrelationRural section={selected} />
        : selected?.section_id === 'g5_scenario_model' && country === 'england' ? <ScenarioModel section={selected} />
        : selected && country === 'england' && apiDimensionId === 'economic' ? <EconomicEvidence section={selected} />
        : selected && country === 'england' && apiDimensionId === 'bus_services_act' ? <PolicyEvidence section={selected} sections={unique} />
        : selected && country==='england' && (apiDimensionId==='equity'||selected.section_id==='a4_coverage_equity') ? <EquityEvidence section={selected} />
        : selected ? <SectionCard key={selected.section_id} section={selected} featured />
        : <p className='app-panel'>This exhibit is unavailable for the selected country and filter.</p>}</>}
    </div>
  )
}

export function DimensionPage() {
  return (
    <DimensionErrorBoundary>
      <DimensionPageContent />
    </DimensionErrorBoundary>
  )
}
