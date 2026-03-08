#!/bin/bash
# SessionEnd hook: removes cwd lookup file when session terminates

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

if [ -z "$CWD" ]; then
  exit 0
fi

CWD_HASH=$(echo "$CWD" | md5 | cut -c1-8)
LOOKUP="$HOME/.claude/session-tasks/current_${CWD_HASH}.txt"

# Only remove if this session owns the lookup (not a different session)
if [ -f "$LOOKUP" ] && [ "$(cat "$LOOKUP")" = "$SESSION_ID" ]; then
  rm -f "$LOOKUP"
fi

exit 0
