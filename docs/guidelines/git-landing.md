# Git landing plan (England, Ireland, packs, Netherlands)

This is the only instruction set for turning the current uncommitted tree
into GitHub PRs. Follow it exactly.

**Counts (fixed):** **4 pull requests**, **12 commits**, stacked on
`origin/main` (`44febd9`). No fifth PR. No docs-only PR. No extra
“cleanup” PR.

**Voice:** public-repo engineering. Imperative Conventional Commits.
Do **not** use programme slang in branch names, subjects, or PR titles
(`Wave`, `stamp`, `PNG pass`, `trap #`, `agent`, `leftover`).

**Do not merge.** Open the four PRs, then **babysit** them (CI, conflicts,
review comments, leaked binaries). If anything is not healthy, write
`docs/guidelines/git-landing-status.md` (do **not** commit that file)
and keep fixing until the stack is green or you are blocked.

---

## 1. Starting state

| Item | Value |
|------|--------|
| Repo | `/Users/souravamseekarmarti/Projects/aequitas` |
| Remote | `origin` → `https://github.com/SVamseekar/aequitas.git` |
| Base | `main` @ `44febd9` (tracks `origin/main`) |
| Headline on main | `feat(frontend): oatmeal & ink redesign with glass UI` |

If `HEAD` is not `44febd9`, stop and tell the user. Do not rebase onto a
different main.

---

## 2. Never stage (hard fail)

If any of these appear in `git diff --cached --name-only`, unstage and
add a `.gitignore` line in the same PR that would have committed them.

```
*.duckdb
*.duckdb.wal
*.bak
*.tmp
data/aequitas_ireland.duckdb.bak-pre-a4
data/aequitas_netherlands.duckdb.tmp
data/aequitas_netherlands.next.duckdb.tmp
data/aequitas_netherlands.next.duckdb.tmp.wal
data/ireland/                 # FAISS binaries and local index
data/ireland_qa_census.json   # local QA dump
data/chat_rate_limit.sqlite
data/refresh_state.json
node_modules/
qa-visual/
frontend/scripts/qa-*.mjs
scripts/rebuild_nl_briefing.py
scripts/rebuild_nl_warehouse_only.py
.env
.env.*
AGENTS.md
docs/superpowers/
.claude/
.cursor/
.playwright-mcp/
.serena/
repomix.config.json
```

**Allowed data only:**

- `data/packs/manifest.json`
- `data/packs/**/metrics.json` (not `warehouse.duckdb` inside a pack)
- `frontend/public/boundaries/*.geojson`

---

## 3. Docs rule

There is **no** docs PR and **no** commit whose subject starts with `docs:`.

Tracked product notes go **in the same commit as the code they describe**:

| File | Rides with |
|------|------------|
| `docs/CURRENT_STATE.md` (England / score / map / Studio / Reach paragraphs) | Commit 1.3 or 1.4 |
| `docs/guidelines/domain-rules.md` | Commit 1.1 |
| `docs/guidelines/decisions.md` | Commit 1.1 |
| `docs/guidelines/testing.md` | Commit 1.4 |
| `docs/guidelines/gotchas.md` (shared + England) | Commit 1.1 |
| `docs/guidelines/git-branching.md` | Commit 1.1 |
| `docs/guidelines/git-landing.md` (this file) | Commit 1.1 |
| `docs/guidelines/AI_BEST_PRACTICES.md` | Commit 1.1 |
| Ireland sections of `CURRENT_STATE.md` + `country-sections.md` (Ireland catalogue + mistakes 1–14) | Commit 2.3 |
| Packs / `/time` paragraphs in `CURRENT_STATE.md` | Commit 3.2 |
| Netherlands paragraphs in `CURRENT_STATE.md` + NL traps in `country-sections.md` | Commit 4.3 |

Use `git add -p` on `CURRENT_STATE.md` and `country-sections.md` so Ireland
sentences are not in PR 1.

Leave `AGENTS.md` unstaged.

---

## 4. Stack

Create branches in order. Each branch’s parent is the previous feature
branch, not a second copy of `main`.

