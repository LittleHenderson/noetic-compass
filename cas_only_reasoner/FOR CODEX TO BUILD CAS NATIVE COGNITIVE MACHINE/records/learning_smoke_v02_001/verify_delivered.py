"""Data-only delivery verification for the single-graph input-v0.2 smoke.

The preserved v0.1 verifier remains byte-identical. Its measured-evidence
function is reused with one structurally checked AST substitution: the old
rendering-version comparison becomes an explicit exact-v0.2 predicate. Every
other inherited check remains unchanged. Neither verifier decodes checkpoints,
imports project code, runs a model, nor contacts a provider.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
RECORDS = Path(__file__).resolve().parent
BASE_PATH = ROOT / "records/learning_smoke_001/verify_delivered.py"
BASE_SHA256 = "318b36e66225ed90f8c2da533fd9ee8685f7d6940c3ef7a75c5a4ebac2c7898c"
SCHEMA = "cncm-ingestion-v02-delivered-verification/1"
RENDERING_SCHEMA = "cncm.cube-contains-node-rel/0.2"
ADAPTER_PATH = "cncm/rpa_learning_adapter.py"
FIXTURE_PATH = "research/CAS_META_2_COMPOSITION/records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/cube_node_001/Cube_Node_Example_v0.1.json"
FIXTURE_SHA256 = "9e62538b807d0b7a6fc04890c4ee0504db53e45bc34b62504f001d7f0610eb32"
INVENTORY_DECLARATION = (
    "Containment inventory is complete within this supplied snapshot; "
    "an unlisted direct contains relation is absent from this snapshot."
)
EXPECTED_CONSTANTS = {
    "PREPARED_SCHEMA": "cncm.rpa-learning-prepared/0.2",
    "LESSON_SCHEMA": "cncm.rpa-learning-lesson/0.2",
    "RENDERING_SCHEMA": RENDERING_SCHEMA,
    "INVENTORY_DECLARATION": INVENTORY_DECLARATION,
}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def digest(raw):
    return sha256(raw).hexdigest()


def exact_v02_rendering(value):
    return type(value) is str and value == RENDERING_SCHEMA


def _adapt_measurement_tree(tree):
    """Replace one exact comparison, and prove all remaining AST is identical."""
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == "measured_evidence"]
    require(len(functions) == 1, "V02_INHERITED_MEASUREMENT_FUNCTION")
    original = deepcopy(functions[0])
    adapted = deepcopy(original)
    expected = ast.parse("source['rendering_schema'] == 'cncm.cube-contains-node-rel/0.1'", mode="eval").body
    expected_dump = ast.dump(expected, include_attributes=False)
    count = 0

    class Upgrade(ast.NodeTransformer):
        def visit_Compare(self, node):
            nonlocal count
            if ast.dump(node, include_attributes=False) == expected_dump:
                count += 1
                return ast.copy_location(ast.Call(
                    func=ast.Name(id="exact_v02_rendering", ctx=ast.Load()),
                    args=[deepcopy(node.left)], keywords=[]), node)
            return self.generic_visit(node)

    adapted = Upgrade().visit(adapted)
    require(count == 1, "V02_UNIQUE_SCHEMA_GUARD_REQUIRED")
    restored = deepcopy(adapted)
    restore_count = 0

    class Restore(ast.NodeTransformer):
        def visit_Call(self, node):
            nonlocal restore_count
            if isinstance(node.func, ast.Name) and node.func.id == "exact_v02_rendering":
                require(len(node.args) == 1 and not node.keywords and ast.dump(node.args[0], include_attributes=False)
                        == ast.dump(expected.left, include_attributes=False), "V02_ADAPTATION_ARGUMENT_CHANGED")
                restore_count += 1
                return ast.copy_location(deepcopy(expected), node)
            return self.generic_visit(node)

    restored = Restore().visit(restored)
    require(restore_count == 1 and ast.dump(restored, include_attributes=False)
            == ast.dump(original, include_attributes=False), "V02_OTHER_INHERITED_LOGIC_CHANGED")
    return adapted, {
        "rule": "unique source.rendering_schema comparison becomes exact_v02_rendering",
        "comparisons_replaced": count,
        "all_other_function_ast_unchanged": True,
        "original_function_ast_sha256": digest(ast.dump(original, include_attributes=False).encode()),
        "adapted_function_ast_sha256": digest(ast.dump(adapted, include_attributes=False).encode()),
    }


def load_base():
    require(BASE_PATH.is_file() and not BASE_PATH.is_symlink()
            and BASE_PATH.resolve().is_relative_to(ROOT), "V02_INHERITED_PATH")
    raw = BASE_PATH.read_bytes()
    require(digest(raw) == BASE_SHA256, "V02_INHERITED_SOURCE_CHANGED")
    tree = ast.parse(raw, str(BASE_PATH))
    function, adaptation = _adapt_measurement_tree(tree)
    base = ModuleType("cncm_preserved_delivery_verifier")
    base.__file__ = str(BASE_PATH)
    exec(compile(tree, str(BASE_PATH), "exec"), base.__dict__)
    namespace = dict(base.__dict__)
    namespace["exact_v02_rendering"] = exact_v02_rendering
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])),
                 str(Path(__file__)) + "::v02_measurement_guard", "exec"), namespace)
    return base, namespace["measured_evidence"], adaptation


def check_v02_package(base, config, members, *, source_commit, adapter_source_sha256):
    """Bind the caller-selected source and exact packaged input-v0.2 contract."""
    require(type(source_commit) is str and re.fullmatch(r"[a-f0-9]{40}", source_commit), "V02_SOURCE_COMMIT")
    base.hex64(adapter_source_sha256)
    require(config["source_sha"] == source_commit, "V02_CALLER_SOURCE_COMMIT_MISMATCH")
    raw = members[ADAPTER_PATH]
    require(type(raw) is bytes and digest(raw) == adapter_source_sha256, "V02_CALLER_ADAPTER_SOURCE_MISMATCH")
    constants = {}
    for node in ast.parse(raw, ADAPTER_PATH).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in EXPECTED_CONSTANTS:
                    require(target.id not in constants, "V02_DUPLICATE_ADAPTER_CONSTANT")
                    constants[target.id] = ast.literal_eval(node.value)
    require(constants == EXPECTED_CONSTANTS and all(type(value) is str for value in constants.values()),
            "V02_PACKAGED_ADAPTER_CONTRACT")
    require(digest(members[FIXTURE_PATH]) == FIXTURE_SHA256, "V02_EXPOSED_FIXTURE_CHANGED")
    fixture = base.parse(members[FIXTURE_PATH])
    require(fixture["context"]["contains_inventory_complete"] is True,
            "V02_EXACT_COMPLETE_SNAPSHOT_REQUIRED")
    return {"source_commit": source_commit, "adapter_source_sha256": adapter_source_sha256,
            "rendering_schema": RENDERING_SCHEMA, "expected_constants": constants,
            "fixture_sha256": FIXTURE_SHA256, "contains_inventory_complete": True,
            "boundary": "Caller-bound packaged source declarations and recorded runtime metadata; no source authenticity or independent numerical proof."}


def check_v02_checkpoint_contexts(base, artifacts):
    """Check both unmodified delivered metadata documents before inherited checks."""
    for phase in ("initial", "final"):
        record = base.parse(artifacts[phase + "_checkpoint.json"])
        source = record["metadata"]["source_binding"]
        base.closed(source, base.SOURCE_CONTEXT_FIELDS, "V02_CHECKPOINT_SOURCE_FIELDS")
        require(exact_v02_rendering(source["rendering_schema"]), "V02_CHECKPOINT_RENDERING_REQUIRED")
        require(source["source_authorship_authenticated"] is False
                and source["world_truth_established"] is False, "V02_UNSUPPORTED_SOURCE_AUTHORITY")
    return True


def verify(result_path, expected, output, *, source_commit, adapter_source_sha256):
    """Retain success or failure receipts; evidence inputs are never repaired."""
    result_path, output = Path(result_path).absolute(), Path(output).absolute()
    require(output.resolve().is_relative_to(RECORDS) and not output.exists()
            and output.parent.is_dir(), "V02_NEW_OUTPUT_REQUIRED")
    output.mkdir()
    helper_raw = Path(__file__).read_bytes()
    report = {"schema": SCHEMA, "status": "FAILED_OR_PARTIAL", "accepted": False,
        "learning_improvement_established": False, "helper_sha256": digest(helper_raw),
        "inherited_verifier_sha256": BASE_SHA256, "caller_result_sha256": expected,
        "caller_source_commit": source_commit, "caller_adapter_source_sha256": adapter_source_sha256,
        "numeric_or_checkpoint_decoder_calls": 0, "provider_calls": 0,
        "boundary": "Caller-pinned local v0.2 evidence integrity and reported single-graph smoke only. No independent numerical rerun, authentication, held-out learning, budget settlement, full-course scope verification, or live provider-cleanup claim."}
    audit = None
    try:
        base, measured, adaptation = load_base()
        audit = base.Audit()
        audit.pin(BASE_PATH, BASE_SHA256)
        audit.pin(Path(__file__), report["helper_sha256"])
        report["inherited_adaptation"] = adaptation
        result = base.parse(audit.pin(result_path, expected))
        report.update(lifecycle_status=result.get("status"), job=result.get("job"))
        directory = result_path.parent
        require(Path(result["receipt_dir"]).resolve() == directory.resolve(), "LIFECYCLE_DIRECTORY_BINDING")
        config, contract, package = base.held_inputs(audit, result, directory)
        report.update(source_sha=config["source_sha"], archive_sha256=package["archive_sha256"])
        members, manifest = base.source_package(audit, package, config)
        report["input_v02_contract"] = check_v02_package(base, config, members,
            source_commit=source_commit, adapter_source_sha256=adapter_source_sha256)
        audit.done("caller_commit_adapter_pin_and_complete_input_v02_source_contract")
        envelope, artifacts = base.collected_files(audit, result, directory, contract)
        check_v02_checkpoint_contexts(base, artifacts)
        report["measurements"] = measured(audit, result, config, envelope, artifacts, members, manifest)
        require(result["status"] == "AWS_CANDIDATE_FINISHED"
                and result["outcome"]["worker_status"] == "REMOTE_FINISHED", "LIFECYCLE_FAILED_OR_PARTIAL")
        audit.done("lifecycle_and_worker_success_agree")
        for row in list(audit.files.values()):
            audit.pin(row["path"], row["sha256"])
        require(Path(__file__).read_bytes() == helper_raw, "V02_VERIFIER_SOURCE_CHANGED")
        report.update(status="RECORDED_INPUT_V02_MECHANICAL_EVIDENCE_VERIFIED", accepted=True)
    except Exception as error:
        report["failure"] = {"type": type(error).__name__, "detail": str(error)[:1000]}
    report["checks_completed"] = audit.checks if audit is not None else []
    report["inputs"] = sorted(audit.files.values(), key=lambda row: row["path"]) if audit is not None else []
    raw = (json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode()
    with (output / "receipt.json").open("xb") as stream:
        stream.write(raw)
    require((output / "receipt.json").read_bytes() == raw, "V02_RECEIPT_WRITE_READBACK")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lifecycle-result", required=True)
    parser.add_argument("--lifecycle-result-sha256", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--adapter-source-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = verify(args.lifecycle_result, args.lifecycle_result_sha256, args.output,
        source_commit=args.source_commit, adapter_source_sha256=args.adapter_source_sha256)
    print(json.dumps({key: report.get(key) for key in ("status", "accepted", "job", "failure")}))
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
