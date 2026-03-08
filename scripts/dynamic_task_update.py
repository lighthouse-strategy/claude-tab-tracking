#!/usr/bin/env python3
"""
Reads Claude Code transcript JSONL, extracts latest user intent as task description,
detects completion signals in last assistant message.
Updates task file with WIP:description or DONE:description.
"""
import json
import sys
import os
import re


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
    """Parse transcript JSONL, return (user_messages, last_assistant_text)."""
    user_messages = []
    last_assistant_text = ''

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

                role = None
                content = None

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

                if role == 'user':
                    # Skip slash commands and very short messages
                    if not content.startswith('/') and len(content) > 3:
                        user_messages.append(content)
                elif role == 'assistant':
                    last_assistant_text = content

    except Exception:
        pass

    return user_messages, last_assistant_text


COMPLETION_KEYWORDS = [
    'complete', 'completed', 'done', 'finished', 'fixed', 'implemented',
    'deployed', 'resolved', 'merged', 'all tests pass', 'tests pass',
    'successfully', 'is working', 'are working', 'is ready', 'are ready',
    '完成', '完毕', '搞定', '结束', '修复了', '部署了', '通过了', '已实现',
]


def is_task_complete(assistant_text):
    """Heuristic: check if the assistant's last message signals completion."""
    text = assistant_text.lower()
    # Count how many completion signals appear
    matches = sum(1 for kw in COMPLETION_KEYWORDS if kw in text)
    # Require at least 2 signals to avoid false positives on casual mentions
    return matches >= 2


def main():
    if len(sys.argv) != 3:
        sys.exit(0)

    transcript_path = sys.argv[1]
    task_file_path = sys.argv[2]

    user_messages, last_assistant_text = parse_transcript(transcript_path)

    if not user_messages:
        sys.exit(0)

    # Use the latest user message as task description
    latest = user_messages[-1]
    # Collapse whitespace and truncate to 70 chars
    task_desc = re.sub(r'\s+', ' ', latest).strip()[:70].rstrip()

    # Determine status
    if is_task_complete(last_assistant_text):
        prefix = 'DONE'
    else:
        prefix = 'WIP'

    new_content = f"{prefix}:{task_desc}\n"

    dirpart = os.path.dirname(task_file_path)
    if dirpart:
        os.makedirs(dirpart, exist_ok=True)
    with open(task_file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)


if __name__ == '__main__':
    main()
