"""Read-only subject discovery; write only new investigation records."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

OUT = Path(__file__).resolve().parent
CN = OUT.parents[1]
REPO = CN.parents[1]
BASE = Path('C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE')
SOURCE_REPO = BASE / '_worktrees/q4-live'
REL = 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE'
SOURCE = SOURCE_REPO / REL


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(cwd, *args):
    result = subprocess.run(['git', '-C', str(cwd), *args], capture_output=True)
    return {'exit_code': result.returncode, 'stdout': result.stdout.decode('utf-8', errors='replace'),
            'stderr': result.stderr.decode('utf-8', errors='replace')}


def fingerprint(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256_raw': sha(raw)}


def write_new(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write((json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))


def main():
    attachment = Path('C:/Users/wakil/Downloads/CODEX_HELM_FAILURE_RESEARCH_TEAM_20260922.md')
    copied = OUT / attachment.name
    with copied.open('xb') as stream:
        stream.write(attachment.read_bytes())
    assert fingerprint(copied)['sha256_raw'] == fingerprint(attachment)['sha256_raw']
    workspace = {'observed_utc': datetime.now(timezone.utc).isoformat(), 'app_cwd': str(BASE.parent),
                 'research_root': str(REPO), 'research_branch': 'codex/helm-failure-research-20260922',
                 'starting_commit': '4eb98682b983f9ceb22c9e0b5fa127e9d21cda0d', 'workspaces': []}
    for label, path in [('outer_app_project', BASE.parents[1]), ('helm_source', SOURCE_REPO),
                        ('preserved_reconciliation', BASE/'_worktrees/codex-cas-reconcile'),
                        ('peer_helm_lab', BASE/'_worktrees/helm3-lab'), ('research', REPO)]:
        workspace['workspaces'].append({'label': label, 'requested_path': str(path),
            'root': git(path, 'rev-parse', '--show-toplevel'), 'branch': git(path, 'branch', '--show-current'),
            'head': git(path, 'rev-parse', 'HEAD'),
            'common_git_dir': git(path, 'rev-parse', '--path-format=absolute', '--git-common-dir'),
            'status': git(path, 'status', '--porcelain', '--untracked-files=normal')})
    write_new('WORKSPACE_SNAPSHOT.json', workspace)
    subjects, source_packages = [], []
    receipts = SOURCE / 'records/typed_pointer_001'
    for version, prefix, admission in [('Helm 1.0', 'receipt_helm1_certified_', 'admission_helm1_certified'),
                                        ('Helm 2.0-experimental', 'receipt_', 'admission_001')]:
        for seed in (20260917, 20260918, 20260919):
            folder = receipts / (prefix + str(seed))
            config = json.loads((folder / 'collected/input/config.json').read_text(encoding='utf-8'))
            files = [folder/'source.zip', folder/'collected/input/config.json', folder/'artifact_manifest.json',
                     folder/'evidence_contract.json']
            files += sorted(p for p in (folder/'checkpoints').rglob('*') if p.is_file())
            subjects.append({'version': version, 'seed': seed, 'source_commit': config['source_sha'],
                'job': config['job'], 'receipt_root': str(folder),
                'source_of_identity': 'collected/input/config.json source_sha and loaded_sources.json; not archive commit',
                'final_checkpoint': fingerprint(folder/'checkpoints/final.pt'),
                'artifacts': [fingerprint(p) for p in files],
                'gate_reading': fingerprint(receipts/admission/'gate_reading.json'),
                'recorded_label': json.loads((receipts/admission/'gate_reading.json').read_text())['label']})
            if seed == 20260917:
                with zipfile.ZipFile(folder/'source.zip') as z:
                    inventory = [{'member': n, 'bytes': z.getinfo(n).file_size, 'sha256': sha(z.read(n))}
                                 for n in z.namelist() if not n.endswith('/')]
                source_packages.append({'version': version, 'package': fingerprint(folder/'source.zip'),
                                        'members': inventory})
    grader_rel = REL + '/records/typed_pointer_001/evaluate_gates.py'
    graders = []
    for version, ref in [('Helm 1.0', subjects[0]['source_commit']), ('Helm 2.0', subjects[3]['source_commit']),
                          ('research integration', workspace['starting_commit'])]:
        raw = subprocess.check_output(['git', 'show', ref+':'+grader_rel], cwd=SOURCE_REPO)
        graders.append({'version': version, 'commit': ref, 'repository_path': grader_rel,
                        'sha256_lf': sha(raw.replace(b'\r\n', b'\n'))})
    archives = []
    for name in ['helm_1_0_certified/receipt_helm1_certified_20260918',
                 'helm_2_0_experimental_20208c92/receipt_20260918']:
        path = Path('D:/tksCAS-archive') / name / 'checkpoints/final.pt'
        archives.append(fingerprint(path) if path.is_file() else {'path': str(path), 'status': 'UNAVAILABLE'})
    required = ['records/typed_course_001/checks_002/public_course.json',
                'records/typed_interface_001/checks_002/training_tokenizer.json',
                'docs/CAS_SHARED_MODULE_INVENTORY_20260922.json',
                'records/typed_pointer_001/evaluate_gates.py',
                'records/q4_authorized_20260922/ACCEPTANCE_MANIFEST.json',
                'records/q4_authorized_20260922/run_001/result.json']
    manifest = {'schema': 'helm.research-subject-manifest/0.1', 'created_utc': datetime.now(timezone.utc).isoformat(),
        'directive': fingerprint(copied), 'directive_original': fingerprint(attachment),
        'immutable_source_workspace': str(SOURCE_REPO), 'cncm_relative_path': REL,
        'integration_commit': workspace['starting_commit'],
        'subject': 'Original Helm 2.0 study compared with historically passing Helm 1.0; all three seeds',
        'subjects': subjects, 'source_packages': source_packages, 'grading_sources': graders,
        'additional_required_sources': [fingerprint(SOURCE / name) for name in required],
        'local_external_archive_duplicates': archives,
        'newer_Q4_context': {'status': 'RAN_LATER_NOT_UNRUN', 'task': 'T14_R1_G_ENGINEERING_SMOKE',
                            'updates': 128, 'exact_reconstructions': 0, 'dev_examples': 16,
                            'scope': 'Separate later task, not explanation or substitute for Helm1/Helm2'},
        'unknowns': ['All historical hypotheses require independent checking; this manifest assigns no cause.',
                     'Cloud job state not queried; no cloud provider actions are part of this investigation.',
                     'Sparse research checkout intentionally omits model files; use hashed immutable references or git objects.',
                     'Archive completeness is not asserted from the two checkpoint duplicate checks.'],
        'prior_exposure': 'Project lead read historical lineage opinions for source discovery. First-round agents receive identifiers and raw sources, not a preferred explanation.',
        'resources': {'model_initialization': False, 'model_inference': False, 'training': False,
                      'gpu_jobs': False, 'cloud_spend': False, 'paid_api_calls': False,
                      'agent_roles': 8, 'max_followup_rounds': 2, 'ordinary_account_allowance_only': True,
                      'observed_weekly_used_percent_at_start': 70, 'observed_remaining_percent_at_start': 30,
                      'paid_credits_available': False, 'do_not_redeem_reset_credit': True,
                      'max_active_sessions_in_tree': 4, 'planned_specialist_batch_size': 2,
                      'pure_cpu_probe_timeout_seconds': 120, 'maximum_parallel_cpu_probes': 2}}
    write_new('SOURCE_AND_EVIDENCE_MANIFEST.json', manifest)
    print(json.dumps({'subjects': len(subjects), 'artifact_rows': sum(len(x['artifacts']) for x in subjects),
                      'source_packages': len(source_packages), 'grader_versions_identical': len({x['sha256_lf'] for x in graders}) == 1}))


if __name__ == '__main__':
    main()
