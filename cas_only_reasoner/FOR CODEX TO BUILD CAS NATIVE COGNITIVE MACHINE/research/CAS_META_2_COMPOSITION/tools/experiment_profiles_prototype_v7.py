"""V7 preparation and exact-source launch profile. Paid execution stays gated."""
from hashlib import sha256
import json
import re
import io
from pathlib import Path, PurePosixPath
import stat
import subprocess

PILOT = 'research/CAS_META_2_COMPOSITION'
PROFILE_NAMES = ('prototype_training_v7',)
ENTRYPOINT = 'cas_meta2.contrast_v7.campaign'
SPEC_PATH = PILOT+'/EXPERIMENT_PROTOTYPE_V7.json'
FIXED_SPEC = json.loads("{\"schema\":\"cas-meta2-prototype-experiment/7\",\"profile\":\"prototype_training_v7\",\"entrypoint\":\"cas_meta2.contrast_v7.campaign\",\"registration_state\":\"PREPARATION_ONLY_GPU_AND_EVALUATION_GATES_PENDING\",\"purpose\":\"TRAIN_WITH_EXACT_ORIGINAL_256_PLUS_FRESH_BASE_CURRICULUM\",\"curriculum_seed\":2026092701,\"curriculum\":{\"train_flat\":128,\"train_pairs_per_cell\":64,\"validation_flat\":32,\"validation_pairs_per_cell\":8,\"test_triplets\":24},\"training\":{\"seed\":7,\"epochs\":200,\"batch_size\":16,\"prediction_batch_size\":16,\"validation_interval\":10,\"max_seconds\":3600},\"base_train_count\":640,\"original_train_append_count\":256,\"train_count\":896,\"validation_count\":96,\"test_count\":72,\"matched_test_triplets\":24,\"train_depths\":{\"1\":128,\"2\":384,\"3\":384},\"validation_depths\":{\"1\":32,\"2\":32,\"3\":32},\"test_depths\":{\"3\":48,\"4\":24},\"optimizer_steps_per_family\":11200,\"exclusion_inventory_path\":\"records/contrast_v7_exclusions_from_failed_v6_001/inventory.json\",\"exclusion_inventory_sha256\":\"9f579ea2d593671dfddf16db39aa22563d6b98f7388758d2a2b99539e66ed623\",\"exclusion_count\":8837,\"source_pins_path\":\"records/contrast_v7_bridge_checks_001/source_pins.json\",\"source_pins_sha256\":\"9d66a81fbdc0e4041cd09d460c821f3cf68e244610ed49831324b5accf74084d\",\"public_loader_path\":\"records/prototype_training_integration_v7_001/public_data.py\",\"public_loader_sha256\":\"5db831d685b2343a16b93cbc3d3c16e53978ebf0e3cf9da8fefd7d10692708b0\",\"original_tasks_path\":\"records/contrast_curriculum_v6_probe_001/tasks.json\",\"original_tasks_sha256\":\"ed6bb0978d34b549917e1ea1b846091f103577936f846bc01db152b19ddbac46\",\"original_tasks_training_only\":true,\"original_graphs_remain_in_fresh_exclusions\":true,\"gpu_gate\":{\"status\":\"PENDING_PRODUCTION_V7_PIPELINE_SMOKE\",\"test_file\":null,\"expected_tests\":null},\"native_evaluation\":{\"status\":\"PENDING_VALIDATED_RECOVERY_WORKER\",\"entrypoint\":null},\"execution_enabled\":false,\"training_permitted\":false,\"local_fresh_data_generation\":false,\"local_neural_execution\":false,\"private_test_labels_in_trainer\":false,\"selection\":\"unchanged_validation_only_depth_selection_v3\",\"policies\":\"unchanged_v3\",\"loss\":\"unchanged_v3\",\"optimizer\":\"unchanged_v3\",\"decoder\":\"unchanged_v3\",\"arms\":[\"cas_untrained\",\"cas_trained\",\"generic_untrained\",\"generic_trained\",\"rule\"],\"automatic_retry\":false,\"automatic_promotion\":false,\"source_release_accepted\":false}")
SOURCE_PINS_PATH = PILOT+'/'+FIXED_SPEC['source_pins_path']
SOURCE_PINS_SHA256 = FIXED_SPEC['source_pins_sha256']
EXTRA_INPUTS = {
    SOURCE_PINS_PATH: SOURCE_PINS_SHA256,
    PILOT+'/'+FIXED_SPEC['exclusion_inventory_path']: FIXED_SPEC['exclusion_inventory_sha256'],
    PILOT+'/'+FIXED_SPEC['public_loader_path']: FIXED_SPEC['public_loader_sha256'],
    PILOT+'/'+FIXED_SPEC['original_tasks_path']: FIXED_SPEC['original_tasks_sha256'],
    PILOT+'/records/prototype_training_integration_v7_001/adapter.py':
        'cef0faa3f659ceb227cf39e12cf0c1ccdd0d6f9043bd732df8dfbcf85a1ff731',
    PILOT+'/records/contrast_v6_exclusions_001/inventory.json':
        '1a8f7f39bee35f14ef002dfe90f2c6760cbe5c70436c7606fad32ee03f4c1256',
}
V7_LOCAL_FILES = (
    'cas_meta2/contrast_v7/__init__.py', 'cas_meta2/contrast_v7/data.py',
    'cas_meta2/contrast_v7/parent.py', 'cas_meta2/contrast_v7/train.py',
    'cas_meta2/contrast_v7/checks.py', 'cas_meta2/contrast_v7/evaluation.py',
    'cas_meta2/contrast_v7/campaign.py', 'EXPERIMENT_PROTOTYPE_V7.json',
    'tools/experiment_profiles_prototype_v7.py', 'tests/test_contrast_v7_bridge.py',
    'tests/test_contrast_v7_campaign.py',
)
PENDING = ('V7_PRODUCTION_GPU_GATE_PENDING', 'V7_NATIVE_EVALUATOR_PENDING_RECOVERY_VALIDATION')


