"""Pure byte admission for one failed packet and a separately pinned recovery."""
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import sys
import zipfile
import xml.etree.ElementTree as ET

from .core import ARMS, canonical, require

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0'
BASELINE = '0917267b1354e5d036263eaa6ba9a7197eafb776'
SOURCE_ARCHIVE = '3153318664641ea3affdbef306929c3113bb937cd04113bce41d02f736e0f1f1'
PACKET = 'db52b01670c9864da7eeecac25c36446986c6b0b625f6d1b6310bbfdcad55def'
PACKET_BYTES = 74958249
PACKET_MEMBERS = 879
ORIGINAL_JOB = 'cas-meta2-20260906064703-c0d74ffa'
EXPECTED_GPU_TESTS = ('test_saved_case_zero_uses_frozen_reference_and_verifier',
                      'test_saved_case_nine_contains_only_known_post_start_failure')
HEX = re.compile(r'[0-9a-f]{64}\Z')


def no_links(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)() for p in (path, *path.parents)),
            'RECOVERY_LINK_REFUSED')
    return path


def file_hash(path):
    path = no_links(path)
    result = sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            result.update(block)
    return result.hexdigest()


def read(path):
    path = no_links(path)
    require(path.is_file() and path.stat().st_size <= 32*1024**2, 'RECOVERY_SMALL_INPUT_BOUND')
    return path.read_bytes()


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'RECOVERY_DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('RECOVERY_NONFINITE_JSON')))
    canonical(value)
    return value


def pinned(path, pin):
    require(type(pin) is str and HEX.fullmatch(pin), 'RECOVERY_EXTERNAL_PIN_REQUIRED')
    raw = read(path)
    require(sha256(raw).hexdigest() == pin, 'RECOVERY_EXTERNAL_PIN_MISMATCH')
    return decode(raw)


def relative(root, name):
    require(type(name) is str and name and '\\' not in name and ':' not in name
            and not name.startswith('/') and all(p not in ('', '.', '..') for p in name.split('/')),
            'RECOVERY_RELATIVE_PATH')
    root = no_links(root).resolve()
    path = no_links(root/name)
    require(path.resolve().is_relative_to(root), 'RECOVERY_PATH_ESCAPE')
    return path


def extract_fixed_packet(packet, output):
    """Extract only the known original packet into a new directory; no imports."""
    packet, output = no_links(packet), no_links(output)
    require(packet.stat().st_size == PACKET_BYTES and file_hash(packet) == PACKET,
            'RECOVERY_FIXED_PACKET_IDENTITY')
    require(not output.exists() and output != output.parent and not packet.resolve().is_relative_to(output.resolve()),
            'RECOVERY_NEW_EXTRACTION_REQUIRED')
    with zipfile.ZipFile(packet) as archive:
        members = archive.infolist()
        require(len(members) == PACKET_MEMBERS and sum(info.file_size for info in members) <= 2*1024**3,
                'RECOVERY_PACKET_EXPANSION_BOUND')
        spellings, names = {},set()
        for info in members:
            relative(output,info.filename)
            require(not info.is_dir() and info.filename not in names and not info.flag_bits & 1
                    and stat.S_IFMT(info.external_attr >> 16) in (0,stat.S_IFREG),
                    'RECOVERY_PACKET_MEMBER_TYPE')
            names.add(info.filename)
            parts = info.filename.split('/')
            for index in range(1,len(parts)+1):
                name = '/'.join(parts[:index])
                folded = name.casefold()
                require(folded not in spellings or spellings[folded] == name,'RECOVERY_PACKET_CASE_ALIAS')
                spellings[folded] = name
        require(not any('/'.join(name.split('/')[:i]) in names
                        for name in names for i in range(1,len(name.split('/')))), 'RECOVERY_PACKET_FILE_DIRECTORY_ALIAS')
        output.mkdir(parents=True,exist_ok=False)
        inventory = []
        for info in members:
            path = relative(output,info.filename)
            path.parent.mkdir(parents=True,exist_ok=True)
            path = relative(output,info.filename)
            digest, count = sha256(),0
            with archive.open(info) as source, path.open('xb') as destination:
                for block in iter(lambda:source.read(1024**2),b''):
                    count += len(block)
                    require(count <= info.file_size,'RECOVERY_PACKET_MEMBER_SIZE')
                    digest.update(block)
                    destination.write(block)
            require(count == info.file_size and file_hash(path) == digest.hexdigest(), 'RECOVERY_EXTRACTED_BYTES_CHANGED')
            inventory.append({'path':info.filename,'bytes':count,'sha256':digest.hexdigest()})
    require(file_hash(packet) == PACKET,'RECOVERY_PACKET_CHANGED_DURING_EXTRACTION')
    return {'schema':'cas-meta2-contrast-recovery-extraction/6','packet_sha256':PACKET,
            'packet_bytes':PACKET_BYTES,'output':str(output),'files_verified':PACKET_MEMBERS,
            'all_member_bytes_verified_after_write':True,'inventory':inventory}


