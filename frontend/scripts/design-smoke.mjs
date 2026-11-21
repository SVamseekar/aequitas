import { chromium } from 'playwright'
import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const output = path.resolve(repo,process.env.DESIGN_EVIDENCE_DIR??'implementation/evidence/browser-regression')
mkdirSync(output, { recursive: true })
const base = process.env.BASE_URL ?? 'http://127.0.0.1:5173'
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const results = []
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' })
  const page = await context.newPage()
  let errors = []
  page.on('pageerror', e => errors.push(e.message))
  const check = async (name, run) => {
    errors = []
    try { await run(); assert.equal(errors.length, 0, errors.join('; ')); results.push({ name, result: 'PASS' }) }
    catch (e) { results.push({ name, result: 'FAIL', error: e.message, labels: await page.getByRole('combobox').evaluateAll(nodes => nodes.map(n => ({ name: n.getAttribute('aria-label'), label: n.labels?.[0]?.textContent, value: n.value }))) }); await page.screenshot({ path: path.join(output, 'failure.png') }) }
  }
  for (const country of process.argv.includes('--filters-only') ? [] : ['england', 'ireland', 'netherlands', 'france']) {
    for (const slug of ['equity', 'access', 'service', 'network', 'correlations', 'economy', 'policy', 'scenarios', 'compare', 'reach', 'time', 'ops', 'studio']) {
      await check(`${country}/${slug}`, async () => {
        await page.goto(`${base}/app/${country}/${slug}`, { waitUntil: 'networkidle' })
        await page.getByRole('navigation', { name: 'Application', exact: true }).waitFor({ timeout: 10000 })
        assert.ok(await page.locator('main h1').count(), 'Missing page heading')
        const text = await page.locator('main').innerText()
        assert.ok(!/failed to render|Something went wrong rendering/.test(text), 'Render boundary caught an error')
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'Horizontal page overflow')
      })
    }
  }
  if (!process.argv.includes('--filters-only')) for (const route of ['/', '/briefings', '/briefings/england', '/briefings/equity', '/methodology', '/about', '/contact', '/privacy', '/terms', '/refunds', '/disclaimer', '/accessibility', '/auth', '/invite/design-preview-invalid']) {
    await check(`public ${route}`, async () => {
      await page.goto(base + route, { waitUntil: 'networkidle' })
      await page.locator('#root .landing-root, #root .app-redesign').first().waitFor({ timeout: 10000 })
      assert.ok(await page.locator('h1').count(), 'Missing page heading')
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'Horizontal page overflow')
    })
  }
  await check('evidence view and global-filter persistence', async () => {
    await page.goto(`${base}/app/england/equity?view=f2_disparity_ratio&pack=2026-08-01`, { waitUntil: 'networkidle' })
    await page.getByLabel('Area', { exact: true }).selectOption('urban')
    assert.equal(new URL(page.url()).searchParams.get('view'), 'f2_disparity_ratio')
    assert.equal(new URL(page.url()).searchParams.get('pack'), '2026-08-01')
    await page.getByRole('link', { name: 'Social access', exact: true }).click()
    assert.equal(new URL(page.url()).searchParams.get('view'), 'f3_ethnic_access')
    await page.getByRole('link', { name: 'Compare', exact: true }).click()
    assert.equal(new URL(page.url()).searchParams.get('urban_rural'), 'urban')
    assert.equal(new URL(page.url()).searchParams.get('pack'), '2026-08-01')
  })
  await check('Time metric deep link and control', async () => {
    await page.goto(`${base}/app/england/time?metric=pct_400m`, { waitUntil: 'networkidle' })
    assert.equal(await page.getByRole('button', { name: 'Area coverage', exact: true }).getAttribute('aria-pressed'), 'true')
    await page.getByRole('button', { name: 'Evening isolated %', exact: true }).click()
    assert.equal(new URL(page.url()).searchParams.get('metric'), 'evening_isolated_pct')
  })
  await check('Protected workspace routes retain session boundary', async () => {
    for (const route of ['/profile', '/saved', '/notes', '/regions']) {
      await page.goto(base + route, { waitUntil: 'networkidle' })
      assert.equal(new URL(page.url()).pathname, '/', 'Unauthenticated personal route exposed')
    }
  })
  await check('Impossible London rural filter', async () => {
    await page.goto(`${base}/app/england/equity?region=E12000007&urban_rural=rural`, { waitUntil: 'networkidle' })
    assert.match(await page.locator('main').innerText(), /no rural LSOAs/)
  })
  await check('Unknown dated network stays unavailable', async () => {
    await page.goto(`${base}/app/england/time?pack=2099-01-01`, { waitUntil: 'networkidle' })
    assert.match(await page.locator('main').innerText(), /Unknown pack/)
  })
  for (const viewport of [{ width: 390, height: 844 }, { width: 768, height: 1024 }]) {
    await page.setViewportSize(viewport)
    for (const slug of ['equity', 'access', 'compare', 'time', 'reach']) {
      await check(`${viewport.width}px ${slug}`, async () => {
        await page.goto(`${base}/app/england/${slug}`, { waitUntil: 'networkidle' })
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'Horizontal page overflow')
        await page.screenshot({ path: path.join(output, `${viewport.width}-${slug}.png`), fullPage: true })
      })
    }
    if (!process.argv.includes('--filters-only')) for (const route of ['/', '/briefings', '/auth']) {
      await check(`${viewport.width}px public ${route}`, async () => {
        await page.goto(base + route, { waitUntil: 'networkidle' })
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'Horizontal page overflow')
        await page.screenshot({ path: path.join(output, `${viewport.width}-public-${route === '/' ? 'landing' : route.slice(1)}.png`), fullPage: true })
      })
    }
  }
} catch(error){
  results.push({name:'Browser run',result:'FAIL',error:error.message})
} finally {
  writeFileSync(path.join(output,'results.json'),JSON.stringify(results,null,2)+'\n')
  console.log(JSON.stringify({passed:results.filter(r=>r.result==='PASS').length,failed:results.filter(r=>r.result==='FAIL')},null,2))
  await Promise.race([browser.close(),new Promise(resolve=>setTimeout(resolve,10000))])
}
process.exit(results.some(r=>r.result==='FAIL')?1:0)
