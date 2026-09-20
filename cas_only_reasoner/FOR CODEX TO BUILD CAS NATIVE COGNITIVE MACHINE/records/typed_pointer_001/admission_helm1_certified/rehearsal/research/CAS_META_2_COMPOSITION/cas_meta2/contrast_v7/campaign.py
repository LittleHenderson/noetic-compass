"""V7 source-bound dataset, training, and evaluation campaign.

The dataset phase builds a fresh base, appends exact known originals through
the source-pinned parent, and exports public-only trainer files. Native
evaluation is deliberately not routed to the old fatal-worker implementation.
No local generation or training is permitted. A literal prerequisite review
and the current job's GPU gate are required before full candidate training.
"""
from dataclasses import asdict
from datetime import datetime, timezone
import math
import os
from pathlib import Path
import re
import signal
import time
import traceback
import sys

from ..contrast_v6 import curriculum as c
from . import data as d, train as t, checks
from tools import experiment_profiles_prototype_v7 as profile

ROOT = Path(__file__).resolve().parents[2]
SPEC_NAME = 'EXPERIMENT_PROTOTYPE_V7.json'
SCHEMA = 'cas-meta2-prototype-assembly/7'


def registered_spec():
    return profile.validate_prototype_spec(d.read(ROOT/SPEC_NAME))


def configurations(spec):
    profile.validate_prototype_spec(profile.canonical(spec))
    return c.Config(**spec['curriculum']).checked(), t.TrainingConfig(**spec['training']).checked()


def experiment_identity():
    raw = d.read(ROOT/SPEC_NAME)
    spec = profile.validate_prototype_spec(raw)
    record = {'profile': spec['profile'], 'entrypoint': spec['entrypoint'],
              'spec_path': profile.SPEC_PATH, 'spec_sha256': d.digest(raw)}
    c.require(os.environ.get('CAS_META2_EXPERIMENT_PROFILE') == record['profile']
        and os.environ.get('CAS_META2_EXPERIMENT_ENTRYPOINT') == record['entrypoint']
        and os.environ.get('CAS_META2_EXPERIMENT_SPEC_SHA256') == record['spec_sha256']
        and re.fullmatch('[a-f0-9]{40}', os.environ.get('CAS_META2_SOURCE_SHA', '')),
        'V7_SOURCE_BOUND_LAUNCH_IDENTITY_REQUIRED')
    return spec, record


def source_identity():
    result = t.source_identity()
    for name in (SPEC_NAME, 'tools/experiment_profiles_prototype_v7.py',
                 profile.FIXED_SPEC['source_pins_path'], profile.FIXED_SPEC['exclusion_inventory_path']):
        result[name] = d.digest(d.read(ROOT/name))
    return result


def checked_inputs(spec):
    """Check literal trust anchors before parent or loader helper execution."""
    profile.validate_prototype_spec(profile.canonical(spec))
    pins = ROOT/spec['source_pins_path']
    raw = d.read(pins)
    c.require(d.digest(raw) == spec['source_pins_sha256'], 'V7_CAMPAIGN_SOURCE_PINS_CHANGED')
    profile.pinned_source_map(raw)
    c.require(d.digest(d.read(ROOT/spec['original_tasks_path'])) == spec['original_tasks_sha256'],
              'V7_CAMPAIGN_ORIGINAL_BYTES_CHANGED')
    loader = d.public_loader(spec['public_loader_sha256'])
    source = d.decode(raw)
    loader.verify_source(source, expected_loader_sha256=spec['public_loader_sha256'], root=ROOT)
    excluded = t.registered_exclusions(ROOT/spec['exclusion_inventory_path'],
                                      expected_sha256=spec['exclusion_inventory_sha256'])
    c.require(len(excluded) == spec['exclusion_count'] == 8837, 'V7_CAMPAIGN_EXCLUSION_COUNT_CHANGED')
    return excluded


def parent_module():
    # Never imported into the trainer or before the campaign's pinned inputs.
    from . import parent
    return parent


