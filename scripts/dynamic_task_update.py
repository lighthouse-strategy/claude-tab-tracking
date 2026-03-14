#!/usr/bin/env python3
"""
Reads Claude Code transcript JSONL and generates a one-line task summary.

Summarization priority (auto-detected, no config needed):
  1. Claude API  — if ANTHROPIC_API_KEY is set
  2. Ollama      — if a local server is running on port 11434
  3. Keywords    — always available, zero dependencies

Updates task file with WIP:description or DONE:description.
"""
import json
import os
import re
import sys
import urllib.request


# ---------------------------------------------------------------------------
# Shared prompt templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    'You are a concise task tracker. '
    'Based on the full conversation arc — including how the task evolved across multiple exchanges — '
    'summarize what is currently being worked on in one sentence '
    '(under 25 characters if Chinese, under 40 if English). '
    'Focus on the overall goal, not just the latest message. '
    'IMPORTANT: When the user message contains ambiguous terms, '
    'use the assistant responses to determine the correct meaning. '
    'For example, if user says "中超" and assistant replies about supermarkets, '
    'the task is about Chinese supermarkets, not the football league. '
    'Output only the task description — no explanations, no quotes, no extra punctuation. '
    'Only prefix with "[完成] " if there is clear evidence across multiple turns that the task is fully done.'
)

USER_PROMPT_TEMPLATE = """根据以下完整对话记录，综合判断当前正在进行的任务。请关注整体目标和对话走向，而不只是最后一条消息。
注意：如果用户用词有歧义，请根据 Claude 的实际回复内容来判断正确含义。

对话记录（含开头和最近内容）：
{conversation}

任务描述："""


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
    """Extract (task_description, is_done) from LLM output."""
    response = response.strip()
    is_done = bool(re.match(
        r'^(\[完成\]|完成\s|完成：|completed[: ]|\[done\])',
        response, re.IGNORECASE
    ))
    task = re.sub(
        r'^(\[完成\]\s*|完成\s+|完成：\s*|\[done\]\s*|completed:\s*)',
        '', response, flags=re.IGNORECASE
    ).strip()
    if len(task) > 60:
        task = task[:57] + '...'
    return task, is_done


# ---------------------------------------------------------------------------
# Backend 1: Claude API
# ---------------------------------------------------------------------------

CLAUDE_API_URL = 'https://api.anthropic.com/v1/messages'
CLAUDE_MODEL = 'claude-haiku-4-5-20251001'
CLAUDE_TIMEOUT = 10


def claude_summarize(messages):
    """Call Claude Haiku via Anthropic API. Raises if ANTHROPIC_API_KEY not set."""
    api_key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if not api_key:
        raise EnvironmentError('ANTHROPIC_API_KEY not set')

    conversation = build_conversation_snippet(messages)
    user_content = USER_PROMPT_TEMPLATE.format(conversation=conversation)

    payload = json.dumps({
        'model': CLAUDE_MODEL,
        'max_tokens': 80,
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


def ollama_summarize(messages):
    """Call local Ollama. Raises if Ollama is not running or has no models."""
    model = _get_ollama_model()
    conversation = build_conversation_snippet(messages)
    user_content = USER_PROMPT_TEMPLATE.format(conversation=conversation)

    payload = json.dumps({
        'model': model,
        'stream': False,
        'think': False,          # disables extended thinking on qwen3.x
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user',   'content': user_content},
        ],
        'options': {'temperature': 0.1, 'num_predict': 80},
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
        return None, False
    # Use first user message as task anchor (original intent), truncated
    task_desc = re.sub(r'\s+', ' ', user_msgs[0]).strip()[:70]
    # Check the last 3 assistant messages for completion signals
    recent_asst = [m.lower() for m in asst_msgs[-3:]]
    kw_hits = sum(1 for msg in recent_asst for kw in COMPLETION_KEYWORDS if kw in msg)
    # Require 3+ keyword hits across recent messages to reduce false positives
    is_done = kw_hits >= 3
    return task_desc, is_done


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

    boundary = detect_task_boundary(messages)
    if boundary > 0:
        messages = messages[boundary:]
    if not messages:
        sys.exit(0)

    task_desc = is_done = None
    for backend in (claude_summarize, ollama_summarize, keyword_fallback):
        try:
            task_desc, is_done = backend(messages)
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


if __name__ == '__main__':
    main()
