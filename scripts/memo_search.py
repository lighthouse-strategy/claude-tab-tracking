#!/usr/bin/env python3
"""Full-text search across all memo files.

Usage (standalone):
    python3 memo_search.py <query> [--dir <memo_base_dir>] [--max <N>]

Programmatic:
    from memo_search import search_memos
    results = search_memos("JWT", max_results=10)
"""
import os
import pathlib
import re
import sys


DEFAULT_MEMO_DIR = os.path.join(str(pathlib.Path.home()), '.claude', 'memos')


def search_memos(query, memo_base_dir=None, max_results=10):
    """Search all memo files for a query string (case-insensitive).

    Returns a list of dicts:
        [{"project": str, "date": str, "time": str, "task": str, "match_line": str}]
    """
    if memo_base_dir is None:
        memo_base_dir = DEFAULT_MEMO_DIR
    if not os.path.isdir(memo_base_dir):
        return []

    pattern = re.compile(re.escape(query), re.IGNORECASE)
    results = []

    for entry in sorted(os.listdir(memo_base_dir)):
        proj_dir = os.path.join(memo_base_dir, entry)
        if not os.path.isdir(proj_dir) or entry.startswith('_'):
            continue
        project = entry

        try:
            md_files = sorted(
                [f for f in os.listdir(proj_dir) if f.endswith('.md')],
                reverse=True,
            )
        except OSError:
            continue

        for fname in md_files:
            fpath = os.path.join(proj_dir, fname)
            date = fname.replace('.md', '')
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except OSError:
                continue

            current_time = ''
            current_task = ''
            for line in lines:
                stripped = line.strip()
                # Section headers: ## HH:MM | task description
                header_m = re.match(r'^##\s+(\d{1,2}:\d{2})\s*\|\s*(.*)$', stripped)
                if header_m:
                    current_time = header_m.group(1)
                    current_task = header_m.group(2).strip()
                    # Check if header itself matches
                    if pattern.search(stripped):
                        results.append({
                            'project': project,
                            'date': date,
                            'time': current_time,
                            'task': current_task,
                            'match_line': stripped,
                        })
                        if len(results) >= max_results:
                            return results
                    continue

                # Content lines (bullet points, etc.)
                if pattern.search(stripped) and stripped:
                    results.append({
                        'project': project,
                        'date': date,
                        'time': current_time,
                        'task': current_task,
                        'match_line': stripped,
                    })
                    if len(results) >= max_results:
                        return results

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Search memo files')
    parser.add_argument('query', help='Search query')
    parser.add_argument('--dir', default=None, help='Memo base directory')
    parser.add_argument('--max', type=int, default=10, help='Max results')
    args = parser.parse_args()

    results = search_memos(args.query, memo_base_dir=args.dir, max_results=args.max)
    if not results:
        print('No matches found.')
        return

    for r in results:
        print(f"[{r['project']}] {r['date']} {r['time']} | {r['task']}")
        print(f"  -> {r['match_line']}")
        print()


if __name__ == '__main__':
    main()
