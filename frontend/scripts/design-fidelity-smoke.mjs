import {chromium} from 'playwright'
import assert from 'node:assert/strict'
import {mkdirSync,writeFileSync} from 'node:fs'
const output='../implementation/evidence/fidelity-oct28/browser';mkdirSync(output,{recursive:true})
const browser=await chromium.launch({channel:'chrome',headless:true}),results=[]
try{
 const page=await browser.newPage({reducedMotion:'reduce'})
 const check=async(name,route,width,height,verify)=>{try{await page.setViewportSize({width,height});await page.goto(`http://127.0.0.1:5173${route}`,{waitUntil:'domcontentloaded'});await page.locator('main h1').waitFor();await page.waitForFunction(()=>!document.querySelector('main .animate-pulse,main [role=status]'));await page.evaluate(()=>document.fonts.ready);await verify();assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);results.push({name,result:'PASS'})}catch(error){results.push({name,result:'FAIL',error:error.message})}await page.screenshot({path:`${output}/${name}.png`,fullPage:true});writeFileSync(`${output}/results.json`,JSON.stringify(results,null,2)+'\n')}
 for(const view of ['f1_gini','f2_disparity_ratio','f3_ethnic_access','f5_rural_penalty','f6_equitable_regions'])await check(view,`/app/england/equity?view=${view}`,990,793,async()=>{
  await page.locator('.equity-evidence [role=img]').waitFor();assert.ok(await page.locator('.chart-insights').first().isVisible())
  if(view==='f1_gini'){
   const source=await(await page.request.get('http://127.0.0.1:5173/api/sections?country=england&dimension=equity')).json(),stats=source.sections.find(r=>r.section_id==='f1_gini').stats
   assert.ok((await page.locator('.equity-stat').first().innerText()).includes(stats.gini.toFixed(4)))
   const dimensions=await page.locator('.equity-stat').evaluateAll(nodes=>nodes.map(node=>({height:node.getBoundingClientRect().height,body:getComputedStyle(node.querySelector('p')).fontSize,padding:getComputedStyle(node).padding})));writeFileSync(`${output}/stat-geometry.json`,JSON.stringify(dimensions,null,2))
   await page.getByRole('button',{name:'Show Gini coefficient provenance'}).click();await page.getByRole('dialog').waitFor();await page.getByRole('button',{name:'Close provenance panel'}).click()
  }
 })
 for(const country of ['england','ireland','netherlands','france'])await check(`context-${country}`,`/app/${country}/access?view=a3_walking_distance&region=all&urban_rural=all`,1100,900,async()=>{
  const date=await page.getByLabel('Network',{exact:true}).locator('option:checked').innerText();assert.match(date,/\d{2} \w{3} \d{4}|unavailable|Current pack/)
  const link=page.getByRole('link',{name:'Sign in to Aequitas',exact:true});assert.ok(await link.isVisible());const href=await link.getAttribute('href');assert.ok(new URL(href,'http://localhost').searchParams.get('returnTo').startsWith(`/app/${country}/access`));assert.match(await page.locator('footer').innerText(),/Network:.*Geography:.*Deprivation:/)
 })
 for(const width of [390,591,768,1440])for(const view of ['f1_gini','f6_equitable_regions'])await check(`${view}-${width}`,`/app/england/equity?view=${view}`,width,900,async()=>{assert.ok(await page.locator('.chart-insights').first().isVisible())})
 await check('density','/app/england/access?view=density',991,793,async()=>{assert.equal(await page.locator('.access-density-layout > .app-panel').count(),2);await page.getByRole('link',{name:'Open stop coverage',exact:true}).click();await page.waitForURL(/view=a3_walking_distance/);await page.locator('.access-coverage').waitFor()})
}finally{console.log(JSON.stringify({passed:results.filter(r=>r.result==='PASS').length,failed:results.filter(r=>r.result==='FAIL')}));process.exitCode=results.some(r=>r.result==='FAIL')?1:0;await browser.close()}
