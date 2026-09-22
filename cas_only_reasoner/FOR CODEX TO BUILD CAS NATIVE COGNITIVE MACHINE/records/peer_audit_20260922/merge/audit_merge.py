"""Read-only audit of frozen merge parents; writes evidence only beside this script."""
import ast
import datetime
import hashlib
import importlib.util
import json
import pathlib
import platform
import subprocess
import sys
import types

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'noetic-compass-scaffold').is_dir())
FROZEN = '626cc84b574e60217a103b72d2f09388d7aa5e34'
COMPILER = 'noetic-compass-scaffold/noetic-compass/api/notation/compiler.py'
TEST = 'noetic-compass-scaffold/noetic-compass/tests/test_notation_compiler_nesting_and_defects.py'

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

def blob(ref, path):
    return git('show', ref + ':' + path)

def names(ref):
    return set(git('ls-tree', '-r', '--name-only', ref).decode().splitlines())

def functions(raw):
    tree = ast.parse(raw)
    return {n.name: {'line': n.lineno, 'end_line': n.end_lineno, 'ast': ast.dump(n, include_attributes=False)}
            for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

def module(ref):
    name = 'peer_audit_compiler_' + ref.replace('^', '_before')
    result = types.ModuleType(name)
    result.__file__ = COMPILER + '@' + ref
    sys.modules[name] = result
    exec(compile(blob(ref, COMPILER), result.__file__, 'exec'), result.__dict__)
    return result

def run_compile(mod, source):
    result = mod.compile_expression(source).to_dict()
    return {k: result.get(k) for k in ('valid', 'error', 'warnings', 'result')}

assert git('rev-parse', 'HEAD').decode().strip() == FROZEN
refs = ['c3855275', 'd50abbbc', '04547c55', '078d00ed', FROZEN]
trees = {ref: names(ref) for ref in refs}
left_changed = git('diff', '--name-only', 'c3855275', 'd50abbbc').decode().splitlines()
right_changed = set(git('diff', '--name-only', 'c3855275', '04547c55').decode().splitlines())
shared = sorted(set(left_changed) & right_changed)
inventory = []
for path in left_changed:
    row = {'path': path, 'both_parents_changed': path in right_changed,
           'present_at_merge': path in trees['078d00ed'], 'present_at_frozen': path in trees[FROZEN]}
    available = {ref: blob(ref, path) for ref in refs if path in trees[ref]}
    row['sha256'] = {ref: hashlib.sha256(raw).hexdigest() for ref, raw in available.items()}
    if path.endswith('.py'):
        parsed = {ref: functions(raw) for ref, raw in available.items()}
        row['left_functions_missing_at_merge'] = sorted(set(parsed['d50abbbc']) - set(parsed.get('078d00ed', {})))
        row['left_functions_missing_at_frozen'] = sorted(set(parsed['d50abbbc']) - set(parsed.get(FROZEN, {})))
        row['left_function_names'] = sorted(parsed['d50abbbc'])
    inventory.append(row)

union = trees['d50abbbc'] | trees['04547c55']
out = {'schema': 'cas.peer-merge-audit/1', 'frozen_commit': FROZEN,
       'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'python': sys.executable, 'python_version': platform.python_version(),
       'compiler_sha256': {ref: hashlib.sha256(blob(ref, COMPILER)).hexdigest() for ref in refs},
       'merge': git('rev-parse', '078d00ed').decode().strip(),
       'parents': git('show', '-s', '--format=%P', '078d00ed').decode().strip().split(),
       'merge_base': git('merge-base', 'd50abbbc', '04547c55').decode().strip(),
       'missing_parent_paths_at_merge': sorted(union - trees['078d00ed']),
       'missing_parent_paths_at_frozen': sorted(union - trees[FROZEN]),
       'both_parents_changed_paths': shared, 'left_change_inventory': inventory}

mods = {ref: module(ref) for ref in ['7f32129d^', '7f32129d', '04547c55', '078d00ed', FROZEN]}
expressions = {
    'drive_register': 'let X = ^8^C_{F2|A} ∘ ^3^C; let Q = {X}; Q',
    'function_cross_domain': 'fn h(s) = s ∘ ^3^O; h(^8^C)',
    'builtin_cross_domain': 'fractal(^8^C, ^3^O)',
    **{name: f'let {name} = ^2^C; {name}' for name in ['P1_count','F2_total','A','T','Noetics','Worlds','Charlie']},
    'N9_short': '^2^C ∘ ^5^C',
    'invalid_numeric_set_probe': 'let Alpha = {1,2}; let Beta = {1,2}; Beta ∈ {Alpha}',
    'set_binding_identity': 'let Alpha = {^2}; let Beta = {^2}; Beta ∈ {Alpha}',
    'set_text_forgery': 'let Alpha = {^2}; "Alpha" ∈ {Alpha}',
    'worlds_label': '(^3^P|A × ^3^P|f) = Worlds',
    'N1_direction': '^8^C ∘ ^3^C',
    'N2_identity': '^0^C ∘ ^8^C',
    'N6_alternation': '^2^C ∘ ^3^C ∘ ^2^C ∘ ^3^C',
    'N8_different_domains': '^8^C ∘ ^3^O',
    'N8_drive_register': '^2^C_{F2|T} ∘ ^3^C_{F2|A}',
    'N11_partner_readings': '^8^C ∘ ^6^C ∘ ^8^C ∘ ^6^C',
    'worlds_alias': 'Worlds',
}
out['compiler_probes'] = {name: {'source': text, 'results': {ref: run_compile(mod, text) for ref,mod in mods.items()}}
                          for name,text in expressions.items()}

# Execute the original deleted test bodies verbatim, rather than rewritten assertions.
old_text = blob('d50abbbc', TEST).decode()
(HERE / 'original_test_nesting_d50abbbc.py.txt').write_text(old_text, encoding='utf-8')
old_tree = ast.parse(old_text)
old_funcs = functions(old_text)
new_funcs = functions(blob(FROZEN, TEST))
dropped = sorted(set(old_funcs) - set(new_funcs))
out['dropped_test_runs'] = []
for ref in ['078d00ed', FROZEN]:
    compiler = mods[ref]
    namespace = {'compile_expression': compiler.compile_expression, 'RING': '∘'}
    helper = next(n for n in old_tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
    exec(compile(ast.Module(body=[helper], type_ignores=[]), TEST + '@d50abbbc', 'exec'), namespace)
    for name in dropped:
        node = next(n for n in old_tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
        case = ast.Module(body=[node], type_ignores=[])
        exec(compile(case, TEST + '@d50abbbc', 'exec'), namespace)
        record = {'ref': ref, 'test': name, 'original_line': node.lineno}
        try:
            namespace[name]()
            record['outcome'] = 'PASS'
        except Exception as exc:
            record.update(outcome='FAIL', exception=type(exc).__name__, message=str(exc))
        out['dropped_test_runs'].append(record)

canon_test = 'noetic-compass-scaffold/noetic-compass/tests/test_offline_help_text_canon.py'
canon_source = blob('7f32129d', canon_test)
(HERE / 'original_test_canon_7f32129d.py.txt').write_bytes(canon_source)
for path in ['offline-cas/cas_terminal.py', 'dist/cas-offline/cas_terminal.py',
             'noetic-compass-scaffold/noetic-compass/dashboard/src/pages/CompilerPage.tsx']:
    assert blob('078d00ed', path) == blob(FROZEN, path) == (ROOT / path).read_bytes().replace(b'\r\n', b'\n')
canon = types.ModuleType('peer_canon_original')
canon.__file__ = str(ROOT / canon_test)
sys.modules[canon.__name__] = canon
exec(compile(canon_source, canon.__file__ + '@7f32129d', 'exec'), canon.__dict__)
canon_runs = []
for name, fn in sorted(canon.__dict__.items()):
    if not name.startswith('test_') or not callable(fn):
        continue
    markers = [m for m in getattr(fn, 'pytestmark', []) if m.name == 'parametrize']
    assert len(markers) <= 1
    arguments = markers[0].args[1] if markers else [()]
    record = {'name': name, 'passed': 0, 'failures': []}
    for args in arguments:
        try:
            fn(*args)
            record['passed'] += 1
        except Exception as exc:
            record['failures'].append({'arguments': args, 'exception': type(exc).__name__, 'message': str(exc)})
    canon_runs.append(record)
out['original_canon_guards_against_merged_inputs'] = {
    'method': 'invoke original test functions with their original pytest parameter rows; all three help sources byte-verified identical to merge078d00ed',
    'functions': len(canon_runs), 'passed': sum(row['passed'] for row in canon_runs),
    'failed': sum(len(row['failures']) for row in canon_runs), 'results': canon_runs,
    'source_sha256': hashlib.sha256(canon_source).hexdigest()}

out['demo_matrix'] = []
for modref in ['7f32129d', '04547c55']:
    for demoref in ['7f32129d', '04547c55']:
        dest = HERE / 'scratch_demos' / demoref
        dest.mkdir(parents=True, exist_ok=True)
        for name in ['CAS_FULL_DEMO_APP.cas', 'CAS_FULL_DEMO_LIB.cas']:
            path = 'noetic-compass-scaffold/noetic-compass/docs/' + name
            (dest / name).write_bytes(blob(demoref, path))
        for name in ['CAS_FULL_DEMO_APP.cas', 'CAS_FULL_DEMO_LIB.cas']:
            result = mods[modref].compile_file(str(dest/name)).to_dict()
            out['demo_matrix'].append({'compiler': modref, 'demo': demoref, 'filename': name,
                                       'valid': result['valid'], 'error': result.get('error')})

target = HERE / 'merge_results.json'
target.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps({'evidence': str(target), 'missing_parent_paths': len(out['missing_parent_paths_at_frozen']),
                  'dropped_test_runs': out['dropped_test_runs'], 'demo_matrix': out['demo_matrix']}, indent=2))
