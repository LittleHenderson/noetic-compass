"""Closed recovery package profile. Pure byte checks, never training or provider work."""
from hashlib import sha256
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess

PILOT = 'research/CAS_META_2_COMPOSITION'
PACKAGES = ('CAS_META_2_COMPOSITION', 'CAS_META_1_LEARNED_SELECTION',
            'CASFORMER_v0_3_META_LOGIC_WIP', 'CAS_CJT_TRANSFORMER_v0_2', 'CASFORMER_v0_1')
PROFILE_NAMES = ('contrast_recovery_v6',)
ENTRYPOINT = 'cas_meta2.contrast_recovery_v6'
SPEC_PATH = PILOT+'/EXPERIMENT_RECOVERY_V6.json'
ORIGINAL_SOURCE = 'acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0'
ORIGINAL_ARCHIVE = '3153318664641ea3affdbef306929c3113bb937cd04113bce41d02f736e0f1f1'
ORIGINAL_JOB = 'cas-meta2-20260906064703-c0d74ffa'
BASELINE_SHA = '0917267b1354e5d036263eaa6ba9a7197eafb776'
ADMISSION_PATH = PILOT+'/records/contrast_failure_review_v6_001/run_002/failure_review_receipt.json'
ADMISSION_SHA256 = 'd479c90f711d417f2f585b87a0b746e250db8db12029df1586a4fbabf3b82420'
SOURCE_MANIFEST_PATH = PILOT+'/cas_meta2/contrast_recovery_v6/source_manifest.json'
PACKET_SHA256 = 'db52b01670c9864da7eeecac25c36446986c6b0b625f6d1b6310bbfdcad55def'
PACKET_BYTES = 74958249
RECOVERY_SOURCE_FILES = (
    'cas_meta2/contrast_recovery_v6/__init__.py', 'cas_meta2/contrast_recovery_v6/binding.py',
    'cas_meta2/contrast_recovery_v6/core.py', 'cas_meta2/contrast_recovery_v6/runtime.py',
    'cas_meta2/contrast_recovery_v6/__main__.py', 'tests/test_contrast_recovery_v6_core.py',
    'tests/test_contrast_recovery_v6_binding.py', 'tests/test_contrast_recovery_v6_gpu.py',
)
RECOVERY_LOCAL_FILES = RECOVERY_SOURCE_FILES + (
    'cas_meta2/contrast_recovery_v6/source_manifest.json', 'aws/launch_recovery_v6.py',
    'aws/launch_recovery_v6_plan.json', 'aws/recovery_remote_v6.py',
    'tests/test_launch_recovery_v6.py', 'tests/test_recovery_remote_v6.py',
    'tools/experiment_profiles_recovery_v6.py', 'tools/build_launch_bundle_recovery_v6.py',
    'EXPERIMENT_RECOVERY_V6.json', 'tests/test_recovery_v6_profile.py',
    'records/contrast_failure_review_v6_001/run_002/failure_review_receipt.json',
)
EXPANDED_LIMIT = 512*1024**2
SHA256 = re.compile(r'[a-f0-9]{64}\Z')
FIXED_SPEC = json.loads("{\"schema\":\"cas-meta2-contrast-recovery-experiment/6\",\"profile\":\"contrast_recovery_v6\",\"entrypoint\":\"cas_meta2.contrast_recovery_v6\",\"purpose\":\"REPLAY_EXISTING_SEALED_ACTIONS_AFTER_FAILED_NATIVE_EVALUATION\",\"original_job\":\"cas-meta2-20260906064703-c0d74ffa\",\"original_source_sha\":\"acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0\",\"original_source_archive_sha256\":\"3153318664641ea3affdbef306929c3113bb937cd04113bce41d02f736e0f1f1\",\"failure_admission_sha256\":\"d479c90f711d417f2f585b87a0b746e250db8db12029df1586a4fbabf3b82420\",\"packet_sha256\":\"db52b01670c9864da7eeecac25c36446986c6b0b625f6d1b6310bbfdcad55def\",\"packet_bytes\":74958249,\"packet_in_source_archive\":false,\"test_count\":72,\"matched_test_triplets\":24,\"reference_count\":72,\"arm_verdict_count\":360,\"arms\":[\"cas_untrained\",\"cas_trained\",\"generic_untrained\",\"generic_trained\",\"rule\"],\"gpu_gate_max_seconds\":300,\"native_max_seconds\":2400,\"max_wall_seconds\":3000,\"training_permitted\":false,\"task_generation_permitted\":false,\"prediction_generation_permitted\":false,\"prediction_resealing_permitted\":false,\"already_exposed_holdout\":true,\"automatic_retry\":false,\"automatic_promotion\":false,\"source_release_accepted\":false,\"unchanged_executor\":true,\"unchanged_verifier\":true}")


