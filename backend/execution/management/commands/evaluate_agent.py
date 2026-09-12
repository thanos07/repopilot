import json
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand,CommandError
from django.db.models import Sum
from coding_tasks.models import CodingTask,AgentRun
from repositories.models import Repository
from agent_engine.loop import execute_run
from execution.sandbox import E2BVerifier
from agent_engine.redaction import redact

class Command(BaseCommand):
    help='Run paid live evaluation on synthetic local cases. Acceptance tests are withheld from the agent.'
    def add_arguments(self, p):
        p.add_argument('--username')
        p.add_argument('--output')
        selection = p.add_mutually_exclusive_group()
        selection.add_argument('--case', dest='case_id', help='Run exactly one case by ID.')
        selection.add_argument('--limit', type=int, help='Run the first N cases (default: 1).')
        p.add_argument('--list-cases', action='store_true', help='List cases without paid execution.')

    def handle(self, *args, **o):
        paths = sorted((settings.BASE_DIR.parent / 'evals').glob('*/case.json'))
        cases = {}
        for path in paths:
            case = json.loads(path.read_text(encoding='utf-8'))
            case_id = case['id']
            if case_id in cases:
                raise CommandError(f'Duplicate case ID: {case_id}')
            cases[case_id] = path
        if not cases:
            raise CommandError('No evaluation cases found.')
        if o['list_cases']:
            for case_id in cases:
                self.stdout.write(case_id)
            return
        if o['case_id']:
            if o['case_id'] not in cases:
                raise CommandError('Unknown case ID. Use --list-cases to see available IDs.')
            selected = [cases[o['case_id']]]
        else:
            limit = o['limit'] if o['limit'] is not None else 1
            if not 1 <= limit <= 10:
                raise CommandError('limit must be 1 through 10.')
            selected = list(cases.values())[:limit]
        if not o['username'] or not o['output']:
            raise CommandError('--username and --output are required for live evaluation.')
        if not settings.LIVE_EXECUTION_ENABLED:
            raise CommandError('Enable live execution explicitly before paid evaluation.')
        user=get_user_model().objects.get(username=o['username'])
        repo,_=Repository.objects.get_or_create(owner=user,github_id=0,defaults={'full_name':'synthetic/evaluation'})
        rows=[]
        for path in selected:
            c=json.loads(path.read_text());task=CodingTask.objects.create(owner=user,repository=repo,title=c['issue'],description=c['issue']+' Add regression tests.',base_sha='0'*40,status='PREPARING')
            run=AgentRun.objects.create(task=task)
            verification = {
                'status': 'not_run', 'exit_code': None,
                'stdout': '', 'stderr': '', 'duration_ms': None,
            }
            failure_reason = ''
            phase = 'agent'
            try:
                # One visible smoke test permits environment setup, but is not an acceptance oracle.
                initial=c['files']|{'test_smoke.py':'import app\ndef test_import():\n    assert app is not None\n'}
                execute_run(task,run,initial_files=initial)
                patch=task.patches.order_by('-created_at').first()
                candidate=c['files']|(patch.contents if patch else {})
                # Withheld tests replace the agent's tests; do not give the oracle to its loop.
                candidate={p:s for p,s in candidate.items() if not p.startswith('test')}
                phase = 'verification'
                verdict=E2BVerifier().verify(candidate|c['acceptance_tests'])
                verification = {
                    'status': verdict.status,
                    'exit_code': verdict.exit_code,
                    'stdout': redact(verdict.stdout)[:16000],
                    'stderr': redact(verdict.stderr)[:8000],
                    'duration_ms': verdict.duration_ms,
                }
                success = verdict.status == 'passed' and verdict.exit_code == 0
                error = ''
                if not success:
                    failure_reason = (
                        'Withheld acceptance tests failed.'
                        if verdict.status == 'failed'
                        else 'Withheld verification did not complete successfully.'
                    )
                run.state='COMPLETED'
            except Exception as e:
                success=False;error=type(e).__name__;run.state='FAILED'
                if phase == 'verification':
                    verification['status'] = 'error'
                    failure_reason = 'Withheld verification raised an exception.'
                else:
                    failure_reason = 'Agent execution raised an exception before withheld verification.'
                # Exception messages can contain credentials; retain only the class name.
            from django.utils import timezone
            run.finished_at=timezone.now();run.save()
            cost=run.usage.aggregate(total=Sum('estimated_cost'))['total'] or 0
            rows.append({'case':c['id'],'accepted':success,'error':error,'failure_reason':failure_reason,'verification':verification,'iterations':run.iteration,'tool_calls':run.tool_count,'api_cost_estimate':str(cost),'latency_seconds':(run.finished_at-run.started_at).total_seconds()})
        successes=sum(r['accepted'] for r in rows);total=sum(float(r['api_cost_estimate']) for r in rows)
        Path(o['output']).write_text(json.dumps({'mode':'live synthetic evaluation','cases':rows,'acceptance_rate':successes/len(rows) if rows else None,'api_cost_per_accepted_task':total/successes if successes else None,'sandbox_cost_included':False},indent=2))
        self.stdout.write('Evaluation written. Acceptance rate measures only these synthetic tests.')
