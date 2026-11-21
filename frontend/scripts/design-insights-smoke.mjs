import {chromium} from 'playwright'
import assert from 'node:assert/strict'
import {mkdirSync,writeFileSync} from 'node:fs'
const output=process.env.DESIGN_EVIDENCE_DIR??'../implementation/evidence/insights-oct28/browser';mkdirSync(output,{recursive:true})
const browser=await chromium.launch({channel:'chrome',headless:true}),results=[]
try{
 const page=await browser.newPage({viewport:{width:1100,height:900},reducedMotion:'reduce'})
 const check=async(name,route,verify)=>{
  try{await page.goto(`http://127.0.0.1:5173${route}`,{waitUntil:'domcontentloaded'});await page.locator('main h1').waitFor();await page.waitForFunction(()=>!document.querySelector('main .animate-pulse,main [role=status]'))
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Horizontal overflow')
   await verify();results.push({name,result:'PASS'})
  }catch(error){results.push({name,result:'FAIL',error:error.message});await page.screenshot({path:`${output}/failure-${results.length}.png`,fullPage:true})}
  writeFileSync(`${output}/results.json`,JSON.stringify(results,null,2)+'\n')
 }
 const views={access:['a3_walking_distance','a5_service_deserts','a6_urban_rural_gap','facilities','destinations','density','a4_coverage_equity','a7_investment_gap','a8_coverage_prediction'],service:['b1_frequency','b2_operating_hours','b3_weekend_penalty','b4_route_frequency','b5_frequency_deprivation'],network:['c1_route_length','c2_stops_per_route','c3_operator_hhi','c4_urban_rural_routes','c5_length_vs_frequency','c6_route_archetypes','c7_network_topology'],correlations:['d1_coverage_deprivation','d2_coverage_unemployment','d3_coverage_car','d4_coverage_elderly','d6_transport_poverty','d7_deprivation_urban_rural','g3_coverage_model','features','g1_route_clusters','g2_anomalies','g5_scenario_model'],equity:['f1_gini','f2_disparity_ratio','f3_ethnic_access','f5_rural_penalty','f6_equitable_regions'],economy:['j1_economic_value','j2_bcr','j3_carbon','j4_investment_priority'],policy:['readiness','operators','bsa3_tier_distribution'],scenarios:['ps1_freq_restoration','ps2_evening_extension','ps3_drt_rural','ps4_franchise','ps5_scenario_comparison']}
 for(const [family,choices]of Object.entries(views))for(const view of choices)await check(`${family} ${view}`,`/app/england/${family}?view=${view}${view==='destinations'?'&region=E12000005&dest=jobs&cutoff=45':''}`,async()=>{
  const panels=page.locator('main .chart-insights');assert.ok(await panels.count()>0,'No visible chart insight panel')
  for(const panel of await panels.all()){assert.ok(await panel.isVisible());assert.equal(await panel.evaluate(node=>Boolean(node.closest('details:not([open])'))),false,'Insight hidden in collapsed details');assert.ok(await panel.locator('li').count()>0)}
 })
 await check('Access findings follow region changes','/app/england/access?view=a3_walking_distance&region=E12000005',async()=>{
  const data=await(await page.request.get('http://127.0.0.1:5173/api/sections?country=england&dimension=accessibility&region=E12000005')).json(),source=data.sections.find(s=>s.section_id==='a3_walking_distance')
  const text=await page.locator('.access-coverage-main .chart-insights').innerText();assert.ok(text.includes(source.stats.pct_covered.toFixed(1)));assert.match(text,/LSOAs/);assert.doesNotMatch(text,/population is within/)
 })
 for(const country of ['ireland','netherlands','france'])await check(`${country} country findings`,`/app/${country}/correlations?view=d7_deprivation_urban_rural`,async()=>{await page.locator('.country-correlation-layout .chart-insights').waitFor();assert.match(await page.locator('.country-correlation-layout .chart-insights').innerText(),/coverage|cells|country/);assert.doesNotMatch(await page.locator('.chart-insights').innerText(),/England|IMD 2025/)})
 for(const country of ['ireland','netherlands','france'])for(const [family,view]of [['access','a7_investment_gap'],['access','a6_urban_rural_gap'],['service','b4_route_frequency'],['network','c4_urban_rural_routes'],['correlations','d8_feature_importance'],['correlations','g2_anomalies'],['equity','f5_rural_penalty'],['policy','bsa3_tier_distribution']])await check(`${country} native ${view}`,`/app/${country}/${family}?view=${view}`,async()=>{
  const panel=page.locator('main .chart-insights').first();await panel.waitFor();assert.ok(await panel.isVisible());assert.equal(await panel.evaluate(node=>Boolean(node.closest('details:not([open])'))),false)
  if(view==='a7_investment_gap')assert.match(await panel.innerText(),/people-gap|currency cost/)
  if(view==='c4_urban_rural_routes')assert.match(await panel.innerText(),/stop counts, not route shares/)
  if(view==='d8_feature_importance')assert.match(await panel.innerText(),/not numerical SHAP/)
  if(view==='g2_anomalies')assert.match(await panel.innerText(),/stored rule|Rule:/)
 })
 await check('All six domain relationship captions retain source strength','/app/england/correlations?view=domains',async()=>{
  for(const card of await page.locator('.correlation-domains-grid > section').all())assert.match(await card.locator('p').first().innerText(),/r = .*\((negligible|weak|moderate|strong)/)
 })
 for(const [name,route]of [['coverage','/app/england/access?view=a3_walking_distance'],['service','/app/england/service?view=b1_frequency'],['correlation','/app/england/correlations?view=d1_coverage_deprivation'],['model','/app/england/correlations?view=features']])for(const width of [390,768,1100]){
  await page.setViewportSize({width,height:900})
  await check(`${name} findings ${width}`,route,async()=>{assert.ok(await page.locator('.chart-insights').first().isVisible());await page.screenshot({path:`${output}/${name}-${width}.png`,fullPage:true})})
 }
}finally{
 writeFileSync(`${output}/results.json`,JSON.stringify(results,null,2)+'\n');console.log(JSON.stringify({passed:results.filter(r=>r.result==='PASS').length,failed:results.filter(r=>r.result==='FAIL')}));process.exitCode=results.some(r=>r.result==='FAIL')?1:0;await browser.close()
}
