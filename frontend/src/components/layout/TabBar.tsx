import { useEffect, useState } from 'react'
import { Link, NavLink, useSearchParams } from 'react-router'
import { BarChart3, Users, MapPin, Bus, Network, ChartNoAxesColumn, Coins, FileText, SlidersHorizontal, Pencil, Copy, Radio, Clock, Settings, Folder, Info, Menu, type LucideIcon } from 'lucide-react'
import { useFilters } from '@/api/hooks'
import { appHome, appPath, withSearch } from '@/lib/appRoutes'

const groups: { label: string; items: [string, string, LucideIcon][] }[] = [
  { label: 'Explore', items: [['Overview', '', BarChart3], ['Equity', 'equity', Users], ['Access', 'access', MapPin], ['Service', 'service', Bus], ['Network', 'network', Network], ['Correlations', 'correlations', ChartNoAxesColumn]] },
  { label: 'Plan', items: [['Economy', 'economy', Coins], ['Policy', 'policy', FileText], ['Scenarios', 'scenarios', SlidersHorizontal], ['Studio', 'studio', Pencil], ['Compare', 'compare', Copy]] },
  { label: 'Observe', items: [['Reach', 'reach', Radio], ['Time', 'time', Clock], ['Ops', 'ops', Settings]] },
]

export function TabBar() {
  const { country } = useFilters()
  const [params] = useSearchParams()
  const [mobile, setMobile] = useState(() => window.matchMedia?.('(max-width: 560px)').matches ?? false)
  const [navigationOpen, setNavigationOpen] = useState(!mobile)
  useEffect(() => {
    const media = window.matchMedia?.('(max-width: 560px)')
    if (!media) return
    const change = (event: MediaQueryListEvent) => { setMobile(event.matches); setNavigationOpen(!event.matches) }
    media.addEventListener('change', change)
    return () => media.removeEventListener('change', change)
  }, [])
  return (
    <>
    <aside className='app-sidebar'>
      <Link to={withSearch(appHome(country), params.toString())} className='app-wordmark'>Aequitas</Link>
      <details className='app-navigation-disclosure' open={navigationOpen} onToggle={event => setNavigationOpen(event.currentTarget.open)}>
        <summary><Menu size={18} /> Navigation</summary>
        <nav aria-label='Application' onClick={event => { if (mobile && (event.target as Element).closest('a')) setNavigationOpen(false) }}>
          {groups.map(group => (
            <div className='app-nav-group' key={group.label}>
              <p className='app-nav-label'>{group.label}</p>
              {group.items.map(([label, slug, Icon]) => (
                <NavLink key={label} to={withSearch(appPath(country, slug), params.toString())} end={!slug} className={({ isActive }) => `app-nav-link${isActive ? ' is-active' : ''}`}>
                  <Icon size={19} strokeWidth={1.6} aria-hidden='true' /><span>{label}</span>
                </NavLink>
              ))}
            </div>
          ))}
          <div className='app-nav-group'>
            <p className='app-nav-label'>Workspace</p>
            <NavLink className='app-nav-link' to='/saved'><Folder size={19} strokeWidth={1.6} aria-hidden='true' /> Saved work</NavLink>
          </div>
        </nav>
      </details>
      <Link to='/methodology' className='app-nav-link app-methodology'><Info size={19} strokeWidth={1.6} aria-hidden='true' /> Methodology</Link>
    </aside>
    {mobile && <nav className='app-mobile-tabs' aria-label='Quick navigation'>
      <NavLink to={withSearch(appHome(country), params.toString())} end><BarChart3 size={21} /><span>Overview</span></NavLink>
      <NavLink to={withSearch(appPath(country, 'equity'), params.toString())}><ChartNoAxesColumn size={21} /><span>Evidence</span></NavLink>
      <NavLink to='/saved'><Folder size={21} /><span>Saved</span></NavLink>
      <button type='button' aria-expanded={navigationOpen} onClick={() => { setNavigationOpen(!navigationOpen); window.scrollTo({ top: 0, behavior: 'smooth' }) }}><Menu size={21} /><span>More</span></button>
    </nav>}
    </>
  )
}
