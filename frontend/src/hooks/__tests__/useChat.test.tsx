import {act,renderHook,waitFor} from '@testing-library/react'
import {afterEach,describe,expect,it,vi} from 'vitest'
import {useChat} from '../useChat'

function responseStream(){
 let controller:ReadableStreamDefaultController<Uint8Array>
 const stream=new ReadableStream<Uint8Array>({start(value){controller=value}})
 return {response:new Response(stream),push:(text:string)=>controller.enqueue(new TextEncoder().encode(text)),close:()=>controller.close()}
}
const context={country:'ireland',page:'access',query:{region:'dublin',pack:'2026-08-01'}}
describe('Assistant stream ownership',()=>{
 afterEach(()=>vi.unstubAllGlobals())
 it('keeps split SSE text, sources and original scope on the actual answer',async()=>{
  const stream=responseStream(),request=vi.fn().mockResolvedValue(stream.response)
  vi.stubGlobal('fetch',request)
  const {result}=renderHook(useChat)
  act(()=>{result.current.sendMessage('Question',{country:'ireland'},context)})
  await waitFor(()=>expect(request).toHaveBeenCalledTimes(1))
  await act(async()=>{stream.push('event: chunk\ndata: {"text":"Actual ');stream.push('answer"}\n\nevent: done\ndata: {"sources":["a1",7],"conversation_id":"retrieval-only"}\n\n');stream.close()})
  await waitFor(()=>expect(result.current.isStreaming).toBe(false))
  expect(result.current.messages[1]).toMatchObject({content:'Actual answer',sources:['a1'],viewContext:context})
  expect(JSON.parse(request.mock.calls[0][1].body).history).toEqual([])
 })
 it('clearing aborts old output and starts with no old conversation or history',async()=>{
  const old=responseStream(),next=responseStream(),request=vi.fn().mockResolvedValueOnce(old.response).mockResolvedValueOnce(next.response)
  vi.stubGlobal('fetch',request)
  const {result}=renderHook(useChat)
  act(()=>{result.current.sendMessage('Old',{country:'england'})})
  await waitFor(()=>expect(request).toHaveBeenCalledTimes(1))
  act(()=>result.current.clearMessages())
  expect(request.mock.calls[0][1].signal.aborted).toBe(true)
  act(()=>{result.current.sendMessage('New',{country:'ireland'},context)})
  await act(async()=>{old.push('event: chunk\ndata: {"text":"obsolete"}\n\n');old.close()})
  expect(result.current.isStreaming).toBe(true)
  expect(result.current.messages.map(row=>row.content)).toEqual(['New',''])
  expect(JSON.parse(request.mock.calls[1][1].body)).toMatchObject({history:[],conversation_id:null})
  await act(async()=>{next.push('data: {"text":"Current"}\n\n');next.close()})
  await waitFor(()=>expect(result.current.isStreaming).toBe(false))
  expect(result.current.messages[1].content).toBe('Current')
 })
 it('aborts on unmount and exposes a server scope error without an empty answer',async()=>{
  const request=vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({detail:'Historical-network answers unavailable'}),{status:400})).mockReturnValueOnce(new Promise(()=>{}))
  vi.stubGlobal('fetch',request)
  const {result,unmount}=renderHook(useChat)
  act(()=>{result.current.sendMessage('Question',{country:'england'})})
  await waitFor(()=>expect(result.current.error).toBe('Historical-network answers unavailable'))
  expect(result.current.messages).toHaveLength(1)
  act(()=>{result.current.sendMessage('Next',{country:'england'})})
  unmount()
  expect(request.mock.calls[1][1].signal.aborted).toBe(true)
 })
 it('marks a partially received answer incomplete when its stream fails',async()=>{
  const stream=responseStream();vi.stubGlobal('fetch',vi.fn().mockResolvedValue(stream.response))
  const {result}=renderHook(useChat)
  act(()=>{result.current.sendMessage('Question',{country:'ireland'},context)})
  await act(async()=>{stream.push('event: chunk\ndata: {"text":"Partial answer"}\n\nevent: error\ndata: {"message":"Generation interrupted"}\n\n');stream.close()})
  await waitFor(()=>expect(result.current.isStreaming).toBe(false))
  expect(result.current.messages[1]).toMatchObject({content:'Partial answer',status:'error'})
  expect(result.current.error).toBe('Generation interrupted')
 })
})
