import {chromium} from 'playwright'
import assert from 'node:assert/strict'
import {mkdirSync,writeFileSync} from 'node:fs'
const output='../implementation/evidence/workspace-browser-oct24';mkdirSync(output,{recursive:true})
const browser=await chromium.launch({channel:'chrome',headless:true}),results=[]
try{
 const page=await browser.newPage({viewport:{width:1100,height:900},reducedMotion:'reduce'})
 let errors=[];page.on('pageerror',error=>errors.push(error.message))
 const check=async(name,run)=>{errors=[];try{await run();assert.deepEqual(errors,[]);results.push({name,result:'PASS'})}catch(error){results.push({name,result:'FAIL',error:error.message});await page.screenshot({path:`${output}/failure-${results.length}.png`,fullPage:true})}}
 const goto=async(route)=>{await page.goto(`http://127.0.0.1:5173${route}`,{waitUntil:'networkidle'})}
 const fits=async()=>assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Horizontal overflow')
 await check('Real anonymous API session remains unauthorized',async()=>{assert.equal((await page.request.get('http://127.0.0.1:5173/api/auth/me')).status(),401)})
 for(const path of ['/saved','/notes','/regions','/conversations','/profile'])await check(`Protected ${path}`,async()=>{await goto(path);assert.equal(new URL(page.url()).pathname,'/');assert.equal(await page.locator('.workspace-page,.account-page').count(),0)})
 for(const width of [1100,768,390]){
  await page.setViewportSize({width,height:900})
  await check(`${width}px sign-in keeps local return destination`,async()=>{await goto('/auth?returnTo=%2Fapp%2Fireland%2Faccess%3Fregion%3Ddublin');await page.getByRole('heading',{name:'Sign in to Aequitas'}).waitFor();await page.getByRole('button',{name:'Continue with Google'}).waitFor();await fits();await page.screenshot({path:`${output}/${width}-auth.png`,fullPage:true})})
  await check(`${width}px unavailable invitation has retry and no acceptance`,async()=>{await goto('/invite/design-preview-invalid');await page.getByRole('heading',{name:'Invitation unavailable'}).waitFor();assert.equal(await page.getByRole('button',{name:'Accept invitation',exact:true}).count(),0);await page.getByRole('button',{name:'Retry invitation'}).waitFor();await fits();await page.screenshot({path:`${output}/${width}-invite-unavailable.png`,fullPage:true})})
  await check(`${width}px anonymous assistant retains scope, focus trap and close`,async()=>{
   await goto('/app/ireland/access?region=dublin&urban_rural=urban&pack=2026-08-01')
   const trigger=page.getByRole('button',{name:'Open AI chat'});await trigger.click()
   const dialog=page.getByRole('dialog',{name:'Ask Aequitas chat'});await dialog.waitFor()
   await dialog.getByRole('heading',{name:'Sign in to ask Aequitas'}).waitFor()
   assert.equal(await dialog.getByLabel('Ask about this evidence').isDisabled(),true)
   assert.match(await dialog.locator('.chat-context').innerText(),/Ireland.*Dublin.*urban.*2026-08-01/)
   const href=await dialog.getByRole('link',{name:'Continue to sign in'}).getAttribute('href')
   assert.equal(new URL(href,'http://localhost').searchParams.get('returnTo'),'/app/ireland/access?region=dublin&urban_rural=urban&pack=2026-08-01')
   await page.waitForFunction(()=>document.querySelector('[role="dialog"]')?.contains(document.activeElement))
   const first=dialog.getByRole('button',{name:'Clear chat messages'});await first.focus();await page.keyboard.press('Shift+Tab')
   assert.equal(await dialog.getByRole('link',{name:'Continue to sign in'}).evaluate(node=>node===document.activeElement),true)
   await fits();await page.screenshot({path:`${output}/${width}-anonymous-assistant.png`,fullPage:true})
   await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});assert.equal(await trigger.evaluate(node=>node===document.activeElement),true)
   assert.equal(await page.evaluate(()=>document.body.style.overflow),'')
  })
 }
}finally{await browser.close();writeFileSync(`${output}/results.json`,JSON.stringify(results,null,2)+'\n')}
console.log(JSON.stringify({passed:results.filter(row=>row.result==='PASS').length,failed:results.filter(row=>row.result==='FAIL')}));process.exitCode=results.some(row=>row.result==='FAIL')?1:0
