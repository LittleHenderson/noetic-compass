"""Shared actual-source acceptance support for derived-memory reproduction.

No imports of model providers. Refuse overwriting any retained output.
"""
from __future__ import annotations
from contextlib import contextmanager
from hashlib import sha256
import ast
import json
from pathlib import Path
import sys
from unittest.mock import patch
from xml.etree import ElementTree

ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent/'cncm/derived_model.py').is_file() and (parent/'cas_reasoner.txt').is_file())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)

def digest(value):
    return sha256(canonical_json(value).encode()).hexdigest()

def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)

FORBIDDEN_IMPORTS = frozenset({'numpy', 'torch', 'transformers', 'tensorflow', 'jax', 'vllm',
                             'boto3', 'botocore', 'openai', 'anthropic', 'requests', 'httpx'})

class DenyProviders:
    def __init__(self):
        self.attempts = []
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN_IMPORTS:
            self.attempts.append(fullname)
            raise AssertionError("forbidden model/provider import: "+fullname)

@contextmanager
def no_models_or_providers():
    blocker = DenyProviders()
    present = sorted(set(sys.modules) & FORBIDDEN_IMPORTS)
    assert not present, ("forbidden imports already loaded", present)
    sys.meta_path.insert(0, blocker)
    try:
        yield blocker.attempts
    finally:
        sys.meta_path.remove(blocker)

def write_new(path, value):
    raw = value if type(value) is bytes else (canonical_json(value)+"\n").encode()
    with Path(path).open("xb") as stream:
        stream.write(raw)
    return {"bytes":len(raw), "sha256":sha256(raw).hexdigest()}

def read(path):
    return json.loads(Path(path).read_bytes())

def identity(path):
    path = Path(path).resolve()
    require(path.is_relative_to(ROOT), 'declared file must be within CNCM root')
    raw = path.read_bytes()
    return {"path":path.relative_to(ROOT).as_posix(),"bytes":len(raw),"sha256":sha256(raw).hexdigest()}

SUPPORT_BOOT_IDENTITY = identity(__file__)

def interpreter_identity():
    require(sys.flags.optimize == 0, 'acceptance requires Python optimization disabled; assert gates must execute')
    return {'executable':str(Path(sys.executable).resolve()),
            'executable_sha256':sha256(Path(sys.executable).read_bytes()).hexdigest(),
            'version':sys.version, 'implementation':sys.implementation.name,
            'optimize':sys.flags.optimize, 'dont_write_bytecode':sys.dont_write_bytecode}

def runtime_source_names():
    """Read only tuple/name/addition SOURCE_FILES expressions, without importing runtime."""
    cache = {}
    def read_profile(name):
        if name in cache:
            return cache[name]
        tree = ast.parse((ROOT/name).read_bytes(), filename=name)
        aliases = {}
        expression = None
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
                for alias in node.names:
                    if alias.name == 'SOURCE_FILES':
                        aliases[alias.asname or alias.name] = 'cncm/'+node.module.replace('.', '/')+'.py'
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SOURCE_FILES' for t in node.targets):
                expression = node.value
        def evaluate(node):
            if isinstance(node, ast.Tuple):
                require(all(isinstance(v, ast.Constant) and type(v.value) is str for v in node.elts), 'SOURCE_FILES must contain literal paths')
                return tuple(v.value for v in node.elts)
            if isinstance(node, ast.Name) and node.id in aliases:
                return read_profile(aliases[node.id])
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                return evaluate(node.left)+evaluate(node.right)
            raise RuntimeError('unsupported static SOURCE_FILES expression: '+name)
        cache[name] = evaluate(expression)
        return cache[name]
    return read_profile('cncm/derived_profile.py')

def import_closure(paths):
    """Pin local static import dependencies, including cncm package initialization."""
    pending = {name for name in paths if name.endswith('.py')} | {'cncm/__init__.py'}
    result = set()
    while pending:
        name = pending.pop()
        if name in result:
            continue
        require((ROOT/name).is_file(), 'missing declared Python source: '+name)
        result.add(name)
        tree = ast.parse((ROOT/name).read_bytes(), filename=name)
        modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names if alias.name.startswith('cncm.'))
            elif isinstance(node, ast.ImportFrom):
                if node.level and name.startswith('cncm/'):
                    require(node.level == 1, 'unexpected local relative import level')
                    modules.extend(['cncm.'+node.module] if node.module else ['cncm.'+a.name for a in node.names])
                elif node.module and (node.module == 'cncm' or node.module.startswith('cncm.')):
                    modules.append(node.module)
        for module in modules:
            candidate = module.replace('.', '/')
            if (ROOT/(candidate+'.py')).is_file():
                pending.add(candidate+'.py')
            elif (ROOT/candidate/'__init__.py').is_file():
                pending.add(candidate+'/__init__.py')
    return sorted(result)

