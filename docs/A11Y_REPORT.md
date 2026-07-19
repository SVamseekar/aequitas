# Accessibility report (2026-07-19)

## Target

WCAG 2.2 **AA** for public marketing pages and authenticated app chrome.

## Automated run (this session)

`@axe-core/cli` against static `dist/` **could not complete**: ChromeDriver / Chrome version mismatch (driver 151 vs Chrome 148). Re-run after aligning Chrome:

```bash
cd frontend && npm run build
npx serve dist -l 4173 &
npx browser-driver-manager install chrome
npx @axe-core/cli http://127.0.0.1:4173/ --exit
npx @axe-core/cli http://127.0.0.1:4173/methodology --exit
npx @axe-core/cli http://127.0.0.1:4173/accessibility --exit
```

## Already in product

- Accessibility statement page: `/accessibility`  
- Semantic landmarks on landing (nav, main sections, footer)  
- Skip-oriented structure: FAQ, methodology, contact  
- Auth / dashboard: `noindex`; keyboard focus styles on primary CTAs  
- Policy disclaimer visible in footer  

## Manual checklist (owner)

- [ ] Keyboard-only pass on landing → explore → filter change  
- [ ] Screen reader: H1 only once per page; nav named  
- [ ] Colour contrast on indigo-on-dark (spot check)  
- [ ] Forms: contact labels associated  
- [ ] Focus trap in chat drawer (implemented)  

## Known gaps (honest)

- Chart library (Observable Plot / custom) may need extra aria on complex graphics  
- Map interactions need keyboard alternatives  
- Automated axe report pending ChromeDriver fix  
