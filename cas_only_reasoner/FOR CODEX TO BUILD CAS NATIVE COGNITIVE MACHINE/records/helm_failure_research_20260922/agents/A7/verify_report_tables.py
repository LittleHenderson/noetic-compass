"""Document/custody checks only; not additional behavioral evidence."""
import hashlib
import json
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
REC = OUT.parent.parent
WD = REC.parents[3]
PREFIX = 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922'
PACK = Path(r'C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/helm-failure-research') / PREFIX
PIN = '3f7ac2967c4bc38313a003e2817a3dcab58451d1'
DATA = json.loads((OUT/'ORIGINAL_RECORD_CHECKS.json').read_text(encoding='utf-8'))
REPORT = (OUT/'FINAL_JUDGMENT.md').read_text(encoding='utf-8')
checks = 0
for run in DATA['check_gate']:
    tag = 'H1' if run['version']=='Helm 1.0' else 'H2'
    kinds = ['analogy','context','correspondence','definition','edge_account','parts','reach','role_set']
    cells = [f"{run['families'][k]['initial']} → {run['families'][k]['final']}" for k in kinds]
    assert '| '+tag+' / '+str(run['seed'])+' | '+' | '.join(cells)+' |' in REPORT
    checks += 1
for run in DATA['check_development']['runs']:
    tag = 'H1' if run['version']=='Helm 1.0' else 'H2'
    kinds = ['ABSENT','DIRECT','VIA','PARTS']
    cells = [f"{run['endpoints']['p00']['correct'][k]} → {run['endpoints']['p10']['correct'][k]}" for k in kinds]
    cells += [f"{run['endpoints']['p00']['all_correct']} → {run['endpoints']['p10']['all_correct']}"]
    assert '| '+tag+' / '+str(run['seed'])+' | '+' | '.join(cells)+' |' in REPORT
    checks += 1
files = [f'agents/A{i}/{name}' for i in range(1,7) for name in ['FIRST_REPORT.md','CONFERENCE_RESPONSE.md']]
files += ['agents/A1/POST_SUBMISSION_CUSTODY_NOTE.md','agents/A5/FIRST_REPORT_ADDENDUM.md','agents/A6/EXECUTION_NOTE.md',
          'agents/A6/F1_REPORT.md','agents/A6/F1_RESULTS.json','agents/A3/F2_REPORT.md','agents/A3/F2_RESULTS.json',
          'agents/A2/probe_results.json','agents/A3/PROBE_RESULTS.json','FINDINGS_MATRIX.md','FOLLOWUP_PLAN.md','CHECK_ACCOUNTING.md',
          'coordinator/TEAM_EXECUTION_LEDGER.md','coordinator/CONFERENCE_RECORD.md']
fingerprints=[]
live_head=subprocess.run(['git','-C',str(PACK.parents[3]),'rev-parse','HEAD'],cwd=WD,capture_output=True,timeout=10,check=True).stdout.decode().strip()
for relative in files:
    live=(PACK/relative).read_bytes()
    proc=subprocess.run(['git','show',PIN+':'+PREFIX+'/'+relative],cwd=WD,capture_output=True,timeout=10,check=True)
    raw=proc.stdout
    # Role reports/raw records must remain exact; coordinator documents can
    # advance during final review. Bind the originally reviewed versions to Git.
    if relative.startswith('agents/'):
        assert live==raw, relative
    if live!=raw:
        saved=OUT/'tmp/at_review_pin'/relative
        saved.parent.mkdir(parents=True,exist_ok=True)
        saved.write_bytes(raw)
    fingerprints.append({'path':str(PACK/relative),'git_commit':PIN,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),
                         'live_sha256':hashlib.sha256(live).hexdigest(),'live_differs_from_reviewed_pin':live!=raw,'live_head_at_check':live_head})
receipt={'report_table_rows_checked':checks,'research_package_files_bound_to_commit':len(fingerprints),
         'research_package_fingerprints':fingerprints,'formal_test_functions':0,'executions':1,
         'scope':'Document numeric transcription and reviewed-package custody only; no original-record calculations repeated.'}
(OUT/'REVIEW_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='research_package_fingerprints'},indent=2))