def require(value, code):
    if not value:
        raise ValueError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def decode(raw):
    require(type(raw) is bytes and 0 < len(raw) <= 4*1024**2, 'PROTOTYPE_PROFILE_JSON_BOUND')
    def pairs(items):
        result = {}
        for name, value in items:
            require(name not in result, 'DUPLICATE_PROFILE_JSON_KEY')
            result[name] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE_PROFILE_JSON')))
    canonical(value)
    return value


def validate_profile_name(profile):
    require(type(profile) is str and profile in PROFILE_NAMES, 'EXPERIMENT_PROFILE_NOT_ALLOWLISTED')
    return profile


def validate_prototype_spec(raw):
    value = decode(raw)
    require(canonical(value) == canonical(FIXED_SPEC) or (REGISTERED_SPEC is not None
        and canonical(value) == canonical(REGISTERED_SPEC)), 'PROTOTYPE_SPEC_IDENTITY_MISMATCH')
    return value


def execution_blockers(spec):
    validate_prototype_spec(canonical(spec))
    if REGISTERED_SPEC is None or canonical(spec) != canonical(REGISTERED_SPEC):
        return list(PENDING)
    require(PREREQUISITE_REVIEW_PATH and PREREQUISITE_REVIEW_SHA256
        and spec['prerequisite_recovery']['review_path'] == PREREQUISITE_REVIEW_PATH.removeprefix(PILOT+'/')
        and spec['prerequisite_recovery']['review_sha256'] == PREREQUISITE_REVIEW_SHA256,
        'V7_LITERAL_PREREQUISITE_REVIEW_REQUIRED')
    return []


def require_execution_ready(spec):
    blockers = execution_blockers(spec)
    require(not blockers and spec['execution_enabled'] is True and spec['training_permitted'] is True,
            'V7_PREPARATION_ONLY:'+','.join(blockers))


def pinned_source_map(raw):
    require(sha256(raw).hexdigest() == SOURCE_PINS_SHA256, 'V7_SOURCE_PINS_CHANGED')
    value = decode(raw)
    require(value.get('frozen_source_sha') == 'acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0'
        and value.get('adapter_schema') == 'cas-meta2-prototype-training-integration/7'
        and value.get('adapter_sha256') == EXTRA_INPUTS[PILOT+'/records/prototype_training_integration_v7_001/adapter.py'],
        'V7_PINNED_SOURCE_IDENTITY')
    mapping = value['frozen_files_sha256']
    require(type(mapping) is dict and len(mapping) == 16, 'V7_PINNED_SOURCE_CLOSURE')
    for name, pin in mapping.items():
        require(type(name) is str and not name.startswith('/') and '\\' not in name and ':' not in name
            and all(part not in ('', '.', '..') for part in name.split('/'))
            and type(pin) is str and re.fullmatch('[a-f0-9]{64}', pin), 'V7_PINNED_SOURCE_PATH')
    return {PILOT+'/'+name: pin for name, pin in mapping.items()}


