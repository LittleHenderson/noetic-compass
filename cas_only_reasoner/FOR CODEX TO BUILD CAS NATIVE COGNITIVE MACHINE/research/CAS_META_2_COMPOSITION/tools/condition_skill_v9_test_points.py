"""Automatic test-point (TP) layer for the condition-skill v9 work.

This layer observes and reports; it never intervenes, and it never modifies a
frozen experiment, trainer, dataset, adjudicator, or execution timing. It is
pure: standard-library imports only, no neural, provider, SQLite, or network
work, and it never reads a dataset partition. It consumes only already-sealed
evidence: the frozen publication packet (for frozen source hashes), the dataset
manifest's raw bytes (hashed, never parsed), and a v9 trainer result.json's
pre-computed metric summaries.

Three outputs:

A. identity_report(source_root=None, expected_hashes=None) -> dict
   Hashes the frozen source set (tools.check_condition_skill_v9.FILES) and the
   dataset manifest. Each check is OK / MISMATCH / MISSING / NOT_REACHED.
   Missing evidence is incompleteness (IDENTITY_INCOMPLETE), never a failure.
   expected_hashes is a test/frozen-override injection point: a mapping of
   research-relative path -> sha256. When omitted, the layer reads FILES
   expectations from the frozen publication packet and fixes the dataset
   manifest expectation to the frozen constant.

B. transition_report(analysis_json_path) -> dict
   One per-transition failure record in the exact saved-repair shape. L2 is the
   expectation for *that fixture* (C, tick 7), not a universal answer; the
   required_output_for_this_fixture field is read from the fixture, never
   hardcoded. Fields the evidence does not cover are "not reached"/None, never
   "failed".

C. development_scorecard(result_json_path=None) -> dict
   Initial-versus-trained joint accuracy, per-bit accuracy, first-wrong-bit
   counts, and equality/unit-margin slices, per family and split, from a v9
   trainer result.json (schema cas-meta2-condition-skill-training/9). With no
   run yet the status is NO_RUN, not a failure.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

# The frozen source set is owned by the guarded checker. Import it read-only so
# this layer can never drift from the set the checker freezes. The import is
# pure: tools/check_condition_skill_v9 imports only standard-library modules at
# import time and performs no file, network, or provider work at import time.
from tools.check_condition_skill_v9 import FILES

ROOT = Path(__file__).resolve().parents[1]

SCHEMA_IDENTITY = "cas-meta2-condition-skill-test-point-identity/9"
SCHEMA_TRANSITION = "cas-meta2-condition-skill-test-point-transition/9"
SCHEMA_SCORECARD = "cas-meta2-condition-skill-test-point-scorecard/9"

TRAINING_SCHEMA = "cas-meta2-condition-skill-training/9"

DATASET_MANIFEST_RELPATH = "records/condition_skill_v9_001/dataset_001/manifest.json"
DATASET_MANIFEST_SHA256 = "6b19020c4653aa535919f4af092020ad3650855bf7f58c6b550169af3d5468dd"
PUBLICATION_PACKET_RELPATH = "records/condition_skill_v9_001/publication_packet.json"

# Frozen expected hashes for the three committed files the publication packet
# does not rebind (they predate the packet's range base and are pinned by the
# branch history itself). Keeping them here lets identity_report cover the
# complete frozen source set instead of reporting honest but avoidable
# incompleteness.
FROZEN_EXPECTED_OVERRIDES = {
    "cas_meta2/condition_skill_v9/__init__.py":
        "74d8d2304a98638cad4cce67089cf83327639fff4afd086738d5d39cb175a5ce",
    "aws/budget.py":
        "77a845ea8669b775a28a940552a9212f667a9506e5586deff64baba06a82eda0",
    "tests/test_budget.py":
        "56bf8cd7e88c3194396bd1b7b0f3b82620bbae0aeded188dfa8dfbb541681b49",
}

FAMILIES = ("cas", "generic_attention")
STAGES = ("untrained", "trained")
TEST_SPLITS = ("test_instances", "test_direction_pair")

NOT_REACHED = "NOT_REACHED"
NOT_REACHED_TEXT = "not reached"

__all__ = ["identity_report", "transition_report", "development_scorecard",
           "FILES", "FAMILIES", "STAGES", "TEST_SPLITS",
           "DATASET_MANIFEST_RELPATH", "DATASET_MANIFEST_SHA256", "NOT_REACHED"]


def _utcnow():
    return datetime.now(timezone.utc).isoformat()


def _sha256(path):
    """Return the hex sha256 of a file's bytes, or None if it cannot be read."""
    try:
        return sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def _read_packet_expected(root):
    """Map research-relative paths to frozen sha256 from the publication packet."""
    packet = root / PUBLICATION_PACKET_RELPATH
    expected = {}
    if not packet.is_file():
        return expected
    try:
        data = json.loads(packet.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return expected
    if not isinstance(data, dict) or not isinstance(data.get("files"), list):
        return expected
    marker = "research/CAS_META_2_COMPOSITION/"
    for item in data["files"]:
        if not isinstance(item, dict):
            continue
        path, digest = item.get("path"), item.get("sha256")
        if isinstance(path, str) and isinstance(digest, str) and marker in path:
            expected[path.split(marker, 1)[1]] = digest
    return expected


def _default_expected(root):
    expected = _read_packet_expected(root)
    # The dataset manifest expectation is the frozen constant, never whatever a
    # (possibly drifted) packet happens to record.
    expected[DATASET_MANIFEST_RELPATH] = DATASET_MANIFEST_SHA256
    expected.update(FROZEN_EXPECTED_OVERRIDES)
    return expected


def _check_file(root, relpath, expected_sha):
    path = root / relpath
    if not path.is_file():
        return {"status": "MISSING", "expected_sha256": expected_sha,
                "actual_sha256": None}
    actual = _sha256(path)
    if expected_sha is None:
        return {"status": "NOT_REACHED", "expected_sha256": None,
                "actual_sha256": actual}
    if actual == expected_sha:
        return {"status": "OK", "expected_sha256": expected_sha,
                "actual_sha256": actual}
    return {"status": "MISMATCH", "expected_sha256": expected_sha,
            "actual_sha256": actual}


def identity_report(source_root=None, expected_hashes=None):
    """Hash the frozen source set and dataset manifest; report identity status.

    For every file in the frozen source set the check is OK / MISMATCH /
    MISSING / NOT_REACHED, with its expected and actual sha256. The dataset
    manifest is checked the same way against the frozen constant. Top-level
    status is IDENTITY_OK only when everything is OK, IDENTITY_MISMATCH when any
    check mismatches, and IDENTITY_INCOMPLETE when anything is missing or
    unreachable (incompleteness is NOT a failure). Missing checks are reported
    as NOT_REACHED, never as FAILED.
    """
    root = Path(source_root).resolve() if source_root is not None else ROOT
    if expected_hashes is None:
        expected = _default_expected(root)
    else:
        expected = dict(expected_hashes)
        expected.setdefault(DATASET_MANIFEST_RELPATH, DATASET_MANIFEST_SHA256)
    files = {name: _check_file(root, name, expected.get(name)) for name in FILES}
    manifest = _check_file(root, DATASET_MANIFEST_RELPATH,
                           expected.get(DATASET_MANIFEST_RELPATH))
    statuses = [entry["status"] for entry in files.values()] + [manifest["status"]]
    if "MISMATCH" in statuses:
        status = "IDENTITY_MISMATCH"
    elif any(state in ("MISSING", "NOT_REACHED") for state in statuses):
        status = "IDENTITY_INCOMPLETE"
    else:
        status = "IDENTITY_OK"
    return {"schema": SCHEMA_IDENTITY, "status": status, "source_root": str(root),
            "frozen_manifest_sha256": DATASET_MANIFEST_SHA256,
            "files": files, "dataset_manifest": manifest, "generated_utc": _utcnow()}


def _stage_decoded(stage):
    if not isinstance(stage, dict):
        return {}
    obs = stage.get("proposal_observation")
    if not isinstance(obs, dict):
        return {}
    content = obs.get("reported_decoded_content")
    return content if isinstance(content, dict) else {}


def _as_int(value, default=-1):
    return value if type(value) is int else default


def transition_report(analysis_json_path):
    """One per-transition failure record in the exact saved-repair shape.

    Reads the first stage of core_analysis.stages (the transition of record).
    L2 is the expectation for *that fixture* (C, tick 7), not a universal
    answer: required_output_for_this_fixture comes from the fixture's
    expected_symbol. Fields the evidence does not cover are "not reached"/None,
    never "failed".
    """
    path = Path(analysis_json_path)
    if not path.is_file():
        raise FileNotFoundError("transition_report: analysis not found: " + str(path))
    try:
        analysis = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("transition_report: analysis JSON unreadable: " + str(path)) from exc
    if not isinstance(analysis, dict):
        raise ValueError("transition_report: analysis must be a JSON object")
    core = analysis.get("core_analysis")
    if not isinstance(core, dict):
        raise ValueError("transition_report: missing core_analysis object")
    stages = core.get("stages")
    if not isinstance(stages, list) or not stages:
        raise ValueError("transition_report: missing core_analysis.stages")
    stage = stages[0] if isinstance(stages[0], dict) else {}
    decoded = _stage_decoded(stage)

    operation = decoded.get("operation_id")
    if operation is None:
        operation = stage.get("cjt_id")
    operation = str(operation) if operation is not None else NOT_REACHED_TEXT

    tick = _as_int(stage.get("tick"))

    symbol = decoded.get("symbol")
    actual = str(symbol) if symbol is not None else NOT_REACHED_TEXT
    expected_symbol = stage.get("expected_symbol")
    required = str(expected_symbol) if expected_symbol is not None else NOT_REACHED_TEXT

    if stage.get("accepted") is True:
        verifier_outcome = "ACCEPTED"
        accepted_result = str(symbol) if symbol is not None else NOT_REACHED_TEXT
    elif stage.get("attempted") is True:
        verifier_outcome = "REFUSED"
        accepted_result = None
    else:
        verifier_outcome = NOT_REACHED_TEXT
        accepted_result = None

    attempt_occurred = stage.get("attempted") is True

    later = [s for s in stages if isinstance(s, dict) and _as_int(s.get("tick")) > tick]
    next_tick_reached = any(s.get("attempted") is True or s.get("returned") is True
                            or s.get("committed") is True for s in later)

    rpm_after = core.get("R_rpm_after")
    open_ids = rpm_after.get("open_repair_ids") if isinstance(rpm_after, dict) else None
    repair_open = bool(open_ids) if isinstance(open_ids, list) else False

    outer = analysis.get("outer_caller_restored")
    outer_caller_restored = outer if type(outer) is bool else None

    first_observed_failed_check = None
    checks = core.get("checks")
    if isinstance(checks, list):
        for item in checks:
            if isinstance(item, dict) and item.get("ok") is False:
                first_observed_failed_check = item.get("check")
                break
    if first_observed_failed_check is None:
        failures = core.get("core_failures")
        if isinstance(failures, list):
            for item in failures:
                if isinstance(item, dict):
                    first_observed_failed_check = item.get("type")
                    break

    return {"operation": operation, "tick": tick,
            "actual_candidate_output": actual,
            "required_output_for_this_fixture": required,
            "verifier_outcome": verifier_outcome,
            "attempt_occurred": attempt_occurred,
            "accepted_result": accepted_result,
            "next_tick_reached": next_tick_reached,
            "repair_open": repair_open,
            "outer_caller_restored": outer_caller_restored,
            "first_observed_failed_check": first_observed_failed_check}


def _summary(metrics, family, stage, split):
    if not isinstance(metrics, dict):
        return None
    stage_metrics = metrics.get(family + "." + stage)
    if not isinstance(stage_metrics, dict):
        return None
    summary = stage_metrics.get(split)
    return summary if isinstance(summary, dict) else None


def _get(summary, key):
    if isinstance(summary, dict) and key in summary:
        return summary[key]
    return NOT_REACHED


def _first_wrong_counts(summary):
    if not isinstance(summary, dict) or "first_wrong_bit" not in summary:
        return NOT_REACHED
    first_wrong = summary["first_wrong_bit"]
    if not isinstance(first_wrong, dict):
        return NOT_REACHED
    return {"bit_1_count": first_wrong.get("bit_1_count"),
            "bit_2_count": first_wrong.get("bit_2_count"),
            "none_count": first_wrong.get("none_count")}


def _slice_accuracy(summary, key):
    if not isinstance(summary, dict) or key not in summary:
        return NOT_REACHED
    slice_dict = summary[key]
    if not isinstance(slice_dict, dict):
        return NOT_REACHED
    return slice_dict.get("accuracy")


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def development_scorecard(result_json_path=None):
    """Scorecard from a v9 trainer result.json; NO_RUN is not a failure.

    With no path (or no scoreable metrics) the status is NO_RUN. A malformed or
    wrong-schema result.json yields a clear MALFORMED status, never a crash into
    a fake pass. For each family / stage / split it reports joint accuracy,
    per-bit accuracy [bit0, bit1], first-wrong-bit counts, no_effect_count, and
    equality/unit-margin slice accuracy; any absent metric is NOT_REACHED.
    Improvement flags compare trained vs untrained joint accuracy per
    family/split, and the overall summary lists which improved. This never opens
    private targets and never reads any dataset partition.
    """
    base = {"schema": SCHEMA_SCORECARD, "families": list(FAMILIES),
            "stages": list(STAGES), "splits": list(TEST_SPLITS),
            "generated_utc": _utcnow()}
    if result_json_path is None:
        return {**base, "status": "NO_RUN",
                "reason": "no result.json path provided (no run evidence)"}
    path = Path(result_json_path)
    if not path.is_file():
        return {**base, "status": "NO_RUN",
                "reason": "result.json not found: " + str(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {**base, "status": "MALFORMED",
                "reason": "result.json unreadable: " + str(exc)}
    if not isinstance(data, dict) or data.get("schema") != TRAINING_SCHEMA:
        return {**base, "status": "MALFORMED",
                "reason": "result.json is not schema " + TRAINING_SCHEMA}
    metrics = data.get("metrics")
    if not isinstance(metrics, dict) or not metrics:
        return {**base, "status": "NO_RUN",
                "reason": "no completed metrics in result.json (run did not produce scoreable evidence)"}

    rows = []
    for family in FAMILIES:
        for stage in STAGES:
            for split in TEST_SPLITS:
                summary = _summary(metrics, family, stage, split)
                rows.append({
                    "family": family, "stage": stage, "split": split,
                    "joint_accuracy": _get(summary, "accuracy"),
                    "bit_accuracy": _get(summary, "bit_accuracy"),
                    "first_wrong_bit_counts": _first_wrong_counts(summary),
                    "no_effect_count": _get(summary, "no_effect_count"),
                    "equality_slice_accuracy": _slice_accuracy(summary, "equality_slice"),
                    "unit_margin_slice_accuracy": _slice_accuracy(summary, "unit_margin_slice"),
                })

    improvement = {}
    overall = {"improved": [], "not_improved": [], "not_reached": []}
    for family in FAMILIES:
        improvement[family] = {}
        for split in TEST_SPLITS:
            untrained = _summary(metrics, family, "untrained", split)
            trained = _summary(metrics, family, "trained", split)
            untrained_acc = _get(untrained, "accuracy")
            trained_acc = _get(trained, "accuracy")
            if untrained_acc == NOT_REACHED or trained_acc == NOT_REACHED or \
                    not _is_number(untrained_acc) or not _is_number(trained_acc):
                improved = NOT_REACHED
            else:
                improved = trained_acc > untrained_acc
            improvement[family][split] = {"untrained_joint_accuracy": untrained_acc,
                                          "trained_joint_accuracy": trained_acc,
                                          "improved": improved}
            key = family + "." + split
            if improved is True:
                overall["improved"].append(key)
            elif improved is False:
                overall["not_improved"].append(key)
            else:
                overall["not_reached"].append(key)

    return {**base, "status": "COMPUTED", "rows": rows,
            "improvement": improvement, "overall": overall}
