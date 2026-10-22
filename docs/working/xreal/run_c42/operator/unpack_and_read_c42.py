"""Unpack the c42 deliverable into x_real\\run_c42_xreal_20261019\\, verify every kept file against the host's own
RUN_RECORD.json hashes, extract a FRESH copy of the sealed X-REAL zip into reader_work\\xreal\\ (every member re-hashed
against its freeze), write MERGE_INPUT_XREAL.json (README_XREAL.md / LAUNCH_BRIEF step 6) and run the frozen reader
from the extracted sealed package in isolated mode:
    python -B -I -X utf8 xr_contract/xrun.py <PKG> xreal.merge_xreal --merge-input MERGE_INPUT_XREAL.json --out XREAL_READING.json
Derived from unpack_and_read_c40.py. Prints only counts, hashes, the verdict and the words; never opens an exam file
(the reader program reads the sealed exam folder itself)."""
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

OP = Path(r'C:\Users\wakil\Documents\Codex\2026-10-01\task-2\helm_operator_preparation')
CTRL = OP / 'controller_claude_xreal_c42'
SHORT = 'claude-xreal-c42'
JOB = 'helm-claude-xreal-20261019-c42'
D19 = Path(r'C:\Users\wakil\Documents\Codex\2026-10-19')
XR = D19 / 'x_real'
RUN = XR / 'run_c42_xreal_20261019'
ZIP = XR / 'HELM_XREAL_20261019_SOURCE_XREAL.zip'
ZIP_SHA = 'a9b4c9547e7276412a95141d24eb38d7d44ca3d539e8ff095abe727cf4e1c249'
FREEZE_SHA = '67b485415078ca11c5c3d984cd3f82a6a1ab1f111efc9ce2a619d3c136c8006d'
PKG = 'HELM_XREAL_20261019'
APPROVAL = OP / 'OWNER_APPROVAL_XREAL_20261020T000138Z.json'
EXAM = XR / 'xr_custody' / 'exam'
DERIV = XR / 'xr_custody' / 'work' / 'SEED_DERIVATION_XREAL.json'
RCHK = XR / 'xr_custody' / 'work' / 'RECEIVER_CHECK_XREAL.json'
C40_FULL = D19 / 'r1_wave5' / 'run_c40_r1w5_20261019' / 'deliverable_unpacked' / 'runs' / 'helm-claude-r1w5-20261019-c40' / \
    'results' / 'r1_w5_host_run' / 'out' / 'r1w5_out'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


assert sha(ZIP) == ZIP_SHA
assert sha(APPROVAL) == '6b4799b22750ca1c0c3050588f2364a66fc743c9ba0cd2245e9dc627399c4d6e'
assert sha(EXAM / 'MANIFEST_XREAL.json') == '1e535511a6e802a727a9a49cf6b4a317037f46fadd7b92271aac4376604a541e'
assert sha(EXAM / 'XREAL_PINS.json') == '4cb97a82f2fa816b2715eea454f1aec48afdd11bcc0aaf1c380e36bad7304999'
download = json.loads((CTRL / ('aws-' + SHORT + '-download.json')).read_bytes())
deliv = CTRL / ('aws-' + SHORT + '-deliverable.zip')
assert sha(deliv) == download['sha256'] and deliv.stat().st_size == download['bytes']
RUN.mkdir(exist_ok=False)
unp = RUN / 'deliverable_unpacked'
with zipfile.ZipFile(deliv) as z:
    assert z.testzip() is None
    z.extractall(unp)
root = unp / 'runs' / JOB
out = root / 'results' / 'xreal_host_run' / 'out'
rr = json.loads((out / 'RUN_RECORD.json').read_bytes())
checked, bad = 0, []
for rel in rr.get('copied_to_output', []):
    p = out / 'xreal_out' / rel
    pin = rr['xreal_output_files'][rel]
    if not p.is_file() or sha(p) != pin['sha256'] or p.stat().st_size != pin['bytes']:
        bad.append(rel)
    checked += 1
