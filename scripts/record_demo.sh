#!/bin/bash
# Automated demo recording script
# Simulates statusline state changes without running Claude Code
# Usage: ./scripts/record_demo.sh

set -euo pipefail

# --- Hide personal info ---
printf '\033]0;claude-tab-tracking demo\007'
clear
export PS1="~ % "
echo "Ready to record. Press Enter to begin..."
read -r

TASKS_DIR="$HOME/.claude/session-tasks"
DEMO_SESSION="demo-session-recording"
TASK_FILE="$TASKS_DIR/${DEMO_SESSION}.txt"

# ANSI
RESET='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'
GREEN='\033[32m'
YELLOW='\033[33m'
CYAN='\033[36m'

# Simulated JSON input for statusline script
mk_status_json() {
  local tokens="$1"
  local duration="$2"
  echo "{
    \"session_id\": \"${DEMO_SESSION}\",
    \"context_window\": {
      \"context_window_size\": 200000,
      \"current_usage\": {
        \"input_tokens\": ${tokens},
        \"cache_creation_input_tokens\": 0,
        \"cache_read_input_tokens\": 0
      }
    },
    \"cost\": { \"total_duration_ms\": ${duration} },
    \"workspace\": { \"current_dir\": \"/Users/dev/my-project\" }
  }"
}

STATUSLINE_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/session_statusline.sh"

render_statusline() {
  mk_status_json "$1" "$2" | bash "$STATUSLINE_SCRIPT"
}

type_text() {
  local text="$1"
  for (( i=0; i<${#text}; i++ )); do
    printf '%s' "${text:$i:1}"
    sleep 0.05
  done
  echo ""
}

stream_lines() {
  while IFS= read -r line; do
    echo -e "$line"
    sleep 0.25
  done
}

clear_and_header() {
  clear
  echo ""
}

cleanup() {
  rm -f "$TASK_FILE"
}
trap cleanup EXIT

mkdir -p "$TASKS_DIR"

# ============================================================
# Scene 1: Session starts — [---], user types first prompt
# ============================================================
clear_and_header
echo "INIT:my-project [main]" > "$TASK_FILE"
render_statusline 0 0
echo -e "  ─────────────────────────────────────────────"
echo ""
echo -e "  ${BOLD}Welcome to Claude Code!${RESET}"
echo ""
echo -ne "  ${BOLD}>${RESET} "
sleep 1.2
type_text "help me write a hello world in python"
sleep 0.6

# ============================================================
# Scene 2: Claude responds with code — [WIP]
# ============================================================
clear_and_header
echo "WIP:Write hello world in Python" > "$TASK_FILE"
render_statusline 3200 30000
echo -e "  ─────────────────────────────────────────────"
echo ""
echo -e "  ${BOLD}>${RESET} help me write a hello world in python"
echo ""
stream_lines <<'EOF'
  I'll create a simple hello world script for you.
EOF
sleep 0.4
echo ""
echo -e "  ${DIM}  hello.py${RESET}"
stream_lines <<EOF
  ${GREEN}def main():${RESET}
  ${GREEN}    print("Hello, World!")${RESET}
  ${GREEN}${RESET}
  ${GREEN}if __name__ == "__main__":${RESET}
  ${GREEN}    main()${RESET}
EOF
sleep 0.4
echo ""
stream_lines <<'EOF'
  Created hello.py. Run it with `python hello.py`.
EOF
sleep 2.5

# ============================================================
# Scene 3: User asks follow-up — still [WIP]
# ============================================================
clear_and_header
echo "WIP:Write hello world in Python" > "$TASK_FILE"
render_statusline 6400 60000
echo -e "  ─────────────────────────────────────────────"
echo ""
echo -e "  ${DIM}  Created hello.py.${RESET}"
echo ""
echo -ne "  ${BOLD}>${RESET} "
sleep 1.0
type_text "can you also add a greet function that takes a name?"
sleep 0.6

# ============================================================
# Scene 4: Claude updates code — WIP description updates
# ============================================================
clear_and_header
echo "WIP:Add greet function to hello.py" > "$TASK_FILE"
render_statusline 10200 90000
echo -e "  ─────────────────────────────────────────────"
echo ""
echo -e "  ${BOLD}>${RESET} can you also add a greet function that takes a name?"
echo ""
stream_lines <<'EOF'
  Sure! I'll add a greet function.
EOF
sleep 0.4
echo ""
echo -e "  ${DIM}  hello.py${RESET}"
stream_lines <<EOF
  ${GREEN}def greet(name: str) -> str:${RESET}
  ${GREEN}    return f"Hello, {name}!"${RESET}
  ${GREEN}${RESET}
  ${GREEN}def main():${RESET}
  ${GREEN}    print(greet("World"))${RESET}
EOF
sleep 0.4
echo ""
stream_lines <<'EOF'
  Updated hello.py with the greet function.
EOF
sleep 2.5

# ============================================================
# Scene 5: Task done — [DONE], user starts new task
# ============================================================
clear_and_header
echo "DONE:Add greet function to hello.py" > "$TASK_FILE"
render_statusline 14000 120000
echo -e "  ─────────────────────────────────────────────"
echo ""
echo -e "  ${DIM}  Updated hello.py with the greet function.${RESET}"
echo ""
echo -ne "  ${BOLD}>${RESET} "
sleep 1.5
type_text "now add unit tests for it"
sleep 0.6

# ============================================================
# Scene 6: New task — 3-line statusline with PREV (money shot)
# ============================================================
clear_and_header
printf 'WIP:Add unit tests for hello.py\nPREV:Add greet function to hello.py\n' > "$TASK_FILE"
render_statusline 20000 150000
echo -e "  ─────────────────────────────────────────────"
echo ""
echo -e "  ${BOLD}>${RESET} now add unit tests for it"
echo ""
stream_lines <<'EOF'
  I'll create tests for both main() and greet().
EOF
sleep 0.4
echo ""
echo -e "  ${DIM}  test_hello.py${RESET}"
stream_lines <<EOF
  ${GREEN}import unittest${RESET}
  ${GREEN}from hello import greet, main${RESET}
  ${GREEN}${RESET}
  ${GREEN}class TestHello(unittest.TestCase):${RESET}
  ${GREEN}    def test_greet(self):${RESET}
  ${GREEN}        self.assertEqual(greet("Alice"), "Hello, Alice!")${RESET}
  ${GREEN}${RESET}
  ${GREEN}    def test_greet_empty(self):${RESET}
  ${GREEN}        self.assertEqual(greet(""), "Hello, !")${RESET}
EOF
sleep 0.4
echo ""
stream_lines <<'EOF'
  Running tests...
EOF
sleep 0.3
echo -e "  ${GREEN}2 passed${RESET} in 0.01s"
sleep 5.0

# ============================================================
# Done
# ============================================================
echo ""
