import { COUNTRIES,regionsForCountry } from './constants'
import { appPath } from './appRoutes'
const PAGES=['overview','equity','access','service','network','correlations','economy','policy','scenarios','studio','compare','reach','time','ops']
const QUERY_KEYS=new Set(['region','urban_rural','pack','as_of','mode','view','exhibit','metric','a','b','dest','cutoff','cells','freq_pct','last_bus','drt_cov','franchise','lad','rank','sort','cluster','point'])
export interface SavedViewContext {country:string;page:string;query:Record<string,string>}
export interface SavedAnalysis {id:string;title:string;content:string;section_id:string|null;dimension:string|null;tags:string[];created_at:string;view_context?:unknown}
export interface PolicyNote {id:string;dimension:string;region:string;stance:'priority'|'monitor'|'adequate'|null;thesis:string;critique:string|null;created_at:string;updated_at:string;view_context?:unknown}
export interface SavedRegion {id:string;region_code:string;region_name:string;notes:string|null;created_at:string;view_context?:unknown}

export function savedContext(raw:unknown):SavedViewContext|null {
 if(!raw||typeof raw!=='object'||Array.isArray(raw))return null
 const row=raw as Record<string,unknown>
 if(typeof row.country!=='string'||!COUNTRIES.some(country=>country.code===row.country)||typeof row.page!=='string'||!PAGES.includes(row.page)||!row.query||typeof row.query!=='object'||Array.isArray(row.query))return null
 const query=row.query as Record<string,unknown>
 if(Object.entries(query).some(([key,value])=>!QUERY_KEYS.has(key)||typeof value!=='string'||value.length>256))return null
 return {country:row.country,page:row.page,query:query as Record<string,string>}
}

export function captureViewContext(pathname:string,search:string,currentDate?:string):SavedViewContext|null {
 const match=pathname.match(/^\/app\/(england|ireland|netherlands|france)(?:\/([a-z-]+))?\/?$/)
 if(!match)return null
 const params=new URLSearchParams(search),query:Record<string,string>={region:'all',urban_rural:'all'}
 for(const [key,value]of params)if(QUERY_KEYS.has(key)&&value.length<=256)query[key]=value
 if((!query.pack||query.pack==='current')&&!query.as_of){if(currentDate)query.pack=currentDate;else delete query.pack}
 return savedContext({country:match[1],page:match[2]??'overview',query})
}

export const savedContextHref=(context:SavedViewContext)=>`${appPath(context.country,context.page==='overview'?undefined:context.page)}?${new URLSearchParams(context.query)}`
export function savedContextLabels(raw:unknown){
 const context=savedContext(raw)
 return {context,country:COUNTRIES.find(row=>row.code===context?.country)?.name??'Not stored',network:context?.query.pack??context?.query.as_of??'Date not stored',region:context?regionsForCountry(context.country).find(row=>row.code===context.query.region)?.name??context.query.region??'All areas':'Not stored'}
}
