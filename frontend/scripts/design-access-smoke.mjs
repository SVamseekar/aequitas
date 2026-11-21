import { chromium } from 'playwright'
import assert from 'node:assert/strict'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'

const output = process.env.DESIGN_EVIDENCE_DIR ?? '../implementation/evidence/access-browser-oct24'
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
  const get = async path => {
    const response = await page.request.get(`http://127.0.0.1:5173/api${path}`)
    assert.equal(response.status(), 200, path)
    return response.json()
  }
  for (const country of ['england', 'ireland', 'netherlands', 'france']) for (const view of ['a3_walking_distance', 'a5_service_deserts', 'a6_urban_rural_gap', 'facilities', 'destinations', 'density', 'a4_coverage_equity', 'a7_investment_gap', 'a8_coverage_prediction']) await check(`${country} Access ${view}`, async () => {
    await goto(`/app/${country}/access?view=${view}`)
    const text = await page.locator('main').innerText()
    assert.doesNotMatch(text, /Something went wrong rendering|Chart could not be rendered/)
    if (view === 'facilities') {
      assert.equal(await page.locator('.access-facility-cards article').count(), 3)
      assert.match(text, /Inventory scope: national/)
      const data = await get(`/destinations?country=${country}`)
      for (const [index,key] of ['jobs','gp','school'].entries()) {
        const row = data.facility_400m[key]
        assert.equal(await page.locator('.access-facility-cards strong').nth(index).innerText(), row?.available && row.people_share != null ? `${(row.people_share * 100).toFixed(1)}%` : '—')
      }
    }
    if (view === 'destinations' && country !== 'england') { assert.match(text, /Not available in this pack/); assert.equal(await page.locator('.access-travel [aria-label^="Distribution"]').count(), 0) }
    if (view === 'a8_coverage_prediction' && country === 'england') assert.match(text, /0\.0830/)
  })
  await check('Coverage keeps actual area denominator, geographic values and scoped CSV', async () => {
    await goto('/app/england/access?view=a3_walking_distance&region=E12000005&pack=2026-08-01&urban_rural=all')
    assert.match(await page.locator('main').innerText(), /area-based, rather than population-weighted/)
    const source = await get('/map?country=england&region=E12000005&metric=coverage&pack=2026-08-01')
    const table = page.getByRole('table', { name: 'Geographic coverage' })
    assert.equal(await table.locator('tbody tr').count(), source.data.length)
    const pending = page.waitForEvent('download')
    await page.getByRole('button', { name: 'Download coverage CSV' }).click()
    const csv = readFileSync(await (await pending).path(), 'utf8')
    assert.match(csv, /% of LSOAs/); assert.match(csv, /E12000005/); assert.match(csv, /2026-08-01/)
  })
  await check('Sunday summary and district inspection do not substitute zero-stop populations', async () => {
    await goto('/app/england/access?view=a5_service_deserts')
    const payload = await get('/sections?dimension=service_quality&country=england')
    const stats = payload.sections.find(section => section.section_id === 'b3_weekend_penalty').stats
    assert.match(await page.locator('.access-metrics').innerText(), new RegExp(stats.n_sunday_desert.toLocaleString('en-GB')))
    assert.match(await page.locator('main').innerText(), /Sunday-desert population is not stored/)
    const access = await get('/sections?dimension=accessibility&country=england')
    const row = access.sections.find(section => section.section_id === 'a5_service_deserts').chart_data.data[0]
    await page.getByRole('combobox', { name: 'Inspect district' }).selectOption(row.area_code)
    await page.waitForURL(url => url.searchParams.get('lad') === row.area_code)
    await page.locator('.access-desert-layout aside').getByRole('heading', { name: row.area_name, exact: true }).waitFor()
    assert.match(await page.locator('.access-desert-layout aside').innerText(), new RegExp(row.value.toFixed(1).replace('.', '\\.') + '%'))
    await page.reload({ waitUntil: 'domcontentloaded' })
    await page.getByRole('combobox', { name: 'Inspect district' }).waitFor()
    assert.equal(await page.getByRole('combobox', { name: 'Inspect district' }).inputValue(), row.area_code)
  })
  await check('Travel-time controls use actual zero and retain configuration in Reach deep link', async () => {
    await goto('/app/england/access?view=destinations&region=E12000005&pack=2026-08-01&dest=jobs&cutoff=45')
    assert.match(await page.locator('.access-travel-layout aside').innerText(), /42/)
    await page.getByRole('button', { name: 'School', exact: true }).click()
    await page.getByRole('button', { name: '15 min', exact: true }).click()
    await page.waitForURL(url => url.searchParams.get('dest') === 'school' && url.searchParams.get('cutoff') === '15')
    await page.waitForFunction(() => document.querySelector('.access-travel-layout aside strong')?.textContent === '0')
    const link = page.getByRole('link', { name: 'Open all nine configurations in Reach' })
    await link.click()
    await page.getByRole('table', { name: 'Destination availability' }).waitFor()
    const url = new URL(page.url())
    for (const [key,value] of Object.entries({ view:'travel-time',dest:'school',cutoff:'15',region:'E12000005',pack:'2026-08-01' })) assert.equal(url.searchParams.get(key), value)
  })
  await check('Historical travel-time request remains unavailable', async () => {
    await goto('/app/england/access?view=destinations&region=E12000005&pack=2026-09-25')
    await page.getByRole('alert').waitFor()
    assert.equal(await page.locator('.access-travel [aria-label^="Distribution"]').count(), 0)
    assert.match(await page.getByRole('alert').innerText(), /Historical results are unavailable/)
  })
  await check('Facility inventory explicitly remains national after regional/date selection', async () => {
    await goto('/app/england/access?view=facilities&region=E12000005&pack=2026-09-25&urban_rural=urban')
    assert.match(await page.locator('.access-inventory-scope').innerText(), /region, area and network-date controls do not subset/)
    assert.match(await page.locator('main').innerText(), /every centroid|Every centroid/)
  })
  await check('Settlement summary draws both actual means from a common zero', async () => {
    await goto('/app/england/access?view=a6_urban_rural_gap')
    const bars = page.getByRole('img', { name: 'Urban and rural mean trips per capita' }).locator('[aria-label="bar"] rect')
    await bars.first().waitFor()
    assert.equal(await bars.count(), 2)
    const geometry = await bars.evaluateAll(rows => rows.map(row => ({ y:Number(row.getAttribute('y')), height:Number(row.getAttribute('height')) })))
    assert.ok(geometry[1].height > 0)
    assert.ok(Math.abs(geometry[0].y+geometry[0].height-geometry[1].y-geometry[1].height) < 0.001)
    assert.ok(Math.abs(geometry[0].height/geometry[1].height-0.28/0.12) < 0.001)
  })
  for (const width of [768,390]) for (const view of ['a3_walking_distance','a5_service_deserts','a6_urban_rural_gap','facilities','destinations','density','a4_coverage_equity','a7_investment_gap','a8_coverage_prediction']) await check(`${width}px Access ${view}`, async () => {
    await page.setViewportSize({ width,height:900 })
    await goto(`/app/england/access?view=${view}&region=E12000005`)
    await page.screenshot({ path: `${output}/${width}-${view}.png`,fullPage:true })
  })
} finally { await browser.close(); writeFileSync(`${output}/results.json`,JSON.stringify(results,null,2)+'\n') }
console.log(JSON.stringify({ passed:results.filter(row=>row.result==='PASS').length,failed:results.filter(row=>row.result==='FAIL') }))
process.exitCode=results.some(row=>row.result==='FAIL')?1:0
