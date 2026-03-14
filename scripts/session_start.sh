#!/bin/bash
# SessionStart hook: writes session_id → cwd-indexed lookup file

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

if [ -z "$SESSION_ID" ] || [ -z "$CWD" ]; then
  exit 0
fi

# Hash the cwd to a short 8-char key (macOS + Linux)
cwd_hash() {
  if command -v md5 &>/dev/null; then
    echo "$1" | md5 | cut -c1-8
  else
    echo "$1" | md5sum | cut -c1-8
  fi
}
CWD_HASH=$(cwd_hash "$CWD")
TASKS_DIR="$HOME/.claude/session-tasks"
mkdir -p "$TASKS_DIR"

# Write session_id to lookup file (overwrites previous session for this cwd)
echo "$SESSION_ID" > "$TASKS_DIR/current_${CWD_HASH}.txt"

# Write initial task file: show dir + git branch as placeholder
TASK_FILE="$TASKS_DIR/${SESSION_ID}.txt"
DIR_NAME="${CWD##*/}"
BRANCH=$(git -C "$CWD" rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ -n "$BRANCH" ]; then
  echo "INIT:${DIR_NAME}  [${BRANCH}]" > "$TASK_FILE"
else
  echo "INIT:${DIR_NAME}" > "$TASK_FILE"
fi

# Also clean up task files older than 7 days
find "$TASKS_DIR" -name "*.txt" -mtime +7 -delete 2>/dev/null

exit 0
