# Plugin Description

**Name:** claude-tab-tracking
**Category:** Productivity / Session Management
**Platform:** Claude Code (macOS / Linux)
**Dependencies:** jq, Python 3 (built-in on macOS/Linux)

---

## Problem

Power users of Claude Code often run 4–5 sessions simultaneously across different projects. After switching windows or stepping away, it becomes hard to remember what each session was working on. There is no built-in way to see a summary of each session's current task.

## Solution

`claude-tab-tracking` adds a persistent two-line statusline at the bottom of every Claude Code session that shows:

1. **Task status** — what the session is currently doing, updated after every assistant response
2. **Session info** — working directory, context window usage (%), and session duration

The task description is generated semantically (via Claude API or local Ollama) rather than just copying the last user message, so it stays meaningful even when prompts are short ("continue", "ok", "next step").

## Key Features

- **Zero-config** — works immediately after install, no API keys required
- **Auto-updating** — task description evolves as the conversation progresses
- **Completion detection** — automatically switches to `[DONE]` when a task finishes
- **Smart backend selection** — uses Claude API if available, falls back to Ollama, then keyword matching
- **Manual override** — `/task <description>` pins a custom description for the session
- **Multi-session aware** — each session tracks its own task independently using Claude Code's `session_id`
- **Self-cleaning** — session state files are purged after 7 days

## Technical Design

The plugin uses four Claude Code lifecycle hooks:

```
SessionStart  →  registers session, writes "dir [branch]" as placeholder
UserPromptSubmit  →  (removed; SessionStart handles initialization)
Stop          →  reads transcript JSONL, calls LLM for semantic summary,
                  detects task completion, writes WIP:/DONE: to task file
TaskCompleted →  strong completion signal, immediately writes DONE:
SessionEnd    →  cleans up cwd-indexed lookup file
```

Session state is stored in `~/.claude/session-tasks/`:
- `{session_id}.txt` — task description with prefix (`WIP:` / `DONE:` / `MANUAL:` / `INIT:`)
- `current_{cwd_hash}.txt` — maps working directory → session_id (for `/task` command)

The statusline script is a separate process run by Claude Code after each interaction. It reads the task file for the current `session_id` (provided in the JSON stdin) and renders the two-line display using ANSI color codes.

## Statusline Format

```
[WIP]  Fix authentication bug in api/routes.py     ← Line 1: badge + task
       backend  |  ctx 23%  |  42min               ← Line 2: dir + context + duration
```

Badge colors:
- `[---]` dim — session initializing (showing dir + branch)
- `[WIP]` yellow — task in progress
- `[DONE]` green — task completed
- `[SET]` bold — manually set via `/task`

Context % turns yellow above 50% and red above 80% as a warning.

## Summarization Quality

| Backend | Example output |
|---------|---------------|
| Claude Haiku | "Fix thread-safety bug in yfinance download wrapper" |
| Ollama qwen3.5:4b | "修复 yfinance 下载线程安全问题" |
| Keyword fallback | "yfinance download 不是线程安全的，需要加全局锁" |
