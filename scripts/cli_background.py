#!/usr/bin/env python3
"""Background helper: calls ``claude -p`` and writes the task summary to a file.

Invoked by dynamic_task_update.py as a detached process so the Stop hook
returns immediately while the (slow) CLI call runs in the background.

Usage: cli_background.py <prompt_file> <task_file> [<memo_base_dir> <project_name>]
"""
import logging
import os
import re
import subprocess
import sys
from datetime import datetime

logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

TIMEOUT = 60


def parse_response(text):
    """Parse LLM response into (task, is_done, memo).

    Duplicates the logic from dynamic_task_update.parse_llm_response to avoid
    import complexity (this script runs as a detached process).
    """
    text = text.strip()
    lines = text.splitlines()

    memo = ''
    task_lines = []
    for line in lines:
        m = re.match(r'^备忘[：:](.*)$', line.strip())
        if m:
            memo = m.group(1).strip()
        else:
            task_lines.append(line)

    task_text = task_lines[0].strip() if task_lines else ''
    # Strip 任务： or 任务: prefix
    task_text = re.sub(r'^任务[：:]\s*', '', task_text)

    is_done = bool(re.match(
        r'^(\[完成\]|完成\s|完成：|completed[: ]|\[done\])',
        task_text, re.IGNORECASE,
    ))
    task = re.sub(
        r'^(\[完成\]\s*|完成\s+|完成：\s*|\[done\]\s*|completed:\s*)',
        '', task_text, flags=re.IGNORECASE,
    ).strip()
    if len(task) > 60:
        task = task[:57] + '...'
    return task, is_done, memo


def write_memo_file(memo_content, task_desc, project_name, memo_base_dir):
    """Append a memo entry to the project's daily memo file."""
    if not memo_content:
        return
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


def main():
    if len(sys.argv) < 3 or len(sys.argv) == 4:
        sys.exit(1)

    prompt_path = sys.argv[1]
    task_file_path = sys.argv[2]
    memo_base_dir = sys.argv[3] if len(sys.argv) >= 5 else None
    project_name = sys.argv[4] if len(sys.argv) >= 5 else None

    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read()
    finally:
        # Clean up temp prompt file
        try:
            os.unlink(prompt_path)
        except OSError:
            logging.exception("Failed to delete temp prompt file %s", prompt_path)

    result = subprocess.run(
        ['claude', '-p', '--model', 'haiku'],
        input=prompt,
        capture_output=True, text=True,
        timeout=TIMEOUT,
    )
    if result.returncode != 0:
        sys.exit(1)

    text = result.stdout.strip()
    if not text:
        sys.exit(1)

    task, is_done, memo = parse_response(text)
    if not task:
        sys.exit(1)

    prefix = 'DONE' if is_done else 'WIP'

    # Preserve existing PREV line
    prev = None
    if os.path.exists(task_file_path):
        with open(task_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('PREV:'):
                    prev = line.strip()
                    break

    dirpart = os.path.dirname(task_file_path)
    if dirpart:
        os.makedirs(dirpart, exist_ok=True)
    with open(task_file_path, 'w', encoding='utf-8') as f:
        f.write(f"{prefix}:{task}\n")
        if prev:
            f.write(f"{prev}\n")

    # Write memo file if memo content present and memo args provided
    if memo and memo_base_dir and project_name:
        write_memo_file(memo, task, project_name, memo_base_dir)


if __name__ == '__main__':
    main()
