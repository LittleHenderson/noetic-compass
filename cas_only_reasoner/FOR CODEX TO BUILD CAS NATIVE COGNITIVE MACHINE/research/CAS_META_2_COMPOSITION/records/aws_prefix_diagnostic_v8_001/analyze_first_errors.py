"""Reproduce first-error counts using only saved JSON, ZIP, and pure grammar code.

Run from CAS_META_2_COMPOSITION:
  python -B records/aws_prefix_diagnostic_v8_001/analyze_first_errors.py --output records/aws_prefix_diagnostic_v8_001/first_errors_001

This does not load checkpoints, call AWS, or execute native CJTs.
"""
from __future__ import annotations

import argparse
import builtins
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shlex
import stat
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = {'torch','casformer','cas_cjt','tensorflow','jax','numpy','boto3','botocore','socket'}
BOUNDARY = (
    "Lexical reference differences and selected-role reference-choice mismatches are not "
    "native execution failure proof, autonomous task correctness, semantic equivalence, "
    "or a new learning result. Procedure names remain exact; only the frozen matcher "
    "handles proven producer-address variable renaming."
)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def main():
    if sys.flags.optimize:
        raise ValueError("ASSERTION_ENABLED_PYTHON_REQUIRED")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    requested = args.output.absolute()
    if requested.exists() or requested.is_symlink() or requested.is_junction():
        raise ValueError("OUTPUT_MUST_BE_NEW")
    for ancestor in requested.parents:
        if ancestor.is_symlink() or ancestor.is_junction():
            raise ValueError("LINKED_OUTPUT_PATH_REJECTED")
    output = requested.resolve()
    if output.parent != Path(__file__).resolve().parent:
        raise ValueError("OUTPUT_MUST_BE_DIRECT_CHILD_OF_THIS_RECORD_DIRECTORY")
    script_sha = sha256(Path(__file__).read_bytes()).hexdigest()
    started = datetime.now(timezone.utc).isoformat()
    root=ROOT
    base=root/'records/aws_prefix_diagnostic_v8_001/execution_001'
    bundle=root/'records/child_call_v8_diagnostic_001/bundle_001'
    def digest(raw): return sha256(raw).hexdigest()
    def decode(raw):
     def pairs(items):
      out={}
      for k,v in items:
       assert k not in out, ('duplicate key',k)
       out[k]=v
      return out
     return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    launch_raw=(base/'launch_receipt.json').read_bytes()
    launch=decode(launch_raw)
    archive=base/'cloud_artifacts.zip'
    archive_sha=digest(archive.read_bytes())
    assert archive_sha==launch['result']['sha256'] and archive.stat().st_size==launch['result']['bytes']
    source_archive=root/'records/child_call_v8_diagnostic_001/source_001/source.zip'
    assert digest(source_archive.read_bytes())=='c1e784440b408a81d28efd00444fe69680972b9ef6ce14b5c298598dc6e83be1'
    pure_sources={}
    with ZipFile(source_archive) as z:
     source=decode(z.read('prefix_source_manifest.json'))
     for rel in ('cas_meta2/__init__.py','cas_meta2/codec.py','cas_meta2/grammar_v3.py','cas_meta2/ir.py','cas_meta2/diagnostic_v8/__init__.py','cas_meta2/diagnostic_v8/sites.py'):
      actual=digest((root/rel).read_bytes())
      assert actual==source['files_sha256']['research/CAS_META_2_COMPOSITION/'+rel],rel
      assert digest(z.read('research/CAS_META_2_COMPOSITION/'+rel))==actual,rel
      pure_sources[rel]=actual
    original_import=builtins.__import__
    def guarded_import(name,*args,**kwargs):
     assert name.split('.')[0] not in {'torch','casformer','cas_cjt','tensorflow','jax','numpy','boto3','botocore','socket'},name
     return original_import(name,*args,**kwargs)
    builtins.__import__=guarded_import
    sys.path.insert(0,str(root))
    from cas_meta2 import codec, grammar_v3
    from cas_meta2.ir import validate_program
    from cas_meta2.diagnostic_v8.sites import compare_sites
    manifest_raw=(bundle/'manifest.json').read_bytes()
    assert digest(manifest_raw)=='b4d7970ca59c07342942584e4752ad8c129c3125e25ecc241e3d76c9ddd1c629'
    manifest=decode(manifest_raw)
    cohorts={}
    for cohort in ('train_probe','validation'):
     raw=(bundle/(cohort+'.json')).read_bytes()
     assert digest(raw)==manifest['files'][cohort+'.json']['sha256']
     cohorts[cohort]=decode(raw)
     assert [t['task_id'] for t in cohorts[cohort]]==manifest['cohorts'][cohort]['ordered_task_ids']
    groups=defaultdict(lambda: {'rows':0,'lexically_equal':0,'first_lexical_role':Counter(),'first_wrong_comparable_role':Counter(),'no_wrong_comparable_status':Counter(),'first_wrong_prefix_stratum':Counter(),'first_wrong_at_lexical_divergence':0,'matched_scored_sites':0,'correct_comparable_sites':0,'reference_sites':0,'termination':Counter()})
    examples=[]
    trajectories=[]
    verified_rows=0
    with ZipFile(archive) as z:
     infos=z.infolist(); names=[i.filename for i in infos]
     assert len(names)==len(set(names))==len({n.casefold() for n in names})==511
     assert all(not n.startswith(('/', '\\')) and '\\' not in n and ':' not in n and '..' not in n.split('/') for n in names)
     assert all(not i.is_dir() and not stat.S_ISLNK(i.external_attr>>16) and not i.flag_bits&1 for i in infos)
     assert sum(i.file_size for i in infos)<=512*1024**2
     collection=decode(z.read('artifact_collection_receipt.json'))
     assert collection['job']==launch['job'] and collection['returncode']==0 and collection['partial_evidence'] is False and collection['omitted_full_file_count']==0
     assert set(names)==set(collection['files'])|{'artifact_collection_receipt.json'}
     for name,item in collection['files'].items():
      raw=z.read(name); assert digest(raw)==item['sha256'] and len(raw)==item['bytes'],name
     diagnostic=decode(z.read('diagnostic/diagnostic_receipt.json'))
     assert diagnostic['completed'] is True and diagnostic['job']==launch['job'] and diagnostic['task_rows_completed']==480
     assert diagnostic['bundle_manifest_sha256']==digest(manifest_raw)
     assert len(diagnostic['files_sha256'])==480
     unique=set()
     for filename,expected in sorted(diagnostic['files_sha256'].items()):
      assert '/' not in filename and '\\' not in filename and filename.endswith('.json')
      raw=z.read('diagnostic/'+filename); assert digest(raw)==expected,filename
      row=decode(raw)
      key=(row['checkpoint'],row['cohort'],row['cohort_index'])
      assert key not in unique; unique.add(key)
      assert row['checkpoint_sha256']==manifest['checkpoint_records'][row['checkpoint']]['sha256']
      task=cohorts[row['cohort']][row['cohort_index']]
      assert row['task_id']==task['task_id'] and row['public_sha256']==codec.canonical_sha256(task['public'])
      depth=validate_program(task['target']['program'])['max_call_depth']; assert row['depth']==depth
      ref=codec.action_to_ids(task['target'],max_length=256); gen=row['emitted_token_ids']
      assert gen==(row['action']['token_ids'] if row['action'].get('status')=='REJECTED' else codec.action_to_ids(row['action'],max_length=256))
      comparison=compare_sites(ref,gen,max_length=256)
      assert [{k:v for k,v in s.items() if k not in ('correct_prefix','self_generated_prefix')} for s in row['decision_rows']]==comparison['rows'],filename
      assert row['site_counts']==comparison['totals'] and row['extra_generated_sites']==comparison['extra_generated_sites']
      assert row['generation_termination']==comparison['generated']['termination']
      verified_rows+=1
      equal=ref==gen
      j=next((i for i,(a,b) in enumerate(zip(ref,gen)) if a!=b), min(len(ref),len(gen)))
      first_lex=None
      if not equal:
       ref_token=codec.ACTION_VOCABULARY[ref[j]] if j<len(ref) else '<NO_REFERENCE_TOKEN>'
       gen_token=codec.ACTION_VOCABULARY[gen[j]] if j<len(gen) else '<NO_GENERATED_TOKEN>'
       chosen=next((s for s in comparison['reference']['sites'] if s['token_index']==j),None)
       lexrole=chosen['role'] if chosen is not None else grammar_v3.GrammarState.from_ids(ref[:j],max_length=256).role
       first_lex={'token_index':j,'reference_token':ref_token,'generated_token':gen_token,'reference_role':lexrole,
                  'reference_token_id':ref[j] if j<len(ref) else None, 'generated_token_id':gen[j] if j<len(gen) else None,
                  'preceding_prefix_equal':ref[:j]==gen[:j], 'reference_prefix_ids':ref[:j], 'generated_prefix_ids':gen[:j],
                  'kind':'SUBSTITUTION' if j<len(ref) and j<len(gen) else 'GENERATED_STOP' if j==len(gen) else 'GENERATED_EXTRA'}
      comparable=[s for s in comparison['rows'] if s['correspondence']=='MATCHED' and s['expected_choice']=='LEGAL' and s['generated_site']['observed']]
      assert all(s['correct'] is not None for s in comparable)
      wrong=sorted((s for s in comparable if s['correct'] is False),key=lambda s:s['generated_site']['token_index'])
      first_wrong=None
      if wrong:
       s=wrong[0]; gs=s['generated_site']
       first_wrong={'role':s['reference_site']['role'],'generated_token_index':gs['token_index'],'reference_token_index':s['reference_site']['token_index'],
                    'address':gs['address'],'expected_token':codec.ACTION_VOCABULARY[s['expected_token_id']],'generated_token':gs['chosen_token'],
                    'preceding_tokens_differ':s['preceding_tokens_differ'],'single_option':gs['single_option'],
                    'expected_token_id':s['expected_token_id'],'generated_token_id':gs['chosen_token_id'],
                    'reference_prefix_ids':s['reference_site']['prefix_ids'],'generated_prefix_ids':gs['prefix_ids'],
                    'correspondence':s['correspondence'],'expected_choice':s['expected_choice']}
      group=groups[(row['checkpoint'],row['cohort'],depth)]
      group['rows']+=1; group['lexically_equal']+=equal
      if first_lex: group['first_lexical_role'][first_lex['reference_role']]+=1
      group['reference_sites']+=len(comparison['rows']); group['matched_scored_sites']+=len(comparable); group['correct_comparable_sites']+=sum(s['correct'] is True for s in comparable)
      group['termination'][row['generation_termination']]+=1
      if first_wrong:
       group['first_wrong_comparable_role'][first_wrong['role']]+=1
       group['first_wrong_prefix_stratum']['after_lexical_divergence' if first_wrong['preceding_tokens_differ'] else 'identical_prefix']+=1
       group['first_wrong_at_lexical_divergence']+=first_lex is not None and first_wrong['generated_token_index']==first_lex['token_index']
      else:
       group['no_wrong_comparable_status']['all_reference_sites_scored_correct' if len(comparable)==len(comparison['rows']) else 'zero_comparable_sites' if not comparable else 'some_sites_not_comparable_or_not_emitted']+=1
      trajectories.append({'source_row_filename':filename,'source_row_sha256':expected,
        'checkpoint':row['checkpoint'],'checkpoint_sha256':row['checkpoint_sha256'],
        'cohort':row['cohort'],'cohort_index':row['cohort_index'],'task_id':row['task_id'],
        'public_sha256':row['public_sha256'],'depth':depth,
        'reference_token_ids':ref,'generated_token_ids':gen,'lexically_equal':equal,
        'first_lexical_divergence':first_lex,'first_wrong_comparable_selected_role':first_wrong,
        'scored_comparable_sites':len(comparable),'correct_comparable_sites':sum(s['correct'] is True for s in comparable),
        'wrong_comparable_sites':len(wrong),'reference_sites':len(comparison['rows']),
        'reference_sites_not_comparable_or_not_emitted':len(comparison['rows'])-len(comparable),
        'correspondence_counts':dict(Counter(s['correspondence'] for s in comparison['rows'])),
        'generation_termination':row['generation_termination'],'native_execution_performed':False})
      if row['checkpoint'].endswith('selected') and row['cohort']=='validation' and first_lex:
       example_key=(row['checkpoint'],depth,first_lex['reference_role'],None if first_wrong is None else first_wrong['role'])
       if not any(e['example_key']==list(example_key) for e in examples):
        examples.append({'example_key':list(example_key),'filename':filename,'task_id':row['task_id'],'cohort_index':row['cohort_index'],
                         'first_lexical_divergence':first_lex,'first_wrong_comparable_selected_role':first_wrong,
                         'scored_comparable_sites':len(comparable),'reference_sites':len(comparison['rows']),
                         'termination':row['generation_termination']})
     assert len(unique)==480
    assert digest(archive.read_bytes())==archive_sha
    assert verified_rows==480 and sum(v['reference_sites'] for v in groups.values())==9088
    expected_keys={(checkpoint,cohort,i) for checkpoint in manifest['checkpoint_records'] for cohort,tasks in cohorts.items() for i in range(len(tasks))}
    assert unique==expected_keys
    assert all(digest((root/rel).read_bytes())==expected for rel,expected in pure_sources.items())
    assert digest(source_archive.read_bytes())=='c1e784440b408a81d28efd00444fe69680972b9ef6ce14b5c298598dc6e83be1'
    assert digest((bundle/'manifest.json').read_bytes())==digest(manifest_raw)
    assert digest(Path(__file__).read_bytes())==script_sha
    assert not any(n.split('.')[0] in FORBIDDEN for n in sys.modules)
    grouped={'schema':'cas-meta2-prefix-first-errors/1','boundary':BOUNDARY,
     'definitions':{
      'first_lexical_divergence':'First actual full-stream token mismatch or stream ending; BOS has index 0. Includes structural tokens and exact procedure names. No EOS is inserted or removed.',
      'first_wrong_comparable_selected_role':'Earliest generated token index with MATCHED correspondence, LEGAL mapped expected choice, observed generated choice, and correct=false under the frozen matcher.',
      'no_wrong_comparable':'Not success: missing, changed-context, ambiguous, or unemitted sites remain unscored in the reference denominator.',
      'renaming':'Procedure names remain exact. The frozen matcher alone accepts output variable renaming through unique producer addresses; lexical mismatch itself need not be semantically wrong.'},
     'distinct_task_instances':120,'checkpoint_task_rows':480,
     'groups':[{'checkpoint':k[0],'cohort':k[1],'depth':k[2],**v} for k,v in sorted(groups.items())],
     'selected_validation_examples':examples}
    trajectory_report={'schema':'cas-meta2-prefix-first-error-trajectories/1','boundary':BOUNDARY,'rows':trajectories}
    output.mkdir()
    files={}
    for name,value in [('grouped_counts.json',grouped),('trajectories.json',trajectory_report)]:
     raw=canonical(value); (output/name).write_bytes(raw)
     files[name]={'sha256':digest(raw),'bytes':len(raw)}
    (output/'launch_receipt_observed.json').write_bytes(launch_raw)
    files['launch_receipt_observed.json']={'sha256':digest(launch_raw),'bytes':len(launch_raw)}
    receipt={'schema':'cas-meta2-prefix-first-errors-receipt/1','status':'PURE_JSON_REPLAY_COMPLETE',
     'started_utc':started,'finished_utc':datetime.now(timezone.utc).isoformat(),
     'command':shlex.join([sys.executable,'-B',str(Path(__file__).resolve()),'--output',str(output)]),
     'working_directory':str(Path.cwd()),'python':sys.version,
     'script':str(Path(__file__).resolve()),'script_sha256_before':script_sha,
     'script_sha256_after':digest(Path(__file__).read_bytes()),
     'job':launch['job'],'cloud_archive_sha256':archive_sha,'cloud_archive_bytes':archive.stat().st_size,
     'launch_receipt_observed_sha256':digest(launch_raw),
     'source_archive_sha256':digest(source_archive.read_bytes()),'source_sha':source.get('source_sha'),
     'pure_source_sha256_before':pure_sources,
     'pure_source_sha256_after':{rel:digest((root/rel).read_bytes()) for rel in pure_sources},
     'bundle_manifest_sha256':digest(manifest_raw),
     'cohort_sha256':{c:digest((bundle/(c+'.json')).read_bytes()) for c in cohorts},
     'verified_collection_files':len(collection['files']),'verified_and_replayed_row_hashes':verified_rows,
     'reference_selected_site_opportunities':sum(v['reference_sites'] for v in groups.values()),
     'neural_tensor_native_provider_execution':False,'forbidden_imports_absent':True,
     'boundary':BOUNDARY,'files':files}
    (output/'receipt.json').write_bytes(canonical(receipt))
    print(json.dumps({'status':receipt['status'],'output':str(output),'rows':verified_rows,'reference_sites':9088,'files':files},sort_keys=True))
    

if __name__ == '__main__':
    main()
