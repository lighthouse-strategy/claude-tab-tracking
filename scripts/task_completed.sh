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

# Read current description (line 1 only), strip any existing prefix
CURRENT=$(head -1 "$TASK_FILE")
PREV_LINE=$(sed -n '2p' "$TASK_FILE")
DESC="${CURRENT#WIP:}"
DESC="${DESC#AUTO:}"
DESC="${DESC#DONE:}"
DESC="${DESC#MANUAL:}"
DESC="${DESC#INIT:}"
DESC=$(echo "$DESC" | tr -d '\n')

# Write DONE status, preserving PREV line
echo "DONE:${DESC}" > "$TASK_FILE"
if [[ -n "$PREV_LINE" && "$PREV_LINE" == PREV:* ]]; then
  echo "$PREV_LINE" >> "$TASK_FILE"
fi

exit 0
