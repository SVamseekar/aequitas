import type {PacksResponse,ReachResponse,ScoreResponse} from '@/api/types'
import type {CountryCode} from './constants'
export interface ResearchPack {place:string;filter:{country:string;region:string;urban_rural:string};vintages:Record<string,string>;score:ScoreResponse;reach:ReachResponse;caveats:string[];written_at?:string}
export function researchUnavailable(country:CountryCode,pack:string,mode:string,packs:PacksResponse|undefined):string|null {
 if(country==='netherlands')return 'A Netherlands research pack is not available in this checkout.'
 if(mode==='all')return 'Research exports use the bus network. An all-mode research pack is unavailable.'
 if(!['','current','latest'].includes(pack.toLowerCase())&&!packs?.[country]?.dates?.some(row=>row.current&&(row.pack_id===pack||row.as_of===pack)))return 'The selected network is not registered as current. Historical research packs are unavailable; no current results are relabelled with a past date.'
 return null
}
