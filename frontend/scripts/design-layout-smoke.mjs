import {chromium} from 'playwright'
import assert from 'node:assert/strict'
import {mkdirSync,writeFileSync} from 'node:fs'
const output = process.env.DESIGN_EVIDENCE_DIR ?? '../implementation/evidence/shared-layout-oct27';mkdirSync(output,{recursive:true})
const browser=await chromium.launch({channel:'chrome',headless:true}),results=[]
try{
 const page=await browser.newPage({reducedMotion:'reduce'})
 const inspect=async(name,route,width,height,check)=>{
  try{
   await page.setViewportSize({width,height});await page.goto(`http://127.0.0.1:5173${route}`,{waitUntil:'networkidle'});await page.locator('main h1').waitFor();await page.evaluate(()=>document.fonts.ready)
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Horizontal overflow')
   await check();await page.screenshot({path:`${output}/${name}.png`,fullPage:true});results.push({name,result:'PASS'})
  }catch(error){results.push({name,result:'FAIL',error:error.message});await page.screenshot({path:`${output}/${name}-failure.png`,fullPage:true})}
 }
 await inspect('overview-reference-layout','/app/england',990,793,async()=>{
  const map=await page.locator('.app-map-panel > [data-map-state]').boundingBox();assert.ok(map.y+map.height<=793,'Overview map falls below reference viewport')
  const action=await page.getByRole('link',{name:'Open Access',exact:true}).boundingBox();assert.ok(action.y+action.height<=793,'Open Access falls below reference viewport')
  const context=await page.locator('.app-context-bar').boundingBox();assert.ok(context.height<=46,'Desktop context wraps')
  assert.equal(await page.getByRole('navigation',{name:'Explore briefing'}).getByRole('link').count(),6)
  assert.equal(await page.getByRole('button',{name:'Open AI chat',exact:true}).isVisible(),false)
  await page.getByRole('button',{name:'Ask Aequitas',exact:true}).click();await page.getByRole('dialog',{name:'Ask Aequitas chat'}).waitFor();await page.getByRole('button',{name:'Close chat',exact:true}).click()
 })
 await inspect('network-reference-layout','/app/england/network?view=c5_length_vs_frequency',648,809,async()=>{
  const context=await page.locator('.app-context-bar').boundingBox();assert.ok(context.height<=46,'Desktop context wraps')
  assert.equal(await page.locator('.network-relationship-statistics > section').count(),3)
  const response=await page.request.get('http://127.0.0.1:5173/api/sections?dimension=route_network&country=england');assert.equal(response.status(),200)
  const source=(await response.json()).sections.find(row=>row.section_id==='c5_length_vs_frequency')
  const values=await page.locator('.network-relationship-statistics').innerText();assert.ok(values.includes(source.stats.r.toFixed(4)));assert.ok(values.includes(source.stats.n.toLocaleString('en-GB')))
  const expected=source.chart_data.data.filter(row=>Number.isFinite(row.x)&&Number.isFinite(row.y)).length
  assert.equal(await page.locator('.network-relationship [aria-label="dot"] circle').count(),expected)
  const method=await page.locator('.network-relationship > section:last-child').boundingBox();assert.ok(method.y+method.height<=809,'Relationship method falls below reference viewport')
 })
 await inspect('ireland-reference-layout','/app/ireland/correlations?view=d7_deprivation_urban_rural',647,717,async()=>{
  assert.ok((await page.locator('.app-context-bar').boundingBox()).height<=46,'Desktop context wraps')
  const notes=await page.locator('.country-correlation-notes').boundingBox();assert.ok(notes.y+notes.height<=717,'Country notes fall below reference viewport')
 })
 await inspect('score-reference-layout','/app/england?view=score',990,793,async()=>{
  await page.getByRole('heading',{name:'Component details',exact:true}).waitFor()
  const response=await page.request.get('http://127.0.0.1:5173/api/score?country=england');assert.equal(response.status(),200)
  const source=await response.json(),text=await page.locator('.overview-component-details').innerText()
  for(const component of source.components)if(component.value!=null)assert.ok(text.includes((component.value*100).toFixed(2)))
 })
 await inspect('correlation-short-window','/app/england/correlations?view=d1_coverage_deprivation',836,470,async()=>{
  const plot=await page.locator('.evidence-chart svg').last().boundingBox();assert.ok(plot.y+plot.height<=470,'Relationship plot falls below short reference viewport')
  const stats=await page.locator('.evidence-statistics').boundingBox();assert.ok(stats.y+stats.height<=470,'Relationship statistics fall below short reference viewport')
 })
 for(const width of [390,768,1440])for(const [name,route]of [['overview','/app/england'],['network','/app/england/network?view=c5_length_vs_frequency'],['ireland','/app/ireland/correlations?view=d7_deprivation_urban_rural']])await inspect(`${name}-${width}`,route,width,900,async()=>{
  assert.ok(await page.locator('main').innerText());if(name==='overview')assert.equal(await page.getByRole('link',{name:'How the score works'}).count(),1)
 })
}finally{await browser.close();writeFileSync(`${output}/layout-results.json`,JSON.stringify(results,null,2)+'\n')}
console.log(JSON.stringify({passed:results.filter(row=>row.result==='PASS').length,failed:results.filter(row=>row.result==='FAIL')}));process.exitCode=results.some(row=>row.result==='FAIL')?1:0
