'use client';

import {useEffect, useState} from 'react';
import {ArrowRight, ArrowUpRight, Check, ChevronDown, ChevronRight, Code2, FileCode2, GitBranch, GitPullRequest, Home, Layers, ListTodo, LoaderCircle, Menu, Plus, Search, Settings, ShieldCheck, Terminal, X, Clock3, PanelRightClose, PanelRightOpen, CircleAlert, Github, ExternalLink} from 'lucide-react';

type Event = {id: number; kind: string; message: string; created_at: string};
type Verification = {id: number; phase: string; status: string; exit_code: number|null; stdout: string; stderr: string; duration_ms: number};
type Patch = {id: string; digest: string; diff: string; files: string[]};
type Task = {id: string; title: string; description: string; status: string; repository: {id: string; full_name: string}; base_sha: string; plan: string[]; summary: string; limitation: string; events: Event[]; tests: Verification[]; patch: Patch|null; cost: string; max_cost?: string; model: string; tool_count: number; is_demo?: boolean; pr_url?: string; usage?:{input_tokens:number;output_tokens:number;cached_tokens:number|null;cache_hit_percent:number|null;calls:number;cost_basis:string}; tools?:{id:number;name:string;status:string;duration_ms:number}[]};
const API = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/$/, '');
let csrf = '';
async function request(path: string, init: RequestInit = {}) {
  if (!API) {
    throw new Error(
      'This preview is read-only. Connect the Django API to run tasks.'
    );
  }

  let res: Response;
  try {
    res = await fetch(API + path, {
      ...init,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf,
        ...init.headers,
      },
    });
  } catch {
    throw new Error(
      'Could not reach the server. Check your connection and that the backend is running. Refresh the task status before repeating an action.'
    );
  }

  if (res.status >= 500) {
    throw new Error(
      `The server could not complete the request (HTTP ${res.status}). Refresh the task status before repeating an action.`
    );
  }

  if (res.status === 204) return {};

  let data;
  try {
    data = await res.json();
  } catch {
    throw new Error(
      `The server returned an unreadable response (HTTP ${res.status}). Refresh the task status before repeating an action.`
    );
  }

  if (!res.ok) {
    const detail =
      data && typeof data.detail === 'string'
        ? data.detail.trim()
        : '';

    throw new Error(
      detail
        ? `${detail} (HTTP ${res.status})`
        : `The request could not be completed (HTTP ${res.status}).`
    );
  }

  return data;
}

