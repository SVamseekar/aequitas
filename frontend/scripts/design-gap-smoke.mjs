import { chromium } from 'playwright'
import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync } from 'node:fs'
const output=process.env.DESIGN_EVIDENCE_DIR??'../implementation/evidence/gaps-oct28/layout'
mkdirSync(output,{recursive:true})
const browser=await chromium.launch({channel:'chrome',headless:true}),results=[]
try {
 const page=await browser.newPage({reducedMotion:'reduce'})
 let errors=[];page.on('pageerror',error=>errors.push(error.message))
 const check=async(name,route,width,height,verify)=>{
  errors=[]
  try {
   await page.setViewportSize({width,height});await page.goto(`http://127.0.0.1:5173${route}`,{waitUntil:'domcontentloaded'})
   await page.locator('main h1').waitFor();await page.waitForFunction(()=>!document.querySelector('main .animate-pulse,main [role="status"]'))
   await page.evaluate(()=>document.fonts.ready)
   assert.deepEqual(errors,[]);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Horizontal overflow')
   await verify();results.push({name,result:'PASS'})
  } catch(error){results.push({name,result:'FAIL',error:error.message})}
  writeFileSync(`${output}/results.json`,JSON.stringify(results,null,2)+'\n');await page.screenshot({path:`${output}/${name}.png`,fullPage:true})
 }
 await check('coverage-reference','/app/england/access?view=a3_walking_distance',976,806,async()=>{
  const summary=await page.locator('.access-coverage-detail').boundingBox();assert.ok(summary.y+summary.height<=806,'Coverage table and side summary below reference frame')
  const source=await(await page.request.get('http://127.0.0.1:5173/api/sections?country=england&dimension=accessibility')).json()
  const pct=source.sections.find(s=>s.section_id==='a3_walking_distance').stats.pct_covered
  assert.ok((await page.locator('.coverage-proportion').innerText()).includes(`${pct.toFixed(1)}%`))
  assert.equal(await page.getByRole('navigation',{name:'Evidence views'}).getByRole('link').count(),6)
  await page.getByRole('navigation',{name:'Evidence views'}).getByRole('link',{name:'More evidence'}).click()
  await page.getByRole('navigation',{name:'Access exhibits'}).getByRole('link',{name:'Prediction'}).click()
  await page.waitForURL(url=>url.searchParams.get('view')==='a8_coverage_prediction')
 })
 for(const view of ['g1_route_clusters','g2_anomalies','g5_scenario_model'])await check(`correlation-${view}-591`,`/app/england/correlations?view=${view}`,591,887,async()=>{
  assert.ok(await page.getByRole('navigation',{name:'Application',exact:true}).isVisible())
  assert.equal(await page.getByRole('navigation',{name:'Quick navigation'}).count(),0)
  assert.equal(await page.getByRole('navigation',{name:'Evidence views'}).getByRole('link').count(),3)
  if(view!=='g5_scenario_model')assert.ok((await page.locator('.compact-cluster-legend').boundingBox()).y<650)
  if(view==='g1_route_clusters'){
   await page.locator('.route-cluster-summary svg').waitFor()
   assert.equal(await page.locator('.route-cluster-summary [aria-label=bar] rect').count(),7)
   const summary=await page.locator('.route-cluster-summary').boundingBox();assert.ok(summary.y+summary.height<=887,'Route cluster summary below reference frame')
  }
  if(view==='g5_scenario_model'){
   const summary=await page.locator('.scenario-model-summary').boundingBox();assert.ok(summary.y+summary.height<=887,'Scenario summary below reference frame')
   const response=await page.request.get('http://127.0.0.1:5173/api/sections?country=england&dimension=correlations')
   const source=(await response.json()).sections.find(row=>row.section_id===view)
   for(const tile of source.chart_data.tiles)assert.ok((await page.locator('.scenario-model-metrics').innerText()).includes(tile.value.toLocaleString('en-GB')))
  }
 })
 await check('facilities-reference','/app/england/access?view=facilities',1052,748,async()=>{
  const notes=await page.locator('.access-facility-notes').boundingBox();assert.ok(notes.y+notes.height<=748,'Facility source panels below original frame')
  assert.equal(await page.locator('.access-facility-cards article').count(),3)
 })
 for(const [view,selector]of [['d6_transport_poverty','.poverty-groups'],['d7_deprivation_urban_rural','.correlation-rural-notes'],['g3_coverage_model','.correlation-model .network-main'],['features','.correlation-model .network-main']])await check(`supporting-${view}`,`/app/england/correlations?view=${view}`,992,793,async()=>{
  const panel=await page.locator(selector).boundingBox();assert.ok(panel.y+panel.height<=793,'Supporting source panels below reference frame')
 })
 await check('time-reference','/app/england/time',792,495,async()=>{
  assert.ok(await page.getByRole('button',{name:'Ask Aequitas',exact:true}).isVisible())
  assert.ok(await page.getByRole('button',{name:'Export observations CSV',exact:true}).isVisible())
  assert.equal(await page.getByRole('heading',{name:'Time — In-country score',exact:true}).count(),1)
  const grid=await page.locator('.app-time-grid').boundingBox();assert.ok(grid.width>600);assert.ok(grid.y+grid.height<=495,'Time panel falls below short reference')
 })
 for(const country of ['ireland','netherlands','france'])await check(`country-${country}`,`/app/${country}/correlations?view=d7_deprivation_urban_rural`,648,717,async()=>{
  const notes=await page.locator('.country-correlation-notes').boundingBox();assert.ok(notes.y+notes.height<=717,'Country source notes below reference frame')
 })
 if(!process.env.DESIGN_LAYOUT_ONLY)for(const width of [390,560,591,640,768,1440])for(const [name,route] of [['overview','/app/england'],['access','/app/england/access?view=a5_service_deserts'],['clusters','/app/england/correlations?view=g1_route_clusters'],['ops','/app/ireland/ops']])await check(`${name}-${width}`,route,width,900,async()=>{
  if(width<=560){assert.ok(await page.getByRole('navigation',{name:'Quick navigation'}).isVisible());await page.getByRole('button',{name:'More',exact:true}).click();assert.ok(await page.getByRole('navigation',{name:'Application',exact:true}).isVisible())}
  else assert.ok(await page.getByRole('navigation',{name:'Application',exact:true}).isVisible())
 })
} finally {
 writeFileSync(`${output}/results.json`,JSON.stringify(results,null,2)+'\n')
 console.log(JSON.stringify({passed:results.filter(r=>r.result==='PASS').length,failed:results.filter(r=>r.result==='FAIL')}))
 process.exitCode=results.some(r=>r.result==='FAIL')?1:0
 await browser.close()
}
