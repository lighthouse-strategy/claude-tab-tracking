# Token Budget System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a token budget system that limits /recall context injection and deduplicates memo entries at write time.

**Architecture:** Extend `write_memo()` with a merge-before-append check, extend `load_memo_config()` with 3 new keys, and update `recall.md` to enforce token budgets with three-tier loading. No new files beyond tests.

**Tech Stack:** Python 3, pytest, existing YAML config parser

---

### Task 1: Add title_similarity() and config parsing for new keys

**Files:**
- Modify: `scripts/dynamic_task_update.py:43-94` (DEFAULT_CONFIG + load_memo_config)
- Test: `tests/test_task_update.py`

- [ ] **Step 1: Write failing tests for title_similarity**

Add to `tests/test_task_update.py`:

```python
# ---------------------------------------------------------------------------
# Tests for title_similarity
# ---------------------------------------------------------------------------

from dynamic_task_update import title_similarity


def test_similarity_identical():
    assert title_similarity("修复登录页验证", "修复登录页验证") == 1.0


def test_similarity_completely_different():
    assert title_similarity("Fix auth bug", "Deploy to production") < 0.2


def test_similarity_partial_overlap():
    score = title_similarity(
        "Phase 3 Preset系统开发已完成并测试通过",
        "Phase 3 Preset系统开发已完成"
    )
    assert score > 0.6


def test_similarity_empty_strings():
    assert title_similarity("", "") == 0.0
    assert title_similarity("hello", "") == 0.0
    assert title_similarity("", "world") == 0.0


def test_similarity_case_insensitive():
    assert title_similarity("Fix Auth Bug", "fix auth bug") == 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/xinguanying/claude-tab-tracking && uv run python -m pytest tests/test_task_update.py::test_similarity_identical -v --timeout=60 -x`
Expected: FAIL with `ImportError: cannot import name 'title_similarity'`

- [ ] **Step 3: Implement title_similarity**

Add to `scripts/dynamic_task_update.py` after the `load_memo_config` function (after line 94):

```python
def title_similarity(a: str, b: str) -> float:
    """Word-overlap ratio between two titles (Jaccard on word tokens)."""
    words_a = set(re.findall(r'\w+', a.lower()))
    words_b = set(re.findall(r'\w+', b.lower()))
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)
```

- [ ] **Step 4: Run title_similarity tests to verify they pass**

Run: `cd /Users/xinguanying/claude-tab-tracking && uv run python -m pytest tests/test_task_update.py -k "similarity" -v --timeout=60 -x`
Expected: All 5 similarity tests PASS

- [ ] **Step 5: Write failing tests for new config keys**

Add to `tests/test_task_update.py`:

