import { readFileSync, existsSync, mkdirSync, writeFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const root = path.join(repo, 'docs/design-concepts/2026-10-09')
const catalog = JSON.parse(readFileSync(path.join(root, 'metadata/catalog.json')))
const manifest = JSON.parse(readFileSync(path.join(repo, 'design/screen-status.json')))
const errors = []
for (const board of catalog.boards) {
  const file = path.join(root, board.file)
  if (!existsSync(file)) { errors.push(`Missing ${board.id}: ${file}`); continue }
  const hash = createHash('sha256').update(readFileSync(file)).digest('hex')
  if (board.sha256 && hash !== board.sha256) errors.push(`Original modified: ${board.id}`)
}
if (manifest.screens.length !== 79) errors.push(`Expected 79 detailed views, found ${manifest.screens.length}`)
if (new Set(manifest.screens.map(s => s.id)).size !== manifest.screens.length) errors.push('Duplicate screen IDs')
for (const screen of [...manifest.screens, ...manifest.supplemental]) {
  if (!catalog.boards.some(b => b.id === screen.boardId)) errors.push(`Unknown board for ${screen.id}`)
  if (!existsSync(path.join(repo, screen.component))) errors.push(`Missing component: ${screen.component}`)
  if (screen.status === 'VERIFIED' && ['visual', 'functional', 'regression', 'responsive'].some(k => !['PASS', 'NOT_APPLICABLE'].includes(screen[k]))) errors.push(`Unsubstantiated VERIFIED: ${screen.id}`)
  for (const evidence of screen.evidence ?? []) if (!existsSync(path.join(repo, evidence))) errors.push(`Missing evidence ${evidence}`)
}
const result = { boards: catalog.boards.length, detailedBoards: new Set(manifest.screens.map(s => s.boardId)).size, screens: manifest.screens.length, supplemental: manifest.supplemental.length, errors }
mkdirSync(path.join(repo, 'implementation/evidence'), { recursive: true })
writeFileSync(path.join(repo, 'implementation/evidence/harness-validation.json'), JSON.stringify(result, null, 2) + '\n')
console.log(JSON.stringify(result, null, 2))
process.exitCode = errors.length ? 1 : 0
