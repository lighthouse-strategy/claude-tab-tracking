#!/bin/bash
# Statusline: shows session task (WIP/DONE), context usage, and session duration

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')
PCT=$(echo "$INPUT" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
PCT=${PCT:-0}
DURATION_MS=$(echo "$INPUT" | jq -r '.cost.total_duration_ms // 0' | cut -d. -f1)
DURATION_MS=${DURATION_MS:-0}
DIR=$(echo "$INPUT" | jq -r '.workspace.current_dir // .cwd // ""')
DIR_NAME="${DIR##*/}"

# Format duration: show as "5min" or "1h23m"
DURATION_MIN=$(( DURATION_MS / 60000 ))
if [ "$DURATION_MIN" -ge 60 ]; then
  DURATION_FMT="$(( DURATION_MIN / 60 ))h$(( DURATION_MIN % 60 ))m"
else
  DURATION_FMT="${DURATION_MIN}min"
fi

# ANSI colors
RESET='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
CYAN='\033[36m'

# --- Line 1: Task status badge + description ---
TASK_FILE="$HOME/.claude/session-tasks/${SESSION_ID}.txt"

if [ -f "$TASK_FILE" ]; then
  RAW=$(cat "$TASK_FILE" | tr -d '\n')
  if [[ "$RAW" == DONE:* ]]; then
    BADGE="${GREEN}[DONE]${RESET}"
    TASK="${RAW#DONE:}"
  elif [[ "$RAW" == MANUAL:* ]]; then
    BADGE="${BOLD}[SET] ${RESET}"
    TASK="${RAW#MANUAL:}"
  elif [[ "$RAW" == WIP:* ]]; then
    BADGE="${YELLOW}[WIP] ${RESET}"
    TASK="${RAW#WIP:}"
  elif [[ "$RAW" == INIT:* ]]; then
    BADGE="${DIM}[---]${RESET}"
    TASK="${RAW#INIT:}"
  else
    BADGE="${DIM}[---]${RESET}"
    TASK="$RAW"
  fi
  # Truncate to 60 chars
  if [ ${#TASK} -gt 60 ]; then
    TASK="${TASK:0:57}..."
  fi
  echo -e "${BADGE} ${TASK}"
else
  echo -e "${DIM}[---] starting...${RESET}"
fi

# --- Line 2: Directory | context% | duration ---
# Color context % based on usage
if [ "$PCT" -lt 50 ]; then
  PCT_COLOR="$GREEN"
elif [ "$PCT" -lt 80 ]; then
  PCT_COLOR="$YELLOW"
else
  PCT_COLOR="$RED"
fi

echo -e "${DIM}${DIR_NAME}${RESET}  |  ctx ${PCT_COLOR}${PCT}%${RESET}  |  ${DIM}${DURATION_FMT}${RESET}"