```
origin/main (44febd9)
  └── feat/england-score-map-studio-reach     (PR 1, 4 commits)
        └── feat/ireland-tfi-hp-cso           (PR 2, 3 commits)
              └── feat/network-packs-and-time (PR 3, 2 commits)
                    └── feat/netherlands-ovapi (PR 4, 3 commits)
```

Graphite (`gt`) if installed; otherwise:

```bash
git fetch origin
git checkout -b feat/england-score-map-studio-reach origin/main
# … commits 1.1–1.4, push, gh pr create --base main

git checkout -b feat/ireland-tfi-hp-cso
# … commits 2.1–2.3, push, gh pr create --base feat/england-score-map-studio-reach

git checkout -b feat/network-packs-and-time
# … commits 3.1–3.2, push, gh pr create --base feat/ireland-tfi-hp-cso

git checkout -b feat/netherlands-ovapi
# … commits 4.1–4.3, push, gh pr create --base feat/network-packs-and-time
```

Never `git add .`  
Never `git commit --amend` after push unless the PR is still draft and
you are fixing a leaked binary.  
Never force-push `main`.

---

## 5. Shared files (`git add -p`)

These files span countries. Split hunks by the **first** country that
needs them; later PRs only get later hunks.

| Path | PR 1 | PR 2 | PR 3 | PR 4 |
|------|------|------|------|------|
| `frontend/src/App.tsx` | `/app/:country`, Studio, Reach routes | Ireland routes if any remain | `TimePage` route | NL mode query if any |
| `frontend/src/lib/constants.ts` | `COUNTRIES`, England dimensions | `IRELAND_*` | pack labels if any | `NETHERLANDS_*` |
| `frontend/src/lib/appRoutes.ts` | create file: country + England slugs | Ireland query stripping | `pack` / `as_of` | NL `mode` |
| `frontend/src/components/charts/ChoroplethMap.tsx` | England / SVG-first | `ireland_county` | — | NL provincies + `mode` |
| `frontend/src/components/layout/FilterDropdowns.tsx` | country + England regions | Ireland counties | pack dropdown | NL provincies + bus/all |
| `frontend/src/components/layout/MetricsTicker.tsx` | live ticker | Ireland nouns | unknown-pack chips | NL + `mode` |
| `frontend/src/components/layout/Header.tsx` | app chrome | country switch | pack control | mode control |
| `frontend/src/api/hooks.ts` | score/map/studio/reach | `country=ireland` | `useTimeSeries`, pack | `mode` |
| `frontend/src/api/types.ts` | score/reach/studio | Ireland types | time series | mode |
| `src/aequitas/api/app.py` | new routers: score, map, reach, studio | Ireland warehouse wiring | time router | NL warehouse + mode |
| `src/aequitas/api/services/warehouse.py` | country path England | Ireland duckdb | pack resolve | NL duckdb |
| `src/aequitas/api/routers/chat.py` | England chat | `country=ireland` | — | NL honest empty |
| `src/aequitas/pipeline/cli.py` | `reach`, `studio`, score CLI | `ireland` | `refresh` | `netherlands` |
| `.gitignore` | duckdb/tmp/qa ignores | — | packs exceptions if needed | NL tmp names |
| `README.md` | England local run | Ireland CLI | refresh / time | NL CLI + mode |

If a hunk cannot be split cleanly, put the **whole file on the earliest
PR that would not compile without it**, then later PRs show the extra
lines only.

---

## 6. The 12 commits

Subjects are **fixed**. Do not rename. Bodies may add a short why.

### PR 1 — `feat/england-score-map-studio-reach`

**Title:** `feat: in-country score, map home, Studio, and Reach (England)`

**Commit 1.1** `feat(analytics): add in-country score, service bands, and reach writers`

Stage:

