import { chromium } from 'playwright'
import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync } from 'node:fs'
const output = process.env.DESIGN_EVIDENCE_DIR ?? '../implementation/evidence/network-browser-oct24'
mkdirSync(output,{recursive:true})
const browser=await chromium.launch({channel:'chrome',headless:true})
const results=[]
try {
  const page=await browser.newPage({viewport:{width:1050,height:850},reducedMotion:'reduce'})
  let errors=[];page.on('pageerror',error=>errors.push(error.message))
  const check=async(name,run)=>{errors=[];try{await run();assert.deepEqual(errors,[]);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Horizontal overflow');results.push({name,result:'PASS'})}catch(error){results.push({name,result:'FAIL',error:error.message});await page.screenshot({path:`${output}/failure-${results.length}.png`,fullPage:true})}}
  const goto=async(route)=>{await page.goto(`http://127.0.0.1:5173${route}`,{waitUntil:'domcontentloaded'});await page.getByRole('navigation',{name:'Evidence views'}).waitFor();await page.waitForFunction(()=>!document.querySelector('main [role="status"], main .animate-pulse'))}
  const get=async(path)=>{const response=await page.request.get(`http://127.0.0.1:5173/api${path}`);assert.equal(response.status(),200);return response.json()}
  const views=['c1_route_length','c2_stops_per_route','c3_operator_hhi','c6_route_archetypes','c4_urban_rural_routes','c5_length_vs_frequency','c7_network_topology']
  for(const country of ['england','ireland','netherlands','france'])for(const view of views)await check(`${country} Network ${view}`,async()=>{await goto(`/app/${country}/network?view=${view}`);assert.doesNotMatch(await page.locator('main').innerText(),/Something went wrong|Chart could not be rendered|NaN|Infinity/);assert.match(await page.locator('h1').innerText(),/Network/)})
  for(const view of ['c1_route_length','c2_stops_per_route'])await check(`${view} source quartiles/outlier count`,async()=>{
    await goto(`/app/england/network?view=${view}`)
    const payload=await get('/sections?dimension=route_network&country=england')
    const source=payload.sections.find(row=>row.section_id===view)
    const expected=source.chart_data.groups.reduce((total,row)=>total+row.outliers.filter(value=>typeof value==='number'&&Number.isFinite(value)).length,0)
    const plot=page.getByRole('img',{name:view==='c1_route_length'?'Route length distribution':'Stops per route distribution'})
    await plot.locator('svg').waitFor();assert.equal(await plot.locator('[aria-label="dot"] circle').count(),expected)
    assert.match(await page.locator('main').innerText(),/No density curve is inferred/)
    if(view==='c1_route_length')assert.match(await page.locator('main').innerText(),/London has no route-length geometry/)
  })
  await check('HHI uses exact national precision and explicit contextual thresholds',async()=>{await goto('/app/england/network?view=c3_operator_hhi');assert.match(await page.locator('.network-main aside').innerText(),/84\.5/);assert.match(await page.locator('.network-main aside').innerText(),/4\.2%/);assert.match(await page.locator('main').innerText(),/1,500 and 2,500/);const plot=page.getByRole('img',{name:'Regional operator concentration'});await plot.locator('svg').waitFor();assert.match(await plot.innerText(),/10,000/)})
  await check('Actual route archetype selection persists in URL and reload',async()=>{
    await goto('/app/england/network?view=c6_route_archetypes&region=all&pack=2026-08-01')
    const source=(await get('/sections?dimension=route_network&country=england')).sections.find(row=>row.section_id==='c6_route_archetypes')
    const cluster=source.stats.clusters.find(row=>row.id===6)
    await page.getByRole('combobox',{name:'Inspect route archetype'}).selectOption('6');await page.getByRole('heading',{name:'Cluster 6',exact:true}).waitFor()
    assert.equal(new URL(page.url()).searchParams.get('cluster'),'6');assert.equal(new URL(page.url()).searchParams.get('pack'),'2026-08-01');assert.match(await page.locator('main').innerText(),new RegExp(cluster.n.toLocaleString('en-GB')))
    await page.reload({waitUntil:'domcontentloaded'});await page.getByRole('heading',{name:'Cluster 6',exact:true}).waitFor()
    const scatter=page.getByRole('img',{name:'Route archetypes'});await scatter.locator('svg[viewBox]').waitFor();assert.match(await page.locator('.network-archetypes .compact-cluster-legend').innerText(),/6 · Medium-length cross-boundary/)
  })
  await check('Route mix retains actual three national shares, independent regional details',async()=>{await goto('/app/england/network?view=c4_urban_rural_routes');assert.match(await page.locator('.network-metrics').innerText(),/50\.9%/);assert.match(await page.locator('.network-metrics').innerText(),/6\.4%/);assert.match(await page.locator('.network-metrics').innerText(),/42\.7%/);await page.getByText('Regional route mix',{exact:true}).click();await page.getByRole('img',{name:'Regional route mix'}).waitFor();assert.match(await page.locator('main').innerText(),/A mixed route need not cross/)})
  await check('Route relationship uses stops rather than temporal frequency or LSOA observations',async()=>{await goto('/app/england/network?view=c5_length_vs_frequency');assert.match(await page.locator('main').innerText(),/each point is a supplied route observation/);const plot=page.getByRole('img',{name:'Route length vs stop count'});await plot.locator('svg').waitFor();assert.match(await plot.innerText(),/Stops per route \(stop count\)/)})
  for(const width of [768,390])for(const view of views)await check(`${width}px Network ${view}`,async()=>{await page.setViewportSize({width,height:900});await goto(`/app/england/network?view=${view}`);await page.screenshot({path:`${output}/${width}-${view}.png`,fullPage:true})})
}finally{await browser.close();writeFileSync(`${output}/results.json`,JSON.stringify(results,null,2)+'\n')}
console.log(JSON.stringify({passed:results.filter(row=>row.result==='PASS').length,failed:results.filter(row=>row.result==='FAIL')}))
process.exitCode=results.some(row=>row.result==='FAIL')?1:0
