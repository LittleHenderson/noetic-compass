"""Independent standard-library artifact auditor for Pythia V4."""

from __future__ import annotations

from array import array
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping


LOCK_SCHEMA = "cas_harness_pythia160m_execution_lock.v4"
RESULT_SCHEMA = "cas_harness_pythia160m_layer_specificity_result.v4"
FORBIDDEN_FRAMEWORKS = frozenset({"torch", "transformers", "tokenizers", "safetensors"})


class V4AuditError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise V4AuditError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def _verify_record(repo_root: Path, record: Mapping[str, Any], label: str) -> Path:
    path = repo_root / str(record.get("path", ""))
    _require(path.is_file(), f"{label} missing")
    _require(path.stat().st_size == int(record.get("byte_count", -1)), f"{label} size drift")
    _require(sha256_file(path) == record.get("sha256"), f"{label} hash drift")
    return path


def _load_controller(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("cas_pythia_v4_audit_spec", path)
    _require(spec is not None and spec.loader is not None, "Cannot load frozen audit specification")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_lock_independently(repo_root: Path, lock_path: Path) -> dict[str, Any]:
    _require(not (FORBIDDEN_FRAMEWORKS & set(sys.modules)), "Framework imported before independent audit")
    lock = load_json(lock_path)
    _require(lock.get("schema_version") == LOCK_SCHEMA, "Execution lock schema drift")
    _require(
        lock.get("status")
        == "PROSPECTIVE_EXECUTION_LOCK / EXECUTOR_AUDITOR_MODEL_FREE_PASS / RUN_NOT_AUTHORIZED",
        "Execution lock status drift",
    )
    for label, record in lock["preserved_prior_evidence"].items():
        _verify_record(repo_root, record, f"preserved_prior_evidence.{label}")
    for label, record in lock["frozen_files"].items():
        _verify_record(repo_root, record, f"frozen_files.{label}")
    _require(lock["compute_cap"]["max_forward_passes"] == 1536, "Compute cap drift")
    _require(lock["compute_cap"]["max_generated_tokens"] == 0, "Generation cap drift")
    return lock


def _read_f32(path: Path, artifact: Mapping[str, Any], expected_count: int) -> list[float]:
    _require(path.is_file(), f"Artifact missing: {path}")
    _require(path.stat().st_size == expected_count * 4, f"Artifact size drift: {path}")
    _require(path.stat().st_size == int(artifact["byte_count"]), f"Recorded byte count drift: {path}")
    _require(sha256_file(path) == artifact["sha256"], f"Artifact hash drift: {path}")
    values = array("f")
    with path.open("rb") as handle:
        values.fromfile(handle, expected_count)
    result = [float(value) for value in values]
    _require(all(math.isfinite(value) for value in result), f"Nonfinite artifact: {path}")
    return result


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _max_abs_delta(left: list[float], right: list[float]) -> float:
    return max(abs(a - b) for a, b in zip(left, right, strict=True))


def _recompute_readout(
    calibration: list[tuple[str, list[float]]],
) -> list[float]:
    target = [state for label, state in calibration if label == "^0|C"]
    contrast = [state for label, state in calibration if label == "^0|E"]
    _require(len(target) == len(contrast) == 8, "Calibration label-count drift")
    target_mean = [sum(row[i] for row in target) / 8.0 for i in range(768)]
    contrast_mean = [sum(row[i] for row in contrast) / 8.0 for i in range(768)]
    vector = [a - b for a, b in zip(target_mean, contrast_mean, strict=True)]
    norm = math.sqrt(sum(value * value for value in vector))
    _require(norm > 0 and math.isfinite(norm), "Degenerate common readout")
    return [value / norm for value in vector]


def audit_result_directory(
    *,
    repo_root: Path,
    lock_path: Path,
    run_dir: Path,
) -> dict[str, Any]:
    lock = validate_lock_independently(repo_root, lock_path)
    _require(not (run_dir / "failure.json").exists(), "Run has fail-closed terminal packet")
    retained_lock = run_dir / "execution_lock.json"
    retained_receipt = run_dir / "authorization_receipt.json"
    result_path = run_dir / "result.json"
    journal_path = run_dir / "journal.jsonl"
    for path in (retained_lock, retained_receipt, result_path, journal_path):
        _require(path.is_file(), f"Terminal artifact missing: {path.name}")
    _require(sha256_file(retained_lock) == sha256_file(lock_path), "Retained lock drift")
    result = load_json(result_path)
    _require(result.get("schema_version") == RESULT_SCHEMA, "Result schema drift")
    payload = {key: value for key, value in result.items() if key != "result_payload_sha256"}
    _require(result.get("result_payload_sha256") == canonical_sha256(payload), "Result payload drift")
    _require(result.get("status") == "TERMINAL_UNAUDITED_RESEARCH_ONLY", "Result status drift")
    _require(result.get("claim_status") == "RESEARCH_ONLY / NO DECISION AUTHORITY", "Result claim drift")
    _require(result.get("lock_sha256") == sha256_file(lock_path), "Result lock binding drift")
    _require(result.get("retained_lock_sha256") == sha256_file(retained_lock), "Retained lock result drift")
    _require(result.get("retained_receipt_sha256") == sha256_file(retained_receipt), "Retained receipt result drift")
    _require(result.get("journal_sha256") == sha256_file(journal_path), "Journal hash drift")
    records = result.get("records", [])
    _require(len(records) == result.get("request_count") == 1536, "Exact request count drift")
    controller_path = repo_root / lock["frozen_files"]["model_free_controller"]["path"]
    controller = _load_controller(controller_path)
    prompt_split = load_json(repo_root / lock["frozen_files"]["prompt_split"]["path"])
    diagnostic_lock = load_json(
        repo_root / lock["preserved_prior_evidence"]["v4_diagnostic_lock"]["path"]
    )
    expected = controller.build_request_plan(diagnostic_lock, prompt_split)
    key_fields = ("prompt_id", "split", "condition", "dose", "effective_layer", "seed")
    _require(
        [tuple(row.get(field) for field in key_fields) for row in records]
        == [tuple(row[field] for field in key_fields) for row in expected],
        "Request order or binding drift",
    )
    calibration: list[tuple[str, list[float]]] = []
    state_by_index: list[list[float]] = []
    logits_by_index: list[list[float]] = []
    raw_bytes = 0
    baseline_by_prompt: dict[str, int] = {}
    baseline_layer3_count = 0
    for index, row in enumerate(records):
        logits_artifact = row["logits_artifact"]
        state_artifact = row["final_state_artifact"]
        logits = _read_f32(Path(logits_artifact["path"]), logits_artifact, 50304)
        state = _read_f32(Path(state_artifact["path"]), state_artifact, 768)
        logits_by_index.append(logits)
        state_by_index.append(state)
        raw_bytes += int(logits_artifact["byte_count"]) + int(state_artifact["byte_count"])
        _require(row.get("generated_tokens") == 0, "Generated-token drift")
        _require(row.get("finite_logits") is True, "Finite-logit record drift")
        _require(int(row["top1_token_id"]) == max(range(len(logits)), key=logits.__getitem__), "Top1 drift")
        if row["condition"] == "readout_calibration_baseline":
            calibration.append((row["label"], state))
        if row["condition"] == "baseline":
            baseline_by_prompt[row["prompt_id"]] = index
            artifact = row.get("baseline_layer3_artifact")
            _require(isinstance(artifact, dict), "Baseline layer-3 artifact missing")
            _read_f32(Path(artifact["path"]), artifact, 768)
            raw_bytes += int(artifact["byte_count"])
            baseline_layer3_count += 1
        else:
            _require(row.get("baseline_layer3_artifact") is None, "Unexpected layer-3 artifact")
    _require(baseline_layer3_count == 38, "Baseline layer-3 artifact count drift")
    readout = _recompute_readout(calibration)
    recorded_readout = _read_f32(
        Path(result["common_readout_artifact"]["path"]),
        result["common_readout_artifact"],
        768,
    )
    raw_bytes += int(result["common_readout_artifact"]["byte_count"])
    _require(_max_abs_delta(readout, recorded_readout) <= 0.000001, "Common readout reconstruction drift")
    _require(raw_bytes <= int(lock["compute_cap"]["max_raw_artifact_bytes"]), "Raw artifact byte cap exceeded")
    audited_rows: list[dict[str, Any]] = []
    for index, row in enumerate(records):
        audited = dict(row)
        margin = _dot(state_by_index[index], readout)
        _require(abs(margin - float(row["final_readout_margin"])) <= 0.00001, "Readout margin drift")
        baseline_index = baseline_by_prompt.get(row["prompt_id"])
        if row["split"] == "calibration" or row["condition"] == "baseline":
            delta = 0.0
            logit_delta = 0.0
            top1_preserved = True
        else:
            _require(baseline_index is not None, "Same-prompt baseline missing")
            delta = margin - _dot(state_by_index[baseline_index], readout)
            logit_delta = _max_abs_delta(logits_by_index[index], logits_by_index[baseline_index])
            top1_preserved = (
                row["top1_token_id"] == records[baseline_index]["top1_token_id"]
            )
        _require(abs(delta - float(row["final_readout_margin_delta"])) <= 0.00001, "Readout delta drift")
        _require(abs(logit_delta - float(row["downstream_logit_max_abs_delta"])) <= 0.00001, "Logit delta drift")
        _require(bool(row["top1_preserved"]) == top1_preserved, "Top1 preservation drift")
        audited["final_readout_margin"] = margin
        audited["final_readout_margin_delta"] = delta
        audited["downstream_logit_max_abs_delta"] = logit_delta
        audited["top1_preserved"] = top1_preserved
        audited_rows.append(audited)
    audit = controller.audit_result_mapping(
        lock=diagnostic_lock,
        prompt_split=prompt_split,
        packet={"records": audited_rows},
    )
    audit.update(
        {
            "schema_version": "cas_harness_pythia160m_layer_specificity_artifact_audit.v4",
            "auditor_framework_imports": [],
            "raw_artifact_bytes": raw_bytes,
            "raw_logits_count": 1536,
            "raw_final_state_count": 1536,
            "raw_baseline_layer3_count": 38,
            "receipt_sha256": sha256_file(retained_receipt),
            "lock_sha256": sha256_file(lock_path),
            "result_sha256": sha256_file(result_path),
            "claim_status": "RESEARCH_ONLY / NO DECISION AUTHORITY",
        }
    )
    return audit
