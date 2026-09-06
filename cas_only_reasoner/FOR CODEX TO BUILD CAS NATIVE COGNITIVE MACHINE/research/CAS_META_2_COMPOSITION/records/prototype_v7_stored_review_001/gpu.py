"""Stored v7 smoke evidence only. Never loads a tensor or executes a task."""
from hashlib import sha256
import math
from pathlib import PurePosixPath
import xml.etree.ElementTree as ET

MANIFEST = '19162857679b3eb2e698c58ee8e0ac5dc3c7ffe7265e11e8ae1c726834067f29'
ARMS = ('cas_untrained', 'cas_trained', 'generic_untrained', 'generic_trained', 'rule')
COLD_CODE = ('import sys;from cas_meta2.contrast_v7.native_evaluation import validate_private_child;'
             'validate_private_child(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4])')


def audit_smoke(packet, *, job, source, baseline, spec, modules, c, evidence):
    """Caller must authenticate source/Git/ZIP and every Packet byte first.

    Recounts source-bound public training records and native result structure.
    Changed CUDA tensors remain an attributed GPU-authored claim, not a local
    tensor check. Native SQLite/verifier semantics are not rerun by this helper.
    """
    q, checks, train = (modules[name] for name in ('gpu_preflight', 'checks', 'train'))
    curriculum, parent, native = (modules[name] for name in ('curriculum', 'parent', 'native'))
    prefix = '/opt/cas-meta2/package/' + c.PILOT + '/runs/'
    artifacts = {}

    def same(actual, expected, code):
        c.require(c.canonical(actual) == c.canonical(expected), code)

    def bound(name, pin=None):
        c.safe_name(name)
        c.require(name in packet.inventory, 'SMOKE_MEMBER_MISSING:' + name)
        if pin is not None:
            packet.same_hash(name, pin)
        path = packet.path(name)
        artifacts[name] = packet.inventory[name]['sha256']
        return path

    def doc(name):
        bound(name)
        return packet.json(name)

    def exact_directory(directory, names):
        actual = {name[len(directory):] for name in packet.inventory if name.startswith(directory)}
        same(sorted(actual), sorted(names), 'SMOKE_DIRECTORY_COVERAGE:' + directory)

    def process(name, command):
        row = evidence.process(packet, name, command, c)
        bound(name)
        for stream in ('stdout', 'stderr'):
            bound(name.removesuffix('process_receipt.json') + stream + '.txt', row[stream + '_sha256'])
        return row

    def stamp(value):
        return evidence.timestamp(value, c)

    outer_name = c.BASE + 'processes/gpu_gate/process_receipt.json'
    outer = doc(outer_name)
    command = outer['command']
    c.require(type(command) is list and command and type(command[0]) is str
              and command[0].startswith('/opt/cas-meta2/venv/bin/python'), 'SMOKE_PYTHON_COMMAND')
    python = command[0]
    expected = [python, '-B', '-m', 'pytest', '-q', '-m', 'gpu', '-p', 'cas_meta2.pytest_no_aliases_v4',
                '-p', 'no:cacheprovider', 'tests/test_contrast_v7_train_gpu.py', '--basetemp',
                prefix + c.BASE + 'gpu_tmp', '--junitxml', prefix + c.BASE + 'gpu_test.xml']
    same(command, expected, 'SMOKE_GPU_COMMAND')
    outer = process(outer_name, expected)
    xml_name = c.BASE + 'gpu_test.xml'
    bound(xml_name)
    raw = packet.raw(xml_name, 2 * 1024**2)
    c.require(b'<!DOCTYPE' not in raw.upper() and b'<!ENTITY' not in raw.upper(), 'SMOKE_XML_DECLARATION')
    xml = ET.fromstring(raw)
    cases, suites = list(xml.iter('testcase')), list(xml.iter('testsuite'))
    c.require(len(cases) == 1 and cases[0].get('name') == q.GPU_TEST
        and cases[0].get('classname', '').endswith('test_contrast_v7_train_gpu') and suites
        and sum(int(row.get('tests', '-1')) for row in suites) == 1
        and not any(list(xml.iter(tag)) for tag in ('failure', 'error', 'skipped'))
        and all(int(row.get(key, '-1')) == 0 for row in suites for key in ('failures', 'errors', 'skipped')),
        'SMOKE_ONE_ACTUAL_GPU_TEST')
    found = sorted(name for name in packet.inventory if name.startswith(c.BASE + 'gpu_tmp/')
                   and name.endswith('/gpu_smoke_receipt.json'))
    c.require(len(found) == 1, 'SMOKE_ONE_CURRENT_RECEIPT')
    smoke_name = found[0]
    smoke_base = smoke_name.removesuffix('gpu_smoke_receipt.json')
    smoke = doc(smoke_name)
    initial = doc(c.BASE + 'initial_identity.json')
    same(initial['source_sha256'], source, 'SMOKE_INITIAL_SOURCE')
    evidence.baseline(initial['baseline'], baseline, c)
    c.require(smoke['schema'] == q.SCHEMA and smoke['status'] == 'V7_KNOWN_FIXTURE_CUDA_FULL_PIPELINE_SMOKE_PASSED'
        and smoke['completed'] is True and smoke['job'] == job and smoke['neural_execution'] is True
        and smoke['native_evaluation_completed'] is True and smoke['task_generation'] is False
        and smoke['learning_accepted'] is False and smoke['prepare_exit_before_training'] is True
        and smoke['native_integration_status'] == 'COMPLETED_KNOWN_FIXTURE_ONLY'
        and type(smoke['wall_seconds']) in (int, float) and math.isfinite(smoke['wall_seconds'])
        and 0 < smoke['wall_seconds'] <= 900, 'SMOKE_COMPLETED_BOUNDARY')
    same(smoke['source_sha256'], source, 'SMOKE_SOURCE')
    evidence.baseline(smoke['baseline'], baseline, c)
    same(smoke['splits'], q.EXPECTED_SPLITS, 'SMOKE_SPLITS')
    same(smoke['optimizer_steps'], {'cas': 22, 'generic': 22}, 'SMOKE_STEPS')
    fixture = {'seed': q.SEED, 'fixture_files_sha256': q.FIXTURE_PINS,
               'source_pins_sha256': q.PINS_SHA256, 'public_loader_sha256': q.LOADER_SHA256}
    same(smoke['fixture'], fixture, 'SMOKE_KNOWN_FIXTURE')
    c.require(spec['source_pins_sha256'] == q.PINS_SHA256
              and spec['public_loader_sha256'] == q.LOADER_SHA256, 'SMOKE_REGISTERED_PINS')
    remote_smoke = prefix + smoke_base.rstrip('/')
    phase_commands = {phase: [python, '-B', '-m', 'cas_meta2.contrast_v7.gpu_preflight',
                      '--phase', phase, '--output', remote_smoke, '--job', job]
                      for phase in ('prepare', 'train', 'native')}
    processes = {}
    for phase, directory, field in (('prepare', 'prepare_process', 'prepare_process_receipt_sha256'),
        ('train', 'training_process', 'training_process_receipt_sha256'),
        ('native', 'native_process', 'native_process_receipt_sha256')):
        name = smoke_base + directory + '/process_receipt.json'
        bound(name, smoke[field])
        processes[phase] = process(name, phase_commands[phase])
    prep, trained, proc_native = (processes[name] for name in ('prepare', 'train', 'native'))
    c.require(len({outer['pid'], prep['pid'], trained['pid'], proc_native['pid']}) == 4
        and type(smoke['prepare_pid']) is int and type(smoke['training_pid']) is int
        and smoke['prepare_pid'] == prep['pid'] and smoke['training_pid'] == trained['pid']
        and stamp(outer['started_utc']) <= stamp(prep['started_utc'])
        and stamp(prep['finished_utc']) <= stamp(trained['started_utc'])
        and stamp(trained['finished_utc']) <= stamp(proc_native['started_utc'])
        and stamp(proc_native['finished_utc']) <= stamp(outer['finished_utc']), 'SMOKE_CHILD_EXIT_ORDER')

    assembly_name = smoke_base + 'assembly_receipt.json'
    bound(assembly_name, smoke['assembly_receipt_sha256'])
    assembly = doc(assembly_name)
    c.require(assembly['schema'] == q.SCHEMA and assembly['phase'] == 'prepare'
        and assembly['completed'] is True and assembly['job'] == job and assembly['pid'] == prep['pid']
        and assembly['neural_execution'] is False and assembly['task_generation'] is False
        and assembly['native_evaluation_completed'] is False
        and assembly['parent_process_must_exit_before_training'] is True
        and assembly['manifest_sha256'] == MANIFEST, 'SMOKE_ASSEMBLY_IDENTITY')
    same(assembly['source_sha256'], source, 'SMOKE_ASSEMBLY_SOURCE')
    same(assembly['fixture'], fixture, 'SMOKE_ASSEMBLY_FIXTURE')
    same(assembly['splits'], q.EXPECTED_SPLITS, 'SMOKE_ASSEMBLY_SPLITS')
    for name, pin in q.FIXTURE_PINS.items():
        bound(smoke_base + 'base_dataset/' + name, pin)
    exact_directory(smoke_base + 'base_dataset/', q.FIXTURE_PINS)
    manifest_name = smoke_base + 'dataset/manifest.json'
    bound(manifest_name, MANIFEST)
    manifest = doc(manifest_name)
    same(manifest['splits'], q.EXPECTED_SPLITS, 'SMOKE_MANIFEST_SPLITS')
    dataset_names = {'manifest.json', *manifest['sha256']}
    exact_directory(smoke_base + 'dataset/', dataset_names)
    for name, pin in manifest['sha256'].items():
        c.require(PurePosixPath(name).name == name and '\\' not in name, 'SMOKE_DATA_BASENAME')
        bound(smoke_base + 'dataset/' + name, pin)
    exact_directory(smoke_base + 'trainer_input/', q.PUBLIC_FILES)
    same(sorted(assembly['public_export_files_sha256']), sorted(q.PUBLIC_FILES), 'SMOKE_PUBLIC_EXPORT_COVERAGE')
    for name in q.PUBLIC_FILES:
        pin = MANIFEST if name == 'manifest.json' else manifest['sha256'][name]
        c.require(assembly['public_export_files_sha256'][name] == pin, 'SMOKE_PUBLIC_EXPORT_PIN')
        bound(smoke_base + 'trainer_input/' + name, pin)
    config = curriculum.Config(**q.CONFIG)
    train_config = train.TrainingConfig(epochs=1, max_seconds=900)
    training_dir = bound(smoke_base + 'training/training_receipt.json').parent
    registration = doc(smoke_base + 'training/registration.json')
    runtime = doc('cloud_job/runtime.json')
    evidence.baseline(registration['baseline'], baseline, c)
    evidence.environment(registration['environment'], runtime, c)
    gate = checks.check_training(training_dir, bound(smoke_base + 'training_process/process_receipt.json'),
        bound(smoke_base + 'trainer_input/manifest.json').parent, expected_command=phase_commands['train'], job=job,
        expected_manifest_sha256=MANIFEST, expected_loader_sha256=q.LOADER_SHA256,
        curriculum_seed=q.SEED, curriculum_config=config, excluded=frozenset(), config=train_config,
        expected_source=source, expected_baseline=registration['baseline'])
    same(gate, smoke['training_gate'], 'SMOKE_TRAINING_GATE_RECOUNT')
    c.require(gate['completed'] is True and gate['private_test_labels_opened'] is False, 'SMOKE_TRAINING_BOUNDARY')
    receipt = doc(smoke_base + 'training/training_receipt.json')
    c.require(type(receipt['completed_epochs']) is int and receipt['completed_epochs'] == 1
        and receipt['learning_accepted'] is False and receipt['seal']['test_examples'] == 9
        and receipt['seal']['prediction_count'] == 36 and receipt['seal']['private_labels_read'] is False,
        'SMOKE_ONE_EPOCH_COUNTS')
    same(receipt['optimizer_steps'], {'cas': 22, 'generic': 22}, 'SMOKE_TRAINING_STEPS')
    checkpoint_hashes = {}
    for family in ('cas', 'generic'):
        same(sorted(receipt['checkpoints'][family]), ['final', 'initial', 'selected'], 'SMOKE_CHECKPOINT_KINDS')
        for kind, epoch in (('initial', 0), ('selected', 1), ('final', 1)):
            row = receipt['checkpoints'][family][kind]
            expected_name = f'{family}_{kind}_epoch_{epoch:04d}.pt'
            c.require(row['path'] == expected_name and row['family'] == family and type(row['epoch']) is int
                and row['epoch'] == epoch and type(row['optimizer_steps']) is int and row['optimizer_steps'] == 22*epoch,
                'SMOKE_CHECKPOINT_ATTRIBUTION')
            name = smoke_base + 'training/' + expected_name
            bound(name, row['sha256'])
            c.require(type(row['bytes']) is int and row['bytes'] > 0
                and packet.inventory[name]['bytes'] == row['bytes'], 'SMOKE_CHECKPOINT_SIZE')
            checkpoint_hashes[family + '/' + kind] = row['sha256']
    saved_checkpoints = {name for name in packet.inventory if name.startswith(smoke_base + 'training/')
                         and name.endswith('.pt')}
    same(sorted(saved_checkpoints), sorted(smoke_base + 'training/' + row['path']
        for family in receipt['checkpoints'].values() for row in family.values()), 'SMOKE_EXTRA_CHECKPOINT')
    checkpoint = doc(smoke_base + 'checkpoint_verification.json')
    c.require(checkpoint['schema'] == q.SCHEMA and checkpoint['completed'] is True and checkpoint['job'] == job
        and checkpoint['manifest_sha256'] == MANIFEST, 'SMOKE_CUDA_ATTESTATION')
    same(checkpoint['source_sha256'], source, 'SMOKE_CUDA_SOURCE')
    evidence.baseline(checkpoint['baseline'], baseline, c)
    bound(smoke_base + 'training_process/process_receipt.json', checkpoint['training_process_receipt_sha256'])
    bound(smoke_base + 'training/training_receipt.json', checkpoint['training_receipt_sha256'])
    same(checkpoint['changed_weights'], smoke['changed_weights'], 'SMOKE_CHANGED_WEIGHTS_ATTRIBUTION')
    same(sorted(checkpoint['changed_weights']), ['cas', 'generic'], 'SMOKE_CHANGED_FAMILIES')
    for row in checkpoint['changed_weights'].values():
        names = row['changed_state_tensors']
        c.require(type(names) is list and names and all(type(name) is str and name for name in names)
            and names == sorted(set(names)) and type(row['changed_count']) is int
            and row['changed_count'] == len(names) and row['all_loaded_on_cuda'] is True,
            'SMOKE_CHANGED_TENSOR_RECORD')

    native_base = smoke_base + 'native_evaluation/'
    bound(native_base + 'native_receipt.json', smoke['native_receipt_sha256'])
    native_receipt = doc(native_base + 'native_receipt.json')
    same(native_receipt, smoke['native_receipt'], 'SMOKE_EMBEDDED_NATIVE_CHANGED')
    q.check_native_smoke(native_receipt)
    c.require(native_receipt['recovery_helper_manifest_sha256'] == c.RUNTIME
        and type(native_receipt['workers']) is int and native_receipt['workers'] == 8, 'SMOKE_NATIVE_HELPER_SOURCE')
    same(doc(native_base + 'training_parent_gate.json'), gate, 'SMOKE_NATIVE_TRAINING_GATE')
    seal = doc(native_base + 'predictions_seal.json')
    same(native_receipt['seal'], seal, 'SMOKE_NATIVE_SEAL')
    c.require(seal['schema'] == 'cas-meta2-contrast-evaluation-seal/7'
        and seal['manifest_sha256'] == MANIFEST and seal['test_examples'] == 9 and seal['prediction_count'] == 45
        and seal['arms'] == list(ARMS) and seal['neural_predictions_sha256'] == gate['predictions_sha256']
        and seal['parent_gate_sha256'] == c.digest(gate)
        and seal['rule_input'] == 'public problem and permitted observations only', 'SMOKE_NATIVE_SEAL_IDENTITY')
    bound(native_base + 'predictions.jsonl', seal['sha256'])
    opening = doc(native_base + 'private_opening_receipt.json')
    c.require(opening['prediction_sha256'] == seal['sha256']
        and opening['training_exit_receipt_sha256'] == gate['process_receipt_sha256']
        and opening['private_sha256'] == manifest['sha256']['test_private.json']
        and stamp(proc_native['started_utc']) <= stamp(seal['sealed_utc']) < stamp(opening['opened_utc'])
        <= stamp(proc_native['finished_utc']), 'SMOKE_PRIVATE_OPENING_ORDER')
    request_name = native_base + 'cold_validation_request.json'
    request = doc(request_name)
    request_pin = artifacts[request_name]
    expected_request = {'job': job, 'private_data': remote_smoke + '/dataset', 'expected_sha256': MANIFEST,
        'seed': q.SEED, 'config': q.CONFIG, 'excluded': [], 'pins': '/opt/cas-meta2/package/' + c.PILOT + '/' + q.PINS_PATH,
        'expected_pins_sha256': q.PINS_SHA256, 'expected_loader_sha256': q.LOADER_SHA256, 'source_sha256': source}
    same(request, expected_request, 'SMOKE_COLD_REQUEST')
    cold_command = [python, '-B', '-c', COLD_CODE, prefix + request_name, request_pin,
                    prefix + native_base + 'cold_dataset_validation.json', job]
    cold = process(native_base + 'cold_validation_process/process_receipt.json', cold_command)
    c.require(cold['pid'] != proc_native['pid']
        and stamp(opening['opened_utc']) <= stamp(cold['started_utc'])
        and stamp(cold['finished_utc']) <= stamp(proc_native['finished_utc']), 'SMOKE_COLD_EXIT_ORDER')
    cold_report = parent.validate_bundle(bound(manifest_name).parent, expected_sha256=MANIFEST,
        seed=q.SEED, config=config, excluded=frozenset(), pins=c.ROOT / q.PINS_PATH,
        expected_pins_sha256=q.PINS_SHA256, expected_loader_sha256=q.LOADER_SHA256)
    same(doc(native_base + 'cold_dataset_validation.json'), cold_report, 'SMOKE_COLD_RECOUNT')
    same(assembly['parent_validation'], cold_report, 'SMOKE_ASSEMBLY_COLD_RECOUNT')
    c.require(cold_report['completed'] is True and cold_report['prototype_tasks'] == 256
        and cold_report['prototype_pairs'] == 128 and cold_report['tokenizer_fit_examples'] == 352,
        'SMOKE_EXACT_ORIGINAL_APPEND')
    same(cold_report['splits'], q.EXPECTED_SPLITS, 'SMOKE_COLD_SPLITS')
    exported = assembly['public_export']
    same(exported['parent_validation'], cold_report, 'SMOKE_EXPORT_COLD_RECOUNT')
    same(exported['splits'], q.EXPECTED_SPLITS, 'SMOKE_EXPORT_SPLITS')
    c.require(type(exported['base_train_examples']) is int and exported['base_train_examples'] == 96
        and type(exported['imported_train_examples']) is int and exported['imported_train_examples'] == 256
        and exported['private_labels_read_by_loader'] is False and exported['test_programs_parsed_by_loader'] is False,
        'SMOKE_EXPORT_BOUNDARY')
    public = doc(smoke_base + 'dataset/test_public.json')
    tasks = doc(smoke_base + 'dataset/test_private.json')
    c.require(len(public) == len(tasks) == 9, 'SMOKE_PRIVATE_CASE_COUNT')
    same([curriculum.permitted_view(task) for task in tasks], public, 'SMOKE_PUBLIC_PRIVATE_MAPPING')
    predictions = [c.decode(line) for line in packet.raw(native_base + 'predictions.jsonl').splitlines()]
    neural = [c.decode(line) for line in packet.raw(smoke_base + 'training/neural_predictions.jsonl').splitlines()]
    c.require(len(predictions) == len(neural) == 9, 'SMOKE_PREDICTION_COUNT')
    result = doc(native_base + 'evaluation_results.json')
    helper_files = native.recovery_identity()
    worker_pids = set()
    c.require(len(result['cases']) == 9, 'SMOKE_STORED_CASE_COUNT')
    for index, (row, original, task, case) in enumerate(zip(predictions, neural, tasks, result['cases'], strict=True)):
        c.require(type(row['case_index']) is int and row['case_index'] == index
            and row['public_sha256'] == c.digest(public[index]) and type(case['case_index']) is int
            and case['case_index'] == index and case['task_id'] == task['task_id'], 'SMOKE_CASE_ATTRIBUTION')
        c.require(type(case.get('reference_verification')) is dict
            and case['reference_verification'].get('task_correct') is True, 'SMOKE_REFERENCE_VERIFICATION')
        same(row['actions'], {**original['actions'], 'rule': curriculum.parse_problem(public[index])},
             'SMOKE_RULE_OR_NEURAL_ACTION_CHANGED')
        same(sorted(row['actions']), sorted(ARMS), 'SMOKE_ALL_FIVE_ARMS')
        for arm in ARMS:
            same(case['arms'][arm]['action'], row['actions'][arm], 'SMOKE_NATIVE_ACTION_CHANGED')
        worker = doc(native_base + f'evaluation/case_{index:04d}/worker_identity.json')
        same(worker['source_sha256'], source, 'SMOKE_WORKER_SOURCE')
        same(worker['recovery_helpers_sha256'], helper_files, 'SMOKE_WORKER_HELPER_SOURCE')
        c.require(type(worker['pid']) is int and worker['pid'] > 0
            and worker['pid'] not in {outer['pid'], proc_native['pid']},
            'SMOKE_WORKER_PID')
        worker_pids.add(worker['pid'])
        evidence.baseline(worker['baseline'], baseline, c)
        evidence.environment(worker['environment'], runtime, c)
    c.require(1 <= len(worker_pids) <= 8, 'SMOKE_WORKER_POOL_BOUND')
    recounted = native.aggregate_cases(result['cases'], 9)
    grouped = native.grouped_results(result['cases'], tasks)
    same(recounted, result['results'], 'SMOKE_CASE_RECOUNT')
    same(recounted, native_receipt['results'], 'SMOKE_NATIVE_RESULT_RECOUNT')
    same(grouped, result['groups'], 'SMOKE_GROUP_RECOUNT')
    same(grouped, native_receipt['groups'], 'SMOKE_NATIVE_GROUP_RECOUNT')
    summary = {'tests': 1, 'process_pid': outer['pid'], 'smoke_path': smoke_name.removeprefix(c.BASE),
        'smoke_sha256': artifacts[smoke_name], 'native_cases': 9, 'native_arm_verdicts': 45,
        'process_receipt_sha256': artifacts[outer_name], 'tests_xml_sha256': artifacts[xml_name]}
    return {'completed': True, **summary, 'smoke_member': smoke_name, 'source_sha256': source,
        'campaign_gpu_gate': summary, 'processes': {'gpu': outer, **processes, 'cold': cold},
        'training_gate': gate, 'checkpoint_byte_hashes': checkpoint_hashes, 'artifacts_sha256': artifacts,
        'all_smoke_artifacts_sha256': {name: row['sha256'] for name, row in packet.inventory.items()
                                      if name.startswith(smoke_base)},
        'changed_weights': checkpoint['changed_weights'], 'native_results': recounted,
        'recorded_native_worker_pids': sorted(worker_pids),
        'tensor_state_independently_replayed': False, 'native_verifier_or_sqlite_independently_replayed': False,
        'fresh_evaluation': False, 'learning_accepted': False,
        'boundary': 'Authenticated stored known-fixture smoke only. Public training records and native counts/actions '
                    'recounted; checkpoint bytes and CUDA-authored changed-weight claim bound. No tensor/model loading '
                    'or execution, no new tasks, and no fresh-learning result.'}
