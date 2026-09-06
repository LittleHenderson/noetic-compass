"""Explicit partial native audit of the fixed failed v7 packet."""
from datetime import datetime,timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
JOB='cas-meta2-20260906094002-39762c47'
SOURCE='42f9164754312f12850d9b8789c062fa7fb8069f'
ARCHIVE='f9bed05bd582e0796e2c4e78ff0f5174e5e1b6a3f447e5c3eab56ad002d473f9'
PACKET='f28603b7aab07d7d75a06cfa52fb5b802689b8896001fa9f572971c9140c9799'
EXTRACTION='9bf40771df6dd7f67189d402d6bcfd8e05bd8cd997b71a6825fff21da105ae98'
TRAINING='452705ca332f9cf8b42c8815c3c08f031ec73ba4fc443a51797679acddc62d76'
TIMEOUT='fc444ba90f71cca2d1b539884da56f5ddc32d41b3e841c3dbf4c94867fd17fbe'
PINS={'common.py':'bb13cd57b88beafefd1546f504ee38b8595855430dfc55e5d66ecba8bf4684c7',
      'dataset.py':'171d5e151596b2b86d18b606e8abc1ba08fd0321131b17e2b15d1469b1acf3c5'}

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def progress(stage):
    print(json.dumps({'stage':stage,'utc':datetime.now(timezone.utc).isoformat()}),flush=True)

