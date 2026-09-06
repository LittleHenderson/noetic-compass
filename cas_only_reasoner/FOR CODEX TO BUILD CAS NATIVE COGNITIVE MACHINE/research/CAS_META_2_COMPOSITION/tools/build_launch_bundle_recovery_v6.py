"""Build a closed recovery source ZIP from committed bytes. No neural/provider work."""
import argparse
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = '0917267b1354e5d036263eaa6ba9a7197eafb776'
BASELINE_MANIFEST_SHA256 = '476a8bbdc7a4b07a406e46b246ed417ea1d902e04cfb852ca710de09dcbc59f0'
META1 = 'research/CAS_META_1_LEARNED_SELECTION'
PILOT = 'research/CAS_META_2_COMPOSITION'


def regular(path):
    path = Path(path).absolute()
    if not path.is_file() or any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
                                for p in (path, *path.parents)):
        raise ValueError('SOURCE_LINK_OR_MISSING:'+str(path))
    return path


def verify_cli_helpers_before_import():
    repo = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=ROOT, text=True).strip())
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    for relative in ('tools/build_launch_bundle_recovery_v6.py', 'tools/experiment_profiles_recovery_v6.py'):
        path = regular(ROOT/relative)
        raw = subprocess.check_output(['git', 'cat-file', 'blob', head+':'+path.relative_to(repo).as_posix()], cwd=repo)
        if path.read_bytes() != raw:
            raise ValueError('PREIMPORT_BUNDLE_HELPER_NOT_COMMITTED:'+relative)


if __name__ == '__main__':
    verify_cli_helpers_before_import()

_PROFILE_PATH = ROOT/'tools/experiment_profiles_recovery_v6.py'
_PROFILE_SPEC = importlib.util.spec_from_file_location('cas_meta2_recovery_package_profile', _PROFILE_PATH)
_PROFILE_IMPORT_SHA256 = sha256(regular(_PROFILE_PATH).read_bytes()).hexdigest()
profiles = importlib.util.module_from_spec(_PROFILE_SPEC)
_PROFILE_SPEC.loader.exec_module(profiles)
PACKAGES = profiles.PACKAGES
EXPANDED_LIMIT = profiles.EXPANDED_LIMIT


def make_manifest(members, head, *, experiment_profile='contrast_recovery_v6'):
    profiles.require(type(head) is str and __import__('re').fullmatch('[a-f0-9]{40}', head),
                     'EXACT_SOURCE_SHA_REQUIRED')
    experiment = profiles.make_record(members, experiment_profile)
    baseline_raw = members[META1+'/BASELINE_MANIFEST.json']
    profiles.require(sha256(baseline_raw).hexdigest() == BASELINE_MANIFEST_SHA256, 'PROTECTED_BASELINE_MANIFEST_CHANGED')
    baseline = profiles.decode(baseline_raw)
    profiles.require(baseline.get('baseline_sha') == BASELINE_SHA and len(baseline['files']) == 316,
                     'ACCEPTED_BASELINE_REQUIRED')
    for item in baseline['files']:
        name = 'research/'+item['path']
        profiles.require(name in members and sha256(members[name]).hexdigest() == item['sha256'],
                         'PROTECTED_BASELINE_BYTES_CHANGED:'+name)
    profiles.require(sum(len(raw) for raw in members.values()) <= EXPANDED_LIMIT, 'ARCHIVE_EXPANDED_SIZE_CEILING')
    dist = 'research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/'
    mapping = {name: sha256(raw).hexdigest() for name, raw in sorted(members.items())}
    manifest = {
        'schema_version': 2, 'source_sha': head, 'baseline_sha': BASELINE_SHA,
        'pilot_dir': PILOT, 'meta1_dir': META1,
        'meta_runtime_dir': 'research/CASFORMER_v0_3_META_LOGIC_WIP',
        'dependency_lock': PILOT+'/requirements-gpu.txt',
        'dependency_scope': 'Unchanged pinned direct requirements; actual remote environment must be receipted.',
        'wheel_paths': [dist+'casformer_reference-0.1.0-py3-none-any.whl',
                        dist+'cas_neural_cjt-0.2.0-py3-none-any.whl'],
        'included_packages': list(PACKAGES), 'files_sha256': mapping,
        'protected_baseline_files': 316, 'original_source_files': 538, 'recovery_additional_files': 19,
        'excluded_inputs': 'Exact original 538 inputs plus 19 explicit recovery inputs only. '
                           'The original failed 74,958,249-byte packet is a separately pinned input, not Git source. '
                           'No new training data, task generation, prediction generation or resealing.',
        'experiment': experiment, 'recovery': profiles.recovery_record(mapping),
        'external_packet': {'sha256': profiles.PACKET_SHA256, 'bytes': profiles.PACKET_BYTES},
        'neural_execution_performed_during_packaging': False,
        'provider_execution_performed_during_packaging': False,
        'training_permitted': False, 'automatic_promotion': False,
    }
    profiles.validate_manifest(manifest, members.__getitem__)
    return manifest


