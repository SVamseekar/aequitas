import { describe, expect, it } from 'vitest'
import type { SectionItem } from '@/api/types'
import { sectionPresentation } from '../sectionPresentation'

const section: SectionItem = { section_id: 'f5_rural_penalty', dimension: 'equity', stats: {}, suppressed: false, narrative: '', chart_data: {
  type: 'grouped_bar', categories: ['London', 'North East'], series: [{ name: 'Urban', values: [82.212, 77.204] }, { name: 'Rural', values: [0, 0] }],
} }
describe('stored exhibit presentation', () => {
  it.each(['d8_feature_importance','g3_coverage_model','g4_shap'])('keeps %s model scope and target distinct from binary proximity or causal policy claims', id => {
    const result=sectionPresentation({...section,section_id:id},'england')
    expect(result.interpretation).toContain('log1p(trips per capita)')
    expect(result.interpretation).toContain('not causal')
    expect(result.interpretation).toContain('do not refit')
  })
  it('marks the impossible London rural observation unavailable while retaining other observed zeroes', () => {
    const result = sectionPresentation(section, 'england')
    expect(result.chartData.series).toEqual([{ name: 'Urban', values: [82.212, 77.204] }, { name: 'Rural', values: [null, 0] }])
    expect(section.chart_data.series).toEqual([{ name: 'Urban', values: [82.212, 77.204] }, { name: 'Rural', values: [0, 0] }])
    expect(result.chartData.x_label).toBe('Service Quality Index (points)')
  })
  it('preserves other countries source measures and deprivation terminology', () => {
    const result = sectionPresentation(section, 'ireland')
    expect(result.chartData).toBe(section.chart_data)
    expect(result.interpretation).toBeUndefined()
  })
  it('labels the extended regional index as vulnerability rather than Gini', () => {
    const result = sectionPresentation({ ...section, section_id: 'f6_equitable_regions' }, 'england')
    expect(result.title).toBe('Regional vulnerability')
    expect(result.interpretation).toContain('not Gini')
  })
  it.each(['france', 'netherlands'])('labels %s origin evidence without copying England ethnicity', country => {
    const result = sectionPresentation({ ...section, section_id: 'f3_ethnic_access' }, country)
    expect(result.title).not.toContain('ethnicity')
    expect(result.interpretation).toMatch(/origin.*rather than ethnicity/)
    expect(result.chartData.data).toBe(section.chart_data.data)
  })
})
