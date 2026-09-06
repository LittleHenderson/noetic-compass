"""Offline v7 review. Requires external source/archive/packet/job identities."""
import argparse
from datetime import datetime,timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import platform
import re
import sys
import traceback
import zipfile


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def progress(stage):
    print(json.dumps({'stage':stage,'utc':datetime.now(timezone.utc).isoformat()}),flush=True)


def metadata(packet,manifest,source,archive_pin,launch_pin,job,helper,c):
    c.require(type(job) is str and re.fullmatch(r'cas-meta2-\d{14}-[0-9a-f]{8}',job),
              'V7_EXTERNAL_JOB_REQUIRED')
    collection,index=helper._collection(packet,job,source,archive_pin)
    c.require(index is True and collection['returncode']==0 and collection['partial_evidence'] is False
        and collection['smoke_only'] is False and collection.get('experiment')==manifest['experiment'],
        'V7_COMPLETE_COLLECTION_REQUIRED')
    remote=packet.json('cloud_job/job.json')
    c.require(all(remote.get(k)==v for k,v in {'job':job,'source_sha':source,'archive_sha256':archive_pin,
        'baseline_sha':c.BASELINE,'returncode':0,'smoke_only':False,'experiment':manifest['experiment']}.items())
        and type(remote['returncode']) is int,'V7_JOB_IDENTITY')
    expected_command=['/opt/cas-meta2/venv/bin/python','-B',
        '/opt/cas-meta2/package/'+c.PILOT+'/aws/prototype_remote_v7.py',
        '--output','/opt/cas-meta2/package/'+c.PILOT+'/runs/'+c.BASE.rstrip('/'),
        '--job',job,'--max-wall-seconds','6900','--launch-manifest','/opt/cas-meta2/package/launch_manifest.json',
        '--launch-manifest-sha256',launch_pin]
    c.require(packet.json('cloud_job/command.json')==expected_command,'V7_COORDINATOR_COMMAND')
    campaign=packet.json(c.BASE+'campaign_receipt.json')
    expected={'schema':'cas-meta2-prototype-campaign/7','job':job,'experiment':manifest['experiment'],
        'completed':True,'training_performed':True,'training_attempted':True,
        'native_evaluation_completed':True,'learning_accepted':False,'release_accepted':False,
        'automatic_retry':False,'stage':'completed'}
    c.require(all(type(campaign.get(k)) is type(v) and campaign[k]==v for k,v in expected.items())
        and 'failure' not in campaign and 'finalization_error' not in campaign
        and set(campaign['processes'])=={'gpu_gate','dataset','training','evaluate'},'V7_COMPLETE_CAMPAIGN_REQUIRED')
    c.require(packet.json(c.BASE+'campaign_status.json')=={'job':job,'stage':'completed','completed':True},
              'V7_FINAL_STATUS_COPY')
    index_record=packet.json(c.BASE+'payload_sha256.json')
    c.require(index_record=={name.removeprefix(c.BASE):row['sha256'] for name,row in packet.inventory.items()
        if name.startswith(c.BASE) and name!=c.BASE+'payload_sha256.json'},'V7_FULL_PAYLOAD_INDEX')
    coordinator=packet.json('cloud_job/prototype_coordinator_receipt.json')
    c.require(all(type(coordinator.get(k)) is type(v) and coordinator[k]==v for k,v in {
        'schema':'cas-meta2-prototype-coordinator/7','completed':True,'job':job,
        'experiment':manifest['experiment'],'learning_accepted':False,'source_and_inputs_rechecked':True,
        'source_sha':source,'launch_manifest_sha256':launch_pin}.items())
        and 'failure' not in coordinator,'V7_COMPLETE_COORDINATOR_REQUIRED')
    fixed={'train_examples':896,'validation_examples':96,'test_variants':72,'matched_test_triplets':24,
        'optimizer_steps_per_family':11200,'native_arm_verdicts':360,
        'known_fixture_smoke_reference_cases':9,'known_fixture_smoke_arm_verdicts':45}
    c.require(all(type(coordinator['evidence'].get(k)) is type(v) and coordinator['evidence'][k]==v
                  for k,v in fixed.items()),'V7_COORDINATOR_COUNTS')
    hashes=coordinator['evidence']['files_sha256']
    required={'campaign_receipt.json','payload_sha256.json','dataset_assembly_receipt.json','training_gate.json',
        'training/training_receipt.json','training/neural_predictions.jsonl','training/neural_predictions_seal.json',
        'native/native_receipt.json','native/evaluation_results.json'}
    smoke={name.removeprefix(c.BASE) for name in packet.inventory if name.startswith(c.BASE)
           and name.endswith('/gpu_smoke_receipt.json')}
    c.require(len(smoke)==1 and set(hashes)==required|smoke,'V7_COORDINATOR_HASH_COVERAGE')
    for name,pin in hashes.items():packet.same_hash(c.BASE+name,pin)
    gate=helper._gpu_gate(packet,'contract')
    expected_contract=['/opt/cas-meta2/venv/bin/python','-m','pytest','-m','gpu',
        'tests/test_execution_contract.py','-q','--junitxml',
        '/opt/cas-meta2/package/'+c.PILOT+'/runs/cloud_job/gpu_contract_tests.xml','-p','no:cacheprovider']
    c.require(packet.json('cloud_job/gpu_contract_command.json')==expected_contract,'V7_EXACT_CONTRACT_GPU_COMMAND')
    return {'collection':collection,'campaign':campaign,'coordinator':coordinator,'contract_gpu_gate':gate,
            'runtime':packet.json('cloud_job/runtime.json')}


