#!/bin/bash
# claude-tab-tracking installer
# Copies scripts, registers hooks and statusline in ~/.claude/settings.json

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
SCRIPTS_DIR="$CLAUDE_DIR/scripts"
COMMANDS_DIR="$CLAUDE_DIR/commands"
TASKS_DIR="$CLAUDE_DIR/session-tasks"
SETTINGS="$CLAUDE_DIR/settings.json"

echo "Installing claude-tab-tracking..."

# --- Check dependencies ---
if ! command -v jq &>/dev/null; then
  echo "Error: jq is required. Install with: brew install jq"
  exit 1
fi

# --- Create directories ---
mkdir -p "$SCRIPTS_DIR" "$COMMANDS_DIR" "$TASKS_DIR"

# --- Copy scripts ---
cp "$REPO_DIR/scripts/"*.sh "$SCRIPTS_DIR/"
cp "$REPO_DIR/scripts/"*.py "$SCRIPTS_DIR/"
cp "$REPO_DIR/commands/task.md" "$COMMANDS_DIR/"
chmod +x "$SCRIPTS_DIR/"*.sh "$SCRIPTS_DIR/"*.py

echo "Scripts installed to $SCRIPTS_DIR"

# --- Update settings.json ---
if [ ! -f "$SETTINGS" ]; then
  echo '{}' > "$SETTINGS"
fi

# Backup
cp "$SETTINGS" "${SETTINGS}.bak-$(date +%Y%m%d%H%M%S)"

# Merge new config using Python (avoids jq for complex nested merges)
/usr/bin/python3 - "$SETTINGS" << 'PYEOF'
import json, sys

path = sys.argv[1]
with open(path) as f:
    d = json.load(f)

hooks = d.setdefault("hooks", {})

new_hooks = {
    "SessionStart": [{"matcher": "", "hooks": [{"type": "command", "command": "~/.claude/scripts/session_start.sh"}]}],
    "Stop":         [{"hooks": [{"type": "command", "command": "~/.claude/scripts/dynamic_task_update.sh"}]}],
    "TaskCompleted":[{"hooks": [{"type": "command", "command": "~/.claude/scripts/task_completed.sh"}]}],
    "SessionEnd":   [{"matcher": "", "hooks": [{"type": "command", "command": "~/.claude/scripts/session_end.sh"}]}],
}

for event, config in new_hooks.items():
    if event not in hooks:
        hooks[event] = config

if "statusLine" not in d:
    d["statusLine"] = {"type": "command", "command": "~/.claude/scripts/session_statusline.sh"}

with open(path, "w") as f:
    json.dump(d, f, indent=2)
    f.write("\n")

print("settings.json updated")
PYEOF

echo ""
echo "Done. Open a new Claude Code session to see live task tracking in the statusline."
echo "Use /task <description> to manually set a session task."