- `src/aequitas/analytics/score.py`
- `src/aequitas/analytics/bands.py`
- `src/aequitas/analytics/reach.py`
- `src/aequitas/analytics/studio.py`
- `src/aequitas/analytics/centroids.py`
- `src/aequitas/analytics/writers.py`
- `src/aequitas/ingestion/download.py`
- `src/aequitas/processing/service_quality.py`
- `src/aequitas/validation/gates.py`
- `src/aequitas/validation/sanity.py`
- `src/aequitas/warehouse/builder.py`
- `src/aequitas/warehouse/precompute.py`
- `src/aequitas/warehouse/schema.py`
- `src/aequitas/warehouse/stats_builders/market_concentration.py`
- `src/aequitas/intelligence/templates/reach_access.j2`
- `src/aequitas/intelligence/templates/reach_bands.j2`
- `src/aequitas/intelligence/templates/score_home.j2`
- `src/aequitas/intelligence/templates/studio_delta.j2`
- `src/aequitas/core/config.py`
- `docs/guidelines/domain-rules.md`
- `docs/guidelines/decisions.md`
- `docs/guidelines/gotchas.md`
- `docs/guidelines/git-branching.md`
- `docs/guidelines/git-landing.md`
- `docs/guidelines/AI_BEST_PRACTICES.md`
- `.gitignore` (only ignore-rule hunks)

**Commit 1.2** `feat(api): expose score, map, reach, and studio endpoints`

Stage:

- `src/aequitas/api/routers/score.py`
- `src/aequitas/api/routers/map_data.py`
- `src/aequitas/api/routers/reach.py`
- `src/aequitas/api/routers/studio.py`
- `src/aequitas/api/services/score.py`
- `src/aequitas/api/services/reach_query.py`
- `src/aequitas/api/services/export_pack.py` (England research pack)
- `src/aequitas/api/models/responses.py`
- `src/aequitas/api/config.py`
- `src/aequitas/api/deps.py`
- `src/aequitas/api/app.py` (hunks for those routers)
- `src/aequitas/api/routers/export.py`
- `src/aequitas/api/routers/overview.py`
- `src/aequitas/api/routers/sections.py`
- `src/aequitas/api/routers/metrics.py`
- `src/aequitas/api/services/warehouse.py` (England path)
- `src/aequitas/pipeline/_stages.py`
- `src/aequitas/pipeline/cli.py` (England commands)

**Commit 1.3** `feat(frontend): add country app shell, map home, Studio, and Reach`

Stage:

- `frontend/src/App.tsx` (England routes)
- `frontend/src/lib/appRoutes.ts`
- `frontend/src/lib/constants.ts` (England)
- `frontend/src/lib/site.ts`
- `frontend/src/lib/scoreFormat.ts`
- `frontend/src/lib/uniqueExhibits.ts`
- `frontend/src/lib/compareLabels.ts`
- `frontend/src/pages/ReachPage.tsx`
- `frontend/src/pages/StudioPage.tsx`
- `frontend/src/components/studio/`
- `frontend/src/components/access/`
- `frontend/src/components/home/HomePage.tsx`
- `frontend/src/components/home/DimensionCard.tsx`
- `frontend/src/components/charts/ChoroplethMap.tsx` (England / SVG-first)
- `frontend/src/components/charts/ChartRenderer.tsx`
- `frontend/src/components/charts/GaugeChart.tsx`
- `frontend/src/components/charts/HeatmapChart.tsx`
- `frontend/src/components/charts/HorizontalBarChart.tsx`
- `frontend/src/components/charts/LorenzCurveChart.tsx`
- `frontend/src/components/dimension/DimensionPage.tsx`
- `frontend/src/components/dimension/SectionCard.tsx`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/FilterDropdowns.tsx`
- `frontend/src/components/layout/Header.tsx`
- `frontend/src/components/layout/Footer.tsx`
- `frontend/src/components/layout/TabBar.tsx`
- `frontend/src/components/layout/MetricsTicker.tsx`
- `frontend/src/components/landing/*` (already modified landing files)
- `frontend/src/pages/AuthPage.tsx`
- `frontend/src/pages/ComparePage.tsx`
- `frontend/src/pages/InviteAcceptPage.tsx`
- `frontend/src/pages/MethodologyPage.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/api/hooks.ts`
- `frontend/src/api/types.ts`
- `frontend/src/components/chat/ChatDrawer.tsx` (England)
- `frontend/src/components/chat/QuickActions.tsx`
- `frontend/src/components/chat/SuggestedQuestions.tsx`
- `frontend/src/components/shared/Markdown.tsx`
- `README.md`
- `scripts/smoke_local.py`

**Commit 1.4** `test(england): cover score, reach, studio, bands, and chrome`

Stage:

- `tests/analytics/test_score.py`
- `tests/analytics/test_bands.py`
- `tests/analytics/test_reach.py`
- `tests/analytics/test_studio.py`
- `tests/analytics/test_centroids.py`
- `tests/analytics/test_writers.py`
- `tests/api/test_score.py`
- `tests/api/test_studio.py`
- `tests/api/test_export_pack.py` (England cases only if split; else whole file here and Ireland asserts in 2.3)
- `tests/api/test_metrics_ticker.py`
- `tests/validation/test_gates.py`
- `tests/validation/test_sanity.py`
- `tests/ingestion/test_download.py`
- `tests/fixtures/` (England fixtures only)
- `frontend/src/components/charts/__tests__/ChoroplethMap.test.tsx`
- `frontend/src/components/charts/__tests__/GaugeChart.test.tsx`
- `frontend/src/components/home/__tests__/`
- `frontend/src/lib/__tests__/appRoutes.test.ts`
- `frontend/src/lib/__tests__/scoreFormat.test.ts`
- `frontend/src/lib/__tests__/uniqueExhibits.test.ts`
- `frontend/src/pages/__tests__/ReachPage.test.tsx`
- `frontend/src/pages/__tests__/StudioPage.test.tsx`
- `docs/guidelines/testing.md`
- England hunks of `docs/CURRENT_STATE.md`

**PR 1 checks:**  
`uv run pytest tests/analytics/test_score.py tests/api/test_score.py tests/api/test_studio.py -q`  
`cd frontend && npx vitest run src/lib/__tests__/appRoutes.test.ts src/pages/__tests__/StudioPage.test.tsx`

---

### PR 2 — `feat/ireland-tfi-hp-cso`

**Title:** `feat: Ireland briefing from TFI, Pobal HP, and CSO Small Areas`

**Commit 2.1** `feat(ireland): ingest TFI against CSO Small Areas and Pobal HP`

Stage:

- `src/aequitas/ireland/` (entire tree)
- `scripts/smoke_ireland.py`
- `scripts/census_ireland_qa.py`
- Ireland hunks of `src/aequitas/pipeline/cli.py`
- Ireland hunks of `src/aequitas/warehouse/*` if still unstaged

**Commit 2.2** `feat(frontend): Ireland filters, county map, and country-keyed chat`

Stage:

- `frontend/public/boundaries/ireland_counties.geojson`
- Ireland hunks: `constants.ts`, `appRoutes.ts`, `ChoroplethMap.tsx`,
  `FilterDropdowns.tsx`, `HomePage.tsx`, `DimensionCard.tsx`,
  `ChatDrawer.tsx`, `SuggestedQuestions.tsx`, `QuickActions.tsx`,
  `tickerCountry.ts` (create if Ireland-only; else add Ireland branch),
  `src/aequitas/api/routers/chat.py`,
  `src/aequitas/api/services/rag.py`,
  `src/aequitas/rag/index_builder.py` (**code only**)
- Ireland hunks of `export_pack.py`, `warehouse.py`, `app.py`

**Commit 2.3** `test(ireland): cover catalogue, scores, and export labels`

Stage:

- `tests/ireland/`
- `tests/api/test_ireland.py`
- Ireland cases in `tests/api/test_export_pack.py` if not already in 1.4
- `frontend/src/lib/__tests__/countrySwitcher.test.ts`
- `frontend/src/components/chat/__tests__/`
- Ireland hunks of `docs/CURRENT_STATE.md`
- `docs/guidelines/country-sections.md` (catalogue + Ireland mistakes)

**PR 2 checks:**  
`uv run pytest tests/ireland/ tests/api/test_ireland.py -q`  
`cd frontend && npx vitest run src/lib/__tests__/countrySwitcher.test.ts`

Do **not** add `data/ireland/` or `data/ireland_qa_census.json`.

---

### PR 3 — `feat/network-packs-and-time`

**Title:** `feat: dated network packs and time-series view`

**Commit 3.1** `feat(packs): snapshot network metrics and expose time series`

Stage:

- `src/aequitas/warehouse/packs.py`
- `src/aequitas/pipeline/refresh.py`
- `src/aequitas/api/routers/time_series.py`
- `data/packs/manifest.json`
- `data/packs/england/**/metrics.json`
- `data/packs/ireland/**/metrics.json` (metrics only)
- `scripts/com.aequitas.refresh.plist.example`
- refresh / time hunks of `cli.py`, `app.py`
- `tests/warehouse/test_packs.py`
- `tests/pipeline/test_refresh_interval.py`
- `tests/api/test_time.py`

**Commit 3.2** `feat(frontend): add time-series page and pack date handling`

Stage:

- `frontend/src/pages/TimePage.tsx`
- `frontend/src/components/charts/TimeLineChart.tsx`
- `frontend/src/pages/__tests__/TimePage.test.tsx`
- pack / `as_of` hunks: `hooks.ts`, `FilterDropdowns.tsx`, `Header.tsx`,
  `appRoutes.ts`, `tickerCountry.ts`, `lib/__tests__/tickerCountry.test.ts`
- packs / time paragraphs in `docs/CURRENT_STATE.md`
- `frontend/src/pages/MethodologyPage.tsx` (vintage sentences if unstaged)

**PR 3 checks:**  
`uv run pytest tests/api/test_time.py tests/warehouse/test_packs.py -q`  
`cd frontend && npx vitest run src/pages/__tests__/TimePage.test.tsx`

---

### PR 4 — `feat/netherlands-ovapi`

**Title:** `feat: Netherlands briefing from OVapi and CBS SES-WOA`

**Commit 4.1** `feat(netherlands): build OVapi warehouse with bus and all-PT modes`

Stage:

- `src/aequitas/netherlands/` (entire tree)
- NL hunks of `cli.py`, `warehouse.py`, `app.py`, `score` router (`mode`)
- **Not** `scripts/rebuild_nl_*.py`

**Commit 4.2** `feat(frontend): Netherlands provincie briefing and mode control`

Stage:

- `frontend/public/boundaries/netherlands_provincies.geojson`
- NL hunks: `constants.ts`, `appRoutes.ts`, `ChoroplethMap.tsx`,
  `FilterDropdowns.tsx`, `HomePage.tsx`, `tickerCountry.ts`,
  `SuggestedQuestions.tsx`, `hooks.ts`
- `frontend/src/lib/__tests__/nlSwitcher.test.ts`

**Commit 4.3** `test(netherlands): cover filters, SES join, and no England fallback`

Stage:

- `tests/netherlands/`
- `tests/api/test_netherlands_filter_matrix.py`
- `tests/api/test_netherlands_no_fallback.py`
- remaining NL hunks of `docs/CURRENT_STATE.md`
- NL traps section of `docs/guidelines/country-sections.md`

**PR 4 checks:**  
`uv run pytest tests/netherlands/ tests/api/test_netherlands_no_fallback.py -q`  
`cd frontend && npx vitest run src/lib/__tests__/nlSwitcher.test.ts`

Do **not** add NL `.duckdb` or `.tmp` files.

---

## 7. Commit command shape

```bash
git add -p -- <paths>
git status
git diff --cached --name-only
# abort if a never-stage path appears