def make_record(members, profile='prototype_training_v7'):
    validate_profile_name(profile)
    require(SOURCE_PINS_PATH in members, 'V7_SOURCE_PINS_MISSING')
    pins = {**pinned_source_map(members[SOURCE_PINS_PATH]), **EXTRA_INPUTS}
    require(all(PILOT+'/'+name in members for name in V7_LOCAL_FILES)
            and all(name in members for name in pins), 'V7_PREPARATION_SOURCE_MISSING')
    require(all(sha256(members[name]).hexdigest() == pin for name, pin in pins.items()), 'V7_PREPARATION_INPUT_CHANGED')
    validate_prototype_spec(members[SPEC_PATH])
    return {'profile': PROFILE_NAMES[0], 'entrypoint': ENTRYPOINT,
            'spec_path': SPEC_PATH, 'spec_sha256': sha256(members[SPEC_PATH]).hexdigest()}


def validate_manifest(manifest, read_member=None):
    record, mapping = manifest.get('experiment'), manifest.get('files_sha256', {})
    require(type(record) is dict and set(record) == {'profile','entrypoint','spec_path','spec_sha256'}
        and record['profile'] == PROFILE_NAMES[0] and record['entrypoint'] == ENTRYPOINT
        and record['spec_path'] == SPEC_PATH and type(record['spec_sha256']) is str
        and re.fullmatch('[a-f0-9]{64}', record['spec_sha256']), 'V7_PREPARATION_MANIFEST_IDENTITY')
    require(type(mapping) is dict and all(PILOT+'/'+name in mapping for name in V7_LOCAL_FILES)
        and all(mapping.get(name) == pin for name, pin in EXTRA_INPUTS.items())
        and mapping.get(SPEC_PATH) == record['spec_sha256'], 'V7_PREPARATION_MANIFEST_PINS')
    if read_member is not None:
        pins = pinned_source_map(read_member(SOURCE_PINS_PATH))
        require(all(mapping.get(name) == pin for name, pin in pins.items()), 'V7_PREPARATION_SOURCE_MAP_CHANGED')
        for name, pin in {**pins, **EXTRA_INPUTS, SPEC_PATH: record['spec_sha256']}.items():
            require(sha256(read_member(name)).hexdigest() == pin, 'V7_PREPARATION_MEMBER_CHANGED')
        validate_prototype_spec(read_member(SPEC_PATH))
    return dict(record)


def entrypoint(manifest):
    validate_manifest(manifest)
    require_execution_ready(FIXED_SPEC)
    return ENTRYPOINT



# Only a later reviewed source edit may fill this exact registered specification.
# Never derive readiness, source pins, or approval from a supplied packet itself.
REGISTERED_SPEC = None
PREREQUISITE_REVIEW_PATH = None
PREREQUISITE_REVIEW_SHA256 = None
PACKAGES = ('CAS_META_2_COMPOSITION','CAS_META_1_LEARNED_SELECTION',
    'CASFORMER_v0_3_META_LOGIC_WIP','CAS_CJT_TRANSFORMER_v0_2','CASFORMER_v0_1')
EXPANDED_LIMIT = 512*1024**2
SHA256 = re.compile(r'[a-f0-9]{64}\Z')
ORIGINAL_SOURCE = 'acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0'
ORIGINAL_ARCHIVE = '3153318664641ea3affdbef306929c3113bb937cd04113bce41d02f736e0f1f1'
ORIGINAL_JOB = 'cas-meta2-20260906064703-c0d74ffa'
BASELINE_SHA = '0917267b1354e5d036263eaa6ba9a7197eafb776'
ADMISSION_PATH = PILOT+'/records/contrast_failure_review_v6_001/run_002/failure_review_receipt.json'
ADMISSION_SHA256 = 'd479c90f711d417f2f585b87a0b746e250db8db12029df1586a4fbabf3b82420'
PACKET_SHA256 = 'db52b01670c9864da7eeecac25c36446986c6b0b625f6d1b6310bbfdcad55def'
PACKET_BYTES = 74958249
SOURCE_MANIFEST_PATH = PILOT+'/cas_meta2/contrast_recovery_v6/source_manifest.json'
RECOVERY_MANIFEST_SHA256 = '897c6a72c7411676c4ad80ac9734b3dbe7a7ac169951f58d2ab2fd6d387ecb37'
RECOVERY_SOURCE_FILES = (
    'cas_meta2/contrast_recovery_v6/__init__.py','cas_meta2/contrast_recovery_v6/binding.py',
    'cas_meta2/contrast_recovery_v6/core.py','cas_meta2/contrast_recovery_v6/runtime.py',
    'cas_meta2/contrast_recovery_v6/__main__.py','tests/test_contrast_recovery_v6_core.py',
    'tests/test_contrast_recovery_v6_binding.py','tests/test_contrast_recovery_v6_gpu.py')
