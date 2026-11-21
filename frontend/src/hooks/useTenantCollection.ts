import { useQuery } from '@tanstack/react-query'
import {useAuth} from '@/contexts/AuthContext'
import {fetchJson} from '@/api/client'

/** Cache keys include identity and active tenancy; switching never reuses another workspace's rows. */
export function useTenantCollection<T>(path:string){
 const {user,activeTenant}=useAuth()
 return useQuery({queryKey:['workspace',user?.id,activeTenant?.id,path],queryFn:()=>fetchJson<T[]>(path),enabled:Boolean(user&&activeTenant?.id),retry:false})
}
