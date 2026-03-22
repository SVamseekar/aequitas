#!/bin/bash
# Fires before every Bash command.
# Blocks commands that could corrupt the data pipeline or warehouse.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

# Block patterns: dropping DuckDB warehouse, deleting processed data, force-resetting git
BLOCKED_PATTERNS=(
    '(^|;|&&|\|\|)\s*rm\b.*aequitas\.duckdb'
    '(^|;|&&|\|\|)\s*rm\b.*data/processed'
    '(^|;|&&|\|\|)\s*rm\b.*data/raw'
    '(^|;|&&|\|\|)\s*rm\s+-rf\s+\.'
    'git\s+reset\s+--hard'
    'git\s+clean\s+-f'
    '\bDROP\s+TABLE\b'
    '\bDROP\s+DATABASE\b'
)

for pattern in "${BLOCKED_PATTERNS[@]}"; do
    if echo "$COMMAND" | grep -qE "$pattern"; then
        jq -n \
            --arg reason "Blocked: '$pattern' matched in command. This could corrupt pipeline data or the warehouse. Run manually if intentional." \
            '{
                hookSpecificOutput: {
                    hookEventName: "PreToolUse",
                    permissionDecision: "deny",
                    permissionDecisionReason: $reason
                }
            }'
        exit 0
    fi
done

exit 0
