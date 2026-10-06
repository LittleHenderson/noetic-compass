"""Disabled-by-default offline Pythia-160M research intervention executor.

Only the Python standard library is imported at module import time. The sole
framework/model path is guarded by a fresh, exact, one-use owner receipt, nonce
consumption, and an installed zero-network guard. This module has no live
worker, provider, product-decision, or production-verdict integration.
"""

from __future__ import annotations

from array import array
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
from typing import Any, Callable, Mapping, Sequence


LOCK_SCHEMA = "cas_harness_pythia160m_research_lock.v2"
RECEIPT_SCHEMA = "cas_harness_pythia160m_research_authorization.v2"
RESULT_SCHEMA = "cas_harness_pythia160m_research_result.v2"
FEATURE_FLAG = "CAS_PYTHIA160M_RESEARCH_ENABLED"
LIVE_FLAG = "CAS_PYTHIA160M_RESEARCH_LIVE"
EXPECTED_MODEL_ID = "EleutherAI/pythia-160m"
EXPECTED_REVISION = "50f5173d932e8e61f858120bcb800b97af589f46"
FORBIDDEN_FRAMEWORK_MODULES = frozenset(
    {"torch", "transformers", "tokenizers", "safetensors"}
)
RUN_ID_RE = re.compile(r"^pythia160m-riv2-[a-z0-9]{16,64}$")
NONCE_RE = re.compile(r"^[0-9a-f]{64}$")
PROHIBITED_NETWORK_MESSAGE = "network prohibited by Pythia-160M research lock V2"


class PythiaResearchExecutionError(RuntimeError):
    """Base fail-closed exception."""


class PythiaResearchDisabled(PythiaResearchExecutionError):
    """The research-only feature gate is disabled."""


class PythiaResearchLockError(PythiaResearchExecutionError):
    """The successor lock or a frozen binding drifted."""


class PythiaResearchAuthorizationError(PythiaResearchExecutionError):
    """A required fresh one-use owner authorization is absent or invalid."""


class PythiaResearchNetworkBlocked(PythiaResearchExecutionError):
    """A network-capable operation was attempted while offline."""


@dataclass(frozen=True)
class AuthorizedExecutionToken:
    run_id: str
    nonce: str
    receipt_sha256: str
    lock_sha256: str
    source_commit: str
    output_root: Path
    nonce_marker: Path
    validated_at: str
    nonce_consumed: bool = False


class CompatibleZeroNetworkGuard:
    """Block socket construction while preserving socket's class contract."""

    def __init__(self) -> None:
        self._original_socket = socket.socket
        self._original_create_connection = socket.create_connection
        self._original_getaddrinfo = socket.getaddrinfo
        self._original_gethostbyname = socket.gethostbyname
        self.attempts = 0
        self.installed = False

    def _blocked(self, *args: Any, **kwargs: Any) -> Any:
        self.attempts += 1
        raise PythiaResearchNetworkBlocked(PROHIBITED_NETWORK_MESSAGE)

    def install(self) -> None:
        if self.installed:
            raise PythiaResearchExecutionError("zero-network guard already installed")
        original_socket = self._original_socket
        blocked = self._blocked

        class NetworkBlockedSocket(original_socket):
            def __new__(cls, *args: Any, **kwargs: Any) -> Any:
                blocked(*args, **kwargs)
                raise PythiaResearchNetworkBlocked(PROHIBITED_NETWORK_MESSAGE)

        NetworkBlockedSocket.__name__ = "socket"
        NetworkBlockedSocket.__qualname__ = "socket"
        NetworkBlockedSocket.__module__ = "socket"
        socket.socket = NetworkBlockedSocket
        socket.create_connection = self._blocked
        socket.getaddrinfo = self._blocked
        socket.gethostbyname = self._blocked
        self.installed = True

    def restore(self) -> None:
        socket.socket = self._original_socket
        socket.create_connection = self._original_create_connection
        socket.getaddrinfo = self._original_getaddrinfo
        socket.gethostbyname = self._original_gethostbyname
        self.installed = False


def canonical_sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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


def _require(condition: bool, message: str, error: type[Exception] = PythiaResearchLockError) -> None:
    if not condition:
        raise error(message)