def require_request(job, enabled):
    require(enabled is True and sys.platform == 'linux', 'RECOVERY_AWS_LINUX_EXPLICIT_ENABLE_REQUIRED')
    require(type(job) is str and re.fullmatch(r'cas-meta2-[0-9]{14}-[0-9a-f]{8}', job)
            and job != ORIGINAL_JOB, 'RECOVERY_NEW_JOB_REQUIRED')
    require(os.environ.get('CAS_META2_RUN_CONTRAST_RECOVERY') == '1'
            and os.environ.get('CAS_META2_RUN_GPU_TESTS') == '1'
            and os.environ.get('CAS_META2_AWS_JOB_ID') == job
            and os.environ.get('CAS_META1_AWS_JOB_ID') == job, 'RECOVERY_AWS_JOB_ENABLE_MISMATCH')


def source_identity(admission, recovery_manifest, *, root=ROOT):
    old = admission['source_manifest']
    require(old['source_sha'] == SOURCE and old['baseline_sha'] == BASELINE, 'RECOVERY_FROZEN_SOURCE_IDENTITY')
    require(recovery_manifest['schema'] == 'cas-meta2-contrast-recovery-source/6'
            and recovery_manifest['original_source_sha'] == SOURCE
            and recovery_manifest['original_source_archive_sha256'] == SOURCE_ARCHIVE,
            'RECOVERY_SOURCE_MANIFEST_IDENTITY')
    frozen = old['files_sha256']
    require(type(frozen) is dict and frozen, 'RECOVERY_FROZEN_SOURCE_MAP')
    package_root = Path(root).resolve().parents[1]
    for name, pin in frozen.items():
        require(type(pin) is str and HEX.fullmatch(pin)
                and file_hash(relative(package_root, name)) == pin, 'RECOVERY_FROZEN_BYTES_CHANGED:'+name)
    own = recovery_manifest['files_sha256']
    expected = {p.relative_to(root).as_posix() for p in (Path(root)/'cas_meta2/contrast_recovery_v6').glob('*.py')}
    expected |= {p.relative_to(root).as_posix() for p in (Path(root)/'tests').glob('test_contrast_recovery_v6_*.py')}
    require(type(own) is dict and set(own) == expected and len(expected) >= 7, 'RECOVERY_SOURCE_CLOSURE')
    for name, pin in own.items():
        require(type(pin) is str and HEX.fullmatch(pin) and file_hash(relative(root, name)) == pin,
                'RECOVERY_CODE_BYTES_CHANGED:'+name)
    return {'frozen_source_sha': SOURCE, 'baseline_sha': BASELINE,
            'frozen_files_sha256': frozen, 'recovery_files_sha256': own}


