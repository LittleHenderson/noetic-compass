"""Shared schema and hashing primitives for WELD v3.

This module intentionally contains no scientific scoring rule. The bound Rust
adapter owns all detection and repair decisions; Python validates closed enums.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


PROTOCOL_SCHEMA = "weld-v3-protocol/2"
PUBLIC_CASES_SCHEMA = "weld-v3-public-cases/1"
PUBLIC_CASE_SCHEMA = "weld-v3-public-case/1"
ACTOR_OUTPUT_SCHEMA = "weld-v3-actor-output/1"
ACTOR_RECEIPT_SCHEMA = "weld-v3-actor-receipt/2"
ACTOR_RECEIPT_SEAL_SCHEMA = "weld-v3-actor-receipt-seal/1"
TRUTH_SCHEMA = "weld-v3-sealed-truth/1"
TRUTH_COMMITMENT_SCHEMA = "weld-v3-truth-commitment/2"
EXTERNAL_COMMITMENT_EVIDENCE_SCHEMA = "weld-v3-external-commitment-evidence/1"
CUSTODIAN_RELEASE_SCHEMA = "weld-v3-custodian-release/1"
ADJUDICATION_SCHEMA = "weld-v3-adjudication/2"
FREEZE_SCHEMA = "weld-v3-freeze-receipt/2"

FIXED_PIPELINE = (
    "INGEST_PUBLIC_CARRIER",
    "J1_CONTRACT_GATE",
    "COMPILE_OR_VALIDATE_ARTIFACT",
    "DIAGNOSE",
    "LOCALIZE",
    "REPAIR",
    "VERIFY",
    "J2_CONTRACT_GATE",
    "STAGE5_CONTRACT_GATE",
    "EMIT_DECISION",
)

ALLOWED_DECISIONS = frozenset(
    {
        "REPAIR_ACCEPTED",
        "NO_REPAIR_NEEDED",
        "REPAIR_REJECTED",
        "PIPELINE_ERROR",
    }
)
MODEL_ADAPTER_STATUS = {"J1": "NOT_RUN", "J2": "NOT_RUN", "STAGE5": "NOT_RUN"}

_CASE_ID = re.compile(r"^[0-9a-f]{32}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_LOWER_HEX = re.compile(r"^[0-9a-f]+$")
_LEXICAL_TOKEN = re.compile(r"\w+|[^\w\s]", flags=re.UNICODE)
_FORBIDDEN_PUBLIC_KEYS = frozenset(
    {
        "truth",
        "expected",
        "role",
        "label",
        "positive",
        "negative",
        "control",
        "target",
        "gold",
        "pair_id",
        "target_case_id",
        "control_case_id",
    }
)


class WeldProtocolError(RuntimeError):
    """Raised when an input violates the frozen WELD-v3 protocol."""


def canonical_json_bytes(value: Any) -> bytes:
    try:
        rendered = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise WeldProtocolError(f"value is not canonical JSON: {exc}") from exc
    return (rendered + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WeldProtocolError(f"cannot read JSON {path}: {exc}") from exc


def write_exclusive_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(canonical_json_bytes(value).decode("utf-8"))
    except FileExistsError as exc:
        raise WeldProtocolError(f"refusing to overwrite {path}") from exc


def require_mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise WeldProtocolError(f"{where} must be an object")
    return value


def require_exact_keys(value: Mapping[str, Any], expected: Iterable[str], where: str) -> None:
    expected_set = set(expected)
    actual_set = set(value)
    if actual_set != expected_set:
        missing = sorted(expected_set - actual_set)
        extra = sorted(actual_set - expected_set)
        raise WeldProtocolError(f"{where} key mismatch; missing={missing}, extra={extra}")


def require_sha256(value: Any, where: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise WeldProtocolError(f"{where} must be a lowercase 64-hex SHA-256")
    return value


def require_high_entropy_hex(value: Any, where: str, *, minimum_bytes: int = 32) -> str:
    """Validate an encoded random value without claiming to prove randomness.

    Length and encoding are mechanically enforceable. Entropy source and custody
    remain external evidence requirements.
    """
    if (
        not isinstance(value, str)
        or len(value) < minimum_bytes * 2
        or len(value) % 2
        or not _LOWER_HEX.fullmatch(value)
    ):
        raise WeldProtocolError(
            f"{where} must be lowercase hex encoding at least {minimum_bytes} bytes"
        )
    if len(set(bytes.fromhex(value))) < 16:
        raise WeldProtocolError(
            f"{where} fails the minimum byte-diversity floor; CSPRNG origin still requires "
            "external custodian evidence"
        )
    return value


def require_nonempty_string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WeldProtocolError(f"{where} must be a non-empty string")
    return value


def _reject_public_truth_keys(value: Any, where: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise WeldProtocolError(f"{where} contains a non-string key")
            normalized_key = key.casefold()
            if any(token in normalized_key for token in _FORBIDDEN_PUBLIC_KEYS):
                raise WeldProtocolError(f"{where} contains forbidden truth-bearing key {key!r}")
            _reject_public_truth_keys(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_public_truth_keys(child, f"{where}[{index}]")


def validate_protocol(protocol: Any) -> Mapping[str, Any]:
    item = require_mapping(protocol, "protocol")
    required = {
        "schema_version",
        "protocol_id",
        "experimental_status",
        "validation_status",
        "provider_calls",
        "fixed_pipeline",
        "allowed_decisions",
        "python_decision_policy",
        "pair_policy",
        "overall_policy",
        "runtime_profile_required_for_real_run",
        "truth_phase_policy",
        "actor_receipt_policy",
        "case_cwd_policy",
        "production_adjudication_status",
        "model_adapter_status",
    }
    require_exact_keys(item, required, "protocol")
    if item["schema_version"] != PROTOCOL_SCHEMA:
        raise WeldProtocolError("unsupported protocol schema")
    require_nonempty_string(item["protocol_id"], "protocol.protocol_id")
    if item["experimental_status"] != "NOT_RUN" or item["validation_status"] != "NOT_VALIDATED":
        raise WeldProtocolError("the checked protocol must remain NOT_RUN and NOT_VALIDATED")
    if item["provider_calls"] != "FORBIDDEN":
        raise WeldProtocolError("provider calls must be FORBIDDEN")
    if tuple(item["fixed_pipeline"]) != FIXED_PIPELINE:
        raise WeldProtocolError("protocol pipeline differs from the fixed WELD-v3 pipeline")
    if set(item["allowed_decisions"]) != ALLOWED_DECISIONS:
        raise WeldProtocolError("protocol decision enum differs from WELD v3")
    if item["python_decision_policy"] != "EXACT_ENUM_EQUALITY_ONLY":
        raise WeldProtocolError("Python decision policy must use enum equality only")
    if item["pair_policy"] != "TARGET_AND_CONTROL_AND_INFORMATION_MATCH_MUST_ALL_PASS":
        raise WeldProtocolError("pair policy is not the verdict-bearing matched-control policy")
    if item["overall_policy"] != "ALL_PAIRS_MUST_PASS":
        raise WeldProtocolError("overall policy must require every pair")
    if item["runtime_profile_required_for_real_run"] != "PRODUCTION_RUST":
        raise WeldProtocolError("real runs must require PRODUCTION_RUST")
    if item["truth_phase_policy"] != (
        "HMAC_COMMITMENT_ONLY_DURING_ACTOR_EXTERNAL_ACTOR_SEAL_BEFORE_KEY_AND_"
        "PLAINTEXT_RELEASE"
    ):
        raise WeldProtocolError("truth phase policy changed")
    if item["actor_receipt_policy"] != (
        "ONE_SUCCESSFUL_INVOCATION_PER_CASE_EXTERNALLY_SEALED_BEFORE_TRUTH_RELEASE"
    ):
        raise WeldProtocolError("actor receipt policy changed")
    if item["case_cwd_policy"] != "FRESH_EMPTY_UNIQUE_CWD_PER_CASE":
        raise WeldProtocolError("case working-directory policy changed")
    if item["production_adjudication_status"] != (
        "BLOCKED_PENDING_TRUSTED_EXTERNAL_ANCHOR_VERIFIER"
    ):
        raise WeldProtocolError("production adjudication must remain blocked in this revision")
    if item["model_adapter_status"] != MODEL_ADAPTER_STATUS:
        raise WeldProtocolError("J1, J2, and Stage 5 must remain NOT_RUN")
    return item


def validate_public_cases(document: Any) -> list[Mapping[str, Any]]:
    root = require_mapping(document, "public cases")
    require_exact_keys(root, {"schema_version", "cases"}, "public cases")
    if root["schema_version"] != PUBLIC_CASES_SCHEMA:
        raise WeldProtocolError("unsupported public-cases schema")
    cases = root["cases"]
    if not isinstance(cases, list) or not cases:
        raise WeldProtocolError("public cases must contain a non-empty cases array")

    seen: set[str] = set()
    validated: list[Mapping[str, Any]] = []
    keys = {
        "schema_version",
        "case_id",
        "carrier_kind",
        "carrier",
        "information_profile",
        "model_adapter_status",
    }
    for index, raw in enumerate(cases):
        case = require_mapping(raw, f"public cases[{index}]")
        require_exact_keys(case, keys, f"public cases[{index}]")
        if case["schema_version"] != PUBLIC_CASE_SCHEMA:
            raise WeldProtocolError(f"public cases[{index}] has unsupported schema")
        case_id = case["case_id"]
        if not isinstance(case_id, str) or not _CASE_ID.fullmatch(case_id):
            raise WeldProtocolError(f"public cases[{index}].case_id must be opaque 32-hex")
        if case_id in seen:
            raise WeldProtocolError(f"duplicate public case_id {case_id}")
        seen.add(case_id)
        require_nonempty_string(case["carrier_kind"], f"public cases[{index}].carrier_kind")
        if not isinstance(case["carrier"], dict) or not case["carrier"]:
            raise WeldProtocolError(f"public cases[{index}].carrier must be a non-empty object")
        if not isinstance(case["information_profile"], dict) or not case["information_profile"]:
            raise WeldProtocolError(
                f"public cases[{index}].information_profile must be a non-empty object"
            )
        if case["model_adapter_status"] != MODEL_ADAPTER_STATUS:
            raise WeldProtocolError(f"public cases[{index}] must mark J1/J2/Stage5 NOT_RUN")
        _reject_public_truth_keys(case, f"public cases[{index}]")
        canonical_json_bytes(case)
        validated.append(case)
    return validated


def validate_actor_output(output: Any, case: Mapping[str, Any]) -> Mapping[str, Any]:
    item = require_mapping(output, f"actor output for {case['case_id']}")
    keys = {
        "schema_version",
        "case_id",
        "input_sha256",
        "pipeline_id",
        "pipeline_trace",
        "decision",
        "diagnosis_code",
        "localization_ref",
        "repair_ref",
        "verification_code",
        "model_adapter_status",
    }
    require_exact_keys(item, keys, f"actor output for {case['case_id']}")
    if item["schema_version"] != ACTOR_OUTPUT_SCHEMA:
        raise WeldProtocolError("actor output schema changed")
    if item["case_id"] != case["case_id"]:
        raise WeldProtocolError("actor output case_id does not match input")
    expected_input_hash = sha256_bytes(canonical_json_bytes(case))
    if item["input_sha256"] != expected_input_hash:
        raise WeldProtocolError("actor output input_sha256 does not match canonical input")
    if item["pipeline_id"] != "WELD-V3-FIXED-PIPELINE-1":
        raise WeldProtocolError("actor used an unregistered pipeline_id")
    if tuple(item["pipeline_trace"]) != FIXED_PIPELINE:
        raise WeldProtocolError("actor output does not contain the exact fixed pipeline trace")
    if item["decision"] not in ALLOWED_DECISIONS:
        raise WeldProtocolError("actor emitted a decision outside the closed enum")
    for field in ("diagnosis_code", "verification_code"):
        require_nonempty_string(item[field], f"actor output.{field}")
    for field in ("localization_ref", "repair_ref"):
        if item[field] is not None and not isinstance(item[field], str):
            raise WeldProtocolError(f"actor output.{field} must be a string or null")
    if item["model_adapter_status"] != MODEL_ADAPTER_STATUS:
        raise WeldProtocolError("actor may not claim J1, J2, or Stage 5 ran")
    canonical_json_bytes(item)
    return item


def _information_shape(value: Any) -> Any:
    """Describe public information exposure for matched-control comparison.

    String contents remain opaque, but byte/code-point and deterministic lexical
    token lengths are matched. Numeric and boolean values are public information
    and therefore must match exactly rather than only by primitive type.
    """
    if isinstance(value, dict):
        return {
            "type": "object",
            "fields": {key: _information_shape(value[key]) for key in sorted(value)},
        }
    if isinstance(value, list):
        return {
            "type": "array",
            "length": len(value),
            "items": [_information_shape(child) for child in value],
        }
    if isinstance(value, str):
        tokens = _LEXICAL_TOKEN.findall(value)
        return {
            "type": "string",
            "utf8_bytes": len(value.encode("utf-8")),
            "unicode_codepoints": len(value),
            "lexical_token_count": len(tokens),
            "lexical_token_utf8_bytes": [len(token.encode("utf-8")) for token in tokens],
        }
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean", "value": value}
    if isinstance(value, int):
        return {"type": "integer", "value": value}
    if isinstance(value, float):
        return {
            "type": "number",
            "canonical_value": canonical_json_bytes(value).decode("utf-8").strip(),
        }
    raise WeldProtocolError("public carrier contains a value outside the JSON type system")


def information_profile_hash(case: Mapping[str, Any]) -> str:
    mechanically_observed = {
        "carrier_kind": case["carrier_kind"],
        "carrier_shape": _information_shape(case["carrier"]),
        "declared_information_profile": case["information_profile"],
        "model_adapter_status": case["model_adapter_status"],
    }
    return sha256_bytes(canonical_json_bytes(mechanically_observed))


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
