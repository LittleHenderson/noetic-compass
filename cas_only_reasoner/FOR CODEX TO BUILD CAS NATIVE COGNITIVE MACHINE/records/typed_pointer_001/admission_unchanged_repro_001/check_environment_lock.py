"""Check the candidate environment lock for the unchanged-arm reproduction (helm.reproduction-environment/1).

Stdlib only. No torch, no network, no AWS. It reads git objects and writes nothing inside the repository.

What it checks, in plain words:
  1. The lock (`ENVIRONMENT_LOCK_CANDIDATE.json`) and its sources file (`ENVIRONMENT_LOCK_SOURCES.json`) are ASCII,
     LF-only, strict JSON (no duplicate keys, no NaN).
  2. Every lock field is either FILLED (its value is in the sources file with citations) or a BLOCKER (it holds the
     exact marker UNESTABLISHED_FROM_PUBLIC_HISTORICAL_RECORDS). No field is both, none is missing, and the sources
     file's blocker list is exactly the set of marked fields, in lock order.
  3. Every citation is re-read from git. Its commit must be public (an ancestor of a pushed branch the sources file
     names), and the cited value must be at the cited place. Candidate values offered for blockers are re-read the
     same way; they are NOT in the lock.
  4. The reader's own schema validator, exactly as committed, is run on the lock bytes:
       - revision 4 (fee4ebec, no blocker marker): its only complaints are the value-level ones the blockers cause,
         and with the blockers replaced by well-typed placeholders it accepts the lock outright (structure accepted);
       - revision 5 (55182f5f, explicit blocker marker): it accepts the lock, lists exactly the same blockers, and
         comparing the lock with the Helm 2.0 seed-17 recorded runtime gives UNVERIFIED for each blocker and no
         other difference.
Exit 0: every check passed. Exit 1: a check failed (each failure is printed). Exit 2: the tool could not run.

LABEL. CLAUDE_BUILT_CLAUDE_CHECKED. Not yet checked by Codex.
"""
import argparse
import copy
import io
import json
import re
import subprocess
import sys
import tempfile
import types
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
LOCK_NAME = 'ENVIRONMENT_LOCK_CANDIDATE.json'
SOURCES_NAME = 'ENVIRONMENT_LOCK_SOURCES.json'
OWN_FILES = (LOCK_NAME, SOURCES_NAME, 'ENVIRONMENT_LOCK_REPORT.md', 'check_environment_lock.py')
MARKER = 'UNESTABLISHED_FROM_PUBLIC_HISTORICAL_RECORDS'
GIT_PREFIX = 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/'
HERE_REL = 'records/typed_pointer_001/admission_unchanged_repro_001'
LOCK_SCHEMA = 'helm.reproduction-environment/1'
SOURCES_SCHEMA = 'cncm.helm-unchanged-reproduction-environment-lock-sources/1'
# The reader revisions whose schema validator is run (full commit ids).
READERS = {'4': 'fee4ebecca7457a341bc3427bb8773b040aa0666', '5': '55182f5f540cdfbbcba089b609c98a35212d9ac2'}
SHAPE = (
    ('image', ('ami_id', 'provider', 'region')),
    ('runtime', ('kernel', 'machine', 'os', 'python_implementation', 'python_version')),
    ('accelerator', ('compute_capability', 'driver_version', 'gpu_model', 'instance_type')),
    ('libraries', ('cuda_runtime', 'cudnn', 'packages', 'torch')),
    ('numerics', ('cudnn_allow_tf32', 'deterministic_algorithms', 'dtype', 'environment_variables',
                  'float32_matmul_precision', 'matmul_allow_tf32', 'seeds', 'thread_counts')),
)
LEAVES = tuple(section + '.' + key for section, keys in SHAPE for key in keys)
TOP = ('accelerator', 'comparison', 'image', 'libraries', 'numerics', 'runtime', 'schema', 'source_commit', 'status')
FILLED_CLASSES = ('RUN_RECORD', 'PACKAGE_CODE', 'PACKAGE_CODE_WITH_PINNED_LIBRARY_DEFAULT', 'IMAGE_METADATA')
CANDIDATE_CLASS = 'SAME_IMAGE_OTHER_JOB'
CITATION_KEYS = {'json': ('commit', 'equals', 'kind', 'path', 'pointer'),
                 'text': ('commit', 'contains', 'kind', 'path'),
                 'text_absent': ('absent', 'commit', 'kind', 'path'),
                 'sha256': ('commit', 'equals', 'kind', 'path'),
                 'zip_json': ('commit', 'equals', 'kind', 'member', 'path', 'pointer'),
                 'zip_text': ('commit', 'contains', 'kind', 'member', 'path'),
                 'zip_absent': ('commit', 'kind', 'path', 'pattern')}
