"""Model-free validator for the prospective Pythia-160M steering lock.

This module is intentionally standard-library-only. It inventories and hashes
local files; it never imports a model framework, queries a GPU, opens a socket,
loads a tokenizer/model, or creates scoring output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping


LOCK_RELATIVE_PATH = Path(
    "docs/working/research_intervention_pythia160m_v1/"
    "PYTHIA160M_RESEARCH_LOCK_V1.json"
)
EXPECTED_MODEL_ID = "EleutherAI/pythia-160m"
EXPECTED_REVISION = "50f5173d932e8e61f858120bcb800b97af589f46"
EXPECTED_CONTROLS = {
    "no_op",
    "same_norm_random_direction",
    "wrong_layer",
    "wrong_token",
    "wrong_sign",
    "wrong_axis",
    "patch_back",
}
FORBIDDEN_FRAMEWORK_MODULES = {
    "torch",
    "transformers",
    "tokenizers",
    "safetensors",
}


class PythiaResearchLockError(RuntimeError):
    """The prospective lock or a bound local artifact failed closed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PythiaResearchLockError(f"Cannot read trusted JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PythiaResearchLockError(f"Trusted JSON must be an object: {path}")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PythiaResearchLockError(message)


def _verify_file(path: Path, *, expected_sha256: str, expected_bytes: int | None = None) -> None:
    _require(path.is_file(), f"Missing frozen file: {path}")
    if expected_bytes is not None:
        _require(path.stat().st_size == expected_bytes, f"Byte-count drift: {path}")
    _require(sha256_file(path) == expected_sha256, f"SHA-256 drift: {path}")


def _validate_lock_shape(lock: Mapping[str, Any]) -> None:
    _require(
        lock.get("schema_version") == "cas_harness_pythia160m_research_lock.v1",
        "Unsupported lock schema",
    )
    _require(
        lock.get("status")
        == "PROSPECTIVE_LOCK / MODEL_FREE_VALIDATION_REQUIRED / RUN_NOT_AUTHORIZED",
        "Lock must remain prospective and unauthorized",
    )
    included = lock.get("family_scope", {}).get("included", {})
    _require(included.get("model_id") == EXPECTED_MODEL_ID, "Wrong model family")
    _require(included.get("revision") == EXPECTED_REVISION, "Wrong model revision")
    _require(
        lock.get("family_scope", {}).get("excluded", {}).get("gpt2"),
        "GPT-2 must remain an explicit later comparison",
    )
    executor = lock.get("executor_contract", {})
    _require(
        executor.get("status")
        == "PYTHIA_EXECUTOR_NOT_IMPLEMENTED / NO LIVE RECEIPT MAY BE CREATED",
        "This lock must not imply a real-model executor exists",
    )
    prohibitions = lock.get("current_prohibitions", {})
    _require(prohibitions.get("live_receipt_exists") is False, "Live receipt is prohibited")
    for field in (
        "model_or_tokenizer_load",
        "framework_import_for_validation",
        "gpu_query",
        "network_provider_paid_runpod",
        "live_worker_or_product_change",
        "live_steering",
        "prompt_injection_blocking_or_prevention_claim",
        "production_safety_accept_licensed_gate_claim",
    ):
        _require(
            str(prohibitions.get(field, "")).lower() == "prohibited",
            f"Missing prohibition: {field}",
        )

    compute = lock.get("compute_cap", {})
    expected_compute = {
        "mode": "LOCAL_OFFLINE",
        "device": "CPU_ONLY",
        "torch_num_threads": 8,
        "max_prompt_tokens": 128,
        "max_forward_passes": 512,
        "max_total_prompt_tokens": 65536,
        "max_wall_clock_seconds": 2700,
        "max_generated_tokens": 0,
    }
    for field, expected in expected_compute.items():
        _require(compute.get(field) == expected, f"Compute cap drift: {field}")
    for field in (
        "network_allowed",
        "provider_calls_allowed",
        "paid_compute_allowed",
        "runpod_allowed",
        "gpu_query_allowed",
        "gpu_use_allowed",
        "retry_allowed",
        "resume_allowed",
        "repair_top_up_backfill_allowed",
    ):
        _require(compute.get(field) is False, f"Compute prohibition drift: {field}")

    experiment = lock.get("experiment", {})
    _require(experiment.get("target_layer") == 3, "Target layer drift")
    _require(experiment.get("target_token") == "prompt_final_non_padding_token", "Target token drift")
    _require(
        experiment.get("fixed_doses_l2") == [-0.5, -0.25, 0.0, 0.25, 0.5],
        "Dose grid drift",
    )
    _require(
        set(experiment.get("controls", [])) == EXPECTED_CONTROLS | {"baseline"},
        "Control set drift",
    )
    seeds = experiment.get("seeds", [])
    _require(len(seeds) == 4 and len(set(seeds)) == 4, "Four distinct seeds are required")

    replication = lock.get("replication", {})
    _require(
        replication.get("second_architecture_required_before_broader_claim") is True
        and replication.get("gpt2_status")
        == "LATER_COMPARISON / NOT_PART_OF_THIS_LOCK / NOT_AUTHORIZED"
        and replication.get("broader_claim_status") == "OPEN",
        "Second-architecture claim boundary drift",
    )


def _validate_model_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    _require(
        manifest.get("schema_version") == "cas_harness_pythia160m_model_manifest.v1",
        "Unsupported model manifest schema",
    )
    _require(manifest.get("model_id") == EXPECTED_MODEL_ID, "Model ID drift")
    _require(manifest.get("revision") == EXPECTED_REVISION, "Model revision drift")
    _require(manifest.get("architecture") == "GPTNeoXForCausalLM", "Architecture drift")
    _require(manifest.get("expected_layers") == 12, "Layer-count drift")
    _require(manifest.get("hidden_size") == 768, "Hidden-size drift")
    _require(manifest.get("excluded_models") == ["gpt2"], "GPT-2 exclusion drift")
    inspection = manifest.get("inspection_boundary", {})
    _require(
        inspection
        == {
            "framework_imports_performed": False,
            "model_loads_performed": 0,
            "gpu_queries_performed": 0,
            "network_calls_performed": 0,
        },
        "Static inspection boundary drift",
    )
    files = manifest.get("files", [])
    _require(len(files) == 5, "Exact five-file Pythia snapshot inventory required")
    expected_names = {
        "config.json",
        "model.safetensors",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
    }
    _require({entry.get("name") for entry in files} == expected_names, "Snapshot inventory drift")
    total_bytes = 0
    for entry in files:
        path = Path(str(entry["resolved_blob_path"]))
        _verify_file(
            path,
            expected_sha256=str(entry["sha256"]),
            expected_bytes=int(entry["byte_count"]),
        )
        total_bytes += int(entry["byte_count"])
    tokenizer = manifest.get("tokenizer_binding", {})
    _require(tokenizer.get("model_id") == EXPECTED_MODEL_ID, "Tokenizer family drift")
    _require(tokenizer.get("revision") == EXPECTED_REVISION, "Tokenizer revision drift")
    _require(tokenizer.get("local_files_only_required") is True, "Tokenizer must be local-only")
    _require(tokenizer.get("trust_remote_code") is False, "Remote code must remain disabled")
    return {"snapshot_file_count": len(files), "snapshot_total_bytes": total_bytes}


def _validate_prompt_split(split: Mapping[str, Any]) -> dict[str, Any]:
    _require(
        split.get("schema_version") == "cas_harness_pythia160m_prompt_split.v1",
        "Unsupported prompt split schema",
    )
    _require(split.get("target_label") == "^0|C", "Target label drift")
    _require(split.get("contrast_label") == "^0|E", "Contrast label drift")
    source = split.get("source", {})
    source_path = Path(str(source["path"]))
    _verify_file(
        source_path,
        expected_sha256=str(source["sha256"]),
        expected_bytes=int(source["byte_count"]),
    )
    source_doc = load_json(source_path)
    rows = source_doc.get("scenarios")
    _require(isinstance(rows, list) and len(rows) == 8320, "Scenario source drift")
    by_id = {row.get("id"): row for row in rows if isinstance(row, dict)}
    _require(len(by_id) == 8320, "Scenario IDs must be unique")

    calibration_ids: list[str] = []
    heldout_ids: list[str] = []
    for label in ("^0|C", "^0|E"):
        calibration = split.get("calibration", {}).get(label, [])
        heldout = split.get("heldout", {}).get(label, [])
        _require(len(calibration) == 8 and len(heldout) == 16, f"Split count drift for {label}")
        _require(calibration == sorted(calibration), f"Calibration ordering drift for {label}")
        _require(heldout == sorted(heldout), f"Held-out ordering drift for {label}")
        for prompt_id, expected_split in [
            *((prompt_id, "val") for prompt_id in calibration),
            *((prompt_id, "test") for prompt_id in heldout),
        ]:
            row = by_id.get(prompt_id)
            _require(row is not None, f"Unknown frozen prompt ID: {prompt_id}")
            _require(
                row.get("expected_cas_axes", {}).get("element") == label,
                f"Prompt label drift: {prompt_id}",
            )
            _require(
                row.get("metadata", {}).get("split") == expected_split,
                f"Prompt source-split drift: {prompt_id}",
            )
        calibration_ids.extend(calibration)
        heldout_ids.extend(heldout)

    collateral = split.get("collateral_heldout", [])
    _require(len(collateral) == 6, "Six collateral held-out prompts required")
    collateral_ids = [item.get("prompt_id") for item in collateral]
    _require(len(set(collateral_ids)) == 6, "Collateral prompt IDs must be unique")
    _require(
        {item.get("category") for item in collateral} == {"utility", "fluency", "safety"},
        "Collateral categories drift",
    )
    _require(
        all(isinstance(item.get("text"), str) and item["text"].strip() for item in collateral),
        "Collateral prompt text missing",
    )
    all_ids = calibration_ids + heldout_ids + collateral_ids
    _require(len(all_ids) == len(set(all_ids)), "Calibration and held-out prompts overlap")
    contract = split.get("disjointness_contract", {})
    _require(
        contract.get("calibration_source_split") == "val"
        and contract.get("heldout_source_split") == "test"
        and contract.get("no_id_overlap") is True
        and contract.get("heldout_not_used_for_direction_or_dose_selection") is True,
        "Prompt disjointness contract drift",
    )
    return {
        "calibration_prompt_count": len(calibration_ids),
        "heldout_target_contrast_count": len(heldout_ids),
        "collateral_heldout_count": len(collateral),
    }


def _validate_intervention_map(intervention: Mapping[str, Any]) -> dict[str, Any]:
    _require(
        intervention.get("schema_version")
        == "cas_harness_pythia160m_intervention_map.v1",
        "Unsupported intervention map schema",
    )
    _require(intervention.get("status") == "PROSPECTIVE / NEVER_EXECUTED", "Intervention status drift")
    sources = intervention.get("source_evidence", {})
    for key in ("cover_discovery", "cover_adapter", "matched_ablation_report"):
        source = sources.get(key, {})
        _verify_file(
            Path(str(source["path"])),
            expected_sha256=str(source["sha256"]),
            expected_bytes=int(source["byte_count"]),
        )
    cover = load_json(Path(str(sources["cover_discovery"]["path"])))
    source_rows = cover.get("cover_map", {}).get("^0|C", {}).get("ranked_neurons", [])
    _require(len(source_rows) == 8, "Frozen ^0|C cover must have eight neurons")
    target = intervention.get("target", {})
    coordinates = target.get("coordinates", [])
    raw = target.get("raw_signed_contrast_z", [])
    unit = target.get("unit_values", [])
    _require(coordinates == [int(row["index"]) for row in source_rows], "Target coordinate drift")
    _require(
        all(
            math.isclose(float(actual), float(row["signed_contrast_z"]), rel_tol=0.0, abs_tol=1e-15)
            for actual, row in zip(raw, source_rows, strict=True)
        ),
        "Target source values drift",
    )
    raw_norm = math.sqrt(sum(float(value) ** 2 for value in raw))
    _require(
        math.isclose(raw_norm, float(target["raw_l2_norm"]), rel_tol=0.0, abs_tol=1e-14),
        "Target raw norm drift",
    )
    _require(
        math.isclose(sum(float(value) ** 2 for value in unit), 1.0, rel_tol=0.0, abs_tol=1e-14),
        "Target direction must be unit L2",
    )
    _require(
        all(
            math.isclose(float(actual), float(source) / raw_norm, rel_tol=0.0, abs_tol=1e-14)
            for actual, source in zip(unit, raw, strict=True)
        ),
        "Target normalization drift",
    )
    model = intervention.get("model_contract", {})
    _require(
        model.get("model_id") == EXPECTED_MODEL_ID
        and model.get("revision") == EXPECTED_REVISION
        and model.get("module") == "gpt_neox.layers[3]"
        and model.get("target_layer") == 3
        and model.get("hidden_size") == 768,
        "Intervention model contract drift",
    )
    controls = intervention.get("controls", {})
    _require(set(controls) == EXPECTED_CONTROLS, "Intervention controls drift")
    random_values = controls["same_norm_random_direction"]["unit_values"]
    _require(
        math.isclose(sum(float(value) ** 2 for value in random_values), 1.0, abs_tol=1e-14),
        "Same-norm control drift",
    )
    _require(controls["wrong_layer"].get("layer") == 2, "Wrong-layer control drift")
    _require(
        controls["wrong_token"].get("token") == "prompt_first_non_padding_token",
        "Wrong-token control drift",
    )
    _require(
        intervention.get("fixed_doses_l2") == [-0.5, -0.25, 0.0, 0.25, 0.5],
        "Intervention dose drift",
    )
    return {"target_coordinate_count": len(coordinates), "target_l2_norm": 1.0}


def validate_repository(repo_root: Path, lock_override: Mapping[str, Any] | None = None) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    lock_path = repo_root / LOCK_RELATIVE_PATH
    lock = dict(lock_override) if lock_override is not None else load_json(lock_path)
    _validate_lock_shape(lock)

    frozen: dict[str, dict[str, str]] = {}
    loaded: dict[str, dict[str, Any]] = {}
    for name, record in lock.get("frozen_files", {}).items():
        path = repo_root / str(record["path"])
        _verify_file(path, expected_sha256=str(record["sha256"]))
        frozen[name] = {"path": str(path), "sha256": str(record["sha256"])}
        loaded[name] = load_json(path)
    _require(set(loaded) == {"model_manifest", "prompt_split", "intervention_map"}, "Frozen-file set drift")

    scaffold: dict[str, str] = {}
    for name, record in lock.get("safety_scaffold_bindings", {}).items():
        path = repo_root / str(record["path"])
        _verify_file(path, expected_sha256=str(record["sha256"]))
        scaffold[name] = str(record["sha256"])

    required_executor = repo_root / str(lock["executor_contract"]["required_path"])
    _require(not required_executor.exists(), "A real executor exists but is not bound by a successor lock")
    lock_dir = lock_path.parent
    _require(not list(lock_dir.glob("*RECEIPT*.json")), "Live or stale receipt present beside lock")
    _require(not list(lock_dir.glob("run_*")), "Unauthorized run output present beside lock")

    before = FORBIDDEN_FRAMEWORK_MODULES & set(sys.modules)
    _require(not before, f"Forbidden framework already imported during validation: {sorted(before)}")
    model_summary = _validate_model_manifest(loaded["model_manifest"])
    split_summary = _validate_prompt_split(loaded["prompt_split"])
    intervention_summary = _validate_intervention_map(loaded["intervention_map"])
    after = FORBIDDEN_FRAMEWORK_MODULES & set(sys.modules)
    _require(not after, f"Validator imported forbidden framework: {sorted(after)}")

    return {
        "schema_version": "cas_harness_pythia160m_lock_validation.v1",
        "status": "LOCAL_MODEL_FREE_VALIDATION_PASS / RUN_NOT_AUTHORIZED",
        "lock_path": str(lock_path),
        "lock_sha256": sha256_file(lock_path),
        "frozen_files": frozen,
        "safety_scaffold_sha256": scaffold,
        "model": model_summary,
        "prompt_split": split_summary,
        "intervention": intervention_summary,
        "framework_imports_performed": False,
        "model_loads_performed": 0,
        "gpu_queries_performed": 0,
        "network_calls_performed": 0,
        "receipt_created": False,
        "scoring_output_created": False,
        "next_required_state": (
            "Prospectively implement and locally validate the family-specific executor and "
            "auditor, then create a successor lock before any one-use run receipt."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[4],
    )
    args = parser.parse_args()
    try:
        report = validate_repository(args.repo_root)
    except PythiaResearchLockError as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL_CLOSED",
                    "error": str(exc),
                    "framework_imports_performed": False,
                    "model_loads_performed": 0,
                    "scoring_output_created": False,
                },
                indent=2,
            )
        )
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