def junit_summary(path):
    source_identity = identity(path)
    tree = ElementTree.parse(path)
    root = tree.getroot()
    require(root.tag in {'testsuite','testsuites'}, 'retained evidence must be JUnit XML')
    cases = list(root.iter('testcase'))
    suites = list(root.iter('testsuite'))
    failures, errors, skipped = (sum(len(list(case.iter(name))) for case in cases)
                                 for name in ('failure', 'error', 'skipped'))
    require(cases and suites and not failures and not errors and len(cases)>skipped,
            'retained JUnit report must contain executed cases with no failures/errors')
    for suite in suites:
        for name in ('failures','errors'):
            raw = suite.attrib.get(name,'0')
            require(raw.isdecimal() and int(raw)==0, 'reported JUnit failure/error count is nonzero or invalid')
    return {'identity':source_identity, 'testcase_elements':len(cases),
            'failure_elements':failures, 'error_elements':errors, 'skipped_elements':skipped,
            'reported_suite_counts':[{k:s.attrib[k] for k in ('name','tests','failures','errors','skipped') if k in s.attrib} for s in suites],
            'boundary':'Retained report input, not a test rerun; testcase elements and reported counts are distinct. This helper does not establish which historical source bytes generated this report.'}

def declared_inputs(helper, support, test_evidence):
    names = runtime_source_names()
    roles = {}
    def add(path, role):
        row = identity(path)
        roles.setdefault(row['path'], {'identity':row, 'roles':[]})['roles'].append(role)
    for name in names:
        add(ROOT/name, 'runtime_profile')
    for name in import_closure(names):
        add(ROOT/name, 'static_import_dependency')
    add(helper, 'acceptance_helper'); add(support, 'acceptance_support')
    add(ROOT/'records/derived_memory_001/source_baseline.json', 'preservation_baseline')
    tests = sorted(ROOT.glob('tests/test_derived*.py'))
    require(tests, 'derived test sources missing')
    for path in tests:
        add(path, 'derived_test_source')
    require(test_evidence, 'at least one retained JUnit report is required')
    reports = []
    for path in test_evidence:
        reports.append(junit_summary(path)); add(path, 'retained_junit_evidence')
    return {'runtime_source_names':list(names), 'files':[roles[k] for k in sorted(roles)],
            'junit_reports':reports, 'freeze_boundary':'Declared inputs and actual imported files only; unrelated unimported viewer modules are outside this freeze.'}

def verify_declared(manifest):
    for item in manifest['files']:
        row = item['identity']
        require(identity(ROOT/row['path']) == row, 'declared input changed: '+row['path'])
    expected_tests = {r['identity']['path'] for r in manifest['files'] if 'derived_test_source' in r['roles']}
    require({p.relative_to(ROOT).as_posix() for p in ROOT.glob('tests/test_derived*.py')} == expected_tests,
            'derived test inventory changed')

def verify_imported_subset(manifest):
    known = {row['identity']['path']:row['identity'] for row in manifest['files']}
    actual = imported_source_inventory()
    for row in actual:
        require(known.get(row['path']) == row, 'unbound or changed imported source: '+row['path'])
    return actual

def checked_manifest(path, expected_sha256):
    raw = Path(path).read_bytes()
    require(type(expected_sha256) is str and len(expected_sha256) == 64
            and sha256(raw).hexdigest() == expected_sha256, 'child manifest differs from parent-held SHA-256')
    manifest = json.loads(raw)
    require(manifest['schema_version'] == 'cncm.derived-child-input-manifest/0.1', 'child manifest version invalid')
    for row in manifest['artifacts']:
        require(identity(ROOT/row['path']) == row, 'child input changed: '+row['path'])
    verify_declared(manifest['declared_inputs'])
    return manifest

def policy_guard(*, allow_generation, allow_acquisition):
    import cncm.compound_kernel as compound
    import cncm.derived_kernel as derived
    targets = []
    if not allow_generation:
        targets.append((derived,'generate_candidate'))
    if not allow_acquisition:
        targets.extend((compound,name) for name in ('construct_program','qualify_program','select_finite_candidate','qualify_procedure'))
    return deny_new_generation(tuple(targets))

def require_stale_refusal(result, machine, correction, work):
    require(result.output is None and result.terminal_status.value == 'NEEDS_INFORMATION', 'stale task must request information')
    state = machine.state
    require(state.derived_failure == 'GENERATION_DISABLED' and state.memory_failure is None,
            'stale task failed for another reason')
    require(correction in state.memory_statements and not state.rpm_stack and state.compound_call is None
            and state.commitment_state.decision_status == 'UNCOMMITTED', 'stale task executed, committed, or missed correction')
    inspections = [r.body_dict() for r in state.derived_records if r.kind == 'INSPECTION' and r.body_dict()['run_id'] == state.run_id]
    require(len(inspections) == 1 and inspections[0]['report']['status'] == 'STALE'
            and inspections[0]['report']['reason'] == 'STALE_FORMAL_INPUTS', 'expected exact stale support refusal missing')
    require(work['cncm.derived_kernel.generate_candidate'] == 0
            and work['cncm.compound_kernel.check_program_call'] == 0, 'stale refusal performed generation or numeric dispatch')

