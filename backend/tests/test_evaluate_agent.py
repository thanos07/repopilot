import json
from io import StringIO
from unittest.mock import Mock

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from execution.management.commands import evaluate_agent
from execution.sandbox import VerificationResult, SandboxError


@pytest.fixture
def evaluation(db, settings, tmp_path, monkeypatch):
    settings.BASE_DIR = tmp_path / 'backend'
    settings.LIVE_EXECUTION_ENABLED = True
    folder = tmp_path / 'evals' / 'example'
    folder.mkdir(parents=True)
    (folder / 'case.json').write_text(json.dumps({
        'id': 'example', 'issue': 'Fix example.',
        'files': {'app.py': 'value = 1\n'},
        'acceptance_tests': {'test_acceptance.py': 'assert False\n'},
    }), encoding='utf-8')
    get_user_model().objects.create_user(username='evaluator')
    agent = Mock()
    verify = Mock()
    monkeypatch.setattr(evaluate_agent, 'execute_run', agent)
    monkeypatch.setattr(evaluate_agent, 'E2BVerifier', lambda: Mock(verify=verify))
    output = tmp_path / 'report.json'

    def run():
        call_command('evaluate_agent', '--username', 'evaluator',
                     '--case', 'example', '--output', str(output), stdout=StringIO())
        return json.loads(output.read_text(encoding='utf-8'))

    return run, agent, verify


@pytest.mark.parametrize('status,code,accepted', [
    ('passed', 0, True),
    ('failed', 1, False),
    ('infrastructure_error', 124, False),
    ('passed', 1, False),
])
def test_verification_evidence(evaluation, status, code, accepted):
    run, agent, verify = evaluation
    verify.return_value = VerificationResult(status, code, 'test output', 'stderr', 25)
    report = run()
    row = report['cases'][0]
    assert row['accepted'] is accepted
    assert row['verification'] == {
        'status': status, 'exit_code': code, 'stdout': 'test output',
        'stderr': 'stderr', 'duration_ms': 25,
    }
    assert row['error'] == ''
    assert bool(row['failure_reason']) is not accepted
    assert report['acceptance_rate'] == (1.0 if accepted else 0.0)
    assert report['sandbox_cost_included'] is False
    assert 'test_acceptance.py' not in agent.call_args.kwargs['initial_files']
    assert 'test_acceptance.py' in verify.call_args.args[0]


@pytest.mark.parametrize('phase', ['agent', 'verification'])
def test_exception_phase_without_sensitive_message(evaluation, phase):
    run, agent, verify = evaluation
    target = agent if phase == 'agent' else verify
    target.side_effect = SandboxError('private credential details')
    report = run()
    row = report['cases'][0]
    assert row['accepted'] is False
    assert row['error'] == 'SandboxError'
    assert row['failure_reason']
    assert row['verification']['status'] == ('not_run' if phase == 'agent' else 'error')
    assert row['verification']['exit_code'] is None
    assert row['verification']['stdout'] == ''
    assert 'private credential details' not in json.dumps(report)
    if phase == 'agent':
        verify.assert_not_called()


def test_output_redacted_and_bounded(evaluation):
    run, _, verify = evaluation
    token = 'ghp_abcdefghijklmnop'
    verify.return_value = VerificationResult(
        'failed', 1, token + '\n' + 'x' * 20000,
        'Authorization: Bearer secret-value\n' + 'y' * 10000, 1,
    )
    report = run()
    evidence = report['cases'][0]['verification']
    assert len(evidence['stdout']) == 16000
    assert len(evidence['stderr']) == 8000
    assert '[REDACTED]' in evidence['stdout']
    assert token not in json.dumps(report)
    assert 'secret-value' not in json.dumps(report)