git commit -m "$(cat <<'EOF'
feat(analytics): add in-country score, service bands, and reach writers

Writers own compute_score and Aequitas service bands. Travel-time
layers stay empty without r5py.
EOF
)"
```

No `--no-verify` unless a hook blocks on missing local DuckDB; if you
skip a hook, say so in the PR body.

No `Co-authored-by`. No `Made-with:`.

---

## 8. Pull request bodies

Use this template. Do not mention internal programme numbers.

```markdown
## Summary
<three bullets of user-visible behaviour>

## How to try
./scripts/dev.sh
<URLs, e.g. http://localhost:5173/app/england>

## Out of this change
- Analytics DuckDB files stay on the machine (gitignored).
- 15/30/45 travel times are empty unless r5py has been run locally.
- Chat index binaries are not in git.

## Checks
<exact commands you ran and pass counts>
```

Open with `gh pr create --base <parent-branch> --title "<title from §6>" --body-file -`

If `gh` is not authenticated: `git push -u origin <branch>` and stop.
Print the compare URL. Do not merge.

---

## 9. Definition of done

You are done when:

1. Exactly **four** open PRs exist, stacked 1 → 4.
2. Exactly **twelve** commits exist on the tip of
   `feat/netherlands-ovapi` that are not on `origin/main`
   (4 + 3 + 2 + 3). Fix-up commits for CI/conflicts are extra and
   allowed; do not rewrite the original 12 subjects.
3. `git diff origin/main --stat` on the tip contains **no** never-stage path.
4. All four PRs are **healthy** (§10) **or**
   `docs/guidelines/git-landing-status.md` exists, is complete, and
   every remaining problem is something only the human can unblock
   (auth, missing GitHub Actions secrets, required reviewers).
5. You report: 12 original SHAs, extra fix SHAs, 4 PR URLs, babysit
   table (CI / conflicts / comments), path to the status file if any.

If you cannot split a file, stop and write the status file — do not
invent a fifth PR and do not dump it all into PR 1 silently.

---

## 10. Babysit the stack (required)

After `gh pr create` for all four, do **not** walk away. Watch the
whole stack until it is fine or you have written the problems doc.

### 10.1 What to check (every PR, bottom-up)

For each of the four numbers:

```bash
gh pr view <n> --json number,title,url,state,baseRefName,headRefName,mergeable,mergeStateStatus,statusCheckRollup,reviewDecision
gh pr checks <n>
gh pr diff <n> --name-only
```

Fail the babysit (and write the status file) if any of these is true:

| Check | Fail if |
|-------|---------|
| Count | Not exactly 4 open PRs, or bases are not main → 1 → 2 → 3 |
| Binaries | `gh pr diff --name-only` matches duckdb, faiss, `.bin`, `node_modules`, `qa-visual`, `.env`, `sqlite`, `qa-*.mjs`, `rebuild_nl_` |
| Conflicts | `mergeable` is `CONFLICTING` or `mergeStateStatus` is `DIRTY` |
| CI | Any check `FAILURE` or `ERROR` |
| CI stuck | `CANCELLED`, `TIMED_OUT`, `STARTUP_FAILURE`, `STALE` |
| Review | `CHANGES_REQUESTED` or unresolved review threads |
| Titles | Title or commits contain `Wave`, `stamp`, `PNG`, `trap #`, `agent` |
| Commit count | Branch 1≠4 / 2≠3 / 3≠2 / 4≠3 *product* commits (fix-ups extra) |

