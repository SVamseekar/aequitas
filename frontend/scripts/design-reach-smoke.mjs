import { chromium } from 'playwright'
import assert from 'node:assert/strict'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
const output = '../implementation/evidence/reach-browser-oct23'
mkdirSync(output, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const results = []
try {
  const page = await browser.newPage({ viewport: { width: 1024, height: 793 }, reducedMotion: 'reduce', acceptDownloads: true })
  let errors = []
  page.on('pageerror', error => errors.push(error.message))
  const check = async (name, run) => { errors = []; try { await run(); assert.deepEqual(errors, []); assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'Horizontal overflow'); results.push({ name, result: 'PASS' }) } catch (error) { results.push({ name, result: 'FAIL', error: error.message }); await page.screenshot({ path: `${output}/failure-${results.length}.png`, fullPage: true }) } }
  const goto = async route => { await page.goto(`http://127.0.0.1:5173${route}`, { waitUntil: 'networkidle' }); await page.getByRole('navigation', { name: 'Reach views', includeHidden: true }).waitFor({ state: 'attached' }) }
  await check('England authentic bands and CSV', async () => {
    await goto('/app/england/reach?view=bands'); assert.match(await page.locator('main').innerText(), /8,606,099/); assert.match(await page.locator('main').innerText(), /Mixed classification/)
    const pending = page.waitForEvent('download'); await page.getByRole('button', { name: 'Download regional data' }).click(); const csv = readFileSync(await (await pending).path(), 'utf8'); assert.match(csv, /North East/); assert.match(csv, /4.6/)
  })
  await check('Deprivation all cells and actual CSV', async () => {
    await goto('/app/england/reach?view=deprivation'); await page.getByRole('button', { name: 'All cells', exact: true }).click(); await page.getByRole('table').waitFor(); assert.ok(await page.getByRole('table').getByRole('row').count() >= 61)
    const pending = page.waitForEvent('download'); await page.getByRole('button', { name: 'Download detailed table' }).click(); const csv = readFileSync(await (await pending).path(), 'utf8'); assert.match(csv, /deprivation_decile/); assert.ok(csv.split('\n').length >= 61)
  })
  await check('Nine configurations, observed zero, URL and area scope', async () => {
    await goto('/app/england/reach?view=travel-time&region=E12000005&pack=2026-08-01'); const table = page.getByRole('table', { name: 'Destination availability' }); await table.getByRole('button', { name: 'Jobs · 45 minutes', exact: true }).getByText('42', { exact: true }).waitFor(); assert.equal(await table.getByRole('button').count(), 9)
    await table.getByRole('button', { name: 'School · 15 minutes', exact: true }).getByText('0', { exact: true }).waitFor(); await table.getByRole('button', { name: 'GP · 30 minutes', exact: true }).click(); await page.waitForURL(url => url.searchParams.get('dest') === 'gp' && url.searchParams.get('cutoff') === '30'); await page.waitForFunction(() => document.querySelector('select[aria-label="Travel time cutoff"]')?.value === '30'); assert.equal(await page.getByLabel('Travel time cutoff').inputValue(), '30')
    await page.getByLabel('Area', { exact: true }).selectOption('urban'); await page.waitForURL(/urban_rural=urban/); const url = new URL(page.url()); assert.equal(url.searchParams.get('dest'), 'gp'); assert.equal(url.searchParams.get('cutoff'), '30'); assert.equal(url.searchParams.get('pack'), '2026-08-01'); await page.getByRole('heading', { name: /Covered origins:/ }).waitFor(); assert.doesNotMatch(await page.getByRole('heading', { name: /Covered origins:/ }).innerText(), /3,574/)
  })
  await check('Export review and exact download scope', async () => {
    await goto('/app/england/reach?view=export&region=E12000005&pack=2026-08-01&dest=gp&cutoff=30'); await page.getByRole('link', { name: 'Download CSV', exact: true }).waitFor(); assert.match(await page.locator('main').innerText(), /Source vintages/)
    const pending = page.waitForEvent('download'); await page.getByRole('link', { name: 'Download CSV', exact: true }).click(); const csv = readFileSync(await (await pending).path(), 'utf8'); assert.match(csv, /West Midlands/); assert.match(csv, /gp/); assert.match(csv, /30/)
    const html = await page.request.get(new URL(await page.getByRole('link', { name: 'Download printable HTML' }).getAttribute('href'), page.url()).href); assert.equal(html.status(), 200); assert.match(await html.text(), /research/i)
  })
  for (const view of ['bands', 'travel-time', 'export']) await check(`Historical ${view} unavailable`, async () => { await goto(`/app/england/reach?view=${view}&pack=2026-09-25`); await page.getByRole('alert').waitFor(); assert.match(await page.getByRole('alert').innerText(), /current network/); assert.equal(await page.getByRole('link', { name: 'Download CSV', exact: true }).count(), 0) })
  for (const country of ['ireland', 'netherlands', 'france']) await check(`${country} no England fallback`, async () => { await goto(`/app/${country}/reach?view=travel-time`); await page.getByText('Unavailable', { exact: true }).first().waitFor(); assert.equal(await page.getByText('Unavailable', { exact: true }).count(), 9); assert.equal(await page.getByRole('heading', { name: /Covered origins:/ }).count(), 0) })
  await check('London rural empty', async () => { await goto('/app/england/reach?region=E12000007&urban_rural=rural'); assert.match(await page.locator('main').innerText(), /no rural LSOAs/) })
  for (const width of [768, 390]) for (const view of ['bands','deprivation','travel-time','export']) await check(`${width}px ${view}`, async () => { await page.setViewportSize({ width, height: 900 }); await goto(`/app/england/reach?view=${view}&region=E12000005`); await page.screenshot({ path: `${output}/${width}-${view}.png`, fullPage: true }) })
  await check('Mobile summary opens the complete shared table and navigation', async () => {
    await goto('/app/england/reach?view=bands')
    assert.equal(await page.locator('.app-navigation-disclosure').getAttribute('open'), null)
    await page.getByRole('navigation', { name: 'Mobile band views' }).getByRole('link', { name: 'Table', exact: true }).click()
    await page.getByRole('table', { name: 'All reach band and deprivation cells' }).waitFor()
    assert.equal(new URL(page.url()).searchParams.get('cells'), 'all')
    await page.getByRole('button', { name: 'More', exact: true }).click()
    await page.getByRole('navigation', { name: 'Application', exact: true }).getByRole('link', { name: 'Time', exact: true }).waitFor()
  })
} finally { await browser.close(); writeFileSync(`${output}/results.json`, JSON.stringify(results, null, 2) + '\n') }
console.log(JSON.stringify({ passed: results.filter(row => row.result === 'PASS').length, failed: results.filter(row => row.result === 'FAIL') }))
process.exitCode = results.some(row => row.result === 'FAIL') ? 1 : 0
