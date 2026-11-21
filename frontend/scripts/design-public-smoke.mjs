import { chromium } from 'playwright'
import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync } from 'node:fs'
const output = '../implementation/evidence/public-browser-oct23'
mkdirSync(output, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const results = []
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' })
  let errors = []
  page.on('pageerror', error => errors.push(error.message))
  const check = async (name, run) => { errors = []; try { await run(); assert.deepEqual(errors, []); assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'Horizontal overflow'); results.push({ name, result: 'PASS' }) } catch (error) { results.push({ name, result: 'FAIL', error: error.message }); await page.screenshot({ path: `${output}/failure-${results.length}.png`, fullPage: true }) } }
  const goto = async route => {
    await page.goto(`http://127.0.0.1:5173${route}`, { waitUntil: 'domcontentloaded' })
    await page.locator('main h1').waitFor()
    await page.waitForFunction(() => !document.querySelector('main [role=status]'))
  }
  for (const country of ['england','ireland','netherlands','france']) await check(`${country} country evidence and selected-topic context`, async () => {
    await goto(`/briefings/${country}`)
    await page.locator('.public-coverage-card strong').waitFor()
    const score = await (await page.request.get(`http://127.0.0.1:5173/api/score?country=${country}&mode=bus`)).json()
    const coverage = score.components.find(item => item.id === 'pop_within_400m')?.value
    assert.equal(await page.locator('.public-coverage-card strong').innerText(), coverage == null ? '—' : `${(coverage*100).toFixed(1)}%`)
    const equity = page.getByRole('link', { name: 'Equity & deprivation', exact: true }); assert.match(await equity.getAttribute('href'), new RegExp(`country=${country}`))
    await page.screenshot({ path: `${output}/${country}.png`, fullPage: true })
    await equity.click(); await page.waitForURL(/\/briefings\/equity/); await page.locator('.public-topic-primary strong').waitFor()
    assert.equal(new URL(page.url()).searchParams.get('country'), country)
    assert.match(await page.getByRole('link', { name: 'Open selected evidence', exact: true }).getAttribute('href'), new RegExp(`/app/${country}/equity`))
  })
  await check('Topic country switching has distinct API values and selected exhibits', async () => {
    await goto('/briefings/equity?country=england'); await page.locator('.public-topic-primary strong').waitFor(); const before = await page.locator('.public-topic-primary strong').innerText()
    await page.getByRole('navigation', { name: 'Country evidence' }).getByRole('link', { name: 'Ireland', exact: true }).click(); await page.waitForURL(/country=ireland/); await page.waitForFunction(value => document.querySelector('.public-topic-primary strong')?.textContent !== value, before)
    assert.equal(await page.getByRole('navigation', { name: 'Country evidence' }).getByRole('link', { name: 'Ireland', exact: true }).getAttribute('aria-current'), 'page')
    await page.locator('.public-topic-exhibits a').nth(1).click(); await page.waitForURL(/exhibit=/); assert.equal(new URL(page.url()).searchParams.get('country'), 'ireland')
  })
  for (const topic of ['access','service','network','correlations','economy','policy','scenarios','time','reach','ops','destinations','appraisal','realtime','chat']) await check(`topic ${topic}`, async () => { await goto(`/briefings/${topic}?country=france`); assert.equal(await page.locator('h1').count(), 1); assert.ok(await page.getByRole('link', { name: 'Open selected evidence', exact: true }).count()); assert.doesNotMatch(await page.locator('main').innerText(), /failed to render|Something went wrong rendering/) })
  for (const route of ['privacy','terms','refunds','disclaimer']) await check(`${route} anchors preserve reading content`, async () => {
    await goto(`/${route}`); const nav = page.getByRole('navigation', { name: 'On this page' }); const links = await nav.getByRole('link').all(); assert.ok(links.length >= 4)
    for (const link of links) assert.equal(await page.locator(await link.getAttribute('href')).count(), 1)
    await links[links.length-1].click(); assert.ok(new URL(page.url()).hash); assert.ok((await page.locator('.public-document-content').innerText()).length > 500)
  })
  await check('Contact client errors and success against an intercepted local fixture only', async () => {
    await goto('/contact'); let body
    await page.route('**/api/contact', async route => { body = route.request().postDataJSON(); await route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: 'Fixture delivery unavailable' }) }) })
    await page.getByLabel('Name', { exact: true }).fill('Local browser fixture'); await page.getByLabel('Email', { exact: true }).fill('fixture@example.invalid'); await page.getByLabel('Country or region', { exact: true }).fill('Ireland'); await page.getByLabel('I am interested in').selectOption('Research or teaching'); await page.getByLabel('Project', { exact: true }).fill('Local intercepted verification, no external delivery.')
    await page.getByRole('button', { name: 'Send enquiry', exact: true }).click(); await page.getByRole('alert').waitFor(); assert.match(await page.getByRole('alert').innerText(), /Fixture/); assert.match(body.message, /Ireland/); assert.match(body.message, /Research or teaching/)
    await page.unroute('**/api/contact'); await page.route('**/api/contact', route => route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })); await page.getByRole('button', { name: 'Send enquiry', exact: true }).click(); await page.getByText(/Received. We will write/).waitFor()
    await page.unroute('**/api/contact')
  })
  for (const width of [768,390]) for (const route of ['/contact','/privacy','/briefings/england','/briefings/equity?country=netherlands']) await check(`${width}px ${route}`, async () => { await page.setViewportSize({ width, height: 900 }); await goto(route); await page.screenshot({ path: `${output}/${width}-${route.split('?')[0].replaceAll('/','-')}.png`, fullPage: true }) })
} finally { await browser.close(); writeFileSync(`${output}/results.json`, JSON.stringify(results,null,2)+'\n') }
console.log(JSON.stringify({ passed: results.filter(row => row.result==='PASS').length, failed: results.filter(row => row.result==='FAIL') }))
process.exitCode=results.some(row=>row.result==='FAIL')?1:0
