---
name: run-pipeline
description: Run the Aequitas data pipeline. Specify stage: ingestion, processing, intelligence, warehouse, or all.
disable-model-invocation: true
argument-hint: [ingestion|processing|intelligence|warehouse|all]
---

# Run Pipeline

Runs the Aequitas pipeline for the specified stage: $ARGUMENTS

## Pre-flight checks (always run first)
1. Confirm virtual environment is active: `which python` should point to `venv/bin/python`
2. Confirm data audit notebook has been completed and ground truth counts are locked
3. Confirm previous stage passed validation (check `data/validation/` for reports)

## Stages

### ingestion
```bash
python -m aequitas.pipeline.cli --stage=ingestion
```
Validates: `data/raw/` has NaPTAN CSV, 9 BODS feeds, Census parquet, IMD CSV, GeoJSON boundaries

### processing
```bash
python -m aequitas.pipeline.cli --stage=processing
```
Validates: entity counts match ground truth within 1%, match rates >95%

### intelligence
```bash
python -m aequitas.pipeline.cli --stage=intelligence
```
Validates: all 43 sections × 30 filter combos produce non-null results

### warehouse
```bash
python -m aequitas.pipeline.cli --stage=warehouse
```
Validates: `aequitas.duckdb` built, schema intact, 1,290 rows in results table

### all
Runs all stages in sequence. Stops at first validation failure.

## On failure
- Read the error carefully — do NOT retry the same command
- Check `logs/pipeline.log` for full traceback
- Check the relevant validation report in `data/validation/`
- Fix the root cause before re-running