def load_inputs(*, admission_path, admission_sha256, recovery_manifest_path,
                recovery_manifest_sha256, inputs, packet, root=ROOT):
    """No generation, program parsing, checkpoint loading, or native imports."""
    require(file_hash(packet) == PACKET, 'RECOVERY_ORIGINAL_PACKET_CHANGED')
    admission = pinned(admission_path, admission_sha256)
    require(admission['schema'] == 'cas-meta2-contrast-failure-review/6'
            and admission['status'] == 'FAILED_RUN_TRAINING_RECOUNT_PASSED'
            and admission['audit_completed'] is True and admission['training_recount_passed'] is True
            and admission['campaign_completed'] is False and admission['native_evaluation_completed'] is False
            and admission['source_sha'] == SOURCE and admission['source_archive_sha256'] == SOURCE_ARCHIVE
            and admission['packet_sha256'] == PACKET and admission['job'] == ORIGINAL_JOB
            and admission['source_and_extraction_rechecked_at_end'] is True, 'RECOVERY_INPUT_ADMISSION_REQUIRED')
    recovery_manifest = pinned(recovery_manifest_path, recovery_manifest_sha256)
    sources = source_identity(admission, recovery_manifest, root=root)
    inventory = {row['path']: row for row in admission['inventory']}
    require(len(inventory) == len(admission['inventory']), 'RECOVERY_DUPLICATE_INVENTORY')
    paths, loaded = {}, {}
    def bound(name):
        full = 'cloud_job/campaign/'+name
        path = relative(inputs, full)
        raw = read(path)
        entry = inventory[full]
        require(len(raw) == entry['bytes'] and sha256(raw).hexdigest() == entry['sha256'],
                'RECOVERY_PACKET_MEMBER_CHANGED:'+name)
        paths[full] = entry['sha256']
        loaded[name] = raw
        return decode(raw)
    manifest = bound('dataset/manifest.json')
    publics, tasks = bound('dataset/test_public.json'), bound('dataset/test_private.json')
    neural_seal = bound('training/neural_predictions_seal.json')
    native_seal = bound('native/predictions_seal.json')
    gate = bound('native/training_parent_gate.json')
    registration = bound('training/registration.json')
    training = bound('training/training_receipt.json')
    process = bound('processes/training/process_receipt.json')
    opening = bound('native/private_opening_receipt.json')
    # JSONL is read without passing a whole multi-document buffer to JSON.
    def jsonl(name):
        full = 'cloud_job/campaign/'+name
        path = relative(inputs, full)
        raw = read(path)
        entry = inventory[full]
        require(len(raw) == entry['bytes'] and sha256(raw).hexdigest() == entry['sha256'],
                'RECOVERY_PREDICTION_MEMBER_CHANGED')
        paths[full] = entry['sha256']
        loaded[name] = raw
        return [decode(line) for line in raw.splitlines()]
    neural = jsonl('training/neural_predictions.jsonl')
    predictions = jsonl('native/predictions.jsonl')
    checks = admission['binding_checks']
    bindings = {'dataset/manifest.json':'dataset_manifest_sha256', 'dataset/test_public.json':'test_public_sha256',
        'dataset/test_private.json':'test_private_sha256', 'training/neural_predictions.jsonl':'neural_predictions_sha256',
        'native/predictions.jsonl':'native_predictions_sha256', 'native/predictions_seal.json':'native_predictions_seal_sha256',
        'native/training_parent_gate.json':'native_training_parent_gate_sha256',
        'native/private_opening_receipt.json':'private_opening_receipt_sha256'}
    require(all(sha256(loaded[name]).hexdigest() == checks[field] for name, field in bindings.items())
            and checks['cases_bound'] == 72 and checks['arm_choices_bound'] == 360
            and checks['recorded_private_opening_order_checked'] is True,
            'RECOVERY_ADMISSION_MEMBER_BINDING')
    require(manifest == admission['dataset_manifest'] and gate == admission['training_gate'],
            'RECOVERY_RECOUNT_BINDING_CHANGED')
    require(training['completed'] is True and training['completed_epochs'] == 200
            and training['optimizer_steps'] == {'cas':8000, 'generic':8000}
            and process['completed'] is True and process['returncode'] == 0 and process['timed_out'] is False
            and sha256(loaded['processes/training/process_receipt.json']).hexdigest() == gate['process_receipt_sha256']
            and sha256(loaded['training/registration.json']).hexdigest() == gate['registration_sha256']
            and sha256(loaded['training/training_receipt.json']).hexdigest() == gate['training_receipt_sha256'],
            'RECOVERY_TRAINING_PROCESS_BINDING')
    require(native_seal['sha256'] == checks['native_predictions_sha256']
            and neural_seal['sha256'] == checks['neural_predictions_sha256']
            and native_seal['neural_predictions_sha256'] == neural_seal['sha256']
            and native_seal['parent_gate_sha256'] == sha256(canonical(gate)).hexdigest()
            and native_seal['arms'] == list(ARMS) and native_seal['test_examples'] == 72
            and native_seal['prediction_count'] == 360 and neural_seal['test_examples'] == 72
            and neural_seal['prediction_count'] == 288, 'RECOVERY_ORIGINAL_SEAL_CHANGED')
    require(len(publics) == len(tasks) == len(predictions) == len(neural) == 72, 'RECOVERY_FIXED_INPUT_COVERAGE')
    for index, (public, task, row, old) in enumerate(zip(publics, tasks, predictions, neural, strict=True)):
        require(task['public'] == public and type(row['case_index']) is int and row['case_index'] == index
                and row['public_sha256'] == sha256(canonical(public)).hexdigest()
                and set(row['actions']) == set(ARMS) and old['case_index'] == index
                and old['public_sha256'] == row['public_sha256']
                and {k:v for k,v in row['actions'].items() if k != 'rule'} == old['actions'],
                'RECOVERY_SEALED_CHOICE_MAPPING')
    # Every consumed byte is also matched directly to the known original ZIP.
    with zipfile.ZipFile(packet) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())), 'RECOVERY_DUPLICATE_PACKET_MEMBER')
        for name, raw in loaded.items():
            require(archive.read('cloud_job/campaign/'+name) == raw, 'RECOVERY_ARCHIVE_EXTRACT_MISMATCH')
    return {'admission': admission, 'admission_sha256': admission_sha256, 'recovery_manifest': recovery_manifest,
        'recovery_manifest_sha256': recovery_manifest_sha256, 'sources': sources, 'input_sha256': paths,
        'tasks': tasks, 'predictions': predictions, 'seal': native_seal, 'registration': registration,
        'training_process': process, 'opening': opening}


