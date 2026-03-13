#!/bin/bash
# Fires at session start.
# Prints a concise project status so Claude always knows where things stand
# without needing to ask or explore.

cd "$CLAUDE_PROJECT_DIR" || exit 0

echo "=== Aequitas Session Context ==="

# Current git branch + last commit
echo "Branch: $(git branch --show-current 2>/dev/null)"
echo "Last commit: $(git log -1 --format='%h %s' 2>/dev/null)"

# Phase indicator — derived from what exists
if [[ -f "aequitas.duckdb" ]]; then
    echo "Phase: Warehouse built"
elif [[ -d "src/aequitas/intelligence" ]]; then
    echo "Phase: Intelligence layer in progress"
elif [[ -d "src/aequitas/processing" ]]; then
    echo "Phase: Data pipeline in progress"
elif [[ -f "data/audit/master_lsoa_table.parquet" ]]; then
    NB03=$(ls notebooks/03*.ipynb 2>/dev/null | wc -l | tr -d ' ')
    NB04=$(ls notebooks/04*.ipynb 2>/dev/null | wc -l | tr -d ' ')
    echo "Phase: 0 IN PROGRESS — Series 03: ${NB03}/8 notebooks exist (03a/03b/03c/03h=full; 03d/03e/03f/03g=need rebuild to plan standard). Series 04: ${NB04}/6 not started. Use subagent-driven-development with plan at docs/superpowers/plans/2026-03-12-phase0-complete-eda.md. Next task: rebuild 03d (GIAS schools)."
elif [[ -f "notebooks/01_data_audit.ipynb" ]]; then
    echo "Phase: 0 — Data audit in progress"
else
    echo "Phase: 0 — Data audit not started"
fi

# Validation reports if they exist
if [[ -d "data/validation" ]]; then
    LATEST=$(ls -t data/validation/*.json 2>/dev/null | head -1)
    if [[ -n "$LATEST" ]]; then
        echo "Latest validation: $LATEST"
        python3 -c "
import json, sys
try:
    d = json.load(open('$LATEST'))
    status = d.get('status', 'unknown')
    print(f'  Status: {status}')
except:
    pass
" 2>/dev/null
    fi
fi

echo "================================"
exit 0
