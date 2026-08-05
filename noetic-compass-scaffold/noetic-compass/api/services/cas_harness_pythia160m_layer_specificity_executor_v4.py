"""Receipt-gated real-model executor for the prospective Pythia V4 design.

Top-level imports are standard-library only.  The exact lock and a fresh
one-use receipt are validated, and the nonce is consumed, before torch,
transformers, the model, tokenizer, or any output path can be reached.
"""

from __future__ import annotations

from array import array
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Mapping


LOCK_SCHEMA = "cas_harness_pythia160m_execution_lock.v4"
RECEIPT_SCHEMA = "cas_harness_pythia160m_research_authorization.v4"
RUN_ID_RE = re.compile(r"^pythia160m-riv4-[a-z0-9]{16,64}$")
NONCE_RE = re.compile(r"^[0-9a-f]{64}$")
FEATURE_FLAG = "CAS_PYTHIA160M_LAYER_SPECIFICITY_V4_ENABLED"
LIVE_FLAG = "CAS_PYTHIA160M_RESEARCH_LIVE"
FORBIDDEN_FRAMEWORKS = frozenset({"torch", "transformers", "tokenizers", "safetensors"})


class V4ExecutionError(RuntimeError):
    pass


class V4AuthorizationError(V4ExecutionError):
    pass


@dataclass(frozen=True)
class AuthorizedToken:
    run_id: str
    nonce: str
    output_root: Path
    receipt: Mapping[str, Any]
    receipt_sha256: str
    lock: Mapping[str, Any]
    lock_sha256: str
    nonce_marker: Path
    nonce_consumed: bool = False


def _require(
    condition: bool,
    message: str,
    error: type[V4ExecutionError] = V4ExecutionError,
) -> None:
    if not condition:
        raise error(message)


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


def frameworks_loaded() -> list[str]:
    return sorted(FORBIDDEN_FRAMEWORKS & set(sys.modules))


