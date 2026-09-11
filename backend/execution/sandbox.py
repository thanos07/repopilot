import json
import time
from dataclasses import dataclass
from pathlib import PurePosixPath
from django.conf import settings

class SandboxError(RuntimeError): pass

@dataclass
class VerificationResult:
    status:str
    exit_code:int|None
    stdout:str=''
    stderr:str=''
    duration_ms:int=0

# This trusted runner exists only in the disposable sandbox, never on the API host.
RUNNER = r'''
import json,os,subprocess,tempfile,resource
def limits():
    resource.setrlimit(resource.RLIMIT_CPU,(100,100))
    resource.setrlimit(resource.RLIMIT_FSIZE,(2_000_000,2_000_000))
    resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
    try:
        p=subprocess.run(['/usr/local/bin/python','-m','pytest','-q','-p','no:cacheprovider'],cwd='/home/user/repo',stdout=out,stderr=err,timeout=110,preexec_fn=limits,env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':'/home/user','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','PYTHONDONTWRITEBYTECODE':'1'})
        code=p.returncode
    except subprocess.TimeoutExpired:
        code=124
    out.seek(0);err.seek(0)
    print(json.dumps({'exit_code':code,'stdout':out.read(16000).decode('utf-8','replace'),'stderr':err.read(8000).decode('utf-8','replace')}))
'''

class E2BVerifier:
    """One network-disabled sandbox per verification. No keys enter the guest."""
    def verify(self,files,on_created=None):
        if not settings.E2B_API_KEY or not settings.E2B_TEMPLATE:
            raise SandboxError('Set E2B_API_KEY and E2B_TEMPLATE to a template with Python and pytest preinstalled.')
        from e2b import Sandbox
        started=time.monotonic();sandbox=None
        try:
            sandbox=Sandbox.create(template=settings.E2B_TEMPLATE,api_key=settings.E2B_API_KEY,timeout=180,allow_internet_access=False)
            if on_created:on_created(sandbox.sandbox_id)
            for path,content in files.items():
                p=PurePosixPath(path)
                if p.is_absolute() or '..' in p.parts:raise SandboxError('Unsafe source path.')
                sandbox.files.write('/home/user/repo/'+path,content)
            sandbox.files.write('/tmp/repopilot_runner.py',RUNNER)
            result=sandbox.commands.run('python3 /tmp/repopilot_runner.py',timeout=125)
            # The guest output is evidence, never an instruction or approval.
            payload=json.loads(result.stdout)
            code=int(payload['exit_code'])
            status='passed' if code==0 else 'infrastructure_error' if code in {2,3,4,5,124} else 'failed'
            return VerificationResult(status,code,str(payload.get('stdout',''))[:16000],str(payload.get('stderr',''))[:8000],int((time.monotonic()-started)*1000))
        except SandboxError:raise
        except Exception as exc:
            # Do not expose SDK error text, which can contain request headers.
            raise SandboxError('Sandbox verification failed ('+type(exc).__name__+').') from exc
        finally:
            if sandbox:
                try:sandbox.kill()
                except Exception:
                    # The hard 180-second lifetime is a second cleanup boundary.
                    import logging
                    logging.getLogger(__name__).warning('Sandbox cleanup failed; expiry is the fallback.')