def expected_splits(spec):
    return {name: {'tasks': spec[field], 'depths': spec[depths]} for name, field, depths in (
        ('train','train_count','train_depths'), ('validation','validation_count','validation_depths'),
        ('test','test_count','test_depths'))}


def parent_options(spec, cfg, excluded):
    return {'seed': spec['curriculum_seed'], 'config': cfg, 'excluded': excluded,
        'pins': ROOT/spec['source_pins_path'], 'expected_pins_sha256': spec['source_pins_sha256'],
        'expected_loader_sha256': spec['public_loader_sha256']}


def prepare_configuration_files(output, cfg, training, spec):
    """Materialize or verify the exact files consumed by the later trainer CLI."""
    for name, value in (('curriculum_config.json', asdict(cfg)),
                        ('training_config.json', asdict(training)), ('experiment.json', spec)):
        path = output/name
        if path.exists():
            c.require(checks.read(path) == value, 'V7_REGISTERED_CONFIGURATION_CHANGED:'+name)
        else:
            t.write_new(path, value)


def validate_assembly_records(base, merged, cold, exported, *, spec, base_pin, merged_pin, excluded):
    """Validate recounted saved metadata; never infer counts from planned labels."""
    expected = expected_splits(spec)
    base_expected = {**expected, 'train': {'tasks': 640, 'depths': {'1':128,'2':256,'3':256}}}
    c.require(all({k: base['splits'][name][k] for k in ('tasks','depths')} == value
                  for name, value in base_expected.items()), 'V7_BASE_ACTUAL_COUNTS_CHANGED')
    c.require(merged.get('schema') == 'cas-meta2-prototype-training-integration/7'
        and merged.get('splits') == expected and merged.get('training_append_count') == 256
        and merged.get('pair_members_kept_together') is True, 'V7_MERGED_ACTUAL_COUNTS_CHANGED')
    c.require(merged['base']['manifest_sha256'] == base_pin
        and merged['base']['seed'] == spec['curriculum_seed']
        and merged['base']['config'] == spec['curriculum']
        and merged['base']['exclusion_count'] == len(excluded) == spec['exclusion_count']
        and merged['base']['exclusions_sha256'] == d.digest(profile.canonical(sorted(excluded))),
        'V7_MERGE_BASE_BINDING_CHANGED')
    original = merged['prototype']
    c.require(original['tasks'] == 256 and original['pairs'] == 128
        and original['depths'] == {'2':128,'3':128}
        and original['tasks_sha256'] == spec['original_tasks_sha256']
        and original['allowed_split'] == 'train' and original['fresh_evaluation'] is False
        and original['original_provenance_preserved'] is True, 'V7_EXACT_ORIGINAL_IMPORT_REQUIRED')
    heldout = {name: base['sha256'][name] for name in ('validation.json','test_public.json','test_private.json')}
    c.require(merged['heldout_bytes_unchanged'] == heldout
        and all(merged['sha256'][name] == pin for name, pin in heldout.items()),
        'V7_HELDOUT_BYTES_CHANGED')
    c.require(cold.get('schema') == 'cas-meta2-prototype-integration-validation/7'
        and cold.get('completed') is True and cold.get('manifest_sha256') == merged_pin
        and cold.get('dataset_id') == merged['dataset_id'] and cold.get('splits') == expected
        and cold.get('prototype_tasks') == 256 and cold.get('prototype_pairs') == 128
        and cold.get('heldout_bytes_unchanged') == heldout and cold.get('tokenizer_fit_examples') == 896
        and cold.get('parent_reads_private_test_targets') is True and cold.get('training_performed') is False,
        'V7_COLD_PARENT_ADMISSION_REQUIRED')
    c.require(exported.get('schema') == 'cas-meta2-public-training-bundle/7'
        and exported.get('dataset_id') == merged['dataset_id'] and exported.get('manifest_sha256') == merged_pin
        and exported.get('splits') == expected and exported.get('base_train_examples') == 640
        and exported.get('imported_train_examples') == 256 and exported.get('tokenizer_fit_examples') == 896
        and exported.get('private_labels_read_by_loader') is False
        and exported.get('test_programs_parsed_by_loader') is False
        and exported.get('parent_validation_replayed_by_loader') is False
        and exported.get('parent_validation') == cold and exported.get('training_performed') is False
        and 'test_private.json' not in exported.get('loaded_sha256', {}), 'V7_PUBLIC_EXPORT_BOUNDARY')
    c.require(all(merged['sha256'].get(name) == pin for name, pin in exported['loaded_sha256'].items()),
              'V7_EXPORTED_FILE_PIN_CHANGED')
    steps = math.ceil(expected['train']['tasks']/spec['training']['batch_size'])*spec['training']['epochs']
    c.require(steps == spec['optimizer_steps_per_family'] == 11200, 'V7_ASSEMBLED_STEP_COUNT_CHANGED')
    return {'actual_splits': expected, 'base_train_examples': 640, 'imported_train_examples': 256,
            'optimizer_steps_per_family': steps, 'heldout_bytes_unchanged': heldout}


