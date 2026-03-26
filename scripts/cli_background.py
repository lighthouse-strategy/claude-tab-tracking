#!/usr/bin/env python3
"""Background helper: calls ``claude -p`` and writes the task summary to a file.

Invoked by dynamic_task_update.py as a detached process so the Stop hook
returns immediately while the (slow) CLI call runs in the background.

Usage: cli_background.py <prompt_file> <task_file> [<memo_base_dir> <project_name>]
"""
import logging
import os
import subprocess
import sys
from datetime import datetime

from claude_cli_common import build_claude_cli_cmd
from dynamic_task_update import parse_llm_response

logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

TIMEOUT = 60


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
    except Exception:
        logging.exception("Failed to read prompt file %s", prompt_path)
        sys.exit(1)
    finally:
        # Always clean up the temp file, even on read failure or later crash
        try:
            os.unlink(prompt_path)
        except OSError:
            logging.exception("Failed to delete temp prompt file %s", prompt_path)

    result = subprocess.run(
        build_claude_cli_cmd(),
        input=prompt,
        capture_output=True, text=True,
        timeout=TIMEOUT,
    )
    if result.returncode != 0:
        sys.exit(1)

    text = result.stdout.strip()
    if not text:
        sys.exit(1)

    task, is_done, memo = parse_llm_response(text)
    if not task:
        sys.exit(1)

    prefix = 'DONE' if is_done else 'WIP'

    # Preserve existing PREV line, use file lock to prevent race conditions
    import fcntl

    dirpart = os.path.dirname(task_file_path)
    if dirpart:
        os.makedirs(dirpart, exist_ok=True)

    lock_path = task_file_path + '.lock'
    with open(lock_path, 'w') as lock_f:
        try:
            fcntl.flock(lock_f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            # Another process holds the lock, skip this write
            sys.exit(0)

        prev = None
        if os.path.exists(task_file_path):
            with open(task_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('PREV:'):
                        prev = line.strip()
                        break

        with open(task_file_path, 'w', encoding='utf-8') as f:
            f.write(f"{prefix}:{task}\n")
            if prev:
                f.write(f"{prev}\n")

        fcntl.flock(lock_f, fcntl.LOCK_UN)

    # Write memo file if memo content present and memo args provided
    if memo and memo_base_dir and project_name:
        write_memo_file(memo, task, project_name, memo_base_dir)


if __name__ == '__main__':
    main()
