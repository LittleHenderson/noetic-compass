"""Synthetic pure-data checks only; never calls verify() or reads a run result."""
import ast
import builtins
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
HELPER = HERE.parent / "verify_delivered.py"
DENIED = {"torch", "numpy", "casformer", "cas_cjt", "boto3", "botocore", "socket", "subprocess", "requests", "httpx"}
original_import = builtins.__import__


def guarded(name, *args, **kwargs):
    if name.split(".")[0] in DENIED:
        raise RuntimeError("FORBIDDEN_IMPORT:" + name)
    return original_import(name, *args, **kwargs)


class Guard:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in DENIED:
            raise RuntimeError("FORBIDDEN_IMPORT:" + fullname)


builtins.__import__ = guarded
sys.meta_path.insert(0, Guard())
spec = importlib.util.spec_from_file_location("pure_delivery_verifier", HELPER)
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
tests = []


def case(name, call, error=None):
    try:
        call()
    except ValueError as failure:
        v.require(error == str(failure), "SELFTEST_WRONG_ERROR:" + name + ":" + str(failure))
    else:
        v.require(error is None, "SELFTEST_MISSING_REFUSAL:" + name)
    tests.append({"name": name, "status": "PASSED"})


case("strict_boolean_integer", lambda: v.integer(True, 1, 64, "bound"), "bound")
case("strict_float_integer", lambda: v.integer(1.0, 1, 64, "bound"), "bound")
case("zero_update", lambda: v.integer(0, 1, 64, "bound"), "bound")
case("excess_update", lambda: v.integer(65, 1, 64, "bound"), "bound")
case("last_authorized_update", lambda: v.integer(64, 1, 64, "bound"))
case("duplicate_json_key", lambda: v.parse(b'{"a":1,"a":2}'), "DUPLICATE_JSON_KEY")
case("nonfinite_json", lambda: v.parse(b'{"a":NaN}'), "NONFINITE_JSON:NaN")
case("canonical_boolean_is_not_integer", lambda: v.same(True, 1, "alias"), "alias")
case("closed_fields", lambda: v.closed({"a": 1, "extra": 2}, {"a"}, "fields"), "fields")
for path in ("../escaped", "/absolute", "folder\\alias", "C:/absolute"):
    case("unsafe_path_" + path, lambda p=path: v.safe_relative(p), "UNSAFE_RELATIVE_PATH")

body = {"schema_version": v.SEAL_SCHEMA, "predictions": [
    {"record_id": "rpa-learning-input-" + f"{i:064x}", "public_input_digest": "a" * 64,
     "encoded_options": ["first", "second", "third"], "selected_index": i % 3} for i in range(6)],
    "answer_access": "NO_TARGET_ARGUMENT_OR_TEACHER_CALL",
    "scores": "UNAVAILABLE_TARGET_READING_LEGACY_SCORES_NOT_CALLED"}


def sealed(body_value=body, change_pin=None, raw_suffix=b""):
    raw = v.canonical(body_value) + raw_suffix
    receipt = {"path": "/remote/results/artifacts/before_predictions.json", "bytes": len(raw), "sha256": v.digest(raw)}
    if change_pin:
        change_pin(receipt)
    return v.seal(receipt, "before_predictions.json", {"before_predictions.json": raw})


case("synthetic_six_row_seal", sealed)
case("seal_hash_mismatch", lambda: sealed(change_pin=lambda r: r.update(sha256="0" * 64)), "REMOTE_ARTIFACT_PIN:before_predictions.json")
case("seal_size_float", lambda: sealed(change_pin=lambda r: r.update(bytes=float(r["bytes"]))), "REMOTE_PIN_SIZE_TYPE")
case("seal_wrong_remote_name", lambda: sealed(change_pin=lambda r: r.update(path="/remote/after_predictions.json")), "REMOTE_ARTIFACT_NAME")
case("noncanonical_seal", lambda: sealed(raw_suffix=b" "), "PREDICTION_CANONICAL")
for name, mutate, reason in (
    ("selection_boolean", lambda b: b["predictions"][0].update(selected_index=True), "PREDICTION_SELECTION"),
    ("duplicate_id", lambda b: b["predictions"][1].update(record_id=b["predictions"][0]["record_id"]), "DUPLICATE_PREDICTION_ID"),
    ("target_added", lambda b: b.update(target=1), "PREDICTION_FIELDS"),
    ("missing_row", lambda b: b["predictions"].pop(), "PREDICTION_ROWS"),
):
    changed = deepcopy(body); mutate(changed)
    case(name, lambda b=changed: sealed(b), reason)

