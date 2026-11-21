import { chromium } from 'playwright'
import assert from 'node:assert/strict'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
const output = process.env.DESIGN_EVIDENCE_DIR ?? '../implementation/evidence/observe-browser-oct23'
mkdirSync(output, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const results=[]
try {
 const page=await browser.newPage({viewport:{width:1024,height:800},reducedMotion:'reduce',acceptDownloads:true})
 let errors=[];page.on('pageerror',e=>errors.push(e.message))
 const check=async(name,run)=>{errors=[];try{await run();assert.deepEqual(errors,[]);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Horizontal overflow');results.push({name,result:'PASS'})}catch(e){results.push({name,result:'FAIL',error:e.message});await page.screenshot({path:`${output}/failure-${results.length}.png`,fullPage:true})}}
 const goto=async route=>{await page.goto(`http://127.0.0.1:5173${route}`,{waitUntil:'domcontentloaded'});await page.locator('main h1').waitFor();await page.waitForFunction(()=>!document.querySelector('main [role=status]'))}
 for(const metric of ['score','pct_400m','evening_isolated_pct','mean_sqi'])await check(`Time ${metric} uses registered points and CSV`,async()=>{
  await goto(`/app/england/time?metric=${metric}`);const api=await(await page.request.get(`/api/time?country=england&metric=${metric}`.replace('/api','http://127.0.0.1:5173/api'))).json();assert.equal(api.points.length,2);assert.equal(await page.locator('.time-page aside dl>div').count(),2)
  const last=api.points.at(-1);assert.match(await page.locator('.app-score-number').innerText(),new RegExp(last.value.toFixed(metric==='mean_sqi'?2:1).replace('.','\\.')))
  const pending=page.waitForEvent('download');await page.getByRole('button',{name:'Export observations CSV',exact:true}).click();const csv=readFileSync(await(await pending).path(),'utf8');assert.equal(csv.split('\n').length,3);assert.match(csv,/2026-08-01/);assert.match(csv,/2026-09-25/);await page.screenshot({path:`${output}/time-${metric}.png`,fullPage:true})
 })
 for(const country of ['england','ireland','netherlands','france'])for(const view of ['snapshot','regional','deprivation','sources'])await check(`${country} Ops ${view}`,async()=>{
  await goto(`/app/${country}/ops?view=${view}`);const response=await page.request.get(`http://127.0.0.1:5173/api/ops?country=${country}`)
  if(response.status()===404){assert.match(await page.locator('main').innerText(),/No ops rollup/);return}
  const data=await response.json();if(!data.empty){assert.match(await page.locator('main').innerText(),new RegExp(data.n_updates.toLocaleString('en-GB')));if(data.n_with_delay===0)assert.match(await page.locator('main').innerText(),/Punctuality: —/);if(view==='sources')assert.match(await page.locator('main').innerText(),/Stored feed metadata/)}
  if(country==='england'&&view==='deprivation'&&!data.by_imd_decile?.some(row=>row.n_updates>0)){assert.match(await page.locator('main').innerText(),/No IMD-decile join/);assert.equal(await page.getByRole('img',{name:'Updates by deprivation decile'}).count(),0)}
  await page.screenshot({path:`${output}/${country}-${view}.png`,fullPage:true})
 })
 await check('Static area filters do not pretend to subset collector data',async()=>{await goto('/app/england/ops?view=regional&region=E12000007&urban_rural=rural');assert.match(await page.locator('main').innerText(),/29,391/);assert.match(await page.locator('main').innerText(),/independent of the static region/);await page.getByRole('table',{name:'Regional update summary'}).waitFor()})
 for(const width of [768,390])for(const route of ['time?metric=mean_sqi','ops?view=regional','ops?view=deprivation'])await check(`${width}px ${route}`,async()=>{await page.setViewportSize({width,height:900});await goto(`/app/england/${route}`);await page.screenshot({path:`${output}/${width}-${route.replaceAll('?','-').replaceAll('=','-')}.png`,fullPage:true})})
}finally{writeFileSync(`${output}/results.json`,JSON.stringify(results,null,2)+'\n');console.log('Assertions finished',results.filter(row=>row.result==='PASS').length);await browser.close()}
console.log(JSON.stringify({passed:results.filter(row=>row.result==='PASS').length,failed:results.filter(row=>row.result==='FAIL')}));process.exitCode=results.some(row=>row.result==='FAIL')?1:0
