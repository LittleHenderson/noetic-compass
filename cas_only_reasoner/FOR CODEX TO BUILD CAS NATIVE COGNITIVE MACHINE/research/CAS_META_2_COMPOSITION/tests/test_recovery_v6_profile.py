"""Pure recovery packaging tests. Frozen source bytes plus inert new-file fixtures."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import pytest
from tools import experiment_profiles_recovery_v6 as p
from tools import build_launch_bundle_recovery_v6 as b

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def members():
    # This reads source/development inputs already admitted in the original
    # source package, not the failed run's private dataset or any model state.
    admission = (ROOT.parents[1]/p.ADMISSION_PATH).read_bytes()
    frozen = p.frozen_inputs(admission)
    result = {name: (ROOT.parents[1]/name).read_bytes() for name in frozen}
    assert all(sha256(result[name]).hexdigest() == pin for name, pin in frozen.items())
    result.update({p.PILOT+'/'+name: b'# inert packaging unit fixture\n' for name in p.RECOVERY_LOCAL_FILES})
    result[p.ADMISSION_PATH] = admission
    result[p.SPEC_PATH] = (ROOT/'EXPERIMENT_RECOVERY_V6.json').read_bytes()
    runtime = {'schema': 'cas-meta2-contrast-recovery-source/6',
        'original_source_sha': p.ORIGINAL_SOURCE, 'original_source_archive_sha256': p.ORIGINAL_ARCHIVE,
        'files_sha256': {name: sha256(result[p.PILOT+'/'+name]).hexdigest() for name in p.RECOVERY_SOURCE_FILES}}
    result[p.SOURCE_MANIFEST_PATH] = p.canonical(runtime)
    return result


def test_fixed_recovery_spec():
    spec = p.validate_recovery_spec((ROOT/'EXPERIMENT_RECOVERY_V6.json').read_bytes())
    assert spec == p.FIXED_SPEC
    assert (spec['test_count'], spec['matched_test_triplets'], spec['arm_verdict_count']) == (72,24,360)
    assert (spec['gpu_gate_max_seconds'], spec['native_max_seconds'], spec['max_wall_seconds']) == (300,2400,3000)
    assert not spec['training_permitted'] and spec['already_exposed_holdout']


@pytest.mark.parametrize('field,value', [
    ('profile','contrast_learning_v6'), ('training_permitted',True), ('task_generation_permitted',True),
    ('prediction_generation_permitted',True), ('prediction_resealing_permitted',True),
    ('automatic_retry',True), ('automatic_promotion',True), ('source_release_accepted',True),
    ('already_exposed_holdout',False), ('test_count',71), ('test_count',72.0),
    ('packet_bytes',74958250), ('packet_in_source_archive',True), ('native_max_seconds',2401),
    ('gpu_gate_max_seconds',301), ('max_wall_seconds',3001), ('entrypoint','cas_meta2.contrast_v6.campaign'),
])
def test_fixed_spec_changes_refused(field, value):
    spec = deepcopy(p.FIXED_SPEC); spec[field] = value
    with pytest.raises(ValueError, match='SPEC_IDENTITY'):
        p.validate_recovery_spec(p.canonical(spec))


def test_complete_557_input_fixture_builds_pure_manifest(members):
    record = p.make_record(members)
    assert record['profile'] == 'contrast_recovery_v6' and record['entrypoint'] == p.ENTRYPOINT
    manifest = b.make_manifest(members, 'a'*40)
    assert len(manifest['files_sha256']) == 557
    assert manifest['original_source_files'] == 538 and manifest['protected_baseline_files'] == 316
    assert manifest['recovery_additional_files'] == 19
    assert manifest['external_packet'] == {'sha256':p.PACKET_SHA256,'bytes':74958249}
    assert manifest['recovery']['packet_in_source_archive'] is False
    assert p.validate_manifest(manifest, members.__getitem__) == record
    assert p.entrypoint(manifest) == p.ENTRYPOINT


@pytest.mark.parametrize('name', p.RECOVERY_LOCAL_FILES)
def test_every_new_input_is_required(members, name):
    value = dict(members); del value[p.PILOT+'/'+name]
    with pytest.raises(ValueError, match='ALLOWLIST|ADMISSION_MISSING'):
        p.make_record(value)


@pytest.mark.parametrize('profile', ['contrast_learning_v6', 'default', None, ''])
def test_other_profiles_refused(profile):
    with pytest.raises(ValueError, match='NOT_ALLOWLISTED'):
        p.make_record({}, profile)


def test_old_packet_cannot_be_smuggled_into_git_zip(members):
    value = dict(members); value[p.PILOT+'/records/cloud_artifacts.zip'] = b'not a real packet'
    with pytest.raises(ValueError, match='ALLOWLIST'):
        p.make_record(value)


def test_original_source_cannot_be_resealed(members):
    value = dict(members)
    name = next(iter(p.frozen_inputs(value[p.ADMISSION_PATH])))
    value[name] += b'changed'
    with pytest.raises(ValueError, match='ORIGINAL_FROZEN_SOURCE_CHANGED'):
        p.make_record(value)


def test_original_source_mapping_cannot_be_resealed(members):
    manifest = b.make_manifest(members, 'a'*40)
    name = next(iter(p.frozen_inputs(members[p.ADMISSION_PATH])))
    manifest['files_sha256'][name] = 'b'*64
    with pytest.raises(ValueError, match='ORIGINAL_FROZEN_SOURCE_CHANGED'):
        p.validate_manifest(manifest, members.__getitem__)


def test_failure_admission_cannot_be_resealed(members):
    value = dict(members); raw = p.decode(value[p.ADMISSION_PATH]); raw['campaign_completed'] = True
    value[p.ADMISSION_PATH] = p.canonical(raw)
    with pytest.raises(ValueError, match='PINNED_FAILURE_ADMISSION_CHANGED'):
        p.make_record(value)


@pytest.mark.parametrize('change', ['missing', 'extra', 'self', 'wrong_pin'])
def test_runtime_source_map_requires_exact_eight(members, change):
    value = dict(members); runtime = p.decode(value[p.SOURCE_MANIFEST_PATH])
    own = runtime['files_sha256']
    if change == 'missing':
        del own[p.RECOVERY_SOURCE_FILES[0]]
    elif change == 'extra':
        own['cas_meta2/contrast_recovery_v6/extra.py'] = 'b'*64
    elif change == 'self':
        own[p.SOURCE_MANIFEST_PATH.removeprefix(p.PILOT+'/')] = 'b'*64
    else:
        own[p.RECOVERY_SOURCE_FILES[0]] = 'b'*64
    value[p.SOURCE_MANIFEST_PATH] = p.canonical(runtime)
    with pytest.raises(ValueError, match='RUNTIME_SOURCE_CLOSURE'):
        p.make_record(value)


@pytest.mark.parametrize('which', ['packet', 'recovery'])
def test_external_packet_records_cannot_disagree(members, which):
    manifest = b.make_manifest(members, 'a'*40)
    if which == 'packet':
        manifest['external_packet']['bytes'] += 1
    else:
        manifest['recovery']['packet_sha256'] = 'b'*64
    with pytest.raises(ValueError, match='RECOVERY_EXTERNAL_PACKET|RECOVERY_BINDING'):
        p.validate_manifest(manifest, members.__getitem__)


@pytest.mark.parametrize('raw', [b'',b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":1e400}'])
def test_ambiguous_json_refused(raw):
    with pytest.raises(ValueError):
        p.validate_recovery_spec(raw)


@pytest.mark.parametrize('name', ['../escape','research/CAS_META_2_COMPOSITION/../bad',
                                  'research/CAS_META_2_COMPOSITION/file\\bad','/absolute'])
def test_unsafe_source_names_refused(name):
    with pytest.raises(ValueError):
        p.safe_name(name)


def test_output_escape_refused_before_git_access():
    with patch.object(b.profiles, 'git_context', side_effect=AssertionError('Git must not be reached')):
        with pytest.raises(ValueError, match='NEW_OUTPUT'):
            b.build(ROOT/'records'/'..'/'..'/'outside.zip')


def test_uncommitted_cli_helper_refused():
    repo = ROOT
    with patch.object(b.subprocess, 'check_output', side_effect=[str(repo)+'\n','a'*40+'\n',b'not source bytes']):
        with pytest.raises(ValueError, match='PREIMPORT_BUNDLE_HELPER_NOT_COMMITTED'):
            b.verify_cli_helpers_before_import()


def test_no_neural_import():
    # The full pure suite allows botocore's exception classes. Do not mistake
    # another test's prior import for this profile's own import behavior.
    probe = r'''
import importlib.abc, json, pathlib, sys
root = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
forbidden = {'torch','casformer','cas_cjt','tensorflow','jax','cupy','boto3','botocore','cas_meta'}
def blocked(name):
    return name.split('.')[0] in forbidden or name in (
        'cas_meta2.native', 'cas_meta2.contrast_recovery_v6.runtime')
attempts = []
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if blocked(fullname):
            attempts.append(fullname)
            raise AssertionError('FRESH_PROFILE_FORBIDDEN_IMPORT:' + fullname)
sys.meta_path.insert(0, Guard())
def audit(event, args):
    if event in ('subprocess.Popen', 'os.system', 'socket.connect', 'socket.bind'):
        raise AssertionError('FRESH_IMPORT_SIDE_EFFECT_FORBIDDEN:' + event)
sys.addaudithook(audit)
before = set(sys.modules)
before_forbidden = sorted(name for name in before if blocked(name))
assert before_forbidden == []
hooks, paths = list(sys.meta_path), list(sys.path)
from tools import experiment_profiles_recovery_v6 as profile
from tools import build_launch_bundle_recovery_v6 as builder
after = set(sys.modules)
assert pathlib.Path(profile.__file__).resolve() == root/'tools/experiment_profiles_recovery_v6.py'
assert pathlib.Path(builder.__file__).resolve() == root/'tools/build_launch_bundle_recovery_v6.py'
assert list(sys.meta_path) == hooks and list(sys.path) == paths
after_forbidden = sorted(name for name in after if blocked(name))
assert after_forbidden == [] and attempts == []
print(json.dumps({'fresh_isolated_process': True, 'site_disabled': bool(sys.flags.no_site),
    'before_forbidden': before_forbidden, 'after_forbidden': after_forbidden,
    'attempted_forbidden_imports': attempts, 'new_modules': sorted(after-before),
    'source_files': [str(pathlib.Path(value.__file__).resolve()) for value in (profile,builder)],
    'hook_and_path_unchanged': True}))
'''
    command = [sys.executable, '-I', '-S', '-B', '-c', probe, str(ROOT)]
    child = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert child.returncode == 0, child.stdout + child.stderr
    footprint = json.loads(child.stdout)
    assert footprint['fresh_isolated_process'] and footprint['site_disabled']
    assert footprint['before_forbidden'] == footprint['after_forbidden'] == []
    assert footprint['attempted_forbidden_imports'] == []
    assert 'tools.experiment_profiles_recovery_v6' in footprint['new_modules']
    assert 'tools.build_launch_bundle_recovery_v6' in footprint['new_modules']
    print('PROFILE_IMPORT_FOOTPRINT ' + child.stdout.strip())
