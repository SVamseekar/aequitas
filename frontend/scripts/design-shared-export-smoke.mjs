import {chromium} from 'playwright'
import assert from 'node:assert/strict'
import {mkdirSync,writeFileSync} from 'node:fs'
const output='../implementation/evidence/shared-export-browser-oct24';mkdirSync(output,{recursive:true})
const browser=await chromium.launch({channel:'chrome',headless:true}),results=[]
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'})
 let errors=[];page.on('pageerror',error=>errors.push(error.message))
 const check=async(name,run)=>{errors=[];try{await run();assert.deepEqual(errors,[]);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Horizontal overflow');results.push({name,result:'PASS'})}catch(error){results.push({name,result:'FAIL',error:error.message});await page.screenshot({path:`${output}/failure-${results.length}.png`,fullPage:true})}}
 const goto=async(route)=>{await page.goto(`http://127.0.0.1:5173${route}`,{waitUntil:'domcontentloaded'});await page.locator('main h1').first().waitFor();await page.waitForFunction(()=>!document.querySelector('main [role="status"],main .animate-pulse'));await page.evaluate(()=>document.fonts.ready)}
 const get=async(path)=>{const response=await page.request.get(`http://127.0.0.1:5173/api${path}`);assert.equal(response.status(),200,await response.text());return response.json()}
 for(const country of ['england','ireland','france'])await check(`${country} actual research pack preview and metadata`,async()=>{
  await goto(`/app/${country}?view=export`)
  await page.getByRole('heading',{name:new RegExp(`Aequitas research briefing — ${country}`,'i')}).waitFor()
  const source=await get(`/export/pack.json?country=${country}`)
  assert.equal(source.filter.country,country)
  assert.ok((await page.locator('.research-findings').innerText()).includes(source.score.score.toFixed(1)))
  for(const value of Object.values(source.vintages))assert.ok((await page.locator('.research-metadata').innerText()).includes(value))
  await page.locator('.research-document canvas,.research-document svg[aria-label="Regional choropleth"]').first().waitFor({timeout:15000})
  await page.screenshot({path:`${output}/${country}-preview.png`,fullPage:true})
 })
 await check('Netherlands research export stays unavailable without country fallback',async()=>{await goto('/app/netherlands?view=export');assert.match(await page.locator('main').innerText(),/Netherlands research pack is not available/);assert.equal(await page.locator('.research-document').count(),0)})
 await check('Historical and unknown export scopes never show current report',async()=>{for(const pack of ['2020-01-01','2099-01-01']){await goto(`/app/ireland?view=export&pack=${pack}`);assert.match(await page.locator('main').innerText(),/Historical research packs are unavailable/);assert.equal(await page.locator('.research-document').count(),0);const response=await page.request.get(`http://127.0.0.1:5173/api/export/pack.json?country=ireland&pack=${pack}`);assert.equal(response.status(),400)}})
 await check('Ireland Dublin urban report/CSV/HTML retain identical scope',async()=>{
  await goto('/app/ireland?view=export&region=dublin&urban_rural=urban')
  await page.getByRole('heading',{name:'Aequitas research briefing — Ireland'}).waitFor()
  assert.match(await page.locator('.research-scope').innerText(),/Dublin.*Urban/)
  await page.locator('.research-export-toolbar summary').click()
  const href=await page.getByRole('link',{name:'Printable HTML (tables)'}).getAttribute('href'),url=new URL(href,'http://127.0.0.1:5173')
  assert.equal(url.searchParams.get('country'),'ireland');assert.equal(url.searchParams.get('region'),'dublin');assert.equal(url.searchParams.get('urban_rural'),'urban')
  const html=await page.request.get(url.href);assert.equal(html.status(),200);assert.match(await html.text(),/Dublin/)
  const [download]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'CSV (data tables)'}).click()])
  const path=`${output}/ireland-dublin-urban.csv`;await download.saveAs(path)
  const source=await get('/export/pack.json?country=ireland&region=dublin&urban_rural=urban')
  const {readFileSync}=await import('node:fs'),csv=readFileSync(path,'utf8');assert.match(csv,/Country,ireland/);assert.match(csv,/Region,dublin/);assert.match(csv,/Urban or rural,urban/);assert.ok(csv.includes(String(source.score.score)))
  await page.getByRole('link',{name:'Return to overview'}).click();assert.equal(new URL(page.url()).searchParams.get('region'),'dublin');assert.equal(new URL(page.url()).searchParams.get('urban_rural'),'urban')
 })
 await check('Overview export entry retains country/region/date',async()=>{
  await goto('/app/england?region=E12000005&pack=2026-08-01')
  await page.getByRole('link',{name:'Export research pack'}).click();await page.getByRole('heading',{name:'Export research pack',exact:true}).waitFor()
  assert.equal(new URL(page.url()).searchParams.get('pack'),'2026-08-01');assert.equal(new URL(page.url()).searchParams.get('region'),'E12000005')
  await page.getByRole('heading',{name:'Aequitas research briefing — England'}).waitFor()
 })
 await check('Empty London-rural geography resets only area selection',async()=>{await goto('/app/england?region=E12000007&urban_rural=rural&pack=2026-08-01');await page.getByRole('heading',{name:'No areas match this filter'}).waitFor();await page.getByRole('link',{name:'Reset area filter'}).click();assert.equal(new URL(page.url()).searchParams.get('urban_rural'),'all');assert.equal(new URL(page.url()).searchParams.get('region'),'E12000007');assert.equal(new URL(page.url()).searchParams.get('pack'),'2026-08-01')})
 await check('Overview Gini opens actual national evidence with focus restore',async()=>{await goto('/app/england');const trigger=page.getByRole('button',{name:'Show Gini evidence and calculation'});await trigger.click();const dialog=page.getByRole('dialog',{name:'Data provenance'});await dialog.waitFor();await dialog.getByText('0.5741',{exact:true}).waitFor();assert.match(await dialog.innerText(),/Stored national provenance/);await page.keyboard.press('Escape');assert.equal(await trigger.evaluate(node=>node===document.activeElement),true)})
 await check('Region change waits for actual new map geometry before enabling print',async()=>{
  await goto('/app/ireland?view=export')
  await page.locator('.research-export-toolbar summary').click()
  const print=page.getByRole('button',{name:'Print this preview'})
  await print.waitFor()
  await page.waitForFunction(()=>!document.querySelector('.research-export-menu button:last-of-type')?.disabled)
  let release
  const geometry=new Promise(resolve=>{release=resolve})
  const hold=async route=>{
   await geometry
   // React can abort an obsolete map request while this transport gate waits.
   try{await route.continue()}catch(error){if(!/Route is already handled/.test(error.message))throw error}
  }
  await page.route('**/boundaries/ireland_counties.geojson',hold)
  try{
   await Promise.all([page.waitForRequest('**/boundaries/ireland_counties.geojson'),page.getByLabel('Region',{exact:true}).selectOption('dublin')])
   await page.getByRole('heading',{name:'Aequitas research briefing — Ireland'}).waitFor()
   assert.match(await page.locator('.research-scope').innerText(),/Dublin/)
   if(!await page.locator('.research-export-toolbar details').evaluate(node=>node.open))await page.locator('.research-export-toolbar summary').click()
   assert.equal(await print.isDisabled(),true)
   release()
   await page.waitForFunction(()=>!document.querySelector('.research-export-menu button:last-of-type')?.disabled)
   assert.equal(await print.isEnabled(),true)
  }finally{release();await page.unroute('**/boundaries/ireland_counties.geojson',hold)}
 })
 await check('Protected dimension PDF remains unauthorized for real anonymous request',async()=>{assert.equal((await page.request.get('http://127.0.0.1:5173/api/export/equity')).status(),401)})
 for(const width of [768,390])for(const country of ['england','ireland'])await check(`${width}px ${country} research preview`,async()=>{await page.setViewportSize({width,height:900});await goto(`/app/${country}?view=export`);await page.getByRole('heading',{name:new RegExp(`Aequitas research briefing — ${country}`,'i')}).waitFor();await page.screenshot({path:`${output}/${width}-${country}-preview.png`,fullPage:true})})
 await check('A4 print hides application controls and retains report',async()=>{await page.setViewportSize({width:794,height:1123});await page.emulateMedia({media:'print'});assert.equal(await page.getByRole('navigation',{name:'Quick navigation'}).isVisible(),false);assert.equal(await page.getByRole('link',{name:'Return to overview'}).isVisible(),false);assert.equal(await page.locator('.research-document').isVisible(),true);await page.screenshot({path:`${output}/print-preview.png`,fullPage:true});await page.emulateMedia({media:'screen'})})
 await check('Simulated research transport failure retains filters and retries real data',async()=>{
  await page.route('**/api/export/pack.json?**',route=>route.fulfill({status:500,contentType:'application/json',body:JSON.stringify({detail:'Simulated verification failure'})}))
  await goto('/app/ireland?view=export&region=cork&urban_rural=rural')
  await page.getByRole('heading',{name:'Could not load research evidence'}).waitFor()
  await page.screenshot({path:`${output}/simulated-research-error.png`,fullPage:true})
  await page.unroute('**/api/export/pack.json?**')
  await page.getByRole('button',{name:'Retry research pack'}).click()
  await page.getByRole('heading',{name:'Aequitas research briefing — Ireland'}).waitFor()
  assert.equal(new URL(page.url()).searchParams.get('region'),'cork');assert.equal(new URL(page.url()).searchParams.get('urban_rural'),'rural')
 })
}finally{await browser.close();writeFileSync(`${output}/results.json`,JSON.stringify(results,null,2)+'\n')}
console.log(JSON.stringify({passed:results.filter(row=>row.result==='PASS').length,failed:results.filter(row=>row.result==='FAIL')}));process.exitCode=results.some(row=>row.result==='FAIL')?1:0
