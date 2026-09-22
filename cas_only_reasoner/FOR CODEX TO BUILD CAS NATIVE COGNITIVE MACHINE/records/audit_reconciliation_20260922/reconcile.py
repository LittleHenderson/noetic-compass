"""Reconcile retained evidence; never execute the product or invent old receipts.

Run with --collect-selected once to retain a NEW collection-only listing for
the three deterministic Q4 files. Other results use immutable Git bytes.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
from functools import cache
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CN = 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/'
REF = 'eb9985566bd11a89f485d627186ef0efa7177f02'
PEER_REF = '65ad3008'
PCBA_REF = '4345aa36ab056f9539cad3feb9207bba5356bef4'
ATLAS_REF = '5b3d713c5e7f2b2fc2959aaf776d0d80ca09d256'
EXPECTED = '76d7821ac2cb6e007df42c7143ab1a81aa22ef46e6a29c71e5bb42d40665d1f5'
INDEX: dict[str, dict] = {}

@cache
def git(*args: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(ROOT), *args], stderr=subprocess.PIPE)

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

@cache
def blob(path: str, ref: str = REF) -> bytes:
    return git('show', ref + ':' + path)

def identity(path: str, ref: str = REF) -> dict:
    ref = git('rev-parse', ref).decode().strip()
    key = ref + ':' + path
    if key not in INDEX:
        data = blob(path, ref)
        INDEX[key] = {
            'repository_relative_path': path, 'source_commit': ref,
            'git_blob_sha1': git('rev-parse', ref + ':' + path).decode().strip(),
            'raw_bytes': len(data), 'sha256_raw': sha(data),
            'sha256_lf': sha(data.replace(b'\r\n', b'\n')),
        }
    return INDEX[key]

def cnid(rel: str, ref: str = REF) -> dict:
    return identity(CN + rel, ref)

def write(name: str, value: dict | list) -> None:
    (HERE / name).write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='utf-8', newline='\n')

def status(case: ET.Element) -> str:
    for name in ['failure', 'error', 'skipped']:
        if case.find(name) is not None:
            return name
    return 'passed'

def receipt(rel: str) -> dict:
    doc = ET.fromstring(blob(CN + rel))
    cases = []
    for item in doc.iter('testcase'):
        row = {'case_id': item.attrib.get('classname', '') + '::' + item.attrib['name'],
               'class_name': item.attrib.get('classname', ''), 'name': item.attrib['name'],
               'status': status(item)}
        row['function_id'] = row['case_id'].split('[', 1)[0]
        for bad in ['failure', 'error']:
            el = item.find(bad)
            if el is not None:
                row['message'] = el.attrib.get('message', '')
                row['diagnostic_sha256'] = sha((el.text or '').encode())
        cases.append(row)
    return {'identity': cnid(rel), 'suite_metadata': [s.attrib for s in doc.iter('testsuite')],
            'counts': dict(Counter(r['status'] for r in cases)),
            'test_cases': len(cases), 'test_functions': len({r['function_id'] for r in cases}),
            'cases': cases}

def case_map(receipts: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for rec in receipts:
        for row in rec['cases']:
            out.setdefault(row['case_id'], []).append({
                'receipt_path': rec['identity']['repository_relative_path'],
                'sha256_raw': rec['identity']['sha256_raw'],
                'timestamp': rec['suite_metadata'][0].get('timestamp'),
                'status': row['status']})
    return out

def atlas() -> dict:
    prefix = 'records/rpa_ohm_atlas_20260922/'
    initial = receipt(prefix + 'core_and_regression_tests.xml')
    finals = [receipt(prefix + n) for n in ['core_tests.xml','legacy_view_regression_tests.xml',
                                         'ohm_adapter_regression_tests.xml','view_tests.xml']]
    mapped = case_map(finals)
    rows = []
    for case in initial['cases']:
        observed = mapped.get(case['case_id'], [])
        later = [r for r in observed if r['timestamp'] > initial['suite_metadata'][0]['timestamp']]
        latest = max(later, key=lambda x:x['timestamp']) if later else None
        verdict = ('subsequently_passed' if latest['status'] == 'passed' else 'still_failing') if latest else 'not_rerun'
        rows.append({**case, 'reconciliation': verdict, 'later_receipts': later})
    failed = [r for r in rows if r['status'] in ('failure','error')]
    assert len(mapped) == 354 and len(rows) == 282
    assert Counter(r['reconciliation'] for r in failed) == {'subsequently_passed':38}
    frozen_sources = [cnid(p, ATLAS_REF) for p in [
        'cncm/rpa_coordinates.py','cncm/rpa_ohm_atlas.py',
        'tools/render_rpa_ohm_view.py','tools/render_rpa_view.py',
        'tests/test_rpa_coordinates.py','tests/test_rpa_ohm_atlas.py',
        'tests/test_rpa_model.py','tests/test_rpa_scoped_compound.py',
        'tests/test_rpa_view.py','tests/test_rpa_ohm_view.py',
        'research/helm_cas_expression_lab/test_cas_ohm_connections.py']]
    return {
        'schema':'cas.audit-atlas-case-reconciliation/0.1', 'mode':'HISTORICAL_RECEIPT_COMPARISON_NO_TEST_RUN',
        'initial':initial, 'finals':finals,
        'initial_failed_or_errored_case_reconciliation':dict(Counter(r['reconciliation'] for r in failed)),
        'all_initial_cases_reconciliation':dict(Counter(r['reconciliation'] for r in rows)),
        'final_distinct_case_count':len(mapped),
        'final_distinct_function_count':len({r['function_id'] for f in finals for r in f['cases']}),
        'final_case_overlap_count':sum(f['test_cases'] for f in finals)-len(mapped),
        'final_new_case_ids_relative_to_initial':sorted(set(mapped)-{c['case_id'] for c in initial['cases']}),
        'cases':rows,
        'verification_document':cnid(prefix+'VERIFICATION.md'),
        'atlas_final_snapshot_commit':ATLAS_REF,
        'atlas_final_snapshot_metadata':git('show','-s','--format=%H %aI %cI %s',ATLAS_REF).decode().strip(),
        'atlas_final_snapshot_sources':frozen_sources,
        'atlas_receipts_identical_at_atlas_and_audited_commits':all(
            blob(r['identity']['repository_relative_path'], ATLAS_REF)==blob(r['identity']['repository_relative_path'])
            for r in [initial]+finals),
        'environment':{'reported_interpreter':'Python 3.12', 'host_in_xml':'MSI',
            'receipt_python_version_field':'unavailable',
            'documented_setup_changes':['materialized tracked records/rpa_compound_001 fixtures',
                'reran owned local browser with tool-level WebSocket access'],
            'error_diagnostic_check':{'37_errors_all_mention_FileNotFoundError':all('FileNotFoundError' in r['message'] for r in failed if r['status']=='error'),
                'browser_failure_case_ids':[r['case_id'] for r in failed if r['status']=='failure']}},
        'source_boundary':'All receipts and final test sources are retained at eb998556. XML has no per-run source manifest or interpreter version. Exact case IDs and timestamp order resolve the retained failures; initial loaded-source bytes cannot be reconstructed from these XMLs alone.',
    }

Q4_FILES = ['test_learner_q4.py','test_q4_followup.py','test_q4_preparation.py']
def collect_selected() -> None:
    executable = r'C:\Python314\python.exe'
    args = [executable,'-B','-m','pytest','--collect-only','--noconftest','-o','addopts=',
            '-p','no:cacheprovider','-q',*Q4_FILES]
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE':'1','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','PYTHONIOENCODING':'utf-8'}
    cwd = ROOT / CN / 'research/helm_cas_expression_lab'
    for filename in Q4_FILES:
        expected=blob(CN+'research/helm_cas_expression_lab/'+filename)
        actual=(cwd/filename).read_bytes()
        if actual.replace(b'\r\n',b'\n')!=expected.replace(b'\r\n',b'\n'):
            raise RuntimeError('Refusing to label changed test source as the frozen selection: '+filename)
    started=datetime.now(timezone.utc).isoformat()
    proc = subprocess.run(args, cwd=cwd,env=env,capture_output=True)
    (HERE/'selected_q4_collection_NEW.txt').write_bytes(proc.stdout+proc.stderr)
    write('selected_q4_collection_NEW.json', {'kind':'NEW_COLLECTION_ONLY_NOT_EXECUTION',
        'command':args,'cwd':str(cwd),'returncode':proc.returncode,
        'started_utc':started,'completed_utc':datetime.now(timezone.utc).isoformat(),
        'environment':{k:env[k] for k in ['PYTHONDONTWRITEBYTECODE','PYTEST_DISABLE_PLUGIN_AUTOLOAD','PYTHONIOENCODING']},
        'source_ref':REF,'source_files':[cnid('research/helm_cas_expression_lab/'+p) for p in Q4_FILES],
        'raw_output_sha256':sha(proc.stdout+proc.stderr),
        'note':'This lists current frozen-source cases; it is not the historical 107-case test receipt and asserts no pass.'})
    if proc.returncode: raise RuntimeError('Selected collection failed')

def selected_counts() -> dict:
    recs = [receipt('records/rpa_recorded_helm_20260922/'+s) for s in
            ['recorded_and_shared_view_tests.xml','legacy_regression_tests.xml']]
    rpa = case_map(recs)
    collected = (HERE/'selected_q4_collection_NEW.txt').read_text(encoding='utf-8')
    q4ids = [line.strip().replace('.py::','::').replace('/','.') for line in collected.splitlines() if '.py::test_' in line]
    assert len(q4ids)==len(set(q4ids))==107
    allids = set(rpa)|set(q4ids)
    assert len(rpa)==422 and len(allids)==529
    functions={c.split('[',1)[0] for c in allids}
    assert len(functions)==193
    added=git('diff','--name-only','--diff-filter=A',REF+'^',REF).decode().splitlines()
    newclasses={p[len(CN):].removesuffix('.py').replace('/','.') for p in added if p.startswith(CN) and '/test_' in p}
    newids={c for c in allids if c.split('::')[0] in newclasses}
    assert len(newids)==83
    rows=[]
    for cls,n in sorted(Counter(c.split('::')[0] for c in allids).items()):
        rel=cls.replace('.','/')+'.py'
        rows.append({'source':cnid(rel),'cases':n,
            'functions':len({c.split('[',1)[0] for c in allids if c.split('::')[0]==cls}),
            'added_at_subject_commit':cls in newclasses,
            'case_ids':sorted(c for c in allids if c.split('::')[0]==cls)})
    return {'schema':'cas.audit-selected-scope/0.1','subject_ref':REF,
        'case_count':529,'function_count':193,'new_cases':83,'existing_cases':446,
        'new_functions':len({c.split('[',1)[0] for c in newids}),
        'existing_functions':len(functions-{c.split('[',1)[0] for c in newids}),
        'parameter_expansion_rows_beyond_one_per_function':529-193,
        'count_meaning':'Parameterized cases are distinct input checks. Neither function count nor case count is a requirement count or source-code coverage.',
        'rpa_retained_xml_case_count':422,'q4_retained_text_summary_count':107,
        'q4_retained_text_receipt':cnid('records/rpa_recorded_helm_20260922/q4_preparation/deterministic_tests_short_path.txt'),
        'q4_case_id_limit':'Historical text has 107 passed but no individual IDs. A NEW bounded collect-only listing of the exact frozen source supplies the 107 IDs and 51 functions; it is not substituted for historical execution evidence.',
        'historical_q4_earlier_105_case_receipt':cnid('records/rpa_recorded_helm_20260922/q4_preparation/deterministic_tests_final.txt'),
        'selected_files':rows,'rpa_receipts':recs,
        'unloaded_test_files':{'count_reported_by_peer':20,'reported_missing_jsonschema':5,
             'reported_sparse_module_missing':15,'exact_historical_file_list':'UNAVAILABLE',
             'historical_collection_raw_receipt':'UNAVAILABLE',
             'peer_report':cnid('records/audit_package_20260922/06_AUDIT_OF_THE_CODEX_AGENT.md',PEER_REF),
             'collectible_cases_reported_by_peer':2691,
             'case_selection_ratio_reported':529/2691,
             'ratio_is_source_coverage':False,
             'verification_boundary':'Aggregates are attributed to the peer audit; no broad suite collection or execution was performed in this reconciliation.'},
        'requirements':{'source':cnid('records/rpa_recorded_helm_20260922/VERIFICATION.md'),
             'declared_acceptance_items':18,'declared_engineering_items':17,'learner_execution_item_A18':'NOT_RUN',
             'independent_requirement_coverage_count':'NOT_ESTABLISHED_BY_TEST_COUNTS'},
    }

def lab_history() -> dict:
    prefix='research/helm_cas_expression_lab/'
    later312=receipt(prefix+'cas_ohm_evidence/lab312_tests.xml')
    later314=receipt(prefix+'cas_ohm_evidence/lab314_tests.xml')
    historical314=receipt(prefix+'pcba_evidence/legacy_dependency_recheck.xml')
    pcba=[r for r in later312['cases'] if '.test_pcba_' in r['case_id']]
    assert len(pcba)==289
    legacy312=[r for r in later312['cases'] if not any(s in r['case_id'] for s in ['.test_cas_ohm_connections::','.test_historical_compiler::'])]
    laterunion={r['case_id'] for r in legacy312+later314['cases']}
    assert len(laterunion)==637
    source_files=[]
    for cls in sorted({r['class_name'] for r in legacy312+later314['cases']}):
        path=CN+cls.replace('.','/')+'.py'
        old=identity(path,PCBA_REF); new=identity(path)
        source_files.append({'pcba_commit_source':old,'later_receipt_retained_source':new,
            'identical_test_source':old['sha256_raw']==new['sha256_raw']})
    return {'schema':'cas.audit-lab-history/0.1',
        'old_637_claim':{'verification':cnid(prefix+'pcba_evidence/VERIFICATION.md',PCBA_REF),
            'reported_python312':{'passed':622,'failures':6,'errors':9},
            'reported_python314':{'passed':66,'overlap_passed':51},
            'arithmetic':622+66-51,
            'original_python312_receipt':'UNAVAILABLE_AFTER_BOUNDED_SEARCH',
            'original_python312_failed_and_error_exact_case_ids':'UNAVAILABLE',
            'historical_python314_receipt':historical314,
            'verdict':'The documented cross-environment arithmetic is consistent. The retained 66-case retry is all green. The original 622-pass/15-nonpass individual-case record was not recovered, so the old full union cannot be verified case by case.'},
        'later_recorded_reconciliation':{
            'boundary':'These retained CAS-Ohm runs occurred later. They establish later success, not the missing original PCBA run.',
            'python312_receipt':later312,'python314_receipt':later314,
            'all_later_union':len({r['case_id'] for r in later312['cases']+later314['cases']}),
            'legacy_selected_from_later_python312':len(legacy312),
            'legacy_selected_from_later_python314':len(later314['cases']),
            'legacy_union':len(laterunion),'legacy_case_ids':sorted(laterunion),
            'test_source_comparison':source_files},
        'pcba_289':{'receipt':later312['identity'],'case_ids':[r['case_id'] for r in pcba],
            'cases':289,'functions':len({r['function_id'] for r in pcba}),
            'adapter_cases':sum('.test_pcba_component_adapter::' in r['case_id'] for r in pcba),
            'per_file_counts':dict(Counter(r['class_name'] for r in pcba)),
            'all_passed_in_this_later_receipt':all(r['status']=='passed' for r in pcba),
            'original_standalone_289_receipt':'UNAVAILABLE',
            'claim_scope':'289 passing PCBA cases are explicitly indexed in the retained later 638-case XML; this does not recover the historical standalone invocation.'}}

def acceptance_records() -> dict:
    specs=[('native','records/rpa_001/demo2/receipt.json'),
           ('compound','records/rpa_compound_001/acceptance_002/receipt.json'),
           ('scoped','records/rpa_scoped_001/acceptance_001/receipt.json'),
           ('cube','records/rpa_cube_001/acceptance_001/receipt.json')]
    result=[]
    for family,rel in specs:
        ident=cnid(rel)
        data=json.loads(blob(CN+rel))
        introducing=git('log','--format=%H','--diff-filter=A',REF,'--',CN+rel).decode().splitlines()[-1]
        files=data.get('files',data.get('artifacts',[]))
        checked=[]
        for item in files:
            path=CN+str(Path(rel).parent.as_posix())+'/'+item['path']
            actual=identity(path)
            checked.append({'path':path,'expected_sha256':item['sha256'],
                'actual_sha256':actual['sha256_raw'],'matches':actual['sha256_raw']==item['sha256'],
                'expected_bytes':item.get('bytes'),'actual_bytes':actual['raw_bytes']})
        source_checks=[]
        source_rows=[(item,'receipt_sources') for item in data.get('sources',[])]
        if family=='cube':
            for source_rel,key in [('actual_imports.json','modules'),('declared_inputs_before.json',None)]:
                source_path=str(Path(rel).parent.as_posix())+'/'+source_rel
                cnid(source_path)
                source_data=json.loads(blob(CN+source_path))
                source_rows.extend((item,source_rel) for item in (source_data[key] if key else source_data))
        for item,source_kind in source_rows:
            path=CN+item['path']
            try:
                old=identity(path,introducing)
                source_checks.append({'path':path,'source_kind':source_kind,'expected_sha256':item['sha256'],
                    'retained_at_receipt_introducing_commit':old,
                    'matches':old['sha256_raw']==item['sha256']})
            except subprocess.CalledProcessError:
                source_checks.append({'path':path,'matches':False,'status':'UNAVAILABLE_AT_INTRODUCING_COMMIT'})
        result.append({'family':family,'receipt':ident,'first_commit_containing_receipt':introducing,
            'status_as_recorded':data.get('status'),
            'scope_as_recorded':data.get('scope',data.get('boundary')),
            'artifact_checks':checked,'artifact_matches':sum(r['matches'] for r in checked),
            'artifact_count':len(checked),'historical_source_checks':source_checks,
            'source_matches':sum(r['matches'] for r in source_checks),'source_count':len(source_checks),
            'verification_boundary':'Existing bytes and bound artifact fingerprints checked; no semantic/runtime/browser acceptance was re-executed.'})
    return {'schema':'cas.audit-acceptance-record-index/0.1','records':result,
        'conclusion':'The four source-family records are available in tracked Git at eb998556. The historical verification document omitted their paths and hashes; this index supplies them without creating replacement acceptance runs.',
        'cube_limits':'Cube receipt describes pure authored-source projection and teacher/learner export preparation; it is not a learned result.'}

def attachments() -> dict:
    names=[Path(r'C:\Users\wakil\Downloads\CODEX_RPA_RECORDED_RUN_CONTINUATION_20260922.md'),
           Path(r'C:\Users\wakil\Downloads\CODEX_RPA_RECORDED_RUN_CONTINUATION_20260922 (1).md')]
    found=[]
    destination=HERE/'inputs'/'RECOVERED_ORIGINAL_CONTINUATION.md'
    destination.parent.mkdir(exist_ok=True)
    for path in names:
        if path.exists():
            raw=path.read_bytes()
            found.append({'path':str(path),'bytes':len(raw),'sha256_raw':sha(raw),'sha256_lf':sha(raw.replace(b'\r\n',b'\n')),'matches_expected':sha(raw)==EXPECTED})
            if sha(raw)==EXPECTED:
                if destination.exists(): assert destination.read_bytes()==raw
                else: destination.write_bytes(raw)
    assert destination.exists() and sha(destination.read_bytes())==EXPECTED
    alt=[]
    # Bounded search: small Markdown/text inputs in Downloads (top level) and
    # the attachment mount. No dependency/vendor directory traversal.
    candidates=list(Path(r'C:\Users\wakil\Downloads').glob('*.md'))
    for ext in ('*.md','*.txt'):
        candidates.extend(Path(r'C:\Users\wakil\.codex\attachments').rglob(ext))
    inspected=0
    for path in candidates:
        try:
            if path.stat().st_size>1_000_000: continue
            raw=path.read_bytes(); inspected+=1
        except OSError: continue
        if sha(raw).startswith('cd86eaf8'):
            alt.append({'path':str(path),'bytes':len(raw),'sha256_raw':sha(raw)})
            (HERE/'inputs'/('LATER_COPY_'+sha(raw)[:12]+'.md')).write_bytes(raw)
    return {'schema':'cas.audit-attachment-recovery/0.1','found_original_copies':found,
        'retained_copy':'inputs/RECOVERED_ORIGINAL_CONTINUATION.md','expected_sha256':EXPECTED,
        'copy_status':'RECOVERED_EXISTING_BYTES_NOT_REGENERATED',
        'bounded_candidates_hashed':inspected,'later_copy_prefix_reported_by_peer':'cd86eaf8',
        'later_copy_matches':alt,
        'comparison_status':'LATER_COPY_UNAVAILABLE_FOR_CONTENT_COMPARISON' if not alt else 'BOTH_VERSIONS_RETAINED',
        'custody_boundary':'Recovery from current Downloads verifies the attachment bytes. It does not prove these bytes were present in either historical audited worktree.',
        'user_recovery_notice':{'path':r'C:\Users\wakil\.codex\attachments\595bede0-57a9-401a-835d-46f28b2fbc54\Pasted text.txt',
            'sha256_raw':sha(Path(r'C:\Users\wakil\.codex\attachments\595bede0-57a9-401a-835d-46f28b2fbc54\Pasted text.txt').read_bytes())}}

def main() -> None:
    args=argparse.ArgumentParser()
    args.add_argument('--collect-selected',action='store_true')
    args.add_argument('--check-current-remote',action='store_true')
    args.add_argument('--selection-only',action='store_true',help='With --collect-selected, write only the NEW collection listing, never an execution receipt')
    options=args.parse_args()
    if options.collect_selected: collect_selected()
    if options.selection_only:
        if not options.collect_selected: raise ValueError('--selection-only requires --collect-selected')
        return
    if options.check_current_remote:
        refname='refs/heads/codex/helm-rpa-recorded-run-20260922'
        response=git('ls-remote','origin',refname).decode().strip()
        descendant=response.split()[0]
        ancestry=subprocess.run(['git','-C',str(ROOT),'merge-base','--is-ancestor',ATLAS_REF,descendant],capture_output=True)
        write('publication_observation_NEW.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),
            'kind':'CURRENT_REMOTE_READ_NOT_HISTORICAL_PUBLICATION_PROOF','remote':'origin',
            'command':['git','ls-remote','origin',refname], 'response':response,
            'ancestor':ATLAS_REF,'descendant':descendant,'is_ancestor_exit_code':ancestry.returncode,
            'conclusion':'The atlas commit is reachable through this presently published branch. Remote state today does not establish historical publication timing.'})
    a=atlas(); s=selected_counts(); l=lab_history(); ac=acceptance_records(); at=attachments()
    for name,obj in [('atlas_case_reconciliation.json',a),('selected_case_inventory.json',s),
                     ('lab_history_reconciliation.json',l),('acceptance_record_index.json',ac),('attachment_recovery.json',at)]:
        write(name,obj)
    peer=CN+'records/audit_package_20260922/06_AUDIT_OF_THE_CODEX_AGENT.md'
    (HERE/'inputs'/'PEER_AUDIT_65ad3008.md').write_bytes(blob(peer,PEER_REF))
    identity(peer,PEER_REF)
    identity('CHANGELOG.md')
    write('receipt_and_source_index.json',{'schema':'cas.audit-receipt-source-index/0.1',
        'hash_semantics':'SHA-256 over exact Git blob bytes; LF hash is separate. Paths are repository-relative and source commits are exact.',
        'items':sorted(INDEX.values(),key=lambda r:(r['source_commit'],r['repository_relative_path']))})
    print(json.dumps({'atlas_failed_cases_resolved':a['initial_failed_or_errored_case_reconciliation'],
        'atlas_cases':a['final_distinct_case_count'],'selected_cases':s['case_count'],
        'functions':s['function_count'],'new_cases':s['new_cases'],'existing_cases':s['existing_cases'],
        'later_legacy_union':l['later_recorded_reconciliation']['legacy_union'],
        'pcba_later_receipt_cases':l['pcba_289']['cases'],
        'acceptances':[{k:r[k] for k in ['family','artifact_matches','artifact_count','source_matches','source_count']} for r in ac['records']],
        'attachment_copies':len(at['found_original_copies']),'later_copy':at['comparison_status']}))

if __name__=='__main__': main()