def assemble_dataset(output, *, job, spec=None):
    """Real AWS data phase; tests replace constructors with synthetic stubs."""
    spec = registered_spec() if spec is None else spec
    profile.require_execution_ready(spec)
    cfg, training = configurations(spec)
    t.require_request(job, training)  # Linux and explicit AWS job enablement.
    check_gpu_phase(output, job=job, spec=spec)
    excluded = checked_inputs(spec)
    output = d.no_links(output)
    c.require(output.is_dir() and output.resolve().is_relative_to((ROOT/'runs').resolve())
        and all(not (output/name).exists() for name in ('base_dataset','dataset','trainer_input','dataset_assembly_receipt.json')),
        'V7_NEW_RUNTIME_DATA_OUTPUT_REQUIRED')
    before = source_identity()
    parent = parent_module()
    opts = parent_options(spec, cfg, excluded)
    prepare_configuration_files(output, cfg, training, spec)
    c.write(output/'base_dataset', seed=spec['curriculum_seed'], config=cfg, excluded=excluded)
    base_pin = checks.file_hash(output/'base_dataset/manifest.json')
    merged_check = parent.merge(output/'base_dataset', output/'dataset', expected_sha256=base_pin, **opts)
    merged_pin = checks.file_hash(output/'dataset/manifest.json')
    cold = parent.validate_bundle(output/'dataset', expected_sha256=merged_pin, **opts)
    c.require(cold == merged_check, 'V7_MERGE_COLD_RECEIPT_CHANGED')
    exported = parent.export_training_bundle(output/'dataset', output/'trainer_input',
                                              expected_sha256=merged_pin, **opts)
    base = checks.read(output/'base_dataset/manifest.json')
    merged = checks.read(output/'dataset/manifest.json')
    recounted = validate_assembly_records(base, merged, cold, exported, spec=spec,
        base_pin=base_pin, merged_pin=merged_pin, excluded=excluded)
    c.require(not (output/'trainer_input/test_private.json').exists(), 'V7_PRIVATE_FILE_EXPORTED')
    c.require(source_identity() == before and checked_inputs(spec) == excluded
        and checks.file_hash(output/'base_dataset/manifest.json') == base_pin
        and checks.file_hash(output/'dataset/manifest.json') == merged_pin, 'V7_ASSEMBLY_BOUND_INPUT_CHANGED')
    # The training process cannot start until these actual counts and identities
    # have been written and admitted by the parent.
    receipt = {'schema': SCHEMA, 'completed': True, 'job': job, 'pid': os.getpid(),
        'curriculum_seed': spec['curriculum_seed'], 'base_manifest_sha256': base_pin,
        'manifest_sha256': merged_pin, 'dataset_id': merged['dataset_id'], **recounted,
        'source_pins_sha256': spec['source_pins_sha256'], 'public_loader_sha256': spec['public_loader_sha256'],
        'exclusion_inventory_sha256': spec['exclusion_inventory_sha256'], 'exclusion_count': len(excluded),
        'source_sha256': before, 'parent_validation': cold, 'public_export': exported,
        'original_tasks_sha256': spec['original_tasks_sha256'], 'original_training_only': True,
        'all_original_graphs_remain_in_fresh_exclusions': True,
        'neural_execution': False, 'training_started': False, 'native_evaluation_completed': False,
        'learning_accepted': False, 'utc': datetime.now(timezone.utc).isoformat(),
        'boundary': 'Actual assembled counts after exact-byte training append. Parent checks private targets; '
                    'trainer receives no private file. Not a learning or native-evaluation result.'}
    t.write_new(output/'training_bundle_receipt.json', exported)
    t.write_new(output/'dataset_assembly_receipt.json', receipt)
    return receipt


