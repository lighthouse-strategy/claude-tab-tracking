#!/usr/bin/env python3
"""
Reads Claude Code transcript JSONL, calls local Ollama (qwen3.5:4b) for a
semantic one-line task summary. Falls back to keyword heuristics if Ollama
is unavailable or times out.
Updates task file with WIP:description or DONE:description.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request


# ---------------------------------------------------------------------------
# Transcript parsing
# ---------------------------------------------------------------------------

def extract_text(content):
    """Normalize content field — can be str or list of blocks."""
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

                # Format A: {"type": "user"|"assistant", "message": {...}}
                if obj.get('type') in ('user', 'assistant'):
                    role = obj['type']
                    msg = obj.get('message', obj)
                    content = extract_text(msg.get('content', ''))
                # Format B: {"role": "user"|"assistant", "content": ...}
                elif obj.get('role') in ('user', 'assistant'):
                    role = obj['role']
                    content = extract_text(obj.get('content', ''))

                if not role or not content:
                    continue

                # Skip slash commands and very short user messages
                if role == 'user' and (content.startswith('/') or len(content) <= 3):
                    continue

                messages.append({'role': role, 'content': content})
    except Exception:
        pass
    return messages


# ---------------------------------------------------------------------------
# Ollama LLM summarization
# ---------------------------------------------------------------------------

OLLAMA_URL = 'http://localhost:11434/api/chat'
OLLAMA_MODEL = 'qwen3.5:4b'
OLLAMA_TIMEOUT = 10  # seconds

SYSTEM_PROMPT = (
    'You are a concise task tracker. '
    'Summarize the current task in one sentence (under 25 characters if Chinese, '
    'under 40 if English). Output only the task description — no explanations, '
    'no quotes, no punctuation beyond what is natural. '
    'If the task is fully completed, prefix with "[完成] ".'
)

USER_PROMPT_TEMPLATE = """根据以下对话片段，总结当前正在做的具体任务。

对话记录：
{conversation}

任务描述："""


def build_conversation_snippet(messages, max_exchanges=4):
    """Take the last N exchanges and format as a compact string."""
    recent = messages[-(max_exchanges * 2):]
    lines = []
    for m in recent:
        role_label = '用户' if m['role'] == 'user' else 'Claude'
        text = m['content'][:300].replace('\n', ' ')
        lines.append(f"{role_label}: {text}")
    return '\n'.join(lines)


def ollama_summarize(messages):
    """
    Call Ollama chat API (think:false) for a semantic one-line task summary.
    Returns (task_description, is_done) or raises on failure.
    """
    conversation = build_conversation_snippet(messages)
    user_content = USER_PROMPT_TEMPLATE.format(conversation=conversation)

    # think:false at top level disables qwen3.5 extended thinking mode
    payload = json.dumps({
        'model': OLLAMA_MODEL,
        'stream': False,
        'think': False,
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user',   'content': user_content},
        ],
        'options': {
            'temperature': 0.1,
            'num_predict': 80,
        },
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
        result = json.loads(resp.read())

    response = result.get('message', {}).get('content', '').strip()
    if not response:
        raise ValueError('empty response from Ollama')

    # Accept both bracketed and bare completion prefixes
    is_done = bool(re.match(r'^(\[完成\]|完成\s|完成：|completed[: ]|\[done\])', response, re.IGNORECASE))
    task = re.sub(r'^(\[完成\]\s*|完成\s+|完成：\s*|\[done\]\s*|completed:\s*)', '', response, flags=re.IGNORECASE).strip()

    if len(task) > 60:
        task = task[:57] + '...'

    return task, is_done


# ---------------------------------------------------------------------------
# Keyword fallback
# ---------------------------------------------------------------------------

COMPLETION_KEYWORDS = [
    'complete', 'completed', 'done', 'finished', 'fixed', 'implemented',
    'deployed', 'resolved', 'merged', 'all tests pass', 'tests pass',
    'successfully', 'is working', 'are working', 'is ready', 'are ready',
    '完成', '完毕', '搞定', '结束', '修复了', '部署了', '通过了', '已实现',
]


def keyword_fallback(messages):
    """Original heuristic: latest user message + keyword completion detection."""
    user_messages = [m['content'] for m in messages if m['role'] == 'user']
    assistant_messages = [m['content'] for m in messages if m['role'] == 'assistant']

    if not user_messages:
        return None, False

    latest = user_messages[-1]
    task_desc = re.sub(r'\s+', ' ', latest).strip()[:70].rstrip()

    last_assistant = assistant_messages[-1].lower() if assistant_messages else ''
    matches = sum(1 for kw in COMPLETION_KEYWORDS if kw in last_assistant)
    is_done = matches >= 2

    return task_desc, is_done


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) != 3:
        sys.exit(0)

    transcript_path = sys.argv[1]
    task_file_path = sys.argv[2]

    messages = parse_transcript(transcript_path)
    if not messages:
        sys.exit(0)

    # Try LLM summarization first, fall back to heuristics on any failure
    try:
        task_desc, is_done = ollama_summarize(messages)
    except Exception:
        task_desc, is_done = keyword_fallback(messages)

    if not task_desc:
        sys.exit(0)

    prefix = 'DONE' if is_done else 'WIP'
    new_content = f"{prefix}:{task_desc}\n"

    dirpart = os.path.dirname(task_file_path)
    if dirpart:
        os.makedirs(dirpart, exist_ok=True)
    with open(task_file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)


if __name__ == '__main__':
    main()
