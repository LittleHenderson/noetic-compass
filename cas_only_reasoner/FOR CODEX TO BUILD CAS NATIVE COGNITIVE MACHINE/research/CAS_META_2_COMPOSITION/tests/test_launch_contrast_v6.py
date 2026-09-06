"""Pure launcher tests. No reservations, provider calls, or neural execution."""
import ast
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import zipfile
import pytest
from test_launch_v3 import load, fixture_members, launch as old_launch

ROOT = Path(__file__).resolve().parents[1]
launch = load('launch_contrast_test', ROOT/'aws/launch_contrast_v6.py')
bundle = load('bundle_contrast_test', ROOT/'tools/build_launch_bundle_contrast_v6.py')
p = launch.profiles


@pytest.fixture
def package():
    plan = json.loads(launch.PLAN_FILE.read_bytes())
    members = fixture_members(plan)
    for name in p.V6_LOCAL_FILES:
        members.setdefault(p.PILOT+'/'+name, b'# inert unit fixture\n')
    for name in p.EXTRA_INPUTS:
        members[name] = (ROOT.parents[1]/name).read_bytes()
    members[p.V6_SPEC] = json.dumps(p.FIXED_SPEC).encode()
    baseline = sha256(members[bundle.META1+'/BASELINE_MANIFEST.json']).hexdigest()
    with patch.object(bundle, 'BASELINE_MANIFEST_SHA256', baseline):
        manifest = bundle.make_manifest(members, 'b'*40)
    return plan, members, manifest, baseline


def test_archive_validates_pinned_profile(package, tmp_path):
    plan, members, manifest, baseline = package
    path = tmp_path/'source.zip'
    with zipfile.ZipFile(path, 'x') as archive:
        for name, raw in members.items():
            archive.writestr(name, raw)
        archive.writestr('launch_manifest.json', json.dumps(manifest))
    with patch.object(launch, 'ACCEPTED_BASELINE_MANIFEST_SHA256', baseline):
        assert launch.validate_archive(path, launch.digest(path), 'b'*40, plan) == manifest
    assert manifest['experiment']['profile'] == 'contrast_learning_v6'


def test_remote_program_uses_exact_campaign_and_gpu_checks(package):
    plan, _, manifest, _ = package
    code = launch.remote_program({**plan, 'job': 'cas-meta2-20260906000000-12345678',
        'bucket': 'synthetic', 'archive_sha256': 'a'*64, 'manifest': manifest, 'smoke_only': False})
    tree = ast.parse(code)
    compile(tree, '<not-executed-remote>', 'exec')
    assignments = {target.id: node.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
                   for target in node.targets if isinstance(target, ast.Name)}
    assert assignments['argv'].elts[2].value == 'cas_meta2.contrast_v6.campaign'
    constants = {node.value for node in ast.walk(assignments['argv']) if isinstance(node, ast.Constant)}
    assert {'--job', '--output', '--max-wall-seconds'} <= constants
    assert '--training-file' not in constants
    assert "env['CAS_META2_RUN_CONTRAST_TRAINING'] = '1'" in code
    assert "env['CAS_META2_RUN_FIT_DIAGNOSTIC']" not in code
    assert assignments['policy_expected_tests'].value == 27
    assert "'native_evaluation_completed') is not True" in code
    assert "'optimizer_steps') != {'cas':8000,'generic':8000}" in code
    assert "'training_gate.json'" in code and "'native_receipt.json'" in code
    assert code.index('CLOUD_DEADLINE_NOT_CONFIRMED') < code.index("'-m','pip','install'")


def test_ownership_budget_termination_and_collection_helpers_unchanged():
    def functions(path):
        return {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(path.read_text()).body
                if isinstance(node, ast.FunctionDef)}
    old, new = functions(ROOT/'aws/launch_fit_v5.py'), functions(ROOT/'aws/launch_contrast_v6.py')
    for name in ('validate_approval', 'reserve_budget', 'validate_archive', 'check_tag', 'verify_downloaded_packet',
                 'confirm_deleted_volumes', 'remove_owned_auxiliary_resources', 'reconcile_instance', 'verify_schedule',
                 'terminate_owned_instance', 'build_evidence_bundle', 'sample_artifact_bytes', 'user_data',
                 'campaign_execution_lock', '_execute_locked'):
        assert old[name] == new[name], name
    assert launch.EXECUTION_LOCK_FILE == old_launch.EXECUTION_LOCK_FILE


def test_smoke_only_cannot_start_a_different_job(package):
    with patch.object(launch, 'campaign_execution_lock', side_effect=AssertionError('LOCK_REACHED')):
        with pytest.raises(launch.LaunchRefused):
            launch.execute(SimpleNamespace(smoke_only=True), package[0], package[2])


def test_status_does_not_claim_gpu_execution():
    import inspect
    assert 'CAS_META_2_CONTRAST_V6_PINNED_PACKAGE_BUILT_GPU_NOT_RUN' in inspect.getsource(bundle.build)