LAUNCH_LOCAL_FILES = tuple(sorted(set(V7_LOCAL_FILES) | set(RECOVERY_SOURCE_FILES) | {
    'cas_meta2/contrast_recovery_v6/source_manifest.json',
    'cas_meta2/contrast_v7/native_evaluation.py','cas_meta2/contrast_v7/gpu_preflight.py',
    'tests/test_contrast_v7_native.py','tests/test_contrast_v7_train_gpu.py','tests/test_contrast_v7_gpu_preflight.py',
    'tests/test_contrast_v7_cold_child.py','tests/test_contrast_v7_orchestration.py',
    'tests/test_contrast_v7_smoke_private.py',
    'EXPERIMENT_PROTOCOL_PROTOTYPE_V7.md',
    'tools/build_launch_bundle_prototype_v7.py','aws/launch_prototype_v7.py','aws/launch_prototype_v7_plan.json',
    'aws/prototype_remote_v7.py','tests/test_prototype_v7_profile.py','tests/test_prototype_v7_launcher.py',
    'tests/test_prototype_v7_remote.py'}))
FIXTURE_PINS = {
    'manifest.json':'36e57983fd43ac9650e5946d5fd04ca0888e9013131fc450f8d9f8f3c84131a1',
    'train.json':'e9032b27ac10364120e7eb7a8844eb43da40985a42cc6ab0629c88f874ae8a17',
    'validation.json':'26869a0c61007185e9fb76445297b2b231ff107ff15ad9a37fd7288bc855549d',
    'test_public.json':'cfec9cdbd9519887b9b08b7349d0bc264d1b327bb1efc89d9325eb7a57535e6a',
    'test_private.json':'8c62b9d591fd5f1ad6c8d2ed598315f91b9183d2e480709a0f12241ba0b49fff'}