def native_audit(packet,context,prior,helpers,engine,validator,modules,c,runtime):
    evidence=helpers['evidence'];workers=set();seen=0
    helper_map=modules['native'].recovery_identity()
    def identity(record):
        nonlocal seen
        c.require(set(record)=={'pid','environment','source_sha256','baseline','recovery_helpers_sha256'}
            and type(record['pid']) is int and record['pid']>0
            and record['pid']!=context['processes']['evaluate']['pid']
            and record['source_sha256']==context['source'] and record['baseline']==context['baseline']
            and record['recovery_helpers_sha256']==helper_map,'V7_NATIVE_WORKER_IDENTITY')
        evidence.environment(record['environment'],runtime,c)
        workers.add(record['pid']);c.require(len(workers)<=8,'V7_NATIVE_WORKER_COUNT')
        seen+=1
        if seen==1 or seen%12==0:progress('main_stored_case_start_'+str(seen))
    context['runtime_identity']=prior['outcomes']['runtime_identity']
    audited=helpers['outcomes'].audit(packet,context,engine,validator,helpers['partial'],identity,c)
    receipt=packet.json(c.NATIVE+'native_receipt.json')
    c.require(receipt['schema']=='cas-meta2-prototype-native-evaluation/7' and receipt['completed'] is True
        and receipt['cases']==receipt['reference_cases']==72 and receipt['arm_verdicts']==360
        and type(receipt['workers']) is int and receipt['workers']==8
        and receipt['learning_accepted'] is False and receipt['recovery_helper_manifest_sha256']==c.RUNTIME
        and receipt['seal']==context['seal'],'V7_NATIVE_RECEIPT_IDENTITY')
    helpers['outcomes'].compare_aggregate(receipt['results'],audited['results'],c)
    groups={k:v for k,v in audited['groups'].items() if k!='all'}
    stored=packet.json(c.NATIVE+'evaluation_results.json')
    c.require(set(groups)==set(receipt['groups'])==set(stored['groups']),'V7_NATIVE_GROUP_COVERAGE')
    for name,results in groups.items():
        helpers['outcomes'].compare_aggregate(receipt['groups'][name],results,c)
        helpers['outcomes'].compare_aggregate(stored['groups'][name],results,c)
    return audited,receipt,sorted(workers)


