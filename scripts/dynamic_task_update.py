#!/usr/bin/env python3
"""
Reads Claude Code transcript JSONL and generates a one-line task summary.

Summarization backends (set CLAUDE_TAB_BACKEND to choose):
  "auto"    — try all backends in order: claude-cli → api → ollama → keywords (default)
  "cli"     — Claude Code CLI only (uses your Max subscription, no API key needed)
  "api"     — Claude API only (requires ANTHROPIC_API_KEY)
  "ollama"  — Ollama only (requires local server on port 11434)
  "keyword" — keyword heuristics only (zero dependencies)

Updates task file with WIP:description or DONE:description.
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.request
from datetime import datetime


MEMO_BASE_DIR = os.path.join(str(pathlib.Path.home()), '.claude', 'memos')
MEMO_CONFIG_PATH = os.path.join(MEMO_BASE_DIR, 'config.yaml')

DEFAULT_CONFIG = {
    'tags': ['决策', '数据', '结论', 'TODO'],
    'min_turns': 3,
    'archive_days': 90,
}


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_memo_config(config_path=None):
    """Load memo config from YAML file. Returns dict with defaults for missing keys."""
    if config_path is None:
        config_path = MEMO_CONFIG_PATH
    config = dict(DEFAULT_CONFIG)
    config['tags_str'] = ''.join(f'【{t}】' for t in config['tags'])
    if not os.path.exists(config_path):
        return config
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        current_key = None
        tags = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if stripped == 'tags:':
                current_key = 'tags'
                continue
            if current_key == 'tags' and stripped.startswith('- '):
                tags.append(stripped[2:].strip())
                continue
            else:
                current_key = None
            if ':' in stripped:
                key, val = stripped.split(':', 1)
                key, val = key.strip(), val.strip()
                if key == 'min_turns' and val.isdigit():
                    config['min_turns'] = int(val)
                elif key == 'archive_days' and val.isdigit():
                    config['archive_days'] = int(val)
        if tags:
            config['tags'] = tags
        config['tags_str'] = ''.join(f'【{t}】' for t in config['tags'])
    except Exception:
        pass
    return config


# ---------------------------------------------------------------------------
# Shared prompt templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    'You are a concise task tracker. '
    'Based on the full conversation arc — including how the task evolved across multiple exchanges — '
    'summarize what is currently being worked on. '
    'IMPORTANT: When the user message contains ambiguous terms, '
    'use the assistant responses to determine the correct meaning. '
    'Output only the requested format — no explanations, no quotes, no extra punctuation.'
)

TASK_ONLY_TEMPLATE = """根据以下完整对话记录，综合判断当前正在进行的任务。请关注整体目标和对话走向，而不只是最后一条消息。
注意：如果用户用词有歧义，请根据 Claude 的实际回复内容来判断正确含义。

对话记录（含开头和最近内容）：
{conversation}

用一句话描述任务（中文25字以内，英文40字以内）。仅在任务明确完成时加 [完成] 前缀。
任务："""

MEMO_TEMPLATE = """根据以下完整对话记录，综合判断当前正在进行的任务，并提取关键信息。
注意：如果用户用词有歧义，请根据 Claude 的实际回复内容来判断正确含义。

对话记录（含开头和最近内容）：
{conversation}

请按以下格式输出两行：
第一行：用一句话描述任务（中文25字以内，英文40字以内）。仅在任务明确完成时加 [完成] 前缀。
第二行以"备忘："开头：提取对话中的关键信息，用 | 分隔，每条加标签前缀（{tags}）。如果没有值得记录的信息，省略第二行。

