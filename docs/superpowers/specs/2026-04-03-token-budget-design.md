# Token Budget System Design

## Problem

Long Claude Code sessions with `/recall` can inject large memo files into context, causing excessive token consumption. A single day's memo can reach 13,000+ tokens (e.g., 118 entries in chenglue-agents/2026-03-23). Combined with long conversations (1000+ messages), early-loaded memos compound token costs across every subsequent turn.

Additionally, memo generation produces redundant entries — the same task recorded 2-3 times within minutes with near-identical content.

## Goals

1. Cap token injection from `/recall` with a configurable budget
2. Reduce memo file bloat by merging similar consecutive entries at write time
3. Centralize configuration in `~/.claude/memos/config.yaml`
4. Maintain backward compatibility — no breaking changes for existing users

## Design

### Part 1: Memo Deduplication (write_memo改造)

**File:** `scripts/dynamic_task_update.py` — `write_memo()` function

**Behavior change:** Before appending a new memo entry, read the last entry from today's memo file. If it meets both merge criteria, merge instead of append.

**Merge criteria (both must be true):**
- Time delta: last entry timestamp is within `memo_merge_window` seconds (default: 300s / 5min)
- Title similarity: word-overlap ratio between old and new title exceeds `memo_merge_threshold` (default: 0.6)

**Similarity function:**
```python
def title_similarity(a: str, b: str) -> float:
    """Word-overlap ratio between two titles (Jaccard on word tokens)."""
    words_a = set(re.findall(r'\w+', a.lower()))
    words_b = set(re.findall(r'\w+', b.lower()))
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)
```

**Merge behavior:**
- Keep the newer entry's title (more refined after further work)
- Union of all bullet points from both entries, deduplicated by exact match
- Keep the newer entry's timestamp

**Example — before (current behavior):**
```markdown
## 00:03 | Phase 3 Preset系统开发已完成并测试通过 [完成]
- 【决策】Switch to JWT tokens
- 【结论】Root cause: cache expiration

## 00:03 | Phase 3 Preset系统开发已完成 [完成]
- 【决策】Switch to JWT tokens
- 【数据】Affects 3 API endpoints
```

**Example — after (merged):**
```markdown
## 00:03 | Phase 3 Preset系统开发已完成并测试通过 [完成]
- 【决策】Switch to JWT tokens
- 【结论】Root cause: cache expiration
- 【数据】Affects 3 API endpoints
```

**Implementation notes:**
- Parse last entry by reading file backward until finding the previous `## ` header
- File locking (existing fcntl mechanism) remains unchanged
- If merge window is 0, skip merge logic entirely (opt-out)

### Part 2: Recall Token Budget

**File:** `commands/recall.md` — command definition for Claude Code

**Token estimation function (inline, no separate module):**
```python
def estimate_tokens(text: str) -> int:
    """Rough token estimate for mixed Chinese/English text."""
    return int(len(text) / 1.5)
```

**Three-tier loading strategy:**

1. **Full mode** — estimated tokens <= budget: load entire file as-is
2. **Summary mode** — full exceeds budget: load only `## ` header lines + lines containing 【结论】tag
3. **Truncated mode** — summary still exceeds budget: load summary entries from newest to oldest until budget exhausted

**User feedback** (displayed before loaded content):
```
Loading chenglue-agents/2026-03-23.md
Full content ~13,400 tokens, exceeds budget (8,000)
-> Switched to summary mode: 118 entries (titles + conclusions, ~6,300 tokens)
```

**On-demand expansion:** If user asks to see full details of a specific entry, Claude reads that section with the Read tool. This keeps the initial load within budget.

**Command parameter override:**
- `/recall --budget 4000` overrides config.yaml for this invocation
- `/recall --full` disables budget (loads everything, for when user explicitly wants it)

### Part 3: config.yaml

**File:** `~/.claude/memos/config.yaml`

**New keys (added to existing config structure):**
```yaml
# --- Existing keys ---
tags:
  - 决策
  - 数据
  - 结论
  - TODO
min_turns: 3
archive_days: 90
ollama_timeout: 15

# --- New keys (token budget system) ---
recall_token_budget: 8000    # Max tokens per /recall load. 0 = unlimited
memo_merge_window: 300       # Seconds. Merge similar entries within this window. 0 = disabled
memo_merge_threshold: 0.6    # Title similarity threshold for merge (0.0-1.0)
```

**Defaults** (when config.yaml doesn't exist or keys are missing):
- `recall_token_budget`: 8000
- `memo_merge_window`: 300
- `memo_merge_threshold`: 0.6

**Config loading change:** Extend `load_memo_config()` to parse the three new keys with the same pattern as existing keys (simple key:value YAML parsing).

## Files Changed

| File | Change |
|------|--------|
| `scripts/dynamic_task_update.py` | Add `title_similarity()`, modify `write_memo()` to merge similar entries, extend `load_memo_config()` for new keys |
| `commands/recall.md` | Add token budget logic, three-tier loading, `--budget` and `--full` flags |
| `README.md` | Document new config keys and recall flags |
| `README_CN.md` | Same in Chinese |
| `tests/test_task_update.py` | Tests for merge logic, similarity function, config parsing |

## Non-Goals

- No separate `token_budget.py` module — two call sites don't justify the abstraction
- No real tokenizer (tiktoken etc.) — `len(text)/1.5` is sufficient for budget gating
- No changes to SessionStart hook or statusline rendering
- No retroactive cleanup of existing large memo files
