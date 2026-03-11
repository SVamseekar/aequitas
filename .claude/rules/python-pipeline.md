---
paths:
  - "src/aequitas/**/*.py"
  - "tests/**/*.py"
  - "notebooks/**/*.ipynb"
---

# Python Pipeline Rules

- Type hints on every function signature, no exceptions
- Pydantic v2 models at every data boundary — raw data in, validated model out
- Use `loguru` for all logging, never `print` or stdlib `logging`
- No bare `except` — always catch specific exceptions
- Docstrings on all public functions: one line summary, then Args/Returns if non-obvious
- No function longer than 50 lines — split it
- No file longer than 250 lines — split it
- Every data transformation step must be independently testable
- Population denominator is ALWAYS total ONS regional population (~56.3M for England) — never pipeline-filtered population
- When in doubt about a data counting decision, surface it explicitly rather than assuming