任务："""

DEFAULT_TAGS = '【决策】【数据】【结论】【TODO】'


def build_user_prompt(messages, min_turns=3, tags=None):
    """Build the user prompt, choosing task-only or task+memo based on turn count."""
    conversation = build_conversation_snippet(messages)
    if tags is None:
        tags = DEFAULT_TAGS
    if len(messages) < min_turns:
        return TASK_ONLY_TEMPLATE.format(conversation=conversation)
    return MEMO_TEMPLATE.format(conversation=conversation, tags=tags)


# ---------------------------------------------------------------------------
# Transcript parsing
# ---------------------------------------------------------------------------

def extract_text(content):
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get('type') == 'text':
                parts.append(block.get('text', ''))
        return ' '.join(parts).strip()
    return ''


def parse_transcript(path):
    """Parse transcript JSONL. Returns list of {'role', 'content'} dicts."""
    messages = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                role = content = None
                if obj.get('type') in ('user', 'assistant'):
                    role = obj['type']
                    content = extract_text(obj.get('message', obj).get('content', ''))
                elif obj.get('role') in ('user', 'assistant'):
                    role = obj['role']
                    content = extract_text(obj.get('content', ''))

                if not role or not content:
                    continue
                if role == 'user' and (content.startswith('/') or len(content) <= 3):
                    continue

                messages.append({'role': role, 'content': content})
    except Exception:
        pass
    return messages


def build_conversation_snippet(messages, max_exchanges=10):
    """
    Build a snippet that includes:
    - The first exchange (captures original intent)
    - The most recent exchanges (captures current state)
    This gives the LLM context on both where the task started and where it is now.
    """
    lines = []
    # Always include the first exchange to anchor the original task intent
    first_two = messages[:2]
    recent = messages[-(max_exchanges * 2):]
    # Merge, dedup by position
    combined_indices = set()
    combined = []
    for m in first_two + recent:
        idx = id(m)
        if idx not in combined_indices:
            combined_indices.add(idx)
            combined.append(m)
    # If first exchange is already in recent window, no separator needed
    show_separator = len(messages) > max_exchanges * 2 + 2
    for i, m in enumerate(combined):
        label = '用户' if m['role'] == 'user' else 'Claude'
        if show_separator and i == len(first_two):
            lines.append('...')
        lines.append(f"{label}: {m['content'][:300].replace(chr(10), ' ')}")
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Response parsing (shared by all LLM backends)
# ---------------------------------------------------------------------------

def parse_llm_response(response):
    """Extract (task_description, is_done, memo) from LLM output."""
    response = response.strip()
    lines = response.splitlines()

    # Extract memo line (备忘： or 备忘:)
    memo = ''
    task_lines = []
    for line in lines:
        m = re.match(r'^备忘[：:](.*)$', line.strip())
        if m:
            memo = m.group(1).strip()
        else:
            task_lines.append(line)

    # Reconstruct task text (first non-memo line)
    task_text = task_lines[0].strip() if task_lines else ''

    # Strip 任务： or 任务: prefix from task line
    task_text = re.sub(r'^任务[：:]\s*', '', task_text)

    is_done = bool(re.match(
        r'^(\[完成\]|完成\s|完成：|completed[: ]|\[done\])',
        task_text, re.IGNORECASE
    ))
    task = re.sub(
        r'^(\[完成\]\s*|完成\s+|完成：\s*|\[done\]\s*|completed:\s*)',
        '', task_text, flags=re.IGNORECASE
    ).strip()
    if len(task) > 60:
        task = task[:57] + '...'
    return task, is_done, memo


# ---------------------------------------------------------------------------
# Backend 0: Claude Code CLI (uses Max subscription, no API key needed)
# ---------------------------------------------------------------------------

CLAUDE_CLI_TIMEOUT = 60


def claude_cli_summarize(messages, task_file_path=None, min_turns=3, tags=None):
    """Call claude CLI in print mode, asynchronously.

    Because ``claude -p`` has ~30s startup overhead, this backend spawns the
    process in the background and writes the result to *task_file_path* when
    ready.  When *task_file_path* is provided (the normal path from main()),
    the function launches the helper and returns ``None`` so the caller skips
    synchronous writing.  When *task_file_path* is ``None`` (unit tests), it
    falls back to a blocking call.
    """
    user_content = build_user_prompt(messages, min_turns=min_turns, tags=tags)
    prompt = f"{SYSTEM_PROMPT}\n\n{user_content}"

    if task_file_path is None:
        # Synchronous path (for tests / direct invocation)
        result = subprocess.run(
            ['claude', '-p', '--model', 'haiku'],
            input=prompt,
            capture_output=True, text=True,
            timeout=CLAUDE_CLI_TIMEOUT,
        )
        if result.returncode != 0:
            raise RuntimeError(f'claude CLI exited with {result.returncode}')
        text = result.stdout.strip()
        if not text:
            raise ValueError('empty response from claude CLI')
        return parse_llm_response(text)

    # Async path — fire-and-forget background process
    _launch_cli_background(prompt, task_file_path)
    return None  # signal: handled async, caller should not write


_CLI_HELPER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cli_background.py')


def _launch_cli_background(prompt, task_file_path):
    """Spawn a detached process that calls claude CLI and writes the result."""
    import tempfile
    # Write prompt to a temp file so the helper can read it safely
    fd, prompt_path = tempfile.mkstemp(prefix='claude_tab_', suffix='.txt')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(prompt)

    subprocess.Popen(
        [sys.executable, _CLI_HELPER, prompt_path, task_file_path],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


# ---------------------------------------------------------------------------
# Backend 1: Claude API
# ---------------------------------------------------------------------------

CLAUDE_API_URL = 'https://api.anthropic.com/v1/messages'
CLAUDE_MODEL = 'claude-haiku-4-5-20251001'
CLAUDE_TIMEOUT = 10


def claude_summarize(messages, min_turns=3, tags=None):
    """Call Claude Haiku via Anthropic API. Raises if ANTHROPIC_API_KEY not set."""
    api_key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if not api_key:
        raise EnvironmentError('ANTHROPIC_API_KEY not set')

    user_content = build_user_prompt(messages, min_turns=min_turns, tags=tags)

    payload = json.dumps({
        'model': CLAUDE_MODEL,
        'max_tokens': 300,
        'system': SYSTEM_PROMPT,
        'messages': [{'role': 'user', 'content': user_content}],
    }).encode()

    req = urllib.request.Request(
        CLAUDE_API_URL,
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=CLAUDE_TIMEOUT) as resp:
        result = json.loads(resp.read())

    text = result['content'][0]['text']
    return parse_llm_response(text)


# ---------------------------------------------------------------------------
# Backend 2: Ollama
# ---------------------------------------------------------------------------

OLLAMA_URL = 'http://localhost:11434/api/chat'
OLLAMA_TIMEOUT = 10


def _get_ollama_model():
    """Pick the best available small model from the local Ollama server."""
    req = urllib.request.Request('http://localhost:11434/api/tags')
    with urllib.request.urlopen(req, timeout=2) as resp:
        data = json.loads(resp.read())
    models = [m['name'] for m in data.get('models', [])]
    if not models:
        raise RuntimeError('no Ollama models available')
    preferred = [
        'qwen3.5:4b', 'qwen2.5:4b', 'qwen3:4b',
        'llama3.2:3b', 'llama3.2:latest', 'llama3:latest',
    ]
    for p in preferred:
        if p in models:
            return p
    return models[0]  # fall back to whatever is installed


def ollama_summarize(messages, min_turns=3, tags=None):
    """Call local Ollama. Raises if Ollama is not running or has no models."""
    model = _get_ollama_model()
    user_content = build_user_prompt(messages, min_turns=min_turns, tags=tags)

    payload = json.dumps({
        'model': model,
        'stream': False,
        'think': False,          # disables extended thinking on qwen3.x
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user',   'content': user_content},
        ],
        'options': {'temperature': 0.1, 'num_predict': 300},
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
        result = json.loads(resp.read())

    text = result.get('message', {}).get('content', '').strip()
    if not text:
        raise ValueError('empty response from Ollama')
    return parse_llm_response(text)


# ---------------------------------------------------------------------------
# Backend 3: Keyword fallback (zero dependencies)
# ---------------------------------------------------------------------------

COMPLETION_KEYWORDS = [
    'complete', 'completed', 'done', 'finished', 'fixed', 'implemented',
    'deployed', 'resolved', 'merged', 'all tests pass', 'tests pass',
    'successfully', 'is working', 'are working', 'is ready', 'are ready',
    '完成', '完毕', '搞定', '结束', '修复了', '部署了', '通过了', '已实现',
]


def detect_task_boundary(messages):
    """Find the start of the current task after the last completion signal.

    Returns the index of the first user message after the last detected
    completion, or 0 if no boundary found.
    """
    boundary = 0
    for i, m in enumerate(messages):
        if m['role'] != 'assistant':
            continue
        text = m['content'].lower()
        hits = sum(1 for kw in COMPLETION_KEYWORDS if kw in text)
        if hits >= 3:
            for j in range(i + 1, len(messages)):
                if messages[j]['role'] == 'user':
                    boundary = j
                    break
    return boundary


def keyword_fallback(messages):
    user_msgs = [m['content'] for m in messages if m['role'] == 'user']
    asst_msgs = [m['content'] for m in messages if m['role'] == 'assistant']
    if not user_msgs:
        return None, False, ''
    # Use first user message as task anchor (original intent), truncated
    task_desc = re.sub(r'\s+', ' ', user_msgs[0]).strip()[:70]
    # Check the last 3 assistant messages for completion signals
    recent_asst = [m.lower() for m in asst_msgs[-3:]]
    kw_hits = sum(1 for msg in recent_asst for kw in COMPLETION_KEYWORDS if kw in msg)
    # Require 3+ keyword hits across recent messages to reduce false positives
    is_done = kw_hits >= 3
    return task_desc, is_done, ''


# ---------------------------------------------------------------------------
# Backend registry
# ---------------------------------------------------------------------------

BACKENDS = {
    'cli': claude_cli_summarize,
    'api': claude_summarize,
    'ollama': ollama_summarize,
    'keyword': keyword_fallback,
}

AUTO_ORDER = ['api', 'ollama', 'cli', 'keyword']


def _get_backend_chain():
    """Return list of backend functions based on CLAUDE_TAB_BACKEND env var."""
    choice = os.environ.get('CLAUDE_TAB_BACKEND', 'auto').strip().lower()
    if choice == 'auto':
        return [BACKENDS[k] for k in AUTO_ORDER]
    if choice in BACKENDS:
        return [BACKENDS[choice]]
    return [BACKENDS[k] for k in AUTO_ORDER]


# ---------------------------------------------------------------------------
# Memo file helpers
# ---------------------------------------------------------------------------

def sanitize_project_name(name):
    """Sanitize project name for filesystem use."""
    name = re.sub(r'[^a-zA-Z0-9_-]', '-', name).lower()
    return name[:50]


def resolve_project_name(cwd):
    """Determine project name from working directory."""
    home = str(pathlib.Path.home())
    real_cwd = os.path.realpath(cwd)
    if real_cwd == os.path.realpath(home) or real_cwd.startswith(('/tmp', '/private/tmp', '/var')):
        return 'general'
    try:
        result = subprocess.run(
            ['git', '-C', cwd, 'rev-parse', '--show-toplevel'],
            capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0:
            return sanitize_project_name(os.path.basename(result.stdout.strip()))
    except Exception:
        pass
    return sanitize_project_name(os.path.basename(cwd))


def write_memo(memo_content, task_desc, project_name, memo_base_dir=None):
    """Append a memo entry to the project's daily memo file."""
    if not memo_content:
        return
    if memo_base_dir is None:
        memo_base_dir = MEMO_BASE_DIR
    today = datetime.now().strftime('%Y-%m-%d')
    time_str = datetime.now().strftime('%H:%M')
    project_dir = os.path.join(memo_base_dir, project_name)
    os.makedirs(project_dir, exist_ok=True)
    memo_file = os.path.join(project_dir, f'{today}.md')

    items = [item.strip() for item in memo_content.split('|') if item.strip()]
    entry_lines = [f'\n## {time_str} | {task_desc}']
    for item in items:
        entry_lines.append(f'- {item}')
    entry_lines.append('')

    if not os.path.exists(memo_file):
        with open(memo_file, 'w', encoding='utf-8') as f:
            f.write(f'# {today}\n')
            f.write('\n'.join(entry_lines))
    else:
        with open(memo_file, 'a', encoding='utf-8') as f:
            f.write('\n'.join(entry_lines))


