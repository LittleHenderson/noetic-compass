"""Keep the one missing local source snapshot visible and reconcile saved IDs."""
from a import *
from cas_meta2.graph_teaching import face_evaluation
h=read(OUT/'history.json'); archive_by_path={r['path']:r for r in h['archives']}
associations=[]
for r in h['run_metadata']:
    if not any(v in r['schema'] for v in ('result/','failure/')) or 'ordered-encoder' in r['schema']:continue
    p=Path(r['path']); found=None
    for parent in (p.parent,*p.parents):
        if parent.as_posix() in ('records','.'):break
        name=(parent/'source.zip').as_posix()
        if name in archive_by_path:found=archive_by_path[name];break
    associations.append({k:r[k] for k in ('path','sha256','schema','job','status')}|
      {'co_located_archive':None if found is None else {k:found[k] for k in ('path','sha256')},
       'association_scope':'Retained co-location, not independent proof of execution or external authenticity.'})
missing=[r for r in associations if r['co_located_archive'] is None]
assert len(missing)==1 and missing[0]['job']=='rdcjt-local-smoke'
local=ROOT/'records/recurrent_cjt_001/local_smoke_rtx4070_001'
exp=read(local/'artifacts/experiment.json')
saved_ids=set();saved_families=set()
def collect(v):
    if isinstance(v,dict):
        if 'record_id' in v:saved_ids.add(v['record_id'])
        if 'family_id' in v:saved_families.add(v['family_id'])
        for value in v.values():
            if isinstance(value,(dict,list)):collect(value)
    elif isinstance(v,list):
        for value in v:
            if isinstance(value,(dict,list)):collect(value)
collect(exp)
expected_ids=set(); expected_families=set()
for item in face_evaluation.panel():
    entry=(face_evaluation.diagnostic_item(item) if item['kind'] in face_evaluation.DIAGNOSTIC_KINDS else face_evaluation.compile_panel_item(item))
    expected_ids.add(entry['episode']['public_record']['record_id'])
    expected_families.add(entry['episode']['public_record']['family_id'])
assert saved_ids==expected_ids and saved_families==expected_families
write('custody.json',{'schema':'cas.learning-panel-source-custody-audit/0.1',
  'association_rows':associations,'unmatched_source_snapshot_rows':missing,
  'local_smoke':{'pins':[pin(local/n) for n in ('result.json','LOCAL_SMOKE.json','artifacts/experiment.json','artifacts/depth_sweep.json')],
    'saved_evaluation_record_ids':len(saved_ids),'saved_root_family_ids':len(saved_families),
    'evaluation_ids_exactly_match_reconstructed_old_face_panel':True,
    'training_decisions_per_arm':exp['plan']['teaching_decisions_per_arm'],'updates_per_arm':exp['plan']['optimizer_updates_per_arm'],
    'training_input_bytes_reconciled':False,'exact_historical_source_snapshot_available':False,
    'gap':'Local run retains per-batch work/loss and old-panel evaluation IDs, not exact per-training-input bytes or a source archive. Do not silently convert recorded schedule intent into verified training input history.'},
  'retained_history_conclusion':'Prepared canonical36 remain candidate supply with no observed prior learner hit. Absolute demonstrated-unexposed status is not established across the local training-custody gap or unretained history.',
  'input_pins':[pin(OUT/n) for n in ('a.py','d.py','history.json')],'source_pins':modules(),
  'actual_neural_presentations':0,'actual_optimizer_updates':0,'actual_provider_calls':0})
