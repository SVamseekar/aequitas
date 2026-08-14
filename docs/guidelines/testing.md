# Testing Guidelines

Instructions for running unit, integration, and data validation suites across backend and frontend repositories.

---

## 1. Backend Testing (Pytest)

- **Execution Prefix:** Backend tests must always be run using `uv run pytest`. Running bare `pytest` will fail because dependencies from `pyproject.toml` are not resolved in the default environment path.
- **Commands:**
  - Run all tests:
    ```bash
    uv run pytest
    ```
  - Run tests silently (quiet mode):
    ```bash
    uv run pytest -q
    ```
  - Exclude slow integration tests:
    ```bash
    uv run pytest -m "not slow"
    ```

---

## 2. Pipeline Validation (Validation Gates)

Aequitas uses a custom validation suite to enforce that pre-computed metrics align with ground truth expectations before they are written to the database.
- **Run Validation:**
  ```bash
  uv run aequitas validate
  ```
- **Validation Report:** The command produces a markdown report at `data/processed/validation_report.md`. Check this report to ensure all gates pass before committing backend data changes.

---

## 3. Frontend Testing (Vitest)

- **Test Suite:** The frontend uses Vitest for component unit tests.
- **Execution:** Run the tests from the `frontend/` directory:
  ```bash
  cd frontend
  npx vitest run
  ```
