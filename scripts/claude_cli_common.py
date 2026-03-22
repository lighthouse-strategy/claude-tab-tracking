#!/usr/bin/env python3
"""Shared Claude CLI invocation helpers for child summarizer sessions."""
import json


_CHILD_SESSION_SETTINGS = json.dumps({'disableAllHooks': True}, separators=(',', ':'))


def build_claude_cli_cmd(model='haiku'):
    """Return a claude CLI command safe for nested summarizer calls.

    Child summarizer sessions must not inherit user hooks, otherwise a Stop
    hook that shells out to ``claude -p`` can recursively trigger itself.
    """
    return [
        'claude',
        '-p',
        '--model', model,
        '--output-format', 'text',
        '--settings', _CHILD_SESSION_SETTINGS,
        '--no-session-persistence',
    ]