operations = [op for op in ("LIST_PARTS", "FIND_SHARED_PART", "REACHED_VIA") for _ in range(2)]
config = {"material": {"prediction_requests": [{"operation": op} for op in operations]}}
training = {"record_ids": [row["record_id"] for row in body["predictions"]][::2]}
score_rows = [{"record_id": row["record_id"], "operation": op, "correct_index": 0,
               "selected_index": row["selected_index"], "correct": row["selected_index"] == 0}
              for row, op in zip(body["predictions"], operations)]
scoring = {phase: {"rows": deepcopy(score_rows), "correct": 2, "total": 6} for phase in ("before", "after")}


def join_check(mutate=None):
    c, t, b, s = deepcopy((config, training, body, scoring))
    if mutate:
        mutate(c, t, b, s)
    return v.prediction_training_joins(c, t, b, s)


case("valid_fixed_training_and_scoring_joins", join_check)


def changed_target_with_consistent_total(c, t, b, s):
    row = s["after"]["rows"][0]
    row.update(correct_index=1, correct=False)
    s["after"]["correct"] = 1


case("resealed_after_target_and_total_change",
     lambda: join_check(changed_target_with_consistent_total), "SCORE_PHASE_TARGET_IDENTITY")
case("after_target_integer_float_alias",
     lambda: join_check(lambda c,t,b,s: s["after"]["rows"][0].update(correct_index=0.0)), "SCORE_PHASE_TARGET_IDENTITY")
case("after_operation_changed",
     lambda: join_check(lambda c,t,b,s: s["after"]["rows"][0].update(operation="REACHED_VIA")), "SCORE_HELD_OPERATION_ORDER:after")


def coordinated_wrong_operation(c, t, b, s):
    for phase in ("before", "after"):
        s[phase]["rows"][0]["operation"] = "REACHED_VIA"


case("both_phases_same_wrong_operation",
     lambda: join_check(coordinated_wrong_operation), "SCORE_HELD_OPERATION_ORDER:before")
case("same_operation_reordered_ids",
     lambda: join_check(lambda c,t,b,s: s["after"]["rows"].__setitem__(slice(0,2), list(reversed(s["after"]["rows"][:2])))),
     "SCORE_PHASE_TARGET_IDENTITY")
case("training_ids_reordered", lambda: join_check(lambda c,t,b,s: t["record_ids"].reverse()), "TRAINING_SEALED_ID_SUBSET")
case("wrong_prediction_subset", lambda: join_check(lambda c,t,b,s: t.update(record_ids=[r["record_id"] for r in b["predictions"]][1::2])),
     "TRAINING_SEALED_ID_SUBSET")
case("duplicate_training_id", lambda: join_check(lambda c,t,b,s: t["record_ids"].__setitem__(1,t["record_ids"][0])),
     "TRAINING_SEALED_ID_SUBSET")
case("missing_training_id", lambda: join_check(lambda c,t,b,s: t["record_ids"].pop()), "TRAINING_SEALED_ID_SUBSET")
case("prediction_changes_keep_same_teacher_target",
     lambda: join_check(lambda c,t,b,s: s["after"]["rows"][0].update(selected_index=1,correct=False)))
tree = ast.parse(HELPER.read_bytes())
imports = [n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
imports += [alias.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for alias in n.names]
v.require(not DENIED.intersection(imports) and not DENIED.intersection(sys.modules), "SELFTEST_FORBIDDEN_IMPORT")
v.require(not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                  and n.func.attr in {"load", "loads"} and isinstance(n.func.value, ast.Name)
                  and n.func.value.id in {"torch", "pickle"} for n in ast.walk(tree)), "CHECKPOINT_DECODER_PRESENT")
report = {"schema": "cncm-delivery-verifier-selfcheck/1", "status": "PASSED", "cases": tests,
          "case_count": len(tests), "helper_sha256": v.digest(HELPER.read_bytes()),
          "selfcheck_sha256": v.digest(Path(__file__).read_bytes()), "model_or_provider_imports": [],
          "full_verifier_run": False, "actual_run_results_read": False,
          "boundary": "Synthetic parser/pin/seal tests only; does not establish delivered-run acceptance."}
with (HERE.parent / "verifier_development_002/selfcheck_002.json").open("xb") as stream:
    stream.write(v.canonical(report))
print(json.dumps({"status": "PASSED", "cases": len(tests), "helper_sha256": report["helper_sha256"]}))
