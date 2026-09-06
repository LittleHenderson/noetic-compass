"""Read-only source/checkout gate. Only new receipt paths are written."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
META2 = HERE.parents[1]
RESEARCH = META2.parent
CNCM = RESEARCH.parent
MANIFEST = RESEARCH/'CAS_META_1_LEARNED_SELECTION/BASELINE_MANIFEST.json'
# Exact existing accepted manifest; this is not a regenerated acceptance map.
MANIFEST_SHA = '476a8bbdc7a4b07a406e46b246ed417ea1d902e04cfb852ca710de09dcbc59f0'
SOURCE = '42f9164754312f12850d9b8789c062fa7fb8069f'
ARCHIVE = META2/'records/aws_prototype_v7_source_001'
ARCHIVE_SHA = 'f9bed05bd582e0796e2c4e78ff0f5174e5e1b6a3f447e5c3eab56ad002d473f9'
ATTR = RESEARCH/'.gitattributes'
ATTRS = ('text', 'eol', 'diff', 'binary', 'filter', 'working-tree-encoding', 'ident')

def require(ok, message):
    if not ok:
        raise ValueError(message)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def git(*args, data=None):
    result = subprocess.run(['git', *args], cwd=CNCM, input=data,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(result.returncode == 0, 'GIT_FAILED:'+result.stderr.decode(errors='replace'))
    return result.stdout

def literal(path):
    require(type(path) is str and path and not path.startswith('/') and '\\' not in path
        and all(part not in ('', '.', '..') for part in path.split('/')),
        'UNSAFE_ATTRIBUTE_PATH')
    # Quote whitespace/#/! and escape glob metacharacters: paths, never patterns.
    escaped = ''.join('\\'+ch if ch in '*?[]' else ch for ch in path)
    return json.dumps('/'+escaped, ensure_ascii=True)

def policy(paths):
    return ('# Exact accepted baseline bytes: no line-ending conversion.\n'
        '# Keep readable diffs; no binary or diff attribute is set here.\n'
        '# Source: CAS_META_1_LEARNED_SELECTION/BASELINE_MANIFEST.json (316 files).\n'
        + ''.join(literal(name)+' -text\n' for name in sorted(paths))).encode()

def source_gate():
    raw = MANIFEST.read_bytes()
    require(digest(raw) == MANIFEST_SHA, 'ACCEPTED_MANIFEST_CHANGED')
    baseline = json.loads(raw)
    require(baseline['baseline_sha'] == '0917267b1354e5d036263eaa6ba9a7197eafb776'
        and len(baseline['files']) == 316, 'BASELINE_IDENTITY')
    protected = {item['path']: item['sha256'] for item in baseline['files']}
    require(len(protected) == 316, 'BASELINE_DUPLICATES')
    archive_raw = ARCHIVE.read_bytes()
    require(digest(archive_raw) == ARCHIVE_SHA, 'FROZEN_SOURCE_ARCHIVE_CHANGED')
    with zipfile.ZipFile(ARCHIVE) as z:
        launch = json.loads(z.read('launch_manifest.json'))
        mapping = launch['files_sha256']
        require(len(mapping) == 603 and len(z.infolist()) == 604, 'SOURCE_CLOSURE_COUNT')
        require(all(name.startswith('research/') for name in mapping), 'SOURCE_OUTSIDE_RESEARCH')
        require('research/.gitattributes' not in mapping and '.gitattributes' not in protected,
            'POLICY_FILE_IS_FROZEN')
        for name, pin in protected.items():
            require(mapping.get('research/'+name) == pin, 'BASELINE_SOURCE_DISAGREEMENT:'+name)
        prefix = git('rev-parse', '--show-prefix').decode().strip()
        names = sorted(mapping)
        batch = git('cat-file', '--batch', data=''.join(SOURCE+':'+prefix+name+'\n' for name in names).encode())
        offset = 0
        identities = {}
        for name in names:
            end = batch.index(b'\n', offset)
            header = batch[offset:end].split()
            require(len(header) == 3 and header[1] == b'blob', 'SOURCE_GIT_BLOB_MISSING:'+name)
            size = int(header[2]); start = end+1; git_raw = batch[start:start+size]
            require(batch[start+size:start+size+1] == b'\n', 'GIT_BATCH_DELIMITER')
            offset = start+size+1
            working = (CNCM/name).read_bytes()
            require(digest(working) == mapping[name] == digest(git_raw) == digest(z.read(name)),
                'SOURCE_RAW_GIT_ZIP_MISMATCH:'+name)
            identities[name] = {'bytes': len(working), 'sha256': mapping[name]}
        require(offset == len(batch), 'GIT_BATCH_EXTRA_BYTES')
    require(digest(ARCHIVE.read_bytes()) == ARCHIVE_SHA and digest(MANIFEST.read_bytes()) == MANIFEST_SHA,
        'SOURCE_CHANGED_DURING_GATE')
    return protected, identities

def attributes(names, *, cached=False, autocrlf=None):
    args = [] if autocrlf is None else ['-c', 'core.autocrlf='+autocrlf]
    args += ['check-attr']+(['--cached'] if cached else [])+['-z', '--stdin', *ATTRS]
    fields = git(*args, data=('\0'.join(names)+'\0').encode()).split(b'\0')
    require(fields[-1] == b'' and (len(fields)-1)%3 == 0, 'ATTRIBUTE_RESPONSE')
    result = {name: {} for name in names}
    for i in range(0, len(fields)-1, 3):
        name, attr, value = [v.decode() for v in fields[i:i+3]]
        require(name in result and attr in ATTRS and attr not in result[name], 'ATTRIBUTE_ATTRIBUTION')
        result[name][attr] = value
    require(all(set(values) == set(ATTRS) for values in result.values()), 'ATTRIBUTE_COVERAGE')
    return result

def snapshot():
    protected, source = source_gate()
    names = [name.decode() for name in git('ls-files', '-z', '--', 'research').split(b'\0') if name]
    require(len(names) == len(set(names)), 'TRACKED_PATH_DUPLICATES')
    return {'schema': 'cas-hash-bound-checkout-snapshot/1', 'source_sha': SOURCE,
        'source_archive_sha256': ARCHIVE_SHA, 'baseline_manifest_sha256': MANIFEST_SHA,
        'protected': protected, 'source_files': source, 'tracked_attributes': attributes(names),
        'policy_existed': ATTR.exists(), 'policy_sha256': digest(ATTR.read_bytes()) if ATTR.exists() else None}

def check(before):
    protected, source = source_gate()  # Must pass before policy assertions or functional tests.
    require(source == before['source_files'] and protected == before['protected'], 'SOURCE_CHANGED_SINCE_BEFORE')
    require(before['policy_existed'] is False, 'ORIGINAL_POLICY_NOT_ABSENT')
    require(ATTR.read_bytes() == policy(protected), 'POLICY_NOT_EXACT_LITERAL_MANIFEST_SCOPE')
    names = sorted(set(before['tracked_attributes']) | set(source))
    current = attributes(names)
    cached = attributes(names, cached=True)
    targets = {'research/'+name for name in protected}
    require(targets <= set(current), 'TARGET_COVERAGE')
    for name in names:
        for attr in ATTRS:
            if name in targets and attr == 'text':
                require(current[name][attr] == 'unset', 'CHECKOUT_CONVERSION_ENABLED:'+name)
            elif name in before['tracked_attributes']:
                require(current[name][attr] == before['tracked_attributes'][name][attr],
                    'UNRELATED_ATTRIBUTE_CHANGED:'+name+':'+attr)
        require(current[name]['diff'] == cached[name]['diff'] and current[name]['binary'] == cached[name]['binary'],
            'DIFF_POLICY_CHANGED:'+name)
    for name in source:
        require(current[name]['text'] == 'unset' and current[name]['filter'] == 'unspecified'
            and current[name]['working-tree-encoding'] == 'unspecified'
            and current[name]['ident'] in ('unset', 'unspecified'), 'SOURCE_CONVERSION_REMAINS:'+name)
    for setting in ('true', 'false', 'input'):
        converted = attributes(sorted(source), autocrlf=setting)
        require(all(converted[name]['text'] == 'unset' for name in source), 'AUTOCRLF_OVERRIDES_POLICY')
    final_protected, final_source = source_gate()
    require(final_protected == protected and final_source == source, 'END_SOURCE_CHANGED')
    return {'schema': 'cas-hash-bound-checkout-policy-check/1', 'status': 'CHECKOUT_POLICY_AND_MANIFEST_GATE_PASSED',
        'completed': True, 'source_sha': SOURCE, 'source_archive_sha256': ARCHIVE_SHA,
        'baseline_manifest_sha256': MANIFEST_SHA, 'protected_files': 316, 'source_files': 603,
        'new_exact_path_rules': 316, 'already_protected_other_source_files': 287,
        'tracked_paths_checked': len(before['tracked_attributes']), 'all_unrelated_attributes_unchanged': True,
        'readable_diff_policy_unchanged': True, 'source_raw_git_archive_bytes_unchanged': True,
        'autocrlf_settings_checked': ['true', 'false', 'input'], 'policy_sha256': digest(ATTR.read_bytes()),
        'functional_tests_run': False, 'model_or_provider_work': False,
        'boundary': 'Prospective checkout policy. Historical source and accepted hashes are unchanged.'}

class LiteralTests(unittest.TestCase):
    def test_normal_path(self):
        self.assertEqual(literal('A/file.py'), '\"/A/file.py\"')
    def test_spaces_and_hash(self):
        self.assertEqual(json.loads(literal('A #!/file.py')), '/A #!/file.py')
    def test_glob_escape(self):
        self.assertEqual(json.loads(literal('A/[x]*?.py')), '/A/\\[x\\]\\*\\?.py')
    def test_unsafe_paths(self):
        for name in ('/a', '../a', 'a/../b', 'a\\b', '', 'a//b'):
            with self.subTest(name=name), self.assertRaises(ValueError): literal(name)
    def test_no_diff_or_binary_flag(self):
        self.assertEqual(policy(['a']).decode().splitlines()[-1], '\"/a\" -text')

def write_new(path, value):
    path = Path(path).resolve()
    require(path.parent == HERE and not path.exists(), 'NEW_RECEIPT_IN_THIS_RECORD_REQUIRED')
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, indent=2, sort_keys=True); handle.write('\n')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture-before', action='store_true')
    parser.add_argument('--before', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    start = time.monotonic()
    if args.capture_before:
        require(args.before is None and not ATTR.exists(), 'BEFORE_REQUIRES_ABSENT_POLICY')
        result = snapshot()
    else:
        require(args.before is not None, 'BEFORE_RECEIPT_REQUIRED')
        result = check(json.loads(args.before.read_bytes()))
        tests = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LiteralTests))
        require(tests.wasSuccessful(), 'PURE_POLICY_TEST_FAILED')
        result.update(pure_tests=tests.testsRun, pure_subtests=6, before_receipt_sha256=digest(args.before.read_bytes()))
    result.update(seconds=time.monotonic()-start, command=sys.argv, verifier_sha256=digest(Path(__file__).read_bytes()))
    write_new(args.output, result)
    print(json.dumps({'status': result.get('status', 'BEFORE_CAPTURED'), 'output': str(args.output),
        'sha256': digest(args.output.read_bytes())}, sort_keys=True))

if __name__ == '__main__': main()
