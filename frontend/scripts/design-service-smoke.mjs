import { chromium } from 'playwright'
import assert from 'node:assert/strict'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'

const output = '../implementation/evidence/service-browser-oct24'
mkdirSync(output, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const results = []
try {
  const page = await browser.newPage({ viewport: { width: 1050, height: 850 }, reducedMotion: 'reduce', acceptDownloads: true })
  let errors = []
  page.on('pageerror', error => errors.push(error.message))
  const check = async (name, run) => {
    errors = []
    try { await run(); assert.deepEqual(errors, []); assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'Horizontal overflow'); results.push({ name, result: 'PASS' }) }
    catch (error) { results.push({ name, result: 'FAIL', error: error.message }); await page.screenshot({ path: `${output}/failure-${results.length}.png`, fullPage: true }) }
  }
  const goto = async route => {
    await page.goto(`http://127.0.0.1:5173${route}`, { waitUntil: 'domcontentloaded' })
    await page.getByRole('navigation', { name: 'Evidence views' }).waitFor()
    await page.waitForFunction(() => !document.querySelector('main [role="status"], main .animate-pulse'))
  }
  const get = async path => { const response = await page.request.get(`http://127.0.0.1:5173/api${path}`); assert.equal(response.status(), 200, path); return response.json() }
  const views = ['b1_frequency', 'b2_operating_hours', 'b3_weekend_penalty', 'b4_route_frequency', 'b5_frequency_deprivation', 'table']
  for (const country of ['england','ireland','netherlands','france']) for (const view of views) await check(`${country} Service ${view}`, async () => {
    await goto(`/app/${country}/service?view=${view}`)
    assert.match(await page.locator('h1').innerText(), /Service/)
    assert.doesNotMatch(await page.locator('main').innerText(), /Something went wrong|NaN|Infinity/)
  })
  await check('SQI chart/table and score context use real source values', async () => {
    await goto('/app/england/service?view=b1_frequency')
    const payload = await get('/sections?dimension=service_quality&country=england')
    const source = payload.sections.find(row => row.section_id === 'b1_frequency')
    assert.match(await page.locator('.service-metrics').innerText(), /65\.42 \/ 100/)
    assert.equal(await page.getByRole('table', { name: 'Regional service quality' }).locator('tbody tr').count(), source.chart_data.data.length)
    const plot = page.getByRole('img', { name: 'Service quality by region' })
    await plot.locator('svg').waitFor(); assert.match(await plot.innerText(), /100/)
  })
  await check('Operating ranges preserve London midnight and next-day endpoint', async () => {
    await goto('/app/england/service?view=b2_operating_hours')
    const table = page.getByRole('table', { name: 'Regional operating hours' })
    const london = table.getByRole('row', { name: /^London / })
    assert.match(await london.innerText(), /00:10/); assert.match(await london.innerText(), /00:27 \(\+1d\)/)
    assert.match(await page.locator('.service-metrics').innerText(), /05:35/)
    assert.match(await page.locator('.service-metrics').innerText(), /23:44/)
    assert.match(await page.locator('main').innerText(), /after 19:00/)
  })
  await check('Sunday colors and values correspond to supplied weekday and Sunday observations', async () => {
    await goto('/app/england/service?view=b3_weekend_penalty')
    const plot = page.getByRole('img', { name: 'Weekday and Sunday departures by region' })
    await plot.locator('[aria-label="bar"] rect').first().waitFor()
    const bars = await plot.locator('[aria-label="bar"] rect').evaluateAll(rows => rows.map(row => ({ fill: row.getAttribute('fill'), height:Number(row.getAttribute('height')) })))
    assert.equal(bars.length,18); assert.equal(bars[0].fill,'#6a98b6'); assert.equal(bars[9].fill,'#d65b2d')
    assert.match(await page.locator('.service-metrics').innerText(), /50\.8%/)
    assert.match(await page.locator('.service-metrics').innerText(), /20\.0% · 6,745/)
  })
  await check('Lowest route toggle, source identifiers and reload preserve context', async () => {
    await goto('/app/england/service?view=b4_route_frequency&region=E12000001&pack=2026-08-01')
    const source = await get('/sections?dimension=service_quality&country=england&region=E12000001&pack=2026-08-01')
    const routes = source.sections.find(row => row.section_id === 'b4_route_frequency').stats.bottom_routes
    await page.getByRole('button', { name:'Lowest frequency', exact:true }).click()
    await page.waitForURL(url => url.searchParams.get('rank') === 'lowest')
    await page.getByRole('heading',{name:'Lowest-frequency routes',exact:true}).waitFor()
    const table = page.getByRole('table', { name:'Scheduled route ranking' })
    await table.getByRole('rowheader').first().waitFor()
    assert.equal(await table.locator('tbody tr').count(), routes.length)
    for (const row of routes) assert.match(await table.innerText(),new RegExp(row.route_short_name))
    assert.equal(new URL(page.url()).searchParams.get('region'),'E12000001')
    assert.equal(new URL(page.url()).searchParams.get('pack'),'2026-08-01')
    await page.reload({waitUntil:'domcontentloaded'}); await page.getByRole('button', { name:'Lowest frequency', exact:true }).waitFor()
    assert.equal(await page.getByRole('button', { name:'Lowest frequency', exact:true }).getAttribute('aria-pressed'),'true')
  })
  await check('Actual sample sorting, paging and scoped CSV export', async () => {
    await goto('/app/england/service?view=table&region=E12000005&pack=2026-08-01')
    const source = await get('/sections?dimension=service_quality&country=england&region=E12000005&pack=2026-08-01')
    const exhibit = source.sections.find(row => row.section_id === 'b5_frequency_deprivation')
    const table = page.getByRole('table', { name:'Small-area service sample' })
    assert.equal(await table.locator('tbody tr').count(),Math.min(25,exhibit.chart_data.data.length))
    await page.getByRole('combobox', {name:'Sort service sample'}).selectOption('x-high')
    const highest = Math.max(...exhibit.chart_data.data.map(row => row.x))
    await page.waitForFunction(value => document.querySelector('table[aria-label="Small-area service sample"] tbody tr td')?.textContent === value,highest.toFixed(3))
    if (exhibit.chart_data.data.length > 25) { await page.getByRole('button', {name:'Next sample page'}).click(); await page.waitForURL(url => url.searchParams.get('page')==='2'); await page.locator('.service-pagination').getByText(/26–50/).waitFor(); }
    const pending=page.waitForEvent('download');await page.getByRole('button', {name:'Download service sample CSV'}).click()
    const csv=readFileSync(await(await pending).path(),'utf8')
    assert.equal(csv.trim().split('\n').length,exhibit.chart_data.data.length+1)
    assert.match(csv,/E12000005/);assert.match(csv,/2026-08-01/);assert.match(csv,/IMD Score/)
    await page.getByRole('navigation',{name:'Service evidence display'}).getByRole('link',{name:'Chart',exact:true}).click()
    await page.getByRole('img',{name:'Service quality and deprivation'}).waitFor()
    assert.equal(new URL(page.url()).searchParams.get('region'),'E12000005')
  })
  for (const width of [768,390]) for (const view of views) await check(`${width}px Service ${view}`, async () => {
    await page.setViewportSize({width,height:900});await goto(`/app/england/service?view=${view}`)
    await page.screenshot({path:`${output}/${width}-${view}.png`,fullPage:true})
  })
} finally { await browser.close();writeFileSync(`${output}/results.json`,JSON.stringify(results,null,2)+'\n') }
console.log(JSON.stringify({passed:results.filter(row=>row.result==='PASS').length,failed:results.filter(row=>row.result==='FAIL')}))
process.exitCode=results.some(row=>row.result==='FAIL')?1:0
