"""Independently recount saved encoder vectors using only Python's standard library.

No model, tensor library, provider, network, worker source or checkpoint is loaded.
This checks recorded numeric evidence; it is not another GPU execution.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path, PurePosixPath
import re
from zipfile import ZipFile

SOURCE_SHA = "e47349be13ee5449d31ae8d5cc3962ae2571ba15"
ARCHIVE_SHA = "57b17ab62301a4f026cde31fe54bec7e3988ee26f08a54e8072b1b6f6e167a0c"
MANIFEST_SHA = "0f23fb81dd93b143c7edbe1d425fd23bc70c2f02769cd3f81a65ea7aa55c185a"
MANIFEST_NAME = "graph6_curriculum_source_manifest.json"
CONTRASTS = ("edge_reversal", "query_role_swap", "unseen_anagram_query", "structural_reorder")
EXPECTED_KEYS = {(family, arm, contrast) for family in range(16)
                 for arm in ("cas", "generic") for contrast in CONTRASTS}
BOUNDARY = (
    "Saved encoding-mechanism evidence only, not learning correctness, trained accuracy, "
    "native reasoning, causal explanation of past scores, provider cleanup or complete CNCM. "
    "Standard-library double arithmetic recounts saved float values; it does not reproduce CUDA rounding. "
    "The worker field bitwise_equal is implemented by torch.equal: this recount verifies numeric "
    "coordinate equality, not original tensor-byte identity. Projection stability checks compare "
    "recorded source-bound digests; no projection checkpoint is available for independent rehashing."
)


class RecountError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise RecountError(message)


def digest(raw):
    return sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def read_json(path):
    raw = Path(path).read_bytes()

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_KEY:" + key)
            result[key] = value
        return result

    def invalid(value):
        raise RecountError("NONFINITE_JSON_CONSTANT:" + value)

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid), raw


def file_identity(path):
    raw = Path(path).read_bytes()
    return {"path": str(Path(path).resolve()), "bytes": len(raw), "sha256": digest(raw)}


def source_manifest(archive):
    raw = Path(archive).read_bytes()
    require(digest(raw) == ARCHIVE_SHA, "SOURCE_ARCHIVE_HASH")
    with ZipFile(archive) as bundle:
        names = bundle.namelist()
        require(len(names) == len(set(names)) == 61, "SOURCE_MEMBER_COUNT")
        body = bundle.read(MANIFEST_NAME)
        require(digest(body) == MANIFEST_SHA, "SOURCE_MANIFEST_HASH")
        manifest = json.loads(body)
        require(manifest["source_sha"] == SOURCE_SHA, "SOURCE_COMMIT")
        require(set(names) == set(manifest["members"]) | {MANIFEST_NAME}, "SOURCE_MEMBER_COVERAGE")
        for name in manifest["members"]:
            member = bundle.read(name)
            require(digest(member) == manifest["files_sha256"][name]
                    and len(member) == manifest["files_bytes"][name], "SOURCE_MEMBER_HASH:" + name)
    return manifest


def numeric_vector(value):
    require(type(value) is list and len(value) == 64, "VECTOR_DIMENSION")
    require(all(type(x) in (int, float) and math.isfinite(x) for x in value), "VECTOR_NONFINITE_OR_TYPE")
    return value


def norm(value):
    return math.sqrt(math.fsum(x * x for x in value))


def vector_metrics(base, variant):
    base, variant = numeric_vector(base), numeric_vector(variant)
    first, second = norm(base), norm(variant)
    delta = norm([a - b for a, b in zip(base, variant)])
    return {"base_l2": first, "variant_l2": second, "delta_l2": delta,
            "relative_l2": delta / max(first, second, 1.0),
            "coordinate_equal": all(a == b for a, b in zip(base, variant))}


def row_key(row):
    require(type(row) is dict and type(row.get("family")) is int, "PAIR_METADATA_TYPE")
    key = (row["family"], row.get("arm"), row.get("contrast"))
    require(key in EXPECTED_KEYS, "UNREGISTERED_PAIR:" + repr(key))
    require(type(row.get("answer_changed")) is bool
            and row["answer_changed"] is (row["contrast"] != "structural_reorder"), "ANSWER_CHANGE_METADATA")
    return key


def recount_rows(rows):
    require(type(rows) is list and len(rows) <= 128, "ROWS_INVALID")
    seen, baselines, recounted = set(), {}, []
    for row in rows:
        key = row_key(row)
        require(key not in seen, "DUPLICATE_PAIR:" + repr(key))
        seen.add(key)
        raw = row.get("raw_vectors")
        require(type(raw) is dict and set(raw) == {"base", "variant"}, "RAW_VECTOR_ROLES")
        output = {"family": key[0], "arm": key[1], "contrast": key[2], "answer_changed": row["answer_changed"]}
        for encoder in ("legacy", "ordered"):
            require(set(raw["base"]) == set(raw["variant"]) == {"legacy", "ordered"}, "RAW_ENCODER_KEYS")
            baseline_key = (key[0], key[1], encoder)
            baseline = numeric_vector(raw["base"][encoder])
            require(baseline_key not in baselines or baseline == baselines[baseline_key], "INCONSISTENT_REPEATED_BASE_VECTOR")
            baselines[baseline_key] = baseline
            measured = vector_metrics(baseline, raw["variant"][encoder])
            recorded = row.get(encoder + "_relative_l2")
            require(type(recorded) in (int, float) and math.isfinite(recorded) and recorded >= 0, "RECORDED_DISTANCE_INVALID")
            require(math.isclose(recorded, measured["relative_l2"], rel_tol=5e-6, abs_tol=1e-12), "RAW_DISTANCE_DISAGREEMENT:" + repr(key) + ":" + encoder)
            require(type(row.get(encoder + "_bitwise_equal")) is bool
                    and row[encoder + "_bitwise_equal"] is measured["coordinate_equal"], "RAW_EQUALITY_DISAGREEMENT")
            threshold = 1e-5 if encoder == "legacy" else 1e-3
            require((recorded <= threshold) == (measured["relative_l2"] <= threshold), "THRESHOLD_ROUNDING_AMBIGUITY")
            output[encoder] = measured
        recounted.append(output)
    changed = [row for row in recounted if row["answer_changed"]]
    controls = [row for row in recounted if not row["answer_changed"]]
    counts = {"assigned_pairs": len(rows), "changed_answer_pairs": len(changed),
              "reorder_controls": len(controls), "legacy_collision_tolerance": 1e-5,
              "ordered_separation_threshold": 1e-3,
              "legacy_near_collisions": sum(row["legacy"]["relative_l2"] <= 1e-5 for row in changed),
              "ordered_separated": sum(row["ordered"]["relative_l2"] > 1e-3 for row in changed),
              "ordered_reorder_exact": sum(row["ordered"]["coordinate_equal"] for row in controls)}
    return {"rows": recounted, "counts": counts, "complete_coverage": seen == EXPECTED_KEYS,
            "missing_pairs": [list(key) for key in sorted(EXPECTED_KEYS - seen)],
            "legacy_changed_coordinate_equal": sum(row["legacy"]["coordinate_equal"] for row in changed),
            "per_contrast": {contrast: {"pairs": sum(row["contrast"] == contrast for row in recounted),
                "legacy_coordinate_equal": sum(row["contrast"] == contrast and row["legacy"]["coordinate_equal"] for row in recounted),
                "ordered_coordinate_equal": sum(row["contrast"] == contrast and row["ordered"]["coordinate_equal"] for row in recounted)} for contrast in CONTRASTS}}


def analyze(result_path, artifacts_dir, archive, expected_job):
    manifest = source_manifest(archive)
    envelope, raw = read_json(result_path)
    result_path, artifacts_dir = Path(result_path), Path(artifacts_dir)
    sidecar = Path(str(result_path) + ".sha256")
    require(sidecar.read_text(encoding="ascii").strip() == digest(raw), "RESULT_SIDECAR_HASH")
    require(envelope.get("schema") == "cas-ordered-encoder-result/1" and envelope.get("job") == expected_job, "RESULT_IDENTITY")
    require(envelope.get("status") in ("ORDERED_ENCODER_DIAGNOSTIC_DELIVERED", "ORDERED_ENCODER_DIAGNOSTIC_FAILED"), "RESULT_STATUS")
    artifact_manifest, _ = read_json(artifacts_dir / "manifest.json")
    entries = artifact_manifest.get("artifacts")
    require(type(entries) is list and entries == envelope.get("artifacts"), "ARTIFACT_MANIFEST_BINDING")
    require({item.get("name") for item in entries} == {"encoder_probe.json", "measurements.json"}
            and len(entries) == 2, "ARTIFACT_INVENTORY")
    files = {"result": file_identity(result_path), "result_sidecar": file_identity(sidecar),
             "manifest": file_identity(artifacts_dir / "manifest.json"), "source_archive": file_identity(archive)}
    for entry in entries:
        require(PurePosixPath(entry["name"]).name == entry["name"] and "\\" not in entry["name"], "ARTIFACT_PATH")
        identity = file_identity(artifacts_dir / entry["name"])
        require(type(entry.get("bytes")) is int and identity["bytes"] == entry["bytes"]
                and identity["sha256"] == entry.get("sha256"), "ARTIFACT_BYTES:" + entry["name"])
        files[entry["name"]] = identity
    report, _ = read_json(artifacts_dir / "encoder_probe.json")
    measurement, _ = read_json(artifacts_dir / "measurements.json")
    require(report.get("schema") == measurement.get("schema") == "cas-ordered-encoder-probe/1", "REPORT_SCHEMA")
    require(report.get("source_sha") == measurement.get("source_sha") == SOURCE_SHA, "REPORT_SOURCE")
    require(report.get("job") == measurement.get("job") == expected_job, "REPORT_JOB")
    require(canonical(report.get("inputs")) == canonical(manifest["inputs"]), "REPORT_SOURCE_INPUTS")
    for document in (envelope, report, measurement):
        require(type(document.get("optimizer_updates")) is int and document["optimizer_updates"] == 0, "NONZERO_UPDATES")
    require(report.get("learner_forward_calls") == measurement.get("learner_forward_calls") == 0, "LEARNER_FORWARDS")
    require(envelope.get("summary") == measurement, "SUMMARY_ARTIFACT_DISAGREEMENT")
    for key in ("job", "source_sha", "checks", "elapsed_seconds", "projection_unchanged", "projection_sha256_before", "projection_sha256_after", "failure"):
        require(measurement.get(key) == report.get(key), "MEASUREMENT_DISAGREEMENT:" + key)
    require(envelope.get("failure") == report.get("failure"), "FAILURE_DISAGREEMENT")
    require(type(report.get("elapsed_seconds")) in (int, float) and math.isfinite(report["elapsed_seconds"])
            and report["elapsed_seconds"] >= 0, "ELAPSED_TIME")
    recounted = recount_rows(report.get("rows"))
    checks = report.get("checks")
    if checks is not None:
        require(canonical(checks) == canonical(recounted["counts"]), "DECLARED_CHECKS_DISAGREE_WITH_RAW_RECOUNT")
    algebraic = report.get("algebraic_audit")
    if algebraic is not None:
        require(algebraic.get("status") == "ALGEBRAIC_COLLISIONS_CONFIRMED" and algebraic.get("neural_calls") == 0, "ALGEBRAIC_STATUS")
        require(canonical(algebraic.get("source_inputs")) == canonical(manifest["inputs"]), "ALGEBRAIC_SOURCE_BINDINGS")
        pairs = algebraic.get("pairs")
        require(type(pairs) is list and len(pairs) == 128 and {row_key(row) for row in pairs} == EXPECTED_KEYS, "ALGEBRAIC_PAIR_COVERAGE")
        for row in pairs:
            require(row.get("algebraically_identical") is True and row.get("base_answer") == "direct"
                    and row.get("variant_answer") == ("absent" if row["answer_changed"] else "direct"), "ALGEBRAIC_TARGET_METADATA")
        require(algebraic.get("changed_answer_collisions") == 96 and algebraic.get("reorder_controls") == 32, "ALGEBRAIC_COUNTS")
    before, after = report.get("projection_sha256_before"), report.get("projection_sha256_after")
    projection_match = (type(before) is str and re.fullmatch(r"[a-f0-9]{64}", before) is not None and before == after)
    if before is not None and after is not None:
        require(type(report.get("projection_unchanged")) is bool and report["projection_unchanged"] is projection_match, "PROJECTION_DIGEST_DISAGREEMENT")
    counts = recounted["counts"]
    gates = {"complete_coverage": recounted["complete_coverage"], "projection_digest_match": projection_match,
             "legacy_near_collisions_96": counts["legacy_near_collisions"] == 96,
             "ordered_separated_96": counts["ordered_separated"] == 96,
             "ordered_reorder_equal_32": counts["ordered_reorder_exact"] == 32,
             "algebraic_audit_present": algebraic is not None, "final_checks_present": checks is not None}
    delivered = envelope["status"] == "ORDERED_ENCODER_DIAGNOSTIC_DELIVERED"
    require(not delivered or (all(gates.values()) and report.get("failure") is None), "SUCCESS_ENVELOPE_WITH_FAILED_OR_MISSING_GATES")
    return {"schema": "cas-ordered-encoder-independent-recount/1",
            "status": "VERIFIED_ENCODING_DIAGNOSTIC" if delivered else (
                "VERIFIED_FAILED_DIAGNOSTIC" if recounted["complete_coverage"] else "VERIFIED_INCOMPLETE_DIAGNOSTIC"),
            "source_sha": SOURCE_SHA, "job": expected_job, "files": files,
            "source_status": envelope["status"], "source_failure": report.get("failure"),
            "gates": gates, "projection_sha256_before": before, "projection_sha256_after": after,
            "recount": recounted, "worker_elapsed_seconds": report["elapsed_seconds"],
            "optimizer_updates": 0, "learner_forward_calls": 0,
            "boundary": BOUNDARY}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--source-archive", required=True, type=Path)
    parser.add_argument("--job", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    require(not args.output.exists(), "OUTPUT_MUST_BE_NEW")
    args.output.mkdir(parents=True)
    try:
        report = analyze(args.result, args.artifacts, args.source_archive, args.job)
        code = 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        report = {"schema": "cas-ordered-encoder-independent-recount/1", "status": "EVIDENCE_RECOUNT_REFUSED",
                  "source_sha": SOURCE_SHA, "job": args.job,
                  "error": {"type": type(error).__name__, "message": str(error)}, "boundary": BOUNDARY}
        code = 1
    report["recount_tool"] = file_identity(__file__)
    report["command"] = vars(args) | {key: str(value) for key, value in vars(args).items() if isinstance(value, Path)}
    body = (json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    (args.output / "recount.json").write_bytes(body)
    (args.output / "recount.json.sha256").write_text(digest(body) + "\n", encoding="ascii")
    print(json.dumps({"status": report["status"], "sha256": digest(body), "output": str(args.output)}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