BASE_SOURCE_FILE_COUNT = 602
TEST_ASSET_PINS = {
    PILOT+'/records/contrast_v7_cold_child_review_001/probe.py':'1f81e7c8114c47769ddd3cb8e4ad68ba121d6a85e3b584fc1f0a898ea167d404',
    PILOT+'/records/contrast_v7_cold_child_review_001/sitecustomize.py':'3769301876e3dd934ee79f32d3e92acacaafd2e724e7f66dc0e8b2754604a8b0',
    PILOT+'/records/prototype_training_integration_v7_001/checks_002/positive_merge/bundle/base_train.json':'e9032b27ac10364120e7eb7a8844eb43da40985a42cc6ab0629c88f874ae8a17',
    PILOT+'/records/prototype_training_integration_v7_001/checks_002/positive_merge/bundle/base_manifest.json':'36e57983fd43ac9650e5946d5fd04ca0888e9013131fc450f8d9f8f3c84131a1',
    PILOT+'/records/prototype_training_integration_v7_001/checks_002/positive_merge/bundle/manifest.json':'19162857679b3eb2e698c58ee8e0ac5dc3c7ffe7265e11e8ae1c726834067f29',
    PILOT+'/records/prototype_training_integration_v7_001/checks_002/positive_merge/bundle/train.json':'c11401b67157d6863ebf1875da086deb3891bcbf2e3d261a9236c70dda8c9729',
    PILOT+'/records/prototype_training_integration_v7_001/checks_002/positive_merge/bundle/validation.json':'26869a0c61007185e9fb76445297b2b231ff107ff15ad9a37fd7288bc855549d',
    PILOT+'/records/prototype_training_integration_v7_001/checks_002/positive_merge/bundle/test_public.json':'cfec9cdbd9519887b9b08b7349d0bc264d1b327bb1efc89d9325eb7a57535e6a',
    PILOT+'/records/prototype_training_integration_v7_001/checks_002/positive_merge/bundle/training_imports.json':'679c13f5aa4ee3e663f15fe3d799c6c9221a8e7e52867016f61d6c5085da54f9',
    PILOT+'/records/prototype_training_integration_v7_001/checks_002/positive_merge/bundle/tokenizer.json':'3c2c2d0d9e5b19b62873238efcc71eeaa9d9927b52ac7757d81ae3a64ccf8e5a',
    PILOT+'/records/prototype_training_integration_v7_001/checks_002/positive_merge/bundle/test_private.json':'8c62b9d591fd5f1ad6c8d2ed598315f91b9183d2e480709a0f12241ba0b49fff',
    PILOT+'/records/contrast_v7_bridge_checks_001/roundtrip/trainer_input/base_train.json':'e9032b27ac10364120e7eb7a8844eb43da40985a42cc6ab0629c88f874ae8a17',
    PILOT+'/records/contrast_v7_bridge_checks_001/roundtrip/trainer_input/base_manifest.json':'36e57983fd43ac9650e5946d5fd04ca0888e9013131fc450f8d9f8f3c84131a1',
    PILOT+'/records/contrast_v7_bridge_checks_001/roundtrip/trainer_input/manifest.json':'19162857679b3eb2e698c58ee8e0ac5dc3c7ffe7265e11e8ae1c726834067f29',
    PILOT+'/records/contrast_v7_bridge_checks_001/roundtrip/trainer_input/train.json':'c11401b67157d6863ebf1875da086deb3891bcbf2e3d261a9236c70dda8c9729',
    PILOT+'/records/contrast_v7_bridge_checks_001/roundtrip/trainer_input/validation.json':'26869a0c61007185e9fb76445297b2b231ff107ff15ad9a37fd7288bc855549d',
    PILOT+'/records/contrast_v7_bridge_checks_001/roundtrip/trainer_input/test_public.json':'cfec9cdbd9519887b9b08b7349d0bc264d1b327bb1efc89d9325eb7a57535e6a',
    PILOT+'/records/contrast_v7_bridge_checks_001/roundtrip/trainer_input/training_imports.json':'679c13f5aa4ee3e663f15fe3d799c6c9221a8e7e52867016f61d6c5085da54f9',
    PILOT+'/records/contrast_v7_bridge_checks_001/roundtrip/trainer_input/tokenizer.json':'3c2c2d0d9e5b19b62873238efcc71eeaa9d9927b52ac7757d81ae3a64ccf8e5a',
}
LAUNCH_PINS = {**EXTRA_INPUTS,**TEST_ASSET_PINS,ADMISSION_PATH:ADMISSION_SHA256,SOURCE_MANIFEST_PATH:RECOVERY_MANIFEST_SHA256,
    PILOT+'/tests/test_contrast_v7_cold_child.py':'df8938fa4c9c3ed5c8bcc09ad322fcbfe8c269e2c8637fe18b13ab23b35efae2',
    **{PILOT+'/records/contrast_v6_bundle_probe_001/dataset/'+name:pin for name,pin in FIXTURE_PINS.items()}}

def safe_name(name):
    require(type(name) is str and '\\' not in name and ':' not in name and not name.startswith('/')
            and all(p not in ('', '.', '..') for p in name.split('/')), 'UNSAFE_SOURCE_PATH')
    parts = PurePosixPath(name).parts
    require(len(parts) >= 3 and parts[0] == 'research' and parts[1] in PACKAGES, 'UNEXPECTED_SOURCE_PACKAGE')
    return name


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
    return mapping


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



def launch_pins(source_pins_raw):
    result = {**pinned_source_map(source_pins_raw), **LAUNCH_PINS}
    if PREREQUISITE_REVIEW_PATH is not None:
        safe_name(PREREQUISITE_REVIEW_PATH)
        require(type(PREREQUISITE_REVIEW_SHA256) is str and SHA256.fullmatch(PREREQUISITE_REVIEW_SHA256),
            'V7_PREREQUISITE_REVIEW_PIN_REQUIRED')
        result[PREREQUISITE_REVIEW_PATH] = PREREQUISITE_REVIEW_SHA256
    return result


def launch_allowlist(admission_raw, source_pins_raw):
    return set(frozen_inputs(admission_raw)) | set(launch_pins(source_pins_raw)) | {
        PILOT+'/'+name for name in LAUNCH_LOCAL_FILES}


