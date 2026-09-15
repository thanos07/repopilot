import io
import tarfile
from unittest.mock import patch
import pytest
from django.contrib.auth.models import User
from django.test import Client
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError
from repositories.models import Repository
from coding_tasks.models import CodingTask, AgentRun, PatchSet, TestRun as Verification, ReviewDecision
from coding_tasks.lifecycle import approve
from integrations.github.publish import publish
from integrations.github.client import snapshot, GitHubError
from agent_engine.redaction import redact

@pytest.fixture
def owned(db):
    user=User.objects.create_user('operator',is_staff=True)
    repo=Repository.objects.create(owner=user,github_id=123,full_name='example/python')
    return CodingTask.objects.create(owner=user,repository=repo,title='Fix',description='Fix',base_sha='a'*40)

@pytest.mark.parametrize('action',['start','cancel','approve','publish'])
def test_nonstaff_cannot_mutate(owned,action):
    owned.owner.is_staff=False;owned.owner.save()
    c=APIClient();c.force_authenticate(owned.owner)
    assert c.post(f'/api/tasks/{owned.id}/{action}/',{}).status_code==403
    owned.refresh_from_db();assert owned.status=='DRAFT'

@pytest.mark.parametrize('url',['/api/tasks/','/api/repositories/'])
def test_nonstaff_cannot_create(owned,url):
    owned.owner.is_staff=False;owned.owner.save()
    c=APIClient();c.force_authenticate(owned.owner)
    with patch('coding_tasks.views.metadata') as remote:
        assert c.post(url,{'url':'https://github.com/a/b'}).status_code==403
        remote.assert_not_called()

@pytest.mark.parametrize('action',['start','cancel','approve','publish'])
def test_other_staff_cannot_mutate(owned,action):
    other=User.objects.create_user('other',is_staff=True)
    c=APIClient();c.force_authenticate(other)
    assert c.post(f'/api/tasks/{owned.id}/{action}/',{}).status_code==404

def checkpoint(t,code):
    p=PatchSet.objects.create(task=t,base_sha=t.base_sha,digest='b'*64,contents={'x.py':'x=2'},files=['x.py'],diff='patch')
    run=AgentRun.objects.create(task=t)
    Verification.objects.create(task=t,run=run,phase='final',patch_digest=p.digest,status='passed',exit_code=code)
    return p

def test_nonzero_pass_record_cannot_approve(owned):
    owned.status='AWAITING_APPROVAL';owned.save();p=checkpoint(owned,1)
    with pytest.raises(ValidationError):approve(owned.id,owned.owner,p.digest)
    assert not owned.reviews.exists()

def test_publication_rechecks_verification_before_network(owned):
    owned.status='PUBLISHING';owned.save();p=checkpoint(owned,1)
    ReviewDecision.objects.create(task=owned,patch=p,reviewer=owned.owner)
    with patch('integrations.github.publish.AppClient') as client:
        with pytest.raises(GitHubError):publish(owned.id)
        client.assert_not_called()

@pytest.mark.parametrize('name',['/root/x.py','root/../x.py','root\\x.py'])
def test_archive_unsafe_names(name):
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w:gz') as t:
        member=tarfile.TarInfo(name);member.size=3;t.addfile(member,io.BytesIO(b'x=1'))
    with patch('integrations.github.client.httpx.stream') as stream:
        response=stream.return_value.__enter__.return_value
        response.status_code=200;response.iter_bytes.return_value=[buf.getvalue()]
        with pytest.raises(GitHubError):snapshot('example/python','a'*40)

def test_headers(db):
    response=Client().get('/api/auth/session/')
    assert response['X-Frame-Options']=='DENY'
    assert response['X-Content-Type-Options']=='nosniff'
    assert response['Referrer-Policy']=='same-origin'

@pytest.mark.parametrize('key',['Authorization','E2B_API_KEY','GITHUB_APP_PRIVATE_KEY','Cookie','refresh_token'])
def test_sensitive_keys(key):
    assert redact({key:'sensitive'})[key]=='[REDACTED]'

def test_private_key_redaction():
    assert 'secret' not in redact('-----BEGIN RSA PRIVATE KEY-----\nsecret\n-----END RSA PRIVATE KEY-----')

def test_staff_create_ignores_client_budget_override(owned):
    c=APIClient();c.force_authenticate(owned.owner)
    response=c.post('/api/tasks/',{'repository_id':str(owned.repository_id),'title':'Fix','description':'Fix','max_cost':'999','max_tools':999})
    assert response.status_code==201
    created=CodingTask.objects.get(pk=response.json()['id'])
    assert str(created.max_cost)=='0.050000' and created.max_tools==24

def test_session_operator_capability(owned):
    c=APIClient();c.force_authenticate(owned.owner)
    assert c.get('/api/auth/session/').json()['can_operate'] is True
    owned.owner.is_staff=False;owned.owner.save()
    assert c.get('/api/auth/session/').json()['can_operate'] is False

@pytest.mark.parametrize('variable,value',[('DJANGO_SECRET_KEY','short'),('DJANGO_ALLOWED_HOSTS','*'),('FRONTEND_ORIGINS','https://*.example.com'),('SECURE_HSTS_SECONDS','-1')])
def test_production_configuration_fails_closed(variable,value):
    import os,subprocess,sys
    env={**os.environ,'DJANGO_DEBUG':'false','DJANGO_SECRET_KEY':'abcdefghij0123456789'*4,'DJANGO_ALLOWED_HOSTS':'example.com','FRONTEND_ORIGINS':'https://example.com','DATABASE_URL':'postgresql://unused:unused@localhost/db','SECURE_HSTS_SECONDS':'0'}
    env[variable]=value
    result=subprocess.run([sys.executable,'-c','import config.settings'],env=env,capture_output=True,text=True)
    assert result.returncode!=0 and 'RuntimeError' in result.stderr

def test_browser_accept_header_uses_json_renderer(db):
    response = Client().get(
        '/api/auth/session/',
        HTTP_ACCEPT='text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    )
    assert response.status_code == 200
    assert response['Content-Type'].startswith('application/json')
