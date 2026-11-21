import { chromium } from 'playwright'
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const args = process.argv.slice(2)
const option = (name, fallback) => { const at = args.indexOf(name); return at < 0 ? fallback : args[at + 1] }
const id = option('--screen', 'D01-01')
const manifest = JSON.parse(readFileSync(path.join(repo, 'design/screen-status.json')))
const screen = [...manifest.screens, ...manifest.supplemental].find(s => s.id === id)
if (!screen) throw new Error(`Unknown screen ${id}`)
const phase = option('--phase', 'current')
if (!/^[a-z0-9-]+$/i.test(phase)) throw new Error('Invalid phase')
const output = path.join(repo, 'implementation/evidence', phase, id)
mkdirSync(output, { recursive: true })
const viewport = screen.viewport ?? { width: 1586, height: 992 }
const browser = await chromium.launch({ channel: process.env.DESIGN_BROWSER ?? 'chrome', headless: true, args: ['--enable-webgl', '--use-gl=angle', '--use-angle=swiftshader'] })
try {
  const context = await browser.newContext({ viewport, reducedMotion: 'reduce', colorScheme: 'light', locale: 'en-GB' })
  const page = await context.newPage()
  if(screen.networkFault){
    const fault=screen.networkFault
    if(!['/api/overview','/api/export/pack.json','/api/provenance/gini_national'].includes(fault.path)||![500,503].includes(fault.status))throw new Error('Unsupported read-only verification fault')
    await page.route('**/api/**',route=>new URL(route.request().url()).pathname===fault.path&&route.request().method()==='GET'?route.fulfill({status:fault.status,contentType:'application/json',body:JSON.stringify({detail:'Simulated verification transport failure'})}):route.continue())
  }
  const errors = [], failedRequests = [], responses = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('requestfailed', request => failedRequests.push({ url: request.url(), error: request.failure()?.errorText }))
  page.on('response', response => { if (response.status() >= 400) responses.push({ url: response.url(), status: response.status() }) })
  await page.goto(`${process.env.BASE_URL ?? 'http://127.0.0.1:5173'}${screen.captureRoute ?? screen.route}`, { waitUntil: 'networkidle' })
  if (screen.route.startsWith('/app/')) await page.getByRole('navigation', { name: 'Application', exact: true, includeHidden: true }).waitFor({ state: 'attached', timeout: 30000 })
  else await page.locator('#root .landing-root, #root .app-redesign').first().waitFor({ timeout: 10000 })
  await page.evaluate(() => document.fonts.ready)
  for (const action of screen.actions ?? []) {
    if(action.type==='hover-region'){
      const map=page.locator('.app-map-panel .maplibregl-canvas');await map.waitFor({timeout:20000})
      const bounds=await map.boundingBox();if(!bounds)throw new Error('Map canvas has no bounds')
      let found=false
      for(let y=30;y<bounds.height-20&&!found;y+=18)for(let x=30;x<bounds.width-20&&!found;x+=18){
        await page.mouse.move(bounds.x+x,bounds.y+y);await page.waitForTimeout(12)
        found=(await page.locator('.maplibregl-popup-content strong').allTextContents()).some(text=>text===action.name)
      }
      if(!found)throw new Error(`Actual region hover not found: ${action.name}`)
    }else{
      if (action.type !== 'click') throw new Error(`Unsupported action ${action.type}`)
      await page.getByRole(action.role ?? 'button', { name: action.name, exact: true }).click()
    }
  }
  if(screen.waitForHeading)await page.getByRole('heading',{name:screen.waitForHeading,exact:true}).waitFor()
  await page.waitForTimeout(1500)
  if(screen.captureSelector)await page.locator(screen.captureSelector).screenshot({path:path.join(output,'rendered.png'),animations:'disabled'})
  else await page.screenshot({ path: path.join(output, 'rendered.png'), animations: 'disabled' })
  await page.screenshot({ path: path.join(output, 'full-page.png'), fullPage: true, animations: 'disabled' })
  const layout = await page.evaluate(() => ({ url: location.href, title: document.title, horizontalOverflow: document.documentElement.scrollWidth > innerWidth, headings: [...document.querySelectorAll('h1,h2,h3')].map(n => n.textContent), links: [...document.querySelectorAll('nav a')].map(n => ({ text: n.textContent, href: n.getAttribute('href') })) }))
  const evidence = { screen: id, phase, capturedAt: new Date().toISOString(), viewport, captureSelector:screen.captureSelector??null, simulatedNetworkFault:screen.networkFault??null, reference: screen.reference, referenceCrop: screen.referenceCrop ?? null, layout, errors, failedRequests, responses, comparison: 'NOT_PERFORMED', functional: 'NOT_PERFORMED' }
  writeFileSync(path.join(output, 'capture.json'), JSON.stringify(evidence, null, 2) + '\n')
  console.log(JSON.stringify({ id, output, ...layout, errors, responses }, null, 2))
} catch(error) {
  process.exitCode=1;console.error(error)
} finally {
  let closed=false
  await Promise.race([browser.close().then(()=>{closed=true}),new Promise(resolve=>setTimeout(resolve,10000))])
  if(!closed)writeFileSync(path.join(output,'browser-cleanup.json'),JSON.stringify({result:'TIMEOUT',note:'Capture outcome recorded before browser cleanup; driver terminated after bounded close.'},null,2)+'\n')
  process.exit(process.exitCode??0)
}
