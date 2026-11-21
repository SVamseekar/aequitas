import { chromium } from 'playwright'
import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const output = path.join(repo, 'implementation/evidence/compare-browser-oct11')
mkdirSync(output, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const results = []
try {
  const page = await browser.newPage({ viewport: { width: 991, height: 793 }, reducedMotion: 'reduce', acceptDownloads: true })
  let errors = []
  page.on('pageerror', error => errors.push(error.message))
  const check = async (name, run) => {
    errors = []
    try { await run(); assert.equal(errors.length, 0, errors.join('; ')); assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'Horizontal overflow'); results.push({ name, result: 'PASS' }) }
    catch (error) { results.push({ name, result: 'FAIL', error: error.message }); await page.screenshot({ path: path.join(output, `failure-${results.length}.png`), fullPage: true }) }
  }
  const goto = async url => { await page.goto(`http://127.0.0.1:5173${url}`, { waitUntil: 'networkidle' }); await page.getByRole('navigation', { name: 'Comparison views' }).waitFor() }
  for (const country of ['england', 'ireland', 'netherlands', 'france']) {
    await check(`${country} authentic summary and selected geometry`, async () => {
      await goto(`/app/${country}/compare`)
      await page.getByRole('table').waitFor()
      assert.equal(await page.getByRole('row').count(), 6)
      const map = page.locator('.compare-region-map')
      await map.waitFor()
      assert.ok(await map.locator('path[fill="#c6582b"]').count(), 'Region A was not matched to its geometry')
      assert.ok(await map.locator('path[fill="#759765"]').count(), 'Region B was not matched to its geometry')
      await page.screenshot({ path: path.join(output, `${country}-summary.png`), fullPage: true })
    })
  }
  await check('global filters preserve A/B/date/view and CSV exports actual measures', async () => {
    await goto('/app/england/compare?a=E12000005&b=E12000004&pack=2026-08-01&view=coverage')
    await page.getByRole('table').waitFor()
    await page.getByLabel('Area', { exact: true }).selectOption('urban')
    const url = new URL(page.url())
    assert.equal(url.searchParams.get('a'), 'E12000005'); assert.equal(url.searchParams.get('b'), 'E12000004')
    assert.equal(url.searchParams.get('pack'), '2026-08-01'); assert.equal(url.searchParams.get('view'), 'coverage')
    await page.getByRole('button', { name: 'Export comparison CSV' }).waitFor()
    await page.waitForFunction(() => !document.querySelector('.compare-heading button:last-child')?.disabled)
    const pending = page.waitForEvent('download')
    await page.getByRole('button', { name: 'Export comparison CSV' }).click()
    const downloaded = await pending
    const csv = readFileSync(await downloaded.path(), 'utf8')
    assert.match(csv, /"england","2026-08-01","urban"/)
    assert.match(csv, /"West Midlands","East Midlands"/)
    assert.equal(csv.split('\n').length, 2)
  })
  await check('same-region and London rural retain selectors without showing metrics', async () => {
    await goto('/app/england/compare?a=E12000007&b=E12000007')
    assert.match(await page.locator('main').innerText(), /Choose two different regions/)
    assert.equal(await page.getByRole('table').count(), 0)
    await page.screenshot({ path: path.join(output, 'same-region.png'), fullPage: true })
    await page.getByLabel('Region A', { exact: true }).selectOption('E12000002')
    await page.waitForURL(/a=E12000002/)
    await page.getByLabel('Area type', { exact: true }).selectOption('rural')
    await page.getByText('London has no rural LSOAs — this combination is empty. Choose an urban or all-area scope.', { exact: true }).waitFor()
    assert.match(await page.locator('main').innerText(), /no rural LSOAs/)
  })
  await check('Dutch mode retains comparison context and active evidence tab', async () => {
    await goto('/app/netherlands/compare?a=groningen&b=noord-holland&view=coverage')
    await page.getByLabel('Mode', { exact: true }).selectOption('all')
    await page.waitForURL(/mode=all/)
    const url = new URL(page.url())
    assert.equal(url.searchParams.get('a'), 'groningen'); assert.equal(url.searchParams.get('b'), 'noord-holland')
    assert.equal(url.searchParams.get('view'), 'coverage'); assert.equal(url.searchParams.get('mode'), 'all')
  })
  for (const width of [768, 390]) for (const view of ['summary', 'coverage', 'service', 'evening', 'jobs']) await check(`${width}px ${view}`, async () => {
    await page.setViewportSize({ width, height: 900 })
    await goto(`/app/england/compare?view=${view}`)
    await page.getByRole('table').waitFor()
    await page.screenshot({ path: path.join(output, `${width}-${view}.png`), fullPage: true })
  })
} finally { writeFileSync(path.join(output, 'results.json'), JSON.stringify(results, null, 2) + '\n'); console.log(JSON.stringify({phase:'assertions-complete',passed:results.filter(row=>row.result==='PASS').length,failed:results.filter(row=>row.result==='FAIL')})); await browser.close() }
console.log(JSON.stringify({ passed: results.filter(result => result.result === 'PASS').length, failed: results.filter(result => result.result === 'FAIL') }))
process.exitCode = results.some(result => result.result === 'FAIL') ? 1 : 0
