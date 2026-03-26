#!/bin/bash
# claude-tab-tracking uninstaller
# Removes hooks, scripts, and commands installed by install.sh.
# Does NOT remove user data (~/.claude/memos/, ~/.claude/session-tasks/).

set -euo pipefail

CLAUDE_DIR="$HOME/.claude"
SCRIPTS_DIR="$CLAUDE_DIR/scripts"
COMMANDS_DIR="$CLAUDE_DIR/commands"
SETTINGS="$CLAUDE_DIR/settings.json"

echo "Uninstalling claude-tab-tracking..."

# --- Check dependencies ---
if ! command -v python3 &>/dev/null; then
  echo "Error: python3 is required for settings.json cleanup."
  exit 1
fi

# --- Remove installed scripts ---
SCRIPT_FILES=(
  "claude_cli_common.py"
  "cli_background.py"
  "dynamic_task_update.py"
  "dynamic_task_update.sh"
  "session_end.sh"
  "session_start.sh"
  "session_statusline.sh"
  "task_completed.sh"
)

removed_scripts=0
for f in "${SCRIPT_FILES[@]}"; do
  target="$SCRIPTS_DIR/$f"
  if [ -f "$target" ]; then
    rm "$target"
    removed_scripts=$((removed_scripts + 1))
  fi
done
echo "Removed $removed_scripts script(s) from $SCRIPTS_DIR"

# --- Remove installed commands ---
COMMAND_FILES=("task.md" "memo.md" "recall.md")

removed_commands=0
for f in "${COMMAND_FILES[@]}"; do
  target="$COMMANDS_DIR/$f"
  if [ -f "$target" ]; then
    rm "$target"
    removed_commands=$((removed_commands + 1))
  fi
done
echo "Removed $removed_commands command(s) from $COMMANDS_DIR"

# --- Clean up settings.json (remove hooks and statusLine) ---
if [ -f "$SETTINGS" ]; then
  # Backup before modifying
  cp "$SETTINGS" "${SETTINGS}.bak-$(date +%Y%m%d%H%M%S)"

  python3 - "$SETTINGS" << 'PYEOF'
import json, sys

path = sys.argv[1]
try:
    with open(path) as f:
        d = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    print("Warning: could not parse settings.json, skipping hook removal.", file=sys.stderr)
    sys.exit(0)

# Commands registered by install.sh
OUR_COMMANDS = {
    "~/.claude/scripts/session_start.sh",
    "~/.claude/scripts/dynamic_task_update.sh",
    "~/.claude/scripts/task_completed.sh",
    "~/.claude/scripts/session_end.sh",
}

hooks = d.get("hooks", {})
changed = False

for event in list(hooks.keys()):
    rules = hooks[event]
    new_rules = []
    for rule in rules:
        new_hooks = [h for h in rule.get("hooks", []) if h.get("command", "") not in OUR_COMMANDS]
        if new_hooks:
            rule["hooks"] = new_hooks
            new_rules.append(rule)
        else:
            changed = True
    if new_rules:
        hooks[event] = new_rules
    else:
        del hooks[event]
        changed = True

# Remove statusLine if it points to our script
sl = d.get("statusLine", {})
if isinstance(sl, dict) and "session_statusline.sh" in sl.get("command", ""):
    del d["statusLine"]
    changed = True

if not hooks:
    d.pop("hooks", None)

if changed:
    with open(path, "w") as f:
        json.dump(d, f, indent=2)
        f.write("\n")
    print("Hooks and statusLine removed from settings.json")
else:
    print("No claude-tab-tracking hooks found in settings.json")
PYEOF
else
  echo "No settings.json found, skipping hook removal."
fi

# --- Warn about user data (do NOT delete) ---
echo ""
echo "User data preserved (not deleted):"
if [ -d "$CLAUDE_DIR/memos" ]; then
  echo "  $CLAUDE_DIR/memos/  (conversation memos)"
fi
if [ -d "$CLAUDE_DIR/session-tasks" ]; then
  echo "  $CLAUDE_DIR/session-tasks/  (session task files)"
fi
echo ""
echo "To remove user data manually:"
echo "  rm -rf ~/.claude/memos/ ~/.claude/session-tasks/"

echo ""
echo "Uninstall complete."