def run(*,packet_path,packet_sha256,extracted,source_archive,source_archive_sha256,source_sha,job,
        create_extraction=False):
    here=Path(__file__).resolve().parent;c=module('_v7_review_common',here/'common.py')
    own={p.name:c.file_hash(p) for p in here.glob('*.py')}
    progress('checking_external_source_and_git')
    with c.pure_guard():
        manifest,prior=c.source_preflight(source_archive,source_archive_sha256,source_sha)
        with zipfile.ZipFile(source_archive) as archive:
            launch_pin=sha256(archive.read('launch_manifest.json')).hexdigest()
        helpers=c.prior_helpers(prior);evidence=helpers['evidence']
        helper=c.load('_v7_collection',c.ROOT/'tools/inspect_cloud_packet.py')
        from cas_meta2.contrast_v6 import curriculum
        from cas_meta2.contrast_v7 import checks,train,data,campaign,parent,native_evaluation,gpu_preflight
        modules={'checks':checks,'train':train,'data':data,'curriculum':curriculum,'campaign':campaign,
                 'parent':parent,'native':native_evaluation,'gpu_preflight':gpu_preflight}
        spec=campaign.registered_spec()
        c.require(manifest['experiment']['spec_sha256']==c.file_hash(c.ROOT/'EXPERIMENT_PROTOTYPE_V7.json'),
                  'V7_REGISTERED_SPEC_PIN')
        progress('checking_and_extracting_external_packet')
        packet=c.Packet(packet_path,packet_sha256,extracted,create=create_extraction)
        meta=metadata(packet,manifest,source_sha,source_archive_sha256,launch_pin,job,helper,c)
        initial=packet.json(c.BASE+'initial_identity.json')
        admission_path=c.ROOT/'records/contrast_failure_review_v6_001/run_002/failure_review_receipt.json'
        c.pin(admission_path,c.ADMISSION);admission=c.decode(admission_path.read_bytes())
        evidence.baseline(initial['baseline'],admission['baseline'],c)
        c.require(initial['baseline']==meta['campaign']['baseline_before'],'V7_CAMPAIGN_BASELINE_COPY')
        c.require({v['wheel_sha256'] for v in initial['baseline']['installed_wheels'].values()}
            =={manifest['files_sha256'][name] for name in manifest['wheel_paths']},'V7_BASELINE_WHEEL_PINS')
        dataset=c.load('_v7_dataset_recount',here/'dataset.py')
        progress('recounting_training_and_exact_training_append')
        context=dataset.audit(packet,job=job,spec=spec,initial=initial,campaign=meta['campaign'],
                              modules=modules,c=c,evidence=evidence)
        progress('recounting_known_fixture_gpu_smoke')
        gpu=c.load('_v7_gpu_receipt_review',here/'gpu.py')
        smoke=gpu.audit_smoke(packet,job=job,source=context['source'],baseline=context['baseline'],
                             spec=spec,modules=modules,c=c,evidence=evidence)
        c.require(meta['campaign']['gpu_gate']==smoke['campaign_gpu_gate'],'V7_CAMPAIGN_GPU_COPY')
        gpu_process=packet.json(c.BASE+'processes/gpu_gate/process_receipt.json')
        c.require(meta['campaign']['processes']['gpu_gate']==gpu_process
            and evidence.timestamp(gpu_process['finished_utc'],c)
                <=evidence.timestamp(context['processes']['dataset']['started_utc'],c),'V7_GPU_BEFORE_DATASET')
        c.require(type(gpu_process['wall_seconds']) in (int,float)
            and 0<gpu_process['wall_seconds']<=spec['gpu_gate_max_seconds']==450,
            'V7_REGISTERED_OUTER_GPU_450_SECOND_BOUND')
        engine=c.load('_v7_stored_engine',c.ROOT/'tools/audit_stored_packet_v3.py')
        from jsonschema import Draft202012Validator
        from cas_meta2.campaign_v3 import admission_error
        from cas_meta2.curriculum import check_native_topology,graph_signature,parse_problem
        from cas_meta2.stored import verify_stored_composition
        engine.Draft202012Validator=Draft202012Validator;engine.admission_error=admission_error
        engine.check_native_topology=check_native_topology;engine.graph_signature=graph_signature
        engine.parse_problem=parse_problem;engine.verify_stored_composition=verify_stored_composition
        engine.safe_name=c.safe_name
        validator,schema=engine.protected_schema()
        audited,native,workers=native_audit(packet,context,prior,helpers,engine,validator,modules,c,meta['runtime'])
        compact={k:native[k] for k in ('results','groups','cases','reference_cases','arm_verdicts')}
        compact.update(native_receipt_sha256=packet.inventory[c.NATIVE+'native_receipt.json']['sha256'],
            evaluation_results_sha256=packet.inventory[c.NATIVE+'evaluation_results.json']['sha256'])
        c.require(meta['campaign']['native']==compact,'V7_CAMPAIGN_NATIVE_COPY')
        c.require(meta['campaign']['actual_splits']==context['manifest']['splits']
            and meta['campaign']['dataset_assembly_receipt_sha256']
                ==packet.inventory[c.BASE+'dataset_assembly_receipt.json']['sha256'],'V7_CAMPAIGN_DATA_COPY')
        progress('checking_all_schemas_exports_and_final_bytes')
        traces=engine.validate_all_traces(packet,validator);exports=helpers['outcomes'].exports(packet,validator,c)
        diagnostics=helpers['report'].build_report(context['tasks'],context['predictions'],audited['cases'],
                                                   helpers['differences'],c)
        for row in (meta['campaign'],meta['coordinator']):
            c.require(type(row['wall_seconds']) in (int,float) and 0<row['wall_seconds']<=spec['max_wall_seconds'],
                      'V7_PARENT_WALL_BOUND')
        for name,row in context['processes'].items():
            bound={'dataset':spec['dataset_max_seconds'],'training':spec['training']['max_seconds']+15,
                   'evaluate':spec['native_max_seconds']+15}[name]
            c.require(row['wall_seconds']<=bound,'V7_PHASE_WALL_BOUND:'+name)
        c.require(evidence.timestamp(meta['coordinator']['started_utc'],c)
            <=evidence.timestamp(gpu_process['started_utc'],c)
            and evidence.timestamp(context['processes']['evaluate']['finished_utc'],c)
                <=evidence.timestamp(meta['campaign']['finished_utc'],c)
                <=evidence.timestamp(meta['coordinator']['finished_utc'],c),'V7_FINAL_PROCESS_ORDER')
        compute=packet.json('cloud_job/compute_window.json')
        c.require(compute['maximum_seconds']==7200
            and compute['includes_cuda_probe_meta1_gpu_gate_and_v7_parent'] is True
            and 0<compute['deadline_epoch']-compute['started_epoch']<=7200
            and compute['started_epoch']<=evidence.timestamp(meta['coordinator']['started_utc'],c).timestamp()
            and evidence.timestamp(meta['coordinator']['finished_utc'],c).timestamp()<=compute['deadline_epoch'],
            'V7_COMPUTE_WINDOW_BOUND')
        meta['compute_window']=compute
        c.require(train.source_identity()==context['source'] and campaign.source_identity()==initial['campaign_source_sha256'],
                  'V7_SOURCE_MAP_CHANGED_AT_END')
        c.check_source_again(manifest);packet.verify_all();c.pin(source_archive,source_archive_sha256)
        c.prior_helpers(prior)
        c.require(own=={p.name:c.file_hash(p) for p in here.glob('*.py')},'V7_REVIEWER_BYTES_CHANGED')
        c.require(not any(name.split('.')[0] in c.FORBIDDEN for name in sys.modules),'V7_NEURAL_PROVIDER_IMPORTED')
    return {'schema':'cas-meta2-prototype-stored-review/7','status':'PROTOTYPE_V7_STORED_REVIEW_PASSED',
        'completed':True,'errors':[],'job':job,'source_sha':source_sha,'source_archive_sha256':source_archive_sha256,
        'launch_manifest_sha256':launch_pin,'packet_sha256':packet_sha256,'source_manifest':manifest,
        'source_files_verified':603,'protected_files_verified':316,'prerequisite_review_sha256':c.PRIOR_REVIEW,
        'runtime_manifest_sha256':c.RUNTIME,'reviewer_files_sha256':own,
        'prior_semantic_helpers_sha256':{k:prior['reviewer_files_sha256'][k] for k in
                                       ('evidence.py','outcomes.py','partial.py','report.py')},
        'inventory':list(packet.inventory.values()),'member_files':len(packet.inventory),
        'extraction':{'path':str(packet.root),'files_verified':len(packet.inventory),
                      'all_member_bytes_verified_after_write':True},
        'process_evidence':meta,'known_fixture_gpu_smoke':smoke,'training_gate':context['training_gate'],
        'dataset':{k:context[k] for k in ('manifest','manifest_sha256','base_manifest_sha256','assembly',
                   'parent_validation','public_loader','configuration','boundary')},
        'sealed_choices':{'seal':context['seal'],'opening':context['opening'],'unchanged':True},
        'native_receipt':native,'outcomes':audited,'diagnostics':diagnostics,'worker_pids':workers,
        'trace_schema_counts':traces,'trace_exports':exports,'protected_schema':schema,
        'sources_and_extraction_rechecked_at_end':True,'checkpoint_tensors_loaded':False,
        'neural_execution_during_audit':False,'provider_calls_during_audit':False,
        'training_performed_during_audit':False,'learning_accepted':False,'automatic_promotion':False,
        'environment':{'python':sys.version,'platform':platform.platform()},
        'finished_utc':datetime.now(timezone.utc).isoformat(),
        'boundary':'Main72 references/360 saved choices independently replayed with unchanged stored verifier; '
          'exact original256 are a training-only append to640, not fresh held-out data. Test72 are24 matched triplets. '
          'Known-fixture smoke is documentary/checkpoint-byte/aggregate checked, not independent neural or native '
          'semantic replay. Unknown failed-tick compute remains incomplete. Literal first divergence is not the '
          'earliest causal neural error. No independent neural arithmetic or general reasoning/CAS advantage claim.'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    for name in ('packet','extracted','source-archive','output'):parser.add_argument('--'+name,type=Path,required=True)
    for name in ('packet-sha256','source-archive-sha256','source-sha','job'):parser.add_argument('--'+name,required=True)
    parser.add_argument('--create-extraction',action='store_true');args=parser.parse_args(argv)
    here=Path(__file__).resolve().parent;c=module('_v7_main_common',here/'common.py');output=args.output.absolute()
    c.require(not output.exists() and output.resolve().is_relative_to(here.resolve())
        and not any(p.is_symlink() or getattr(p,'is_junction',lambda:False)() for p in (output,*output.parents)),
        'V7_NEW_LOCAL_OUTPUT_REQUIRED')
    output.mkdir(parents=True,exist_ok=False)
    try:
        result=run(packet_path=args.packet,packet_sha256=args.packet_sha256,extracted=args.extracted,
            source_archive=args.source_archive,source_archive_sha256=args.source_archive_sha256,
            source_sha=args.source_sha,job=args.job,create_extraction=args.create_extraction)
    except BaseException as error:
        failure={'schema':'cas-meta2-prototype-stored-review/7','completed':False,
            'status':'PROTOTYPE_V7_STORED_REVIEW_FAILED','errors':[{'type':type(error).__name__,
            'message':str(error),'traceback':traceback.format_exc()}],'source_sha':args.source_sha,
            'source_archive_sha256':args.source_archive_sha256,'packet_sha256':args.packet_sha256,
            'job':args.job,'no_partial_success_claim':True}
        with (output/'review_failure.json').open('xb') as stream:stream.write(c.canonical(failure)+b'\n')
        raise
    path=output/'prototype_stored_review.json'
    with path.open('xb') as stream:stream.write(c.canonical(result)+b'\n')
    summary_path=here/'summary.py'
    c.pin(summary_path,result['reviewer_files_sha256']['summary.py'])
    summary=c.load('_v7_human_summary',summary_path).build(result)
    with (output/'SUMMARY.md').open('x',encoding='utf-8') as stream:stream.write(summary)
    print(json.dumps({'status':result['status'],'receipt':str(path),'sha256':c.file_hash(path),
                      'cases':72,'arm_verdicts':360}),flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
