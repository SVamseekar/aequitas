import {describe,expect,it} from 'vitest'
import {authReturnPath} from '../authReturn'
describe('Sign-in return destination',()=>{
 it('keeps analytical context and invitation route',()=>{
  for(const route of ['/app/ireland/access?region=dublin&pack=2026-08-01','/invite/unit-proof','/saved?analysis=unit'])expect(authReturnPath(route)).toBe(route)
 })
 it('rejects external, malformed and unknown destinations',()=>{
  for(const route of ['https://example.org','//example.org','/\\example.org','/app/unknown','/auth','/saved\r\nLocation: evil'])expect(authReturnPath(route)).toBe('/app/england')
 })
})
