import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from dynamic_task_update import detect_task_boundary


def _msg(role, content):
    return {'role': role, 'content': content}


def test_no_boundary():
    msgs = [_msg('user', 'Fix the bug'), _msg('assistant', 'Working on it')]
    assert detect_task_boundary(msgs) == 0


def test_single_boundary():
    msgs = [
        _msg('user', 'Fix the bug'),
        _msg('assistant', 'Done, the bug is fixed and all tests pass.'),
        _msg('user', 'Now add a new feature'),
        _msg('assistant', 'Working on the feature'),
    ]
    assert detect_task_boundary(msgs) == 2


def test_multiple_boundaries_returns_last():
    msgs = [
        _msg('user', 'Fix bug A'),
        _msg('assistant', 'Fixed, all tests pass successfully.'),
        _msg('user', 'Fix bug B'),
        _msg('assistant', 'Done, bug B is resolved and deployed.'),
        _msg('user', 'Now build feature C'),
        _msg('assistant', 'Starting on feature C'),
    ]
    assert detect_task_boundary(msgs) == 4


def test_no_boundary_when_no_followup_user_msg():
    msgs = [
        _msg('user', 'Fix the bug'),
        _msg('assistant', 'Done, the bug is completely fixed and tests pass.'),
    ]
    assert detect_task_boundary(msgs) == 0


# ---------------------------------------------------------------------------
# Tests for extract_text
# ---------------------------------------------------------------------------

from dynamic_task_update import extract_text


def test_extract_text_string():
    assert extract_text('hello world') == 'hello world'


def test_extract_text_list_of_text_blocks():
    blocks = [
        {'type': 'text', 'text': 'hello'},
        {'type': 'text', 'text': 'world'},
    ]
    assert extract_text(blocks) == 'hello world'


def test_extract_text_mixed_content():
    blocks = [
        'raw string',
        {'type': 'text', 'text': 'block text'},
        {'type': 'tool_use', 'name': 'bash'},
    ]
    assert extract_text(blocks) == 'raw string block text'


def test_extract_text_empty():
    assert extract_text('') == ''
    assert extract_text([]) == ''
    assert extract_text(None) == ''


# ---------------------------------------------------------------------------
# Tests for parse_llm_response
# ---------------------------------------------------------------------------

from dynamic_task_update import parse_llm_response


def test_parse_plain_text():
    task, done, memo = parse_llm_response('Fix the data pipeline')
    assert task == 'Fix the data pipeline'
    assert done is False
    assert memo == ''


def test_parse_done_chinese():
    task, done, memo = parse_llm_response('[完成] 修复数据管道')
    assert task == '修复数据管道'
    assert done is True
    assert memo == ''


def test_parse_done_english():
    task, done, memo = parse_llm_response('[DONE] Fix the pipeline')
    assert task == 'Fix the pipeline'
    assert done is True
    assert memo == ''


def test_parse_truncates_long_text():
    long_text = 'A' * 100
    task, done, memo = parse_llm_response(long_text)
    assert len(task) <= 60
    assert task.endswith('...')
    assert memo == ''


# ---------------------------------------------------------------------------
# Tests for memo parsing
# ---------------------------------------------------------------------------


def test_parse_response_with_memo():
    response = '任务：修复登录页验证\n备忘：【决策】改用 JWT | 【数据】影响 3 个 endpoint'
    task, is_done, memo = parse_llm_response(response)
    assert task == '修复登录页验证'
    assert is_done is False
    assert memo == '【决策】改用 JWT | 【数据】影响 3 个 endpoint'


def test_parse_response_without_memo():
    response = '任务：修复登录页验证'
    task, is_done, memo = parse_llm_response(response)
    assert task == '修复登录页验证'
    assert is_done is False
    assert memo == ''


def test_parse_response_no_prefix_backward_compat():
    response = 'Fix the data pipeline'
    task, is_done, memo = parse_llm_response(response)
    assert task == 'Fix the data pipeline'
    assert is_done is False
    assert memo == ''


def test_parse_response_done_with_memo():
    response = '任务：[完成] 修复数据管道\n备忘：【结论】根因是缓存过期'
    task, is_done, memo = parse_llm_response(response)
    assert task == '修复数据管道'
    assert is_done is True
    assert memo == '【结论】根因是缓存过期'


def test_parse_response_memo_only_no_task_prefix():
    response = '修复登录页\n备忘：【决策】改用 JWT'
    task, is_done, memo = parse_llm_response(response)
    assert task == '修复登录页'
    assert memo == '【决策】改用 JWT'