const demo: Task = {
  id:'example-coupon', title:'Fix duplicate coupon redemption', description:'A customer can redeem the same coupon more than once. Return a clear error when a coupon has already been redeemed, and add a regression test for repeat redemption.', status:'AWAITING_APPROVAL', repository:{id:'example', full_name:'repopilot-examples/coupon-service'}, base_sha:'b41e7a2',
  plan:['Locate the redemption flow and existing tests','Add a guard for previously redeemed coupons','Add a regression test for repeat redemption','Run verification and inspect the final diff'], summary:'Reject a second redemption before updating the coupon. Cover the original behavior and the duplicate redemption case.', limitation:'Illustrative example only. These changes and test results were not produced by a live agent run. Concurrency behavior is outside this example.',
  events:[{id:1,kind:'search_code',message:'Located the redemption handler',created_at:''},{id:2,kind:'read_file',message:'Read coupon service and existing tests',created_at:''},{id:3,kind:'plan',message:'Prepared a four-step implementation plan',created_at:''},{id:4,kind:'apply_patch',message:'Updated the handler and regression test',created_at:''},{id:5,kind:'run_tests',message:'Example verification report available',created_at:''},{id:6,kind:'review',message:'Prepared the change for inspection',created_at:''}],
  tests:[{id:1,phase:'final',status:'passed',exit_code:0,stdout:'Illustrative output — not a live execution\n\ntests/test_coupons.py::test_redeem_coupon PASSED\ntests/test_coupons.py::test_reject_repeat_redemption PASSED\n\n2 passed',stderr:'',duration_ms:0}],
  patch:{id:'example',digest:'illustrative',files:['src/coupons.py','tests/test_coupons.py'],diff:'diff --git a/src/coupons.py b/src/coupons.py\n--- a/src/coupons.py\n+++ b/src/coupons.py\n@@ -8,4 +8,7 @@\n def redeem_coupon(coupon):\n+    if coupon.redeemed:\n+        raise ValueError("Coupon already redeemed")\n+\n     coupon.redeemed = True\n     coupon.save()\n     return coupon\ndiff --git a/tests/test_coupons.py b/tests/test_coupons.py\n--- a/tests/test_coupons.py\n+++ b/tests/test_coupons.py\n@@ -12,0 +13,5 @@\n+def test_reject_repeat_redemption(coupon):\n+    redeem_coupon(coupon)\n+    with pytest.raises(ValueError, match="already redeemed"):\n+        redeem_coupon(coupon)\n+'},cost:'—',model:'Example',tool_count:0,is_demo:true
};
const nav = [{name:'Home',icon:Home},{name:'Repositories',icon:Layers},{name:'Tasks',icon:ListTodo}];
const activeStates = ['QUEUED','PREPARING','ANALYZING','PLANNING','IMPLEMENTING','TESTING','REVIEWING','PUBLISHING'];
function readable(s:string){return s.toLowerCase().replaceAll('_',' ')}