```python
# ---------------------------------------------------------------------------
# Tests for new config keys (token budget)
# ---------------------------------------------------------------------------


def test_load_config_token_budget_defaults(tmp_path):
    """Default config should have token budget keys."""
    config = load_memo_config(str(tmp_path / 'nonexistent.yaml'))
    assert config['recall_token_budget'] == 8000
    assert config['memo_merge_window'] == 300
    assert config['memo_merge_threshold'] == 0.6


def test_load_config_token_budget_custom(tmp_path):
    """load_memo_config should parse new token budget keys."""
    config_file = tmp_path / 'config.yaml'
    config_file.write_text(
        'recall_token_budget: 4000\n'
        'memo_merge_window: 600\n'
        'memo_merge_threshold: 0.8\n'
    )
    config = load_memo_config(str(config_file))
    assert config['recall_token_budget'] == 4000
    assert config['memo_merge_window'] == 600
    assert config['memo_merge_threshold'] == 0.8


def test_load_config_token_budget_partial(tmp_path):
    """Missing new keys should fall back to defaults."""
    config_file = tmp_path / 'config.yaml'
    config_file.write_text('recall_token_budget: 5000\n')
    config = load_memo_config(str(config_file))
    assert config['recall_token_budget'] == 5000
    assert config['memo_merge_window'] == 300  # default
    assert config['memo_merge_threshold'] == 0.6  # default


def test_load_config_merge_disabled(tmp_path):
    """memo_merge_window: 0 should be parsed as 0 (disabled)."""
    config_file = tmp_path / 'config.yaml'
    config_file.write_text('memo_merge_window: 0\n')
    config = load_memo_config(str(config_file))
    assert config['memo_merge_window'] == 0
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `cd /Users/xinguanying/claude-tab-tracking && uv run python -m pytest tests/test_task_update.py::test_load_config_token_budget_defaults -v --timeout=60 -x`
Expected: FAIL with `KeyError: 'recall_token_budget'`

- [ ] **Step 7: Add new keys to DEFAULT_CONFIG and load_memo_config**

In `scripts/dynamic_task_update.py`, update `DEFAULT_CONFIG` (line 43):

```python
DEFAULT_CONFIG = {
    'tags': ['决策', '数据', '结论', 'TODO'],
    'min_turns': 3,
    'archive_days': 90,
    'ollama_timeout': 15,
    'recall_token_budget': 8000,
    'memo_merge_window': 300,
    'memo_merge_threshold': 0.6,
}
```

In `load_memo_config()`, add parsing for the new keys inside the `if ':' in stripped:` block (after the `ollama_timeout` elif around line 88):

```python
                elif key == 'recall_token_budget' and val.isdigit():
                    config['recall_token_budget'] = int(val)
                elif key == 'memo_merge_window' and val.isdigit():
                    config['memo_merge_window'] = int(val)
                elif key == 'memo_merge_threshold':
                    try:
                        config['memo_merge_threshold'] = float(val)
                    except ValueError:
                        pass
```

- [ ] **Step 8: Run all config tests to verify they pass**

Run: `cd /Users/xinguanying/claude-tab-tracking && uv run python -m pytest tests/test_task_update.py -k "config" -v --timeout=60 -x`
Expected: All config tests PASS (existing + 4 new)

- [ ] **Step 9: Commit**

```bash
cd /Users/xinguanying/claude-tab-tracking
git add scripts/dynamic_task_update.py tests/test_task_update.py
git commit -m "feat: add title_similarity() and config keys for token budget system"
```

---

### Task 2: Add memo merge logic to write_memo()

**Files:**
- Modify: `scripts/dynamic_task_update.py:528-569` (write_memo function)
- Test: `tests/test_task_update.py`

- [ ] **Step 1: Write failing tests for memo merging**

Add to `tests/test_task_update.py`:

```python
# ---------------------------------------------------------------------------
# Tests for memo merge (write_memo deduplication)
# ---------------------------------------------------------------------------


def test_write_memo_merges_similar_within_window(tmp_path):
    """Two similar memos within merge window should be merged."""
    memo_dir = tmp_path / "memos"
    write_memo('【决策】Switch to JWT', 'Phase 3 Preset系统开发已完成', 'proj', str(memo_dir))
    write_memo('【数据】Affects 3 endpoints', 'Phase 3 Preset系统开发已完成并测试通过', 'proj', str(memo_dir))

    today = datetime.now().strftime('%Y-%m-%d')
    content = (memo_dir / 'proj' / f'{today}.md').read_text()
    # Should have only ONE ## header (merged), not two
    headers = [l for l in content.splitlines() if l.startswith('## ')]
    assert len(headers) == 1
    # Merged entry should have both bullet points
    assert '【决策】Switch to JWT' in content
    assert '【数据】Affects 3 endpoints' in content
    # Title should be the newer one
    assert 'Phase 3 Preset系统开发已完成并测试通过' in headers[0]


def test_write_memo_no_merge_different_titles(tmp_path):
    """Memos with different titles should NOT be merged."""
    memo_dir = tmp_path / "memos"
    write_memo('【决策】改用 JWT', '修复登录页验证', 'proj', str(memo_dir))
    write_memo('【数据】新增 10 个 API', '开发支付模块', 'proj', str(memo_dir))

    today = datetime.now().strftime('%Y-%m-%d')
    content = (memo_dir / 'proj' / f'{today}.md').read_text()
    headers = [l for l in content.splitlines() if l.startswith('## ')]
    assert len(headers) == 2


