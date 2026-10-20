"""Back up the X-REAL c42 deliverable and records to D:\\tksCAS-archive\\x_real_c42_20261019\\ with three sha256
confirmations per file (source before copy, destination after copy, destination re-read). Writes BACKUP_MANIFEST.
Derived from backup_r1w5_c40.py. X-REAL custody files are copied by bytes only (custody: never opened)."""
import datetime
import hashlib
import json
import shutil
from pathlib import Path

OP = Path(r'C:\Users\wakil\Documents\Codex\2026-10-01\task-2\helm_operator_preparation')
XRD = Path(r'C:\Users\wakil\Documents\Codex\2026-10-19\x_real')
DEST = Path(r'D:\tksCAS-archive\x_real_c42_20261019')
SOURCES = {
    'run_c42_xreal_20261019': XRD / 'run_c42_xreal_20261019',
    'controller_claude_xreal_c42': OP / 'controller_claude_xreal_c42',
    'x_real_c42_operator_notes': OP / 'x_real_c42_operator_notes',
    'x_real_c42_reservation_20261019': OP / 'x_real_c42_reservation_20261019',
    'xrealkit': OP / 'claude_jobkit' / 'xrealkit',
    'xr_custody_exam': XRD / 'xr_custody' / 'exam',
    'xr_custody_work': XRD / 'xr_custody' / 'work',
}
SINGLE = sorted(OP.glob('OWNER_APPROVAL_XREAL_*.json')) + [
    OP / 'CLAUDE_XREAL_C42_TRANSPORT_LEASE.json', OP / 'CLAUDE_XREAL_C42_SINGLE_LAUNCH_CLAIM.json',
    XRD / 'APPROVAL_RECORD_XREAL.md', XRD / 'LAUNCH_BRIEF_XREAL_20261019.md', XRD / 'PREREGISTRATION_X_REAL.md',
    XRD / 'TEST_COUNTS_XREAL.json', XRD / 'ZIP_SHA256.txt',
    XRD / 'HELM_XREAL_20261019_SOURCE_XREAL.zip', XRD / 'PACKAGE_FREEZE_XREAL.json',
    XRD / 'xr_custody' / 'XREAL_SEALED_20261019T235639Z.json',
    OP / 'claude_jobkit' / 'claude_xreal_c42_config.json', OP / 'claude_jobkit' / 'bus_xreal_c42_slot_notice.json',
    OP / 'claude_jobkit' / 'bus_xreal_c42_release.json']
SINGLE += sorted(OP.glob('BUDGET_RECONCILIATION_ADDENDUM_CLAUDE_XREAL_C42_*.json'))
SINGLE = [p for p in SINGLE if p.is_file()]


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


DEST.mkdir(parents=True, exist_ok=False)
rows, bad, pairs = {}, [], []
for name, src in SOURCES.items():
    for p in sorted(src.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            pairs.append((p, DEST / name / p.relative_to(src)))
for p in SINGLE:
    pairs.append((p, DEST / 'records' / p.name))
for src, dst in pairs:
    s1 = sha(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    s2 = sha(dst)
    s3 = sha(dst)
    rel = dst.relative_to(DEST).as_posix()
    rows[rel] = {'sha256': s1, 'bytes': dst.stat().st_size, 'confirmations': 3 if s1 == s2 == s3 else 0}
    if not s1 == s2 == s3:
        bad.append(rel)
manifest = {'schema': 'helm.backup-manifest/1', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'job': 'helm-claude-xreal-20261019-c42', 'files': len(rows), 'bad': bad,
            'status': 'BACKED_UP_THREE_CONFIRMS' if not bad else 'BACKUP_MISMATCH', 'rows': rows}
(DEST / 'BACKUP_MANIFEST_XREAL_C42.json').write_text(json.dumps(manifest, indent=1) + '\n', encoding='utf-8')
print(json.dumps({'files': len(rows), 'bad': bad, 'status': manifest['status'],
                  'manifest_sha256': sha(DEST / 'BACKUP_MANIFEST_XREAL_C42.json')}))