export default function Workspace(){
 const [section,setSection]=useState('Tasks'); const [tab,setTab]=useState('Summary');const [task,setTask]=useState<Task>(demo); const [tasks,setTasks]=useState<Task[]>([]);const [repos,setRepos]=useState<{id:string;full_name:string}[]>([]);
 const [rail,setRail]=useState(true); const [mobile,setMobile]=useState(false);const [dialog,setDialog]=useState('');const [error,setError]=useState('');const [notice,setNotice]=useState('');const [busy,setBusy]=useState(false); const [user,setUser]=useState(''); const [query,setQuery]=useState('');const [selectedEvent,setSelectedEvent]=useState<number|null>(null); const [toolDetail,setToolDetail]=useState<Record<string,unknown>|null>(null);
 useEffect(()=>{if(!dialog)return;const prior=document.activeElement as HTMLElement|null;const modal=document.querySelector<HTMLElement>('[role=dialog]');const focusable=()=>Array.from(modal?.querySelectorAll<HTMLElement>('button:not(:disabled),input,select,textarea,a[href]')||[]);focusable()[0]?.focus();const key=(e:KeyboardEvent)=>{if(e.key==='Escape')setDialog('');if(e.key==='Tab'){const a=focusable();const first=a[0],last=a[a.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus()}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus()}}};document.addEventListener('keydown',key);return ()=>{document.removeEventListener('keydown',key);prior?.focus()}},[dialog]);
 useEffect(()=>{const ctx=(document as Document & {modelContext?:{registerTool:(t:unknown,o:{signal:AbortSignal})=>unknown}}).modelContext;if(!ctx)return;const life=new AbortController();Promise.resolve().then(()=>ctx.registerTool({name:'inspect_current_task',description:'Read the task currently visible in RepoPilot. Illustrative tasks are explicitly marked.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true,untrustedContentHint:true},execute:(input:unknown)=>{if(!input||typeof input!=='object'||Object.keys(input).length)throw new Error('Expected an empty object');return {id:task.id,title:task.title,status:task.status,illustrative:!!task.is_demo,summary:task.summary}}},{signal:life.signal})).catch(()=>{});return()=>life.abort()},[task]);
 async function refresh(){const [t,r]=await Promise.all([request('/tasks/'),request('/repositories/')]);setTasks(t);setRepos(r)}
 useEffect(()=>{if(API) request('/auth/session/').then(d=>{csrf=d.csrf_token;setUser(d.username||'');if(d.username)return refresh()}).catch(e=>setError(e.message))},[]);
 useEffect(()=>{if(task.is_demo || !activeStates.includes(task.status))return; const t=setInterval(()=>request('/tasks/'+task.id+'/').then(setTask).catch(e=>setError(e.message)),2000);return ()=>clearInterval(t)},[task.id,task.status,task.is_demo]);
 async function action(path:string, body:object={}){setError('');setBusy(true);try{const data=await request(path,{method:'POST',body:JSON.stringify(body)});if(data.id)setTask(data);await refresh();return data}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 async function submit(e:React.FormEvent<HTMLFormElement>){e.preventDefault();const f=new FormData(e.currentTarget);setError('');setBusy(true);try{
   if(dialog==='login'){const d=await request('/auth/login/',{method:'POST',body:JSON.stringify({username:f.get('username'),password:f.get('password')})});csrf=d.csrf_token;setUser(d.username);await refresh()}
   if(dialog==='repository'){await request('/repositories/',{method:'POST',body:JSON.stringify({url:f.get('url')})});await refresh()}
   if(dialog==='task'){const d=await request('/tasks/',{method:'POST',body:JSON.stringify({repository_id:f.get('repository'),title:f.get('title'),description:f.get('description')})});setTask(d);setSection('Tasks');setTab('Summary');await refresh()}
   setDialog('');
 }catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 function downloadPatch(){if(!task.patch)return;const u=URL.createObjectURL(new Blob([task.patch.diff],{type:'text/plain'}));const a=document.createElement('a');a.href=u;a.download=task.is_demo?'illustrative-example.patch':'repopilot.patch';a.click();URL.revokeObjectURL(u)}
 const shown=tasks.filter(t=>t.title.toLowerCase().includes(query.toLowerCase())); const isRunning=activeStates.includes(task.status);
 return <div className="app">
  <aside className={'sidebar '+(mobile?'open':'')}>
   <a className="brand" href="/" aria-label="RepoPilot home"><span className="brandmark"><Code2 size={21}/></span>RepoPilot<span className="version">BETA</span></a>
   <button className="workspace-select" onClick={()=>setSection('Home')}><span className="avatar">N</span><span>{user || 'Personal workspace'}<small>RepoPilot workspace</small></span><ChevronDown size={15}/></button>
   <button className="primary new-task" onClick={()=>setDialog(API&&user?'task':'connection')}><Plus size={17}/>New task<span>＋</span></button>
   <p className="nav-caption">WORKSPACE</p>
   <nav>{nav.map(({name,icon:Icon})=><button key={name} className={section===name?'navitem selected':'navitem'} onClick={()=>{setSection(name);setMobile(false)}}><Icon size={18}/>{name}{name==='Tasks'&&<span className="nav-count">{tasks.length||1}</span>}</button>)}</nav>
   <div className="sidebar-repos"><p className="nav-caption">REPOSITORIES<button aria-label="Add repository" onClick={()=>setDialog(API&&user?'repository':'connection')}><Plus size={14}/></button></p>{(repos.length?repos:[demo.repository]).slice(0,5).map(r=><button className="repo-nav" key={r.id} onClick={()=>setSection('Repositories')}><Github size={16}/><span>{r.full_name.split('/')[1]}</span></button>)}</div>
   <div className="sidebar-bottom"><div className="boundary"><ShieldCheck size={18}/><div>You're in control<small>Review changes before publishing.</small></div></div><button className={'navitem '+(section==='Settings'?'selected':'')} onClick={()=>setSection('Settings')}><Settings size={18}/>Settings</button><button className="profile" onClick={()=>setDialog(API?'login':'connection')}><span className="avatar">{(user||'N')[0].toUpperCase()}</span><span>{user||'Noor’s workspace'}<small>{API?(user?'Signed in':'Sign in to your backend'):'Read-only product preview'}</small></span><ChevronDown size={15}/></button></div>
  </aside>
  <main>
   <header className="topbar"><div className="breadcrumb"><button className="mobile-menu icon-button" aria-label="Open navigation" onClick={()=>setMobile(!mobile)}><Menu size={20}/></button><span>Workspace</span><ChevronRight size={14}/><strong>{section}</strong></div><div className="top-actions"><span className="preview-badge">{API?'API configured':'Preview'}</span><a href="https://github.com" target="_blank" rel="noreferrer" aria-label="GitHub"><Github size={19}/></a></div></header>
   {!API&&<div className="preview-notice"><span><Code2 size={15}/> Explore an illustrative task. Live execution requires the Django backend and provider credentials.</span><button onClick={()=>setSection('Settings')}>Connection details <ArrowUpRight size={14}/></button></div>}
   {error&&<div className="message error" role="alert">{error}<button aria-label="Dismiss error" onClick={()=>setError('')}><X size={16}/></button></div>}{notice&&<div className="message" role="status">{notice}<button aria-label="Dismiss notification" onClick={()=>setNotice('')}><X size={16}/></button></div>}
   {section==='Tasks'&&<>
    <div className="task-heading"><div className="task-kicker"><span className="mono">{task.is_demo?'EXAMPLE TASK':`TASK ${task.id.slice(0,8)}`}</span><span className={'status '+(task.status==='FAILED'?'failed':'')}><span className="status-dot"/>{readable(task.status)}</span></div><div className="title-row"><h1>{task.title}</h1><button className="icon-button" aria-label={rail?'Hide activity':'Show activity'} onClick={()=>setRail(!rail)}>{rail?<PanelRightClose size={20}/>:<PanelRightOpen size={20}/>}</button></div><div className="task-meta"><span><Github size={14}/>{task.repository.full_name}</span><span><GitBranch size={14}/>{task.base_sha?task.base_sha.slice(0,7):'Base commit pending'}</span><span><ShieldCheck size={14}/>Human approval required</span></div></div>
    <div className="tabs-row"><div role="tablist" aria-label="Task detail">{['Summary','Changes','Verification'].map(t=><button key={t} role="tab" aria-selected={tab===t} onClick={()=>setTab(t)} className={tab===t?'tab active':'tab'}>{t}{t==='Changes'&&task.patch&&<span>{task.patch.files.length}</span>}</button>)}</div><span className="task-cost">Model cost <b className="mono">{task.cost==='—'?'—':'$'+task.cost}</b></span></div>
    <div className={'workspace-body '+(!rail?'wide':'')}><section className="task-content" role="tabpanel" aria-label={tab}>
     {tab==='Summary'&&<>
      <div className="section-label"><FileCode2 size={17}/><h2>The task</h2>{task.is_demo&&<span className="small-tag">Illustrative example</span>}</div><p className="issue-copy">{task.description}</p>
      <div className="plan-card"><div className="section-label"><ListTodo size={18}/><h2>Implementation plan</h2><span className="muted">{task.plan.length} steps</span></div>{task.plan.length?task.plan.map((s,i)=><div className="plan-step" key={s}><span className={task.is_demo||task.patch?'step-check':'step-number'}>{task.is_demo||task.patch?<Check size={13}/>:i+1}</span><span>{s}</span></div>):<p className="muted">The agent will prepare a plan after inspecting the repository.</p>}</div>
      <div className="section-label"><GitPullRequest size={18}/><h2>Change summary</h2></div>{!task.is_demo&&task.max_cost&&<p className="muted">API estimate: ${Number(task.cost).toFixed(4)} used / ${Number(task.max_cost).toFixed(2)} task limit. Sandbox charges excluded.</p>}<p className="issue-copy">{task.summary||'No change has been prepared yet.'}</p>
      {task.patch&&<div className="file-list">{task.patch.files.map(f=><button key={f} onClick={()=>setTab('Changes')}><FileCode2 size={17}/><span className="mono">{f}</span><span className="file-action">View diff <ArrowUpRight size={14}/></span></button>)}</div>}
      {task.limitation&&<div className="limitation"><CircleAlert size={18}/><div><strong>{task.is_demo?'About this example':'Review notes'}</strong><p>{task.limitation}</p></div></div>}
      {['DRAFT','FAILED'].includes(task.status)&&<button className="primary" disabled={busy} onClick={()=>action('/tasks/'+task.id+'/start/')}>{busy?<LoaderCircle className="spin" size={16}/>:<ArrowRight size={16}/>}{task.status==='FAILED'?'Retry saved task':'Start agent'}</button>}
      {isRunning&&<button className="secondary" disabled={busy} onClick={()=>action('/tasks/'+task.id+'/cancel/')}>Stop task</button>}
      {task.status==='AWAITING_APPROVAL'&&<div className="approval"><div><ShieldCheck size={22}/><div><strong>Ready for your review</strong><p>Inspect the diff and verification before publishing.</p></div></div><button className="primary" onClick={()=>task.is_demo?setNotice('This is an illustrative task. Connect your backend to review and publish real changes.'):setDialog('approve')}>Review change <ArrowRight size={16}/></button></div>}
      {task.status==='APPROVED'&&<button className="primary" disabled={busy} onClick={()=>action('/tasks/'+task.id+'/publish/')}>Create draft pull request <GitPullRequest size={17}/></button>}
      {task.pr_url&&<a className="primary inline-link" href={task.pr_url} target="_blank" rel="noreferrer">Open draft pull request <ExternalLink size={16}/></a>}
     </>}
     {tab==='Changes'&&<><div className="section-label"><GitBranch size={18}/><h2>Code changes</h2><button className="secondary small" disabled={!task.patch} onClick={downloadPatch}>Download patch</button></div>{task.patch?<div className="diff"><div className="diff-header"><span>{task.patch.files.length} files changed</span><span>{task.is_demo?'Illustrative patch':'Unified diff'}</span></div><pre>{task.patch.diff.split('\n').map((l,i)=><div key={i} className={l.startsWith('+')&&!l.startsWith('+++')?'added':l.startsWith('-')&&!l.startsWith('---')?'removed':l.startsWith('@@')?'hunk':''}><span className="line-no">{i+1}</span><code>{l||' '}</code></div>)}</pre></div>:<div className="empty"><FileCode2/><h3>No patch yet</h3><p>Code changes will appear after the agent edits the repository.</p></div>}</>}
     {tab==='Verification'&&<><div className="section-label"><Terminal size={18}/><h2>Verification</h2></div>{task.tests.length?task.tests.map(t=><div className="test-card" key={t.id}><div><strong>{t.phase==='baseline'?'Baseline tests':'Final tests'}</strong><span className={'test-status '+t.status}>{t.status}</span></div><p className="muted">{task.is_demo?'Illustrative report — no tests executed':`Exit code: ${t.exit_code??'unavailable'} · ${t.duration_ms} ms`}</p><pre>{t.stdout}{t.stderr?'\n'+t.stderr:''}</pre></div>):<div className="empty"><Terminal/><h3>No verification recorded</h3><p>Not run is different from passed. Actual results will appear here.</p></div>}</>}
    </section>{rail&&<aside className="activity"><div className="activity-title"><h2>Agent activity</h2><span className="small-tag">{task.is_demo?'EXAMPLE':isRunning?'RUNNING':'RECORDED'}</span></div><p className="activity-sub">A trace of actions and evidence.</p><div className="timeline">{task.events.map((e,i)=><div className="timeline-item" key={e.id}><span className="timeline-icon"><Check size={12}/></span><button onClick={()=>setSelectedEvent(selectedEvent===e.id?null:e.id)}><strong>{readable(e.kind)}</strong><span>{e.message}</span>{selectedEvent===e.id&&<span className="event-detail">{e.created_at?new Date(e.created_at).toLocaleString():'Illustrative sequence'} · Event {i+1}</span>}</button></div>)}</div><div className="usage"><div className="section-label"><h2>Run details</h2></div><dl><div><dt>Model</dt><dd>{task.model||'Not called'}</dd></div><div><dt>Tool calls</dt><dd className="mono">{task.is_demo?'—':task.tool_count}</dd></div><div><dt>API cost estimate</dt><dd className="mono">{task.cost==='—'?'—':'$'+task.cost}</dd></div><div><dt>Execution</dt><dd>{task.is_demo?'Illustrative':'Isolated sandbox'}</dd></div></dl><p>Usage is recorded from provider responses. Sandbox charges are separate.</p>{task.usage&&<details><summary>Token usage</summary><dl><div><dt>Input tokens</dt><dd>{task.usage.input_tokens}</dd></div><div><dt>Output tokens</dt><dd>{task.usage.output_tokens}</dd></div><div><dt>Cached tokens</dt><dd>{task.usage.cached_tokens??"Unavailable"}</dd></div><div><dt>Cache hit rate</dt><dd>{task.usage.cache_hit_percent==null?"Unavailable":task.usage.cache_hit_percent+"%"}</dd></div></dl><p>{task.usage.cost_basis}</p></details>}{!!task.tools?.length&&<details><summary>Tool execution details</summary>{task.tools.map(t=><button key={t.id} className="tool-record" onClick={()=>request(`/tasks/${task.id}/tools/${t.id}/`).then(setToolDetail).catch(e=>setError(e.message))}>{t.name} · {t.status} · {t.duration_ms} ms</button>)}{toolDetail&&<pre className="tool-payload">{JSON.stringify(toolDetail,null,2)}</pre>}</details>}</div></aside>}</div>
   </>}
   {section==='Home'&&<div className="page-content"><div className="home-intro"><span className="eyebrow">YOUR CODING WORKSPACE</span><h1>What should RepoPilot<br/>work on?</h1><p>Start with a repository and a specific task.<br/>Review the code, tests, and evidence before publishing.</p><button className="primary" onClick={()=>setDialog(API&&user?'task':'connection')}><Plus size={17}/>Create a task</button></div><div className="section-label"><h2>Recent tasks</h2><span className="muted">{tasks.length?'Your workspace':'Explore the workflow'}</span></div>{(tasks.length?tasks:[demo]).map(t=><button className="task-list-row" key={t.id} onClick={()=>{setTask(t);setSection('Tasks')}}><span className="task-row-icon"><GitPullRequest size={19}/></span><span><strong>{t.title}</strong><small>{t.repository.full_name} {t.is_demo?'· Illustrative example':''}</small></span><span className="small-tag">{readable(t.status)}</span><ChevronRight size={18}/></button>)}</div>}
   {section==='Repositories'&&<div className="page-content"><div className="page-heading"><div><h1>Repositories</h1><p>Small Python repositories with a supported pytest setup.</p></div><button className="primary" onClick={()=>setDialog(API&&user?'repository':'connection')}><Plus size={16}/>Add repository</button></div>{(repos.length?repos:[demo.repository]).map(r=><div className="repository-card" key={r.id}><Github size={24}/><div><h2>{r.full_name}</h2><p>{r.id==='example'?'Illustrative repository':'Public repository · Python / pytest'}</p></div><span className="small-tag">{r.id==='example'?'EXAMPLE':'CONNECTED'}</span></div>)}</div>}
   {section==='Settings'&&<div className="page-content settings"><h1>Workspace settings</h1><p className="muted">Connections and execution boundaries.</p><div className="settings-card"><h2>Backend connection</h2><p>{API?API:'This product preview has no live execution backend attached.'}</p><p>Run the included Django API and configure NEXT_PUBLIC_API_URL when building the frontend. Model and sandbox keys stay on the server.</p><button className="secondary" disabled={!API} onClick={()=>setDialog('login')}>{user?'Sign in as another user':'Sign in'}</button>{user&&<button className="secondary" onClick={async()=>{try{await request('/auth/logout/',{method:'POST',body:'{}'});setUser('');setTasks([]);setRepos([]);setTask(demo);const d=await request('/auth/session/');csrf=d.csrf_token}catch(e){setError((e as Error).message)}}}>Sign out</button>}</div><div className="settings-card"><h2>Execution policy</h2><dl><div><dt>Repository support</dt><dd>Public Python / pytest</dd></div><div><dt>Code execution</dt><dd>Isolated sandbox only</dd></div><div><dt>Remote changes</dt><dd>Explicit approval required</dd></div><div><dt>Automatic merge</dt><dd>Never</dd></div></dl></div>{tasks.length>0&&<div className="settings-card"><h2>Find a task</h2><label className="search"><Search size={16}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search task titles"/></label>{shown.map(t=><button className="task-list-row" key={t.id} onClick={()=>{setTask(t);setSection('Tasks')}}>{t.title}<ArrowRight size={16}/></button>)}</div>}</div>}
  </main>
  {dialog&&<div className="modal-backdrop" onClick={e=>{if(e.target===e.currentTarget)setDialog('')}}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="dialog-title"><button className="modal-close icon-button" aria-label="Close dialog" onClick={()=>setDialog('')}><X size={20}/></button><h2 id="dialog-title">{dialog==='connection'?'Connect your execution backend':dialog==='login'?'Sign in':dialog==='repository'?'Add a repository':dialog==='approve'?'Approve this exact patch?':'Create a task'}</h2>
   {dialog==='connection'?<><p>This preview lets you inspect the workspace. Live tasks need the included Django backend, a model API key, and an E2B sandbox key.</p><p>Configure the backend using the project’s setup guide. Credentials are entered on your deployment platform, never in this preview.</p><button className="primary" onClick={()=>{setDialog('');setSection('Settings')}}>View settings <ArrowRight size={16}/></button></>:dialog==='approve'?<><p>Approval is bound to this patch and its base commit. Further edits require a new review.</p><p className="mono digest">{task.patch?.digest}</p><button className="secondary" onClick={()=>{setDialog('');setTab('Changes')}}>Inspect diff</button> <button className="primary" disabled={busy} onClick={async()=>{const d=await action('/tasks/'+task.id+'/approve/',{digest:task.patch?.digest});if(d)setDialog('')}}>Approve patch</button></>:<form onSubmit={submit}>
   {dialog==='login'?<><label>Username<input name="username" autoComplete="username" required autoFocus/></label><label>Password<input type="password" name="password" autoComplete="current-password" required/></label></>:dialog==='repository'?<label>Public GitHub repository URL<input name="url" type="url" placeholder="https://github.com/owner/repository" required autoFocus/></label>:<><label>Repository<select name="repository" required>{repos.map(r=><option key={r.id} value={r.id}>{r.full_name}</option>)}</select></label><label>Task title<input name="title" placeholder="Fix a specific bug" maxLength={240} required autoFocus/></label><label>Description<textarea name="description" rows={5} placeholder="Describe one small bug, the relevant file if known, and expected behavior." required maxLength={12000}/></label><p>New tasks use a $0.05 API estimate limit. Focus on one small Python fix.</p>{!repos.length&&<p>Add a repository before creating a task.</p>}</>}
   {error&&<p role="alert" className="form-error">{error}</p>}<button className="primary" disabled={busy||(dialog==='task'&&!repos.length)}>{busy?<LoaderCircle className="spin" size={17}/>:null}{dialog==='login'?'Sign in':dialog==='repository'?'Add repository':'Create draft task'}<ArrowRight size={16}/></button></form>}
  </section></div>}
 </div>
}