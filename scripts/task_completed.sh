#!/bin/bash
# TaskCompleted hook: marks session task as DONE (strong completion signal)

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')

if [ -z "$SESSION_ID" ]; then
  exit 0
fi

TASK_FILE="$HOME/.claude/session-tasks/${SESSION_ID}.txt"

if [ ! -f "$TASK_FILE" ]; then
  exit 0
fi

# Read current description, strip any existing prefix
CURRENT=$(cat "$TASK_FILE")
DESC="${CURRENT#WIP:}"
DESC="${DESC#AUTO:}"
DESC="${DESC#DONE:}"
DESC="${DESC#MANUAL:}"
DESC=$(echo "$DESC" | tr -d '\n')

# Write DONE status
echo "DONE:${DESC}" > "$TASK_FILE"

exit 0
