"""Offline recorded-result review. Never loads tensors or calls a provider."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import importlib.abc
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = 'acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0'
SOURCE_HASH = '3153318664641ea3affdbef306929c3113bb937cd04113bce41d02f736e0f1f1'
JOB = 'cas-meta2-20260906064703-c0d74ffa'
SOURCE_ZIP = ROOT/'records/aws_contrast_v6_source_001'
PACKET = ROOT/'records/aws_contrast_v6_001/cloud_artifacts.zip'
BASE = 'cloud_job/campaign/'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        require(fullname.split('.')[0] not in {
            'torch', 'casformer', 'cas_cjt', 'tensorflow', 'jax', 'cupy', 'boto3', 'botocore'
        }, 'LOCAL_NEURAL_OR_PROVIDER_IMPORT_REFUSED')


def digest(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
                    for p in (path, *path.parents)), 'LINK_REFUSED')
    result = sha256()
    with path.open('rb') as stream:
        for raw in iter(lambda: stream.read(1024**2), b''):
            result.update(raw)
    return result.hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def gpu_cases():
    """Exact identities from the frozen native/policy/contrast test sources."""
    native = [('tests.test_execution_contract', name) for name in [
        *('test_gpu_authored_execution_matches_independent_reference['+str(i)+']' for i in range(3)),
        'test_gpu_wrong_binding_and_wrong_procedure_are_wrong_despite_valid_traces']]
    policy = [('tests.test_policy_gpu', name) for name in [
        'test_cuda_guard_precedes_model_construction',
        'test_both_generators_have_gradients_and_matched_active_parameters',
        'test_decoder_cannot_see_future_target_tokens',
        'test_incomplete_generation_is_rejected_without_gold_repair']]
    policy += [('tests.test_policy_v3_gpu', name) for name in [
        'test_cuda_guard_precedes_candidate_construction',
        'test_identical_shared_initialization_and_finite_nonzero_task_gradients',
        'test_mean_pooling_covers_all_byte_fallback_rows',
        'test_repeated_spelling_copy_mass_is_aggregated_in_fixed_vocabulary',
        'test_no_symbols_uses_exact_fixed_head_and_keeps_binding_pointer_active',
        'test_causal_copy_scores_cannot_see_future_decoder_tokens',
        'test_occurrence_scope_refuses_observation_and_invalid_destination_ids',
        'test_same_grammar_blocks_disallowed_high_logits_and_never_repairs_bounded_dead_end',
        'test_mixed_symbol_and_no_symbol_rows_remain_finite_with_correct_mass',
        'test_rejected_row_evidence_excludes_inactive_batch_padding']]
    loss = ['test_weighted_nll_matches_independent_sum_and_pad_gradients_are_zero',
            'test_weight_encoding_rejects_misaligned_target_or_decoder_inputs']
    loss += ['test_invalid_weights_are_refused['+name+']' for name in
             ('negative', 'nan', 'zero_valid', 'positive_pad', 'learnable', 'cpu')]
    loss += ['test_bad_log_probabilities_and_target_layout_are_refused['+name+']' for name in
             ('raw_logits', 'nan', 'wrong_vocabulary', 'bad_valid', 'bad_lengths')]
    policy += [('tests.test_loss_v3_gpu', name) for name in loss]
    return {'native': native, 'policy': policy, 'contrast_pipeline': [
        ('tests.test_contrast_v6_train_gpu', 'test_full_matched_cuda_training_exit_and_native_evaluation')]}


def exact_gpu_xml(raw, expected):
    require(b'<!DOCTYPE' not in raw.upper() and b'<!ENTITY' not in raw.upper(), 'GPU_XML_DECLARATION_REFUSED')
    tree = ET.fromstring(raw)
    suites, cases = list(tree.iter('testsuite')), list(tree.iter('testcase'))
    require(tree.tag in ('testsuites', 'testsuite') and suites
            and all(len(list(suite.iter('testsuite'))) == 1 for suite in suites), 'GPU_XML_SUITE_STRUCTURE')
    require(all(int(suite.get(field, '-1')) >= 0 for suite in suites
                for field in ('tests', 'failures', 'errors', 'skipped')), 'GPU_XML_NEGATIVE_OR_MISSING_TOTAL')
    totals = {field: sum(int(suite.get(field, '-1')) for suite in suites)
              for field in ('tests', 'failures', 'errors', 'skipped')}
    require(totals == {'tests': len(expected), 'failures': 0, 'errors': 0, 'skipped': 0}
            and all(int(suite.get('tests', '-1')) == len(list(suite.iter('testcase'))) for suite in suites),
            'GPU_XML_TOTALS_MISMATCH')
    actual = [(row.get('classname'), row.get('name')) for row in cases]
    require(len(actual) == len(expected) and len(set(actual)) == len(actual)
            and set(actual) == set(expected), 'GPU_XML_CASE_IDENTITIES_MISMATCH')
    require(not any(list(tree.iter(tag)) for tag in ('failure', 'error', 'skipped')), 'GPU_XML_NONPASS_CASE')
    return {'passed': len(cases), 'cases': [{'classname': cls, 'name': name} for cls, name in actual]}


def gpu_commands(manifest):
    py = '/opt/cas-meta2/venv/bin/python'
    out = '/opt/cas-meta2/package/'+manifest['pilot_dir']+'/runs/cloud_job'
    return {'native': [py, '-m', 'pytest', '-m', 'gpu', 'tests/test_execution_contract.py', '-q',
                       '--junitxml', out+'/gpu_contract_tests.xml', '-p', 'no:cacheprovider'],
            'policy': [py, '-m', 'pytest', '-m', 'gpu', 'tests/test_policy_gpu.py', 'tests/test_policy_v3_gpu.py',
                       'tests/test_loss_v3_gpu.py', '-q', '--junitxml', out+'/gpu_policy_tests.xml', '-p', 'no:cacheprovider'],
            'contrast_pipeline': [py, '-B', '-m', 'pytest', '-q', '-m', 'gpu', '-p', 'cas_meta2.pytest_no_aliases_v4',
                '-p', 'no:cacheprovider', 'tests/test_contrast_v6_train_gpu.py', '--basetemp', out+'/campaign/gpu_tmp',
                '--junitxml', out+'/campaign/gpu_test.xml']}


def check_gpu_gates(packet, manifest, campaign):
    expected, commands, result = gpu_cases(), gpu_commands(manifest), {}
    for name, label in (('native', 'contract'), ('policy', 'policy')):
        prefix = 'cloud_job/gpu_'+label
        result[name] = exact_gpu_xml(packet.raw(prefix+'_tests.xml', 2*1024**2), expected[name])
        require(packet.json(prefix+'_command.json') == commands[name], 'GPU_COMMAND_MISMATCH:'+name)
        receipt = packet.json(prefix+'_receipt.json')
        require(all(type(receipt.get(field)) is int for field in ('passed', 'tests', 'failures', 'errors', 'skipped'))
            and receipt == {
            'passed': len(expected[name]), 'tests': len(expected[name]), 'failures': 0, 'errors': 0, 'skipped': 0},
            'GPU_RECEIPT_MISMATCH:'+name)
        require(prefix+'_tests.log' in packet.inventory, 'GPU_LOG_MISSING:'+name)
    path = BASE+'gpu_test.xml'
    result['contrast_pipeline'] = exact_gpu_xml(packet.raw(path, 2*1024**2), expected['contrast_pipeline'])
    gate = campaign['gpu_gate']
    require(all(type(gate.get(field)) is int for field in ('tests', 'passed', 'failed', 'errors', 'skipped'))
        and gate == {'path': commands['contrast_pipeline'][-1], 'sha256': packet.inventory[path]['sha256'],
        'tests': 1, 'passed': 1, 'failed': 0, 'errors': 0, 'skipped': 0,
        'cases': [{**row, 'failed': False, 'error': False, 'skipped': False}
                  for row in result['contrast_pipeline']['cases']]}, 'CONTRAST_GPU_RECEIPT_MISMATCH')
    process = packet.json(BASE+'processes/gpu_gate/process_receipt.json')
    require(process == campaign['processes']['gpu_gate']
            and process['command'] == commands['contrast_pipeline'], 'CONTRAST_GPU_PROCESS_COPY_MISMATCH')
    return result


def check_dataset(output, *, pin, seed, config, excluded):
    """Recheck saved construction, never generate new tasks or read a model."""
    from cas_meta2.contrast_v6 import curriculum as c, data as d, checks
    root = d.directory(Path(output)/'dataset', (*d.ALL_FILES, 'manifest.json'))
    manifest = d.checked_manifest(d.read(root/'manifest.json'), expected_sha256=pin,
        seed=seed, config=config, excluded=excluded)
    values = {}
    for name in d.ALL_FILES:
        raw = d.read(root/name)
        require(d.digest(raw) == manifest['sha256'][name], 'REVIEW_DATASET_BYTES_MISMATCH:'+name)
        values[name] = d.decode(raw)
    splits = {split: values[name] for split, name in
              (('train', 'train.json'), ('validation', 'validation.json'), ('test', 'test_private.json'))}
    report = c.validate({'schema': c.SCHEMA, 'seed': seed, 'config': asdict(config),
                         'dataset_id': manifest['dataset_id'], 'splits': splits}, excluded=excluded)
    require(report == {k: v for k, v in manifest.items() if k not in ('seed', 'config', 'sha256')},
            'REVIEW_COLD_DATASET_MISMATCH')
    require(values['test_public.json'] == [c.permitted_view(task) for task in splits['test']],
            'REVIEW_PUBLIC_PRIVATE_MAPPING_MISMATCH')
    require(checks.read(Path(output)/'native/cold_dataset_validation.json') == report, 'RECORDED_COLD_DATASET_MISMATCH')
    return manifest, splits['test'], values['test_public.json']


def check_native_bindings(output, *, gate, manifest, tasks, publics, remote_output, job):
    """Bind saved actions to native records; no SQLite semantics or tensor replay."""
    from cas_meta2.contrast_v6 import curriculum as c, data as d, checks
    from cas_meta2.codec import canonical_sha256
    output = Path(output)
    arms = ('cas_untrained', 'cas_trained', 'generic_untrained', 'generic_trained', 'rule')
    fields = ('task_correct', 'procedure_correct', 'binding_correct', 'dependency_correct',
              'actual_output_correct', 'trace_valid')
    process = checks.process_exit(output/'processes/evaluate/process_receipt.json', expected_command=[
        '/opt/cas-meta2/venv/bin/python', '-B', '-m', 'cas_meta2.contrast_v6.campaign',
        '--output', remote_output, '--job', job, '--phase', 'evaluate'])
    training_exit = checks.read(output/'processes/training/process_receipt.json')
    require(checks.timestamp(training_exit['finished_utc']) <= checks.timestamp(process['started_utc']),
            'EVALUATION_BEFORE_TRAINING_EXIT')
    native = output/'native'
    require(checks.read(native/'training_parent_gate.json') == gate, 'NATIVE_PARENT_GATE_MISMATCH')
    raw = d.read(native/'predictions.jsonl')
    neural_raw = d.read(output/'training/neural_predictions.jsonl')
    require(d.digest(neural_raw) == gate['predictions_sha256'], 'BOUND_NEURAL_PREDICTIONS_CHANGED')
    neural = [d.decode(line) for line in neural_raw.splitlines()]
    predictions = [d.decode(line) for line in raw.splitlines()]
    require(len(predictions) == len(neural) == len(tasks) == len(publics), 'NATIVE_PREDICTION_COVERAGE')
    seal = checks.read(native/'predictions_seal.json')
    expected = {'schema': 'cas-meta2-contrast-evaluation-seal/6', 'sha256': d.digest(raw),
        'neural_predictions_sha256': gate['predictions_sha256'], 'parent_gate_sha256': canonical_sha256(gate),
        'manifest_sha256': gate['manifest_sha256'], 'arms': list(arms), 'test_examples': len(tasks),
        'prediction_count': 5*len(tasks), 'rule_input': 'public problem and permitted observations only',
        'sealed_utc': seal.get('sealed_utc')}
    require(seal == expected and checks.read(native/'native_receipt.json')['seal'] == seal, 'NATIVE_SEAL_BINDING_MISMATCH')
    opening = checks.read(native/'private_opening_receipt.json')
    require(opening == {'opened_utc': opening.get('opened_utc'), 'prediction_sha256': seal['sha256'],
        'training_exit_receipt_sha256': gate['process_receipt_sha256'],
        'private_sha256': manifest['sha256']['test_private.json']}, 'PRIVATE_OPENING_BINDING_MISMATCH')
    require(checks.timestamp(process['started_utc']) <= checks.timestamp(seal['sealed_utc'])
            < checks.timestamp(opening['opened_utc']) <= checks.timestamp(process['finished_utc']),
            'PRIVATE_OPENING_ORDER_MISMATCH')
    cases = checks.read(native/'evaluation_results.json')['cases']
    require(len(cases) == len(tasks), 'NATIVE_CASE_COVERAGE')
    for index, (task, public, row, model, case) in enumerate(zip(tasks, publics, predictions, neural, cases, strict=True)):
        require(type(row) is dict and set(row) == {'case_index', 'public_sha256', 'actions'}
                and type(row['case_index']) is int and row['case_index'] == index
                and row['public_sha256'] == canonical_sha256(public)
                and set(row['actions']) == set(arms) and model == {
                    **row, 'actions': {arm: row['actions'][arm] for arm in arms[:-1]}}, 'NATIVE_NEURAL_ACTION_MAPPING')
        require(row['actions']['rule'] == c.parse_problem(public), 'RULE_NOT_FROM_PUBLIC_INPUT')
        folder = native/'evaluation'/f'case_{index:04d}'
        require(type(case['case_index']) is int and case['case_index'] == index
                and case['task_id'] == task['task_id'] and set(case['arms']) == set(arms)
                and case == checks.read(folder/'case_receipt.json'), 'NATIVE_CASE_COPY_MISMATCH')
        reference = checks.read(folder/'reference_result.json')
        reference_verdict = checks.read(folder/'reference_verdict.json')
        require(reference.get('status') == 'EXECUTED' and reference.get('reference') is True
                and reference['selected_action'] == task['target'] and reference['public_digest'] == canonical_sha256(public)
                and reference_verdict == case['reference_verification']
                and all(reference_verdict.get(field) is True for field in fields), 'NATIVE_REFERENCE_BINDING_MISMATCH')
        for arm in arms:
            item, arm_dir = case['arms'][arm], folder/arm
            require(item == checks.read(arm_dir/'case_receipt.json')
                    and type(item['case_index']) is int and item['case_index'] == index and item['arm'] == arm
                    and item['action'] == row['actions'][arm], 'NATIVE_ARM_ACTION_COPY_MISMATCH')
            verdict, execution = checks.read(arm_dir/'verification.json'), checks.read(arm_dir/'execution_result.json')
            require(verdict == item['verification'] and all(type(verdict.get(field)) is bool for field in fields)
                    and verdict.get('repair_required') is False and verdict.get('repair_success') is None
                    and verdict['task_correct'] == all(verdict[field] for field in fields[1:]), 'NATIVE_VERDICT_COPY_OR_TYPES')
            require(type(item['model_rejection']) is bool and execution['status'] == item['execution_status'], 'NATIVE_EXECUTION_STATUS')
            if item['model_rejection']:
                require(execution['status'] == 'REJECTED' and execution['action'] == item['action']
                        and not any(verdict[field] for field in fields), 'REJECTED_ACTION_ATTRIBUTION')
            else:
                require(execution['status'] == 'EXECUTED' and execution.get('reference') is False
                        and execution['selected_action'] == item['action']
                        and execution['public_digest'] == canonical_sha256(public), 'EXECUTED_ACTION_ATTRIBUTION')
    return {'dataset_manifest_sha256': gate['manifest_sha256'], 'neural_predictions_sha256': gate['predictions_sha256'],
            'native_predictions_sha256': seal['sha256'], 'cases_bound': len(tasks), 'arm_choices_bound': 5*len(tasks),
            'reference_choices_bound': len(tasks), 'recorded_private_opening_order_checked': True,
            'stored_trace_semantics_checked': False}


def review(expected_hash):
    require(len(expected_hash) == 64 and all(c in '0123456789abcdef' for c in expected_hash),
            'EXACT_PACKET_HASH_REQUIRED')
    require(digest(PACKET) == expected_hash and digest(SOURCE_ZIP) == SOURCE_HASH,
            'EXTERNAL_ARCHIVE_HASH_MISMATCH')
    repo = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=ROOT, text=True).strip())
    for relative in ('aws/launch_contrast_v6.py', 'aws/budget.py',
                     'tools/experiment_profiles_contrast_v6.py',
                     'tools/build_launch_bundle_contrast_v6.py',
                     'aws/launch_plan.json', 'requirements-gpu.txt'):
        path = ROOT/relative
        raw = subprocess.check_output(['git', 'cat-file', 'blob',
            SOURCE+':'+path.relative_to(repo).as_posix()], cwd=repo)
        require(digest(path) == sha256(raw).hexdigest(), 'PREIMPORT_SOURCE_MISMATCH:'+relative)
    launch = load('contrast_review_launch', ROOT/'aws/launch_contrast_v6.py')
    manifest = launch.validate_archive(SOURCE_ZIP, SOURCE_HASH, SOURCE,
                                      json.loads(launch.PLAN_FILE.read_bytes()))
    launch.verify_launcher_identity(manifest)
    # Check every helper and input against the frozen package before importing it.
    for relative, checksum in manifest['files_sha256'].items():
        require(digest(ROOT.parent.parent/relative) == checksum, 'LOCAL_SOURCE_MISMATCH:'+relative)
    helper = load('contrast_review_archive', ROOT/'tools/inspect_cloud_packet.py')
    extraction = helper._new_output(ROOT/'records/aws_contrast_v6_001_review_extracted', extracted=True)
    with zipfile.ZipFile(PACKET) as archive:
        infos, expanded = helper._safe_infos(archive)
        inventory = []
        for name, info in sorted(infos.items()):
            if info.is_dir():
                continue
            state, count = sha256(), 0
            with archive.open(info) as stream:
                for raw in iter(lambda: stream.read(1024**2), b''):
                    count += len(raw)
                    require(count <= info.file_size, 'MEMBER_SIZE_EXCEEDED')
                    state.update(raw)
            require(count == info.file_size, 'MEMBER_SIZE_MISMATCH')
            inventory.append({'path': name, 'bytes': count, 'sha256': state.hexdigest()})
        packet = helper.Packet(archive, infos, inventory)
        collection, full_index = helper._collection(packet, JOB, SOURCE, SOURCE_HASH)
        require(full_index and collection['returncode'] == 0
                and collection['partial_evidence'] is False
                and collection.get('experiment') == manifest['experiment'], 'COMPLETE_BOUND_PACKET_REQUIRED')
        campaign = packet.json(BASE+'campaign_receipt.json')
        require(campaign.get('schema') == 'cas-meta2-contrast-campaign/6'
                and campaign.get('job') == JOB and campaign.get('experiment') == manifest['experiment']
                and all(campaign.get(key) is True for key in
                        ('completed', 'training_performed', 'native_evaluation_completed'))
                and all(campaign.get(key) is False for key in
                        ('learning_accepted', 'release_accepted', 'automatic_retry')),
                'COMPLETED_CANDIDATE_CAMPAIGN_REQUIRED')
        from cas_meta2.contrast_v6 import train, curriculum, data, checks
        from cas_meta2.contrast_v6.campaign import configurations, check_native_output
        require(campaign['source_sha256'] == train.source_identity(), 'SOURCE_MAPPING_MISMATCH')
        baseline = campaign['baseline_before']
        require(baseline['source'] == {'baseline_sha': manifest['baseline_sha'], 'files_verified': 316},
                'BASELINE_IDENTITY_MISMATCH')
        require({v['wheel_sha256'] for v in baseline['installed_wheels'].values()}
                == {manifest['files_sha256'][p] for p in manifest['wheel_paths']}, 'WHEEL_IDENTITY_MISMATCH')
        payload = packet.json(BASE+'payload_sha256.json')
        require(payload == {r['path'].removeprefix(BASE): r['sha256'] for r in inventory
                            if r['path'].startswith(BASE) and r['path'] != BASE+'payload_sha256.json'},
                'FULL_PAYLOAD_INDEX_MISMATCH')
        gpu = check_gpu_gates(packet, manifest, campaign)
        runtime = packet.json('cloud_job/runtime.json')
        require(runtime.get('cuda_matmul_passed') is True and runtime.get('torch') == '2.11.0+cu128'
                and runtime.get('cuda') == '12.8' and 'RTX PRO 4500' in runtime.get('gpu', ''),
                'CUDA_ENVIRONMENT_MISMATCH')
        extraction_record = helper._extract(packet, extraction)
    output = extraction/'cloud_job/campaign'
    spec = checks.read(ROOT/'EXPERIMENT_CONTRAST_V6.json')
    require(checks.read(output/'experiment.json') == spec, 'REGISTERED_EXPERIMENT_MISMATCH')
    cfg, training = configurations(spec)
    excluded = train.registered_exclusions(ROOT/'records/contrast_v6_exclusions_001/inventory.json')
    initial = checks.read(output/'initial_identity.json')
    require(initial == {'source_sha256': campaign['source_sha256'],
                        'baseline': baseline, 'experiment': manifest['experiment']}, 'INITIAL_IDENTITY_MISMATCH')
    pin = checks.file_hash(output/'dataset/manifest.json')
    remote_root = '/opt/cas-meta2/package/'+manifest['pilot_dir']
    remote_output = remote_root+'/runs/cloud_job/campaign'
    gpu_process = checks.process_exit(output/'processes/gpu_gate/process_receipt.json',
                                     expected_command=gpu_commands(manifest)['contrast_pipeline'])
    require(gpu_process == campaign['processes']['gpu_gate'], 'GPU_PROCESS_RECEIPT_CHANGED')
    command = ['/opt/cas-meta2/venv/bin/python', '-B', '-m', 'cas_meta2.contrast_v6.train',
               '--bundle', remote_output+'/trainer_input', '--output', remote_output+'/training',
               '--job', JOB, '--manifest-sha256', pin, '--curriculum-seed', str(spec['curriculum_seed']),
               '--curriculum-config', remote_output+'/curriculum_config.json',
               '--training-config', remote_output+'/training_config.json',
               '--exclusions', remote_root+'/records/contrast_v6_exclusions_001/inventory.json']
    gate = checks.check_training(output/'training', output/'processes/training/process_receipt.json',
        output/'trainer_input', expected_command=command, job=JOB, expected_manifest_sha256=pin,
        curriculum_seed=spec['curriculum_seed'], curriculum_config=cfg, excluded=excluded,
        config=training, expected_source=campaign['source_sha256'], expected_baseline=baseline)
    require(gate == checks.read(output/'training_gate.json'), 'RECORDED_TRAINING_GATE_MISMATCH')
    dataset_manifest, tasks, publics = check_dataset(output, pin=pin, seed=spec['curriculum_seed'],
                                                   config=cfg, excluded=excluded)
    bindings = check_native_bindings(output, gate=gate, manifest=dataset_manifest, tasks=tasks,
                                    publics=publics, remote_output=remote_output, job=JOB)
    for phase in ('gpu_gate', 'dataset', 'training', 'evaluate'):
        require(checks.read(output/'processes'/phase/'process_receipt.json') == campaign['processes'][phase],
                'CAMPAIGN_PROCESS_COPY_MISMATCH:'+phase)
    native = check_native_output(output, spec['test_count'])
    require(native == campaign['native'], 'NATIVE_SUMMARY_RECOUNT_MISMATCH')
    require(digest(PACKET) == expected_hash and digest(SOURCE_ZIP) == SOURCE_HASH, 'ARCHIVE_CHANGED')
    for relative, checksum in manifest['files_sha256'].items():
        require(digest(ROOT.parent.parent/relative) == checksum, 'SOURCE_CHANGED_DURING_REVIEW:'+relative)
    for row in inventory:
        require(digest(extraction/row['path']) == row['sha256'], 'EXTRACTION_CHANGED_DURING_REVIEW:'+row['path'])
    receipt = checks.read(output/'training/training_receipt.json')
    return {'schema': 'cas-meta2-offline-contrast-review/6',
        'status': 'RECORDED_CONTRAST_RECOUNT_PASSED', 'job': JOB,
        'source_sha': SOURCE, 'source_archive_sha256': SOURCE_HASH, 'packet_sha256': expected_hash,
        'source_files_verified': len(manifest['files_sha256']), 'expanded_bytes': expanded,
        'source_manifest': manifest, 'extraction': extraction_record, 'member_files': len(inventory),
        'source_and_extraction_rechecked_at_end': True, 'binding_checks': bindings,
        'gpu_tests': gpu, 'runtime': runtime, 'training_gate': gate, 'native_summary': native,
        'history': receipt['history'], 'optimizer_steps': receipt['optimizer_steps'],
        'inventory': inventory, 'script_sha256': digest(__file__),
        'utc': datetime.now(timezone.utc).isoformat(), 'neural_execution': False,
        'provider_calls': False, 'learning_accepted': False,
        'boundary': 'Offline saved-action, selection, checkpoint-byte and summary recount. '
                    'Not independent neural replay or native stored-trace semantic audit.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    sys.meta_path.insert(0, Guard())
    sys.path.insert(0, str(ROOT))
    output = HERE/'receipt.json'
    require(not output.exists(), 'NEW_REVIEW_RECEIPT_REQUIRED')
    result = review(args.sha256)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in
        ('status', 'source_files_verified', 'optimizer_steps', 'native_summary')}, indent=2))