def verify_preservation():
    baseline = read(ROOT/"records/derived_memory_001/source_baseline.json")
    for row in baseline["accepted_sources"]+baseline["preserved_negative_records"]:
        assert identity(ROOT/row["path"]) == row, ("preserved file changed",row["path"])
    from cncm.native_profile import load_native_profile
    from cncm.nested_profile import load_nested_profile
    from cncm.semantic_profile import load_semantic_profile
    from cncm.compound_profile import load_compound_profile
    profiles={name:loader().profile_digest for name,loader in (
        ("native0.2",load_native_profile),("nested0.3",load_nested_profile),
        ("semantic0.4",load_semantic_profile),("compound0.5",load_compound_profile))}
    assert profiles == baseline["profiles"]
    return {"accepted_sources":len(baseline["accepted_sources"]),
            "negative_records":len(baseline["preserved_negative_records"]),"profiles":profiles}

def imported_source_inventory():
    rows = {}
    for module in tuple(sys.modules.values()):
        filename = getattr(module,"__file__",None)
        if not filename:
            continue
        source = Path(filename).resolve()
        if source.suffix == ".py" and source.is_relative_to(ROOT):
            row = identity(source)
            rows[row["path"]] = row
    return [rows[key] for key in sorted(rows)]

@contextmanager
def deny_new_generation(candidate_targets):
    """Install after historical recovery; fail on every new generation attempt."""
    attempts = []
    patches = []
    def forbidden(name):
        def fail(*args, **kwargs):
            attempts.append(name)
            raise AssertionError("new generation/acquisition called: "+name)
        return fail
    try:
        for module,attribute in candidate_targets:
            label = module.__name__+"."+attribute
            change = patch.object(module,attribute,forbidden(label))
            change.start()
            patches.append(change)
        yield attempts
    finally:
        for change in reversed(patches):
            change.stop()

def allocation_conservation(machine):
    """Validate recorded funded work; policy allowances are not measured CPU work."""
    journal=machine.journal()
    rows=[]
    for episode_index,episode in enumerate(journal["episodes"]):
        state=episode["final_state"]
        expected=episode["problem"]["budget"]
        allocated={"instructions":0,"checker_calls":0}
        for field in ("native_records","semantic_records","compound_records","derived_records"):
            for record in state.get(field,[]):
                if record.get("kind") != "WORK_RESERVATION":
                    continue
                body=json.loads(record["body_json"])
                if body.get("run_id") != state["run_id"]:
                    continue
                for public,stored in (("instructions","instructions_allocated"),
                                      ("checker_calls","checker_calls_allocated")):
                    value=body[stored]
                    assert type(value) is int and value>=0
                    allocated[public]+=value
                before,after=body["before"],body["after"]
                assert before["instructions_remaining"]-after["instructions_remaining"] == body["instructions_allocated"]
                assert before["checker_calls_remaining"]-after["checker_calls_remaining"] == body["checker_calls_allocated"]
        remaining=state["native_budget"]
        assert expected["instructions_remaining"]-allocated["instructions"]==remaining["instructions_remaining"]
        assert expected["checker_calls_remaining"]-allocated["checker_calls"]==remaining["checker_calls_remaining"]
        rows.append({"episode":episode_index,"allocated":allocated,"remaining":remaining})
    return rows


@contextmanager
def observe_work():
    """Count actual new work at pinned call boundaries, independently of budgets."""
    import cncm.compound_kernel as compound
    import cncm.derived_kernel as derived
    import cncm.derived_verification as verifier
    import cncm.math_kernel as math_kernel
    points = ((derived,"generate_candidate"),(derived,"inspect_memory"),(verifier,"inspect_memory"),
              (compound,"check_program_call"),(verifier,"check_math_step"),
              (math_kernel,"check_math_step"))
    counts = {module.__name__+"."+name:0 for module,name in points}
    patches = []
    def wrapper(label,original):
        def call(*args,**kwargs):
            counts[label]+=1
            return original(*args,**kwargs)
        return call
    try:
        for module,name in points:
            label=module.__name__+"."+name
            change=patch.object(module,name,wrapper(label,getattr(module,name)))
            change.start(); patches.append(change)
        yield counts
    finally:
        for change in reversed(patches):
            change.stop()