# ---------------------------------------------------------------------------
# Tests for keyword_fallback
# ---------------------------------------------------------------------------

from dynamic_task_update import keyword_fallback


def test_keyword_no_completion():
    msgs = [
        _msg('user', 'Fix the bug in parser'),
        _msg('assistant', 'I see the issue, working on it now.'),
    ]
    task, done, memo = keyword_fallback(msgs)
    assert task is not None
    assert done is False
    assert memo == ''


def test_keyword_clear_completion():
    msgs = [
        _msg('user', 'Fix the auth bug'),
        _msg('assistant', 'The bug is fixed and all tests pass. The fix is deployed successfully.'),
    ]
    task, done, memo = keyword_fallback(msgs)
    assert done is True
    assert memo == ''


def test_keyword_edge_case_two_hits_not_done():
    msgs = [
        _msg('user', 'Fix the bug'),
        _msg('assistant', 'I have finished the investigation. The root cause is identified.'),
    ]
    task, done, memo = keyword_fallback(msgs)
    assert done is False
    assert memo == ''


def test_keyword_empty_messages():
    task, done, memo = keyword_fallback([])
    assert task is None
    assert done is False
    assert memo == ''


# ---------------------------------------------------------------------------
# Tests for parse_transcript
# ---------------------------------------------------------------------------

import json
import tempfile

from dynamic_task_update import parse_transcript


def test_parse_valid_transcript():
    lines = [
        json.dumps({'type': 'user', 'message': {'content': 'Hello'}}),
        json.dumps({'type': 'assistant', 'message': {'content': 'Hi there'}}),
    ]
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write('\n'.join(lines))
        path = f.name
    try:
        msgs = parse_transcript(path)
        assert len(msgs) == 2
        assert msgs[0]['role'] == 'user'
        assert msgs[1]['role'] == 'assistant'
    finally:
        os.unlink(path)


def test_parse_skips_slash_commands():
    lines = [
        json.dumps({'type': 'user', 'message': {'content': '/task Set something'}}),
        json.dumps({'type': 'user', 'message': {'content': 'Fix the bug'}}),
    ]
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write('\n'.join(lines))
        path = f.name
    try:
        msgs = parse_transcript(path)
        assert len(msgs) == 1
        assert msgs[0]['content'] == 'Fix the bug'
    finally:
        os.unlink(path)


def test_parse_skips_malformed_lines():
    lines = [
        'not valid json',
        json.dumps({'type': 'user', 'message': {'content': 'Valid message'}}),
        '{broken',
    ]
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write('\n'.join(lines))
        path = f.name
    try:
        msgs = parse_transcript(path)
        assert len(msgs) == 1
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Tests for PREV line preservation
# ---------------------------------------------------------------------------


def test_main_preserves_prev_line(tmp_path):
    """When Python script writes a new task, it should preserve existing PREV line."""
    from dynamic_task_update import main as _unused  # just verify import works
    # We can't easily test main() directly (it reads sys.argv),
    # so test the PREV preservation logic in isolation.

    # Simulate: task file has WIP + PREV
    task_file = tmp_path / "test_session.txt"
    task_file.write_text("WIP:Old task\nPREV:Even older task\n")

    # Read PREV line (same logic as in main)
    prev_line = None
    with open(task_file, 'r') as f:
        for line in f:
            if line.startswith('PREV:'):
                prev_line = line.strip()
                break

    # Write new task, preserving PREV
    with open(task_file, 'w') as f:
        f.write("WIP:New task\n")
        if prev_line:
            f.write(f"{prev_line}\n")

    lines = task_file.read_text().splitlines()
    assert lines[0] == "WIP:New task"
    assert lines[1] == "PREV:Even older task"
    assert len(lines) == 2


def test_prev_line_not_added_when_absent(tmp_path):
    """When no PREV line exists, output should be single line."""
    task_file = tmp_path / "test_session.txt"
    task_file.write_text("WIP:Current task\n")

    prev_line = None
    with open(task_file, 'r') as f:
        for line in f:
            if line.startswith('PREV:'):
                prev_line = line.strip()
                break

    with open(task_file, 'w') as f:
        f.write("DONE:Current task\n")
        if prev_line:
            f.write(f"{prev_line}\n")

    lines = task_file.read_text().splitlines()
    assert lines[0] == "DONE:Current task"
    assert len(lines) == 1