### 10.2 What you may fix yourself

- Merge conflicts: rebase onto the parent branch (`git rebase` or `gt restack`).
  Push with `--force-with-lease` only. Restack children after the parent moves.
- CI red because of a test you own: fix on that branch, commit
  `fix: <what failed>` (not a 13th product commit with a new feature).
- Leaked never-stage file: `git rm --cached`, ignore line, commit
  `chore: stop tracking local data files`.
- Wrong PR base: `gh pr edit <n> --base <parent>`.

Cap: **3 fix commits per PR**. If still red, stop coding and write §10.4.

Never merge. Never `git push --force` without `--force-with-lease`.
Never change product scope (no new country, no FAISS binary).

### 10.3 Recheck after every fix

Wait for checks (`gh pr checks --watch` up to 20 minutes per PR).
Then re-run §10.1 on **all four** (a parent rebase dirties children).

### 10.4 Problems file (when not all-green)

Create **and leave unstaged**:

`docs/guidelines/git-landing-status.md`

Overwrite each time you learn more. Use this shape:

```markdown
# Git landing status

Date: <ISO date>
Author: landing agent
Stack: 4 PRs (list URLs)

## Verdict
BLOCKED | PARTIAL | GREEN

## PR table
| # | URL | Base | CI | Mergeable | Review | Notes |
|---|-----|------|----|-----------|--------|-------|

## Problems
### P1 — <short name>
- PR:
- Symptom:
- Command / log excerpt:
- What I tried:
- Why I stopped:
- What the human must do:

## Leaked paths
(none | list)

## Checks I ran
```

If the stack is **GREEN**, delete `git-landing-status.md` if you created
it, or write `Verdict: GREEN` and still leave it unstaged.

### 10.5 Human-only blockers (do not fake a fix)

Write these into the status file and stop:

- `gh auth` missing or no `repo` scope
- GitHub Actions not configured / secrets missing
- Required reviewers or branch protection you cannot satisfy
- `origin/main` moved and the user forbade rebase
- HEAD was not `44febd9` at start

