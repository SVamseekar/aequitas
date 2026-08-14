# Branching, Commits, and Git Workflows

Guidelines for version control, cross-platform git configuration, and AI footprint isolation in this repository.

**Programme hold (2026-08-14):** wave agents do **not** commit mid-wave.
When the user asks for git, **divide PRs logically** — not one mega-diff of
the whole tree. Natural cuts (only after that slice is stamped Done):

1. England product (Waves 1–4: app IA, score, map, Studio, Reach)
2. Ireland pack + briefing + FAISS (Wave 5)
3. Dated packs + `/time` + refresh (Wave 6)
4. Netherlands warehouse + briefing (Wave 7)
5. Ops GTFS-RT/SIRI (Wave 8)
6. France (Wave 9)

No standalone docs PR. Product-facing notes (CURRENT_STATE, country catalogue)
ride in the same commit as the feature they describe. Do not open
`docs/product-state`. Programme-only files stay unstaged (`AGENTS.md`,
`docs/superpowers/`).

Squash-merge each PR. Conventional commits. No AI co-author trailers.
Do not mix an unfinished wave into a Done-wave PR.

---

## 1. Branching Model (GitHub Flow)
- **Feature Development:** Create isolated feature branches off `main` (e.g. `feat/core-auth` or `fix/payment-gateway`).
- **PR Merge Strategy:** Squash-merge feature branches into `main`.
- **Branch Cleanup:** Manually delete local and remote feature branches after merging to keep the repository clean.

---

## 2. Commit Message Format
Every commit message **must** conform to the Conventional Commits style:
- `feat(<component>):` - A new feature (e.g. `feat(api): add lsoa metrics`)
- `fix(<component>):` - A bug fix (e.g. `fix(charts): fix box-violin schema mismatch`)
- `chore:` - Maintenance, dependencies, or local configurations
- `docs:` - Documentation updates

*Strict Rule:* **NEVER** append "Co-Authored-By" metadata tags or any AI assistant tags to git commit messages.

---

## 3. Cross-Platform Line Endings (CRLF vs. LF)
This repository’s `.gitattributes` mandates line endings as LF (`eol=lf`).
- **Mac/Linux Environment:** The local configuration `core.autocrlf` **must** be set to `input`.
- **Windows Environment:** `core.autocrlf` **must** be set to `true`.

---

## 4. AI Footprint & Workspace Isolation (Strict Rule)
To maintain project cleanliness and ensure that development trace files do not pollute the git history:
- **No AI Traces in Git:** **NEVER** commit or stage files related to AI developer tools, plugins, or plans.
- **Ignored Directories:** The following files/directories are explicitly gitignored and **must not** be tracked:
  - `AGENTS.md` (root runbook)
  - `docs/superpowers/` (all specs and implementation plans)
  - `.claude/`, `.superpowers/`, `.serena/`, `.cursor/`, `.playwright-mcp/`
- **Sanity Check:** Before committing, always verify your staged files using `git status` or `git diff --staged` to ensure no AI trace or plan files are staged.

---

## 5. Versioning
- **Release Versioning:** We use release-style versioning (e.g., `v1.0.0`, `v1.1.0`) for tags, builds, and major iterations rather than arbitrary build numbers or raw commit SHAs.
- **Version Alignment:** Ensure project configuration files (e.g., `pyproject.toml`, `package.json`) have their version fields updated in sync with release versions.

