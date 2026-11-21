import {lazy,Suspense,useCallback,useState} from 'react'
import {Link,useSearchParams} from 'react-router'
import {useQuery} from '@tanstack/react-query'
import {Download,Printer} from 'lucide-react'
import {useFilters,useMapLayer,usePackDates} from '@/api/hooks'
import {fetchJson} from '@/api/client'
import {AREA_TYPES,COUNTRIES,regionsForCountry} from '@/lib/constants'
import {coveragePresentation} from '@/lib/coverage'
import {researchUnavailable,type ResearchPack} from '@/lib/researchExport'

const ChoroplethMap=lazy(()=>import('@/components/charts/ChoroplethMap'))
const finite=(value:unknown):value is number=>typeof value==='number'&&Number.isFinite(value)
const display=(value:unknown,suffix='',digits=1)=>finite(value)?`${value.toLocaleString('en-GB',{minimumFractionDigits:digits,maximumFractionDigits:digits})}${suffix}`:'Unavailable'

export function ResearchExport(){
 const {country,region,urbanRural,pack,mode}=useFilters(),packs=usePackDates()
 const [params]=useSearchParams(),[downloadError,setDownloadError]=useState<string|null>(null),[downloading,setDownloading]=useState(false)
 const mapScope=JSON.stringify([country,region,urbanRural,pack,mode])
 const [mapState,setMapState]=useState<{scope:string;status:'ready'|'unavailable'}|null>(null)
 const onMapStatus=useCallback((status:'ready'|'unavailable')=>setMapState({scope:mapScope,status}),[mapScope])
 const countryName=COUNTRIES.find(row=>row.code===country)?.name??country,regionName=regionsForCountry(country).find(row=>row.code===region)?.name??region,areaName=AREA_TYPES.find(row=>row.code===urbanRural)?.name??urbanRural
 const reason=researchUnavailable(country,pack,mode,packs.data)
 const checkNetwork=!['','current','latest'].includes(pack.toLowerCase())&&country!=='netherlands'
 const context={country,region,urban_rural:urbanRural,dest_type:'jobs',cutoff:'45',...(pack?{pack}:{})}
 const query=useQuery({queryKey:['research-pack',context],queryFn:()=>fetchJson<ResearchPack>('/export/pack.json',context),enabled:!reason,retry:false,staleTime:Infinity})
 const map=useMapLayer(region,urbanRural,country,pack,mode,'coverage')
 const dates=packs.data?.[country]?.dates??[],date=dates.find(row=>row.pack_id===pack||row.as_of===pack)||dates.find(row=>row.current)
 const network=date?.as_of??(pack||'Current network — date unavailable')
 const back=new URLSearchParams(params);back.delete('view')
 const data=query.data,scopeMatches=data?.filter?.country===country&&data?.filter?.region===region&&data?.filter?.urban_rural===urbanRural
 const component=(id:string)=>data?.score.components.find(row=>row.id===id)?.value
 const coverage=component('pop_within_400m'),quality=component('weekday_frequency'),served=component('evening_served')
 const meaning=coveragePresentation(country),search=new URLSearchParams(context)
 const mapPending=map.isPending||!map.error&&!map.data?.empty&&Boolean(map.data?.data.length)&&mapState?.scope!==mapScope
 const downloadCsv=async()=>{
  setDownloading(true);setDownloadError(null)
  try{
   const response=await fetch(`/api/export/pack.csv?${search}`,{credentials:'include'})
   if(!response.ok)throw new Error(`Research CSV could not be downloaded (${response.status}).`)
   const href=URL.createObjectURL(await response.blob()),link=document.createElement('a')
   link.href=href;link.download=`aequitas_${country}_${region}_${urbanRural}_research.csv`;link.click();window.setTimeout(()=>URL.revokeObjectURL(href),1000)
  }catch(error){setDownloadError(error instanceof Error?error.message:'Research CSV could not be downloaded.')}
  finally{setDownloading(false)}
 }
 return <div className='research-export'>
  <div className='app-page-heading research-controls'><div><h1>Export research pack</h1><p>Create a printable briefing with key findings, evidence and source metadata.</p></div><Link className='app-panel-button' to={{search:`?${back}`}}>Return to overview</Link></div>
  {checkNetwork&&packs.isPending?<p className='app-panel' role='status'>Checking selected network…</p>:checkNetwork&&packs.error?<section className='app-panel research-controls' role='alert'><h2>Could not load the network registry</h2><p>Your selection is retained.</p><button type='button' className='app-panel-button' onClick={()=>void packs.refetch()}>Retry network dates</button></section>:reason?<section className='app-panel research-controls'><h2>Research pack unavailable</h2><p>{reason}</p></section>:query.isPending?<p className='app-panel' role='status'>Loading actual research pack…</p>:query.error||!scopeMatches?<section className='app-panel research-controls' role='alert'><h2>Could not load research evidence</h2><p>Your country, region, area and network selection is retained. No other scope is substituted.</p><button type='button' className='app-panel-button' onClick={()=>void query.refetch()}>Retry research pack</button></section>:data&&<>
   <div className='research-export-toolbar research-controls'><p>{countryName} · {regionName} · {areaName} · {network}</p><details><summary className='app-btn-primary'><Download size={15} aria-hidden='true' />Export research pack</summary><div className='research-export-menu'><button type='button' disabled={downloading} onClick={()=>void downloadCsv()}>{downloading?'Downloading…':'CSV (data tables)'}</button><a href={`/api/export/pack.html?${search}`} target='_blank' rel='noopener noreferrer'>Printable HTML (tables)</a><button type='button' disabled={mapPending} onClick={()=>window.print()}><Printer size={15} aria-hidden='true' />Print this preview</button>{mapPending&&<p role='status' className='p-3'>Preparing the coverage map…</p>}</div></details></div>
   {downloadError&&<p className='research-controls' role='alert'>{downloadError}</p>}
   <article className='research-document app-panel'>
    <header className='research-document-brand'><span className='app-wordmark'>Aequitas</span><p>Research pack<br />Not a statutory submission</p></header>
    <h2>Aequitas research briefing — {countryName}</h2><p className='research-scope'>Country: {countryName} · Region: {regionName} · Area: {areaName} · Network: {network}</p>
    <section><h3>Key findings</h3><dl className='research-findings'>
     {[['In-country score',display(data.score.score,' / 100')],
       [meaning.shortLabel,display(finite(coverage)?coverage*100:null,'%')],
       ['Mean service quality',display(finite(quality)?quality*100:null,' / 100')],
       ['Evening isolated',display(finite(served)?(1-served)*100:null,'%')]].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
    </dl></section>
    <div className='research-document-main'><section><h3>Transport coverage across {region==='all'?countryName:regionName}</h3><p>{meaning.definition}</p>
     {map.isPending?<p role='status'>Loading selected coverage map…</p>:map.error?<p>Coverage map unavailable for this selected scope.</p>:map.data?.empty||!map.data?.data.length?<p>{map.data?.empty_reason??'No mapped observations for this scope.'}</p>:<Suspense fallback={<p role='status'>Loading map renderer…</p>}><ChoroplethMap key={mapScope} className='research-map' onStatus={onMapStatus} chartData={{type:'choropleth',geography:map.data.geography,metric_label:map.data.metric_label,data:map.data.data,color_mode:'coverage'}} /></Suspense>}
     <div className='app-coverage-legend' aria-label='Coverage legend'><span>Lower coverage</span><i aria-hidden='true' /><span>Higher coverage</span><span className='text-muted-foreground'>Grey: unavailable</span></div>
    </section><aside><h3>About this pack</h3><p>Evidence describes this country and selected scope. Scores and deprivation ranks remain within {countryName}.</p><p>Stop proximity is separate from computed travel times.</p>{data.score.note&&<p>{data.score.note}</p>}</aside></div>
    <section className='research-appendix'><h3>Appendix: Source metadata and limitations</h3><div className='research-metadata'><dl>{Object.entries(data.vintages).map(([key,value])=><div key={key}><dt>{key.replaceAll('_',' ')}</dt><dd>{value}</dd></div>)}</dl><dl><div><dt>Network date</dt><dd>{network}</dd></div><div><dt>Scope</dt><dd>{countryName} · {regionName} · {areaName}</dd></div><div><dt>Scored areas</dt><dd>{finite(data.score.n_areas)?data.score.n_areas.toLocaleString('en-GB'):'Unavailable'}</dd></div></dl></div>
     <h3>Travel-time results scope</h3><p>{data.reach.available?`${data.reach.n_areas.toLocaleString('en-GB')} computed origin areas · employment destination points · 45 minutes. This does not imply national coverage.`:data.reach.note||'No computed travel-time results for this selected scope.'}</p>
     <h3>Limitations</h3><ul>{data.caveats.map(note=><li key={note}>{note}</li>)}</ul>
    </section>
   </article><p className='research-controls research-export-note'>CSV and printable HTML contain the existing research tables and source metadata. Print this preview for its map and key findings; choose A4 in your browser. Downloads describe evidence and do not establish causes.</p>
  </>}
 </div>
}
