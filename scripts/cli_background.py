#!/usr/bin/env python3
"""Background helper: calls ``claude -p`` and writes the task summary to a file.

Invoked by dynamic_task_update.py as a detached process so the Stop hook
returns immediately while the (slow) CLI call runs in the background.

Usage: cli_background.py <prompt_file> <task_file>
"""
import os
import re
import subprocess
import sys

TIMEOUT = 60


def main():
    if len(sys.argv) != 3:
        sys.exit(1)

    prompt_path, task_file_path = sys.argv[1], sys.argv[2]

    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read()
    finally:
        # Clean up temp prompt file
        try:
            os.unlink(prompt_path)
        except OSError:
            pass

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

    # Parse response
    done = bool(re.match(
        r'^(\[完成\]|完成\s|完成：|completed[: ]|\[done\])',
        text, re.IGNORECASE,
    ))
    task = re.sub(
        r'^(\[完成\]\s*|完成\s+|完成：\s*|\[done\]\s*|completed:\s*)',
        '', text, flags=re.IGNORECASE,
    ).strip()
    if len(task) > 60:
        task = task[:57] + '...'
    prefix = 'DONE' if done else 'WIP'

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


if __name__ == '__main__':
    main()
