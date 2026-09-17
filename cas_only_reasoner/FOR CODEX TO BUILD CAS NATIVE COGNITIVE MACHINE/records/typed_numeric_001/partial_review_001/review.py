from pathlib import Path, PurePosixPath
from hashlib import sha256
from datetime import datetime, timezone
import json, math
ROOT=Path.cwd(); OUT=ROOT/'records/typed_numeric_001/partial_review_001'; BASE=ROOT/'records/typed_numeric_001/receipt_001'; COL=BASE/'collected'; ART=COL/'results/artifacts'
def read(p): return json.loads(p.read_bytes())
def h(b): return sha256(b).hexdigest()
def canon(d): return (json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode()
def pin(p):
 b=p.read_bytes();return {'path':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':h(b)}
inv=read(BASE/'collected_inventory.json');receiver=read(BASE/'receiver_receipt.json');contract=read(BASE/'evidence_contract.json');launch=read(BASE/'launch.json')
assert inv['job']==receiver['job']==launch['job']=='cas-meta2-typedcourse-20260917020901-85736789'
assert inv['file_count']==len(inv['files'])==142
seen=set()
for e in inv['files']:
 r=PurePosixPath(e['relative_path']);assert not r.is_absolute() and '..' not in r.parts and str(r) not in seen
 seen.add(str(r));p=COL/str(r);assert p.resolve().is_relative_to(COL.resolve()) and p.is_file() and not p.is_symlink()
 b=p.read_bytes();assert len(b)==e['bytes'] and h(b)==e['sha256']
assert {p.relative_to(COL).as_posix() for p in COL.rglob('*') if p.is_file()}==seen
projection=[{k:e[k] for k in ['relative_path','bytes','sha256']} for e in sorted(inv['files'],key=lambda x:x['relative_path'])]
assert h(canon(projection))==receiver['inventory_sha256'] and h(canon(contract))==receiver['contract_sha256']
assert h(canon({k:v for k,v in receiver.items() if k!='receipt_sha256'}))==receiver['receipt_sha256']
assert receiver['collection']=='INCOMPLETE' and not receiver['byte_integrity']['mismatched'] and not receiver['byte_integrity']['unavailable']
terminal=read(COL/'results/result.json');assert terminal==read(BASE/'curriculum_result.json') and terminal['status']=='WORKER_FAILED' and terminal['failure']['type']=='TimeoutExpired' and '1800 seconds' in terminal['failure']['message']
assert (COL/'results/result.json.sha256').read_text().strip()==h((COL/'results/result.json').read_bytes())
config=read(COL/'input/config.json');assert config['source_sha']=='857367899983783c8f048df195338c71bdcb8aa5'
course_path=ROOT/'records/typed_course_001/checks_002/public_course.json';assert h(course_path.read_bytes())=='cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987';course=read(course_path)
checkpoint=read(ART/'initial_checkpoint.json');assert len((ART/'initial.pt').read_bytes())==checkpoint['bytes'] and h((ART/'initial.pt').read_bytes())==checkpoint['sha256']
initial=read(ART/'initial_predictions.json');scoring=read(ART/'initial_scoring.json');rows=initial['predictions'];ids=[r['record_id'] for r in rows]
assert initial['phase']=='initial' and len(rows)==len(set(ids))==564
assert scoring['public_seal']['sha256']==h((ART/'initial_predictions.json').read_bytes()) and scoring['public_seal']['bytes']==len((ART/'initial_predictions.json').read_bytes())
assert len(scoring['rows'])==scoring['total']==564 and [r['record_id'] for r in scoring['rows']]==ids
assert [r['prediction_id'] for r in scoring['rows']]==[r['prediction_id'] for r in rows]
assert all(type(r['correct']) is bool for r in scoring['rows']) and sum(r['correct'] for r in scoring['rows'])==scoring['correct']==18
baseline_slots=sum(len(r['scores']) for r in rows);baseline_core=sum(len(r['scores'])*r['depth'] for r in rows)
assert baseline_slots==2598 and baseline_core==20784
updates=sorted(ART.glob('update_*.json'));batches=sorted(ART.glob('batch_*.json'));assert [p.name for p in updates]==['update_%03d.json'%i for i in range(61)] and [p.name for p in batches]==['batch_%03d.json'%i for i in range(62)]
trained=0;trained_slots=0;trained_core=0;gradients=[];last=None
for i,p in enumerate(updates):
 u=read(p);b=read(batches[i]);wanted=course['batches'][i]
 assert b['cursor']==b['model_revision']==i and u['cursor_committed']==u['model_revision']==i+1
 assert b['run_identity_digest']==checkpoint['run_identity_digest'] and u['batch_id']==b['batch_id']
 assert h(batches[i].read_bytes())==u['public_seal_sha256']
 assert b['occurrence_ids']==wanted['occurrence_ids']
 bids=[r['record_id'] for r in b['predictions']];assert bids==wanted['record_ids']==[r['record_id'] for r in u['tasks']]
 assert all(r['depth']==wanted['depth'] and r['model_revision']==i for r in b['predictions'])
 assert len(u['loss_plan_digests'])==len(bids)
 trained+=len(bids);trained_slots+=sum(len(r['scores']) for r in b['predictions']);trained_core+=sum(len(r['scores'])*r['depth'] for r in b['predictions'])
 c=u['counters'];assert c['optimizer_updates']==c['optimizer_step_attempts']==c['backward_calls']==c['backward_attempts']==c['staged_batches']==i+1
 assert c['prediction_calls']==564+trained and c['private_loss_plan_calls']==trained
 assert c['slot_forwards']==baseline_slots+trained_slots and c['core_forward_calls']==c['core_forward_attempts']==c['sample_core_passes']==baseline_core+trained_core
 assert math.isfinite(u['gradient_squared_norm']) and u['gradient_squared_norm']>0 and all(math.isfinite(u[k]) for k in ['raw_batch_loss','normalized_batch_loss'])
 gradients.append(u['gradient_squared_norm']);last=u
uncommitted=read(batches[-1]);wanted=course['batches'][61]
assert uncommitted['cursor']==uncommitted['model_revision']==61 and uncommitted['occurrence_ids']==wanted['occurrence_ids'] and [r['record_id'] for r in uncommitted['predictions']]==wanted['record_ids']
assert trained==440 and trained_core==6244 and trained_slots==1751
absent=['final.pt','prelast.pt','final_checkpoint.json','final_predictions.json','final_scoring.json','replay_report.json','worker_report.json','loaded_sources.json','installed_sources.json']
assert all(not (ART/n).exists() for n in absent)
report={'schema':'cncm.typed-course-partial-review/0.1','status':'PARTIAL_EVIDENCE_BYTE_AND_JOIN_CHECKS_PASS','reviewed_at':datetime.now(timezone.utc).isoformat(),'job':inv['job'],'source_sha':config['source_sha'],'inputs':[pin(BASE/n) for n in ['collected_inventory.json','receiver_receipt.json','evidence_contract.json','curriculum_result.json','launch.json']]+[pin(course_path),pin(ART/'initial_checkpoint.json'),pin(ART/'initial_predictions.json'),pin(ART/'initial_scoring.json'),pin(updates[-1]),pin(batches[-1])],'verified_collected_files':len(seen),'receiver_collection':receiver['collection'],'required_files':receiver['required_count'],'required_present':receiver['byte_integrity']['verified_count'],'required_missing':len(receiver['byte_integrity']['missing']),'terminal':{'status':terminal['status'],'failure_type':terminal['failure']['type'],'timeout_seconds':1800},'updates':{'completed':61,'hash_bound_batch_update_pairs':61,'trained_presentations':trained,'training_core_forward_calls':trained_core,'baseline_core_forward_calls':baseline_core,'total_core_forward_calls':last['counters']['core_forward_calls'],'training_slot_forwards':trained_slots,'gradient_squared_norm_range':[min(gradients),max(gradients)],'last_counters':last['counters']},'uncommitted_seal':{'cursor':61,'presentations':len(uncommitted['predictions']),'counts_as_completed_update':False},'initial_score':{'correct':18,'total':564,'public_prediction_sha256':h((ART/'initial_predictions.json').read_bytes()),'recount_only_no_semantic_reexecution':True},'initial_checkpoint':{'sha256':checkpoint['sha256'],'bytes':checkpoint['bytes'],'decoded':False},'absent_completion_artifacts':absent,'cleanup':'Independent current provider observation must be supplied separately; original receiver receipt predates cleanup.','boundaries':['Not full-course acceptance.','No final learned checkpoint or post-training score was delivered.','No learning gain, held-out performance, matched benefit, or reload success is established.','Hashes bind supplied bytes, not independent execution truth.','No model, tensor, private semantic checker, or provider mutation was executed by this review.'],'review_helper':pin(Path(__file__))}
with (OUT/'receipt.json').open('xb') as f:f.write(canon(report))
print(json.dumps({'status':report['status'],'verified_files':len(seen),'completed_updates':61,'trained_presentations':trained,'training_core_calls':trained_core,'initial_correct':18,'uncommitted_presentations':len(uncommitted['predictions']),'receipt':pin(OUT/'receipt.json')}))