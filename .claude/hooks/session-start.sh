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
elif [[ -f "notebooks/01_data_audit.ipynb" ]]; then
    echo "Phase: Data audit notebook exists"
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