def test_prev_line_stripped_properly(tmp_path):
    """PREV line should be stripped of whitespace including \\r\\n."""
    task_file = tmp_path / "test_session.txt"
    task_file.write_text("WIP:Task\nPREV:Old task\r\n")

    prev_line = None
    with open(task_file, 'r') as f:
        for line in f:
            if line.startswith('PREV:'):
                prev_line = line.strip()
                break

    assert prev_line == "PREV:Old task"  # no \r


# ---------------------------------------------------------------------------
# Tests for _get_backend_chain
# ---------------------------------------------------------------------------

import subprocess

from dynamic_task_update import (
    _get_backend_chain,
    build_user_prompt,
    claude_cli_summarize,
    claude_summarize,
    ollama_summarize,
)


# ---------------------------------------------------------------------------
# Tests for build_user_prompt
# ---------------------------------------------------------------------------


def test_build_prompt_short_conversation():
    msgs = [_msg('user', 'Hi'), _msg('assistant', 'Hello')]
    prompt = build_user_prompt(msgs, min_turns=3)
    assert '备忘' not in prompt


def test_build_prompt_long_conversation():
    msgs = [
        _msg('user', 'Fix the bug'),
        _msg('assistant', 'Working on it'),
        _msg('user', 'Use JWT instead'),
        _msg('assistant', 'Done, switched to JWT'),
    ]
    prompt = build_user_prompt(msgs, min_turns=3)
    assert '备忘' in prompt


def test_build_prompt_custom_tags():
    msgs = [_msg('user', 'a'), _msg('assistant', 'b'), _msg('user', 'c'), _msg('assistant', 'd')]
    prompt = build_user_prompt(msgs, min_turns=3, tags='【风险】【成本】')
    assert '【风险】【成本】' in prompt


def test_backend_chain_auto(monkeypatch):
    monkeypatch.delenv('CLAUDE_TAB_BACKEND', raising=False)
    chain = _get_backend_chain()
    assert chain[0] is claude_summarize
    assert chain[1] is ollama_summarize
    assert chain[2] is claude_cli_summarize
    assert chain[3] is keyword_fallback


def test_backend_chain_cli_only(monkeypatch):
    monkeypatch.setenv('CLAUDE_TAB_BACKEND', 'cli')
    chain = _get_backend_chain()
    assert len(chain) == 1
    assert chain[0] is claude_cli_summarize


def test_backend_chain_api_only(monkeypatch):
    monkeypatch.setenv('CLAUDE_TAB_BACKEND', 'api')
    chain = _get_backend_chain()
    assert len(chain) == 1
    assert chain[0] is claude_summarize


def test_backend_chain_ollama_only(monkeypatch):
    monkeypatch.setenv('CLAUDE_TAB_BACKEND', 'ollama')
    chain = _get_backend_chain()
    assert len(chain) == 1
    assert chain[0] is ollama_summarize


def test_backend_chain_keyword_only(monkeypatch):
    monkeypatch.setenv('CLAUDE_TAB_BACKEND', 'keyword')
    chain = _get_backend_chain()
    assert len(chain) == 1
    assert chain[0] is keyword_fallback


def test_backend_chain_invalid_falls_back_to_auto(monkeypatch):
    monkeypatch.setenv('CLAUDE_TAB_BACKEND', 'nonexistent')
    chain = _get_backend_chain()
    assert len(chain) == 4  # same as auto


# ---------------------------------------------------------------------------
# Tests for claude_cli_summarize
# ---------------------------------------------------------------------------


def test_claude_cli_summarize_success(monkeypatch):
    """claude_cli_summarize should parse CLI stdout into task description."""
    def mock_run(cmd, **kwargs):
        class Result:
            returncode = 0
            stdout = '修复认证 bug'
            stderr = ''
        return Result()

    monkeypatch.setattr(subprocess, 'run', mock_run)
    msgs = [_msg('user', 'Fix the auth bug'), _msg('assistant', 'Working on it')]
    task, done, memo = claude_cli_summarize(msgs)
    assert task == '修复认证 bug'
    assert done is False
    assert memo == ''


def test_claude_cli_summarize_done(monkeypatch):
    """claude_cli_summarize should detect completion prefix."""
    def mock_run(cmd, **kwargs):
        class Result:
            returncode = 0
            stdout = '[完成] 修复认证 bug'
            stderr = ''
        return Result()

    monkeypatch.setattr(subprocess, 'run', mock_run)
    msgs = [_msg('user', 'Fix the auth bug'), _msg('assistant', 'Done')]
    task, done, memo = claude_cli_summarize(msgs)
    assert task == '修复认证 bug'
    assert done is True
    assert memo == ''