MISSING = object()


class ToolStop(Exception):
    """The tool could not run (exit 2); never a verdict on the lock."""


def git(*args, ok_codes=(0,)):
    done = subprocess.run(['git', '-C', str(HERE), *args], capture_output=True)
    if done.returncode not in ok_codes:
        raise ToolStop('GIT_FAILED:' + ' '.join(args)[:160] + ':' + done.stderr.decode('utf-8', 'replace').strip()[:200])
    return done


def strict_json(raw):
    """A JSON value from bytes, refusing duplicate keys and NaN/Infinity (the reader's own strictness)."""
    def pairs(items):
        keys = [key for key, _ in items]
        if len(keys) != len(set(keys)):
            raise ValueError('DUPLICATE_KEY')
        return dict(items)

    def constant(name):
        raise ValueError('NON_FINITE:' + name)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def same(left, right):
    """Exact equality, type included, all the way down (True is not 1)."""
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(same(left[key], right[key]) for key in left)
    if type(left) in (list, tuple):
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


def at(value, pointer):
    for key in pointer:
        if type(key) is int and type(value) is list and 0 <= key < len(value):
            value = value[key]
        elif type(key) is str and type(value) is dict and key in value:
            value = value[key]
        else:
            return MISSING
    return value


def is_hex(value, length):
    return type(value) is str and len(value) == length and all(ch in '0123456789abcdef' for ch in value)


class Blobs:
    """Git blobs by (commit, CNCM-relative path), each read once."""

    def __init__(self):
        self.raw, self.zips = {}, {}

    def get(self, commit, path):
        key = (commit, path)
        if key not in self.raw:
            self.raw[key] = git('cat-file', 'blob', commit + ':' + GIT_PREFIX + path).stdout
        return self.raw[key]

    def archive(self, commit, path):
        key = (commit, path)
        if key not in self.zips:
            self.zips[key] = ZipFile(io.BytesIO(self.get(commit, path)))
        return self.zips[key]


def python_sources(archive):
    """(name, text) of every .py member of the archive, and of every .py inside each .whl member."""
    for name in archive.namelist():
        if name.endswith('.py'):
            yield name, archive.read(name).decode('utf-8', 'replace')
        elif name.endswith('.whl'):
            with ZipFile(io.BytesIO(archive.read(name))) as wheel:
                for inner in wheel.namelist():
                    if inner.endswith('.py'):
                        yield name + '!' + inner, wheel.read(inner).decode('utf-8', 'replace')


def citation_failure(blobs, cite):
    """None when the citation holds; otherwise a short reason."""
    kind = cite.get('kind') if type(cite) is dict else None
    if kind not in CITATION_KEYS or sorted(cite) != list(CITATION_KEYS[kind]):
        return 'CITATION_FORM'
    if not is_hex(cite['commit'], 40) or type(cite['path']) is not str or not cite['path']:
        return 'CITATION_COMMIT_OR_PATH'
    if kind == 'json':
        found = at(strict_json(blobs.get(cite['commit'], cite['path'])), cite['pointer'])
        return None if found is not MISSING and same(found, cite['equals']) else 'VALUE_IS:' + repr(found)[:80]
    if kind == 'text':
        return None if cite['contains'].encode('utf-8') in blobs.get(cite['commit'], cite['path']) else 'TEXT_ABSENT'
    if kind == 'text_absent':
        raw = blobs.get(cite['commit'], cite['path'])
        present = [item for item in cite['absent'] if item.encode('utf-8') in raw]
        return None if cite['absent'] and not present else 'PRESENT:' + ','.join(present)[:120]
    if kind == 'sha256':
        return None if sha256(blobs.get(cite['commit'], cite['path'])).hexdigest() == cite['equals'] else 'SHA256'
    archive = blobs.archive(cite['commit'], cite['path'])
    if kind == 'zip_json':
        found = at(strict_json(archive.read(cite['member'])), cite['pointer'])
        return None if found is not MISSING and same(found, cite['equals']) else 'VALUE_IS:' + repr(found)[:80]
    if kind == 'zip_text':
        return None if cite['contains'].encode('utf-8') in archive.read(cite['member']) else 'TEXT_ABSENT'
    pattern = re.compile(cite['pattern'])
    hits = [name for name, text in python_sources(archive) if pattern.search(text)]
    return None if not hits else 'PATTERN_FOUND_IN:' + ','.join(hits)[:200]


