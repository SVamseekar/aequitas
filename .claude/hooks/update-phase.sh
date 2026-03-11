#!/bin/bash
# Fires after every Write or Edit.
# When a key milestone file is created, auto-updates the Current Phase
# in CLAUDE.md so future sessions always reflect reality.

FILE=$(cat | jq -r '.tool_input.file_path // .tool_input.path // ""')
CLAUDE_MD="$CLAUDE_PROJECT_DIR/CLAUDE.md"

[[ ! -f "$CLAUDE_MD" ]] && exit 0

update_phase() {
    local new_phase="$1"
    # Replace the Current Phase line in CLAUDE.md
    sed -i '' "s|^## Current Phase.*|## Current Phase|" "$CLAUDE_MD"
    sed -i '' "/^## Current Phase/{n;s|.*|$new_phase|}" "$CLAUDE_MD"
}

case "$FILE" in
    */notebooks/01_data_audit.ipynb)
        update_phase "**Phase 0 — Data audit notebook created.** Profile each source and lock ground truth counts."
        ;;
    */src/aequitas/ingestion/*)
        update_phase "**Phase 1 — Ingestion layer in progress.** Build processing/ next."
        ;;
    */src/aequitas/processing/*)
        update_phase "**Phase 1 — Processing layer in progress.** Build validation/ next."
        ;;
    */src/aequitas/intelligence/engine.py)
        update_phase "**Phase 2 — Intelligence layer in progress.** Build warehouse/ next."
        ;;
    */src/aequitas/warehouse/builder.py)
        update_phase "**Phase 2 — Warehouse builder in progress.** Run pipeline to produce aequitas.duckdb."
        ;;
    */frontend/src/pages/Dashboard.tsx)
        update_phase "**Phase 3 — Dashboard in progress.** Connect to warehouse API."
        ;;
    */src/aequitas/rag/chatbot.py)
        update_phase "**Phase 4 — RAG chatbot in progress.**"
        ;;
esac

exit 0
