"""Independent data-only audit of the exact second typed-course delivery."""
from pathlib import Path, PurePosixPath
from hashlib import sha256
from zipfile import ZipFile
from io import BytesIO
from collections import Counter
from datetime import datetime, timezone
import json, math
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
BASE=ROOT/'records/typed_numeric_001/receipt_002'; COL=BASE/'collected'; ART=COL/'results/artifacts'
JOB='cas-meta2-typedcourse-20260917024221-2a221243'; SOURCE='2a221243bf2f82f82bdce19514fe04bcb6b26bb0'
checks=[]
def require(test,label):
 if not test: raise AssertionError(label)
 checks.append(label)
def read(p): return json.loads(p.read_bytes())
def h(raw): return sha256(raw).hexdigest()
def c0(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
def c1(x): return c0(x)+b'\n'
def digest(x): return h(c0(x))
def pin(p):
 b=p.read_bytes();return {'path':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':h(b)}
def equality(a,b): return c0(a)==c0(b)
def checked_predictions(doc, expected_ids=None, revision=None):
 rows=doc['predictions'];ids=[p['record_id'] for p in rows]
 require(len(ids)==len(set(ids)),'prediction unique registry')
 if expected_ids is not None:require(ids==expected_ids,'prediction order')
 for p in rows:
  require(p['prediction_id']=='typed-prediction-'+digest({k:v for k,v in p.items() if k!='prediction_id'}),'prediction digest')
  if revision is not None:require(p['model_revision']==revision,'prediction model revision')
 return rows
try:
 inv=read(BASE/'collected_inventory.json');receiver=read(BASE/'receiver_receipt.json');contract=read(BASE/'evidence_contract.json');intent=read(BASE/'intent.json')
 require(inv['job']==receiver['job']==intent['request']['job']==intent['authority']['job']==JOB,'job joins')
 require(intent['request']['source_sha']==intent['authority']['source_sha']==SOURCE,'source commit joins')
 require(inv['file_count']==len(inv['files'])==504,'collected count504')
 seen=set()
 for e in inv['files']:
  rel=PurePosixPath(e['relative_path']);require(not rel.is_absolute() and '..' not in rel.parts and str(rel) not in seen,'safe unique inventory path');seen.add(str(rel));p=COL/str(rel)
  require(p.resolve().is_relative_to(COL.resolve()) and p.is_file() and not p.is_symlink(),'collected file scope')
  raw=p.read_bytes();require(len(raw)==e['bytes'] and h(raw)==e['sha256'],'inventory exact bytes')
 require({p.relative_to(COL).as_posix() for p in COL.rglob('*') if p.is_file()}==seen,'no unlisted collected files')
 projection=[{k:e[k] for k in ['relative_path','bytes','sha256']} for e in sorted(inv['files'],key=lambda x:x['relative_path'])]
 require(h(c1(projection))==receiver['inventory_sha256'] and h(c1(contract))==receiver['contract_sha256'],'receiver inventory contract joins')
 require(h(c1({k:v for k,v in receiver.items() if k!='receipt_sha256'}))==receiver['receipt_sha256'],'receiver digest')
 require(receiver['collection']=='COMPLETE_VERIFIED' and receiver['required_count']==347 and receiver['byte_integrity']=={'mismatched':[],'missing':[],'required_count':347,'state':'COMPLETE_VERIFIED','unavailable':[],'verified_count':347},'required347 complete')
 require(receiver['measurement_completeness']['state']=='COMPLETE' and not receiver['measurement_completeness']['failures'],'measurement completeness')
 terminal=read(COL/'results/result.json');manifest=read(ART/'manifest.json');report=read(ART/'worker_report.json');measurements=read(ART/'measurements.json');config=read(COL/'input/config.json')
 require(terminal==read(BASE/'curriculum_result.json') and terminal['status']=='TYPED_COURSE_DELIVERED' and terminal['failure'] is None,'terminal delivery')
 require((COL/'results/result.json.sha256').read_text().strip()==h((COL/'results/result.json').read_bytes()),'terminal sidecar')
 expected=set('batch_%03d.json'%i for i in range(160))|set('update_%03d.json'%i for i in range(160))|set(('initial.pt prelast.pt final.pt initial_checkpoint.json prelast_checkpoint.json final_checkpoint.json initial_predictions.json final_predictions.json initial_scoring.json final_scoring.json initial_reload_predictions.json final_reload_predictions.json replay_1_batch.json replay_2_batch.json replay_1_update.json replay_2_update.json replay_1_predictions.json replay_2_predictions.json replay_report.json encoding_checks.json installed_sources.json loaded_sources.json worker_report.json measurements.json').split())
 require(len(expected)==344 and len(manifest['artifacts'])==344 and {x['name'] for x in manifest['artifacts']}==expected,'exact344 artifact contract')
 require(terminal['artifacts']==manifest['artifacts'] and {p.name for p in ART.iterdir()}==expected|{'manifest.json'},'artifact terminal manifest joins')
 for e in manifest['artifacts']:
  raw=(ART/e['name']).read_bytes();require(len(raw)==e['bytes'] and h(raw)==e['sha256'],'artifact exact bytes')
 require(report['job']==measurements['job']==config['job']==JOB and report['source_sha']==measurements['source_sha']==config['source_sha']==SOURCE,'runtime source job joins')
 require(report['status']=='COMPLETE_EXPOSED_TYPED_COURSE_AND_SAME_PROCESS_RELOAD_OBSERVED' and report['checkpoint_reload_verified'] is True,'worker success scope')
 require(report['learning_advantage_established'] is False and measurements['learning_advantage_established'] is False and terminal['summary']['learning_advantage_established'] is False,'no learning advantage claim')
 require(report['design']==config['design']==intent['authority']['worker_config']['design'] and report['inputs']==config['inputs'],'design and input joins')
 require(config==intent['authority']['worker_config'] and config['inputs_sha256']==h(c1(config['inputs'])),'exact authorized config')
 require(report['design']['partial_course_is_success'] is False and report['design']['max_wall_seconds']==3300 and report['design']['global_optimizer_updates_max']==162,'bounded design')
 require(report['elapsed_seconds']<3300 and report['runtime']=={'cuda_version':'12.8','device':'cuda:0','gpu_name':'NVIDIA RTX PRO 4500 Blackwell Server Edition','torch_version':'2.11.0+cu128'},'reported runtime')
 archive=(BASE/'source.zip').read_bytes();require(h(archive)==intent['request']['archive_sha256']==intent['authority']['archive_sha256'],'authorized archive pin')
 with ZipFile(BytesIO(archive)) as z:
  names=z.namelist();require(len(names)==len(set(names))==232,'archive232 unique members')
  package_manifest_name='graph6_curriculum_source_manifest.json';package_raw=z.read(package_manifest_name);pm=json.loads(package_raw)
  require(h(package_raw)==intent['request']['manifest_sha256']==intent['authority']['manifest_sha256'],'authorized package manifest pin')
  require(pm['source_sha']==SOURCE and pm['inputs']==config['inputs'] and pm['typed_design']==config['design'],'package source input design')
  require(set(pm['members'])==set(names) and set(pm['files_sha256'])==set(pm['files_bytes'])==set(names)-{package_manifest_name},'package exact member manifest')
  for name in pm['files_sha256']:
   raw=z.read(name);require(h(raw)==pm['files_sha256'][name] and len(raw)==pm['files_bytes'][name],'package exact member bytes')
  source_index={e['path']:e for e in config['inputs']};require(len(source_index)==len(config['inputs'])==222,'declared222 inputs')
  for name,e in source_index.items():require(h(z.read(name))==e['sha256'] and len(z.read(name))==e['bytes'],'declared input source bytes')
  course_name='records/typed_course_001/checks_002/public_course.json';course_raw=z.read(course_name);course=json.loads(course_raw)
  require(h(course_raw)=='cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987','frozen full public course')
  loaded=read(ART/'loaded_sources.json');before={e['module']:e for e in loaded['before']['modules']};after={e['module']:e for e in loaded['after']['modules']}
  require(len(before)==28 and len(after)==46 and all(after[k]==v for k,v in before.items()),'project loaded28to46 stable subset')
  for phase in ['before','after']:
   for e in loaded[phase]['modules']:
    src=source_index[e['path']];require(e['execution']=='COMPILED_FROM_VERIFIED_SOURCE_BYTES' and e['sha256']==src['sha256'] and e['bytes']==src['bytes'],'loaded project exact declared source')
  vendor=read(ART/'installed_sources.json');require(vendor['before']['source_files']==vendor['after']['source_files'],'vendor35 unchanged source inventory')
  vendor_sources=vendor['after']['source_files'];require(len(vendor_sources)==35,'vendor35 source count')
  wheels={Path(n).name:ZipFile(BytesIO(z.read(n))) for n in names if n.endswith('.whl')}
  expected_vendor={(wheel,n) for wheel,wz in wheels.items() for n in wz.namelist() if n.endswith('.py')}
  require({(e['wheel'],e['path']) for e in vendor_sources}==expected_vendor,'all wheel Python files covered')
  vendor_index={e['path']:e for e in vendor_sources}
  for e in vendor_sources:
   raw=wheels[e['wheel']].read(e['path']);require(h(raw)==e['sha256'] and len(raw)==e['bytes'],'vendor exact wheel source bytes')
  vb={e['module']:e for e in vendor['before']['loaded_modules']};va={e['module']:e for e in vendor['after']['loaded_modules']}
  require(len(vb)==8 and len(va)==12 and all(va[k]==v for k,v in vb.items()),'vendor loaded8to12 stable subset')
  for phase in ['before','after']:
   require(vendor[phase]['status']=='INSTALLED_AND_LOADED_SOURCES_MATCH_PINNED_WHEELS','vendor status')
   for e in vendor[phase]['loaded_modules']:require(e['sha256']==vendor_index[e['source']]['sha256'],'loaded vendor exact source')
 course_ids=[x['record_id'] for x in course['registry']];require(len(course_ids)==len(set(course_ids))==564 and len(course['batches'])==160,'full course564registry160groups')
 kinds={x['record_id']:x['query']['kind'] for x in course['registry']}
 predictions={};scores={};checkpoint={}
 for phase,revision in [('initial',0),('final',160)]:
  pd=read(ART/(phase+'_predictions.json'));rows=checked_predictions(pd,course_ids,revision);require(pd['phase']==phase and all(p['depth']==8 for p in rows),'prediction phase depth')
  predictions[phase]={p['record_id']:p for p in rows};sd=read(ART/(phase+'_scoring.json'));raw=(ART/(phase+'_predictions.json')).read_bytes()
  require(sd['public_seal']=={'name':phase+'_predictions.json','bytes':len(raw),'sha256':h(raw)},'scoring exact public seal')
  require(sd['total']==len(sd['rows'])==564 and [s['record_id'] for s in sd['rows']]==course_ids,'score registry count order')
  for s,p in zip(sd['rows'],rows):
   require(s['prediction_id']==p['prediction_id'] and s['answer_digest']==digest(p['answer']) and type(s['correct']) is bool and s['kind']==kinds[p['record_id']],'score prediction answer joins')
   require(s['check_digest']==digest({k:v for k,v in s.items() if k not in {'record_id','prediction_id','check_digest'}}),'scoring check digest')
  require(sum(s['correct'] for s in sd['rows'])==sd['correct']==report[phase+'_score']['correct'] and report[phase+'_score']['total']==564,'score recount')
  scores[phase]={s['record_id']:s for s in sd['rows']}
 for phase,cursor in [('initial',0),('prelast',159),('final',160)]:
  cp=read(ART/(phase+'_checkpoint.json'));raw=(ART/(phase+'.pt')).read_bytes();require(len(raw)==cp['bytes'] and h(raw)==cp['sha256'],'opaque checkpoint file pin')
  require(cp['metadata']['cursor']==cp['metadata']['model_revision']==cursor and cp['run_identity_digest']==cp['metadata']['run_identity_digest']==digest(cp['metadata']['run_identity']),'checkpoint cursor run identity')
  checkpoint[phase]=cp
 require(checkpoint['initial']['run_identity_digest']==checkpoint['prelast']['run_identity_digest']==checkpoint['final']['run_identity_digest'],'same checkpoint run identity')
 require(checkpoint['initial']['metadata']['model_state_identity']!=checkpoint['final']['metadata']['model_state_identity'],'reported trainable state changed')
 require(len({cp['metadata']['encoder_state_identity'] for cp in checkpoint.values()})==1,'reported frozen encoder unchanged')
 baseline_slots=sum(len(p['scores']) for p in predictions['initial'].values());baseline_core=sum(len(p['scores'])*p['depth'] for p in predictions['initial'].values());require(baseline_slots==2598 and baseline_core==20784,'initial forward counts')
 trained=trained_slots=trained_core=0;gradients=[];all_occurrences=[];last=None
 for i,wanted in enumerate(course['batches']):
  bp=ART/('batch_%03d.json'%i);batch=read(bp);update=read(ART/('update_%03d.json'%i));rows=checked_predictions(batch,wanted['record_ids'],i)
  require(batch['cursor']==batch['model_revision']==i and batch['occurrence_ids']==wanted['occurrence_ids'] and batch['run_identity_digest']==checkpoint['initial']['run_identity_digest'],'batch exact course lineage')
  require(batch['batch_id']=='typed-batch-'+digest({k:v for k,v in batch.items() if k!='batch_id'}) and update['batch_id']==batch['batch_id'] and update['public_seal_sha256']==h(bp.read_bytes()),'update exact public batch seal')
  require(update['cursor_committed']==update['model_revision']==i+1 and [t['record_id'] for t in update['tasks']]==wanted['record_ids'],'update task order cursor')
  require(all(p['depth']==wanted['depth'] for p in rows),'course depth')
  trained+=len(rows);trained_slots+=sum(len(p['scores']) for p in rows);trained_core+=sum(len(p['scores'])*p['depth'] for p in rows);all_occurrences.extend(batch['occurrence_ids'])
  counters=update['counters'];require(counters['optimizer_updates']==counters['optimizer_step_attempts']==counters['backward_calls']==counters['backward_attempts']==counters['staged_batches']==i+1,'actual update counters')
  require(counters['prediction_calls']==564+trained and counters['private_loss_plan_calls']==trained and counters['slot_forwards']==baseline_slots+trained_slots and counters['core_forward_calls']==counters['core_forward_attempts']==counters['sample_core_passes']==baseline_core+trained_core,'exact main cumulative work')
  require(math.isfinite(update['gradient_squared_norm']) and update['gradient_squared_norm']>0 and all(math.isfinite(update[k]) for k in ['raw_batch_loss','normalized_batch_loss']),'finite nonzero training gradient and losses');gradients.append(update['gradient_squared_norm']);last=update
 require(trained==len(all_occurrences)==len(set(all_occurrences))==1152 and trained_slots==4613 and trained_core==17178,'complete1152 unique occurrences and main work')
 require(checkpoint['final']['metadata']['counters']==last['counters'],'final checkpoint saved main boundary')
 partials=[]
 for cursor in range(20,160,20):
  path=COL/'results/evidence'/('main_checkpoint_%04d.json'%cursor);doc=read(path);cp=doc['checkpoint'];pt=path.with_suffix('.pt');raw=pt.read_bytes();u=read(ART/('update_%03d.json'%(cursor-1)))
  require(doc['completed_main_updates']==cp['metadata']['cursor']==cursor and doc['main_course_complete'] is False and cp['metadata']['counters']==u['counters'] and cp['run_identity_digest']==checkpoint['initial']['run_identity_digest'],'partial checkpoint exact saved update boundary')
  require(len(raw)==cp['bytes'] and h(raw)==cp['sha256'],'partial opaque checkpoint pin');partials.append({'cursor':cursor,'bytes':len(raw),'sha256':h(raw)})
 replay=read(ART/'replay_report.json');require(len(replay['reloads'])==2 and len(replay['replays'])==2,'two reloads two replays')
 statekeys=['model_state_identity','optimizer_state_identity','encoder_state_identity','rng_state_identity']
 for rr in replay['reloads']:
  phase=rr['phase'];require(phase in ['initial','final'] and rr['checkpoint_sha256']==checkpoint[phase]['sha256'] and rr['exact_predictions'] is True,'reload checkpoint flag')
  require(rr['exact_state']=={k:checkpoint[phase]['metadata'][k] for k in statekeys},'reload reported exact state joins')
  rows=checked_predictions(read(ART/(phase+'_reload_predictions.json')),list(rr['kinds'].values()),0 if phase=='initial' else 160)
  require(set(rr['kinds'])==set(kinds.values()) and len(rows)==8 and all(equality(p,predictions[phase][p['record_id']]) for p in rows),'reload full prediction equality all eight kinds')
 for rr in replay['replays']:
  n=rr['branch'];require(n in [1,2] and rr['restored_cursor']==159 and rr['committed_cursor']==160 and rr['additional_presentations']==8 and rr['exact_preupdate_predictions'] is True and rr['exact_postupdate_predictions'] is True,'replay boundaries')
  bp=ART/('replay_%d_batch.json'%n);up=read(ART/('replay_%d_update.json'%n));require(bp.read_bytes()==(ART/'batch_159.json').read_bytes() and up['public_seal_sha256']==h(bp.read_bytes()),'replay exact preupdate seal')
  require(equality(up,read(ART/'update_159.json')),'replay full update receipt equality')
  require(rr['exact_state']=={k:checkpoint['final']['metadata'][k] for k in statekeys},'replay reported final state joins')
  rows=checked_predictions(read(ART/('replay_%d_predictions.json'%n)),revision=160);require(len(rows)==8 and set(kinds[p['record_id']] for p in rows)==set(kinds.values()) and all(equality(p,predictions['final'][p['record_id']]) for p in rows),'replay exact final predictions all eight kinds')
 work=report['global_actual_work'];phases={p['phase']:p['delta'] for p in work['phases']};require(len(phases)==7,'seven distinct actual work phases')
 require({k:sum(v[k] for v in phases.values()) for k in work['totals']}==work['totals'],'actual work sum')
 require(work['totals']['optimizer_updates']==work['totals']['backward_calls']==162 and work['totals']['core_forward_calls']==60202 and work['totals']['prediction_calls']==2328 and work['totals']['private_loss_plan_calls']==1168,'actual global work counts')
 require(work['main_presentations']==1152 and work['additional_replay_presentations']==16 and work['historical_restored_counters_counted_again'] is False,'replay counts separately')
 require(phases['main_training']==report['main_training_delta'] and phases['main_training']['core_forward_calls']==trained_core and phases['main_training']['slot_forwards']==trained_slots,'main work joins')
 for rr in replay['reloads']:require(rr['delta']==phases[rr['phase']+'_reload'],'reload work phase join')
 for rr in replay['replays']:require(rr['delta']==phases['replay_%d'%rr['branch']] and rr['delta']['optimizer_updates']==1,'replay work phase join')
 enc=read(ART/'encoding_checks.json');require(enc['initial']['finite_unit_packet_count']==564 and enc['final']['finite_unit_packet_count']==8,'encoding coverage boundary')
 require(equality(enc['initial']['frozen_identity'],enc['final']['frozen_identity']),'frozen identity before after')
 for phase in ['initial','final']:
  e=enc[phase];require(e['readout_distinct_unit_rows']==90 and all(abs(x-1)<2e-5 for x in e['packet_norm_range']) and len(e['representatives'])==8,'encoding declared numeric checks')
  require(set(x['kind'] for x in e['representatives'])==set(kinds.values()) and all(x['packet_exact'] is True and x['slot_exact'] is True and abs(x['slot_norm']-1)<2e-5 for x in e['representatives']),'eight representative cache checks')
 perkind={}
 for kind in sorted(set(kinds.values())):
  ids=[key for key in course_ids if kinds[key]==kind];a=[scores['initial'][key]['correct'] for key in ids];b=[scores['final'][key]['correct'] for key in ids]
  perkind[kind]={'total':len(ids),'initial_correct':sum(a),'final_correct':sum(b),'gained':sum(not x and y for x,y in zip(a,b)),'lost':sum(x and not y for x,y in zip(a,b)),'retained_correct':sum(x and y for x,y in zip(a,b))}
 for key in course_ids:
  a,b=scores['initial'][key],scores['final'][key];require(all(a[k]==b[k] for k in ['target_digest','query_id','source_digest','checker_profile_digest','admissible_answer_count']),'same initial final target binding')
 score_summary={k:sum(row[k] for row in perkind.values()) for k in ['total','initial_correct','final_correct','gained','lost','retained_correct']}
 require(score_summary=={'total':564,'initial_correct':18,'final_correct':196,'gained':195,'lost':17,'retained_correct':1},'paired score recount')
 require(measurements==terminal['summary'],'summary exact measurements')
 receipt={'schema':'cncm.typed-course-independent-delivery-review/0.1','status':'INDEPENDENT_DELIVERY_BYTE_AND_JOIN_CHECKS_PASS','reviewed_at_utc':datetime.now(timezone.utc).isoformat(),'job':JOB,'source_sha':SOURCE,'pins':[pin(BASE/n) for n in ['collected_inventory.json','receiver_receipt.json','evidence_contract.json','intent.json','curriculum_result.json','source.zip']]+[pin(ART/n) for n in ['manifest.json','worker_report.json','replay_report.json','encoding_checks.json','installed_sources.json','loaded_sources.json','initial_scoring.json','final_scoring.json']]+[pin(Path(__file__))],'verified_collected_files':504,'required_files_verified':347,'exact_artifact_count':344,'declared_inputs':222,'archive_members':232,'loaded_project_modules':{'before':28,'after':46,'common_unchanged':True},'vendor_sources':{'installed_files':35,'loaded_before':8,'loaded_after':12,'common_unchanged':True,'all_wheel_python_sources_checked':True},'main_training':{'updates':160,'presentations':1152,'unique_occurrences':1152,'slot_forwards':4613,'core_forwards':17178,'gradient_squared_norm_range':[min(gradients),max(gradients)]},'actual_global_work':work['totals'],'additional_replay_presentations':16,'checkpoints':{phase:{'bytes':cp['bytes'],'sha256':cp['sha256'],'cursor':cp['metadata']['cursor']} for phase,cp in checkpoint.items()},'partial_checkpoints':partials,'reconstruction':{'initial_and_final_eight_kind_predictions_exact':True,'two_pre_last_update_replays_exact_seals_updates_and_final_predictions':True,'state_identity_strings_join_checkpoint_metadata':True,'checkpoint_payloads_decoded_by_this_review':False,'boundary':replay['boundary']},'exposed_score':score_summary,'per_kind':perkind,'encoding':{'initial_norm_packets':564,'final_norm_packets':8,'cache_direct_representatives_each_phase':8,'readout_distinct_unit_rows':90,'all564_cache_direct_equivalence_claim':False},'runtime_reported':report['runtime'],'elapsed_seconds_reported':report['elapsed_seconds'],'peak_cuda_allocated_bytes_reported':report['peak_cuda_allocated_bytes'],'peak_cuda_reserved_bytes_reported':report['peak_cuda_reserved_bytes'],'false_claim_flags':{'learning_advantage_established':False,'partial_course_is_success':False,'source_package_launch_enabled':False,'source_package_launch_flag_boundary':pm['boundary']},'cleanup':'Handled separately by lifecycle and current provider reads; this audit does not establish all resource cleanup.','boundaries':['Exposed training material from one source seed and one model initialization; no held-out transfer or matched benefit.','195 gained and17lost items are paired changes on the same exposed564, not a retention or generalization benchmark.','Same-process checkpoint reconstruction only; no fresh-process or cross-device numerical restart proof.','Saved state identities and prediction equality were joined without decoding checkpoints or rerunning models.','Loaded source receipts describe an exact process loader and source bytes, not authenticated hardware or operating-system truth.','No private checker, model, tensor, or provider mutation executed during this independent audit.'],'check_count':len(checks)}
 (OUT/'receipt.json').open('xb').write(c1(receipt))
 print(json.dumps({'status':receipt['status'],'receipt':pin(OUT/'receipt.json'),'counts':{'files':504,'artifacts':344,'checks':len(checks)},'score':score_summary,'per_kind':perkind}))
except Exception as error:
 failure={'status':'REVIEW_FAILED','type':type(error).__name__,'detail':str(error),'checks_completed':len(checks),'helper':pin(Path(__file__))}
 (OUT/'failure.json').open('xb').write(c1(failure));print(json.dumps(failure));raise