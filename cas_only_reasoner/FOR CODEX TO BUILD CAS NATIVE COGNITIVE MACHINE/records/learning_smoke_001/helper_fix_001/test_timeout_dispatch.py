"""Pure regressions for the timeout check, using the exact accepted archive."""
import ast
import builtins
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
HELPER = ROOT.parent / "rehearse_package.py"
DENIED = {"torch", "numpy", "casformer", "cas_cjt", "boto3", "botocore", "tensorflow", "jax"}
original_import = builtins.__import__


def guarded(name, *args, **kwargs):
    if name.split(".")[0] in DENIED:
        raise RuntimeError("FORBIDDEN_IMPORT:" + name)
    return original_import(name, *args, **kwargs)


class ImportGuard:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in DENIED:
            raise RuntimeError("FORBIDDEN_IMPORT:" + fullname)


builtins.__import__ = guarded
sys.meta_path.insert(0, ImportGuard())
spec = importlib.util.spec_from_file_location("pure_rehearsal_helper", HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
inspection = json.loads((ROOT / "inspection.json").read_bytes())
receipt = json.loads(Path(inspection["package_receipt"]["path"]).read_bytes())
archive_path = Path(receipt["archive"])
archive_raw = archive_path.read_bytes()
helper.require(helper.hashed(archive_raw) == inspection["archive_sha256"], "TEST_ARCHIVE_CHANGED")
with ZipFile(archive_path) as archive:
    source = archive.read("ingestion_smoke_worker.py")
helper.require(helper.hashed(source) == inspection["packaged_worker_sha256"], "TEST_WORKER_CHANGED")
baseline = ast.parse(source)
results = []


def dispatch(tree):
    return next(n for n in ast.walk(tree) if isinstance(n, ast.Call)
                and ast.unparse(n.func) == "subprocess.run"
                and any(k.arg == "timeout" for k in n.keywords))


def limit(tree):
    return next(n for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "MAX_WALL_SECONDS" for t in n.targets))


def check(name, mutate=None, error=None):
    tree = copy.deepcopy(baseline)
    if mutate:
        mutate(tree)
    ast.fix_missing_locations(tree)
    try:
        outcome = helper.checked_inner_timeout(tree)
    except RuntimeError as failure:
        helper.require(error == str(failure), "UNEXPECTED_TEST_ERROR:" + name + ":" + str(failure))
        outcome = {"refused": str(failure)}
    else:
        helper.require(error is None and outcome["timeout_seconds"] == 1200,
                       "MUTATION_WAS_NOT_REFUSED:" + name)
    results.append({"name": name, "status": "PASSED", "outcome": outcome})


check("actual_unified_archive_has_valid_execution_and_publisher_timeouts")
check("unrelated_timeout_does_not_change_execution_check",
      lambda t: t.body.append(ast.parse("another_thread.join(timeout=5)").body[0]))
for value in (1199, 1201, 1200.0, True):
    check("limit_rejects_" + repr(value), lambda t, v=value: setattr(limit(t), "value", ast.Constant(v)),
          "REHEARSAL_TIMEOUT_CONSTANT")
check("limit_cannot_be_rebound",
      lambda t: t.body.append(ast.parse("MAX_WALL_SECONDS = 1300").body[0]), "REHEARSAL_TIMEOUT_CONSTANT")
check("missing_execution_timeout", lambda t: setattr(dispatch(t), "keywords", []), "REHEARSAL_TIMEOUT_DISPATCH")
check("literal_timeout_does_not_bypass_bound_name",
      lambda t: setattr(next(k for k in dispatch(t).keywords if k.arg == "timeout"), "value", ast.Constant(1200)),
      "REHEARSAL_TIMEOUT_DISPATCH")
check("wrong_timeout_binding",
      lambda t: setattr(next(k for k in dispatch(t).keywords if k.arg == "timeout"), "value", ast.Name(id="other", ctx=ast.Load())),
      "REHEARSAL_TIMEOUT_DISPATCH")
check("keyword_expansion_refused",
      lambda t: dispatch(t).keywords.append(ast.keyword(arg=None, value=ast.Name(id="extra", ctx=ast.Load()))),
      "REHEARSAL_TIMEOUT_DISPATCH")
check("altered_runner_argv_refused", lambda t: setattr(dispatch(t), "args", [ast.List(elts=[], ctx=ast.Load())]),
      "REHEARSAL_INNER_DISPATCH")
check("duplicate_execution_dispatch_refused", lambda t: t.body.append(ast.Expr(value=copy.deepcopy(dispatch(t)))),
      "REHEARSAL_INNER_DISPATCH")


def change_result_target(tree):
    call = dispatch(tree)
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign) and n.value is call)
    node.targets[0].id = "ignored"


check("execution_result_binding_required", change_result_target, "REHEARSAL_TIMEOUT_DISPATCH")
helper.require(not DENIED.intersection(sys.modules), "FORBIDDEN_MODULE_LOADED")
helper.require(archive_path.read_bytes() == archive_raw, "TEST_ARCHIVE_MUTATED")
report = {"schema": "cncm-rehearsal-timeout-regressions/1", "status": "PASSED", "tests": results,
          "test_count": len(results), "test_source_sha256": helper.hashed(Path(__file__).read_bytes()),
          "helper_sha256": helper.hashed(HELPER.read_bytes()), "archive_sha256": helper.hashed(archive_raw),
          "numeric_calls": 0, "provider_calls": 0, "archive_unchanged": True}
helper.save(ROOT / "timeout_tests.json", report)
print(json.dumps({"status": "PASSED", "tests": len(results), "helper_sha256": report["helper_sha256"]}))