def run(output):
    output=Path(output).resolve()
    if output.parent!=HERE or output.exists():raise ValueError('NEW_OUTPUT_REQUIRED')
    output.mkdir()
    tick=time.monotonic(); own={p.name:sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.py')}
    reviewer=ROOT/'records/prototype_v7_stored_review_001'
    for name,pin in PINS.items():
        if sha256((reviewer/name).read_bytes()).hexdigest()!=pin:raise ValueError('FROZEN_HELPER_CHANGED')
    c=load('_partial_v7_common',reviewer/'common.py')
    try:
        with c.pure_guard():
            progress('fixed_source_and_external_receipts')
            manifest,prior=c.source_preflight(ROOT/'records/aws_prototype_v7_source_001',ARCHIVE,SOURCE)
            helpers=c.prior_helpers(prior);evidence=helpers['evidence']
            extract_path=ROOT/'records/prototype_v7_partial_review_001/extraction_receipt.json'
            training_path=ROOT/'records/prototype_v7_training_recount_001/receipt_001.json'
            c.pin(extract_path,EXTRACTION);c.pin(training_path,TRAINING)
            extraction=c.decode(extract_path.read_bytes());training=c.decode(training_path.read_bytes())
            c.require(training['status']=='V7_SAVED_TRAINING_RECOUNT_PASSED' and training['completed'] is True
                and training['packet_sha256']==PACKET and training['source_sha']==SOURCE
                and training['source_archive_sha256']==ARCHIVE and training['job']==JOB
                and training['campaign_completed'] is False and training['native_evaluation_completed'] is False,
                'PARTIAL_PINNED_TRAINING_ADMISSION')
            packet=c.Packet(ROOT/'records/aws_prototype_v7_001/cloud_artifacts.zip',PACKET,
                ROOT/'records/prototype_v7_partial_review_001/extracted_001')
            c.require(extraction['inventory']==packet.inventory,'PARTIAL_EXTRACTION_INVENTORY')
            collection_helper=c.load('_partial_collection',ROOT/'tools/inspect_cloud_packet.py')
            collection,index=collection_helper._collection(packet,JOB,SOURCE,ARCHIVE)
            c.require(index is True and collection['returncode']==1 and collection['partial_evidence'] is False
                and collection['omitted_full_file_count']==0 and collection['experiment']==manifest['experiment'],
                'PARTIAL_FAILED_JOB_FULL_COLLECTION')
            initial=packet.json(c.BASE+'initial_identity.json')
            admission_path=ROOT/'records/contrast_failure_review_v6_001/run_002/failure_review_receipt.json'
            c.pin(admission_path,c.ADMISSION)
            evidence.baseline(initial['baseline'],c.decode(admission_path.read_bytes())['baseline'],c)
            c.require({v['wheel_sha256'] for v in initial['baseline']['installed_wheels'].values()}
                =={manifest['files_sha256'][n] for n in manifest['wheel_paths']},'PARTIAL_ACCEPTED_WHEEL_PINS')
            from cas_meta2.contrast_v7 import train,native_evaluation
            from cas_meta2.contrast_v6 import curriculum
            from cas_meta2.codec import canonical_sha256
            ds=c.load('_partial_dataset_binding',reviewer/'dataset.py')
            source=train.source_identity()
            c.require(source==initial['source_sha256']==training['training_gate']['source_sha256'], 'PARTIAL_SOURCE_BINDING')
            gate=packet.json(c.BASE+'training_gate.json')
            c.require(gate==training['training_gate']==packet.json(c.NATIVE+'training_parent_gate.json'), 'PARTIAL_GATE_COPY')
            dataset=packet.json(c.BASE+'dataset/manifest.json')
            c.require(dataset==training['dataset'] and gate['manifest_sha256']==packet.inventory[c.BASE+'dataset/manifest.json']['sha256'],
                'PARTIAL_DATASET_PIN')
            for name in ('test_public.json','test_private.json'):
                packet.same_hash(c.BASE+'dataset/'+name,dataset['sha256'][name])
            tasks=packet.json(c.BASE+'dataset/test_private.json');publics=packet.json(c.BASE+'dataset/test_public.json')
            neural_raw=packet.raw(c.BASE+'training/neural_predictions.jsonl');raw=packet.raw(c.NATIVE+'predictions.jsonl')
            neural=[c.decode(x) for x in neural_raw.splitlines()];predictions=[c.decode(x) for x in raw.splitlines()]
            ds.bind_choices(neural,predictions,tasks,publics,canonical=canonical_sha256,parse=curriculum.parse_problem,c=c)
            seal=packet.json(c.NATIVE+'predictions_seal.json');opening=packet.json(c.NATIVE+'private_opening_receipt.json')
            pin=packet.inventory[c.BASE+'dataset/manifest.json']['sha256']
            c.require(seal=={'schema':'cas-meta2-contrast-evaluation-seal/7','sha256':sha256(raw).hexdigest(),
                'neural_predictions_sha256':gate['predictions_sha256'],'parent_gate_sha256':canonical_sha256(gate),
                'manifest_sha256':pin,'arms':list(c.ARMS),'test_examples':72,'prediction_count':360,
                'rule_input':'public problem and permitted observations only','sealed_utc':seal['sealed_utc']}
                and sha256(neural_raw).hexdigest()==gate['predictions_sha256'],'PARTIAL_SEALED_360_CHOICES')
            c.require(opening=={'opened_utc':opening['opened_utc'],'prediction_sha256':seal['sha256'],
                'training_exit_receipt_sha256':gate['process_receipt_sha256'],
                'private_sha256':dataset['sha256']['test_private.json']}
                and evidence.timestamp(seal['sealed_utc'],c)<evidence.timestamp(opening['opened_utc'],c),
                'PARTIAL_PRIVATE_OPENING_ORDER')
            process=packet.json(c.BASE+'processes/evaluate/process_receipt.json')
            c.require(process==training['processes']['evaluate'] and process['completed'] is False
                and type(process['returncode']) is int and process['returncode']==1 and process['timed_out'] is False
                and process['automatic_retry'] is False and 2700<=process['wall_seconds']<2715,
                'PARTIAL_FIXED_EVALUATION_TIMEOUT_BOUNDARY')
            for stream in ('stdout','stderr'):
                packet.same_hash(c.BASE+'processes/evaluate/'+stream+'.txt',process[stream+'_sha256'])
            stderr=packet.raw(c.BASE+'processes/evaluate/stderr.txt').decode()
            c.require('TimeoutError: 1 (of 72) futures unfinished' in stderr,'PARTIAL_EXACT_TIMEOUT')
            runtime=packet.json('cloud_job/runtime.json');helper_map=native_evaluation.recovery_identity()
            def identity_check(record):
                c.require(set(record)=={'pid','environment','source_sha256','baseline','recovery_helpers_sha256'}
                    and type(record['pid']) is int and record['pid']>0 and record['pid']!=process['pid']
                    and record['source_sha256']==source and record['baseline']==initial['baseline']
                    and record['recovery_helpers_sha256']==helper_map,'PARTIAL_COMPLETED_WORKER_IDENTITY')
                evidence.environment(record['environment'],runtime,c)
            engine=c.load('_partial_v7_stored_engine',ROOT/'tools/audit_stored_packet_v3.py')
            from jsonschema import Draft202012Validator
            from cas_meta2.campaign_v3 import admission_error
            from cas_meta2.curriculum import check_native_topology,graph_signature,parse_problem
            from cas_meta2.stored import verify_stored_composition
            engine.Draft202012Validator=Draft202012Validator;engine.admission_error=admission_error
            engine.check_native_topology=check_native_topology;engine.graph_signature=graph_signature
            engine.parse_problem=parse_problem;engine.verify_stored_composition=verify_stored_composition;engine.safe_name=c.safe_name
            validator,schema=engine.protected_schema()
            context={'tasks':tasks,'predictions':predictions,'runtime_identity':prior['outcomes']['runtime_identity']}
            auditor=c.load('_partial_v7_native',HERE/'native_audit.py')
            audited=auditor.audit(packet,context,engine,validator,helpers,c,identity_check,progress)
            timeout_path=ROOT/'records/prototype_v7_timeout_prefix_001/timeout_prefix_receipt.json'
            c.pin(timeout_path,TIMEOUT);timeout=c.decode(timeout_path.read_bytes())
            c.require(timeout['status']=='TIMEOUT_COMMITTED_PREFIX_VERIFIED'
                and timeout['packet_sha256']==PACKET and timeout['source_sha']==SOURCE and timeout['job']==JOB
                and timeout['extraction_admission_sha256']==EXTRACTION
                and timeout['case_index']==45 and timeout['arm']=='generic_trained'
                and timeout['selected_action']==predictions[45]['actions']['generic_trained']
                and timeout['public_sha256']==c.digest(publics[45])
                and timeout['original_db_wal_shm_unchanged'] is True and timeout['model_or_tensor_loaded'] is False
                and timeout['runtime_root_cause_determined'] is False
                and timeout['source603_and_protected316_rechecked'] is True,'PARTIAL_EXTERNAL_TIMEOUT_PREFIX')
            for name,value in timeout['input_files_sha256'].items():packet.same_hash(name,value)
            prefix=timeout['prefix']
            c.require(prefix['compute_complete'] is False and prefix['full_task_correctness'] is None
                and prefix['complete_execution_trace'] is False and prefix['sealed_program_prefix_checked'] is True
                and prefix['software_model_and_public_input_bound'] is True,'PARTIAL_TIMEOUT_PREFIX_BOUNDARY')
            unfinished=audited['cases'][45]['arms']['generic_trained']
            unfinished.update(rows=prefix['rows'],next_sealed_run=prefix['next_sealed_run'],
                partial_work={'committed_native_runs':prefix['committed_native_runs'],
                    'committed_reserved_policy_units':prefix['committed_reserved_policy_units_lower_bound'],
                    'compute_complete':False,'failed_tick_compute':None,'rows':prefix['rows'],
                    'separate_receipt_sha256':TIMEOUT,'full_task_correctness':None})
            progress('closed_database_schema_and_exports')
            excluded=c.NATIVE+'evaluation/case_0045/generic_trained/native/native.db'
            closed=SimpleNamespace(inventory={k:v for k,v in packet.inventory.items() if k!=excluded},
                path=packet.path,json=packet.json,raw=packet.raw)
            traces=engine.validate_all_traces(closed,validator)
            exports=helpers['outcomes'].exports(packet,validator,c)
            report=c.load('_partial_v7_report',HERE/'report.py').build(tasks,predictions,audited['cases'],helpers,c)
            progress('final_bytes')
            packet.verify_all();c.check_source_again(manifest);c.pin(extract_path,EXTRACTION);c.pin(training_path,TRAINING)
            c.pin(ROOT/'records/aws_prototype_v7_source_001',ARCHIVE);c.prior_helpers(prior)
            c.pin(timeout_path,TIMEOUT)
            c.require(own=={p.name:sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.py')},'PARTIAL_AUDITOR_CHANGED')
            result={'schema':'cas-meta2-prototype-partial-native-audit/7','status':'PARTIAL_NATIVE_EVIDENCE_CHECKED',
                'audit_completed':True,'campaign_completed':False,'native_evaluation_completed':False,
                'job':JOB,'source_sha':SOURCE,'source_archive_sha256':ARCHIVE,'packet_sha256':PACKET,
                'extraction_receipt_sha256':EXTRACTION,'training_recount_receipt_sha256':TRAINING,
                'separate_timeout_prefix_receipt_sha256':TIMEOUT,'separate_timeout_prefix':timeout,
                'auditor_files_sha256':own,'frozen_helpers':PINS,'runtime_manifest_sha256':c.RUNTIME,
                'source_files_verified':603,'protected_files_verified':316,'source_manifest':manifest,
                'seal':seal,'opening':opening,'process':process,'collection':collection,
                'outcomes':audited,'diagnostics':report,'closed_database_trace_schemas':traces,
                'trace_exports':exports,'excluded_timeout_database':excluded,'protected_schema':schema,
                'wall_seconds':time.monotonic()-tick,'finished_utc':datetime.now(timezone.utc).isoformat(),
                'source_and_original_packet_rechecked':True,'provider_calls':False,'neural_execution':False,
                'checkpoint_tensors_loaded':False,'learning_accepted':False,'automatic_retry':False,
                'boundary':'71 complete cases and three saved arms of case45;72 independently checked references. '
                    'Two missing arm outcomes stay unknown with72 assigned cases per arm. '
                    'Timeout WAL work is excluded from this semantic proof and handled separately. '
                    'No full campaign acceptance, replay launch, neural arithmetic, or earliest neural cause claim.'}
            with (output/'partial_native_receipt.json').open('xb') as stream:stream.write(c.canonical(result)+b'\n')
            print(json.dumps({'status':result['status'],'receipt':str(output/'partial_native_receipt.json'),
                'sha256':c.file_hash(output/'partial_native_receipt.json'),'wall_seconds':result['wall_seconds']}),flush=True)
    except BaseException as error:
        failure={'status':'PARTIAL_NATIVE_AUDIT_FAILED','audit_completed':False,'campaign_completed':False,
            'job':JOB,'packet_sha256':PACKET,'error':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()}
        with (output/'failure.json').open('xb') as stream:stream.write(c.canonical(failure)+b'\n')
        raise

if __name__=='__main__':run(sys.argv[1])
