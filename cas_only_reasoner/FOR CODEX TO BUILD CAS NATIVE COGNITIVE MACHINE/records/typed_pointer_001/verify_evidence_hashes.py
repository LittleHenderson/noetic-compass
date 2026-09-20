"""Check that every evidence file still matches the hash the run itself recorded.

WHY THIS EXISTS. The frozen grader (`evaluate_gates.py`) reads the `correct` flags out of
`course_p00_scoring.json` and `course_p10_scoring.json` and decides the label from them. **It never
checks those two files against the sha256 the run recorded in its own `artifact_manifest.json`.** An
independent audit on 2026-09-20 demonstrated the consequence: it hand-edited seed `20260919`'s
`course_p10_scoring.json` so every real-correct answer read wrong and every real-wrong read right,
re-ran the grader, and still got `label: LEARNS_NEW_WORLDS` with `integrity: pass, failures: []`.

The real files were verified intact after that test, so nothing is forged. But a certificate that
cannot detect an edited input is a weaker guarantee than the design intends, and this program is the
missing check. **It is deliberately NOT part of the frozen grader**: changing `evaluate_gates.py`
would move its sha256 and the certificate `475379d2...` could no longer be reproduced. The fix
belongs in the next grader version; this belongs beside it.

WHAT IT DOES. For each receipt, read `artifact_manifest.json`, and for every entry recompute the
sha256 and byte count of the collected file and compare. Report every mismatch with both numbers.
Exit 0 only if every file in every receipt matches.

Usage:
    python records/typed_pointer_001/verify_evidence_hashes.py [RECEIPT_DIR ...]

With no arguments it checks the three claim-bearing receipts of the certified study.
"""
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
DEFAULT_RECEIPTS = ('receipt_20260917', 'receipt_20260918', 'receipt_20260919')
# The two files the label is actually a function of. Reported separately and loudly, because these
# are the ones whose integrity the frozen grader does not check.
LABEL_DECIDING = ('course_p00_scoring.json', 'course_p10_scoring.json')


def rows_of(manifest):
    """The manifest's artifact list, under either name it has been written with."""
    for key in ('artifacts', 'files'):
        rows = manifest.get(key)
        if isinstance(rows, list) and rows:
            return rows
    return []


def check(receipt):
    """`(checked, problems, label_files_ok)` for one receipt directory."""
    manifest_path = receipt / 'artifact_manifest.json'
    if not manifest_path.is_file():
        return 0, ['NO_MANIFEST:%s' % receipt.name], False
    artifacts = receipt / 'collected' / 'results' / 'artifacts'
    if not artifacts.is_dir():
        return 0, ['NO_ARTIFACTS_DIR:%s' % receipt.name], False
    rows = rows_of(json.loads(manifest_path.read_text(encoding='utf-8')))
    if not rows:
        return 0, ['EMPTY_MANIFEST:%s' % receipt.name], False
    checked, problems, label_ok = 0, [], True
    for row in rows:
        name = row.get('name')
        target = artifacts / str(name)
        if not target.is_file():
            problems.append('MISSING:%s' % name)
            if name in LABEL_DECIDING:
                label_ok = False
            continue
        raw = target.read_bytes()
        checked += 1
        got, want = sha256(raw).hexdigest(), row.get('sha256')
        if got != want or len(raw) != row.get('bytes'):
            problems.append('MISMATCH:%s recorded=%s bytes=%s got=%s bytes=%d'
                            % (name, want, row.get('bytes'), got, len(raw)))
            if name in LABEL_DECIDING:
                label_ok = False
    return checked, problems, label_ok


def main(argv):
    names = argv or DEFAULT_RECEIPTS
    total, failures = 0, []
    print('receipt                          files  label-deciding files  result')
    for name in names:
        receipt = HERE / name
        if not receipt.is_dir():
            failures.append('NO_RECEIPT:%s' % name)
            print('%-32s %5s  %-20s %s' % (name, '-', '-', 'ABSENT'))
            continue
        checked, problems, label_ok = check(receipt)
        total += checked
        failures.extend('%s:%s' % (name, p) for p in problems)
        verdict = 'INTACT' if not problems else 'MISMATCH (%d)' % len(problems)
        print('%-32s %5d  %-20s %s' % (name, checked, 'INTACT' if label_ok else 'CHANGED', verdict))
        for problem in problems:
            print('    %s' % problem)
    print()
    print('files checked          : %d' % total)
    print('mismatches or missing  : %d' % len(failures))
    print('EVIDENCE_HASH_CHECK:%s' % ('PASS' if not failures else 'FAIL'))
    print()
    print('NOTE: this check is NOT part of the frozen grader. A PASS here means the evidence files')
    print('still match what the run recorded. It does not mean the grader read them, and it does not')
    print('mean the label is correct. See BRAIN_LINEAGE.md rule 3.')
    return 0 if not failures else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
