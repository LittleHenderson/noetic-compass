"""Failure-only packet audit. Byte checks and saved-action recount, no neural execution."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
import sys
import traceback
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = 'cloud_job/campaign/'
SOURCE = 'acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0'
SOURCE_HASH = '3153318664641ea3affdbef306929c3113bb937cd04113bce41d02f736e0f1f1'
JOB = 'cas-meta2-20260906064703-c0d74ffa'
SOURCE_ZIP = ROOT/'records/aws_contrast_v6_source_001'
PACKET = ROOT/'records/aws_contrast_v6_001/cloud_artifacts.zip'
EXTRACTION = ROOT/'records/aws_contrast_v6_001_failure_extracted'
PINS = {
    'contrast_stored_audit_v6_001/audit.py': '68b3051902428b71b8c85a3295a52d362f8d321e15f14ff5a2347721157b4435',
    'contrast_packet_review_v6_001/review.py': 'b9d803fd58cd6d06619221100019c6463267f88e47ee7231fde6430f41f85e3a',
}
ARMS = ('cas_untrained', 'cas_trained', 'generic_untrained', 'generic_trained', 'rule')


def require(value, code):
    if not value:
        raise ValueError(code)


def digest(path):
    path = Path(path).absolute()
    require(path.is_file() and not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
            for p in (path, *path.parents)), 'NONREGULAR_INPUT')
    with path.open('rb') as stream:
        return __import__('hashlib').file_digest(stream, 'sha256').hexdigest()


def bound_helper(relative, name):
    path = ROOT/'records'/relative
    require(digest(path) == PINS[relative], 'REVIEW_HELPER_CHANGED:'+relative)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def failure_state(collection, campaign, experiment, full_index):
    require(full_index is True and type(collection.get('returncode')) is int
            and collection['returncode'] != 0 and collection.get('partial_evidence') is False
            and type(collection.get('omitted_full_file_count')) is int
            and collection['omitted_full_file_count'] == 0
            and collection.get('experiment') == experiment, 'FULL_FAILED_COLLECTION_REQUIRED')
    require(campaign.get('schema') == 'cas-meta2-contrast-campaign/6'
            and campaign.get('job') == JOB and campaign.get('experiment') == experiment
            and campaign.get('stage') == 'evaluate' and campaign.get('training_performed') is True
            and all(campaign.get(k) is False for k in
                    ('completed', 'native_evaluation_completed', 'learning_accepted', 'release_accepted', 'automatic_retry'))
            and type(campaign.get('failure')) is dict, 'FAILED_EVALUATION_CAMPAIGN_REQUIRED')


def failed_process(checks, path, command):
    value = checks.read(path)
    require(value.get('schema') == 'cas-meta2-campaign-subprocess/3'
            and value.get('completed') is False and type(value.get('returncode')) is int
            and value['returncode'] != 0 and value.get('timed_out') is False
            and type(value.get('pid')) is int and value['pid'] > 0
            and value.get('new_process_group') is True and value.get('automatic_retry') is False
            and value.get('command') == command and checks.finite(value.get('wall_seconds'), positive=True),
            'FAILED_EVALUATOR_PROCESS_REQUIRED')
    require(checks.timestamp(value['started_utc']) < checks.timestamp(value['finished_utc'])
            <= datetime.now(timezone.utc), 'FAILED_PROCESS_TIME_INVALID')
    for field in ('stdout', 'stderr'):
        require(digest(path.parent/(field+'.txt')) == value[field+'_sha256'], 'FAILED_PROCESS_LOG_CHANGED')
    return value


def bind_rows(neural, predictions, tasks, publics, canonical, parse):
    require(len(neural) == len(predictions) == len(tasks) == len(publics) == 72, 'SEALED_CASE_COVERAGE')
    for index, (n, row, public) in enumerate(zip(neural, predictions, publics, strict=True)):
        require(type(row) is dict and set(row) == {'case_index', 'public_sha256', 'actions'}
                and type(row['case_index']) is int and row['case_index'] == index
                and row['public_sha256'] == canonical(public) and set(row['actions']) == set(ARMS)
                and n == {**row, 'actions': {arm: row['actions'][arm] for arm in ARMS[:-1]}},
                'SEALED_ACTION_MAPPING')
        require(row['actions']['rule'] == parse(public), 'RULE_INPUT_BINDING')


def native_inputs(checks, data, curriculum, output, gate, manifest, tasks, publics, process):
    from cas_meta2.codec import canonical_sha256
    native = output/'native'
    require(checks.read(native/'training_parent_gate.json') == gate, 'NATIVE_PARENT_GATE_CHANGED')
    raw = data.read(native/'predictions.jsonl')
    neural_raw = data.read(output/'training/neural_predictions.jsonl')
    require(data.digest(neural_raw) == gate['predictions_sha256'], 'NEURAL_PREDICTIONS_CHANGED')
    predictions = [data.decode(line) for line in raw.splitlines()]
    neural = [data.decode(line) for line in neural_raw.splitlines()]
    seal = checks.read(native/'predictions_seal.json')
    require(seal == {'schema': 'cas-meta2-contrast-evaluation-seal/6', 'sha256': data.digest(raw),
        'neural_predictions_sha256': gate['predictions_sha256'], 'parent_gate_sha256': canonical_sha256(gate),
        'manifest_sha256': gate['manifest_sha256'], 'arms': list(ARMS), 'test_examples': 72,
        'prediction_count': 360, 'rule_input': 'public problem and permitted observations only',
        'sealed_utc': seal.get('sealed_utc')}, 'NATIVE_PREDICTION_SEAL_CHANGED')
    opening = checks.read(native/'private_opening_receipt.json')
    require(opening == {'opened_utc': opening.get('opened_utc'), 'prediction_sha256': seal['sha256'],
        'training_exit_receipt_sha256': gate['process_receipt_sha256'],
        'private_sha256': manifest['sha256']['test_private.json']}, 'PRIVATE_OPENING_BINDING')
    training = checks.read(output/'processes/training/process_receipt.json')
    require(checks.timestamp(training['finished_utc']) <= checks.timestamp(process['started_utc'])
        <= checks.timestamp(seal['sealed_utc']) < checks.timestamp(opening['opened_utc'])
        <= checks.timestamp(process['finished_utc']), 'PRIVATE_OPENING_ORDER')
    bind_rows(neural, predictions, tasks, publics, canonical_sha256, curriculum.parse_problem)
    return predictions, {
        'dataset_manifest_sha256': gate['manifest_sha256'],
        'test_public_sha256': manifest['sha256']['test_public.json'],
        'test_private_sha256': manifest['sha256']['test_private.json'],
        'neural_predictions_sha256': gate['predictions_sha256'],
        'native_predictions_sha256': seal['sha256'],
        'native_predictions_seal_sha256': digest(native/'predictions_seal.json'),
        'native_training_parent_gate_sha256': digest(native/'training_parent_gate.json'),
        'private_opening_receipt_sha256': digest(native/'private_opening_receipt.json'),
        'cases_bound': 72, 'arm_choices_bound': 360, 'reference_choices_bound': 0,
        'recorded_private_opening_order_checked': True, 'stored_trace_semantics_checked': False,
        'boundary': '72 sealed input rows, not 72 completed native tasks.'}


def partial_cases(files, tasks, predictions):
    prefix = BASE+'native/evaluation/'
    partial = files.json(BASE+'native/evaluation_partial.json')
    require(partial.get('completed') is False and partial.get('automatic_retry') is False
        and partial.get('partial_files_retained') is True and type(partial.get('expected')) is int
        and partial['expected'] == 72 and type(partial.get('cases')) is list, 'PARTIAL_RECORD_REQUIRED')
    require(BASE+'native/native_receipt.json' not in files.inventory
            and BASE+'native/evaluation_results.json' not in files.inventory, 'SUCCESS_RECORD_ON_FAILED_EVALUATION')
    case_names = sorted({name[len(prefix):].split('/')[0] for name in files.inventory if name.startswith(prefix)})
    require(all(re.fullmatch(r'case_\d{4}', name) and 0 <= int(name[-4:]) < 72 for name in case_names),
            'CASE_DIRECTORY_INVALID')
    recorded, arm_counts, failures = [], Counter(), []
    ids = [row.get('case_index') for row in partial['cases']]
    require(all(type(i) is int and 0 <= i < 72 for i in ids) and len(set(ids)) == len(ids),
            'PARTIAL_CASE_IDENTITY')
    for name in case_names:
        index = int(name[-4:])
        folder = prefix+name+'/'
        complete = folder+'case_receipt.json' in files.inventory
        if complete:
            row = files.json(folder+'case_receipt.json')
            require(row.get('case_index') == index and row.get('task_id') == tasks[index]['task_id']
                    and set(row.get('arms', {})) == set(ARMS), 'PARTIAL_CASE_IDENTITY')
            recorded.append(index)
        for arm in ARMS:
            path = folder+arm+'/case_receipt.json'
            if path not in files.inventory:
                continue
            item = files.json(path)
            require(item.get('case_index') == index and item.get('arm') == arm
                    and item.get('action') == predictions[index]['actions'][arm]
                    and item.get('verification') == files.json(folder+arm+'/verification.json'),
                    'PARTIAL_ARM_COPY_CHANGED')
            if complete:
                require(row['arms'][arm] == item, 'PARTIAL_CASE_ARM_COPY_CHANGED')
            arm_counts[arm] += 1
        if folder+'worker_failure.json' in files.inventory:
            value = files.json(folder+'worker_failure.json')
            require(value.get('case_index') == index and value.get('completed') is False, 'WORKER_FAILURE_IDENTITY')
            failures.append({'path': folder+'worker_failure.json',
                             'sha256': files.inventory[folder+'worker_failure.json']['sha256'], 'record': value})
    for row in partial['cases']:
        require(row == files.json(prefix+f"case_{row['case_index']:04d}/case_receipt.json"),
                'PARTIAL_RESULT_COPY_CHANGED')
    require(set(ids).issubset(recorded) and failures, 'FAILED_NATIVE_PARTIAL_MISSING')
    native_failures = [{'path': name, 'sha256': row['sha256'], 'record': files.json(name)}
                      for name, row in files.inventory.items()
                      if name.startswith(prefix) and name.endswith('/native/failure.json')]
    return {'case_directories': [int(n[-4:]) for n in case_names], 'case_directory_count': len(case_names),
        'complete_case_receipt_indices': recorded, 'complete_case_receipt_count': len(recorded),
        'parent_collected_case_indices': ids, 'parent_collected_case_count': len(ids),
        'arm_receipts_present': dict(arm_counts), 'worker_failures': failures, 'native_failures': native_failures,
        'partial_receipt_sha256': files.inventory[BASE+'native/evaluation_partial.json']['sha256'],
        'full_task_metrics': None, 'full_task_denominator': None, 'stored_trace_semantics_checked': False,
        'boundary': 'Incomplete native run. Counts describe preserved files, not a completed task evaluation.'}


def review(expected_hash):
    require(re.fullmatch('[a-f0-9]{64}', expected_hash) and digest(PACKET) == expected_hash, 'EXTERNAL_PACKET_HASH')
    require(digest(SOURCE_ZIP) == SOURCE_HASH, 'EXTERNAL_SOURCE_HASH')
    audit = bound_helper('contrast_stored_audit_v6_001/audit.py', '_failure_source_audit')
    require(not audit.FORBIDDEN.intersection(n.split('.')[0] for n in sys.modules), 'PRELOADED_NEURAL_OR_PROVIDER')
    sys.meta_path.insert(0, audit.Guard())
    sys.path.insert(0, str(ROOT))
    manifest, helper = audit.load_bound_source(SOURCE_ZIP, SOURCE_HASH, SOURCE)
    require(len(manifest['files_sha256']) == 538, 'SOURCE_COUNT_CHANGED')
    byte_review = bound_helper('contrast_packet_review_v6_001/review.py', '_failure_byte_primitives')
    target = helper._new_output(EXTRACTION, extracted=True)
    with zipfile.ZipFile(PACKET) as archive:
        infos, expanded = helper._safe_infos(archive)
        inventory = []
        for name, info in sorted(infos.items()):
            if info.is_dir():
                continue
            state, size = sha256(), 0
            with archive.open(info) as stream:
                for block in iter(lambda: stream.read(1024**2), b''):
                    size += len(block)
                    require(size <= info.file_size, 'MEMBER_SIZE_EXCEEDED')
                    state.update(block)
            require(size == info.file_size, 'MEMBER_SIZE_MISMATCH')
            inventory.append({'path': name, 'bytes': size, 'sha256': state.hexdigest()})
        packet = helper.Packet(archive, infos, inventory)
        collection, full_index = helper._collection(packet, JOB, SOURCE, SOURCE_HASH)
        campaign = packet.json(BASE+'campaign_receipt.json')
        failure_state(collection, campaign, manifest['experiment'], full_index)
        require(packet.json(BASE+'payload_sha256.json') ==
            {row['path'].removeprefix(BASE): row['sha256'] for row in inventory
             if row['path'].startswith(BASE) and row['path'] != BASE+'payload_sha256.json'}, 'FULL_PAYLOAD_INDEX_CHANGED')
        remote = packet.json('cloud_job/job.json')
        require(all(remote.get(k) == collection.get(k) for k in
                    ('job', 'source_sha', 'baseline_sha', 'archive_sha256', 'smoke_only')), 'REMOTE_JOB_IDENTITY')
        gpu = byte_review.check_gpu_gates(packet, manifest, campaign)
        runtime = packet.json('cloud_job/runtime.json')
        require(runtime.get('cuda_matmul_passed') is True and runtime.get('torch') == '2.11.0+cu128'
            and runtime.get('cuda') == '12.8' and 'RTX PRO 4500' in runtime.get('gpu', ''), 'CUDA_ENVIRONMENT')
        extraction_record = helper._extract(packet, target)
    print('All packet bytes safely extracted and verified.', flush=True)
    files = audit.Files(target, inventory, helper)
    from cas_meta2.contrast_v6 import checks, train, data, curriculum
    from cas_meta2.contrast_v6.campaign import configurations
    require(campaign['source_sha256'] == train.source_identity(), 'SOURCE_MAPPING_CHANGED')
    baseline = campaign['baseline_before']
    require(baseline['source'] == {'baseline_sha': manifest['baseline_sha'], 'files_verified': 316},
            'BASELINE_IDENTITY_CHANGED')
    require({v['wheel_sha256'] for v in baseline['installed_wheels'].values()}
            == {manifest['files_sha256'][p] for p in manifest['wheel_paths']}, 'WHEEL_IDENTITIES_CHANGED')
    output = target/'cloud_job/campaign'
    spec = checks.read(ROOT/'EXPERIMENT_CONTRAST_V6.json')
    require(checks.read(output/'experiment.json') == spec, 'EXPERIMENT_CHANGED')
    require(checks.read(output/'initial_identity.json') ==
        {'source_sha256': campaign['source_sha256'], 'baseline': baseline, 'experiment': manifest['experiment']},
        'INITIAL_IDENTITY_CHANGED')
    cfg, training = configurations(spec)
    excluded = train.registered_exclusions(ROOT/'records/contrast_v6_exclusions_001/inventory.json')
    remote_root = '/opt/cas-meta2/package/'+manifest['pilot_dir']
    remote_output = remote_root+'/runs/cloud_job/campaign'
    command_base = ['/opt/cas-meta2/venv/bin/python', '-B', '-m', 'cas_meta2.contrast_v6.campaign',
                    '--output', remote_output, '--job', JOB, '--phase']
    for phase, command in [('gpu_gate', byte_review.gpu_commands(manifest)['contrast_pipeline']),
                           ('dataset', command_base+['dataset'])]:
        value = checks.process_exit(output/'processes'/phase/'process_receipt.json', expected_command=command)
        require(value == campaign['processes'][phase], 'PROCESS_COPY_CHANGED:'+phase)
    pin = checks.file_hash(output/'dataset/manifest.json')
    command = ['/opt/cas-meta2/venv/bin/python', '-B', '-m', 'cas_meta2.contrast_v6.train',
        '--bundle', remote_output+'/trainer_input', '--output', remote_output+'/training',
        '--job', JOB, '--manifest-sha256', pin, '--curriculum-seed', str(spec['curriculum_seed']),
        '--curriculum-config', remote_output+'/curriculum_config.json',
        '--training-config', remote_output+'/training_config.json',
        '--exclusions', remote_root+'/records/contrast_v6_exclusions_001/inventory.json']
    gate = checks.check_training(output/'training', output/'processes/training/process_receipt.json',
        output/'trainer_input', expected_command=command, job=JOB, expected_manifest_sha256=pin,
        curriculum_seed=spec['curriculum_seed'], curriculum_config=cfg, excluded=excluded, config=training,
        expected_source=campaign['source_sha256'], expected_baseline=baseline)
    require(gate == checks.read(output/'training_gate.json'), 'RECORDED_TRAINING_GATE_CHANGED')
    require(campaign['processes']['training'] == checks.read(output/'processes/training/process_receipt.json'),
            'TRAINING_PROCESS_COPY_CHANGED')
    dataset_manifest, tasks, publics = byte_review.check_dataset(output, pin=pin,
        seed=spec['curriculum_seed'], config=cfg, excluded=excluded)
    process = failed_process(checks, output/'processes/evaluate/process_receipt.json', command_base+['evaluate'])
    predictions, bindings = native_inputs(checks, data, curriculum, output, gate, dataset_manifest, tasks, publics, process)
    partial = partial_cases(files, tasks, predictions)
    raw_stderr = files.raw(BASE+'processes/evaluate/stderr.txt').decode('utf-8')
    require(all(row['record']['message'] in raw_stderr for row in partial['worker_failures']), 'FAILURE_STDERR_BINDING')
    receipt = checks.read(output/'training/training_receipt.json')
    registration = checks.read(output/'training/registration.json')
    result = {'schema': 'cas-meta2-contrast-failure-review/6', 'status': 'FAILED_RUN_TRAINING_RECOUNT_PASSED',
        'audit_completed': True, 'campaign_completed': False, 'native_evaluation_completed': False,
        'training_recount_passed': True, 'job': JOB, 'source_sha': SOURCE, 'source_archive_sha256': SOURCE_HASH,
        'packet_sha256': expected_hash, 'packet_bytes': PACKET.stat().st_size, 'source_manifest': manifest,
        'source_files_verified': 538, 'protected_files_verified': 316, 'source_archive_members': 539,
        'extraction': extraction_record, 'inventory': inventory, 'member_files': len(inventory),
        'expanded_bytes': expanded, 'collection': collection, 'collection_full_index_verified': full_index,
        'gpu_tests': gpu, 'runtime': runtime, 'baseline': baseline, 'dataset_manifest': dataset_manifest,
        'training_gate': gate, 'binding_checks': bindings, 'partial_native': partial,
        'failed_campaign_receipt_sha256': files.inventory[BASE+'campaign_receipt.json']['sha256'],
        'campaign_failure': campaign['failure'], 'failed_evaluation_process': process,
        'evaluation_stderr': {'path': BASE+'processes/evaluate/stderr.txt',
            'sha256': process['stderr_sha256'], 'raw_text': raw_stderr},
        'training': {'completed_epochs': receipt['completed_epochs'], 'optimizer_steps': receipt['optimizer_steps'],
            'checkpoints': receipt['checkpoints'], 'validation_action_curves': receipt['history'],
            'selection_rule': registration['selection_rule'], 'parameter_matching': registration['parameter_matching'],
            'environment': registration['environment'], 'registered_data': registration['data'],
            'recorded_training_step_seconds': receipt['training_step_seconds'],
            'recorded_prediction_seconds': receipt['prediction_seconds'], 'recorded_wall_seconds': receipt['wall_seconds'],
            'boundary': 'Recounted recorded actions and checkpoint bytes. No neural rerun or full native task result.'},
        'helper_sha256': PINS, 'script_sha256': digest(__file__), 'utc': datetime.now(timezone.utc).isoformat(),
        'neural_execution': False, 'provider_calls': False, 'learning_accepted': False, 'release_accepted': False,
        'estimated_cost_usd': None, 'invoice_cost_usd': None, 'budget_reservation_usd': None,
        'boundary': 'The original run failed. This preserves complete collection, completed training and sealed inputs. '
                    'It does not complete native evaluation, retry, audit stored-trace semantics or accept learning.'}
    require(digest(PACKET) == expected_hash and digest(SOURCE_ZIP) == SOURCE_HASH, 'ARCHIVES_CHANGED')
    audit.check_source(manifest)
    for name, pin in PINS.items():
        require(digest(ROOT/'records'/name) == pin, 'HELPER_CHANGED')
    files.verify_all()
    require(not audit.FORBIDDEN.intersection(n.split('.')[0] for n in sys.modules), 'FORBIDDEN_IMPORT_OCCURRED')
    result['source_and_extraction_rechecked_at_end'] = True
    return result


def markdown(result):
    tr, partial = result['training'], result['partial_native']
    lines = ['# Contrast v6: failed run, completed training checked', '',
        'The original run failed during native evaluation. This is not a completed learning result.', '',
        f"Source: {result['source_sha']}", f"Packet SHA-256: {result['packet_sha256']}", '',
        f"Training: {tr['completed_epochs']} epochs; {tr['optimizer_steps']} optimizer steps.",
        'Dataset: 640 training tasks, 96 validation tasks, 72 held-out task variants in 24 matched triplets.',
        'The original 256-task prototype is excluded from this v6 dataset.', '',
        'Validation action match (not native task correctness):', '',
        '| Family | Initial | Selected | Epoch | Depth 1 | Depth 2 | Depth 3 |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for family in ('cas', 'generic'):
        initial = tr['checkpoints'][family]['initial']['validation']['generation']['overall']
        selected = tr['checkpoints'][family]['selected']
        score = selected['validation']['generation']
        depths = [f"{score['by_depth'][str(d)]['joint_correct']}/{score['by_depth'][str(d)]['total']}" for d in (1,2,3)]
        lines.append(f"| {family} | {initial['joint_correct']}/{initial['total']} | "
                     f"{score['overall']['joint_correct']}/{score['overall']['total']} | {selected['epoch']} | "
                     +' | '.join(depths)+' |')
    lines += ['', f"Preserved native evidence: {partial['case_directory_count']} case directories; "
        f"{partial['complete_case_receipt_count']} complete case receipts, indices "
        f"{partial['complete_case_receipt_indices']}. No 72-task success rate is reported.", '',
        'Failure: RuntimeContractError: repair cannot open without a durable distinct ^6 round trip; '
        'case 9, CAS trained arm.', '',
        'All 72 sealed prediction rows were checked. No predictions were regenerated; no checkpoint was loaded.',
        'All source files and all extracted packet files were checked again at the end.',
        'Recorded GPU: '+tr['environment']['cuda_device_name']+'. Costs and cleanup are separate provider records.',
        'Earlier familiar 24/24 and earlier held-out CAS 0/72 results remain separate and unchanged.',
        'No accepted baseline, executor, verifier, weights or completed-success review gate was changed.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.absolute()
    require(output.parent == HERE and not output.exists() and re.fullmatch(r'run_\d{3}', output.name),
            'NEW_OWNED_RUN_DIRECTORY_REQUIRED')
    output.mkdir()
    try:
        result = review(args.sha256)
        (output/'failure_review_receipt.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n', encoding='utf-8')
        (output/'REPORT.md').write_text(markdown(result), encoding='utf-8')
        print(json.dumps({k: result[k] for k in ('status','source_files_verified','member_files','binding_checks','partial_native')}, indent=2))
        return 0
    except Exception as error:
        (output/'review_failure.json').write_text(json.dumps({'completed': False, 'learning_accepted': False,
            'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}, indent=2)+'\n', encoding='utf-8')
        raise


if __name__ == '__main__':
    raise SystemExit(main())
