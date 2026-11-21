import { Link } from 'react-router'
import { COUNTRY_BRIEFS } from '@/lib/briefingCatalog'
import { CountryOutline } from '@/components/shared/CountryOutline'

export function CountryBriefCards() {
  return <div className='public-country-grid'>{COUNTRY_BRIEFS.map(country => <Link key={country.code} to={country.path} className='public-country-card'>
    <CountryOutline country={country.code} name={country.name} />
    <div><h3>{country.name}</h3><p>{country.network.split(' + ')[0]} × {country.deprivation}</p><span className='app-text-link'>Read {country.name} briefing</span></div>
  </Link>)}</div>
}
