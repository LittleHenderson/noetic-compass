"""Recount saved training only. A failed evaluation remains failed."""
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
JOB = 'cas-meta2-20260906094002-39762c47'
SOURCE = '42f9164754312f12850d9b8789c062fa7fb8069f'
ARCHIVE = 'f9bed05bd582e0796e2c4e78ff0f5174e5e1b6a3f447e5c3eab56ad002d473f9'
PACKET = 'f28603b7aab07d7d75a06cfa52fb5b802689b8896001fa9f572971c9140c9799'
PINS = {'common.py':'bb13cd57b88beafefd1546f504ee38b8595855430dfc55e5d66ecba8bf4684c7',
        'dataset.py':'171d5e151596b2b86d18b606e8abc1ba08fd0321131b17e2b15d1469b1acf3c5'}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(output):
    output = Path(output).absolute()
    assert output.parent == HERE and not output.exists()
    started = datetime.now(timezone.utc).isoformat()
    tick = time.monotonic()
    reviewer = ROOT/'records/prototype_v7_stored_review_001'
    for name, pin in PINS.items():
        assert sha256((reviewer/name).read_bytes()).hexdigest() == pin
    c = load('_v7_training_recount_common', reviewer/'common.py')
    with c.pure_guard():
        manifest, prior = c.source_preflight(ROOT/'records/aws_prototype_v7_source_001', ARCHIVE, SOURCE)
        packet = c.Packet(ROOT/'records/aws_prototype_v7_001/cloud_artifacts.zip', PACKET,
            ROOT/'records/prototype_v7_partial_review_001/extracted_001')
        collection = packet.json('artifact_collection_receipt.json')
        c.require(collection['job'] == JOB and collection['source_sha'] == SOURCE
            and collection['archive_sha256'] == ARCHIVE and collection['returncode'] == 1
            and collection['partial_evidence'] is False and collection['omitted_full_file_count'] == 0,
            'EXACT_FAILED_RUN_WITH_COMPLETE_COLLECTION_REQUIRED')
        from cas_meta2.contrast_v7 import campaign, checks, data, parent, train
        from cas_meta2.codec import canonical_sha256
        from cas_meta2.contrast_v6 import curriculum
        ds = c.load('_v7_training_recount_dataset_helpers', reviewer/'dataset.py')
        spec = campaign.registered_spec()
        cfg, training = campaign.configurations(spec)
        excluded = train.registered_exclusions(ROOT/spec['exclusion_inventory_path'],
            expected_sha256=spec['exclusion_inventory_sha256'])
        c.require(len(excluded) == spec['exclusion_count'] == 8837, 'FULL_EXCLUSIONS_REQUIRED')
        source = train.source_identity()
        initial = packet.json(c.BASE+'initial_identity.json')
        helpers = c.prior_helpers(prior)
        admission_path = ROOT/'records/contrast_failure_review_v6_001/run_002/failure_review_receipt.json'
        c.pin(admission_path, c.ADMISSION)
        admission = c.decode(admission_path.read_bytes())
        helpers['evidence'].baseline(initial['baseline'], admission['baseline'], c)
        c.require({v['wheel_sha256'] for v in initial['baseline']['installed_wheels'].values()}
            == {manifest['files_sha256'][n] for n in manifest['wheel_paths']}, 'BASELINE_WHEEL_PINS')
        campaign_record = packet.json(c.BASE+'campaign_receipt.json')
        c.require(initial['source_sha256'] == source
            and initial['campaign_source_sha256'] == campaign.source_identity()
            and campaign_record['source_sha256'] == source
            and campaign_record['completed'] is False, 'SOURCE_AND_FAILED_CAMPAIGN_REQUIRED')
        bound = packet.json(c.BASE+'dataset/manifest.json')
        pin = packet.inventory[c.BASE+'dataset/manifest.json']['sha256']
        base = packet.root/c.BASE
        parent_report = parent.validate_bundle(base/'dataset', expected_sha256=pin,
            seed=spec['curriculum_seed'], config=cfg, excluded=excluded,
            pins=ROOT/spec['source_pins_path'], expected_pins_sha256=spec['source_pins_sha256'],
            expected_loader_sha256=spec['public_loader_sha256'])
        loaded = data.load_training_bundle(base/'trainer_input', expected_sha256=pin,
            seed=spec['curriculum_seed'], config=cfg, excluded=excluded,
            expected_loader_sha256=spec['public_loader_sha256'])
        c.require(parent_report['completed'] is True and loaded['manifest'] == bound,
            'DATASET_AND_PUBLIC_EXPORT_REQUIRED')
        expected_public = set(loaded['receipt']['loaded_sha256']) | {'manifest.json'}
        actual_public = {n.removeprefix(c.BASE+'trainer_input/') for n in packet.inventory
                         if n.startswith(c.BASE+'trainer_input/')}
        c.require(actual_public == expected_public and 'test_private.json' not in actual_public,
            'NO_PRIVATE_TRAINER_FILE')
        for name in expected_public:
            c.require(packet.raw(c.BASE+'trainer_input/'+name) == packet.raw(c.BASE+'dataset/'+name),
                'PUBLIC_EXPORT_BYTES_CHANGED')
        for name in ('validation.json','test_public.json','test_private.json'):
            c.require(packet.raw(c.BASE+'base_dataset/'+name) == packet.raw(c.BASE+'dataset/'+name),
                'APPEND_CHANGED_HELDOUT')
        commands = ds.commands(c.BASE, JOB, spec, pin, c)
        gate = checks.check_training(base/'training', base/'processes/training/process_receipt.json',
            base/'trainer_input', expected_command=commands['training'], job=JOB,
            expected_manifest_sha256=pin, expected_loader_sha256=spec['public_loader_sha256'],
            curriculum_seed=spec['curriculum_seed'], curriculum_config=cfg, excluded=excluded,
            config=training, expected_source=source, expected_baseline=initial['baseline'])
        c.require(gate == packet.json(c.BASE+'training_gate.json')
            == packet.json(c.NATIVE+'training_parent_gate.json'), 'ORIGINAL_TRAINING_GATES_CHANGED')
        processes = {n:packet.json(c.BASE+'processes/'+n+'/process_receipt.json')
                     for n in ('dataset','training','evaluate')}
        c.require(processes['dataset']['completed'] is True and processes['dataset']['returncode'] == 0
            and processes['evaluate']['completed'] is False and processes['evaluate']['returncode'] == 1
            and checks.timestamp(processes['dataset']['finished_utc'])
                <= checks.timestamp(processes['training']['started_utc'])
            and checks.timestamp(processes['training']['finished_utc'])
                <= checks.timestamp(processes['evaluate']['started_utc']), 'PROCESS_ORDER_OR_STATUS')
        for name, process in processes.items():
            c.require(process['command'] == commands[name], 'EXACT_PHASE_COMMAND')
            for stream in ('stdout','stderr'):
                packet.same_hash(c.BASE+'processes/'+name+'/'+stream+'.txt', process[stream+'_sha256'])
        neural = [c.decode(line) for line in packet.raw(c.BASE+'training/neural_predictions.jsonl').splitlines()]
        rows = [c.decode(line) for line in packet.raw(c.NATIVE+'predictions.jsonl').splitlines()]
        tasks = packet.json(c.BASE+'dataset/test_private.json')
        publics = packet.json(c.BASE+'dataset/test_public.json')
        ds.bind_choices(neural, rows, tasks, publics, canonical=canonical_sha256,
            parse=curriculum.parse_problem, c=c)
        seal = packet.json(c.NATIVE+'predictions_seal.json')
        opening = packet.json(c.NATIVE+'private_opening_receipt.json')
        c.require(seal == {'schema':'cas-meta2-contrast-evaluation-seal/7',
            'sha256':sha256(packet.raw(c.NATIVE+'predictions.jsonl')).hexdigest(),
            'neural_predictions_sha256':gate['predictions_sha256'],
            'parent_gate_sha256':canonical_sha256(gate), 'manifest_sha256':pin,
            'arms':list(c.ARMS), 'test_examples':72, 'prediction_count':360,
            'rule_input':'public problem and permitted observations only',
            'sealed_utc':seal['sealed_utc']}, 'EXACT_NATIVE_SEAL_REQUIRED')
        c.require(opening == {'opened_utc':opening['opened_utc'],
            'prediction_sha256':seal['sha256'],
            'training_exit_receipt_sha256':gate['process_receipt_sha256'],
            'private_sha256':bound['sha256']['test_private.json']}
            and checks.timestamp(processes['evaluate']['started_utc'])
                <= checks.timestamp(seal['sealed_utc']) < checks.timestamp(opening['opened_utc'])
                <= checks.timestamp(processes['evaluate']['finished_utc']),
            'SEALED_BEFORE_PRIVATE_OPENING_REQUIRED')
        receipt = packet.json(c.BASE+'training/training_receipt.json')
        registration = packet.json(c.BASE+'training/registration.json')
        curves = []
        for row in receipt['history']:
            epoch = row['epoch']
            for family in ('cas','generic'):
                measured = packet.json(c.BASE+f'training/{family}_development_epoch_{epoch:04d}.json')
                curves.append({'epoch':epoch,'family':family,
                    'validation':measured['validation']['generation'],
                    'training_probe':measured['probe_metrics'],
                    'selected':row['families'][family]['selected']})
        c.check_source_again(manifest)
        packet.verify_all()
        for name, expected in PINS.items():
            c.pin(reviewer/name, expected)
        result = {'status':'V7_SAVED_TRAINING_RECOUNT_PASSED', 'completed':True,
            'job':JOB, 'source_sha':SOURCE, 'source_archive_sha256':ARCHIVE, 'packet_sha256':PACKET,
            'reviewer_sha256':sha256(Path(__file__).read_bytes()).hexdigest(), 'helper_sha256':PINS,
            'started_utc':started, 'finished_utc':datetime.now(timezone.utc).isoformat(),
            'wall_seconds':time.monotonic()-tick, 'dataset':bound, 'parent_validation':parent_report,
            'public_loader':loaded['receipt'], 'training_gate':gate, 'processes':processes,
            'parameter_matching':registration['parameter_matching'], 'environment':registration['environment'],
            'training_step_seconds':receipt['training_step_seconds'],
            'prediction_seconds':receipt['prediction_seconds'], 'training_wall_seconds':receipt['wall_seconds'],
            'completed_epochs':receipt['completed_epochs'], 'optimizer_steps':receipt['optimizer_steps'],
            'curves':curves, 'source_files_checked':603, 'protected_files_checked':316,
            'sealed_comparison_choices':360, 'campaign_completed':False,
            'native_evaluation_completed':False, 'learning_accepted':False, 'provider_calls':False,
            'neural_execution':False, 'boundary':'Saved actions and validation selection independently recounted; '
                'checkpoint bytes checked but no tensors loaded. No complete-task score or independent neural arithmetic claim.'}
    with output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(result,stream,indent=2,sort_keys=True,allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status':result['status'],'receipt':str(output),
        'sha256':sha256(output.read_bytes()).hexdigest(),'wall_seconds':result['wall_seconds']}),flush=True)


if __name__ == '__main__':
    run(sys.argv[1])
