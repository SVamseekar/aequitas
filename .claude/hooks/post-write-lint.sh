#!/bin/bash
# Fires after every Write or Edit on a Python file.
# Runs ruff check silently — output feeds back to Claude as context.

FILE=$(echo "$1" | jq -r '.tool_input.file_path // .tool_input.path // ""')

[[ "$FILE" != *.py ]] && exit 0
[[ ! -f "$FILE" ]] && exit 0

cd "$CLAUDE_PROJECT_DIR" || exit 0

if command -v ruff &>/dev/null; then
    OUTPUT=$(ruff check "$FILE" --output-format=concise 2>&1)
    if [[ -n "$OUTPUT" ]]; then
        echo "$OUTPUT"
    fi
fi

exit 0
