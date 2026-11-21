import { chromium } from 'playwright'
import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync } from 'node:fs'

const output = process.env.DESIGN_EVIDENCE_DIR ?? '../implementation/evidence/evidence-browser-oct23'
mkdirSync(output, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const results = []
try {
  const page = await browser.newPage({ viewport: { width: 1050, height: 820 }, reducedMotion: 'reduce' })
  let errors = []
  page.on('pageerror', error => errors.push(error.message))
  const check = async (name, run) => {
    errors = []
    try { await run(); assert.deepEqual(errors, []); assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'Horizontal overflow'); results.push({ name, result: 'PASS' }) }
    catch (error) { results.push({ name, result: 'FAIL', error: error.message }); await page.screenshot({ path: `${output}/failure-${results.length}.png`, fullPage: true }) }
  }
  const goto = async route => {
    await page.goto(`http://127.0.0.1:5173${route}`, { waitUntil: 'domcontentloaded' })
    await page.locator('main h1').waitFor()
    await page.locator('.evidence-featured,.country-correlations').first().waitFor()
  }
  for (const view of ['f1_gini', 'f2_disparity_ratio', 'f3_ethnic_access', 'f5_rural_penalty', 'f6_equitable_regions']) await check(`England ${view} source units and stored marks`, async () => {
    await goto(`/app/england/equity?view=${view}`)
    await page.locator('.evidence-chart svg').last().waitFor()
    const text = await page.locator('main').innerText()
    if (view === 'f1_gini') { assert.match(text, /0\.5741/); assert.match(text, /5\.702/); assert.match(text, /0\.1358/) }
    if (view === 'f2_disparity_ratio') { assert.match(text, /Trips per capita/); assert.equal(await page.locator('.evidence-chart [aria-label="bar"] rect').count(), 10) }
    if (view === 'f3_ethnic_access') { assert.match(text, /-0\.3127/); assert.match(text, /area-level|area level/); assert.equal(await page.locator('.evidence-chart [aria-label="dot"] circle').count(), 2000) }
    if (view === 'f5_rural_penalty') { assert.match(text, /London.*rural.*unavailable/s); assert.equal(await page.locator('.evidence-chart [aria-label="bar"] rect').count(), 17) }
    if (view === 'f6_equitable_regions') { assert.match(text, /Regional vulnerability/); assert.match(text, /not Gini/); assert.equal(await page.locator('.evidence-chart [aria-label="bar"] rect').count(), 9) }
    await page.screenshot({ path: `${output}/${view}.png`, fullPage: true })
  })
  for (const country of ['england', 'ireland', 'netherlands', 'france']) await check(`${country} provenance stays scoped and returns focus`, async () => {
    await goto(`/app/${country}/equity?view=f1_gini`)
    const trigger = page.getByRole('button', { name: 'Show data provenance' })
    const pending = page.waitForResponse(response => response.url().includes('/api/provenance/gini_national'))
    await trigger.click()
    const response = await pending
    assert.equal(new URL(response.url()).searchParams.get('country'), country)
    const dialog = page.getByRole('dialog', { name: 'Data provenance' })
    await dialog.waitFor()
    if (response.ok()) {
      const data = await response.json()
      await dialog.getByText(data.value.toLocaleString('en-GB', { minimumFractionDigits: 4, maximumFractionDigits: 4 }), { exact: true }).waitFor()
    } else await dialog.getByRole('button', { name: 'Retry provenance' }).waitFor()
    await page.keyboard.press('Escape')
    assert.equal(await dialog.count(), 0)
    assert.equal(await trigger.evaluate(node => node === document.activeElement), true)
  })
  for (const country of ['ireland', 'netherlands', 'france']) {
    await check(`${country} heatmap retains actual finite cells and source counts`, async () => {
      await goto(`/app/${country}/correlations?view=d7_deprivation_urban_rural`)
      await page.locator('.country-correlation-layout [aria-label="cell"] rect').first().waitFor()
      const payload = await (await page.request.get(`http://127.0.0.1:5173/api/sections?country=${country}&dimension=correlations`)).json()
      const source = payload.sections.find(section => section.section_id === 'd7_deprivation_urban_rural')
      const cells = (source.chart_data.values ?? source.chart_data.z).flat().filter(value => typeof value === 'number' && Number.isFinite(value))
      assert.equal(await page.locator('.country-correlation-layout [aria-label="cell"] rect').count(), cells.length)
      assert.match(await page.locator('main').innerText(), /People within 400 m \(%\)/)
      assert.doesNotMatch(await page.locator('.country-correlation-layout').innerText(), /−100/)
      for (const key of ['n_with_ses', 'n_without_ses', 'n_with_fedi', 'n_without_fedi']) if (typeof source.stats[key] === 'number') assert.match(await page.locator('main').innerText(), new RegExp(source.stats[key].toLocaleString('en-GB')))
      await page.screenshot({ path: `${output}/${country}-matrix.png`, fullPage: true })
    })
    await check(`${country} origin and source views retain URL context`, async () => {
      await goto(`/app/${country}/correlations?view=d7_deprivation_urban_rural&pack=current`)
      await page.getByRole('button', { name: country === 'ireland' ? 'Ethnicity' : 'Origin share', exact: true }).click()
      await page.waitForURL(/view=origin/)
      assert.equal(new URL(page.url()).searchParams.get('pack'), 'current')
      await page.locator('.country-correlations [role=status]').waitFor({ state: 'detached' })
      if (country === 'france') assert.doesNotMatch(await page.locator('main').innerText(), /Buiten Europa/)
      await page.getByRole('button', { name: 'Notes & sources', exact: true }).click()
      await page.waitForURL(/view=sources/)
      await page.getByRole('heading', { name: /Notes and sources/ }).waitFor()
      assert.match(await page.locator('main').innerText(), /Network date/)
      await page.getByRole('button', { name: 'More evidence', exact: true }).click()
      await page.getByRole('combobox', { name: 'Additional warehouse exhibit' }).waitFor()
    })
  }
  await check('Dutch mode control reloads the selected country heatmap', async () => {
    await goto('/app/netherlands/correlations?view=d7_deprivation_urban_rural&region=groningen&pack=current')
    await page.getByRole('button', { name: 'All public transport', exact: true }).click()
    await page.waitForURL(/mode=all/)
    assert.equal(new URL(page.url()).searchParams.get('view'), 'd7_deprivation_urban_rural')
    assert.equal(new URL(page.url()).searchParams.get('region'), 'groningen')
    await page.locator('.country-correlation-layout [aria-label="cell"] rect').first().waitFor()
  })
  for (const width of [768, 390]) for (const route of ['/app/england/equity?view=f5_rural_penalty', '/app/ireland/correlations?view=d7_deprivation_urban_rural', '/app/netherlands/correlations?view=d7_deprivation_urban_rural', '/app/france/correlations?view=d7_deprivation_urban_rural']) await check(`${width}px ${route}`, async () => {
    await page.setViewportSize({ width, height: 900 }); await goto(route)
    await page.locator('main svg').last().waitFor()
    await page.screenshot({ path: `${output}/${width}-${route.split('/')[2]}.png`, fullPage: true })
  })
} finally { await browser.close(); writeFileSync(`${output}/results.json`, JSON.stringify(results, null, 2) + '\n') }
console.log(JSON.stringify({ passed: results.filter(row => row.result === 'PASS').length, failed: results.filter(row => row.result === 'FAIL') }))
process.exitCode = results.some(row => row.result === 'FAIL') ? 1 : 0
