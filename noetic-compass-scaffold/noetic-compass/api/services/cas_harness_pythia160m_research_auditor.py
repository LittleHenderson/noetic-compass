"""Independent standard-library auditor for Pythia-160M research V2.

This module deliberately does not import the executor or any model framework.
It verifies the successor lock, raw artifact hashes, exact request matrix,
bindings, controls, stop rules, and claim boundary from retained files.
"""

from __future__ import annotations

from array import array
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any, Callable, Mapping, Sequence


LOCK_SCHEMA = "cas_harness_pythia160m_research_lock.v2"
RESULT_SCHEMA = "cas_harness_pythia160m_research_result.v2"
AUDIT_SCHEMA = "cas_harness_pythia160m_research_audit.v2"
FORBIDDEN_FRAMEWORK_MODULES = frozenset(
    {"torch", "transformers", "tokenizers", "safetensors"}
)
EXPECTED_CONDITIONS = {
    ("baseline", 0.0),
    ("no_op", 0.0),
    ("target_direction", -0.5),
    ("target_direction", -0.25),
    ("target_direction", 0.25),
    ("target_direction", 0.5),
    ("same_norm_random_direction", 0.5),
    ("wrong_layer", 0.5),
    ("wrong_token", 0.5),
    ("wrong_sign", 0.5),
    ("wrong_axis", 0.5),
    ("patch_back", 0.5),
}


