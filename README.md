# claude-tab-tracking

Live task tracking for [Claude Code](https://code.claude.com). Shows what each session is working on — updated automatically as the conversation progresses.

If you run multiple Claude Code sessions simultaneously, this tells you at a glance what each one is doing.

## What it looks like

```
[WIP] Fix Model-B data pollution bug in core/data.py
      risk-monitor  |  ctx 14%  |  23min

[DONE] Deploy Model-A model to VPS
       risk-monitor  |  ctx 61%  |  1h12m

[---]  my-quant-project  [feature/signal-v2]
       my-quant-project   |  ctx 2%   |  0min
```

**Status badges:**
- `[---]` — session just started, showing directory and git branch
- `[WIP]` — task in progress, auto-updated each turn
- `[DONE]` — task completed (detected automatically)
- `[SET]` — task manually set with `/task`

## How it works

Four Claude Code hooks work together:

| Hook | What it does |
|------|-------------|
| `SessionStart` | Writes `dir [branch]` as initial task label |
| `Stop` | After each assistant response: reads transcript, updates task description, detects completion |
| `TaskCompleted` | Marks task as `[DONE]` when Claude explicitly completes a task |
| `SessionEnd` | Cleans up session state files |

The statusline script reads the task file for the current session and renders two lines: task status on line 1, directory + context usage + session duration on line 2.

**Completion detection** — the `Stop` hook scans the assistant's last message for completion signals (e.g. "fixed", "all tests pass", "deployed", "完成"). Two or more signals trigger a `[DONE]` transition.

## Install

Requires [jq](https://jqlang.github.io/jq/):
```bash
brew install jq  # macOS
```

Then:
```bash
git clone https://github.com/lh-strategy/claude-tab-tracking.git
cd claude-tab-tracking
chmod +x install.sh
./install.sh
```

Open a new Claude Code session — the statusline appears immediately.

## Manual task override

Use the `/task` slash command to set a custom description for the current session:

```
/task Reviewing Q1 strategy report
```

This writes a `MANUAL:` prefix that pins the description and stops the auto-update for this session.

## Files installed

| File | Purpose |
|------|---------|
| `~/.claude/scripts/session_start.sh` | SessionStart hook |
| `~/.claude/scripts/dynamic_task_update.sh` | Stop hook (bash wrapper) |
| `~/.claude/scripts/dynamic_task_update.py` | Stop hook (transcript parser) |
| `~/.claude/scripts/task_completed.sh` | TaskCompleted hook |
| `~/.claude/scripts/session_statusline.sh` | Statusline renderer |
| `~/.claude/scripts/session_end.sh` | SessionEnd cleanup |
| `~/.claude/commands/task.md` | `/task` slash command |
| `~/.claude/session-tasks/` | Session state (auto-cleaned after 7 days) |

## Uninstall

Remove the scripts and revert `~/.claude/settings.json` entries manually, or run:

```bash
# Remove scripts
rm -f ~/.claude/scripts/session_start.sh \
      ~/.claude/scripts/dynamic_task_update.sh \
      ~/.claude/scripts/dynamic_task_update.py \
      ~/.claude/scripts/task_completed.sh \
      ~/.claude/scripts/session_statusline.sh \
      ~/.claude/scripts/session_end.sh \
      ~/.claude/commands/task.md

# Remove session state
rm -rf ~/.claude/session-tasks/
```

Then remove the `SessionStart`, `Stop`, `TaskCompleted`, `SessionEnd` entries from the `hooks` section of `~/.claude/settings.json`, and remove the `statusLine` key.

## License

MIT
