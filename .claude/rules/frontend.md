---
paths:
  - "frontend/src/**/*.tsx"
  - "frontend/src/**/*.ts"
---

# Frontend Rules

- TypeScript strict mode — no `any`, no `as unknown as X` hacks
- Component files ≤ 200 lines — split into smaller components if growing
- No business logic in components — components fetch and render only
- Reuse patterns from bharat-alpha: SSE streaming chat, Supabase auth, conversation persistence
- shadcn/ui components only — no ad-hoc custom UI primitives
- All API calls go through a typed client layer — never raw `fetch` in components
- Loading and error states required on every async operation — no silent failures