def test_write_memo_no_merge_when_disabled(tmp_path):
    """When memo_merge_window=0, merging should be disabled."""
    memo_dir = tmp_path / "memos"
    config = dict(DEFAULT_CONFIG)
    config['memo_merge_window'] = 0
    write_memo('【决策】First', 'Same task name', 'proj', str(memo_dir), merge_config=config)
    write_memo('【数据】Second', 'Same task name', 'proj', str(memo_dir), merge_config=config)

    today = datetime.now().strftime('%Y-%m-%d')
    content = (memo_dir / 'proj' / f'{today}.md').read_text()
    headers = [l for l in content.splitlines() if l.startswith('## ')]
    assert len(headers) == 2


def test_write_memo_deduplicates_bullets(tmp_path):
    """Merged entry should not have duplicate bullet points."""
    memo_dir = tmp_path / "memos"
    write_memo('【决策】改用 JWT | 【结论】测试通过', 'Same task', 'proj', str(memo_dir))
    write_memo('【决策】改用 JWT | 【数据】3 endpoints', 'Same task', 'proj', str(memo_dir))

    today = datetime.now().strftime('%Y-%m-%d')
    content = (memo_dir / 'proj' / f'{today}.md').read_text()
    # 【决策】改用 JWT should appear only once
    assert content.count('【决策】改用 JWT') == 1
    assert '【结论】测试通过' in content
    assert '【数据】3 endpoints' in content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/xinguanying/claude-tab-tracking && uv run python -m pytest tests/test_task_update.py::test_write_memo_merges_similar_within_window -v --timeout=60 -x`
Expected: FAIL (currently write_memo always appends, producing 2 headers)

- [ ] **Step 3: Implement memo merge logic**

Rewrite `write_memo()` in `scripts/dynamic_task_update.py`. Replace the existing function (lines 528-569) with:

```python
def _parse_last_entry(memo_file):
    """Parse the last entry from a memo file. Returns (header_line_idx, time_str, title, bullets, all_lines) or None."""
    if not os.path.exists(memo_file):
        return None
    with open(memo_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    last_header_idx = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip().startswith('## '):
            last_header_idx = i
            break
    if last_header_idx is None:
        return None
    header = lines[last_header_idx].strip()
    m = re.match(r'^##\s+(\d{1,2}:\d{2})\s*\|\s*(.*)$', header)
    if not m:
        return None
    time_str = m.group(1)
    title = m.group(2).strip()
    bullets = []
    for line in lines[last_header_idx + 1:]:
        stripped = line.strip()
        if stripped.startswith('- '):
            bullets.append(stripped)
    return last_header_idx, time_str, title, bullets, lines


def write_memo(memo_content, task_desc, project_name, memo_base_dir=None, merge_config=None):
    """Append a memo entry to the project's daily memo file.

    If the last entry is similar and recent, merges instead of appending.
    Uses fcntl file locking (Unix) to prevent interleaved writes.
    """
    if not memo_content:
        return
    if memo_base_dir is None:
        memo_base_dir = MEMO_BASE_DIR
    if merge_config is None:
        merge_config = DEFAULT_CONFIG

    merge_window = merge_config.get('memo_merge_window', 300)
    merge_threshold = merge_config.get('memo_merge_threshold', 0.6)

    today = datetime.now().strftime('%Y-%m-%d')
    time_str = datetime.now().strftime('%H:%M')
    project_dir = os.path.join(memo_base_dir, project_name)
    os.makedirs(project_dir, exist_ok=True)
    memo_file = os.path.join(project_dir, f'{today}.md')

    new_items = [item.strip() for item in memo_content.split('|') if item.strip()]
    new_bullets = [f'- {item}' for item in new_items]

    def _do_write():
        merged = False
        if merge_window > 0:
            parsed = _parse_last_entry(memo_file)
            if parsed is not None:
                header_idx, last_time, last_title, last_bullets, all_lines = parsed
                # Check time window
                try:
                    now_minutes = int(time_str.split(':')[0]) * 60 + int(time_str.split(':')[1])
                    last_minutes = int(last_time.split(':')[0]) * 60 + int(last_time.split(':')[1])
                    delta_seconds = abs(now_minutes - last_minutes) * 60
                except (ValueError, IndexError):
                    delta_seconds = 9999
                # Check similarity
                if delta_seconds <= merge_window and title_similarity(last_title, task_desc) >= merge_threshold:
                    # Merge: replace last entry with combined content
                    existing_bullet_texts = set(last_bullets)
                    merged_bullets = list(last_bullets)
                    for b in new_bullets:
                        if b not in existing_bullet_texts:
                            merged_bullets.append(b)
                    # Rebuild file: everything before last entry + merged entry
                    new_header = f'## {time_str} | {task_desc}\n'
                    with open(memo_file, 'w', encoding='utf-8') as f:
                        for line in all_lines[:header_idx]:
                            f.write(line)
                        f.write(f'\n{new_header}')
                        for b in merged_bullets:
                            f.write(f'{b}\n')
                    merged = True

        if not merged:
            entry_lines = [f'\n## {time_str} | {task_desc}']
            for b in new_bullets:
                entry_lines.append(b)
            entry_lines.append('')
            if not os.path.exists(memo_file):
                with open(memo_file, 'w', encoding='utf-8') as f:
                    f.write(f'# {today}\n')
                    f.write('\n'.join(entry_lines))
            else:
                with open(memo_file, 'a', encoding='utf-8') as f:
                    f.write('\n'.join(entry_lines))

    if HAS_FCNTL:
        lock_path = memo_file + '.lock'
        with open(lock_path, 'w') as lock_f:
            try:
                fcntl.flock(lock_f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                return
            _do_write()
            fcntl.flock(lock_f, fcntl.LOCK_UN)
    else:
        _do_write()
```

- [ ] **Step 4: Run merge tests to verify they pass**

Run: `cd /Users/xinguanying/claude-tab-tracking && uv run python -m pytest tests/test_task_update.py -k "merge" -v --timeout=60 -x`
Expected: All 4 merge tests PASS

- [ ] **Step 5: Run full test suite to verify no regressions**

Run: `cd /Users/xinguanying/claude-tab-tracking && uv run python -m pytest tests/test_task_update.py -v --timeout=60 -x`
Expected: All existing + new tests PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/xinguanying/claude-tab-tracking
git add scripts/dynamic_task_update.py tests/test_task_update.py
git commit -m "feat: add memo merge logic to deduplicate similar entries within time window"
```

---

### Task 3: Wire merge_config into main()

**Files:**
- Modify: `scripts/dynamic_task_update.py:654-738` (main function)
- Modify: `scripts/cli_background.py` (pass merge_config to write_memo)

- [ ] **Step 1: Update main() to pass merge_config to write_memo**

In `scripts/dynamic_task_update.py`, modify the `write_memo` call in `main()` (around line 733):

```python
    if memo_content:
        cwd = os.environ.get('PWD', os.getcwd())
        project = resolve_project_name(cwd)
        write_memo(memo_content, task_desc, project, merge_config=memo_config)
```

- [ ] **Step 2: Update cli_background.py to load config and pass merge_config**

Read `scripts/cli_background.py` first, then modify its `main()` to load the memo config and pass `merge_config` to `write_memo`. The key change: after `write_memo(memo, task, project, memo_base_dir)` add `merge_config=load_memo_config()`.

- [ ] **Step 3: Run full test suite**

Run: `cd /Users/xinguanying/claude-tab-tracking && uv run python -m pytest tests/test_task_update.py -v --timeout=60 -x`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
cd /Users/xinguanying/claude-tab-tracking
git add scripts/dynamic_task_update.py scripts/cli_background.py
git commit -m "feat: wire merge_config into main() and cli_background"
```

---

### Task 4: Add estimate_tokens() and update recall.md with token budget

**Files:**
- Modify: `scripts/dynamic_task_update.py` (add estimate_tokens function)
- Modify: `commands/recall.md`
- Test: `tests/test_task_update.py`

- [ ] **Step 1: Write failing tests for estimate_tokens**

Add to `tests/test_task_update.py`:

```python
# ---------------------------------------------------------------------------
# Tests for estimate_tokens
# ---------------------------------------------------------------------------

from dynamic_task_update import estimate_tokens


def test_estimate_tokens_english():
    text = "Hello world this is a test"
    tokens = estimate_tokens(text)
    assert 10 < tokens < 30


def test_estimate_tokens_chinese():
    text = "修复登录页验证并部署到生产环境"
    tokens = estimate_tokens(text)
    assert 5 < tokens < 30


def test_estimate_tokens_empty():
    assert estimate_tokens("") == 0


def test_estimate_tokens_large():
    """A 15KB text should estimate around 10,000 tokens."""
    text = "测试内容 " * 3000  # ~15KB
    tokens = estimate_tokens(text)
    assert 8000 < tokens < 12000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/xinguanying/claude-tab-tracking && uv run python -m pytest tests/test_task_update.py::test_estimate_tokens_english -v --timeout=60 -x`
Expected: FAIL with `ImportError: cannot import name 'estimate_tokens'`

- [ ] **Step 3: Implement estimate_tokens**

Add to `scripts/dynamic_task_update.py` after the `title_similarity` function:

```python
def estimate_tokens(text: str) -> int:
    """Rough token estimate for mixed Chinese/English text."""
    if not text:
        return 0
    return int(len(text) / 1.5)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/xinguanying/claude-tab-tracking && uv run python -m pytest tests/test_task_update.py -k "estimate_tokens" -v --timeout=60 -x`
Expected: All 4 tests PASS

- [ ] **Step 5: Write failing tests for summarize_memo_content**

Add to `tests/test_task_update.py`:

```python
# ---------------------------------------------------------------------------
# Tests for summarize_memo_content
# ---------------------------------------------------------------------------

from dynamic_task_update import summarize_memo_content


def test_summarize_keeps_headers_and_conclusions():
    content = """# 2026-03-23

## 08:00 | Fix auth bug
- 【决策】Switch to JWT
- 【数据】Affects 3 endpoints
- 【结论】Root cause was cache

## 09:00 | Deploy to prod
- 【决策】Blue-green deploy
- 【结论】Successful rollout
"""
    summary = summarize_memo_content(content)
    assert '## 08:00 | Fix auth bug' in summary
    assert '## 09:00 | Deploy to prod' in summary
    assert '【结论】Root cause was cache' in summary
    assert '【结论】Successful rollout' in summary
    # 【决策】and 【数据】 lines should be excluded in summary
    assert '【决策】Switch to JWT' not in summary
    assert '【数据】Affects 3 endpoints' not in summary


def test_summarize_empty():
    assert summarize_memo_content("") == ""
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `cd /Users/xinguanying/claude-tab-tracking && uv run python -m pytest tests/test_task_update.py::test_summarize_keeps_headers_and_conclusions -v --timeout=60 -x`
Expected: FAIL with `ImportError: cannot import name 'summarize_memo_content'`

- [ ] **Step 7: Implement summarize_memo_content**

Add to `scripts/dynamic_task_update.py` after `estimate_tokens`:

```python
def summarize_memo_content(content: str) -> str:
    """Extract headers and 【结论】lines from memo content for summary mode."""
    if not content:
        return ""
    lines = content.splitlines()
    summary_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('# ') or stripped.startswith('## ') or '【结论】' in stripped:
            summary_lines.append(line)
    return '\n'.join(summary_lines)
```

- [ ] **Step 8: Run all new tests**

Run: `cd /Users/xinguanying/claude-tab-tracking && uv run python -m pytest tests/test_task_update.py -k "estimate_tokens or summarize_memo" -v --timeout=60 -x`
Expected: All 6 tests PASS

- [ ] **Step 9: Update recall.md with token budget logic**

Replace `commands/recall.md` with updated version that includes token budget instructions:

```markdown
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
```

- [ ] **Step 10: Run full test suite**

Run: `cd /Users/xinguanying/claude-tab-tracking && uv run python -m pytest tests/test_task_update.py -v --timeout=60 -x`
Expected: All tests PASS

- [ ] **Step 11: Commit**

```bash
cd /Users/xinguanying/claude-tab-tracking
git add scripts/dynamic_task_update.py commands/recall.md tests/test_task_update.py
git commit -m "feat: add token budget to /recall with three-tier loading strategy"
```

---

### Task 5: Update documentation (README + README_CN)

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md`

- [ ] **Step 1: Read current README files**

Read both `README.md` and `README_CN.md` to find the configuration section.

- [ ] **Step 2: Add token budget documentation to README.md**

In the configuration section, add:

```markdown
### Token Budget (v0.X.X+)

Control how much context `/recall` injects and how memo entries are deduplicated.

Add to `~/.claude/memos/config.yaml`:

```yaml
# Max tokens loaded per /recall invocation (default: 8000, 0 = unlimited)
recall_token_budget: 8000

# Merge similar memo entries within this window in seconds (default: 300, 0 = disabled)
memo_merge_window: 300

# Title similarity threshold for merging (0.0-1.0, default: 0.6)
memo_merge_threshold: 0.6
```

**Recall loading modes:**
- **Full**: file fits within budget → loaded as-is
- **Summary**: file exceeds budget → only headers + conclusions loaded
- **Truncated**: summary exceeds budget → most recent entries loaded up to budget

Override per-invocation: `/recall --budget 4000` or `/recall --full` (no limit).
```

- [ ] **Step 3: Add same section to README_CN.md in Chinese**

Add the equivalent Chinese documentation.

- [ ] **Step 4: Commit**

```bash
cd /Users/xinguanying/claude-tab-tracking
git add README.md README_CN.md
git commit -m "docs: add token budget configuration to README"
```

---

### Task 6: Final integration test

**Files:**
- Test: `tests/test_task_update.py`

- [ ] **Step 1: Write integration test for full memo lifecycle with merge**

Add to `tests/test_task_update.py`:

```python
# ---------------------------------------------------------------------------
# Integration test: memo lifecycle with merge
# ---------------------------------------------------------------------------


def test_memo_lifecycle_merge_and_summarize(tmp_path):
    """End-to-end: write multiple similar memos, verify merge, then summarize."""
    memo_dir = tmp_path / "memos"

    # Write 3 similar memos (should merge into 1)
    write_memo('【决策】Use Redis', 'Optimize caching layer', 'proj', str(memo_dir))
    write_memo('【数据】p99 reduced 40%', 'Optimize caching layer performance', 'proj', str(memo_dir))
    write_memo('【结论】Cache hit rate 95%', 'Optimize caching layer performance tuning', 'proj', str(memo_dir))

    # Write 1 different memo (should NOT merge)
    write_memo('【决策】Add rate limiter', 'Implement API rate limiting', 'proj', str(memo_dir))

    today = datetime.now().strftime('%Y-%m-%d')
    content = (memo_dir / 'proj' / f'{today}.md').read_text()

    # Should have exactly 2 entries
    headers = [l for l in content.splitlines() if l.startswith('## ')]
    assert len(headers) == 2

    # First entry (merged) should have all 3 bullets
    assert '【决策】Use Redis' in content
    assert '【数据】p99 reduced 40%' in content
    assert '【结论】Cache hit rate 95%' in content

    # Second entry should be separate
    assert '【决策】Add rate limiter' in content

    # Summarize should only keep headers + conclusions
    summary = summarize_memo_content(content)
    assert '## ' in summary
    assert '【结论】Cache hit rate 95%' in summary
    assert '【决策】Use Redis' not in summary  # decisions excluded from summary

    # Token estimate should be reasonable
    full_tokens = estimate_tokens(content)
    summary_tokens = estimate_tokens(summary)
    assert summary_tokens < full_tokens
```

- [ ] **Step 2: Run integration test**

Run: `cd /Users/xinguanying/claude-tab-tracking && uv run python -m pytest tests/test_task_update.py::test_memo_lifecycle_merge_and_summarize -v --timeout=60 -x`
Expected: PASS

- [ ] **Step 3: Run complete test suite one final time**

Run: `cd /Users/xinguanying/claude-tab-tracking && uv run python -m pytest tests/test_task_update.py -v --timeout=60 -x`
Expected: ALL tests PASS

- [ ] **Step 4: Commit**

```bash
cd /Users/xinguanying/claude-tab-tracking
git add tests/test_task_update.py
git commit -m "test: add integration test for memo merge + summarize lifecycle"
```
