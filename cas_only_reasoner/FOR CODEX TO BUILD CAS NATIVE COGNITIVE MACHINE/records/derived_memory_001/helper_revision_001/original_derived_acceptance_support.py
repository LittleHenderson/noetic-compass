"""Shared actual-source acceptance support for derived-memory reproduction.

No imports of model providers. Refuse overwriting any retained output.
"""
from __future__ import annotations
from contextlib import contextmanager
from hashlib import sha256
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from cncm.canonical import canonical_json, digest

FORBIDDEN_IMPORTS = frozenset({"torch", "transformers", "boto3", "botocore", "openai", "requests", "httpx"})

class DenyProviders:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN_IMPORTS:
            raise AssertionError("forbidden model/provider import: "+fullname)

@contextmanager
def no_models_or_providers():
    blocker = DenyProviders()
    present = sorted(set(sys.modules) & FORBIDDEN_IMPORTS)
    assert not present, ("forbidden imports already loaded", present)
    sys.meta_path.insert(0, blocker)
    try:
        yield
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
    path = Path(path)
    raw = path.read_bytes()
    return {"path":path.relative_to(ROOT).as_posix(),"bytes":len(raw),"sha256":sha256(raw).hexdigest()}

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
    points = ((derived,"generate_candidate"),(derived,"inspect_memory"),
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
