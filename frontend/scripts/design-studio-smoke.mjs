import { chromium } from 'playwright'
import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const output = path.join(repo, 'implementation/evidence/studio-browser-oct11')
mkdirSync(output, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-gl=angle', '--use-angle=swiftshader'] })
const results = []
try {
  const context = await browser.newContext({ viewport: { width: 1024, height: 793 }, reducedMotion: 'reduce', acceptDownloads: true })
  const page = await context.newPage()
  let errors = []
  page.on('pageerror', error => errors.push(error.message))
  const check = async (name, run) => {
    errors = []
    try { await run(); assert.equal(errors.length, 0, errors.join('; ')); results.push({ name, result: 'PASS' }) }
    catch (error) { results.push({ name, result: 'FAIL', error: error.message }); await page.screenshot({ path: path.join(output, `failure-${results.length}.png`), fullPage: true }) }
  }
  const goto = async route => {
    await page.goto(`http://127.0.0.1:5173${route}`, { waitUntil: 'networkidle' })
    await page.getByRole('navigation', { name: 'Studio views' }).waitFor()
  }
  for (const width of [1024, 768, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 793 })
    for (const view of ['edit', 'upload', 'job', 'results', 'gains', 'export']) {
      await check(`${width}px ${view}`, async () => {
        await goto(`/app/england/studio?view=${view}`)
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'Horizontal overflow')
        await page.screenshot({ path: path.join(output, `${width}-${view}.png`), fullPage: true })
      })
    }
  }
  await page.setViewportSize({ width: 1024, height: 793 })
  await check('draft export retains filters and chosen frequency', async () => {
    await goto('/app/england/studio?region=E12000005&urban_rural=rural')
    await page.getByLabel('Factor', { exact: true }).fill('1.2')
    await page.getByLabel('Extra trips', { exact: true }).fill('2')
    await page.getByRole('button', { name: 'Add frequency uplift (needs r5py)', exact: true }).click()
    const pending = page.waitForEvent('download')
    await page.getByRole('button', { name: 'Download patch JSON', exact: true }).click()
    const file = await pending
    const patch = JSON.parse(readFileSync(await file.path(), 'utf8'))
    assert.equal(patch.country, 'england'); assert.equal(patch.region, 'E12000005'); assert.equal(patch.urban_rural, 'rural')
    assert.equal(patch.ops[0].factor, 1.2); assert.equal(patch.ops[0].extra_trips, 2)
    await page.getByRole('link', { name: 'Export', exact: true }).click()
    assert.equal(new URL(page.url()).searchParams.get('region'), 'E12000005')
    assert.equal(await page.getByRole('checkbox', { name: /Winners/ }).isDisabled(), true)
    await page.screenshot({ path: path.join(output, 'export-draft.png'), fullPage: true })
  })
  await check('country change isolates draft and historical run is disabled', async () => {
    await goto('/app/ireland/studio')
    assert.match(await page.getByTestId('studio-patch-list').innerText(), /Draft edits \(0\)/)
    await goto('/app/england/studio?region=E12000005&urban_rural=rural&pack=2025-01-01')
    await page.getByRole('button', { name: 'Add frequency uplift (needs r5py)', exact: true }).click()
    assert.equal(await page.getByRole('button', { name: 'Apply patch', exact: true }).isDisabled(), true)
  })
  await check('real CSV parsing requires review before changing the draft', async () => {
    await goto('/app/england/studio?view=upload')
    await page.getByLabel('Upload network patch').setInputFiles({ name: 'studio-validation-fixture.csv', mimeType: 'text/csv', buffer: Buffer.from('lat,lon\n52.48,-1.9\n') })
    await page.getByRole('button', { name: 'Add reviewed operations' }).waitFor()
    await page.screenshot({ path: path.join(output, 'upload-valid.png'), fullPage: true })
    await page.getByRole('button', { name: 'Add reviewed operations' }).click()
    assert.match(await page.getByTestId('studio-patch-list').innerText(), /52.4800, -1.9000/)
    await page.getByRole('link', { name: 'Upload', exact: true }).click()
    await page.getByLabel('Upload network patch').setInputFiles({ name: 'outside-country.csv', mimeType: 'text/csv', buffer: Buffer.from('lat,lon\n48.8,2.3\n') })
    await page.getByRole('alert').waitFor()
    assert.match(await page.getByRole('alert').innerText(), /outside England/)
    assert.equal(await page.getByRole('button', { name: 'Add reviewed operations' }).count(), 0)
    await page.screenshot({ path: path.join(output, 'upload-invalid.png'), fullPage: true })
  })
  for (const country of ['netherlands', 'france']) await check(`${country} draft is editable but unsupported calculations are disabled`, async () => {
    await goto(`/app/${country}/studio`)
    await page.getByRole('button', { name: 'Add frequency uplift (needs r5py)', exact: true }).click()
    assert.equal(await page.getByRole('button', { name: 'Apply patch', exact: true }).isDisabled(), true)
  })
} finally { await browser.close(); writeFileSync(path.join(output, 'results.json'), JSON.stringify(results, null, 2) + '\n') }
console.log(JSON.stringify({ passed: results.filter(result => result.result === 'PASS').length, failed: results.filter(result => result.result === 'FAIL') }))
process.exitCode = results.some(result => result.result === 'FAIL') ? 1 : 0