def make_launch_record(members, profile='prototype_training_v7'):
    validate_profile_name(profile)
    require(ADMISSION_PATH in members and SOURCE_PINS_PATH in members,'V7_SOURCE_ADMISSION_MISSING')
    frozen = frozen_inputs(members[ADMISSION_PATH])
    pins = launch_pins(members[SOURCE_PINS_PATH])
    require(all(name not in frozen or frozen[name]==pin for name,pin in pins.items()),
        'V7_PIN_CONFLICT_WITH_ORIGINAL_SOURCE')
    require(set(members) == launch_allowlist(members[ADMISSION_PATH],members[SOURCE_PINS_PATH]),
        'V7_EXACT_SOURCE_CLOSURE_REQUIRED')
    mapping={name:sha256(raw).hexdigest() for name,raw in members.items()}
    require(all(mapping.get(name)==pin for name,pin in {**frozen,**pins}.items()),'V7_FROZEN_OR_PINNED_SOURCE_CHANGED')
    check_runtime_source(members[SOURCE_MANIFEST_PATH],mapping)
    validate_prototype_spec(members[SPEC_PATH])
    return {'profile':PROFILE_NAMES[0],'entrypoint':ENTRYPOINT,'spec_path':SPEC_PATH,'spec_sha256':mapping[SPEC_PATH]}


def prototype_record(mapping):
    return {'original_source_sha':ORIGINAL_SOURCE,'original_source_files':538,
        'source_pins_sha256':SOURCE_PINS_SHA256,'public_loader_sha256':FIXED_SPEC['public_loader_sha256'],
        'exclusion_inventory_sha256':FIXED_SPEC['exclusion_inventory_sha256'],'exclusion_count':8837,
        'original_training_append':256,'recovery_manifest_sha256':RECOVERY_MANIFEST_SHA256,
        'prerequisite_review_path':PREREQUISITE_REVIEW_PATH,'prerequisite_review_sha256':PREREQUISITE_REVIEW_SHA256,
        'source_input_count':len(mapping),'new_source_input_count':len(mapping)-538,
        'raw_v6_failure_packet_in_archive':False,'local_task_generation':False,'local_neural_execution':False}


def validate_launch_manifest(manifest, read_member=None):
    require(type(manifest) is dict,'V7_LAUNCH_MANIFEST_REQUIRED')
    record,mapping=manifest.get('experiment'),manifest.get('files_sha256')
    require(type(record) is dict and set(record)=={'profile','entrypoint','spec_path','spec_sha256'}
        and record['profile']==PROFILE_NAMES[0] and record['entrypoint']==ENTRYPOINT
        and record['spec_path']==SPEC_PATH and type(record['spec_sha256']) is str
        and SHA256.fullmatch(record['spec_sha256']),'V7_LAUNCH_EXPERIMENT_IDENTITY')
    require(type(mapping) is dict and len(mapping)==BASE_SOURCE_FILE_COUNT+int(PREREQUISITE_REVIEW_PATH is not None)
        and all(safe_name(name) and type(pin) is str and SHA256.fullmatch(pin)
        for name,pin in mapping.items()) and all(PILOT+'/'+name in mapping for name in LAUNCH_LOCAL_FILES)
        and all(mapping.get(name)==pin for name,pin in LAUNCH_PINS.items())
        and mapping.get(SPEC_PATH)==record['spec_sha256'],'V7_LAUNCH_MANIFEST_PINS')
    require(PREREQUISITE_REVIEW_PATH is None or mapping.get(PREREQUISITE_REVIEW_PATH)==PREREQUISITE_REVIEW_SHA256,
        'V7_LAUNCH_PREREQUISITE_REVIEW_PIN')
    require(manifest.get('prototype')==prototype_record(mapping),'V7_LAUNCH_BINDING_RECORD_CHANGED')
    if read_member is not None:
        members={name:read_member(name) for name in mapping}
        require(all(sha256(raw).hexdigest()==mapping[name] for name,raw in members.items()),'V7_LAUNCH_MEMBER_BYTES_CHANGED')
        require(make_launch_record(members)==record,'V7_LAUNCH_SOURCE_CLOSURE_CHANGED')
    return dict(record)


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
    source_pins = subprocess.check_output(['git','cat-file','blob',
        source_sha+':'+prefix+SOURCE_PINS_PATH.removeprefix('research/')],cwd=repo)
    required = launch_allowlist(admission,source_pins)
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
    require(set(members) == required, 'REQUIRED_V7_INPUT_NOT_COMMITTED')
    return members
