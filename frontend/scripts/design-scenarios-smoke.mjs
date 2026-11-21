import { chromium } from 'playwright'
import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync } from 'node:fs'

const output = '../implementation/evidence/scenarios-browser-oct23'
mkdirSync(output, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const results = []
try {
  const page = await browser.newPage({ viewport: { width: 991, height: 793 }, reducedMotion: 'reduce' })
  let errors = []
  page.on('pageerror', error => errors.push(error.message))
  const check = async (name, run) => {
    errors = []
    try {
      await run()
      assert.deepEqual(errors, [])
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'Horizontal overflow')
      results.push({ name, result: 'PASS' })
    } catch (error) {
      results.push({ name, result: 'FAIL', error: error.message })
      await page.screenshot({ path: `${output}/failure-${results.length}.png`, fullPage: true })
    }
  }
  const goto = async (query, country = 'england') => {
    await page.goto(`http://127.0.0.1:5173/app/${country}/scenarios?${query}`, { waitUntil: 'domcontentloaded' })
    await page.getByRole('navigation', { name: 'Evidence views' }).waitFor()
  }
  await check('Four stored comparison rows, authentic values and missing combined outputs', async () => {
    await goto('view=ps5_scenario_comparison')
    const payload = await (await page.request.get('http://127.0.0.1:5173/api/sections?dimension=scenarios&country=england')).json()
    const rows = payload.sections.find(section => section.section_id === 'ps5_scenario_comparison').stats.scenarios
    const table = page.getByRole('table', { name: 'Stored scenario comparison' })
    assert.equal(await table.locator('tbody tr').count(), rows.length)
    for (const row of rows) {
      const actual = table.getByRole('row').filter({ hasText: row.name })
      assert.equal(await actual.count(), 1)
      const cells = await actual.locator('td').allTextContents()
      assert.deepEqual(cells, [row.population, row.cost_m, row.co2_t].map(value => value === null ? '—' : value.toLocaleString('en-GB', { maximumFractionDigits: 1 })))
    }
    for (const [metric, count] of [['population', 4], ['cost', 3], ['co2', 3]]) {
      const plot = page.getByRole('img', { name: `Scenario ${metric} comparison` })
      await plot.locator('svg').waitFor()
      assert.equal(await plot.locator('[aria-label="bar"] rect').count(), count)
    }
    assert.doesNotMatch(await page.locator('main').innerText(), /My Custom Scenario|highest value for money|recommended priority/)
  })
  await check('Sandbox settings update shareable URL and retain scope without fabricated outputs', async () => {
    await goto('view=custom&region=E12000005&pack=current&freq_pct=25&last_bus=21&drt_cov=50&franchise=partial')
    assert.equal(await page.getByRole('slider', { name: 'Frequency uplift' }).inputValue(), '25')
    assert.equal(await page.getByRole('slider', { name: 'Last bus time' }).inputValue(), '21')
    await page.getByRole('slider', { name: 'Frequency uplift' }).fill('35')
    await page.waitForURL(/freq_pct=35/)
    assert.equal(new URL(page.url()).searchParams.get('region'), 'E12000005')
    assert.equal(new URL(page.url()).searchParams.get('pack'), 'current')
    assert.deepEqual(await page.locator('.scenario-output-cards strong').allTextContents(), ['—', '—', '—'])
    const target = await page.getByRole('link', { name: 'Open network Studio' }).getAttribute('href')
    assert.match(target, /region=E12000005/)
    assert.match(target, /pack=current/)
    assert.doesNotMatch(target, /view=custom/)
    await page.reload({ waitUntil: 'domcontentloaded' })
    await page.getByRole('slider', { name: 'Frequency uplift' }).waitFor()
    assert.equal(await page.getByRole('slider', { name: 'Frequency uplift' }).inputValue(), '35')
  })
  await check('Urban scope disables rural DRT controls', async () => {
    await goto('view=custom&urban_rural=urban')
    assert.equal(await page.getByRole('slider', { name: 'Rural DRT coverage' }).isDisabled(), true)
  })
  await check('Stored scenario population series uses real warehouse series format', async () => {
    await goto('view=ps1_freq_restoration')
    await page.locator('.scenario-population svg').last().waitFor()
    assert.doesNotMatch(await page.locator('main').innerText(), /Chart could not be rendered/)
    assert.match(await page.locator('.scenario-population').innerText(), /Remaining population/)
  })
  for (const country of ['england', 'ireland', 'netherlands', 'france']) {
    const payload = await (await page.request.get(`http://127.0.0.1:5173/api/sections?dimension=scenarios&country=${country}`)).json()
    for (const section of payload.sections.filter(section => section.stats.scenario)) await check(`${country} ${section.section_id} retains actual target population and missing estimates`, async () => {
      await goto(`view=${section.section_id}`, country)
      await page.locator('.scenario-headline-values').waitFor()
      const values = await page.locator('.scenario-headline-values strong').allTextContents()
      const expected = section.stats.scenario
      assert.equal(values[0], expected.population_affected.toLocaleString('en-GB', { maximumFractionDigits: 1 }))
      if (expected.estimated_annual_cost_m == null) assert.equal(values[1], '—')
      if (expected.co2_saving_t_yr == null) assert.equal(values[2], '—')
      assert.match(await page.locator('main').innerText(), /does not represent newly gained stop access/)
      assert.doesNotMatch(await page.locator('main').innerText(), /highest BCR|positive net economic value|recommended priority/)
      assert.match(await page.getByRole('link', { name: 'Open in network Studio' }).getAttribute('href'), new RegExp(`/app/${country}/studio`))
    })
    if (country !== 'england') await check(`${country} comparison retains four stored country rows and unmodelled cost/carbon`, async () => {
      await goto('view=ps5_scenario_comparison', country)
      const table = page.getByRole('table', { name: 'Stored scenario comparison' })
      const source = payload.sections.find(section => section.section_id === 'ps5_scenario_comparison').stats.rows
      assert.equal(await table.locator('tbody tr').count(), source.length)
      for (const row of source) {
        const actual = table.getByRole('row').filter({ hasText: row.title })
        assert.deepEqual(await actual.locator('td').allTextContents(), [row.people.toLocaleString('en-GB', { maximumFractionDigits: 1 }), '—', '—'])
      }
    })
  }
  for (const width of [768, 390]) for (const view of ['ps1_freq_restoration', 'ps3_drt_rural', 'ps5_scenario_comparison', 'custom']) {
    await check(`${width}px ${view}`, async () => {
      await page.setViewportSize({ width, height: 900 })
      await goto(`view=${view}`)
      if (view === 'custom') await page.getByRole('slider', { name: 'Frequency uplift' }).waitFor()
      else if (view === 'ps5_scenario_comparison') await page.getByRole('img', { name: 'Scenario population comparison' }).locator('svg').waitFor()
      else await page.locator('.scenario-headline-values').waitFor()
      await page.screenshot({ path: `${output}/${width}-${view}.png`, fullPage: true })
    })
  }
} finally {
  await browser.close()
  writeFileSync(`${output}/results.json`, JSON.stringify(results, null, 2) + '\n')
}
console.log(JSON.stringify({ passed: results.filter(row => row.result === 'PASS').length, failed: results.filter(row => row.result === 'FAIL') }))
process.exitCode = results.some(row => row.result === 'FAIL') ? 1 : 0
