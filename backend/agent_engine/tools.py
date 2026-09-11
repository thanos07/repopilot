import difflib
import hashlib
import json
from pathlib import PurePosixPath
from pydantic import BaseModel, ConfigDict, Field

class ToolError(ValueError):pass
class Args(BaseModel):model_config=ConfigDict(extra='forbid')
class Empty(Args):pass
class Read(Args):
    path:str=Field(max_length=240)
    start_line:int=Field(default=1,ge=1)
    end_line:int=Field(default=180,ge=1)
class Search(Args):query:str=Field(min_length=2,max_length=120)
class Patch(Args):
    path:str=Field(max_length=240)
    old_text:str=Field(max_length=25000)
    new_text:str=Field(max_length=25000)
class Plan(Args):steps:list[str]=Field(min_length=1,max_length=8)
class Finish(Args):
    summary:str=Field(min_length=10,max_length=3000)
    limitations:str=Field(max_length=3000)

SCHEMAS={'inspect_repo_tree':(Empty,'List repository paths.'),'read_file':(Read,'Read a bounded line range.'),'search_code':(Search,'Search literal text, case-insensitive, up to 30 matches.'),'set_plan':(Plan,'Record concise implementation steps before editing.'),'apply_patch':(Patch,'Replace one exact unique text occurrence in a Python file. Empty old_text creates a new file.'),'git_diff':(Empty,'Get the unified diff against the pinned base.'),'run_tests':(Empty,'Run the fixed pytest preset in a fresh isolated sandbox.'),'finish':(Finish,'Request final verification and human review. Does not publish.')}

def specs():return [{'type':'function','function':{'name':n,'description':d,'parameters':s.model_json_schema()}} for n,(s,d) in SCHEMAS.items()]
def validate(name,args):
    if name not in SCHEMAS:raise ToolError('Unknown tool.')
    return SCHEMAS[name][0].model_validate(args).model_dump()

def safe_path(path):
    p=PurePosixPath(path)
    if p.is_absolute() or '..' in p.parts or '\\' in path or not p.parts or any(x.startswith('.') for x in p.parts):raise ToolError('Hidden or unsafe paths are not editable.')
    if p.suffix!='.py' or p.name in {'setup.py','conftest.py'}:raise ToolError('Only application/test Python files can be edited; setup.py and conftest.py are protected.')
    return str(p)

class WorkingCopy:
    """Bounded text snapshot. Uploaded source is never imported or executed here."""
    def __init__(self,files):self.base=dict(files);self.files=dict(files)
    def diff(self):
        lines=[]
        for path in sorted(set(self.base)|set(self.files)):
            before=self.base.get(path,'');after=self.files.get(path,'')
            if before==after:continue
            lines.append('diff --git a/'+path+' b/'+path+'\n')
            lines.extend(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='a/'+path if path in self.base else '/dev/null',tofile='b/'+path))
        result=''.join(lines)
        if len(result)>150000:raise ToolError('Patch exceeds the 150 KB limit.')
        return result
    def digest(self):return hashlib.sha256(self.diff().encode()).hexdigest()
    def changes(self):return {p:c for p,c in self.files.items() if self.base.get(p)!=c}
    def execute(self,name,args):
        if name=='inspect_repo_tree':return {'paths':sorted(self.files)[:1000]}
        if name=='read_file':
            p=args['path']
            if p not in self.files:raise ToolError('File not found.')
            start=args['start_line'];end=min(args['end_line'],start+199)
            return {'path':p,'content':'\n'.join(f'{i}: {l}' for i,l in enumerate(self.files[p].splitlines(),1) if start<=i<=end)[:16000]}
        if name=='search_code':
            matches=[];q=args['query'].lower()
            for p,c in self.files.items():
                for i,line in enumerate(c.splitlines(),1):
                    if q in line.lower():matches.append({'path':p,'line':i,'text':line[:300]})
                    if len(matches)>=30:return {'matches':matches,'truncated':True}
            return {'matches':matches}
        if name=='apply_patch':
            p=safe_path(args['path']);old=args['old_text'];new=args['new_text']
            if not old:
                if p in self.files:raise ToolError('Empty old_text is allowed only for a new file.')
                content=new
            else:
                content=self.files.get(p,'')
                if content.count(old)!=1:raise ToolError('old_text must match exactly one occurrence. Read the file again.')
                content=content.replace(old,new,1)
            if not content.endswith('\n'):content+='\n'
            if len(content.encode())>250000:raise ToolError('File too large.')
            before=self.files.get(p)
            self.files[p]=content
            try:
                if len(self.changes())>12:raise ToolError('At most 12 changed files are supported.')
                self.diff()
            except Exception:
                if before is None:del self.files[p]
                else:self.files[p]=before
                raise
            return {'path':p,'digest':self.digest(),'changed_files':list(self.changes())}
        if name=='git_diff':return {'diff':self.diff()[:30000],'digest':self.digest()}
        raise ToolError('Tool requires orchestration.')