def require_assembly(output, spec):
    profile.validate_prototype_spec(profile.canonical(spec))
    output = d.no_links(output)
    receipt = checks.read(output/'dataset_assembly_receipt.json')
    c.require(receipt.get('schema') == SCHEMA and receipt.get('completed') is True
        and receipt.get('actual_splits') == expected_splits(spec)
        and receipt.get('optimizer_steps_per_family') == 11200
        and receipt.get('manifest_sha256') == checks.file_hash(output/'dataset/manifest.json')
        and receipt.get('source_pins_sha256') == spec['source_pins_sha256']
        and receipt.get('public_loader_sha256') == spec['public_loader_sha256']
        and receipt.get('exclusion_inventory_sha256') == spec['exclusion_inventory_sha256']
        and receipt.get('exclusion_count') == spec['exclusion_count']
        and receipt.get('original_tasks_sha256') == spec['original_tasks_sha256']
        and receipt.get('original_training_only') is True
        and receipt.get('all_original_graphs_remain_in_fresh_exclusions') is True
        and receipt.get('training_started') is False and receipt.get('neural_execution') is False,
        'V7_ACTUAL_ASSEMBLY_RECEIPT_REQUIRED_BEFORE_TRAINING')
    return receipt


def training_command(output, job, spec):
    output = Path(output)
    assembly = require_assembly(output, spec)
    return [sys.executable, '-B', '-m', 'cas_meta2.contrast_v7.train',
        '--bundle', str(output/'trainer_input'), '--output', str(output/'training'), '--job', job,
        '--manifest-sha256', assembly['manifest_sha256'], '--loader-sha256', spec['public_loader_sha256'],
        '--curriculum-seed', str(spec['curriculum_seed']),
        '--curriculum-config', str(output/'curriculum_config.json'),
        '--training-config', str(output/'training_config.json'),
        '--exclusions', str(ROOT/spec['exclusion_inventory_path']),
        '--exclusions-sha256', spec['exclusion_inventory_sha256']]


def gate_arguments(output, job, spec):
    output = Path(output)
    cfg, training = configurations(spec)
    excluded = checked_inputs(spec)
    assembly = require_assembly(output, spec)
    initial = checks.read(output/'initial_identity.json')
    c.require(initial.get('source_sha256') == t.source_identity()
        and initial.get('campaign_source_sha256') == source_identity()
        and assembly['source_sha256'] == initial['campaign_source_sha256'], 'V7_INITIAL_SOURCE_IDENTITY_CHANGED')
    return dict(expected_command=training_command(output, job, spec), job=job,
        expected_manifest_sha256=assembly['manifest_sha256'], expected_loader_sha256=spec['public_loader_sha256'],
        curriculum_seed=spec['curriculum_seed'], curriculum_config=cfg, excluded=excluded, config=training,
        expected_source=initial['source_sha256'], expected_baseline=initial['baseline'])


def check_training_phase(output, *, job, spec):
    output = Path(output)
    return checks.check_training(output/'training', output/'processes/training/process_receipt.json',
                                 output/'trainer_input', **gate_arguments(output, job, spec))


def gpu_command(output):
    output = Path(output)
    return [sys.executable, '-B', '-m', 'pytest', '-q', '-m', 'gpu',
        '-p', 'cas_meta2.pytest_no_aliases_v4', '-p', 'no:cacheprovider',
        'tests/test_contrast_v7_train_gpu.py', '--basetemp', str(output/'gpu_tmp'),
        '--junitxml', str(output/'gpu_test.xml')]


