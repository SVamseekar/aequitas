#!/bin/bash
# Fires before every Bash command.
# Blocks commands that could corrupt the data pipeline or warehouse.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

# Block patterns: dropping DuckDB warehouse, deleting processed data, force-resetting git
BLOCKED_PATTERNS=(
    'rm.*aequitas\.duckdb'
    'rm.*data/processed'
    'rm.*data/raw'
    'rm -rf \.'
    'git reset --hard'
    'git clean -f'
    'DROP TABLE'
    'DROP DATABASE'
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