def _verify_record(repo_root: Path, record: Mapping[str, Any], label: str) -> Path:
    path = repo_root / str(record.get("path", ""))
    _require(path.is_file(), f"{label} missing")
    _require(path.stat().st_size == int(record.get("byte_count", -1)), f"{label} size drift")
    _require(sha256_file(path) == record.get("sha256"), f"{label} hash drift")
    return path


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    _require(spec is not None and spec.loader is not None, f"Cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def current_source_commit(repo_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def validate_execution_lock(repo_root: Path, lock_path: Path) -> dict[str, Any]:
    _require(not frameworks_loaded(), "Framework imported before V4 lock validation")
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
    gates = lock["execution_gates"]
    _require(gates["feature_flag_default"] == "disabled", "Feature default drift")
    _require(gates["live_flag_allowed"] is False, "Live flag boundary drift")
    _require(gates["receipt_status"] == "ABSENT / CREATION_NOT_AUTHORIZED", "Receipt status drift")
    _require(gates["output_status"] == "ABSENT", "Output status drift")
    cap = lock["compute_cap"]
    _require(cap["max_forward_passes"] == cap["frozen_planned_forward_passes"] == 1536, "Forward cap drift")
    _require(cap["max_generated_tokens"] == 0, "Generation cap drift")
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
        _require(cap[field] is False, f"Compute boundary drift: {field}")
    controller_path = repo_root / lock["frozen_files"]["model_free_controller"]["path"]
    controller = _load_module(controller_path, "cas_pythia_v4_frozen_controller")
    prompt_split = load_json(repo_root / lock["frozen_files"]["prompt_split"]["path"])
    diagnostic_lock = load_json(
        repo_root / lock["preserved_prior_evidence"]["v4_diagnostic_lock"]["path"]
    )
    requests = controller.build_request_plan(diagnostic_lock, prompt_split)
    _require(len(requests) == 1536, "Request matrix drift")
    return {
        "lock": lock,
        "request_count": len(requests),
        "controller": controller,
        "diagnostic_lock": diagnostic_lock,
    }


def _receipt_payload(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in receipt.items()
        if key not in {"receipt_payload_sha256"}
    }


def validate_owner_receipt(
    *,
    repo_root: Path,
    lock_path: Path,
    receipt_path: Path,
    output_root: Path,
    allow_static_test_fixture: bool = False,
) -> AuthorizedToken:
    validation = validate_execution_lock(repo_root, lock_path)
    lock = validation["lock"]
    _require(not frameworks_loaded(), "Framework imported before V4 receipt validation")
    _require(receipt_path.is_file(), "Fresh one-use V4 owner authorization receipt is missing", V4AuthorizationError)
    receipt = load_json(receipt_path)
    _require(receipt.get("schema_version") == RECEIPT_SCHEMA, "Receipt schema drift", V4AuthorizationError)
    allowed_status = "STATIC_TEST_FIXTURE_ONLY / NO EXECUTION AUTHORITY"
    if allow_static_test_fixture:
        _require(receipt.get("status") == allowed_status, "Fixture receipt status drift", V4AuthorizationError)
    else:
        _require(receipt.get("status") == "OWNER_AUTHORIZED_ONE_USE", "Receipt not owner-authorized", V4AuthorizationError)
    _require(
        receipt.get("receipt_payload_sha256") == canonical_sha256(_receipt_payload(receipt)),
        "Receipt payload hash drift",
        V4AuthorizationError,
    )
    run_id = str(receipt.get("run_id", ""))
    nonce = str(receipt.get("nonce", ""))
    _require(bool(RUN_ID_RE.fullmatch(run_id)), "Receipt run ID drift", V4AuthorizationError)
    _require(bool(NONCE_RE.fullmatch(nonce)), "Receipt nonce drift", V4AuthorizationError)
    _require(output_root.name == run_id, "Output root/run ID mismatch", V4AuthorizationError)
    _require(not output_root.exists(), "Authorized output root already exists", V4AuthorizationError)
    _require(receipt.get("source_commit") == current_source_commit(repo_root), "Receipt source commit drift", V4AuthorizationError)
    _require(receipt.get("execution_lock_sha256") == sha256_file(lock_path), "Receipt execution lock drift", V4AuthorizationError)
    bindings = receipt.get("bindings", {})
    for label in lock["receipt_contract"]["must_bind_frozen_files"]:
        _require(
            bindings.get(label) == lock["frozen_files"][label]["sha256"],
            f"Receipt binding drift: {label}",
            V4AuthorizationError,
        )
    for label in lock["receipt_contract"]["must_bind_preserved_evidence"]:
        _require(
            bindings.get(label) == lock["preserved_prior_evidence"][label]["sha256"],
            f"Receipt preserved-evidence binding drift: {label}",
            V4AuthorizationError,
        )
    _require(bindings.get("request_count") == 1536, "Receipt request-count drift", V4AuthorizationError)
    _require(bindings.get("compute_cap_sha256") == canonical_sha256(lock["compute_cap"]), "Receipt compute-cap drift", V4AuthorizationError)
    _require(bindings.get("seed_schedule_sha256") == canonical_sha256(lock["seed_schedule"]), "Receipt seed drift", V4AuthorizationError)
    if not allow_static_test_fixture:
        now = datetime.now(timezone.utc)
        created = datetime.fromisoformat(str(receipt["created_at"]).replace("Z", "+00:00"))
        expires = datetime.fromisoformat(str(receipt["expires_at"]).replace("Z", "+00:00"))
        _require(created <= now < expires, "Receipt expired or not yet valid", V4AuthorizationError)
        _require((expires - created).total_seconds() <= 86400, "Receipt validity too long", V4AuthorizationError)
    ledger = repo_root / lock["execution_gates"]["nonce_ledger"]
    marker = ledger / f"{hashlib.sha256(nonce.encode('ascii')).hexdigest()}.used"
    _require(not marker.exists(), "Receipt nonce is stale or consumed", V4AuthorizationError)
    return AuthorizedToken(
        run_id=run_id,
        nonce=nonce,
        output_root=output_root,
        receipt=receipt,
        receipt_sha256=sha256_file(receipt_path),
        lock=lock,
        lock_sha256=sha256_file(lock_path),
        nonce_marker=marker,
    )


def _consume_nonce(token: AuthorizedToken) -> AuthorizedToken:
    token.nonce_marker.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "cas_harness_pythia160m_nonce_marker.v4",
        "run_id": token.run_id,
        "nonce_sha256": hashlib.sha256(token.nonce.encode("ascii")).hexdigest(),
        "consumed_at": datetime.now(timezone.utc).isoformat(),
        "status": "CONSUMED / NON_REUSABLE",
    }
    try:
        with token.nonce_marker.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError as error:
        raise V4AuthorizationError("Receipt nonce is stale or consumed") from error
    return replace(token, nonce_consumed=True)


