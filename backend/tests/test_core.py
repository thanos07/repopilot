import json
from decimal import Decimal
from types import SimpleNamespace
import pytest
from django.contrib.auth.models import User
from django.test import Client
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError
from agent_engine.tools import WorkingCopy,ToolError,validate,safe_path
from agent_engine.provider import calculate_cost,BudgetExceeded
from agent_engine.loop import execute_run
from coding_tasks.models import CodingTask,AgentRun,PatchSet,TestRun as VerificationRecord
from coding_tasks.lifecycle import approve,transition
from repositories.models import Repository
from integrations.github.client import repo_name,GitHubError

@pytest.fixture
def task(db):
    user=User.objects.create_user('noor',password='test-password',is_staff=True)
    repo=Repository.objects.create(owner=user,full_name='sample/python',github_id=1)
    return CodingTask.objects.create(owner=user,repository=repo,title='Fix increment',description='Increment by one.',base_sha='a'*40)

def test_exact_patch_does_not_replace_ambiguous_text():
    w=WorkingCopy({'x.py':'x = 1\nx = 1\n'})
    with pytest.raises(ToolError):w.execute('apply_patch',{'path':'x.py','old_text':'x = 1','new_text':'x = 2'})
    assert not w.changes()

@pytest.mark.parametrize('path',['../x.py','/x.py','.github/test.py','setup.py','conftest.py','x\\y.py','script.sh'])
def test_protected_paths(path):
    with pytest.raises(ToolError):safe_path(path)

def test_tool_rejects_unknown_arguments():
    with pytest.raises(Exception):validate('run_tests',{'command':'rm -rf /'})
    with pytest.raises(ToolError):validate('shell',{})

def test_patch_digest_changes_and_new_file_diff():
    w=WorkingCopy({'x.py':'x = 1\n'})
    old=w.digest();w.execute('apply_patch',{'path':'test_x.py','old_text':'','new_text':'assert True\n'})
    assert w.digest()!=old and '--- /dev/null' in w.diff()

def test_cost_does_not_double_count_cached_input():
    rates={'input':'1','cached':'0.1','output':'2'}
    assert calculate_cost(1000,800,100,rates)==Decimal('0.00048')
    assert calculate_cost(1000,None,100,rates)==Decimal('0.0012')

@pytest.mark.parametrize('url',['http://github.com/a/b','https://github.com.evil/a/b','https://github.com/a/b/issues/1','https://user@github.com/a/b','https://github.com/a/b?x=1'])
def test_repository_url_boundary(url):
    with pytest.raises(GitHubError):repo_name(url)

def test_owner_cannot_read_another_users_task(task):
    other=User.objects.create_user('other');c=APIClient();c.force_authenticate(other)
    assert c.get(f'/api/tasks/{task.id}/').status_code==404
    assert c.get('/api/tasks/').json()==[]

def test_unauthenticated_cannot_create_tasks(db):
    assert APIClient().post('/api/tasks/',{}).status_code==403

def test_live_execution_requires_configuration(task,settings):
    settings.LIVE_EXECUTION_ENABLED=False
    c=APIClient();c.force_authenticate(task.owner)
    assert c.post(f'/api/tasks/{task.id}/start/').status_code==400
    task.refresh_from_db();assert task.status=='DRAFT'

def patch_for(task):
    return PatchSet.objects.create(task=task,base_sha=task.base_sha,digest='b'*64,diff='patch',files=['x.py'],contents={'x.py':'x=2\n'})

def test_approval_requires_final_verification_for_exact_digest(task):
    task.status='AWAITING_APPROVAL';task.save();p=patch_for(task)
    with pytest.raises(ValidationError):approve(task.id,task.owner,p.digest)
    run=AgentRun.objects.create(task=task)
    VerificationRecord.objects.create(task=task,run=run,phase='final',status='passed',exit_code=0,patch_digest='wrong')
    with pytest.raises(ValidationError):approve(task.id,task.owner,p.digest)
    VerificationRecord.objects.create(task=task,run=run,phase='final',status='passed',exit_code=0,patch_digest=p.digest)
    assert approve(task.id,task.owner,p.digest).status=='APPROVED'

def test_stale_patch_approval_rejected(task):
    task.status='AWAITING_APPROVAL';task.save();patch_for(task)
    with pytest.raises(ValidationError):approve(task.id,task.owner,'old-digest')

def test_invalid_transition_rejected(task):
    with pytest.raises(ValidationError):transition(task.id,'PR_CREATED')

def test_login_requires_csrf(task):
    c=Client(enforce_csrf_checks=True)
    assert c.post('/api/auth/login/',{'username':'noor','password':'test-password'}).status_code==403
    token=c.get('/api/auth/session/').json()['csrf_token']
    r=c.post('/api/auth/login/',data=json.dumps({'username':'noor','password':'test-password'}),content_type='application/json',HTTP_X_CSRFTOKEN=token)
    assert r.status_code==200
    assert r.json()['csrf_token']!=token
    assert c.cookies['sessionid']['httponly']