def public_failures(commits, refs):
    """Every cited commit must be an ancestor of (or equal to) at least one named pushed branch."""
    present = [ref for ref in refs if git('rev-parse', '--verify', '--quiet', ref + '^{commit}',
                                          ok_codes=(0, 1)).returncode == 0]
    if not present:
        raise ToolStop('PUBLIC_REFS_ABSENT_FETCH_THEM:' + ','.join(refs))
    failures = []
    for commit in sorted(commits):
        if not any(git('merge-base', '--is-ancestor', commit, ref, ok_codes=(0, 1)).returncode == 0
                   for ref in present):
            failures.append('COMMIT_NOT_ON_A_PUSHED_BRANCH:' + commit)
    return failures


def all_citations(sources):
    """(where, citation) for every citation in the sources file."""
    for path, entry in sources['filled'].items():
        for cite in entry.get('citations', []):
            yield 'filled:' + path, cite
    for path, entry in sources['blockers'].items():
        for part in ('established_part', 'candidate'):
            if type(entry.get(part)) is dict:
                for cite in entry[part].get('citations', []):
                    yield part + ':' + path, cite


def lock_form_failures(raw, sources):
    failures = []
    if not raw.isascii() or b'\r' in raw:
        failures.append('LOCK_NOT_ASCII_LF')
    lock = strict_json(raw)
    if type(lock) is not dict or sorted(lock) != list(TOP):
        return ['LOCK_TOP_FIELDS'], None
    if lock['schema'] != LOCK_SCHEMA or lock['status'] != 'FROZEN' or not is_hex(lock['source_commit'], 40):
        failures.append('LOCK_SCHEMA_STATUS_OR_SOURCE_COMMIT')
    if lock['source_commit'] != sources['arm']['source_sha']:
        failures.append('LOCK_SOURCE_COMMIT_IS_NOT_THE_ARM_SOURCE')
    for section, keys in SHAPE:
        if type(lock[section]) is not dict or sorted(lock[section]) != sorted(keys):
            failures.append('LOCK_SECTION:' + section)
    if failures:
        return failures, None
    if not (lock['comparison'] == {'required_equal': list(LEAVES), 'diagnostic_only': []}):
        failures.append('LOCK_COMPARISON_IS_NOT_ALL_REQUIRED_EQUAL')
    marked = [path for path in LEAVES if same(lock[path.split('.')[0]][path.split('.')[1]], MARKER)]
    filled, blockers = sources['filled'], sources['blockers']
    if sorted(list(filled) + list(blockers)) != sorted(LEAVES) or set(filled) & set(blockers):
        failures.append('SOURCES_MUST_NAME_EVERY_FIELD_EXACTLY_ONCE')
    if sources['blocker_list'] != marked or sorted(blockers) != sorted(marked):
        failures.append('BLOCKER_LIST_IS_NOT_EXACTLY_THE_MARKED_FIELDS')
    for path in LEAVES:
        section, key = path.split('.')
        if path in filled and not same(lock[section][key], filled[path].get('value')):
            failures.append('FILLED_VALUE_DIFFERS_FROM_SOURCES:' + path)
        if path in filled and not (filled[path].get('class') in FILLED_CLASSES and filled[path].get('citations')
                                   and type(filled[path].get('why')) is str and filled[path]['why'].strip()):
            failures.append('FILLED_ENTRY_FORM_OR_CLASS:' + path)
        if path in blockers:
            entry = blockers[path]
            if not (type(entry.get('why_not_established')) is str and entry['why_not_established'].strip()
                    and type(entry.get('to_resolve')) is str and entry['to_resolve'].strip()):
                failures.append('BLOCKER_ENTRY_FORM:' + path)
            candidate = entry.get('candidate')
            if candidate is not None and not (type(candidate) is dict and candidate.get('class') == CANDIDATE_CLASS
                                              and candidate.get('citations') and 'value' in candidate):
                failures.append('BLOCKER_CANDIDATE_FORM:' + path)
    return failures, lock