def _set_offline_environment() -> None:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["CUDA_VISIBLE_DEVICES"] = ""


def _prompt_texts(prompt_split: Mapping[str, Any]) -> dict[str, str]:
    source = load_json(Path(str(prompt_split["source"]["path"])))
    texts = {row["id"]: row["prompt"] for row in source["scenarios"]}
    for row in prompt_split["collateral_heldout"]:
        texts[row["prompt_id"]] = row["text"]
    return texts


def _write_f32(path: Path, values: Any) -> dict[str, Any]:
    payload = array("f", (float(value) for value in values))
    with path.open("xb") as handle:
        payload.tofile(handle)
    return {
        "path": str(path),
        "byte_count": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _first(output: Any) -> Any:
    return output[0] if isinstance(output, tuple) else output


def _replace_first(output: Any, replacement: Any) -> Any:
    if isinstance(output, tuple):
        return (replacement, *output[1:])
    return replacement


def _sparse_direction(torch: Any, record: Mapping[str, Any], hidden_size: int) -> Any:
    vector = torch.zeros(hidden_size, dtype=torch.float32)
    for index, value in zip(record["coordinates"], record["unit_values"], strict=True):
        vector[int(index)] = float(value)
    return vector


def _capture_baseline(
    *,
    torch: Any,
    model: Any,
    tokenizer: Any,
    prompt: str,
    seed: int,
    max_prompt_tokens: int,
) -> dict[str, Any]:
    encoded = tokenizer(prompt, return_tensors="pt", add_special_tokens=True)
    _require(int(encoded["input_ids"].shape[-1]) <= max_prompt_tokens, "Prompt token cap exceeded")
    torch.manual_seed(seed)
    captured: dict[str, Any] = {}

    def layer3_hook(_module: Any, _inputs: Any, output: Any) -> Any:
        captured["layer3"] = _first(output)[:, -1, :].detach().float().cpu().clone()
        return output

    def final_hook(_module: Any, _inputs: Any, output: Any) -> Any:
        captured["final"] = _first(output)[:, -1, :].detach().float().cpu().clone()
        return output

    handles = [
        model.gpt_neox.layers[3].register_forward_hook(layer3_hook),
        model.gpt_neox.layers[11].register_forward_hook(final_hook),
    ]
    started = time.monotonic()
    try:
        with torch.no_grad():
            output = model(**encoded, use_cache=False)
    finally:
        for handle in handles:
            handle.remove()
    return {
        "logits": output.logits[0, -1, :].detach().float().cpu(),
        "layer3": captured["layer3"][0],
        "final": captured["final"][0],
        "token_count": int(encoded["input_ids"].shape[-1]),
        "elapsed_seconds": time.monotonic() - started,
    }


def _run_intervention(
    *,
    torch: Any,
    model: Any,
    tokenizer: Any,
    prompt: str,
    request: Mapping[str, Any],
    intervention: Mapping[str, Any],
    baseline_layer3: Any,
    max_prompt_tokens: int,
) -> dict[str, Any]:
    encoded = tokenizer(prompt, return_tensors="pt", add_special_tokens=True)
    _require(int(encoded["input_ids"].shape[-1]) <= max_prompt_tokens, "Prompt token cap exceeded")
    torch.manual_seed(int(request["seed"]))
    condition = str(request["condition"])
    dose = float(request["dose"])
    layer = int(request["effective_layer"])
    token_index = 0 if condition == "wrong_token" else -1
    direction_name = {
        "same_norm_random_direction": "same_norm_random_direction",
        "wrong_axis": "wrong_axis",
    }.get(condition, "target")
    hidden_size = int(intervention["model_contract"]["hidden_size"])
    direction = _sparse_direction(torch, intervention["directions"][direction_name], hidden_size)
    target_direction = _sparse_direction(torch, intervention["directions"]["target"], hidden_size)
    captured: dict[str, Any] = {}

    def intervention_hook(_module: Any, _inputs: Any, output: Any) -> Any:
        hidden = _first(output)
        modified = hidden.clone()
        modified[:, token_index, :] += dose * direction.to(modified)
        if condition == "target_layer_full_state_patchback":
            modified[:, -1, :] = baseline_layer3.to(modified)
        if layer == 11:
            captured["final"] = modified[:, -1, :].detach().float().cpu().clone()
        return _replace_first(output, modified)

    def layer3_patch_hook(_module: Any, _inputs: Any, output: Any) -> Any:
        hidden = _first(output)
        modified = hidden.clone()
        if condition == "layer2_full_state_patchback":
            modified[:, -1, :] = baseline_layer3.to(modified)
        else:
            current = modified[:, -1, :]
            target = target_direction.to(current)
            delta = ((current.float() - baseline_layer3.to(current).float()) @ target).unsqueeze(-1)
            modified[:, -1, :] = current - delta.to(current) * target
        return _replace_first(output, modified)

    def final_hook(_module: Any, _inputs: Any, output: Any) -> Any:
        captured["final"] = _first(output)[:, -1, :].detach().float().cpu().clone()
        return output

    handles = [model.gpt_neox.layers[layer].register_forward_hook(intervention_hook)]
    if condition in {"layer2_projection_patchback", "layer2_full_state_patchback"}:
        handles.append(model.gpt_neox.layers[3].register_forward_hook(layer3_patch_hook))
    if layer != 11:
        handles.append(model.gpt_neox.layers[11].register_forward_hook(final_hook))
    started = time.monotonic()
    try:
        with torch.no_grad():
            output = model(**encoded, use_cache=False)
    finally:
        for handle in handles:
            handle.remove()
    return {
        "logits": output.logits[0, -1, :].detach().float().cpu(),
        "final": captured["final"][0],
        "token_count": int(encoded["input_ids"].shape[-1]),
        "elapsed_seconds": time.monotonic() - started,
    }


def execute_authorized_run(
    *,
    repo_root: Path,
    lock_path: Path,
    receipt_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    _require(os.environ.get(FEATURE_FLAG, "").lower() in {"1", "true"}, "V4 feature flag disabled", V4AuthorizationError)
    _require(os.environ.get(LIVE_FLAG, "").lower() not in {"1", "true"}, "Live research mode prohibited", V4AuthorizationError)
    token = validate_owner_receipt(
        repo_root=repo_root,
        lock_path=lock_path,
        receipt_path=receipt_path,
        output_root=output_root,
    )
    token = _consume_nonce(token)
    _set_offline_environment()
    _require(token.nonce_consumed, "Nonce not consumed", V4AuthorizationError)
    base_path = repo_root / token.lock["frozen_files"]["immutable_v2_executor"]["path"]
    base = _load_module(base_path, "cas_pythia_v2_runtime_utilities")
    guard = base.ZeroNetworkGuard()
    guard.install()
    output_created = False
    try:
        torch = importlib.import_module("torch")
        transformers = importlib.import_module("transformers")
        torch.set_num_threads(int(token.lock["compute_cap"]["torch_num_threads"]))
        torch.use_deterministic_algorithms(True)
        model_manifest = load_json(repo_root / token.lock["frozen_files"]["model_manifest"]["path"])
        snapshot = Path(model_manifest["snapshot_path"])
        tokenizer = transformers.AutoTokenizer.from_pretrained(
            snapshot, local_files_only=True, trust_remote_code=False
        )
        model = transformers.AutoModelForCausalLM.from_pretrained(
            snapshot,
            local_files_only=True,
            trust_remote_code=False,
            torch_dtype=torch.float32,
        )
        model.to("cpu")
        model.eval()
        _require(not output_root.exists(), "Output appeared before model load")
        output_root.mkdir(parents=True, exist_ok=False)
        output_created = True
        (output_root / "raw_logits").mkdir()
        (output_root / "raw_final_states").mkdir()
        (output_root / "raw_baseline_layer3_states").mkdir()
        shutil.copyfile(receipt_path, output_root / "authorization_receipt.json")
        shutil.copyfile(lock_path, output_root / "execution_lock.json")
        controller = token.lock["_validated_controller"] if "_validated_controller" in token.lock else None
        if controller is None:
            controller_path = repo_root / token.lock["frozen_files"]["model_free_controller"]["path"]
            controller = _load_module(controller_path, "cas_pythia_v4_runtime_controller")
        prompt_split = load_json(repo_root / token.lock["frozen_files"]["prompt_split"]["path"])
        diagnostic_lock = load_json(
            repo_root
            / token.lock["preserved_prior_evidence"]["v4_diagnostic_lock"]["path"]
        )
        plan = controller.build_request_plan(diagnostic_lock, prompt_split)
        texts = _prompt_texts(prompt_split)
        intervention = load_json(repo_root / token.lock["frozen_files"]["intervention_map_v2"]["path"])
        cap = token.lock["compute_cap"]
        _require(len(plan) == cap["max_forward_passes"] == 1536, "Exact forward cap drift")
        records: list[dict[str, Any]] = []
        calibration_states: list[tuple[str, Any]] = []
        heldout_baselines: dict[str, dict[str, Any]] = {}
        started = time.monotonic()
        for index, request in enumerate(plan):
            _require(index < cap["max_forward_passes"], "First prohibited forward pass")
            _require(time.monotonic() - started <= cap["max_wall_clock_seconds"], "Wall-clock cap exceeded")
            prompt_id = request["prompt_id"]
            layer3_artifact = None
            if request["condition"] in {"readout_calibration_baseline", "baseline"}:
                result = _capture_baseline(
                    torch=torch,
                    model=model,
                    tokenizer=tokenizer,
                    prompt=texts[prompt_id],
                    seed=int(request["seed"]),
                    max_prompt_tokens=int(cap["max_prompt_tokens"]),
                )
                if request["condition"] == "readout_calibration_baseline":
                    calibration_states.append((request["label"], result["final"]))
                else:
                    heldout_baselines[prompt_id] = result
                    layer3_path = output_root / "raw_baseline_layer3_states" / f"{len(heldout_baselines)-1:04d}.f32"
                    layer3_artifact = _write_f32(layer3_path, result["layer3"].tolist())
            else:
                baseline = heldout_baselines.get(prompt_id)
                _require(baseline is not None, "Intervention preceded same-prompt baseline")
                result = _run_intervention(
                    torch=torch,
                    model=model,
                    tokenizer=tokenizer,
                    prompt=texts[prompt_id],
                    request=request,
                    intervention=intervention,
                    baseline_layer3=baseline["layer3"],
                    max_prompt_tokens=int(cap["max_prompt_tokens"]),
                )
                layer3_artifact = None
            logits_path = output_root / "raw_logits" / f"{index:04d}.f32"
            state_path = output_root / "raw_final_states" / f"{index:04d}.f32"
            logits_artifact = _write_f32(logits_path, result["logits"].tolist())
            state_artifact = _write_f32(state_path, result["final"].tolist())
            record = {
                **request,
                "text": None,
                "logits_artifact": logits_artifact,
                "final_state_artifact": state_artifact,
                "baseline_layer3_artifact": layer3_artifact,
                "token_count": result["token_count"],
                "elapsed_seconds": result["elapsed_seconds"],
                "finite_logits": bool(torch.isfinite(result["logits"]).all().item()),
                "top1_token_id": int(result["logits"].argmax().item()),
                "generated_tokens": 0,
            }
            records.append(record)
            with (output_root / "journal.jsonl").open(
                "a", encoding="utf-8", newline="\n"
            ) as handle:
                handle.write(
                    json.dumps(record, sort_keys=True, separators=(",", ":"))
                    + "\n"
                )
        target_states = [state for label, state in calibration_states if label == "^0|C"]
        contrast_states = [state for label, state in calibration_states if label == "^0|E"]
        target_mean = torch.stack(target_states).mean(dim=0)
        contrast_mean = torch.stack(contrast_states).mean(dim=0)
        readout = target_mean - contrast_mean
        readout = readout / readout.norm(p=2)
        readout_artifact = _write_f32(output_root / "common_readout.f32", readout.tolist())
        by_prompt_baseline = {
            row["prompt_id"]: row
            for row in records
            if row["condition"] == "baseline"
        }
        for row, request in zip(records, plan, strict=True):
            state = array("f")
            with Path(row["final_state_artifact"]["path"]).open("rb") as handle:
                state.fromfile(handle, 768)
            state_tensor = torch.tensor(state, dtype=torch.float32)
            margin = float(state_tensor @ readout)
            row["final_readout_margin"] = margin
            baseline_row = by_prompt_baseline.get(request["prompt_id"])
            if baseline_row is row or request["split"] == "calibration":
                row["final_readout_margin_delta"] = 0.0
                row["downstream_logit_max_abs_delta"] = 0.0
                row["top1_preserved"] = True
            else:
                row["final_readout_margin_delta"] = margin - float(baseline_row["final_readout_margin"])
                baseline_logits = array("f")
                current_logits = array("f")
                with Path(baseline_row["logits_artifact"]["path"]).open("rb") as handle:
                    baseline_logits.fromfile(handle, 50304)
                with Path(row["logits_artifact"]["path"]).open("rb") as handle:
                    current_logits.fromfile(handle, 50304)
                row["downstream_logit_max_abs_delta"] = max(
                    abs(a - b) for a, b in zip(current_logits, baseline_logits, strict=True)
                )
                row["top1_preserved"] = row["top1_token_id"] == baseline_row["top1_token_id"]
        result = {
            "schema_version": "cas_harness_pythia160m_layer_specificity_result.v4",
            "status": "TERMINAL_UNAUDITED_RESEARCH_ONLY",
            "claim_status": "RESEARCH_ONLY / NO DECISION AUTHORITY",
            "run_id": token.run_id,
            "source_commit": current_source_commit(repo_root),
            "lock_sha256": token.lock_sha256,
            "receipt_sha256": token.receipt_sha256,
            "request_count": len(records),
            "common_readout_artifact": readout_artifact,
            "journal_sha256": sha256_file(output_root / "journal.jsonl"),
            "retained_receipt_sha256": sha256_file(
                output_root / "authorization_receipt.json"
            ),
            "retained_lock_sha256": sha256_file(output_root / "execution_lock.json"),
            "records": records,
        }
        result["result_payload_sha256"] = canonical_sha256(result)
        with (output_root / "result.json").open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
        return result
    except Exception as error:
        if output_created:
            failure_path = output_root / "failure.json"
            if not failure_path.exists():
                failure = {
                    "schema_version": "cas_harness_pythia160m_layer_specificity_failure.v4",
                    "status": "FAIL_CLOSED / NON_REUSABLE / NO RETRY",
                    "run_id": token.run_id,
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "claim_status": "RESEARCH_ONLY / NO DECISION AUTHORITY",
                }
                with failure_path.open("x", encoding="utf-8", newline="\n") as handle:
                    json.dump(failure, handle, indent=2, sort_keys=True)
                    handle.write("\n")
        raise
    finally:
        guard.restore()