class ScriptedProvider:
    def __init__(self,steps):self.steps=iter(steps);self.feedback=[]
    def turn(self,messages,tools,run):
        self.feedback=list(messages)
        name,args=next(self.steps)
        return {'role':'assistant','content':'','tool_calls':[{'id':str(run.iteration),'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]}
class FakeVerifier:
    def __init__(self):self.seen=[]
    def verify(self,files,on_created=None):
        self.seen.append(dict(files));passed='return x + 1' in files['x.py']
        return SimpleNamespace(status='passed' if passed else 'failed',exit_code=0 if passed else 1,stdout='1 passed' if passed else 'assert 1 == 2 failed',stderr='',duration_ms=10)

def test_agent_observes_failure_revises_and_checkpoints(task):
    task.status='PREPARING';task.save();run=AgentRun.objects.create(task=task)
    provider=ScriptedProvider([
      ('read_file',{'path':'x.py'}),('set_plan',{'steps':['Fix increment','Verify regression']}),
      ('run_tests',{}),('apply_patch',{'path':'x.py','old_text':'return x','new_text':'return x + 1'}),
      ('git_diff',{}),('finish',{'summary':'Corrected increment to add one.','limitations':'Only the configured test preset was checked.'})])
    v=FakeVerifier();execute_run(task,run,provider,v,{'x.py':'def increment(x):\n    return x\n'})
    task.refresh_from_db();assert task.status=='AWAITING_APPROVAL'
    assert len(v.seen)==3 and 'return x + 1' in v.seen[-1]['x.py']
    assert task.tests.filter(phase='final',status='passed').exists()
    assert task.patches.count()==1
    assert any('assert 1 == 2 failed' in str(m) for m in provider.feedback)
    assert run.tools.count()==6 and not task.reviews.exists()

def test_cancellation_prevents_next_model_call(task):
    task.cancel_requested=True;task.save();run=AgentRun.objects.create(task=task)
    with pytest.raises(InterruptedError):execute_run(task,run,ScriptedProvider([]),FakeVerifier(),{'x.py':'return 1'})

def test_iteration_limit_keeps_task_from_approval(task):
    task.status='PREPARING';task.max_iterations=1;task.save();run=AgentRun.objects.create(task=task)
    with pytest.raises(BudgetExceeded):execute_run(task,run,ScriptedProvider([('inspect_repo_tree',{})]),FakeVerifier(),{'x.py':'return x'})
    task.refresh_from_db();assert task.status!='AWAITING_APPROVAL'

def test_revisited_patch_becomes_latest_checkpoint(task):
    from agent_engine.loop import checkpoint
    w=WorkingCopy({'x.py':'x = 0\n'})
    w.files['x.py']='x = 1\n';first=checkpoint(task,w)
    w.files['x.py']='x = 2\n';checkpoint(task,w)
    w.files['x.py']='x = 1\n';last=checkpoint(task,w)
    assert last.digest==first.digest and last.id!=first.id
    assert task.patches.order_by('-created_at').first().id==last.id

def test_secret_redaction():
    from agent_engine.redaction import redact
    assert redact({'api_key':'value'})=={'api_key':'[REDACTED]'}
    assert 'ghp_' not in redact('token ghp_abcdefghijklmnop')

@pytest.mark.parametrize('scope',['task_retry','account'])
def test_budget_blocks_paid_call_using_previous_recorded_usage(task,settings,scope,monkeypatch):
    from unittest.mock import Mock
    from agent_engine.provider import Provider
    from coding_tasks.models import UsageRecord
    settings.AI_API_KEY='test-key';settings.AI_ACCOUNT_BUDGET='4.00'
    previous_task=task if scope=='task_retry' else CodingTask.objects.create(owner=task.owner,repository=task.repository,title='Earlier task',description='Earlier work')
    previous_run=AgentRun.objects.create(task=previous_task)
    UsageRecord.objects.create(run=previous_run,requested_model='test',returned_model='test',input_tokens=1,output_tokens=1,rates={},estimated_cost=Decimal('0.0499') if scope=='task_retry' else Decimal('3.9999'),latency_ms=0)
    monkeypatch.setattr('agent_engine.provider.OpenAI',Mock())
    provider=Provider();provider.client=Mock()
    run=AgentRun.objects.create(task=task)
    with pytest.raises(BudgetExceeded):provider.turn([{'role':'user','content':'Fix one bug'}],[],run)
    provider.client.chat.completions.create.assert_not_called()

def test_student_output_limit_is_sent_and_usage_recorded(task,settings,monkeypatch):
    from unittest.mock import Mock
    from agent_engine.provider import Provider
    settings.AI_API_KEY='test-key';settings.AI_ACCOUNT_BUDGET='4.00'
    monkeypatch.setattr('agent_engine.provider.OpenAI',Mock())
    provider=Provider();provider.client=Mock()
    provider.client.chat.completions.create.return_value=SimpleNamespace(
        usage=SimpleNamespace(model_dump=lambda:{'prompt_tokens':100,'completion_tokens':20}),
        model='test',choices=[SimpleNamespace(message=SimpleNamespace(model_dump=lambda **kw:{'role':'assistant','content':'Inspect the relevant file.'}))])
    run=AgentRun.objects.create(task=task)
    provider.turn([{'role':'user','content':'Fix one bug'}],[],run)
    assert provider.client.chat.completions.create.call_args.kwargs['max_tokens']==2048
    assert task.max_cost=='0.05' and run.usage.count()==1


def test_last_test_slot_is_preserved_for_final_verification(task):
    task.status='PREPARING';task.save();run=AgentRun.objects.create(task=task)
    provider=ScriptedProvider([
        ('set_plan',{'steps':['Fix increment and verify']}),
        ('apply_patch',{'path':'x.py','old_text':'return x','new_text':'return x + 1'}),
        ('run_tests',{}),('run_tests',{}),('run_tests',{}),
        ('git_diff',{}),('finish',{'summary':'Fixed increment.','limitations':'Small fixture only.'})])
    verifier=FakeVerifier()
    execute_run(task,run,provider,verifier,{'x.py':'def increment(x):\n    return x\n'})
    assert len(verifier.seen)==4
    assert run.tools.filter(name='run_tests',status='FAILED').count()==1
    task.refresh_from_db();assert task.status=='AWAITING_APPROVAL'
