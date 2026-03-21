---
description: "Load past conversation memos into context"
---

Load past conversation memos from `~/.claude/memos/` into the current conversation context.

When this command is invoked:

1. **No argument** (`/recall`):
   - Scan `~/.claude/memos/` for project directories (skip `_archive`)
   - For each project, find the most recent `.md` file and count entries (lines starting with `## `)
   - Sort by most recent activity
   - Show a numbered list:
     ```
     Recent projects:
     1. chenglue-agents (today, 3 entries)
     2. alpha-station (3-20, 5 entries)
     3. claude-tab-tracking (3-19, 2 entries)
     ```
   - Ask: "Which project? (number or name)"
   - After user picks a project, list recent dates:
     ```
     chenglue-agents memos:
     1. 2026-03-21 — 3 entries
     2. 2026-03-20 — 5 entries
     3. 2026-03-19 — 2 entries
     ```
   - Ask: "Which date? (number, or multiple like 1,2)"
   - Read the selected file(s) and present the content

2. **Project name argument** (`/recall chenglue-agents`):
   - Skip to the date selection step for that project

3. **Date argument** (`/recall 3-20`):
   - Convert to `YYYY-MM-DD`, read all project memos for that date
   - Present the content directly

Use AskUserQuestion for the interactive selection steps.