def check_gpu_gate(path, pin, *, job, recovery_manifest_sha256):
    gate = pinned(path, pin)
    require(gate['schema'] == 'cas-meta2-contrast-recovery-gpu-gate/6' and gate['completed'] is True
            and gate['job'] == job and gate['recovery_manifest_sha256'] == recovery_manifest_sha256,
            'RECOVERY_REAL_GPU_GATE_REQUIRED')
    root = Path(path).absolute().parent
    xml_path = relative(root, gate['tests_xml']['path'])
    proc_path = relative(root, gate['process_receipt']['path'])
    require(file_hash(xml_path) == gate['tests_xml']['sha256'], 'RECOVERY_GPU_XML_CHANGED')
    process = pinned(proc_path, gate['process_receipt']['sha256'])
    command = gate['expected_command']
    require(type(command) is list and command and process['command'] == command
            and 'tests/test_contrast_recovery_v6_gpu.py' in command and '-m' in command and 'pytest' in command
            and process['completed'] is True and process['returncode'] == 0 and process['timed_out'] is False
            and type(process['pid']) is int and process['pid'] > 0,
            'RECOVERY_GPU_PROCESS_FAILED')
    start = datetime.fromisoformat(process['started_utc'])
    end = datetime.fromisoformat(process['finished_utc'])
    require(start.tzinfo is not None and end.tzinfo is not None and end > start, 'RECOVERY_GPU_PROCESS_TIME')
    for stream in ('stdout','stderr'):
        log = Path(process[stream])
        if not log.is_absolute():
            log = relative(proc_path.parent, process[stream])
        require(file_hash(log) == process[stream+'_sha256'], 'RECOVERY_GPU_LOG_CHANGED')
    xml = ET.fromstring(read(xml_path))
    cases = list(xml.iter('testcase'))
    require(len(cases) == 2 and sorted(row.attrib['name'] for row in cases) == sorted(EXPECTED_GPU_TESTS)
            and all(row.attrib.get('classname','').endswith('test_contrast_recovery_v6_gpu') for row in cases)
            and not any(list(xml.iter(tag)) for tag in ('failure','error','skipped')), 'RECOVERY_GPU_TEST_COVERAGE')
    suites = list(xml.iter('testsuite'))
    require(suites and sum(int(s.attrib.get('tests','-1')) for s in suites) == 2
            and all(int(s.attrib.get(k,'-1')) == 0 for s in suites for k in ('failures','errors','skipped')),
            'RECOVERY_GPU_XML_TOTALS')
    return {'gate_sha256':pin, 'job':job, 'recovery_manifest_sha256':recovery_manifest_sha256,
            'tests':2, 'process_pid':process['pid'], 'finished_utc':process['finished_utc']}
