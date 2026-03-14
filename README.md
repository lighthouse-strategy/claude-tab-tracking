# claude-tab-tracking

[中文文档](README_CN.md)

> Know what every Claude Code session is doing — at a glance.

![demo](assets/demo.gif)

Live task tracking for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Shows what each session is working on — updated automatically as the conversation progresses.

If you run multiple Claude Code sessions simultaneously, this tells you at a glance what each one is doing.

## What it looks like

```
[WIP]  Fix authentication bug in api/routes.py
[DONE] Deploy model to production server
       my-project  |  ctx 14%  |  23min
```

**Status badges:**
- `[---]` — session just started, showing directory and git branch
- `[WIP]` — task in progress, auto-updated each turn
- `[DONE]` — task completed (detected automatically)
- `[SET]` — task manually set with `/task`

When you finish one task and start another, the previous task stays visible as a dimmed `[DONE]` line beneath the current task.

## How it works

Four Claude Code hooks work together:

| Hook | What it does |
|------|-------------|
| `SessionStart` | Writes `dir [branch]` as initial task label |
| `Stop` | After each assistant response: reads transcript, updates task description, detects completion |
| `TaskCompleted` | Marks task as `[DONE]` when Claude explicitly completes a task |
| `SessionEnd` | Cleans up session state files |

The statusline script reads the task file for the current session and renders the display.

### Summarization backends (auto-detected, no config required)

The plugin picks the best available backend automatically:

| Priority | Backend | Quality | Cost |
|----------|---------|---------|------|
| 1 | Claude API (`ANTHROPIC_API_KEY` set) | Best | ~$1/month |
| 2 | Ollama (local model running) | Good | Free |
| 3 | Keyword heuristics | Basic | Free |

No setup needed — it works out of the box. Set `ANTHROPIC_API_KEY` in your environment for the best results.

## Install

Requires [jq](https://jqlang.github.io/jq/):
```bash
brew install jq  # macOS
apt install jq   # Debian/Ubuntu
```

Then:
```bash
git clone https://github.com/lighthouse-strategy/claude-tab-tracking.git
cd claude-tab-tracking && ./install.sh
```

Open a new Claude Code session — the statusline appears immediately.

## Manual task override

Use the `/task` slash command to set a custom description for the current session:

```
/task Reviewing Q1 strategy report
```

This writes a `MANUAL:` prefix that pins the description and stops auto-updates for this session. The badge shows `[SET]`.

## Files installed

| File | Purpose |
|------|---------|
| `~/.claude/scripts/session_start.sh` | SessionStart hook |
| `~/.claude/scripts/dynamic_task_update.sh` | Stop hook (bash wrapper) |
| `~/.claude/scripts/dynamic_task_update.py` | Stop hook (transcript parser + LLM summarization) |
| `~/.claude/scripts/task_completed.sh` | TaskCompleted hook |
| `~/.claude/scripts/session_statusline.sh` | Statusline renderer |
| `~/.claude/scripts/session_end.sh` | SessionEnd cleanup |
| `~/.claude/commands/task.md` | `/task` slash command |
| `~/.claude/session-tasks/` | Session state (auto-cleaned after 7 days) |

## Uninstall

```bash
rm -f ~/.claude/scripts/session_start.sh \
      ~/.claude/scripts/dynamic_task_update.sh \
      ~/.claude/scripts/dynamic_task_update.py \
      ~/.claude/scripts/task_completed.sh \
      ~/.claude/scripts/session_statusline.sh \
      ~/.claude/scripts/session_end.sh \
      ~/.claude/commands/task.md
rm -rf ~/.claude/session-tasks/
```

Then remove the `SessionStart`, `Stop`, `TaskCompleted`, `SessionEnd` entries from the `hooks` section of `~/.claude/settings.json`, and remove the `statusLine` key.

## Author

Built by [lh-strategy](https://github.com/lh-strategy)

## License

MIT