def check_gpu_phase(output, *, job, spec):
    """A passing XML alone cannot authorize full candidate training."""
    import xml.etree.ElementTree as ET
    from . import gpu_preflight as gpu
    output = d.no_links(output)
    process = checks.process_exit(output/'processes/gpu_gate/process_receipt.json',
                                  expected_command=gpu_command(output))
    xml = ET.parse(output/'gpu_test.xml').getroot()
    cases, suites = list(xml.iter('testcase')), list(xml.iter('testsuite'))
    c.require(len(cases) == 1 and cases[0].get('name') == gpu.GPU_TEST
        and cases[0].get('classname', '').endswith('test_contrast_v7_train_gpu')
        and suites and sum(int(s.get('tests', '-1')) for s in suites) == 1
        and not any(list(xml.iter(tag)) for tag in ('failure','error','skipped'))
        and all(int(s.get(key, '-1')) == 0 for s in suites for key in ('failures','errors','skipped')),
        'V7_EXACT_CURRENT_GPU_TEST_REQUIRED')
    found = list((output/'gpu_tmp').rglob('gpu_smoke_receipt.json'))
    c.require(len(found) == 1, 'V7_ONE_CURRENT_GPU_SMOKE_REQUIRED')
    path = d.no_links(found[0])
    smoke = checks.read(path)
    initial = checks.read(output/'initial_identity.json')
    c.require(smoke.get('schema') == gpu.SCHEMA
        and smoke.get('status') == 'V7_KNOWN_FIXTURE_CUDA_FULL_PIPELINE_SMOKE_PASSED'
        and smoke.get('completed') is True and smoke.get('job') == job
        and smoke.get('native_evaluation_completed') is True
        and smoke.get('source_sha256') == initial['source_sha256'] == t.source_identity()
        and smoke.get('baseline') == initial['baseline']
        and smoke.get('splits') == gpu.EXPECTED_SPLITS
        and smoke.get('optimizer_steps') == {'cas':22,'generic':22}
        and smoke.get('prepare_exit_before_training') is True
        and smoke.get('learning_accepted') is False and smoke.get('task_generation') is False
        and smoke['training_gate']['private_test_labels_opened'] is False
        and smoke['fixture']['source_pins_sha256'] == spec['source_pins_sha256']
        and smoke['fixture']['public_loader_sha256'] == spec['public_loader_sha256']
        and all(smoke['changed_weights'][family]['all_loaded_on_cuda'] is True
            and smoke['changed_weights'][family]['changed_count'] > 0 for family in ('cas','generic')),
        'V7_CURRENT_FULL_GPU_SMOKE_REQUIRED')
    gpu.check_native_smoke(smoke['native_receipt'])
    native_path = path.parent/'native_evaluation/native_receipt.json'
    c.require(checks.file_hash(native_path) == smoke['native_receipt_sha256']
        and checks.read(native_path) == smoke['native_receipt'], 'V7_GPU_NATIVE_RECEIPT_CHANGED')
    return {'tests':1, 'process_pid':process['pid'], 'smoke_path':str(path.relative_to(output)),
        'smoke_sha256':checks.file_hash(path), 'native_cases':9, 'native_arm_verdicts':45,
        'process_receipt_sha256':checks.file_hash(output/'processes/gpu_gate/process_receipt.json'),
        'tests_xml_sha256':checks.file_hash(output/'gpu_test.xml')}


def dataset_command(output, job, name):
    c.require(name in ('dataset','evaluate'), 'V7_REGISTERED_PHASE_REQUIRED')
    return [sys.executable, '-B', '-m', 'cas_meta2.contrast_v7.campaign',
        '--output', str(output), '--job', job, '--phase', name]


