import {render,screen,within} from '@testing-library/react'
import {MemoryRouter} from 'react-router'
import {describe,expect,it} from 'vitest'
import {EvidenceNavigation} from '../EvidenceNavigation'

describe('Network reference navigation',()=>{
 it('groups relationships under route mix while retaining shareable country filters',()=>{
  render(<MemoryRouter initialEntries={['/app/england/network?view=c5_length_vs_frequency&region=E12000005&urban_rural=urban&pack=2026-08-01']}><EvidenceNavigation dimension='route_network' country='england' sections={[]} /></MemoryRouter>)
  const groups=screen.getByRole('navigation',{name:'Evidence views'})
  expect(within(groups).getByRole('link',{name:'Geometry'})).toBeInTheDocument()
  expect(within(groups).getByRole('link',{name:'Route mix'})).toHaveAttribute('aria-current','page')
  const details=screen.getByRole('navigation',{name:'Network exhibits'})
  expect(within(details).getByRole('link',{name:'Relationships'})).toHaveAttribute('aria-current','page')
  const url=new URL(within(groups).getByRole('link',{name:'Geometry'}).getAttribute('href')!,'http://localhost')
  expect(url.searchParams.get('view')).toBe('c1_route_length')
  expect(url.searchParams.get('region')).toBe('E12000005')
  expect(url.searchParams.get('urban_rural')).toBe('urban')
  expect(url.searchParams.get('pack')).toBe('2026-08-01')
 })
})

describe('Access reference navigation',()=>{
 it('groups density and distribution separately from predictive evidence and preserves context',()=>{
  render(<MemoryRouter initialEntries={['/app/england/access?view=a8_coverage_prediction&region=E12000005&urban_rural=rural&pack=2026-08-01&exhibit=old']}><EvidenceNavigation dimension='accessibility' country='england' sections={[]} /></MemoryRouter>)
  const groups=screen.getByRole('navigation',{name:'Evidence views'})
  expect(within(groups).getAllByRole('link')).toHaveLength(6)
  expect(within(groups).getByRole('link',{name:'More evidence'})).toHaveAttribute('aria-current','page')
  const details=screen.getByRole('navigation',{name:'Access exhibits'})
  expect(within(details).getByRole('link',{name:'Prediction'})).toHaveAttribute('aria-current','page')
  const url=new URL(within(details).getByRole('link',{name:'Density & distribution'}).getAttribute('href')!,'http://localhost')
  expect(url.searchParams.get('view')).toBe('density')
  expect(url.searchParams.get('region')).toBe('E12000005')
  expect(url.searchParams.get('urban_rural')).toBe('rural')
  expect(url.searchParams.get('pack')).toBe('2026-08-01')
  expect(url.searchParams.has('exhibit')).toBe(false)
 })
})
describe('Correlation reference groups',()=>{
 it('keeps model subviews selected and clears obsolete exhibits while preserving filters',()=>{
  render(<MemoryRouter initialEntries={['/app/england/correlations?view=features&exhibit=g4_shap&region=E12000005&urban_rural=rural&pack=2026-08-01']}><EvidenceNavigation dimension='correlations' country='england' sections={[]} /></MemoryRouter>)
  const primary=screen.getByRole('navigation',{name:'Evidence views'})
  expect(within(primary).getAllByRole('link')).toHaveLength(5)
  expect(within(primary).getByRole('link',{name:/^Model$/})).toHaveAttribute('aria-current','page')
  const secondary=screen.getByRole('navigation',{name:'Correlation exhibits'})
  expect(within(secondary).getByRole('link',{name:'Feature importance'})).toHaveAttribute('aria-current','page')
  const url=new URL(within(secondary).getByRole('link',{name:'Model fit'}).getAttribute('href')!,'http://localhost')
  expect(url.searchParams.get('view')).toBe('g3_coverage_model')
  expect(url.searchParams.has('exhibit')).toBe(false)
  expect(url.searchParams.get('region')).toBe('E12000005')
  expect(url.searchParams.get('urban_rural')).toBe('rural')
  expect(url.searchParams.get('pack')).toBe('2026-08-01')
 })
})