def build(output, *, experiment_profile='contrast_recovery_v6'):
    profiles.validate_profile_name(experiment_profile)
    output = Path(output).absolute()
    profiles.require('..' not in output.parts and output.resolve().is_relative_to(ROOT.resolve())
        and output.resolve() != ROOT.resolve() and not output.exists()
        and not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)() for p in (output, *output.parents)),
        'NEW_OUTPUT_INSIDE_CAMPAIGN_REQUIRED')
    repo, prefix = profiles.git_context(ROOT)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    members = profiles.git_members(repo, prefix, head)
    # Every packaged source file must be present and exactly match its committed
    # bytes. Unrelated work outside this closed input set is not incorporated.
    for name, raw in members.items():
        local = regular(ROOT.parents[1]/name)
        profiles.require(local.read_bytes() == raw, 'PACKAGED_WORKTREE_BYTES_NOT_COMMITTED:'+name)
    profiles.require(_PROFILE_IMPORT_SHA256 == sha256(members[PILOT+'/tools/experiment_profiles_recovery_v6.py']).hexdigest(),
                     'PROFILE_CHANGED_AFTER_IMPORT')
    manifest = make_manifest(members, head, experiment_profile=experiment_profile)
    members['launch_manifest.json'] = (json.dumps(manifest, indent=2, sort_keys=True)+'\n').encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, raw in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(1980,1,1,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    with zipfile.ZipFile(output) as archive:
        profiles.require(archive.testzip() is None and set(archive.namelist()) == set(members),
                         'ARCHIVE_READBACK_COVERAGE')
        for name, raw in members.items():
            profiles.require(archive.read(name) == raw, 'ARCHIVE_READBACK_BYTES_CHANGED:'+name)
    # Recheck all executable/input source bytes after writing the package.
    for name, pin in manifest['files_sha256'].items():
        profiles.require(sha256(regular(ROOT.parents[1]/name).read_bytes()).hexdigest() == pin,
                         'SOURCE_CHANGED_DURING_PACKAGING:'+name)
    return {
        'status': 'CAS_META2_RECOVERY_V6_PINNED_PACKAGE_BUILT_GPU_NOT_RUN',
        'source_sha': head, 'baseline_sha': BASELINE_SHA, 'archive': str(output),
        'archive_sha256': sha256(output.read_bytes()).hexdigest(), 'archive_bytes': output.stat().st_size,
        'files': len(members), 'protected_baseline_files': 316, 'launch_manifest': manifest,
        'neural_execution': False, 'provider_execution': False, 'training_permitted': False,
        'evaluation_recovery_completed': False,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--experiment-profile', choices=profiles.PROFILE_NAMES, default='contrast_recovery_v6')
    args = parser.parse_args()
    receipt_path = args.output.with_suffix('.receipt.json')
    if receipt_path.exists():
        raise ValueError('PACKAGE_RECEIPT_ALREADY_EXISTS')
    result = build(args.output, experiment_profile=args.experiment_profile)
    with receipt_path.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'launch_manifest'}, indent=2))