def require_dataset_exit(output, *, job, spec):
    process = checks.process_exit(Path(output)/'processes/dataset/process_receipt.json',
        expected_command=dataset_command(output, job, 'dataset'))
    assembled = require_assembly(output, spec)
    c.require(process['pid'] != os.getpid() and assembled['pid'] == process['pid']
        and assembled['job'] == job, 'V7_DATASET_CHILD_EXIT_REQUIRED')
    return process, assembled


def check_native_output(output, count):
    from . import native_evaluation as native
    output = Path(output)
    receipt = checks.read(output/'native/native_receipt.json')
    results = checks.read(output/'native/evaluation_results.json')
    tasks = checks.read(output/'dataset/test_private.json')
    c.require(type(receipt.get('cases')) is int and receipt['cases'] == count == len(tasks)
        and receipt.get('schema') == 'cas-meta2-prototype-native-evaluation/7'
        and receipt.get('completed') is True and receipt.get('learning_accepted') is False
        and receipt.get('reference_cases') == count and receipt.get('arm_verdicts') == count*5,
        'V7_NATIVE_RESULT_COVERAGE')
    recounted = native.aggregate_cases(results['cases'], count)
    groups = native.grouped_results(results['cases'], tasks)
    c.require(recounted == results['results'] == receipt['results']
        and groups == results['groups'] == receipt['groups']
        and recounted['rule']['task_correct'] == count, 'V7_NATIVE_SUMMARY_OR_RULE_CONTROL')
    return {'results':recounted, 'groups':groups, 'cases':count, 'reference_cases':count,
        'arm_verdicts':count*5, 'native_receipt_sha256':checks.file_hash(output/'native/native_receipt.json'),
        'evaluation_results_sha256':checks.file_hash(output/'native/evaluation_results.json')}


def run_phase(output, job, name):
    spec = registered_spec()
    profile.require_execution_ready(spec)
    experiment_identity()
    cfg, training = configurations(spec)
    t.require_request(job, training)
    output = d.no_links(output)
    check_gpu_phase(output, job=job, spec=spec)
    if name == 'dataset':
        return assemble_dataset(output, job=job, spec=spec)
    if name == 'evaluate':
        from . import native_evaluation as native
        require_dataset_exit(output, job=job, spec=spec)
        return native.evaluate(output/'dataset', output/'training',
            output/'processes/training/process_receipt.json', output/'trainer_input', output/'native',
            max_seconds=spec['native_max_seconds'], pins=ROOT/spec['source_pins_path'],
            expected_pins_sha256=spec['source_pins_sha256'], **gate_arguments(output, job, spec))
    raise ValueError('V7_REGISTERED_PHASE_REQUIRED')


