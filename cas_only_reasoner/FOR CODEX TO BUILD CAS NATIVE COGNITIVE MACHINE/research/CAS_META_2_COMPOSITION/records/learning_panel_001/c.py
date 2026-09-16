"""Publish only public identities and independently recount the audit artifacts."""
from a import *
from cas_meta2.complementary_teaching.data import validate_manifest
from cas_meta2.complementary_teaching import course
from cas_meta2.codec import validate_public
manifest=validate_manifest(read(PREP/'data_manifest.json'))
supply=read(OUT/'supply.json'); envelope=read(OUT/'envelope.json'); history=read(OUT/'history.json'); reconciliation=read(OUT/'reconcile.json')
family={r['family_id']:r for r in manifest['families']}
panels={}
for name in ('development_whole_tasks','final_application'):
    rows=[]
    for i,task in enumerate(manifest['panels'][name]):
        validate_public(task['public'])
        row=family[task['family_id']]
        rows.append({'source_pointer':'/panels/'+name+'/'+str(i),'source_record_id':task['record_id'],
          'family_id':task['family_id'],'topology':row['topology'],'split':row['split'],'operation':task['op'],
          'public_sha256':digest(task['public']),'encoded_options_sha256':digest(task['encoded_options']),
          'public_packet_sha256':digest({k:task[k] for k in ('record_id','public','encoded_options')}),
          'public_input_sha256':course.public_identity(task)})
    panels[name]=rows
train=course.compile_complementary_course(101,'ALT_COMPONENT_WHOLE')
training_topologies=sorted({graph_key(t['graph']) for b in train['batches'] for t in b['tasks'] if 'graph' in t})
index={'schema':'cas.learning-panel-existing-public-index/0.1','status':'EXISTING_CANDIDATE_REFERENCES_ONLY_NOT_A_NEW_PANEL_OR_RUN_FREEZE',
 'source_manifest':pin(PREP/'data_manifest.json'),'source_data_sha256':manifest['data_sha256'],
 'prediction_allowlist':['record_id','public','encoded_options'],'panels':panels,
 'training_source':{'seed':101,'condition':'ALT_COMPONENT_WHOLE','schedule_sha256':train['schedule_sha256'],
  'topologies_in_graph_bearing_tasks':training_topologies,'scope':'Existing CFC course; candidate training proposal, not new neural delivery.'},
 'private_labels_exported':False,'old_record_id_scope':'Provenance only. New rendering or encoder context requires a new bound input identity.',
 'excluded_duplicate_audits':{'development_components':6,'final_components':30},
 'old_retention_audits':{'development_earlier_skills':96,'final_earlier_skills':96,'novelty':'Historically examined; not new held-out topology evidence.'}}
write('index.json',index)
checks=[]
def check(name,condition):
    if not condition:raise AssertionError(name)
    checks.append(name)
check('92 exact enumerated /45 excluded /47 candidate',len(supply['rows'])==92 and sum(r['historically_excluded'] for r in supply['rows'])==45 and sum(r['candidate_pool'] for r in supply['rows'])==47)
check('existing6development30final11unsupported',supply['counts']=={'development':6,'final':30,'excluded':45,'unallocated':11})
check('all11unsupportedlackvia',len(reconciliation['unsupported_candidates'])==11 and all(r['unsupported_reach_classes']==['via'] for r in reconciliation['unsupported_candidates']))
dev={r['topology'] for r in panels['development_whole_tasks']};final={r['topology'] for r in panels['final_application']}
check('canonical topology split disjoint',len(dev)==6 and len(final)==30 and not dev&final)
check('training graph topology disjoint from candidate dev/final',not set(training_topologies)&(dev|final))
check('public projection sizes18and90',len(panels['development_whole_tasks'])==18 and len(panels['final_application'])==90)
check('final operations30each',Counter(r['operation'] for r in panels['final_application'])==Counter({'LIST_PARTS':30,'FIND_SHARED_PART':30,'REACHED_VIA':30}))
check('all three separate tokenizers fit all audits',len(envelope['rows'])==3 and all(p['failures']==0 and p['maximum_complete_tokens']<=1024 and p['maximum_framed_tokens']<=1024 for r in envelope['rows'] for p in r['panels'].values()))
check('actual ordered diagnostic tokenizer matched',reconciliation['ordered_tokenizer_match']['matched_tokenizer_sha256']==envelope['rows'][1]['tokenizer_sha256'])
check('all five broadscan parsing failures explicitly reconciled',len(history['parse_failures'])==len(reconciliation['smoke_recovery'])==5)
check('only two authored candidate occurrence files',len(history['candidate_occurrences'])==2 and all('preparation_20260916/data_manifest.json' in r['path'] or 'prepared/perspective_audit_public.json' in r['path'] for r in history['candidate_occurrences']))
overlap=[v for r in reconciliation['candidate_occurrences'] for v in r.get('final_variant_development_overlap',[]) if v['form']=='graph_record']
check('two perspective final variants overlap one dev topology',len(overlap)==2 and len({v['topology'] for v in overlap})==1)
unchanged={}
for document in (supply,envelope,reconciliation):
    for row in document.get('source_pins',[])+document.get('input_pins',[]):
        actual=pin(ROOT/row['path']);check('unchanged:'+row['path'],actual==row);unchanged[row['path']]=row['sha256']
gate=ROOT.parent.parent/'docs/CNCM_NEXT_LEARNING_EXPERIMENT_GATE.md'
write('check.json',{'schema':'cas.learning-panel-audit-check/0.1','status':'PASS','checks':checks,
  'unchanged_input_files':unchanged,'artifact_pins':[pin(OUT/n) for n in ('a.py','b.py','c.py','supply.json','envelope.json','history.json','reconcile.json','index.json')],
  'gate_document_at_review':{'path':str(gate),'sha256':sha256(gate.read_bytes()).hexdigest()},
  'new_neural_executions':0,'new_optimizer_updates':0,'new_provider_calls':0,
  'not_proven':['Global history outside the retained tree','New numerical ordered-encoder training/checkpoint compatibility','Learned transfer, retention, statistical power or causal benefit','Full CAS Phase3 completion']})
