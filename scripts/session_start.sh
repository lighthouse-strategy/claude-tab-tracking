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
find "$TASKS_DIR" -name "*.txt" ! -name "current_*.txt" -mtime +7 -delete 2>/dev/null

# --- Memo overview ---
MEMO_DIR="$HOME/.claude/memos"
if [ -d "$MEMO_DIR" ]; then
  OVERVIEW=""
  for proj_dir in "$MEMO_DIR"/*/; do
    [ -d "$proj_dir" ] || continue
    proj_name=$(basename "$proj_dir")
    [ "$proj_name" = "_archive" ] && continue

    latest=""
    while IFS= read -r memo_file; do
      [ -z "$memo_file" ] && continue
      fname=$(basename "$memo_file" .md)
      count=$(grep -c '^## ' "$memo_file" 2>/dev/null || echo 0)
      if [ "$count" -gt 0 ]; then
        if [ -z "$latest" ]; then
          latest="$fname ${count}"
        else
          latest="$latest | $fname ${count}"
        fi
      fi
    done < <(ls -t "$proj_dir"*.md 2>/dev/null | head -2)

    if [ -n "$latest" ]; then
      OVERVIEW="$OVERVIEW  $proj_name  $latest
"
    fi
  done

  if [ -n "$OVERVIEW" ]; then
    echo "[memo] Recent projects:"
    printf '%s' "$OVERVIEW" | head -5
    echo "Type /recall for details"
  fi
fi

exit 0