def load_reader(commit):
    """The reader's `repro_common` module exactly as committed at `commit`, executed from a temporary copy of this
    folder's files at that commit (so its import-time reads see that commit's pins, allowlist and rule). No bytecode
    is written; the temporary copy is removed by the caller."""
    listing = git('ls-tree', '--full-tree', '-z', commit, '--', GIT_PREFIX + HERE_REL + '/').stdout.decode('utf-8')
    holder = tempfile.TemporaryDirectory()
    folder = Path(holder.name) / 'a' / 'b' / 'c' / Path(HERE_REL).name
    folder.mkdir(parents=True)
    for entry in filter(None, listing.split('\0')):
        meta, name = entry.split('\t', 1)
        _, kind, obj = meta.split()
        if kind == 'blob':
            (folder / Path(name).name).write_bytes(git('cat-file', 'blob', obj).stdout)
    if not (folder / 'repro_common.py').is_file():
        holder.cleanup()
        raise ToolStop('READER_NOT_AT_COMMIT:' + commit)
    module = types.ModuleType('repro_common_at_' + commit[:12])
    module.__file__ = str(folder / 'repro_common.py')
    sys.modules[module.__name__] = module
    try:
        exec(compile((folder / 'repro_common.py').read_bytes(), module.__file__, 'exec'), module.__dict__)
    except BaseException as error:           # an import-time SystemExit is a tool stop, never a pass
        sys.modules.pop(module.__name__, None)
        holder.cleanup()
        raise ToolStop('READER_IMPORT_FAILED:' + commit[:12] + ':' + repr(error)[:200])
    return module, holder


def placeholder(module, path):
    """A well-typed value the revision-4 validator accepts for a blocker field (structure check only)."""
    if path == 'libraries.packages':
        return [{'name': 'placeholder', 'sha256': '0' * 64, 'version': '0'}]
    if path in module.ENVIRONMENT_MAP_LEAVES:
        return {'placeholder': 1}
    if path in module.ENVIRONMENT_BOOL_LEAVES:
        return True
    if path in module.ENVIRONMENT_OBSERVED and module.ENVIRONMENT_OBSERVED[path][1] in ('version', 'cudnn', 'torch'):
        return '1.0'
    return 'placeholder'