def run(output, *, job, max_seconds=6900):
    spec = registered_spec()
    profile.require_execution_ready(spec)
    spec, experiment = experiment_identity()
    cfg, training = configurations(spec)
    t.require_request(job, training)
    c.require(type(max_seconds) is int and max_seconds == spec['max_wall_seconds'] == 6900,
              'V7_REGISTERED_PARENT_TIME_BOUND')
    from ..campaign_v3 import _new_output, _baseline_identity, _run_process, _final_payload_index, _write
    from . import gpu_preflight as gpu
    c.require(gpu.NATIVE_GATE_READY is True, 'V7_GPU_NATIVE_HELPER_NOT_READY')
    output = _new_output(output)
    started = time.monotonic()
    deadline = started+max_seconds-30
    sources, campaign_sources, baseline = t.source_identity(), source_identity(), _baseline_identity()
    checked_inputs(spec)
    t.write_new(output/'initial_identity.json', {'source_sha256':sources,
        'campaign_source_sha256':campaign_sources, 'baseline':baseline, 'experiment':experiment})
    prepare_configuration_files(output, cfg, training, spec)
    record = {'schema':'cas-meta2-prototype-campaign/7', 'job':job, 'experiment':experiment,
        'completed':False, 'training_performed':False, 'training_attempted':False,
        'native_evaluation_completed':False,
        'learning_accepted':False, 'release_accepted':False, 'automatic_retry':False,
        'source_sha256':sources, 'campaign_source_sha256':campaign_sources,
        'baseline_before':baseline, 'processes':{}, 'stage':'gpu_gate'}
    previous = signal.getsignal(signal.SIGALRM)
    def interrupt(signum, frame):
        raise TimeoutError('V7_PARENT_DEADLINE')
    signal.signal(signal.SIGALRM, interrupt)
    signal.setitimer(signal.ITIMER_REAL, max_seconds-30)
    def phase(name, seconds, command):
        record['stage'] = name
        _write(output/'campaign_status.json', {'job':job, 'stage':name, 'completed':False,
            'elapsed_seconds':time.monotonic()-started})
        result = _run_process(command, output/'processes'/name,
            min(deadline, time.monotonic()+seconds), environment=dict(os.environ))
        record['processes'][name] = result
        return result
    try:
        phase('gpu_gate', spec['gpu_gate_max_seconds'], gpu_command(output))
        record['gpu_gate'] = check_gpu_phase(output, job=job, spec=spec)
        phase('dataset', spec['dataset_max_seconds'], dataset_command(output, job, 'dataset'))
        dataset_process, assembly = require_dataset_exit(output, job=job, spec=spec)
        record['actual_splits'] = assembly['actual_splits']
        record['dataset_assembly_receipt_sha256'] = checks.file_hash(output/'dataset_assembly_receipt.json')
        print(c.canonical({'stage':'dataset_assembled', 'actual_splits':assembly['actual_splits'],
            'imported_training_records':assembly['imported_train_examples'],
            'assembly_receipt_sha256':record['dataset_assembly_receipt_sha256']}).decode(), flush=True)
        c.require(deadline-time.monotonic() >= training.max_seconds+spec['native_max_seconds']+90,
                  'V7_INSUFFICIENT_TRAIN_AND_NATIVE_ALLOCATION')
        record.update(training_attempted=True, training_performed=None)
        phase('training', training.max_seconds+15, training_command(output, job, spec))
        gate = check_training_phase(output, job=job, spec=spec)
        record['training_performed'] = True
        training_process = checks.process_exit(output/'processes/training/process_receipt.json',
            expected_command=training_command(output, job, spec))
        c.require(dataset_process['pid'] != training_process['pid']
            and checks.timestamp(dataset_process['finished_utc'])
                <= checks.timestamp(training_process['started_utc']), 'V7_DATASET_EXIT_BEFORE_TRAINING')
        t.write_new(output/'training_gate.json', gate)
        phase('evaluate', spec['native_max_seconds']+15, dataset_command(output, job, 'evaluate'))
        record['native'] = check_native_output(output, spec['test_count'])
        c.require(check_training_phase(output, job=job, spec=spec) == gate
            and check_gpu_phase(output, job=job, spec=spec) == record['gpu_gate']
            and t.source_identity() == sources and source_identity() == campaign_sources
            and _baseline_identity() == baseline and experiment_identity()[1] == experiment,
            'V7_CAMPAIGN_BOUND_STATE_CHANGED')
        record.update(completed=True, native_evaluation_completed=True, stage='completed')
    except BaseException as error:
        record['failure'] = {'type':type(error).__name__, 'message':str(error), 'traceback':traceback.format_exc()}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
    record.update(wall_seconds=time.monotonic()-started, finished_utc=datetime.now(timezone.utc).isoformat())
    t.write_new(output/'campaign_receipt.json', record)
    _write(output/'campaign_status.json', {'job':job, 'stage':record['stage'], 'completed':record['completed']})
    try:
        _final_payload_index(output)
    except BaseException as error:
        record.update(completed=False, stage='collection',
                      finalization_error={'type':type(error).__name__, 'message':str(error)})
        _write(output/'campaign_receipt.json', record)
        raise
    return record


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--job', required=True)
    parser.add_argument('--max-wall-seconds', type=int, default=6900)
    parser.add_argument('--phase', choices=('dataset','evaluate'))
    args = parser.parse_args()
    if args.phase:
        run_phase(args.output, args.job, args.phase)
        return 0
    return 0 if run(args.output, job=args.job, max_seconds=args.max_wall_seconds)['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