def test_claude_cli_summarize_failure(monkeypatch):
    """claude_cli_summarize should raise on non-zero exit code."""
    def mock_run(cmd, **kwargs):
        class Result:
            returncode = 1
            stdout = ''
            stderr = 'error'
        return Result()

    monkeypatch.setattr(subprocess, 'run', mock_run)
    msgs = [_msg('user', 'Fix the bug')]
    import pytest
    with pytest.raises(RuntimeError):
        claude_cli_summarize(msgs)


# ---------------------------------------------------------------------------
# Tests for memo file writing
# ---------------------------------------------------------------------------

from dynamic_task_update import write_memo, resolve_project_name, sanitize_project_name
from datetime import datetime


def test_sanitize_project_name():
    assert sanitize_project_name('my-project') == 'my-project'
    assert sanitize_project_name('My Project 2') == 'my-project-2'
    assert sanitize_project_name('a' * 60) == 'a' * 50
    assert sanitize_project_name('proj@#$name') == 'proj---name'


def test_write_memo_creates_file(tmp_path):
    memo_dir = tmp_path / "memos"
    write_memo(
        memo_content='【决策】改用 JWT | 【数据】影响 3 个 endpoint',
        task_desc='修复登录页验证',
        project_name='test-project',
        memo_base_dir=str(memo_dir),
    )
    today = datetime.now().strftime('%Y-%m-%d')
    memo_file = memo_dir / 'test-project' / f'{today}.md'
    assert memo_file.exists()
    content = memo_file.read_text()
    assert f'# {today}' in content
    assert '修复登录页验证' in content
    assert '【决策】改用 JWT' in content
    assert '【数据】影响 3 个 endpoint' in content


def test_write_memo_appends(tmp_path):
    memo_dir = tmp_path / "memos"
    write_memo('【决策】第一条', '任务A', 'proj', str(memo_dir))
    write_memo('【数据】第二条', '任务B', 'proj', str(memo_dir))
    today = datetime.now().strftime('%Y-%m-%d')
    content = (memo_dir / 'proj' / f'{today}.md').read_text()
    assert '任务A' in content
    assert '任务B' in content


def test_write_memo_skips_empty():
    write_memo('', '任务', 'proj', '/tmp/nonexistent-memo-dir-test')
    # Should not create any file or raise


def test_resolve_project_name_fallback():
    name = resolve_project_name('/tmp')
    assert name == 'general'


def test_resolve_project_name_home():
    import pathlib
    home = str(pathlib.Path.home())
    name = resolve_project_name(home)
    assert name == 'general'


# ---------------------------------------------------------------------------
# Tests for load_memo_config
# ---------------------------------------------------------------------------

from dynamic_task_update import load_memo_config


def test_load_config_defaults(tmp_path):
    config = load_memo_config(str(tmp_path / 'nonexistent.yaml'))
    assert config['min_turns'] == 3
    assert config['archive_days'] == 90
    assert '决策' in config['tags_str']


def test_load_config_custom(tmp_path):
    config_file = tmp_path / 'config.yaml'
    config_file.write_text('tags:\n  - 决策\n  - 风险\nmin_turns: 5\narchive_days: 30\n')
    config = load_memo_config(str(config_file))
    assert config['min_turns'] == 5
    assert config['archive_days'] == 30
    assert '风险' in config['tags_str']


def test_load_config_invalid_yaml(tmp_path):
    config_file = tmp_path / 'config.yaml'
    config_file.write_text('not: valid: yaml: [broken')
    config = load_memo_config(str(config_file))
    assert config['min_turns'] == 3  # defaults


# ---------------------------------------------------------------------------
# Tests for cli_background.parse_response
# ---------------------------------------------------------------------------


def test_cli_background_parse_response():
    """Test that cli_background's parse_response handles memo correctly."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
    from cli_background import parse_response
    task, done, memo = parse_response("任务：修复 bug\n备忘：【决策】改用新方案")
    assert task == '修复 bug'
    assert done is False
    assert memo == '【决策】改用新方案'


def test_cli_background_parse_response_done():
    """parse_response detects completion prefix."""
    from cli_background import parse_response
    task, done, memo = parse_response("任务：[完成] 部署上线\n备忘：【结论】顺利完成")
    assert task == '部署上线'
    assert done is True
    assert memo == '【结论】顺利完成'


def test_cli_background_parse_response_no_memo():
    """parse_response returns empty memo when none present."""
    from cli_background import parse_response
    task, done, memo = parse_response("Fix the data pipeline")
    assert task == 'Fix the data pipeline'
    assert done is False
    assert memo == ''