class PythiaResearchAuditError(RuntimeError):
    """Audit could not trust or reconstruct the packet."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PythiaResearchAuditError(f"Cannot read audit JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PythiaResearchAuditError(f"Audit JSON must be an object: {path}")
    return value


def _read_f32(path: Path, expected_bytes: int, expected_sha256: str) -> list[float]:
    if not path.is_file():
        raise PythiaResearchAuditError(f"Missing raw logits artifact: {path}")
    if path.stat().st_size != expected_bytes:
        raise PythiaResearchAuditError(f"Raw logits byte-count drift: {path}")
    if sha256_file(path) != expected_sha256:
        raise PythiaResearchAuditError(f"Raw logits hash drift: {path}")
    values = array("f")
    with path.open("rb") as handle:
        values.fromfile(handle, expected_bytes // values.itemsize)
    return [float(value) for value in values]


def _softmax(logits: Sequence[float]) -> list[float]:
    if not logits or not all(math.isfinite(value) for value in logits):
        raise PythiaResearchAuditError("Non-finite or empty logits")
    maximum = max(logits)
    exponentials = [math.exp(value - maximum) for value in logits]
    total = sum(exponentials)
    return [value / total for value in exponentials]


def _jsd(left_logits: Sequence[float], right_logits: Sequence[float]) -> float:
    left = _softmax(left_logits)
    right = _softmax(right_logits)
    midpoint = [(a + b) / 2.0 for a, b in zip(left, right, strict=True)]

    def kl(values: Sequence[float], reference: Sequence[float]) -> float:
        return sum(
            value * math.log(value / target)
            for value, target in zip(values, reference, strict=True)
            if value > 0.0
        )

    return 0.5 * kl(left, midpoint) + 0.5 * kl(right, midpoint)


def _max_abs_delta(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise PythiaResearchAuditError("Logit vector length drift")
    return max((abs(a - b) for a, b in zip(left, right, strict=True)), default=0.0)


def _top1(values: Sequence[float]) -> int:
    return max(range(len(values)), key=lambda index: values[index])


def _median(values: Sequence[float]) -> float:
    if not values:
        raise PythiaResearchAuditError("Cannot compute median of empty evidence")
    return float(statistics.median(values))


def _spearman_for_frozen_doses(effects: Mapping[float, float]) -> float:
    doses = [-0.5, -0.25, 0.0, 0.25, 0.5]
    values = [effects[dose] for dose in doses]
    if len(set(values)) != len(values):
        return 0.0
    ranks = {value: rank for rank, value in enumerate(sorted(values), start=1)}
    value_ranks = [ranks[value] for value in values]
    mean_rank = 3.0
    numerator = sum(
        (index - mean_rank) * (rank - mean_rank)
        for index, rank in zip(range(1, 6), value_ranks, strict=True)
    )
    denominator = math.sqrt(
        sum((index - mean_rank) ** 2 for index in range(1, 6))
        * sum((rank - mean_rank) ** 2 for rank in value_ranks)
    )
    return numerator / denominator


def validate_lock_independently(repo_root: Path, lock_path: Path) -> dict[str, Any]:
    before = FORBIDDEN_FRAMEWORK_MODULES & set(sys.modules)
    if before:
        raise PythiaResearchAuditError(f"Framework imported before audit: {sorted(before)}")
    lock = load_json(lock_path)
    if lock.get("schema_version") != LOCK_SCHEMA:
        raise PythiaResearchAuditError("Unsupported successor lock schema")
    if (
        lock.get("status")
        != "PROSPECTIVE_SUCCESSOR_LOCK / EXECUTOR_AUDITOR_LOCAL_STATIC_PASS / RUN_NOT_AUTHORIZED"
    ):
        raise PythiaResearchAuditError("Successor lock status drift")
    frozen = lock.get("frozen_files", {})
    required = {
        "prior_v1_lock",
        "model_manifest",
        "prompt_split",
        "intervention_map_v2",
        "environment_manifest",
        "compute_manifest",
        "executor",
        "auditor",
    }
    if set(frozen) != required:
        raise PythiaResearchAuditError("Frozen-file inventory drift")
    for record in frozen.values():
        path = repo_root / record["path"]
        if not path.is_file() or sha256_file(path) != record["sha256"]:
            raise PythiaResearchAuditError(f"Frozen binding drift: {path}")
        if "byte_count" in record and path.stat().st_size != int(record["byte_count"]):
            raise PythiaResearchAuditError(f"Frozen byte-count drift: {path}")
    if lock.get("execution_gates", {}).get("receipt_status") != "ABSENT / CREATION_NOT_AUTHORIZED":
        raise PythiaResearchAuditError("Preparation lock implies receipt authority")
    if lock.get("execution_gates", {}).get("output_status") != "ABSENT":
        raise PythiaResearchAuditError("Preparation lock implies output exists")
    after = FORBIDDEN_FRAMEWORK_MODULES & set(sys.modules)
    if after:
        raise PythiaResearchAuditError(f"Auditor imported framework: {sorted(after)}")
    return lock


def _prompt_contract(prompt_split: Mapping[str, Any]) -> tuple[list[str], dict[str, str]]:
    heldout: list[str] = []
    labels: dict[str, str] = {}
    for label in ("^0|C", "^0|E"):
        for prompt_id in prompt_split["heldout"][label]:
            heldout.append(prompt_id)
            labels[prompt_id] = label
    for row in prompt_split["collateral_heldout"]:
        heldout.append(row["prompt_id"])
        labels[row["prompt_id"]] = f"collateral:{row['category']}"
    return heldout, labels


def _inline_logits(record: Mapping[str, Any]) -> list[float]:
    values = record.get("logits_inline")
    if not isinstance(values, list):
        raise PythiaResearchAuditError("Static audit fixture lacks inline logits")
    return [float(value) for value in values]


def audit_result_mapping(
    *,
    lock: Mapping[str, Any],
    prompt_split: Mapping[str, Any],
    result: Mapping[str, Any],
    logits_reader: Callable[[Mapping[str, Any]], list[float]] = _inline_logits,
    expected_lock_sha256: str | None = None,
) -> dict[str, Any]:
    """Independently recompute the exact control and harm gates."""

    findings: list[str] = []

    def require(condition: bool, code: str) -> None:
        if not condition:
            findings.append(code)

    require(result.get("schema_version") == RESULT_SCHEMA, "RESULT_SCHEMA_DRIFT")
    require(result.get("status") == "TERMINAL_UNAUDITED_RESEARCH_ONLY", "RESULT_STATUS_DRIFT")
    payload = dict(result)
    recorded_hash = payload.pop("result_payload_sha256", None)
    require(recorded_hash == canonical_sha256(payload), "RESULT_PAYLOAD_HASH_DRIFT")
    if expected_lock_sha256 is not None:
        require(
            result.get("lock_sha256") == expected_lock_sha256,
            "LOCK_BINDING_DRIFT",
        )
    require(
        result.get("claim_status") == "OPEN / NOT_LICENSED / NO ACCEPT / NO PRODUCTION EFFECT",
        "CLAIM_BOUNDARY_DRIFT",
    )
    require(result.get("network_attempts") == 0, "NETWORK_ATTEMPT_RECORDED")

    records = result.get("records")
    if not isinstance(records, list):
        records = []
        findings.append("RECORDS_MISSING")
    require(int(result.get("request_count", -1)) == len(records), "REQUEST_COUNT_DRIFT")
    require(len(records) == 472, "FROZEN_REQUEST_COUNT_DRIFT")
    require(len(records) <= int(lock["compute_cap"]["max_forward_passes"]), "COMPUTE_CAP_EXCEEDED")

    heldout_ids, labels = _prompt_contract(prompt_split)
    calibration_ids: list[str] = []
    calibration_labels: dict[str, str] = {}
    for label in ("^0|C", "^0|E"):
        for prompt_id in prompt_split["calibration"][label]:
            calibration_ids.append(prompt_id)
            calibration_labels[prompt_id] = label
    seeds = lock["experiment"]["seeds"]
    expected_seed = {
        prompt_id: seeds[index % len(seeds)]
        for index, prompt_id in enumerate(heldout_ids)
    }
    heldout_records = [record for record in records if record.get("split") == "heldout"]
    calibration_records = [record for record in records if record.get("split") == "calibration"]
    require(len(calibration_records) == 16, "CALIBRATION_COUNT_DRIFT")
    require(len(heldout_records) == 456, "HELDOUT_COUNT_DRIFT")

    by_prompt: dict[str, list[Mapping[str, Any]]] = {}
    logits: dict[int, list[float]] = {}
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            findings.append(f"INVALID_RECORD:{index}")
            continue
        prompt_id = str(record.get("prompt_id"))
        by_prompt.setdefault(prompt_id, []).append(record)
        try:
            values = logits_reader(record)
        except Exception:
            findings.append(f"LOGITS_UNREADABLE:{index}")
            continue
        logits[id(record)] = values
        require(all(math.isfinite(value) for value in values), f"NONFINITE_LOGITS:{index}")
        require(record.get("finite_logits") is True, f"FINITE_FLAG_DRIFT:{index}")
    require(
        set(by_prompt) == set(calibration_ids) | set(heldout_ids),
        "PROMPT_MEMBERSHIP_DRIFT",
    )
    expected_calibration_seed = {
        prompt_id: seeds[index % len(seeds)]
        for index, prompt_id in enumerate(calibration_ids)
    }
    for prompt_id in calibration_ids:
        rows = by_prompt.get(prompt_id, [])
        require(len(rows) == 1, f"CALIBRATION_DUPLICATE_OR_MISSING:{prompt_id}")
        if rows:
            row = rows[0]
            require(
                row.get("condition") == "baseline"
                and float(row.get("dose", math.nan)) == 0.0,
                f"CALIBRATION_CONDITION_DRIFT:{prompt_id}",
            )
            require(
                row.get("seed") == expected_calibration_seed[prompt_id],
                f"CALIBRATION_SEED_DRIFT:{prompt_id}",
            )
            require(
                row.get("label") == calibration_labels[prompt_id],
                f"CALIBRATION_LABEL_DRIFT:{prompt_id}",
            )

    no_op_deltas: list[float] = []
    patch_back_deltas: list[float] = []
    target_effects: dict[float, list[float]] = {
        -0.5: [],
        -0.25: [],
        0.0: [],
        0.25: [],
        0.5: [],
    }
    control_effects: dict[str, list[float]] = {
        "same_norm_random_direction": [],
        "wrong_layer": [],
        "wrong_token": [],
        "wrong_axis": [],
    }
    wrong_sign_effects: list[float] = []
    utility_preservation: list[bool] = []
    fluency_jsd: list[float] = []
    safety_preservation: list[bool] = []

    for prompt_id in heldout_ids:
        rows = by_prompt.get(prompt_id, [])
        require(len(rows) == 12, f"HELDOUT_DUPLICATE_OR_MISSING:{prompt_id}")
        actual_conditions = {
            (str(row.get("condition")), float(row.get("dose", math.nan)))
            for row in rows
        }
        require(actual_conditions == EXPECTED_CONDITIONS, f"CONDITION_MATRIX_DRIFT:{prompt_id}")
        require(
            all(row.get("seed") == expected_seed[prompt_id] for row in rows),
            f"SEED_DRIFT:{prompt_id}",
        )
        require(
            all(row.get("label") == labels[prompt_id] for row in rows),
            f"LABEL_DRIFT:{prompt_id}",
        )
        row_by_condition = {
            (str(row["condition"]), float(row["dose"])): row for row in rows
        }
        baseline = row_by_condition.get(("baseline", 0.0), {})
        baseline_logits = logits.get(id(baseline), [])
        baseline_projection = float(baseline.get("target_projection", math.nan))
        target_effects[0.0].append(0.0)
        no_op = row_by_condition.get(("no_op", 0.0), {})
        if baseline_logits and logits.get(id(no_op)):
            no_op_deltas.append(_max_abs_delta(baseline_logits, logits[id(no_op)]))
        patch_back = row_by_condition.get(("patch_back", 0.5), {})
        if baseline_logits and logits.get(id(patch_back)):
            patch_back_deltas.append(
                _max_abs_delta(baseline_logits, logits[id(patch_back)])
            )
        for dose in (-0.5, -0.25, 0.25, 0.5):
            row = row_by_condition.get(("target_direction", dose), {})
            target_effects[dose].append(
                float(row.get("target_projection", math.nan)) - baseline_projection
            )
        for condition in control_effects:
            row = row_by_condition.get((condition, 0.5), {})
            control_effects[condition].append(
                float(row.get("target_projection", math.nan)) - baseline_projection
            )
        wrong = row_by_condition.get(("wrong_sign", 0.5), {})
        wrong_sign_effects.append(
            float(wrong.get("target_projection", math.nan)) - baseline_projection
        )
        target_positive = row_by_condition.get(("target_direction", 0.5), {})
        if baseline_logits and logits.get(id(target_positive)):
            label = labels[prompt_id]
            target_logits = logits[id(target_positive)]
            if label == "collateral:utility":
                utility_preservation.append(_top1(baseline_logits) == _top1(target_logits))
            elif label == "collateral:fluency":
                fluency_jsd.append(_jsd(baseline_logits, target_logits))
            elif label == "collateral:safety":
                safety_preservation.append(_top1(baseline_logits) == _top1(target_logits))

    thresholds = lock["thresholds_and_stop_rules"]
    no_op_limit = float(thresholds["no_op_equivalence"]["max_abs_logit_delta"])
    patch_limit = float(thresholds["patch_back"]["maximum_abs_downstream_logit_residual"])
    require(len(no_op_deltas) == 38 and max(no_op_deltas, default=math.inf) <= no_op_limit, "NO_OP_EQUIVALENCE_FAIL")
    require(len(patch_back_deltas) == 38 and max(patch_back_deltas, default=math.inf) <= patch_limit, "PATCH_BACK_FAIL")
    median_effects = {dose: _median(values) for dose, values in target_effects.items()}
    rho = _spearman_for_frozen_doses(median_effects)
    response = thresholds["bidirectional_dose_response"]
    require(rho >= float(response["minimum_spearman_rho"]), "DOSE_RESPONSE_RHO_FAIL")
    floor = float(response["minimum_median_signed_target_margin_effect_at_abs_dose_0_5"])
    require(median_effects[0.5] >= floor and median_effects[-0.5] <= -floor, "BIDIRECTIONAL_EFFECT_FAIL")
    target_abs = abs(median_effects[0.5])
    ceiling = float(
        thresholds["control_effect_ceiling"][
            "maximum_control_to_target_median_abs_effect_ratio"
        ]
    )
    for condition, values in control_effects.items():
        ratio = abs(_median(values)) / target_abs if target_abs > 0 else math.inf
        require(ratio <= ceiling, f"CONTROL_EFFECT_CEILING_FAIL:{condition}")
    wrong_floor = float(thresholds["wrong_sign"]["minimum_median_reversal_fraction"])
    require(
        _median(wrong_sign_effects) <= -wrong_floor * target_abs,
        "WRONG_SIGN_REVERSAL_FAIL",
    )
    utility_floor = float(
        thresholds["utility_floor"]["minimum_baseline_top1_token_preservation_share"]
    )
    require(
        len(utility_preservation) == 2
        and sum(utility_preservation) / len(utility_preservation) >= utility_floor,
        "UTILITY_FLOOR_FAIL",
    )
    fluency_limit = float(
        thresholds["fluency_floor"]["maximum_median_next_token_jsd"]
    )
    require(
        len(fluency_jsd) == 2
        and all(math.isfinite(value) for value in fluency_jsd)
        and _median(fluency_jsd) <= fluency_limit,
        "FLUENCY_FLOOR_FAIL",
    )
    safety_floor = float(
        thresholds["safety_prompt_collateral_floor"][
            "minimum_baseline_top1_token_preservation_share"
        ]
    )
    require(
        len(safety_preservation) == 2
        and sum(safety_preservation) / len(safety_preservation) >= safety_floor,
        "SAFETY_COLLATERAL_FLOOR_FAIL",
    )

    gates = {
        "exact_request_matrix": not any(
            finding.startswith("CONDITION_MATRIX_DRIFT") for finding in findings
        ),
        "no_op_equivalence": "NO_OP_EQUIVALENCE_FAIL" not in findings,
        "bidirectional_dose_response": not any(
            code in findings
            for code in ("DOSE_RESPONSE_RHO_FAIL", "BIDIRECTIONAL_EFFECT_FAIL")
        ),
        "control_effect_ceiling": not any(
            finding.startswith("CONTROL_EFFECT_CEILING_FAIL")
            for finding in findings
        ),
        "wrong_sign_reversal": "WRONG_SIGN_REVERSAL_FAIL" not in findings,
        "utility_floor": "UTILITY_FLOOR_FAIL" not in findings,
        "fluency_floor": "FLUENCY_FLOOR_FAIL" not in findings,
        "safety_collateral_floor": "SAFETY_COLLATERAL_FLOOR_FAIL" not in findings,
        "patch_back": "PATCH_BACK_FAIL" not in findings,
        "compute_cap": "COMPUTE_CAP_EXCEEDED" not in findings,
        "claim_boundary": "CLAIM_BOUNDARY_DRIFT" not in findings,
    }
    return {
        "schema_version": AUDIT_SCHEMA,
        "audit_status": "AUDIT_PASS_RESEARCH_ONLY" if not findings else "FAIL_CLOSED",
        "findings": findings,
        "gates": gates,
        "median_target_effect_by_dose": {
            str(dose): value for dose, value in median_effects.items()
        },
        "spearman_rho": rho,
        "claim_boundary": (
            "Independent offline research audit only. No live steering, safety "
            "or prompt-injection defense, Gate 2, ACCEPT, LICENSED, production "
            "readiness, or production result."
        ),
    }


def audit_result_directory(
    *, repo_root: Path, lock_path: Path, result_root: Path
) -> dict[str, Any]:
    """Audit a future retained packet without importing executor/frameworks."""

    lock = validate_lock_independently(repo_root, lock_path)
    prompt_split = load_json(
        repo_root / lock["frozen_files"]["prompt_split"]["path"]
    )
    result = load_json(result_root / "result.json")
    resolved_root = result_root.resolve()
    retained_receipt = result_root / "authorization_receipt.json"
    retained_lock = result_root / "successor_lock.json"
    journal_path = result_root / "journal.jsonl"
    if (
        not retained_receipt.is_file()
        or sha256_file(retained_receipt) != result.get("retained_receipt_sha256")
        or sha256_file(retained_receipt) != result.get("receipt_sha256")
    ):
        raise PythiaResearchAuditError("Retained receipt binding drift")
    if (
        not retained_lock.is_file()
        or sha256_file(retained_lock) != result.get("retained_lock_sha256")
        or sha256_file(retained_lock) != sha256_file(lock_path)
    ):
        raise PythiaResearchAuditError("Retained successor-lock binding drift")
    receipt = load_json(retained_receipt)
    if (
        receipt.get("lock_sha256") != sha256_file(lock_path)
        or receipt.get("source_commit") != result.get("source_commit")
        or receipt.get("run_id") != result.get("run_id")
    ):
        raise PythiaResearchAuditError("Receipt/result lineage drift")
    for field, key in (
        ("model_manifest_sha256", "model_manifest"),
        ("prompt_split_sha256", "prompt_split"),
        ("intervention_map_sha256", "intervention_map_v2"),
        ("environment_manifest_sha256", "environment_manifest"),
        ("compute_manifest_sha256", "compute_manifest"),
        ("executor_sha256", "executor"),
        ("auditor_sha256", "auditor"),
    ):
        if receipt.get(field) != lock["frozen_files"][key]["sha256"]:
            raise PythiaResearchAuditError(f"Receipt frozen binding drift: {field}")
    if not journal_path.is_file() or sha256_file(journal_path) != result.get(
        "journal_sha256"
    ):
        raise PythiaResearchAuditError("Journal binding drift")
    journal_rows = [
        json.loads(line)
        for line in journal_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    records = result.get("records", [])
    if len(journal_rows) != len(records):
        raise PythiaResearchAuditError("Journal record-count drift")
    for index, (journal, record) in enumerate(
        zip(journal_rows, records, strict=True)
    ):
        if (
            journal.get("index") != index
            or journal.get("record_sha256") != canonical_sha256(record)
            or journal.get("logits_sha256") != record.get("logits_sha256")
        ):
            raise PythiaResearchAuditError(f"Journal lineage drift: {index}")

    def reader(record: Mapping[str, Any]) -> list[float]:
        path = Path(str(record["logits_artifact"])).resolve()
        try:
            path.relative_to(resolved_root)
        except ValueError as exc:
            raise PythiaResearchAuditError("Raw artifact escapes result root") from exc
        return _read_f32(
            path,
            int(record["logits_byte_count"]),
            str(record["logits_sha256"]),
        )

    return audit_result_mapping(
        lock=lock,
        prompt_split=prompt_split,
        result=result,
        logits_reader=reader,
        expected_lock_sha256=sha256_file(lock_path),
    )
