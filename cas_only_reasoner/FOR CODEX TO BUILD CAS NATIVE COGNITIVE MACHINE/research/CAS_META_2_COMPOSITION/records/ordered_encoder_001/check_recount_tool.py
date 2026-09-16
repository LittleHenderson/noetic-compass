"""Synthetic pure validation of the saved-vector recount; no science result."""
import builtins
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools/summarize_ordered_encoder_probe.py"
original_import = builtins.__import__
blocked = []


def guarded(name, *args, **kwargs):
    if name.split(".")[0] in {"torch", "numpy", "boto3", "botocore", "tensorflow", "jax", "casformer", "cas_cjt", "cas_meta2"}:
        blocked.append(name)
        raise AssertionError("FORBIDDEN_IMPORT:" + name)
    return original_import(name, *args, **kwargs)


def no_network(*args, **kwargs):
    raise AssertionError("NETWORK_FORBIDDEN")


builtins.__import__ = guarded
socket.socket = socket.create_connection = socket.getaddrinfo = no_network
spec = importlib.util.spec_from_file_location("recount", TOOL)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
records = Path(__file__).resolve().parent
scratch = records / "_scratch/recount_tool_synthetic_001"
assert not scratch.exists()
scratch.mkdir(parents=True)
checks = []


def reject(name, callback):
    try:
        callback()
    except tool.RecountError:
        checks.append(name)
    else:
        raise AssertionError("Refusal missing: " + name)


rows = []
for family, arm, contrast in sorted(tool.EXPECTED_KEYS):
    changed = contrast != "structural_reorder"
    baseline = [1.0] * 64
    variant = [2.0] + [1.0] * 63 if changed else list(baseline)
    distance = tool.vector_metrics(baseline, variant)["relative_l2"]
    rows.append({"family": family, "arm": arm, "contrast": contrast,
                 "answer_changed": changed, "legacy_relative_l2": 0.0,
                 "legacy_bitwise_equal": True, "ordered_relative_l2": distance,
                 "ordered_bitwise_equal": not changed,
                 "raw_vectors": {"base": {"legacy": baseline, "ordered": baseline},
                                 "variant": {"legacy": baseline, "ordered": variant}}})
result = tool.recount_rows(rows)
assert result["complete_coverage"] and result["counts"]["ordered_separated"] == 96
assert result["counts"]["legacy_near_collisions"] == 96 and result["counts"]["ordered_reorder_exact"] == 32
checks.append("complete_128_pair_recount")
assert tool.vector_metrics([0.0] * 64, [3.0, 4.0] + [0.0] * 62)["delta_l2"] == 5.0
checks.append("independent_3_4_5_norm")
assert tool.recount_rows(rows[:-1])["complete_coverage"] is False
assert len(tool.recount_rows(rows[:-1])["missing_pairs"]) == 1
checks.append("partial_coverage_retained")
reject("duplicate_pair", lambda: tool.recount_rows(rows[:-1] + [rows[0]]))
for name, field, value in (("false_distance", "ordered_relative_l2", 0.0),
                           ("false_equality", "legacy_bitwise_equal", False),
                           ("wrong_answer_metadata", "answer_changed", False),
                           ("unknown_family", "family", 16)):
    changed = deepcopy(rows)
    changed[0][field] = value
    reject(name, lambda changed=changed: tool.recount_rows(changed))
for name, vector in (("nan_coordinate", [float("nan")] + [1.0] * 63),
                     ("short_vector", [1.0] * 63), ("boolean_coordinate", [True] + [1.0] * 63)):
    changed = deepcopy(rows)
    changed[0]["raw_vectors"]["variant"]["ordered"] = vector
    reject(name, lambda changed=changed: tool.recount_rows(changed))

archive = records / "package_e47349be/source.zip"
manifest = tool.source_manifest(archive)
job = "synthetic-recount-only"
algebraic = json.loads((records / "algebraic_001/algebraic_audit.json").read_bytes())
assert tool.canonical(algebraic["source_inputs"]) == tool.canonical(manifest["inputs"])
report = {"schema": "cas-ordered-encoder-probe/1", "job": job, "source_sha": tool.SOURCE_SHA,
          "inputs": manifest["inputs"], "optimizer_updates": 0, "learner_forward_calls": 0,
          "elapsed_seconds": 2.0, "rows": rows, "checks": result["counts"],
          "projection_sha256_before": "a" * 64, "projection_sha256_after": "a" * 64,
          "projection_unchanged": True, "algebraic_audit": algebraic}


def write_fixture(report, destination, status):
    destination.mkdir()
    artifacts = destination / "artifacts"
    artifacts.mkdir()
    measurement = {key: report.get(key) for key in ("job", "source_sha", "checks", "elapsed_seconds", "projection_unchanged", "projection_sha256_before", "projection_sha256_after", "failure")}
    measurement.update(schema=report["schema"], optimizer_updates=0, learner_forward_calls=0)
    entries = []
    for name, value in (("encoder_probe.json", report), ("measurements.json", measurement)):
        raw = json.dumps(value, allow_nan=False).encode()
        (artifacts / name).write_bytes(raw)
        entries.append({"name": name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    (artifacts / "manifest.json").write_text(json.dumps({"artifacts": entries}))
    envelope = {"schema": "cas-ordered-encoder-result/1", "job": job, "status": status,
                "optimizer_updates": 0, "artifacts": entries, "summary": measurement,
                "failure": report.get("failure")}
    raw = json.dumps(envelope).encode()
    (destination / "result.json").write_bytes(raw)
    (destination / "result.json.sha256").write_text(sha256(raw).hexdigest() + "\n")
    return destination / "result.json", artifacts


result_file, artifact_directory = write_fixture(report, scratch / "complete", "ORDERED_ENCODER_DIAGNOSTIC_DELIVERED")
assert tool.analyze(result_file, artifact_directory, archive, job)["status"] == "VERIFIED_ENCODING_DIAGNOSTIC"
checks.append("synthetic_end_to_end_source_and_artifact_bindings")
partial = deepcopy(report)
partial.update(rows=rows[:2], checks=None, projection_sha256_after=None,
               projection_unchanged=None, failure={"type": "Synthetic", "message": "interrupted"})
result_file2, artifact_directory2 = write_fixture(partial, scratch / "partial", "ORDERED_ENCODER_DIAGNOSTIC_FAILED")
assert tool.analyze(result_file2, artifact_directory2, archive, job)["status"] == "VERIFIED_INCOMPLETE_DIAGNOSTIC"
checks.append("synthetic_failed_partial_preserved")
bad = deepcopy(report)
bad["checks"]["ordered_separated"] = 95
result_file3, artifact_directory3 = write_fixture(bad, scratch / "bad_check", "ORDERED_ENCODER_DIAGNOSTIC_DELIVERED")
reject("self_rehashed_wrong_declared_checks", lambda: tool.analyze(result_file3, artifact_directory3, archive, job))
(artifact_directory / "encoder_probe.json").write_bytes(b"{}")
reject("changed_raw_artifact", lambda: tool.analyze(result_file, artifact_directory, archive, job))
assert not blocked
validation = {"status": "PURE_SYNTHETIC_RECOUNT_CHECKS_PASSED", "checks": checks,
              "count": len(checks), "tool_sha256": sha256(TOOL.read_bytes()).hexdigest(),
              "forbidden_import_attempts": blocked, "provider_calls": 0, "model_calls": 0,
              "boundary": "Synthetic parser/numeric-recount/refusal validation only. No actual GPU result assessed."}
(records / "recount_tool_pure_validation.json").write_text(json.dumps(validation, indent=2) + "\n")
print(json.dumps(validation))
