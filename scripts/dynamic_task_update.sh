#!/bin/bash
# Stop hook: dynamically updates task description and detects completion

INPUT=$(cat)

# Prevent infinite loops
STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
if [ "$STOP_ACTIVE" = "true" ]; then
  exit 0
fi

# Prevent recursion from CLI backend subprocess
if [ "${CLAUDE_TAB_SKIP_HOOK:-0}" = "1" ]; then
  exit 0
fi

SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty')

if [ -z "$SESSION_ID" ] || [ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ]; then
  exit 0
fi

TASKS_DIR="$HOME/.claude/session-tasks"
TASK_FILE="$TASKS_DIR/${SESSION_ID}.txt"

# Don't overwrite manually-pinned tasks
if [ -f "$TASK_FILE" ]; then
  CURRENT=$(head -1 "$TASK_FILE")
  if [[ "$CURRENT" == MANUAL:* ]]; then
    exit 0
  fi
fi

# Reset DONE tasks so Python script generates fresh description
if [ -f "$TASK_FILE" ]; then
  CURRENT2=$(head -1 "$TASK_FILE")
  if [[ "$CURRENT2" == DONE:* ]]; then
    DESC="${CURRENT2#DONE:}"
    echo "WIP:" > "$TASK_FILE"
    echo "PREV:${DESC}" >> "$TASK_FILE"
  fi
fi

mkdir -p "$TASKS_DIR"

# Call the Python helper script
PYTHON3="/usr/bin/python3"
[ -x "$PYTHON3" ] || PYTHON3=$(command -v python3 2>/dev/null || true)
[ -z "$PYTHON3" ] && exit 0
"$PYTHON3" "$HOME/.claude/scripts/dynamic_task_update.py" "$TRANSCRIPT" "$TASK_FILE"

exit 0
