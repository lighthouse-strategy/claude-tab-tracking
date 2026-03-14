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
