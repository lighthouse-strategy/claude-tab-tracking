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
    task, done = parse_llm_response('Fix the data pipeline')
    assert task == 'Fix the data pipeline'
    assert done is False


def test_parse_done_chinese():
    task, done = parse_llm_response('[完成] 修复数据管道')
    assert task == '修复数据管道'
    assert done is True


def test_parse_done_english():
    task, done = parse_llm_response('[DONE] Fix the pipeline')
    assert task == 'Fix the pipeline'
    assert done is True


def test_parse_truncates_long_text():
    long_text = 'A' * 100
    task, done = parse_llm_response(long_text)
    assert len(task) <= 60
    assert task.endswith('...')


# ---------------------------------------------------------------------------
# Tests for keyword_fallback
# ---------------------------------------------------------------------------

from dynamic_task_update import keyword_fallback


def test_keyword_no_completion():
    msgs = [
        _msg('user', 'Fix the bug in parser'),
        _msg('assistant', 'I see the issue, working on it now.'),
    ]
    task, done = keyword_fallback(msgs)
    assert task is not None
    assert done is False


def test_keyword_clear_completion():
    msgs = [
        _msg('user', 'Fix the auth bug'),
        _msg('assistant', 'The bug is fixed and all tests pass. The fix is deployed successfully.'),
    ]
    task, done = keyword_fallback(msgs)
    assert done is True


def test_keyword_edge_case_two_hits_not_done():
    msgs = [
        _msg('user', 'Fix the bug'),
        _msg('assistant', 'I have finished the investigation. The root cause is identified.'),
    ]
    task, done = keyword_fallback(msgs)
    assert done is False


def test_keyword_empty_messages():
    task, done = keyword_fallback([])
    assert task is None
    assert done is False


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