assert not bad, bad[:10]
for src, dst in ((out / 'RUN_RECORD.json', 'RUN_RECORD.json'), (out / 'pool.log', 'pool.log'),
                 (out / 'unittest_w1.log', 'unittest_w1.log'), (out / 'unittest_w2.log', 'unittest_w2.log'),
                 (out / 'unittest_w3.log', 'unittest_w3.log'), (out / 'unittest_w3b.log', 'unittest_w3b.log'),
                 (out / 'unittest_w4.log', 'unittest_w4.log'), (out / 'unittest_xr.log', 'unittest_xr.log'),
                 (root / 'results' / 'supervisor_receipt.json', 'supervisor_receipt.json'),
                 (root / 'results' / 'progress.json', 'supervisor_progress.json'), (root / 'assay.stderr.log', 'assay.stderr.log'),
                 (root / 'cgroup_final.log', 'cgroup_final.log'), (out / 'xreal_out' / 'XREAL_HOST.json', 'XREAL_HOST.json'),
                 (out / 'xreal_out' / 'XREAL_HOST.json.sha256', 'XREAL_HOST.json.sha256')):
    if src.is_file():
        shutil.copyfile(src, RUN / dst)
jr = RUN / 'job_record'
jr.mkdir()
for p in sorted(CTRL.iterdir()):
    if p.is_file() and not p.name.endswith('-deliverable.zip') and (p.name.startswith('aws-' + SHORT + '-') or p.name in (
            'sources_manifest.json', 'job_plan.json', 'ALLOCATION.json', 'CONTROLLER_REVIEW.json', 'INDEPENDENT_STATIC_REVIEW.json',
            'COST_POLICY.json', 'CONTROLLER_SOURCE_PINS.json', 'PACKAGING_RECEIPT.json', 'JOB_CONFIG.json',
            'launch.stdout.log', 'launch.stderr.log', 'watch.stdout.log', 'watch.stderr.log', 'independent.stdout.log')):
        shutil.copyfile(p, jr / p.name)
host_sidecar = (RUN / 'XREAL_HOST.json.sha256').read_text(encoding='utf-8').split()[0]
assert host_sidecar == sha(RUN / 'XREAL_HOST.json') == rr['host_sha256']
work = RUN / 'reader_work'
with zipfile.ZipFile(ZIP) as z:
    z.extractall(work / 'xreal')
pkg = work / 'xreal' / PKG
fz = json.loads((pkg / 'PACKAGE_FREEZE.json').read_bytes())
assert sha(pkg / 'PACKAGE_FREEZE.json') == FREEZE_SHA
assert all(sha(pkg / m) == v['sha256'] for m, v in fz['members'].items())
ap = json.loads(APPROVAL.read_bytes())
mi = {'schema': 'helm.xreal.merge-input/1',
      'host': str(RUN / 'XREAL_HOST.json'), 'host_sha256': sha(RUN / 'XREAL_HOST.json'),
      'run_record': str(RUN / 'RUN_RECORD.json'), 'run_record_sha256': sha(RUN / 'RUN_RECORD.json'),
      'exam_dir': str(EXAM),
      'approval': {k: ap[k] for k in ('owner_line_verbatim', 'owner_line_sha256', 'package_zip_sha256', 'package_freeze_sha256',
                                      'cap_usd', 'attempts', 'superseded_by')},
      'approval_record': str(APPROVAL), 'approval_record_sha256': sha(APPROVAL),
      'derivation': str(DERIV), 'derivation_sha256': sha(DERIV),
      'receiver_check': str(RCHK), 'receiver_check_sha256': sha(RCHK),
      'c40_full_dir': str(C40_FULL),
      'package_zip_sha256': sha(ZIP), 'package_freeze_sha256': sha(pkg / 'PACKAGE_FREEZE.json')}
(RUN / 'MERGE_INPUT_XREAL.json').write_text(json.dumps(mi, indent=1) + '\n', encoding='utf-8')
done = subprocess.run([sys.executable, '-B', '-I', '-X', 'utf8', str(pkg / 'xr_contract' / 'xrun.py'), str(pkg),
                       'xreal.merge_xreal', '--merge-input', str(RUN / 'MERGE_INPUT_XREAL.json'),
                       '--out', str(RUN / 'XREAL_READING.json')], cwd=str(work), capture_output=True, text=True, timeout=1800)
(RUN / 'reader.stdout.log').write_text(done.stdout, encoding='utf-8')
(RUN / 'reader.stderr.log').write_text(done.stderr, encoding='utf-8')
rd = RUN / 'XREAL_READING.json'
if rd.is_file():
    (RUN / 'XREAL_READING.json.sha256').write_text(sha(rd) + '  XREAL_READING.json\n', encoding='utf-8')
print(json.dumps({'kept_files_checked': checked, 'bad': len(bad), 'host_sha256': mi['host_sha256'],
                  'run_record_sha256': mi['run_record_sha256'], 'reader_exit': done.returncode,
                  'reading_sha256': sha(rd) if rd.is_file() else None,
                  'stdout_tail': done.stdout[-1500:], 'stderr_tail': done.stderr[-1500:]}, indent=1))
