"""Read-only verification of the other agent's frozen audit package and Git claims."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
CN = HERE.parents[1]
ROOT = CN.parents[1]
FROZEN = '626cc84b574e60217a103b72d2f09388d7aa5e34'
OTHER = 'eb9985566bd11a89f485d627186ef0efa7177f02'
PREFIX = 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/'
PACKAGE = CN / 'records/audit_package_20260922'
MAIN = Path('C:/Users/wakil/OneDrive/Desktop/tksCAS')


def git(*args, cwd=ROOT, check=True):
    result = subprocess.run(['git', *args], cwd=cwd, capture_output=True, check=False)
    if check and result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace'))
    return result


def blob(ref, path):
    return git('show', ref + ':' + path).stdout


def digest(raw):
    return sha256(raw.replace(b'\r\n', b'\n')).hexdigest()


def main():
    manifest = json.loads((PACKAGE/'02_MANIFEST.json').read_text(encoding='utf-8'))
    claims = json.loads((PACKAGE/'01_CLAIMS_TO_CHECK.json').read_text(encoding='utf-8'))
    rows, current = [], []
    for path, record in manifest['files'].items():
        for label, expected in record['by_ref'].items():
            ref = manifest['refs'][label]
            result = git('show', ref + ':' + path, check=False)
            actual = digest(result.stdout) if result.returncode == 0 else None
            rows.append({'path': path, 'ref': ref, 'expected': expected,
                         'actual': actual, 'match': actual == expected})
        raw = blob(FROZEN, path)
        expected = record['on_disk_now']
        current.append({'path': path, 'expected_sha256_lf': expected['sha256_lf'],
                        'actual_sha256_lf': digest(raw), 'expected_bytes': expected['bytes'],
                        'actual_bytes': len(raw), 'match': digest(raw) == expected['sha256_lf']})
    copies = {
        'cas_ohm_quantifiers_BEFORE.py': ('078d00ed', 'noetic-compass-scaffold/noetic-compass/api/cas_ohm/quantifiers.py'),
        'cas_ohm_quantifiers_AFTER.py': (FROZEN, 'noetic-compass-scaffold/noetic-compass/api/cas_ohm/quantifiers.py'),
        'cas_ohm_test_BEFORE.py': ('078d00ed', 'noetic-compass-scaffold/noetic-compass/api/cas_ohm/test_quantifiers.py'),
        'cas_ohm_test_AFTER.py': (FROZEN, 'noetic-compass-scaffold/noetic-compass/api/cas_ohm/test_quantifiers.py'),
        'Chapter_10_BEFORE.md': ('dbb388ee', 'book/CAS_PCBA_Engineer/Chapter_10_Special_Purpose_Components.md'),
        'Chapter_10_AFTER.md': ('d50abbbc', 'book/CAS_PCBA_Engineer/Chapter_10_Special_Purpose_Components.md'),
        'CANON_Appendix_I_CAS_Ohm.md': ('d50abbbc', 'book/CAS_PCBA_Engineer/Appendix_I_CAS_Ohm_Measurement_and_Calibration.md'),
        'canon_guard_RESTORED.py': (FROZEN, 'noetic-compass-scaffold/noetic-compass/tests/test_offline_help_text_canon.py'),
    }
    copy_rows = []
    for name, (ref, path) in copies.items():
        raw = (PACKAGE/'files'/name).read_bytes()
        copy_rows.append({'name': name, 'ref': ref, 'path': path,
                          'copy_sha256_lf': digest(raw), 'source_sha256_lf': digest(blob(ref, path)),
                          'match': digest(raw) == digest(blob(ref, path))})
    main_queries = {}
    for label, args in {
        'head': ('rev-parse', 'HEAD'), 'branch': ('branch', '--show-current'),
        'not_in_local_remote_refs': ('rev-list', '--count', 'HEAD', '--not', '--remotes'),
        'upstream': ('rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'),
    }.items():
        r = git(*args, cwd=MAIN, check=False)
        main_queries[label] = {'command': ['git', *args], 'returncode': r.returncode,
                               'stdout': r.stdout.decode(errors='replace').strip(),
                               'stderr': r.stderr.decode(errors='replace').strip()}
    compiler_path = 'noetic-compass-scaffold/noetic-compass/api/notation/compiler.py'
    pcba_path = PREFIX+'research/helm_cas_expression_lab/pcba_reader.py'
    branches = []
    for ref in (FROZEN, OTHER):
        compiler = blob(ref, compiler_path)
        pcba = git('cat-file', '-e', ref+':'+pcba_path, check=False)
        branches.append({'commit': ref, 'compiler_sha256_lf': digest(compiler),
                         'has_ohm_flow_builtin': b'"ohm_flow"' in compiler,
                         'has_ohm_required_drive_builtin': b'"ohm_required_drive"' in compiler,
                         'has_ohm_effective_constraint_builtin': b'"ohm_effective_constraint"' in compiler,
                         'pcba_reader_exists': pcba.returncode == 0})
    old_tests = 'noetic-compass-scaffold/noetic-compass/tests/test_notation_compiler.py'
    output = {
        'schema': 'cas.peer-audit.package-check/1.0', 'observed_utc': datetime.now(timezone.utc).isoformat(),
        'frozen_source': FROZEN, 'python': sys.version, 'claim_count': len(claims['claims']),
        'manifest_named_files': len(manifest['files']), 'historical_hash_checks': rows,
        'current_manifest_checks': current, 'packaged_copy_checks': copy_rows,
        'main_repository_observations': main_queries, 'parallel_branch_observations': branches,
        'preexisting_compiler_test_unchanged': blob('c3855275', old_tests) == blob(FROZEN, old_tests),
        'limitations': ['Local remote refs are not proof of historical non-publication.',
                        'Absence of run receipts cannot prove no historical model/cloud execution.',
                        'Source feature presence is checked here; runtime probes are recorded separately.'],
    }
    (HERE/'package_results.json').write_text(json.dumps(output, indent=2, ensure_ascii=True)+'\n', encoding='utf-8')
    print(json.dumps({'claim_count': len(claims['claims']), 'historical_checks': len(rows),
                      'historical_mismatches': [r for r in rows if not r['match']],
                      'current_mismatches': [r for r in current if not r['match']],
                      'copy_mismatches': [r for r in copy_rows if not r['match']],
                      'parallel_branches': branches}, indent=2))


if __name__ == '__main__':
    main()
