---
description: "Load past conversation memos into context"
---

Load past conversation memos from `~/.claude/memos/` into the current conversation context.

## Token Budget

Before loading memo content, enforce a token budget to prevent excessive context injection.

1. Read config: `~/.claude/memos/config.yaml` key `recall_token_budget` (default: 8000)
2. If user passed `--budget N`, use N instead. If user passed `--full`, skip budget enforcement.
3. Estimate tokens of the target memo file(s) using `len(content) / 1.5`
4. Apply three-tier loading:
   - **Full mode**: estimated tokens <= budget → load entire file
   - **Summary mode**: full exceeds budget → load only lines starting with `# `, `## `, or containing `【结论】`
   - **Truncated mode**: summary still exceeds budget → load summary entries from end of file backward until budget is reached
5. Show the user which mode was used:
   ```
   Loading {project}/{date}.md
   Full content ~{N} tokens (budget: {budget})
   → Using {mode} mode ({actual} tokens loaded, {entries} entries)
   ```
6. If user wants to expand a specific entry, use Read tool on the memo file with offset/limit to read just that section.

## Selection Flow

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
     1. 2026-03-21 — 3 entries (~800 tokens)
     2. 2026-03-20 — 5 entries (~1200 tokens)
     3. 2026-03-19 — 2 entries (~400 tokens)
     ```
   - Ask: "Which date? (number, or multiple like 1,2)"
   - Read the selected file(s) and present content subject to token budget

2. **Project name argument** (`/recall chenglue-agents`):
   - Skip to the date selection step for that project

3. **Date argument** (`/recall 3-20`):
   - Convert to `YYYY-MM-DD`, read all project memos for that date
   - Present the content subject to token budget

4. **Budget override** (`/recall --budget 4000` or `/recall --full`):
   - `--budget N` overrides config recall_token_budget for this invocation
   - `--full` disables budget enforcement entirely

Use AskUserQuestion for the interactive selection steps.