# ---------------------------------------------------------------------------
# Main — try each backend in priority order
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) != 3:
        sys.exit(0)

    transcript_path, task_file_path = sys.argv[1], sys.argv[2]
    messages = parse_transcript(transcript_path)
    if not messages:
        sys.exit(0)

    memo_config = load_memo_config()

    boundary = detect_task_boundary(messages)
    if boundary > 0:
        messages = messages[boundary:]
    if not messages:
        sys.exit(0)

    task_desc = is_done = None
    memo_content = ''
    for backend in _get_backend_chain():
        try:
            if backend is claude_cli_summarize:
                result = backend(
                    messages,
                    task_file_path=task_file_path,
                    min_turns=memo_config['min_turns'],
                    tags=memo_config['tags_str'],
                )
                if result is None:
                    # CLI backend launched async — it will write the file itself
                    sys.exit(0)
                task_desc, is_done, memo_content = result
            else:
                task_desc, is_done, memo_content = backend(
                    messages,
                    min_turns=memo_config['min_turns'],
                    tags=memo_config['tags_str'],
                )
            if task_desc:
                break
        except Exception:
            continue

    if not task_desc:
        sys.exit(0)

    prefix = 'DONE' if is_done else 'WIP'

    # Read existing PREV line before overwriting
    prev_line = None
    if os.path.exists(task_file_path):
        with open(task_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('PREV:'):
                    prev_line = line.strip()
                    break

    dirpart = os.path.dirname(task_file_path)
    if dirpart:
        os.makedirs(dirpart, exist_ok=True)
    with open(task_file_path, 'w', encoding='utf-8') as f:
        f.write(f"{prefix}:{task_desc}\n")
        if prev_line:
            f.write(f"{prev_line}\n")

    if memo_content:
        cwd = os.environ.get('PWD', os.getcwd())
        project = resolve_project_name(cwd)
        write_memo(memo_content, task_desc, project)


if __name__ == '__main__':
    main()
