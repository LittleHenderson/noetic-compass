"""Pure launch/spec contracts. No provider calls, reservations or neural work."""
import ast
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import zipfile
import pytest
from test_launch_v3 import load, fixture_members as old_fixture, launch as old_launch

pytestmark = pytest.mark.not_gpu
ROOT = Path(__file__).resolve().parents[1]
launch = load('launch_fit_test', ROOT / 'aws/launch_fit_v5.py')
bundle = load('bundle_fit_test', ROOT / 'tools/build_launch_bundle_fit_v5.py')
profiles = launch.profiles


@pytest.fixture
def package():
    plan = json.loads(launch.PLAN_FILE.read_bytes())
    members = old_fixture(plan)
    for name in profiles.V5_LOCAL_FILES:
        members.setdefault(bundle.PILOT + '/' + name, b'# inert source fixture\n')
    for name in profiles.EXTRA_INPUTS:
        members[name] = (ROOT.parents[1] / name).read_bytes()
    members[profiles.V5_SPEC] = json.dumps(profiles.FIXED_SPEC).encode()
    baseline_digest = sha256(members[bundle.META1 + '/BASELINE_MANIFEST.json']).hexdigest()
    with patch.object(bundle, 'BASELINE_MANIFEST_SHA256', baseline_digest):
        manifest = bundle.make_manifest(members, 'b' * 40)
    return plan, members, manifest, baseline_digest


def test_valid_archive_and_exact_preserved_inputs(package, tmp_path):
    plan, members, manifest, baseline = package
    path = tmp_path / 'source.zip'
    with zipfile.ZipFile(path, 'x') as archive:
        for name, raw in members.items(): archive.writestr(name, raw)
        archive.writestr('launch_manifest.json', json.dumps(manifest))
    with patch.object(launch, 'ACCEPTED_BASELINE_MANIFEST_SHA256', baseline):
        assert launch.validate_archive(path, launch.digest(path), 'b' * 40, plan) == manifest
    assert manifest['experiment']['profile'] == 'known_example_fit_v5'


@pytest.mark.parametrize('name', ['learning_v3', 'learning_v2', 'default', None])
def test_training_profiles_refused(package, name):
    with pytest.raises(ValueError, match='NOT_ALLOWLISTED'):
        profiles.make_record(package[1], name)


@pytest.mark.parametrize('field,value', [('training_permitted', False),
    ('fresh_held_out_claim_permitted', True), ('source_release_accepted', True),
    ('entrypoint', 'cas_meta2.campaign_v3'), ('fit_task_count', 25), ('training_permitted', 0)])
def test_no_spec_boundary_relaxation(field, value):
    spec = dict(profiles.FIXED_SPEC, **{field: value})
    with pytest.raises(ValueError, match='SPEC_IDENTITY'):
        profiles.validate_fit_spec(json.dumps(spec).encode())


def test_only_exact_historical_inputs_are_included(package):
    for path in profiles.EXTRA_INPUTS:
        assert profiles.include_member(path) and bundle.include_member(path)
    for path in ['records/other/inputs.zip', 'runs/new/checkpoint.pt',
                 'records/decoder_ablation_inputs_v4_001/predictions.jsonl']:
        assert not profiles.include_member(bundle.PILOT + '/' + path)
        assert not bundle.include_member(bundle.PILOT + '/' + path)
    members = dict(package[1])
    members[next(iter(profiles.EXTRA_INPUTS))] = b'changed'
    with pytest.raises(ValueError, match='PINNED_FIT_TRAINING_INPUT_CHANGED'):
        profiles.make_record(members)


def test_smoke_refused_before_lock_or_budget(package):
    with patch.object(launch, 'campaign_execution_lock', side_effect=AssertionError('LOCK_REACHED')):
        with pytest.raises(launch.LaunchRefused, match='NO_TRAINING_OR_SMOKE'):
            launch.execute(SimpleNamespace(smoke_only=True), package[0], package[2])


def test_remote_dispatch_only_starts_registered_fit(package):
    plan, members, manifest, _ = package
    code = launch.remote_program({**plan, 'job': 'cas-meta2-20260906000000-12345678',
        'bucket': 'fixture', 'archive_sha256': 'a' * 64, 'manifest': manifest, 'smoke_only': False})
    tree = ast.parse(code)
    compile(tree, '<remote-not-executed>', 'exec')
    assignments = {target.id: node.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
                   for target in node.targets if isinstance(target, ast.Name)}
    argv = assignments['argv']
    assert argv.elts[2].value == 'cas_meta2.fit_campaign_v5'
    constants = {node.value for node in ast.walk(argv) if isinstance(node, ast.Constant)
                 and isinstance(node.value, str)}
    assert {'--training-file', '--job', '--max-wall-seconds'} <= constants
    assert 'measurement_0200.json' in code and 'fit_receipt.json' in code
    assert "env['CAS_META2_RUN_FIT_DIAGNOSTIC'] = '1'" in code
    assert "'training_performed') is not True" in code
    assert "'fresh_held_out_claim_permitted') is not False" in code
    assert assignments['policy_expected_tests'].value == 27
    assert code.index('CLOUD_DEADLINE_NOT_CONFIRMED') < code.index("'-m','pip','install'")


def test_budget_shutdown_collection_and_ownership_helpers_unchanged():
    def functions(path):
        return {node.name: ast.dump(node, include_attributes=False)
                for node in ast.parse(path.read_text()).body if isinstance(node, ast.FunctionDef)}
    old = functions(ROOT / 'aws/launch_v3.py')
    new = functions(ROOT / 'aws/launch_fit_v5.py')
    for name in ['validate_approval', 'reserve_budget', 'validate_archive', 'check_tag',
                 'verify_downloaded_packet', 'confirm_deleted_volumes',
                 'remove_owned_auxiliary_resources', 'reconcile_instance', 'verify_schedule',
                 'terminate_owned_instance', 'build_evidence_bundle', 'sample_artifact_bytes',
                 'user_data', 'campaign_execution_lock', '_execute_locked']:
        assert old[name] == new[name], name
    assert launch.EXECUTION_LOCK_FILE == old_launch.EXECUTION_LOCK_FILE


def test_campaign_requires_matching_launch_profile(monkeypatch):
    from cas_meta2 import fit_campaign_v5 as campaign
    digest = sha256((ROOT / 'EXPERIMENT_FIT_V5.json').read_bytes()).hexdigest()
    values = {'CAS_META2_SOURCE_SHA': 'b' * 40, 'CAS_META2_EXPERIMENT_PROFILE': 'known_example_fit_v5',
        'CAS_META2_EXPERIMENT_ENTRYPOINT': 'cas_meta2.fit_campaign_v5',
        'CAS_META2_EXPERIMENT_SPEC_SHA256': digest}
    for key, value in values.items(): monkeypatch.setenv(key, value)
    assert campaign.experiment_identity()['spec_sha256'] == digest
    monkeypatch.setenv('CAS_META2_EXPERIMENT_PROFILE', 'learning_v3')
    with pytest.raises(RuntimeError, match='LAUNCH_EXPERIMENT_IDENTITY_REQUIRED'):
        campaign.experiment_identity()


def test_builder_status_identifies_fit_without_claiming_gpu_execution():
    import inspect
    assert 'CAS_META_2_FIT_V5_PINNED_PACKAGE_BUILT_GPU_NOT_RUN' in inspect.getsource(bundle.build)