def require(value, code):
    if not value:
        raise ValueError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def decode(raw):
    require(type(raw) is bytes and 0 < len(raw) <= 8*1024**2, 'PROFILE_JSON_SIZE_BOUND')
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'DUPLICATE_PROFILE_JSON_FIELD')
            value[key] = item
        return value
    value = json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE_PROFILE_JSON')))
    canonical(value)
    return value


def safe_name(name):
    require(type(name) is str and '\\' not in name and ':' not in name and not name.startswith('/')
            and all(p not in ('', '.', '..') for p in name.split('/')), 'UNSAFE_SOURCE_PATH')
    parts = PurePosixPath(name).parts
    require(len(parts) >= 3 and parts[0] == 'research' and parts[1] in PACKAGES, 'UNEXPECTED_SOURCE_PACKAGE')
    return name


def validate_profile_name(profile):
    require(type(profile) is str and profile in PROFILE_NAMES, 'EXPERIMENT_PROFILE_NOT_ALLOWLISTED')
    return profile


def validate_recovery_spec(raw):
    value = decode(raw)
    require(canonical(value) == canonical(FIXED_SPEC), 'EXPERIMENT_SPEC_IDENTITY_MISMATCH')
    return value


def frozen_inputs(raw):
    require(sha256(raw).hexdigest() == ADMISSION_SHA256, 'PINNED_FAILURE_ADMISSION_CHANGED')
    admission = decode(raw)
    require(admission.get('schema') == 'cas-meta2-contrast-failure-review/6'
        and admission.get('status') == 'FAILED_RUN_TRAINING_RECOUNT_PASSED'
        and admission.get('job') == ORIGINAL_JOB and admission.get('source_sha') == ORIGINAL_SOURCE
        and admission.get('source_archive_sha256') == ORIGINAL_ARCHIVE
        and admission.get('packet_sha256') == PACKET_SHA256 and admission.get('packet_bytes') == PACKET_BYTES
        and admission.get('audit_completed') is True and admission.get('training_recount_passed') is True
        and admission.get('campaign_completed') is False and admission.get('native_evaluation_completed') is False
        and admission.get('source_and_extraction_rechecked_at_end') is True
        and admission.get('source_files_verified') == 538 and admission.get('protected_files_verified') == 316,
        'FAILED_ADMISSION_IDENTITY')
    source = admission['source_manifest']
    require(source['source_sha'] == ORIGINAL_SOURCE and source['baseline_sha'] == BASELINE_SHA
            and source['protected_baseline_files'] == 316, 'ORIGINAL_SOURCE_MANIFEST_IDENTITY')
    mapping = source['files_sha256']
    require(type(mapping) is dict and len(mapping) == 538 and all(
        safe_name(name) and type(pin) is str and SHA256.fullmatch(pin) for name, pin in mapping.items()),
        'ORIGINAL_538_SOURCE_REQUIRED')
    require(not set(mapping).intersection(PILOT+'/'+name for name in RECOVERY_LOCAL_FILES), 'RECOVERY_ORIGINAL_SOURCE_COLLISION')
    return mapping


def allowlist(admission_raw):
    return set(frozen_inputs(admission_raw)) | {PILOT+'/'+name for name in RECOVERY_LOCAL_FILES}


def check_runtime_source(raw, mapping):
    source = decode(raw)
    require(source.get('schema') == 'cas-meta2-contrast-recovery-source/6'
            and source.get('original_source_sha') == ORIGINAL_SOURCE
            and source.get('original_source_archive_sha256') == ORIGINAL_ARCHIVE, 'RECOVERY_SOURCE_MANIFEST_IDENTITY')
    own = source.get('files_sha256')
    require(type(own) is dict and set(own) == set(RECOVERY_SOURCE_FILES)
        and all(type(pin) is str and SHA256.fullmatch(pin) and mapping.get(PILOT+'/'+name) == pin
                for name, pin in own.items()), 'RECOVERY_RUNTIME_SOURCE_CLOSURE')
    return source


def recovery_record(mapping):
    return {'original_source_sha': ORIGINAL_SOURCE, 'original_source_archive_sha256': ORIGINAL_ARCHIVE,
        'original_job': ORIGINAL_JOB, 'admission_path': ADMISSION_PATH, 'admission_sha256': ADMISSION_SHA256,
        'source_manifest_path': SOURCE_MANIFEST_PATH, 'source_manifest_sha256': mapping[SOURCE_MANIFEST_PATH],
        'packet_sha256': PACKET_SHA256, 'packet_bytes': PACKET_BYTES, 'packet_in_source_archive': False}