def reader_failures(label, commit, raw, blockers, runtime):
    failures, notes = [], []
    module, holder = load_reader(commit)
    try:
        violations, lock = module.environment_lock_violations(raw)
        if hasattr(module, 'ENVIRONMENT_UNESTABLISHED'):
            if module.ENVIRONMENT_UNESTABLISHED != MARKER:
                failures.append('R%s:READER_MARKER_IS_%s' % (label, module.ENVIRONMENT_UNESTABLISHED))
            if violations or lock is None:
                failures.append('R%s:VALIDATOR_REFUSED:%s' % (label, '|'.join(violations)[:300]))
            else:
                listed = module.environment_lock_unestablished(lock)
                if listed != blockers:
                    failures.append('R%s:READER_BLOCKERS_DIFFER:%s' % (label, ','.join(listed)))
                invalid, diagnostic, _ = module.environment_lock_comparison(lock, runtime, 'REFERENCE_TRAINING',
                                                                            must_observe=False)
                expected = [module.ENVIRONMENT_UNVERIFIED + ':REFERENCE_TRAINING:' + path for path in blockers]
                if invalid != expected:
                    failures.append('R%s:HISTORICAL_RUNTIME_COMPARISON:%s' % (label, '|'.join(invalid)[:300]))
                notes.append('R%s (%s): validator ACCEPTS the lock; %d blockers read %s; the Helm 2.0 seed-17 recorded '
                             'runtime differs from no filled field (%d diagnostic rows).'
                             % (label, commit[:8], len(listed), module.ENVIRONMENT_UNVERIFIED, len(diagnostic)))
        else:
            expected = []
            for path in blockers:
                if (path == 'libraries.packages' or path in module.ENVIRONMENT_MAP_LEAVES
                        or path in module.ENVIRONMENT_BOOL_LEAVES):
                    expected.append('LOCK_VALUE:' + path)
                elif path in module.ENVIRONMENT_OBSERVED and module.ENVIRONMENT_OBSERVED[path][1] != 'text':
                    expected.append('LOCK_VALUE_UNPARSEABLE:' + path)
            if sorted(violations) != sorted(expected) or lock is not None:
                failures.append('R%s:VIOLATIONS_ARE_NOT_EXACTLY_THE_BLOCKERS:%s' % (label, '|'.join(violations)[:300]))
            substituted = strict_json(raw)
            for path in blockers:
                section, key = path.split('.')
                substituted[section][key] = placeholder(module, path)
            again, accepted = module.environment_lock_violations(json.dumps(substituted).encode('ascii'))
            if again or accepted is None:
                failures.append('R%s:STRUCTURE_REFUSED:%s' % (label, '|'.join(again)[:300]))
            else:
                invalid, _, _ = module.environment_lock_comparison(accepted, runtime, 'REFERENCE_TRAINING',
                                                                   must_observe=False)
                if invalid:
                    failures.append('R%s:HISTORICAL_RUNTIME_COMPARISON:%s' % (label, '|'.join(invalid)[:300]))
            text_blockers = sorted(set(blockers) - {item.split(':', 1)[1] for item in expected})
            notes.append('R%s (%s): structure ACCEPTED (placeholder check); value-level refusals exactly the %d '
                         'expected; %s hold the marker as plain text, which revision 4 cannot tell from a value '
                         '(they still fail closed at comparison; revision 5 names them explicitly).'
                         % (label, commit[:8], len(expected), ','.join(text_blockers) or 'no fields'))
    finally:
        sys.modules.pop(module.__name__, None)
        holder.cleanup()
    return failures, notes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--reader', action='append', metavar='LABEL=COMMIT',
                        help='run this reader revision too (default: revisions 4 and 5)')
    args = parser.parse_args(argv)
    readers = dict(READERS)
    for item in args.reader or []:
        label, _, commit = item.partition('=')
        if not is_hex(commit, 40):
            raise ToolStop('READER_ARGUMENT:' + item)
        readers[label] = commit
    failures, notes = [], []
    for name in OWN_FILES:
        path = HERE / name
        if path.is_file():
            raw = path.read_bytes()
            if not raw.isascii() or b'\r' in raw:
                failures.append('NOT_ASCII_LF:' + name)
    sources_raw = (HERE / SOURCES_NAME).read_bytes()
    sources = strict_json(sources_raw)
    if not (type(sources) is dict and sources.get('schema') == SOURCES_SCHEMA
            and sources.get('unestablished_marker') == MARKER):
        raise ToolStop('SOURCES_FILE_FORM')
    lock_raw = (HERE / LOCK_NAME).read_bytes()
    found, lock = lock_form_failures(lock_raw, sources)
    failures.extend(found)
    blobs, commits, checked = Blobs(), set(), 0
    for where, cite in all_citations(sources):
        reason = citation_failure(blobs, cite)
        checked += 1
        if type(cite) is dict and is_hex(cite.get('commit'), 40):
            commits.add(cite['commit'])
        if reason:
            failures.append('CITATION:' + where + ':' + str(cite.get('path') if type(cite) is dict else cite)[-80:]
                            + ':' + reason)
    failures.extend(public_failures(commits, sources['public_refs']))
    reference = sources['arm']['reference_receipt']
    report = strict_json(blobs.get(reference['commit'], reference['path']
                                   + '/collected/results/artifacts/worker_report.json'))
    runtime = report.get('runtime') if type(report) is dict else None
    if lock is not None:
        for label, commit in sorted(readers.items()):
            found, said = reader_failures(label, commit, lock_raw, sources['blocker_list'], runtime)
            failures.extend(found)
            notes.extend(said)
    for line in notes:
        print('NOTE ' + line)
    for line in failures:
        print('FAIL ' + line)
    summary = {'lock_sha256': sha256(lock_raw).hexdigest(), 'sources_sha256': sha256(sources_raw).hexdigest(),
               'citations_reread': checked, 'distinct_public_commits': len(commits),
               'filled': len(sources['filled']), 'blockers': sources['blocker_list'],
               'readers': {label: commit for label, commit in sorted(readers.items())},
               'result': 'FAIL' if failures else 'PASS'}
    print('ENVIRONMENT_LOCK_CHECK ' + json.dumps(summary, sort_keys=True))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    try:
        sys.exit(main())
    except ToolStop as stop:
        print('TOOL_STOP ' + str(stop))
        sys.exit(2)
