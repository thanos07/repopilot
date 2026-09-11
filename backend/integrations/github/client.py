import re
import io
import tarfile
import time
from pathlib import PurePosixPath
from urllib.parse import urlparse
import httpx
import jwt
from django.conf import settings

class GitHubError(RuntimeError): pass

def repo_name(url):
    p=urlparse(str(url))
    if p.scheme!='https' or p.netloc!='github.com' or p.query or p.fragment:
        raise GitHubError('Use a public https://github.com/owner/repository URL.')
    name=p.path.strip('/').removesuffix('.git')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',name):raise GitHubError('Invalid repository URL.')
    return name

def public_get(path):
    with httpx.Client(timeout=20,follow_redirects=False) as c:
        r=c.get('https://api.github.com'+path,headers={'Accept':'application/vnd.github+json'})
        if r.status_code!=200:raise GitHubError(f'GitHub returned {r.status_code}; check repository access or rate limits.')
        return r.json()

def metadata(name):
    data=public_get('/repos/'+name)
    if data.get('private'):raise GitHubError('Version 1 supports public repositories only.')
    return data

def snapshot(name,sha):
    if not re.fullmatch(r'[0-9a-f]{40}',sha):raise GitHubError('A pinned commit is required.')
    # Fixed codeload origin, bounded streaming, no redirects or host extraction.
    url=f'https://codeload.github.com/{name}/tar.gz/{sha}'
    raw=bytearray()
    with httpx.stream('GET',url,timeout=30,follow_redirects=False) as r:
        if r.status_code!=200:raise GitHubError('Could not download the pinned repository.')
        for chunk in r.iter_bytes():
            raw.extend(chunk)
            if len(raw)>5_000_000:raise GitHubError('Repository archive exceeds the 5 MB MVP limit.')
    files={};total=0;members=0
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        for m in archive:
            members+=1
            if members>3000:raise GitHubError('Repository has too many archive entries.')
            parts=PurePosixPath(m.name).parts[1:]
            if not parts:continue
            if '..' in parts or m.issym() or m.islnk():raise GitHubError('Symlinks and unsafe archive paths are unsupported.')
            if not m.isfile():continue
            if m.size>250_000:raise GitHubError('A repository file exceeds the 250 KB MVP limit.')
            total+=m.size
            if total>5_000_000 or len(files)>1000:raise GitHubError('Repository exceeds the MVP size limit.')
            if any(x in {'.git','node_modules','.venv','__pycache__'} or x.startswith('.env') for x in parts):continue
            if parts[-1].endswith(('.pem','.key','.p12')):continue
            path='/'.join(parts)
            stream=archive.extractfile(m)
            if stream is None:continue
            data=stream.read(250_001)
            try:text=data.decode('utf-8')
            except UnicodeDecodeError:continue
            if '\x00' in text:continue
            files[path]=text
    if not any(p.endswith('.py') for p in files):raise GitHubError('No Python source files found.')
    return files

class AppClient:
    def __init__(self):
        if not all([settings.GITHUB_APP_ID,settings.GITHUB_APP_PRIVATE_KEY,settings.GITHUB_INSTALLATION_ID]):raise GitHubError('GitHub App installation is not configured.')
        now=int(time.time())
        token=jwt.encode({'iat':now-60,'exp':now+500,'iss':settings.GITHUB_APP_ID},settings.GITHUB_APP_PRIVATE_KEY,algorithm='RS256')
        self.client=httpx.Client(base_url='https://api.github.com',timeout=30,headers={'Accept':'application/vnd.github+json','Authorization':'Bearer '+token})
        try:
            r=self.client.post(f'/app/installations/{settings.GITHUB_INSTALLATION_ID}/access_tokens')
            r.raise_for_status();self.client.headers['Authorization']='Bearer '+r.json()['token']
        except Exception:
            self.client.close();raise GitHubError('Could not authenticate the GitHub App installation.')
    def call(self,method,path,**kwargs):
        r=self.client.request(method,path,**kwargs)
        if r.status_code>=400:raise GitHubError(f'GitHub {method} failed with status {r.status_code}.')
        return r.json()
    def close(self):self.client.close()
