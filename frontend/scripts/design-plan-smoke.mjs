import {chromium} from 'playwright'
import assert from 'node:assert/strict'
import {mkdirSync,writeFileSync} from 'node:fs'
const output = process.env.DESIGN_EVIDENCE_DIR ?? '../implementation/evidence/plan-browser-oct24';mkdirSync(output,{recursive:true})
const browser=await chromium.launch({channel:'chrome',headless:true}),results=[]
try{
 const page=await browser.newPage({viewport:{width:1100,height:900},reducedMotion:'reduce'})
 let errors=[];page.on('pageerror',error=>errors.push(error.message))
 const check=async(name,run)=>{errors=[];try{await run();assert.deepEqual(errors,[]);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Horizontal overflow');results.push({name,result:'PASS'})}catch(error){results.push({name,result:'FAIL',error:error.message});await page.screenshot({path:`${output}/failure-${results.length}.png`,fullPage:true})}}
 const goto=async(route)=>{await page.goto(`http://127.0.0.1:5173${route}`,{waitUntil:'domcontentloaded'});await page.locator('main h1').waitFor();await page.waitForFunction(()=>!document.querySelector('main .animate-pulse,main [role="status"]'))}
 const get=async(path)=>{const response=await page.request.get(`http://127.0.0.1:5173/api${path}`);assert.equal(response.status(),200);return response.json()}
 const correlationViews=['d1_coverage_deprivation','d2_coverage_unemployment','d3_coverage_car','d4_coverage_elderly','domains','d6_transport_poverty','d7_deprivation_urban_rural','g3_coverage_model','features','g1_route_clusters','g2_anomalies','g5_scenario_model']
 const economyViews=['j1_economic_value','j2_bcr','j3_carbon','j4_investment_priority','assumptions']
 const policyViews=['readiness','operators','bsa3_tier_distribution','context']
 for(const [family,views] of [['correlations',correlationViews],['economy',economyViews],['policy',policyViews]])for(const view of views)await check(`England ${family} ${view}`,async()=>{await goto(`/app/england/${family}?view=${view}`);assert.doesNotMatch(await page.locator('main').innerText(),/Something went wrong|Chart could not be rendered|NaN|Infinity/)})
 for(const country of ['ireland','netherlands','france'])for(const [family,views]of [['economy',economyViews],['policy',policyViews],['correlations',['d7_deprivation_urban_rural']]])for(const view of views)await check(`${country} ${family} ${view}`,async()=>{await goto(`/app/${country}/${family}?view=${view}`);assert.doesNotMatch(await page.locator('main').innerText(),/Something went wrong|Chart could not be rendered|NaN|Infinity/);assert.match(await page.locator('main h1').innerText(),new RegExp(country,'i'))})
 await check('Four core relationships retain actual axes and full-sample r',async()=>{
  const source=(await get('/sections?dimension=correlations&country=england')).sections
  for(const view of correlationViews.slice(0,4)){
   await goto(`/app/england/correlations?view=${view}`)
   const section=source.find(row=>row.section_id===view),plot=page.locator(`article[data-section="${view}"] .evidence-chart`)
   await plot.locator('svg').waitFor();assert.match(await plot.innerText(),new RegExp(section.chart_data.y_label.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')))
   assert.ok((await page.locator('.evidence-statistics').innerText()).includes(section.stats.r.toFixed(4)))
  }
 })
 await check('Core relationship tabs and More evidence preserve filter context',async()=>{
  await goto('/app/england/correlations?view=d1_coverage_deprivation&region=E12000005&pack=2026-08-01')
  await page.getByRole('navigation',{name:'Evidence views'}).getByRole('link',{name:'Elderly',exact:true}).click()
  await page.waitForURL(url=>url.searchParams.get('view')==='d4_coverage_elderly')
  await page.getByRole('combobox',{name:'Other correlation views'}).selectOption('domains')
  await page.locator('.correlation-domains-grid').waitFor()
  assert.equal(new URL(page.url()).searchParams.get('region'),'E12000005');assert.equal(new URL(page.url()).searchParams.get('pack'),'2026-08-01')
 })
 await check('Domains displays six real source relationships, retaining negative source axes',async()=>{
  await goto('/app/england/correlations?view=d5_coverage_income')
  assert.equal(await page.locator('.correlation-domains-grid > section').count(),6)
  const health=page.locator('[data-section="d9a_health_access"]');await health.locator('svg').waitFor()
  assert.match(await health.innerText(),/Health & Disability/)
  assert.match(await health.innerText(),/0\.1199/)
  assert.match(await page.locator('[data-section="d9e_barriers_access"]').innerText(),/-0\.0130/)
 })
 await check('Missing model fit remains unavailable while exact model summary is supplied',async()=>{await goto('/app/england/correlations?view=g3_coverage_model');assert.match(await page.locator('main').innerText(),/Fit scatter not stored for this pack/);assert.match(await page.locator('.service-metrics').innerText(),/0\.4719/);assert.match(await page.locator('main').innerText(),/log1p\(trips per capita\)/);assert.equal(await page.locator('.model-fit-unavailable svg').count(),0)})
 await check('Feature-summary selector switches supplied exhibits with URL scope',async()=>{await goto('/app/england/correlations?view=features&region=E12000005&pack=2026-08-01');await page.getByRole('combobox',{name:'Exhibit'}).selectOption('g4_shap');await page.waitForURL(url=>url.searchParams.get('exhibit')==='g4_shap');await page.getByRole('img',{name:'National predictive feature importance'}).locator('svg').waitFor();assert.equal(new URL(page.url()).searchParams.get('region'),'E12000005');assert.match(await page.locator('main').innerText(),/not causal policy effects/)})
 await check('Actual anomaly sample inspection persists without summing descriptive categories',async()=>{
  await goto('/app/england/correlations?view=g2_anomalies')
  const source=(await get('/sections?dimension=correlations&country=england')).sections.find(row=>row.section_id==='g2_anomalies'),point=source.chart_data.data[0]
  await page.getByRole('combobox',{name:'Inspect plotted area'}).selectOption(point.id);await page.locator('.correlation-groups .network-summary').getByText(point.id,{exact:true}).waitFor()
  assert.equal(new URL(page.url()).searchParams.get('point'),point.id);assert.match(await page.locator('main').innerText(),/do not sum to the flagged anomaly count/)
  await page.reload({waitUntil:'domcontentloaded'});await page.locator('.correlation-groups .network-summary').getByText(point.id,{exact:true}).waitFor()
 })
 await check('Economy unit conversions, exact BCR and current country factors',async()=>{
  await goto('/app/england/economy?view=j1_economic_value');assert.match(await page.locator('.plan-metrics').innerText(),/£1,387\.2/);assert.match(await page.locator('.plan-metrics').innerText(),/million \/ year/)
  await goto('/app/england/economy?view=j2_bcr');assert.match(await page.locator('.plan-metrics').innerText(),/1\.15/);assert.match(await page.locator('.plan-metrics').innerText(),/£30,095\.7/);assert.match(await page.locator('.network-summary').innerText(),/1\.15 BCR/)
  await goto('/app/england/economy?view=j3_carbon');assert.match(await page.locator('.plan-metrics').innerText(),/£1,838\.62/);assert.match(await page.locator('.plan-metrics').innerText(),/thousand \/ year/)
  await goto('/app/england/economy?view=j4_investment_priority');assert.match(await page.locator('.plan-metrics').innerText(),/£34,165\.46/)
  const table=page.getByRole('table',{name:'Country appraisal availability'});await page.waitForFunction(()=>!document.querySelector('table[aria-label="Country appraisal availability"]')?.textContent.includes('Loading'))
  assert.equal(await table.getByRole('cell',{name:'No currency appraisal applied',exact:true}).count(),3)
 })
 await check('Policy uses exact HHI and district tiers rather than population or legal eligibility',async()=>{
  await goto('/app/england/policy?view=readiness');assert.match(await page.locator('.plan-metrics').innerText(),/30\.72/);assert.match(await page.locator('.plan-metrics').innerText(),/84\.5/)
  await goto('/app/england/policy?view=bsa3_tier_distribution');assert.match(await page.locator('.plan-metrics').innerText(),/298/);assert.match(await page.locator('main').innerText(),/not statutory eligibility/)
  await page.getByRole('navigation',{name:'Evidence views'}).getByRole('link',{name:'Country context'}).click();await page.getByRole('heading',{name:'Country policy context — England'}).waitFor()
 })
 const responsive=[['correlations','domains'],['correlations','g3_coverage_model'],['correlations','g2_anomalies'],['correlations','g5_scenario_model'],['economy','j1_economic_value'],['economy','j2_bcr'],['economy','j3_carbon'],['economy','j4_investment_priority'],['policy','readiness'],['policy','operators'],['policy','bsa3_tier_distribution']]
 for(const width of [768,390])for(const [family,view]of responsive)await check(`${width}px ${family} ${view}`,async()=>{await page.setViewportSize({width,height:900});await goto(`/app/england/${family}?view=${view}`);await page.screenshot({path:`${output}/${width}-${family}-${view}.png`,fullPage:true})})
}finally{await browser.close();writeFileSync(`${output}/results.json`,JSON.stringify(results,null,2)+'\n')}
console.log(JSON.stringify({passed:results.filter(row=>row.result==='PASS').length,failed:results.filter(row=>row.result==='FAIL')}))
process.exitCode=results.some(row=>row.result==='FAIL')?1:0