def make_record(members, profile='contrast_recovery_v6'):
    validate_profile_name(profile)
    require(ADMISSION_PATH in members, 'COMMITTED_FAILURE_ADMISSION_MISSING')
    frozen = frozen_inputs(members[ADMISSION_PATH])
    required = set(frozen) | {PILOT+'/'+name for name in RECOVERY_LOCAL_FILES}
    require(set(members) == required and len(required) == 557, 'EXACT_RECOVERY_SOURCE_ALLOWLIST_REQUIRED')
    mapping = {name: sha256(raw).hexdigest() for name, raw in members.items()}
    require(all(mapping[name] == pin for name, pin in frozen.items()), 'ORIGINAL_FROZEN_SOURCE_CHANGED')
    validate_recovery_spec(members[SPEC_PATH])
    check_runtime_source(members[SOURCE_MANIFEST_PATH], mapping)
    return {'profile': PROFILE_NAMES[0], 'entrypoint': ENTRYPOINT, 'spec_path': SPEC_PATH,
            'spec_sha256': mapping[SPEC_PATH]}


def validate_manifest(manifest, read_member=None):
    require(type(manifest) is dict, 'RECOVERY_MANIFEST_REQUIRED')
    record, mapping = manifest.get('experiment'), manifest.get('files_sha256')
    require(type(record) is dict and set(record) == {'profile', 'entrypoint', 'spec_path', 'spec_sha256'}
        and record['profile'] == PROFILE_NAMES[0] and record['entrypoint'] == ENTRYPOINT
        and record['spec_path'] == SPEC_PATH and type(record['spec_sha256']) is str
        and SHA256.fullmatch(record['spec_sha256']), 'RECOVERY_EXPERIMENT_IDENTITY')
    require(type(mapping) is dict and len(mapping) == 557
        and all(PILOT+'/'+name in mapping for name in RECOVERY_LOCAL_FILES)
        and all(safe_name(name) and type(pin) is str and SHA256.fullmatch(pin) for name, pin in mapping.items()),
        'RECOVERY_MANIFEST_SOURCE_CLOSURE')
    require(mapping[SPEC_PATH] == record['spec_sha256'] and mapping[ADMISSION_PATH] == ADMISSION_SHA256,
            'RECOVERY_MANIFEST_PIN_CHANGED')
    require(manifest.get('recovery') == recovery_record(mapping), 'RECOVERY_BINDING_RECORD_CHANGED')
    require(manifest.get('external_packet') == {'sha256': PACKET_SHA256, 'bytes': PACKET_BYTES},
            'RECOVERY_EXTERNAL_PACKET_CHANGED')
    if read_member is not None:
        raw = read_member(ADMISSION_PATH)
        frozen = frozen_inputs(raw)
        require(set(mapping) == set(frozen) | {PILOT+'/'+name for name in RECOVERY_LOCAL_FILES}
                and all(mapping[name] == pin for name, pin in frozen.items()), 'ORIGINAL_FROZEN_SOURCE_CHANGED')
        for name in (SPEC_PATH, SOURCE_MANIFEST_PATH):
            raw = read_member(name)
            require(sha256(raw).hexdigest() == mapping[name], 'RECOVERY_MANIFEST_MEMBER_CHANGED')
            if name == SPEC_PATH:
                validate_recovery_spec(raw)
            else:
                check_runtime_source(raw, mapping)
    return dict(record)


def entrypoint(manifest):
    return validate_manifest(manifest)['entrypoint']


def git_context(root):
    root = Path(root).resolve()
    repo = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=root, text=True).strip()).resolve()
    return repo, root.parent.relative_to(repo).as_posix()+'/'


def git_members(repo, prefix, source_sha):
    require(type(source_sha) is str and re.fullmatch('[a-f0-9]{40}', source_sha), 'EXACT_SOURCE_SHA_REQUIRED')
    require(subprocess.check_output(['git', 'rev-parse', source_sha+'^{commit}'], cwd=repo,
                                    text=True).strip() == source_sha, 'EXACT_SOURCE_COMMIT_REQUIRED')
    admission = subprocess.check_output(['git', 'cat-file', 'blob',
        source_sha+':'+prefix+ADMISSION_PATH.removeprefix('research/')], cwd=repo)
    required = allowlist(admission)
    # Archive the five packages once, then use the exact closed allowlist.
    # No other current research, records, checkpoints or packet bytes are included.
    raw = subprocess.check_output(['git', '-c', 'core.autocrlf=false', 'archive', '--format=zip',
                                  source_sha, '--', *(prefix+name for name in PACKAGES)], cwd=repo)
    members, aliases, total = {}, set(), 0
    with __import__('zipfile').ZipFile(io.BytesIO(raw)) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            require(info.filename.startswith(prefix), 'GIT_ARCHIVE_PREFIX_CHANGED')
            name = 'research/'+info.filename[len(prefix):]
            if name not in required:
                continue
            safe_name(name)
            mode = info.external_attr >> 16
            require(name.casefold() not in aliases and not stat.S_ISLNK(mode), 'GIT_LINK_OR_DUPLICATE_SOURCE')
            aliases.add(name.casefold())
            total += info.file_size
            require(total <= EXPANDED_LIMIT, 'SOURCE_EXPANDED_SIZE_CEILING')
            members[name] = archive.read(info)
    require(set(members) == required, 'REQUIRED_RECOVERY_INPUT_NOT_COMMITTED')
    return members

