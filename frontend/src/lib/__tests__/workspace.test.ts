import {describe,expect,it}from'vitest'
import{captureViewContext,savedContext,savedContextHref,savedContextLabels}from'../workspace'
describe('Stored analytical context',()=>{
 it('preserves actual country/date/area and view controls while excluding auth query material',()=>{
  const context=captureViewContext('/app/ireland/access','?region=dublin&view=facilities&urban_rural=urban&session_token=secret','2026-08-01')!
  expect(savedContextHref(context)).toContain('/app/ireland/access?')
  expect(context.query).toEqual({region:'dublin',urban_rural:'urban',view:'facilities',pack:'2026-08-01'})
  expect(savedContextHref(context)).not.toContain('secret')
 })
 it('keeps legacy metadata unavailable and rejects arbitrary routes or countries',()=>{
  expect(savedContextLabels(null).country).toBe('Not stored')
  expect(savedContext({country:'england',page:'https://example.org',query:{}})).toBeNull()
  expect(captureViewContext('/profile','')).toBeNull()
  expect(captureViewContext('/app/england','')?.query.pack).toBeUndefined()
 })
})
