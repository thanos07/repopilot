"""Validate authored synthetic fixtures; this is NOT a live agent evaluation."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

def run(files):
    with tempfile.TemporaryDirectory() as folder:
        for name,content in files.items():(Path(folder)/name).write_text(content)
        p=subprocess.run([sys.executable,'-m','pytest','-q'],cwd=folder,capture_output=True,text=True,timeout=20)
        return p.returncode

if __name__=='__main__':
    results=[]
    for path in sorted((Path(__file__).resolve().parents[1]/'evals').glob('*/case.json')):
        case=json.loads(path.read_text())
        baseline=run(case['files']|case['acceptance_tests'])
        reference=run(case['reference_files']|case['acceptance_tests'])
        ok=baseline==1 and reference==0
        results.append({'id':case['id'],'baseline_exit':baseline,'reference_exit':reference,'fixture_valid':ok})
    print(json.dumps({'mode':'synthetic fixture validation, not agent performance','cases':results},indent=2))
    sys.exit(0 if all(r['fixture_valid'] for r in results) else 1)