def _verify_file(path: Path, record: Mapping[str, Any]) -> None:
    _require(path.is_file(), f"Missing frozen file: {path}")
    if "byte_count" in record:
        _require(path.stat().st_size == int(record["byte_count"]), f"Byte-count drift: {path}")
    _require(sha256_file(path) == str(record["sha256"]), f"SHA-256 drift: {path}")


def _frameworks_loaded() -> set[str]:
    return FORBIDDEN_FRAMEWORK_MODULES & set(sys.modules)


def validate_successor_lock(
    repo_root: Path,
    lock_path: Path,
    *,
    lock_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate every frozen V2 binding without framework import or output."""

    repo_root = repo_root.resolve()
    lock_path = lock_path.resolve()
    before = _frameworks_loaded()
    _require(not before, f"Framework imported before lock validation: {sorted(before)}")
    lock = dict(lock_override) if lock_override is not None else load_json(lock_path)
    _require(lock.get("schema_version") == LOCK_SCHEMA, "Unsupported successor lock schema")
    _require(
        lock.get("status")
        == "PROSPECTIVE_SUCCESSOR_LOCK / EXECUTOR_AUDITOR_LOCAL_STATIC_PASS / RUN_NOT_AUTHORIZED",
        "Successor lock must remain prospective and unauthorized",
    )
    family = lock.get("family_scope", {})
    _require(family.get("model_id") == EXPECTED_MODEL_ID, "Model family drift")
    _require(family.get("revision") == EXPECTED_REVISION, "Model revision drift")
    _require(family.get("architecture") == "GPTNeoXForCausalLM", "Architecture drift")
    _require(family.get("gpt2") == "EXCLUDED_LATER_COMPARISON", "GPT-2 exclusion drift")

    frozen = lock.get("frozen_files", {})
    expected_frozen = {
        "prior_v1_lock",
        "model_manifest",
        "prompt_split",
        "intervention_map_v2",
        "environment_manifest",
        "compute_manifest",
        "executor",
        "auditor",
    }
    _require(set(frozen) == expected_frozen, "Frozen-file inventory drift")
    for name, record in frozen.items():
        _verify_file(repo_root / str(record["path"]), record)

    model = load_json(repo_root / str(frozen["model_manifest"]["path"]))
    _require(model.get("model_id") == EXPECTED_MODEL_ID, "Model manifest family drift")
    _require(model.get("revision") == EXPECTED_REVISION, "Model manifest revision drift")
    _require(model.get("expected_layers") == 12 and model.get("hidden_size") == 768, "Model shape drift")
    _require(len(model.get("files", [])) == 5, "Exact snapshot inventory drift")
    for record in model["files"]:
        _verify_file(Path(str(record["resolved_blob_path"])), record)
    tokenizer = model.get("tokenizer_binding", {})
    _require(
        tokenizer.get("revision") == EXPECTED_REVISION
        and tokenizer.get("local_files_only_required") is True
        and tokenizer.get("trust_remote_code") is False,
        "Tokenizer binding drift",
    )

    prompt_split = load_json(repo_root / str(frozen["prompt_split"]["path"]))
    calibration = prompt_split.get("calibration", {})
    heldout = prompt_split.get("heldout", {})
    calibration_ids = [item for label in ("^0|C", "^0|E") for item in calibration.get(label, [])]
    heldout_ids = [item for label in ("^0|C", "^0|E") for item in heldout.get(label, [])]
    collateral_ids = [item.get("prompt_id") for item in prompt_split.get("collateral_heldout", [])]
    _require(len(calibration_ids) == 16, "Calibration split drift")
    _require(len(heldout_ids) == 32 and len(collateral_ids) == 6, "Held-out split drift")
    _require(
        len(calibration_ids + heldout_ids + collateral_ids)
        == len(set(calibration_ids + heldout_ids + collateral_ids)),
        "Prompt split overlap",
    )
    source = prompt_split.get("source", {})
    _verify_file(Path(str(source["path"])), source)

    intervention = load_json(repo_root / str(frozen["intervention_map_v2"]["path"]))
    _require(
        intervention.get("schema_version")
        == "cas_harness_pythia160m_intervention_map.v2",
        "Intervention-map schema drift",
    )
    _require(intervention.get("status") == "PROSPECTIVE / NEVER_EXECUTED", "Intervention status drift")
    _require(intervention.get("model_contract", {}).get("target_layer") == 3, "Target layer drift")
    _require(
        intervention.get("model_contract", {}).get("target_token")
        == "prompt_final_non_padding_token",
        "Target token drift",
    )
    for direction_name in ("target", "same_norm_random_direction", "wrong_axis"):
        direction = intervention.get("directions", {}).get(direction_name, {})
        values = direction.get("unit_values", [])
        _require(len(values) == 8, f"{direction_name} coordinate-count drift")
        _require(
            math.isclose(sum(float(value) ** 2 for value in values), 1.0, abs_tol=1e-14),
            f"{direction_name} is not unit L2",
        )
    _require(
        intervention.get("fixed_doses_l2") == [-0.5, -0.25, 0.0, 0.25, 0.5],
        "Dose grid drift",
    )
    required_controls = {
        "baseline",
        "no_op",
        "target_direction",
        "same_norm_random_direction",
        "wrong_layer",
        "wrong_token",
        "wrong_sign",
        "wrong_axis",
        "patch_back",
    }
    _require(set(intervention.get("conditions", [])) == required_controls, "Control matrix drift")
    experiment = lock.get("experiment", {})
    _require(
        experiment.get("seeds") == [160003, 160019, 160031, 160057],
        "Experiment seed binding drift",
    )
    _require(
        experiment.get("fixed_doses_l2") == [-0.5, -0.25, 0.0, 0.25, 0.5],
        "Experiment dose binding drift",
    )
    _require(
        set(experiment.get("conditions", [])) == required_controls,
        "Experiment control binding drift",
    )
    _require(
        experiment.get("planned_forward_passes") == 472,
        "Planned forward-pass count drift",
    )

    environment = load_json(repo_root / str(frozen["environment_manifest"]["path"]))
    _require(environment.get("framework_imports_performed") is False, "Environment inspection imported frameworks")
    _require(environment.get("model_loads") == 0 and environment.get("gpu_queries") == 0, "Environment inspection boundary drift")
    for package in environment.get("packages", []):
        _verify_file(Path(str(package["metadata_path"])), package)

    compute = load_json(repo_root / str(frozen["compute_manifest"]["path"]))
    compute_body = {
        key: value for key, value in compute.items() if key != "schema_version"
    }
    _require(
        lock.get("compute_cap") == compute_body,
        "Lock and compute manifest drift",
    )
    expected_compute = {
        "device": "CPU_ONLY",
        "torch_num_threads": 8,
        "max_prompt_tokens": 128,
        "max_forward_passes": 512,
        "max_total_prompt_tokens": 65536,
        "max_wall_clock_seconds": 2700,
        "max_generated_tokens": 0,
    }
    for key, value in expected_compute.items():
        _require(compute.get(key) == value, f"Compute cap drift: {key}")
    for key in (
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
        _require(compute.get(key) is False, f"Compute prohibition drift: {key}")

    gates = lock.get("execution_gates", {})
    _require(gates.get("feature_flag_default") == "disabled", "Feature must default disabled")
    _require(gates.get("live_worker_integration") == "prohibited", "Live worker integration drift")
    _require(gates.get("product_decision_integration") == "prohibited", "Product integration drift")
    _require(gates.get("receipt_status") == "ABSENT / CREATION_NOT_AUTHORIZED", "Receipt boundary drift")
    _require(gates.get("output_status") == "ABSENT", "Output boundary drift")
    _require(lock.get("replication", {}).get("gpt2_status") == "LATER / NOT_AUTHORIZED", "GPT-2 status drift")

    receipt_glob = list(lock_path.parent.glob("*AUTHORIZATION_RECEIPT*.json"))
    run_glob = list(lock_path.parent.glob("runs/*"))
    _require(not receipt_glob, "Receipt exists during preparation-only checkpoint")
    _require(not run_glob, "Run output exists during preparation-only checkpoint")
    after = _frameworks_loaded()
    _require(not after, f"Framework imported during lock validation: {sorted(after)}")
    return {
        "status": "SUCCESSOR_LOCK_MODEL_FREE_PASS / RUN_NOT_AUTHORIZED",
        "lock": lock,
        "lock_sha256": sha256_file(lock_path),
        "calibration_prompt_count": len(calibration_ids),
        "heldout_prompt_count": len(heldout_ids) + len(collateral_ids),
        "snapshot_file_count": len(model["files"]),
        "framework_imports_performed": False,
        "model_loads": 0,
        "gpu_queries": 0,
        "network_calls": 0,
        "receipt_created": False,
        "output_created": False,
    }


def _current_source_commit(repo_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    value = completed.stdout.strip()
    _require(bool(re.fullmatch(r"[0-9a-f]{40}", value)), "Cannot resolve exact source commit")
    return value


def validate_owner_receipt(
    repo_root: Path,
    lock_path: Path,
    receipt_path: Path,
    output_root: Path,
    *,
    now: datetime | None = None,
) -> AuthorizedExecutionToken:
    """Validate a future receipt fully before framework import or output."""

    validation = validate_successor_lock(repo_root, lock_path)
    _require(
        receipt_path.is_file(),
        "Fresh one-use owner authorization receipt is missing",
        PythiaResearchAuthorizationError,
    )
    receipt = load_json(receipt_path)
    _require(receipt.get("schema_version") == RECEIPT_SCHEMA, "Receipt schema drift", PythiaResearchAuthorizationError)
    _require(
        receipt.get("authorization_kind") == "OWNER_ONE_USE_OFFLINE_PYTHIA160M_RESEARCH",
        "Receipt authorization kind drift",
        PythiaResearchAuthorizationError,
    )
    _require(receipt.get("status") == "AUTHORIZED_ONE_USE", "Receipt status drift", PythiaResearchAuthorizationError)
    _require(receipt.get("one_use") is True, "Receipt must be one-use", PythiaResearchAuthorizationError)
    _require(receipt.get("lock_sha256") == validation["lock_sha256"], "Receipt lock binding drift", PythiaResearchAuthorizationError)
    lock = validation["lock"]
    frozen = lock["frozen_files"]
    for field, key in (
        ("model_manifest_sha256", "model_manifest"),
        ("prompt_split_sha256", "prompt_split"),
        ("intervention_map_sha256", "intervention_map_v2"),
        ("environment_manifest_sha256", "environment_manifest"),
        ("compute_manifest_sha256", "compute_manifest"),
        ("executor_sha256", "executor"),
        ("auditor_sha256", "auditor"),
    ):
        _require(receipt.get(field) == frozen[key]["sha256"], f"Receipt binding drift: {field}", PythiaResearchAuthorizationError)
    _require(receipt.get("model_id") == EXPECTED_MODEL_ID, "Receipt model drift", PythiaResearchAuthorizationError)
    _require(receipt.get("model_revision") == EXPECTED_REVISION, "Receipt revision drift", PythiaResearchAuthorizationError)
    _require(receipt.get("seeds") == lock["experiment"]["seeds"], "Receipt seed drift", PythiaResearchAuthorizationError)
    _require(receipt.get("compute_cap") == lock["compute_cap"], "Receipt compute-cap drift", PythiaResearchAuthorizationError)
    run_id = str(receipt.get("run_id", ""))
    nonce = str(receipt.get("nonce", ""))
    _require(bool(RUN_ID_RE.fullmatch(run_id)), "Receipt run ID is invalid", PythiaResearchAuthorizationError)
    _require(bool(NONCE_RE.fullmatch(nonce)), "Receipt nonce must be lowercase 64-hex", PythiaResearchAuthorizationError)
    source_commit = _current_source_commit(repo_root)
    _require(receipt.get("source_commit") == source_commit, "Receipt source commit is stale", PythiaResearchAuthorizationError)
    expected_output = (repo_root / "docs/working/research_intervention_pythia160m_v2/runs" / run_id).resolve()
    _require(output_root.resolve() == expected_output, "Output root is not the isolated run namespace", PythiaResearchAuthorizationError)
    _require(receipt.get("output_root") == str(expected_output), "Receipt output binding drift", PythiaResearchAuthorizationError)
    _require(not expected_output.exists(), "Output root already exists", PythiaResearchAuthorizationError)

    payload = dict(receipt)
    recorded_payload_hash = payload.pop("receipt_payload_sha256", None)
    _require(recorded_payload_hash == canonical_sha256(payload), "Receipt payload hash drift", PythiaResearchAuthorizationError)
    current = now or datetime.now(timezone.utc)
    try:
        created = datetime.fromisoformat(str(receipt["created_at"]).replace("Z", "+00:00"))
        expires = datetime.fromisoformat(str(receipt["expires_at"]).replace("Z", "+00:00"))
    except (KeyError, ValueError) as exc:
        raise PythiaResearchAuthorizationError("Receipt timestamps are invalid") from exc
    _require(created.tzinfo is not None and expires.tzinfo is not None, "Receipt timestamps need timezone", PythiaResearchAuthorizationError)
    _require(created <= current <= expires, "Receipt is not currently valid", PythiaResearchAuthorizationError)
    _require((expires - created).total_seconds() <= 86400, "Receipt validity exceeds 24 hours", PythiaResearchAuthorizationError)
    nonce_marker = (
        repo_root
        / "docs/working/research_intervention_pythia160m_v2/nonce_ledger"
        / f"{hashlib.sha256(nonce.encode('ascii')).hexdigest()}.used"
    ).resolve()
    _require(not nonce_marker.exists(), "Receipt nonce is stale or consumed", PythiaResearchAuthorizationError)
    return AuthorizedExecutionToken(
        run_id=run_id,
        nonce=nonce,
        receipt_sha256=sha256_file(receipt_path),
        lock_sha256=validation["lock_sha256"],
        source_commit=source_commit,
        output_root=expected_output,
        nonce_marker=nonce_marker,
        validated_at=current.isoformat(),
    )


def _consume_nonce(token: AuthorizedExecutionToken) -> AuthorizedExecutionToken:
    token.nonce_marker.parent.mkdir(parents=True, exist_ok=True)
    try:
        with token.nonce_marker.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(
                {
                    "run_id": token.run_id,
                    "nonce_sha256": hashlib.sha256(token.nonce.encode("ascii")).hexdigest(),
                    "receipt_sha256": token.receipt_sha256,
                    "consumed_at": datetime.now(timezone.utc).isoformat(),
                },
                handle,
                sort_keys=True,
            )
            handle.write("\n")
    except FileExistsError as exc:
        raise PythiaResearchAuthorizationError("Receipt nonce already consumed") from exc
    return AuthorizedExecutionToken(**{**token.__dict__, "nonce_consumed": True})


def _set_offline_environment() -> None:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["CUDA_VISIBLE_DEVICES"] = ""


def _import_frameworks_after_authorization(
    token: AuthorizedExecutionToken,
    guard: CompatibleZeroNetworkGuard,
) -> dict[str, Any]:
    _require(token.nonce_consumed, "Nonce must be consumed before framework import", PythiaResearchAuthorizationError)
    _require(guard.installed, "Zero-network guard must precede framework import", PythiaResearchAuthorizationError)
    torch = importlib.import_module("torch")
    transformers = importlib.import_module("transformers")
    return {"torch": torch, "transformers": transformers}


def _load_exact_model(
    token: AuthorizedExecutionToken,
    guard: CompatibleZeroNetworkGuard,
    frameworks: Mapping[str, Any],
    model_manifest: Mapping[str, Any],
) -> tuple[Any, Any]:
    _require(token.nonce_consumed and guard.installed, "Model load preconditions not satisfied", PythiaResearchAuthorizationError)
    torch = frameworks["torch"]
    transformers = frameworks["transformers"]
    torch.set_num_threads(8)
    snapshot_path = str(model_manifest["snapshot_path"])
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        snapshot_path,
        local_files_only=True,
        trust_remote_code=False,
    )
    model = transformers.AutoModelForCausalLM.from_pretrained(
        snapshot_path,
        local_files_only=True,
        trust_remote_code=False,
        torch_dtype=torch.float32,
    )
    model.to("cpu")
    model.eval()
    _require(model.config.model_type == "gpt_neox", "Loaded model architecture drift")
    _require(int(model.config.hidden_size) == 768, "Loaded hidden size drift")
    _require(int(model.config.num_hidden_layers) == 12, "Loaded layer count drift")
    return tokenizer, model


def _sparse_direction(torch: Any, direction: Mapping[str, Any]) -> Any:
    vector = torch.zeros(768, dtype=torch.float32)
    for index, value in zip(direction["coordinates"], direction["unit_values"], strict=True):
        vector[int(index)] = float(value)
    return vector


def _replace_first(output: Any, replacement: Any) -> Any:
    if isinstance(output, tuple):
        return (replacement, *output[1:])
    return replacement


def _first(output: Any) -> Any:
    return output[0] if isinstance(output, tuple) else output


def _execute_request(
    *,
    torch: Any,
    model: Any,
    tokenizer: Any,
    prompt: str,
    request: Mapping[str, Any],
    intervention: Mapping[str, Any],
    max_prompt_tokens: int,
    artifact_path: Path,
) -> dict[str, Any]:
    encoded = tokenizer(prompt, return_tensors="pt", add_special_tokens=True)
    token_count = int(encoded["input_ids"].shape[-1])
    _require(token_count <= max_prompt_tokens, "Prompt exceeds frozen token cap")
    seed = int(request["seed"])
    torch.manual_seed(seed)
    condition = str(request["condition"])
    dose = float(request["dose"])
    target_layer = int(intervention["model_contract"]["target_layer"])
    layer = target_layer
    token_index = -1
    direction_name = "target"
    patch_back = False
    if condition == "wrong_layer":
        layer = int(intervention["controls"]["wrong_layer"]["layer"])
    elif condition == "wrong_token":
        token_index = 0
    elif condition == "same_norm_random_direction":
        direction_name = "same_norm_random_direction"
    elif condition == "wrong_axis":
        direction_name = "wrong_axis"
    elif condition == "wrong_sign":
        dose = -abs(dose)
    elif condition == "patch_back":
        patch_back = True
    elif condition in {"baseline", "no_op"}:
        dose = 0.0

    directions = intervention["directions"]
    direction = _sparse_direction(torch, directions[direction_name])
    target_direction = _sparse_direction(torch, directions["target"])
    captured: dict[str, float] = {}

    def intervention_hook(_module: Any, _inputs: Any, output: Any) -> Any:
        hidden = _first(output)
        original = hidden
        modified = original.clone()
        modified[:, token_index, :] = modified[:, token_index, :] + dose * direction.to(
            dtype=modified.dtype, device=modified.device
        )
        captured["attempted_target_projection"] = float(
            (modified[:, -1, :].float() @ target_direction).item()
        )
        if patch_back:
            captured["target_projection"] = float(
                (original[:, -1, :].float() @ target_direction).item()
            )
            return output
        if layer == target_layer:
            captured["target_projection"] = float(
                (modified[:, -1, :].float() @ target_direction).item()
            )
        return _replace_first(output, modified)

    def measurement_hook(_module: Any, _inputs: Any, output: Any) -> Any:
        hidden = _first(output)
        captured["target_projection"] = float(
            (hidden[:, -1, :].float() @ target_direction).item()
        )
        return output

    handles: list[Any] = []
    if condition == "baseline":
        handles.append(
            model.gpt_neox.layers[target_layer].register_forward_hook(measurement_hook)
        )
    else:
        handles.append(
            model.gpt_neox.layers[layer].register_forward_hook(intervention_hook)
        )
        if layer != target_layer:
            handles.append(
                model.gpt_neox.layers[target_layer].register_forward_hook(
                    measurement_hook
                )
            )
    started = time.monotonic()
    try:
        with torch.no_grad():
            output = model(**encoded, use_cache=False)
    finally:
        for handle in handles:
            handle.remove()
    elapsed = time.monotonic() - started
    logits = output.logits[0, -1, :].detach().float().cpu()
    values = array("f", (float(value) for value in logits.tolist()))
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with artifact_path.open("wb") as handle_out:
        values.tofile(handle_out)
    probabilities = torch.softmax(logits, dim=-1)
    return {
        **dict(request),
        "effective_layer": layer,
        "effective_token_index": token_index,
        "effective_direction": direction_name,
        "effective_dose": dose,
        "token_count": token_count,
        "target_projection": captured.get("target_projection"),
        "attempted_target_projection": captured.get(
            "attempted_target_projection"
        ),
        "top1_token_id": int(torch.argmax(logits).item()),
        "finite_logits": bool(torch.isfinite(logits).all().item()),
        "probability_sum": float(probabilities.sum().item()),
        "logits_artifact": str(artifact_path),
        "logits_byte_count": artifact_path.stat().st_size,
        "logits_sha256": sha256_file(artifact_path),
        "elapsed_seconds": elapsed,
    }


def _prompt_rows(prompt_split: Mapping[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    source = load_json(Path(str(prompt_split["source"]["path"])))
    by_id = {row["id"]: row for row in source["scenarios"]}
    calibration: list[dict[str, str]] = []
    heldout: list[dict[str, str]] = []
    for label in ("^0|C", "^0|E"):
        for prompt_id in prompt_split["calibration"][label]:
            calibration.append({"prompt_id": prompt_id, "label": label, "text": by_id[prompt_id]["prompt"]})
        for prompt_id in prompt_split["heldout"][label]:
            heldout.append({"prompt_id": prompt_id, "label": label, "text": by_id[prompt_id]["prompt"]})
    for row in prompt_split["collateral_heldout"]:
        heldout.append(
            {
                "prompt_id": row["prompt_id"],
                "label": f"collateral:{row['category']}",
                "text": row["text"],
            }
        )
    return calibration, heldout


def build_request_plan(lock: Mapping[str, Any], prompt_split: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build the exact 472-forward plan using only frozen data."""

    calibration, heldout = _prompt_rows(prompt_split)
    seeds = list(lock["experiment"]["seeds"])
    requests: list[dict[str, Any]] = []
    for index, prompt in enumerate(calibration):
        requests.append(
            {
                "prompt_id": prompt["prompt_id"],
                "label": prompt["label"],
                "split": "calibration",
                "condition": "baseline",
                "dose": 0.0,
                "seed": seeds[index % len(seeds)],
                "text": prompt["text"],
            }
        )
    conditions = [
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
    ]
    for index, prompt in enumerate(heldout):
        for condition, dose in conditions:
            requests.append(
                {
                    "prompt_id": prompt["prompt_id"],
                    "label": prompt["label"],
                    "split": "heldout",
                    "condition": condition,
                    "dose": dose,
                    "seed": seeds[index % len(seeds)],
                    "text": prompt["text"],
                }
            )
    return requests


def execute_authorized_run(
    *,
    repo_root: Path,
    lock_path: Path,
    receipt_path: Path,
    output_root: Path,
) -> int:
    """Execute exactly once after all future authorization gates pass."""

    if os.environ.get(FEATURE_FLAG, "").strip().lower() not in {"1", "true", "yes"}:
        raise PythiaResearchDisabled(f"{FEATURE_FLAG} is disabled")
    if os.environ.get(LIVE_FLAG, "").strip().lower() in {"1", "true", "yes"}:
        raise PythiaResearchDisabled(f"{LIVE_FLAG} is permanently prohibited")
    _require(not _frameworks_loaded(), "Framework imported before authorization", PythiaResearchAuthorizationError)
    token = validate_owner_receipt(repo_root, lock_path, receipt_path, output_root)
    token = _consume_nonce(token)
    _set_offline_environment()
    guard = CompatibleZeroNetworkGuard()
    guard.install()
    try:
        frameworks = _import_frameworks_after_authorization(token, guard)
        lock = load_json(lock_path)
        frozen = lock["frozen_files"]
        model_manifest = load_json(repo_root / frozen["model_manifest"]["path"])
        prompt_split = load_json(repo_root / frozen["prompt_split"]["path"])
        intervention = load_json(repo_root / frozen["intervention_map_v2"]["path"])
        tokenizer, model = _load_exact_model(token, guard, frameworks, model_manifest)
        requests = build_request_plan(lock, prompt_split)
        compute = lock["compute_cap"]
        _require(len(requests) == 472, "Frozen request count drift")
        _require(len(requests) <= int(compute["max_forward_passes"]), "Forward-pass cap exceeded")
        output_root.mkdir(parents=True, exist_ok=False)
        retained_receipt = output_root / "authorization_receipt.json"
        retained_lock = output_root / "successor_lock.json"
        shutil.copyfile(receipt_path, retained_receipt)
        shutil.copyfile(lock_path, retained_lock)
        raw_root = output_root / "raw_logits"
        journal_path = output_root / "journal.jsonl"
        records: list[dict[str, Any]] = []
        started = time.monotonic()
        try:
            for index, request in enumerate(requests):
                if time.monotonic() - started > float(compute["max_wall_clock_seconds"]):
                    raise PythiaResearchExecutionError("Frozen wall-clock cap exceeded")
                record = _execute_request(
                    torch=frameworks["torch"],
                    model=model,
                    tokenizer=tokenizer,
                    prompt=request["text"],
                    request={
                        key: value for key, value in request.items() if key != "text"
                    },
                    intervention=intervention,
                    max_prompt_tokens=int(compute["max_prompt_tokens"]),
                    artifact_path=raw_root / f"{index:04d}.f32",
                )
                records.append(record)
                with journal_path.open("a", encoding="utf-8", newline="\n") as journal:
                    journal.write(
                        json.dumps(
                            {
                                "index": index,
                                "record_sha256": canonical_sha256(record),
                                "logits_sha256": record["logits_sha256"],
                            },
                            sort_keys=True,
                        )
                        + "\n"
                    )
        except Exception as exc:
            failure = {
                "schema_version": "cas_harness_pythia160m_research_failure.v2",
                "status": "FAIL_CLOSED / NON_REUSABLE / NO RETRY",
                "run_id": token.run_id,
                "completed_request_count": len(records),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "journal_sha256": (
                    sha256_file(journal_path) if journal_path.is_file() else None
                ),
                "claim_status": "OPEN / NOT_LICENSED / NO ACCEPT / NO PRODUCTION EFFECT",
            }
            (output_root / "failure.json").write_text(
                json.dumps(failure, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            raise
        payload: dict[str, Any] = {
            "schema_version": RESULT_SCHEMA,
            "status": "TERMINAL_UNAUDITED_RESEARCH_ONLY",
            "run_id": token.run_id,
            "source_commit": token.source_commit,
            "lock_sha256": token.lock_sha256,
            "receipt_sha256": token.receipt_sha256,
            "request_count": len(records),
            "records": records,
            "journal_sha256": sha256_file(journal_path),
            "retained_receipt_sha256": sha256_file(retained_receipt),
            "retained_lock_sha256": sha256_file(retained_lock),
            "network_attempts": guard.attempts,
            "claim_status": "OPEN / NOT_LICENSED / NO ACCEPT / NO PRODUCTION EFFECT",
        }
        payload["result_payload_sha256"] = canonical_sha256(payload)
        result_path = output_root / "result.json"
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0
    finally:
        guard.restore()


def static_guard_fixture() -> dict[str, Any]:
    """Exercise only the compatible guard; never import a framework or write."""

    before = _frameworks_loaded()
    _require(not before, f"Framework present before fixture: {sorted(before)}")
    guard = CompatibleZeroNetworkGuard()
    original = socket.socket
    guard.install()
    try:
        _require(isinstance(socket.socket, type), "Guarded socket is not a class")
        _require(issubclass(socket.socket, original), "Guarded socket is not compatible")
        try:
            socket.socket()
        except PythiaResearchNetworkBlocked:
            pass
        else:
            raise PythiaResearchExecutionError("Guard allowed socket construction")
    finally:
        guard.restore()
    after = _frameworks_loaded()
    _require(not after, f"Fixture imported framework: {sorted(after)}")
    return {
        "status": "STATIC_ZERO_NETWORK_GUARD_PASS",
        "blocked_attempts": guard.attempts,
        "socket_restored": socket.socket is original,
        "framework_imports": 0,
        "model_loads": 0,
        "gpu_queries": 0,
        "output_created": False,
    }
