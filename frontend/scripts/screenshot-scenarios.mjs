// Screenshots the Policy Scenarios dashboard page across all 30 region x
// area-type filter combinations, with all "Read analysis" narratives
// expanded. Reuses the shared auth session from screenshot-all-filters.mjs.
//
// Usage: node scripts/screenshot-scenarios.mjs
import { chromium } from "playwright"
import { mkdirSync, existsSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const BASE_URL = process.env.BASE_URL ?? "http://localhost:5173"
const OUT_DIR = path.join(__dirname, "..", "screenshots", "scenarios")
const STORAGE_STATE = path.join(__dirname, ".auth-state.json")

const REGIONS = [
  "all",
  "E12000001",
  "E12000002",
  "E12000003",
  "E12000004",
  "E12000005",
  "E12000006",
  "E12000007",
  "E12000008",
  "E12000009",
]

const AREA_TYPES = ["all", "urban", "rural"]

const TEST_EMAIL = process.env.SCREENSHOT_EMAIL ?? "screenshot-bot@aequitas.test"
const TEST_PASSWORD = process.env.SCREENSHOT_PASSWORD ?? "Screenshot123!"

async function ensureLoggedIn(browser) {
  if (existsSync(STORAGE_STATE)) {
    return browser.newContext({ storageState: STORAGE_STATE })
  }

  const context = await browser.newContext()
  const page = await context.newPage()
  await page.goto(`${BASE_URL}/auth`)

  await page.getByPlaceholder("Email address").fill(TEST_EMAIL)
  await page.getByPlaceholder("Password").fill(TEST_PASSWORD)
  await page.getByRole("button", { name: "Sign In" }).click()

  await page.waitForURL(`${BASE_URL}/dashboard`, { timeout: 60 * 1000 })
  await context.storageState({ path: STORAGE_STATE })
  console.log(">>> Login successful, session saved for future runs.\n")
  return context
}

/** Click every "Read analysis" toggle on the page so narratives are visible. */
async function expandAllAnalyses(page) {
  const buttons = page.getByRole("button", { name: "Read analysis" })
  const count = await buttons.count()
  for (let i = 0; i < count; i++) {
    try {
      await buttons.nth(i).click({ timeout: 5000 })
    } catch {
      // button may have shifted out of reach after a prior toggle expanded
      // the layout — skip it rather than aborting the whole run
    }
  }
  if (count > 0) {
    await page.waitForTimeout(300)
  }
}

async function main() {
  mkdirSync(OUT_DIR, { recursive: true })

  const browser = await chromium.launch({ headless: true })
  const context = await ensureLoggedIn(browser)
  const page = await context.newPage()
  await page.setViewportSize({ width: 1440, height: 1024 })

  let count = 0
  const total = REGIONS.length * AREA_TYPES.length

  for (const region of REGIONS) {
    for (const area of AREA_TYPES) {
      count++
      const url = `${BASE_URL}/dashboard/scenarios?region=${region}&urban_rural=${area}`
      const fileName = `scenarios__${region}__${area}.png`
      const filePath = path.join(OUT_DIR, fileName)

      process.stdout.write(`[${count}/${total}] ${url} -> ${fileName} ... `)
      await page.goto(url, { waitUntil: "networkidle" })
      // allow charts and scenario builder data to render after load
      await page.waitForTimeout(800)
      await expandAllAnalyses(page)
      await page.screenshot({ path: filePath, fullPage: true })
      console.log("done")
    }
  }

  await browser.close()
  console.log(`\nAll ${total} screenshots saved to ${OUT_DIR}`)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
