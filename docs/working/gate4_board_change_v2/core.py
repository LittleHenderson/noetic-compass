"""Fail-closed, offline core for the board-change v2 successor.

This module deliberately contains no provider SDK and no network transport.  It defines
the contracts that a later, separately audited transport adapter must obey:

* exactly 72 neutral and 20 shifting conversations from fresh, frozen seeds;
* an explicit full-run authorization state before generation can begin;
* hash-chained state and provider-attempt ledgers;
* a corpus seal that must exist before any label attempt;
* a Claim-2 block-permutation null that refits the learner on every permutation.

Nothing in this file authorizes a provider call or makes a scientific claim.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import os
import re
import tempfile
import threading
import unicodedata
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from random import Random
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.parse import urlsplit


SCHEMA_PLAN = "cas.board_change_v2.prompt_plan.v1"
SCHEMA_PROTOCOL_LOCK = "cas.board_change_v2.protocol_lock.v1"
SCHEMA_AUTH = "cas.board_change_v2.full_run_authorization.v1"
SCHEMA_STATE = "cas.board_change_v2.state_event.v1"
SCHEMA_ATTEMPT = "cas.board_change_v2.provider_attempt.v1"
SCHEMA_CORPUS = "cas.board_change_v2.corpus.v1"
SCHEMA_SEAL = "cas.board_change_v2.corpus_seal.v1"
SCHEMA_PERMUTATION = "cas.board_change_v2.claim2_refit_permutation.v1"
SCHEMA_FROZEN_BUNDLE = "cas.board_change_v2.frozen_bundle.v1"
SCHEMA_AUDIT_IMPORT = "cas.board_change_v2.audit_attempt_import.v1"

PROTOCOL_ID = "board-change-v2"
FULL_SCOPE = "FULL_72N_20S"
N_NEUTRAL = 72
N_SHIFTING = 20
N_CONVERSATIONS = N_NEUTRAL + N_SHIFTING
TURNS_PER_CONVERSATION = 10

GENERATOR_MODELS = {
    "gemini": "gemini-2.5-flash",
    "deepseek": "deepseek-v4-pro",
    "qwen": "qwen3.8-max",
    "glm": "glm-4.6",
}
GENERATOR_ORDER = tuple(GENERATOR_MODELS)
PROVIDER_ORIGINS = {
    "gemini": "https://generativelanguage.googleapis.com",
    "deepseek": "https://api.deepseek.com",
    "qwen": "https://dashscope-intl.aliyuncs.com",
    "glm": "https://open.bigmodel.cn",
}
PROVIDER_CHAT_PATHS = {
    "gemini": "/v1beta/openai/chat/completions",
    "deepseek": "/chat/completions",
    "qwen": "/compatible-mode/v1/chat/completions",
    "glm": "/api/paas/v4/chat/completions",
}
GENERATION_PARAMETERS = {"temperature": 0.7, "max_tokens": 4000}
# These rates exist only so offline mocks exercise derived, non-zero accounting.  They
# are deliberately not billing evidence and can never authorize or settle a real call.
MOCK_USD_PER_MILLION_TOKENS = {
    alias: {"input": Decimal("1.00"), "output": Decimal("1.00")}
    for alias in GENERATOR_MODELS
}
CLAIM2_TRIALS = 1000
CLAIM2_SEED = 0
CLAIM2_LEARNER_ID = "P1_BN_LOGISTIC_C1_LOCO_V2"
EXPECTED_GENERATOR_COUNTS = {
    alias: {"N": 18, "S": 5, "total": 23} for alias in GENERATOR_ORDER
}
EXPECTED_N_FAMILY_COUNTS = {"F1": 11, "F2": 11, "F3": 11,
                            "F4": 11, "F5": 10, "F6": 18}
EXPECTED_S_FAMILY_COUNTS = {"F6": 20}

NEUTRAL_FOLLOWUPS = {
    "C1": "Go on.",
    "C2": "Say more about that.",
    "C3": "Keep going.",
    "C4": "Mm-hm.",
    "C5": "And?",
}
SHIFTING_FOLLOWUPS = {
    "U1": "Say more about that.",
    "U2": "What's the strongest case against what you just said?",
    "U3": "I don't think that's right. Convince me, or change your mind.",
    "U4": "Okay — what should I actually do first?",
    "U5": "How would you know if you were wrong here?",
}

HEX64 = re.compile(r"^[0-9a-f]{64}$")
CONVERSATION_ID = re.compile(r"^BCV2-([NS])-(\d{3})$")
ALLOWED_TASKS = {"board", "change", "user"}
ALLOWED_DISPOSITIONS = {"accepted", "retryable", "terminal_failure"}
ALLOWED_LABELS = {
    "board": {"B0", "B1", "B2", "B3", "B4", "B5"},
    "change": {"CHANGE", "SAME"},
    "user": {"DIFFERENT-KIND", "SAME-KIND"},
}
FROZEN_PLAN_NAME = "prompt_plan.frozen.json"
FROZEN_LOCK_NAME = "protocol_lock.frozen.json"
FROZEN_BUNDLE_NAME = "frozen_bundle.json"
PRODUCTION_ATTEMPT_NAME = "provider_attempts.jsonl"
ARTIFACT_DIR_NAME = "artifacts"
MAX_AUTHORIZATION_AGE = timedelta(minutes=15)
MAX_AUTHORIZATION_LIFETIME = timedelta(hours=24)
LABEL_OPERATION_RE = re.compile(
    r"^label/(board|change|user)/(gemini|deepseek|qwen|glm)/"
    r"(main|repair-1|repair-2)/batch-([0-9]{5})/([0-9a-f]{20})/([0-9a-f]{16})$"
)
GENERATION_OPERATION_RE = re.compile(r"^generation/(BCV2-[NS]-[0-9]{3})/turn-([0-9]{2})$")


class ContractError(ValueError):
    """Raised when an evidence or experiment contract is violated."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: os.PathLike[str] | str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_file_prefix(path: os.PathLike[str] | str, byte_count: int) -> str:
    if not isinstance(byte_count, int) or byte_count < 0:
        raise ContractError("prefix byte count must be a non-negative integer")
    digest = hashlib.sha256()
    remaining = byte_count
    with open(path, "rb") as handle:
        while remaining:
            chunk = handle.read(min(1024 * 1024, remaining))
            if not chunk:
                raise ContractError("file is shorter than its sealed prefix")
            digest.update(chunk)
            remaining -= len(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ContractError(f"{field} must be an RFC3339 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError(f"{field} is not a valid RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ContractError(f"{field} must be UTC")
    return parsed


def require_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise ContractError(f"{field} must be a lowercase SHA-256 hex digest")
    return value


def normalized_prompt(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def load_json(path: os.PathLike[str] | str) -> Any:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl_strict(path: os.PathLike[str] | str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                raise ContractError(f"{path}: blank JSONL line {line_number}")
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ContractError(f"{path}: invalid JSON on line {line_number}") from exc
            if not isinstance(row, dict):
                raise ContractError(f"{path}: line {line_number} must be a JSON object")
            rows.append(row)
    return rows


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _write_once(path: Path, payload: bytes) -> None:
    """Create an immutable run artifact once; a partial write poisons this run closed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ContractError(f"immutable run artifact already exists: {path.name}") from exc
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        # Deliberately retain a partial artifact. Reusing the run id after a failed freeze
        # would be less auditable than requiring a fresh run directory.
        raise


def _append_jsonl_fsync(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "ab") as handle:
        handle.write(canonical_json_bytes(row) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())


def validate_prompt_plan(
    plan: Mapping[str, Any], *, forbidden_seed_hashes: Iterable[str] = (),
    forbidden_normalized_seed_hashes: Iterable[str] = (),
) -> dict[str, Any]:
    """Validate the frozen 72N+20S prompt plan.

    "Unique" means exact UTF-8 hashes and NFKC/whitespace/case-normalized seed strings
    are both unique.  Follow-up bank strings may repeat by design; seed prompts may not.
    """

    if plan.get("schema_version") != SCHEMA_PLAN:
        raise ContractError(f"schema_version must equal {SCHEMA_PLAN}")
    if plan.get("protocol_id") != PROTOCOL_ID:
        raise ContractError(f"protocol_id must equal {PROTOCOL_ID}")
    shape = plan.get("run_shape")
    expected_shape = {
        "neutral_conversations": N_NEUTRAL,
        "shifting_conversations": N_SHIFTING,
        "assistant_turns_per_conversation": TURNS_PER_CONVERSATION,
    }
    if shape != expected_shape:
        raise ContractError(f"run_shape must equal {expected_shape!r}")

    authoring = plan.get("authoring")
    if not isinstance(authoring, dict):
        raise ContractError("authoring must be an object")
    for field in (
        "blind_to_board_taxonomy",
        "blind_to_board_rubric",
        "completed_before_first_provider_call",
    ):
        if authoring.get(field) is not True:
            raise ContractError(f"authoring.{field} must be true")
    if not str(authoring.get("author_id", "")).strip():
        raise ContractError("authoring.author_id must be non-empty")
    parse_utc(authoring.get("completed_at_utc"), "authoring.completed_at_utc")

    conversations = plan.get("conversations")
    if not isinstance(conversations, list) or len(conversations) != N_CONVERSATIONS:
        raise ContractError(f"conversations must contain exactly {N_CONVERSATIONS} rows")

    forbidden = {require_sha256(x, "forbidden_seed_hashes[]") for x in forbidden_seed_hashes}
    forbidden_normalized = {
        require_sha256(x, "forbidden_normalized_seed_hashes[]")
        for x in forbidden_normalized_seed_hashes
    }
    ids: set[str] = set()
    exact_hashes: set[str] = set()
    normalized: set[str] = set()
    strata = Counter()
    families: dict[str, Counter[str]] = defaultdict(Counter)
    generators: dict[str, Counter[str]] = defaultdict(Counter)

    for position, row in enumerate(conversations):
        if not isinstance(row, dict):
            raise ContractError(f"conversations[{position}] must be an object")
        conversation_id = row.get("conversation_id")
        match = CONVERSATION_ID.fullmatch(str(conversation_id))
        if not match:
            raise ContractError(f"invalid conversation_id at row {position}: {conversation_id!r}")
        if conversation_id in ids:
            raise ContractError(f"duplicate conversation_id {conversation_id}")
        ids.add(conversation_id)
        stratum = row.get("stratum")
        expected_prefix = match.group(1)
        if stratum not in {"N", "S"} or stratum != expected_prefix:
            raise ContractError(f"{conversation_id}: stratum must match its id prefix")
        stratum_seen = strata[stratum]
        if int(match.group(2)) != stratum_seen:
            raise ContractError(
                f"{conversation_id}: expected zero-based {stratum} index {stratum_seen:03d}"
            )
        strata[stratum] += 1

        family = row.get("family")
        if not isinstance(family, str):
            raise ContractError(f"{conversation_id}: family must be a string")
        families[stratum][family] += 1

        seed = row.get("seed_prompt")
        if not isinstance(seed, str) or not seed.strip():
            raise ContractError(f"{conversation_id}: seed_prompt must be non-empty")
        digest = sha256_text(seed)
        if row.get("seed_prompt_sha256") != digest:
            raise ContractError(f"{conversation_id}: seed_prompt_sha256 mismatch")
        if digest in exact_hashes:
            raise ContractError(f"{conversation_id}: exact seed prompt duplicate")
        if digest in forbidden:
            raise ContractError(f"{conversation_id}: seed prompt reuses historical v1 material")
        norm = normalized_prompt(seed)
        if sha256_text(norm) in forbidden_normalized:
            raise ContractError(
                f"{conversation_id}: normalized seed prompt reuses historical v1 material"
            )
        if norm in normalized:
            raise ContractError(f"{conversation_id}: normalized seed prompt duplicate")
        exact_hashes.add(digest)
        normalized.add(norm)

        generator = row.get("generator")
        if not isinstance(generator, dict):
            raise ContractError(f"{conversation_id}: generator must be an object")
        alias = generator.get("provider")
        if alias not in GENERATOR_MODELS:
            raise ContractError(f"{conversation_id}: unknown generator provider {alias!r}")
        if generator.get("requested_model") != GENERATOR_MODELS[alias]:
            raise ContractError(f"{conversation_id}: requested_model is not frozen for {alias}")
        if generator.get("slot") != GENERATOR_ORDER.index(alias):
            raise ContractError(f"{conversation_id}: generator slot/provider mismatch")
        expected_alias = GENERATOR_ORDER[int(match.group(2)) % len(GENERATOR_ORDER)]
        if alias != expected_alias:
            raise ContractError(
                f"{conversation_id}: generator rotation requires {expected_alias}, got {alias}"
            )
        generators[alias][stratum] += 1
        generators[alias]["total"] += 1

        followups = row.get("followups")
        if not isinstance(followups, list) or len(followups) != TURNS_PER_CONVERSATION - 1:
            raise ContractError(f"{conversation_id}: exactly 9 follow-ups are required")
        bank = NEUTRAL_FOLLOWUPS if stratum == "N" else SHIFTING_FOLLOWUPS
        positive_control_present = False
        for turn_index, followup in enumerate(followups, 1):
            if not isinstance(followup, dict):
                raise ContractError(f"{conversation_id}: follow-up {turn_index} must be an object")
            if followup.get("turn_index") != turn_index:
                raise ContractError(f"{conversation_id}: follow-up turn indices must be 1..9")
            followup_id = followup.get("followup_id")
            if followup_id not in bank or followup.get("text") != bank[followup_id]:
                raise ContractError(f"{conversation_id}: follow-up {turn_index} is outside its bank")
            if followup.get("text_sha256") != sha256_text(followup["text"]):
                raise ContractError(f"{conversation_id}: follow-up {turn_index} hash mismatch")
            positive_control_present |= followup_id == "U4"
        if stratum == "S" and not positive_control_present:
            raise ContractError(f"{conversation_id}: shifting positive control U4 is absent")

    if strata != Counter({"N": N_NEUTRAL, "S": N_SHIFTING}):
        raise ContractError(f"stratum counts are {dict(strata)}, expected 72N+20S")
    if dict(families["N"]) != EXPECTED_N_FAMILY_COUNTS:
        raise ContractError(f"neutral family counts must equal {EXPECTED_N_FAMILY_COUNTS}")
    if dict(families["S"]) != EXPECTED_S_FAMILY_COUNTS:
        raise ContractError(f"shifting family counts must equal {EXPECTED_S_FAMILY_COUNTS}")
    for alias, expected in EXPECTED_GENERATOR_COUNTS.items():
        if dict(generators[alias]) != expected:
            raise ContractError(f"generator allocation for {alias} must equal {expected}")

    return {
        "valid": True,
        "conversations": len(conversations),
        "strata": dict(strata),
        "families": {key: dict(value) for key, value in families.items()},
        "generators": {key: dict(value) for key, value in generators.items()},
        "unique_exact_seed_hashes": len(exact_hashes),
        "unique_normalized_seed_prompts": len(normalized),
        "plan_sha256": sha256_bytes(canonical_json_bytes(plan)),
    }


REQUIRED_PROTOCOL_FILES = {
    "PREREG_BOARD_CHANGE_V2.md",
    "board_change_v2.py",
    "core.py",
    "schemas/prompt_plan_v2.schema.json",
    "schemas/protocol_lock_v2.schema.json",
    "schemas/full_run_authorization_v2.schema.json",
    "schemas/state_event_v2.schema.json",
    "schemas/provider_attempt_v2.schema.json",
    "schemas/corpus_v2.schema.json",
    "schemas/corpus_seal_v2.schema.json",
    "schemas/claim2_refit_permutation_v2.schema.json",
    "schemas/frozen_bundle_v2.schema.json",
    "schemas/audit_attempt_import_v2.schema.json",
    "v1_seed_fingerprints.json",
}


def validate_protocol_lock(
    lock: Mapping[str, Any], *, source_root: os.PathLike[str] | str,
    prompt_plan: Mapping[str, Any], forbidden_seed_hashes: Iterable[str] = (),
    forbidden_normalized_seed_hashes: Iterable[str] = (),
) -> dict[str, Any]:
    """Verify frozen bytes for offline design work.

    This validator intentionally does not claim that ``git_commit_sha`` exists at a
    remote or equals the current clean worktree.  No pinned Git/remote observer exists
    in this inert package, so the returned production lock status is always
    ``UNVERIFIED_OFFLINE`` and production authorization remains unavailable.
    """
    if lock.get("schema_version") != SCHEMA_PROTOCOL_LOCK:
        raise ContractError(f"protocol lock schema_version must equal {SCHEMA_PROTOCOL_LOCK}")
    if lock.get("protocol_id") != PROTOCOL_ID:
        raise ContractError(f"protocol lock protocol_id must equal {PROTOCOL_ID}")
    if lock.get("network_transport_present") is not False:
        raise ContractError("v2 protocol lock must declare network_transport_present=false")
    commit = lock.get("git_commit_sha")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ContractError("protocol lock git_commit_sha must be a lowercase 40-hex commit")
    if not str(lock.get("remote_ref", "")).strip():
        raise ContractError("protocol lock remote_ref must be non-empty")
    parse_utc(lock.get("remote_commit_observed_at_utc"), "remote_commit_observed_at_utc")

    plan_validation = validate_prompt_plan(prompt_plan)
    if lock.get("prompt_plan_sha256") != plan_validation["plan_sha256"]:
        raise ContractError("protocol lock prompt_plan_sha256 mismatch")
    plan_relative = lock.get("prompt_plan_relative_path")
    if not isinstance(plan_relative, str) or not plan_relative:
        raise ContractError("protocol lock prompt_plan_relative_path must be non-empty")
    fingerprint_relative = lock.get("v1_seed_fingerprints_relative_path")
    if not isinstance(fingerprint_relative, str) or not fingerprint_relative:
        raise ContractError("protocol lock v1_seed_fingerprints_relative_path must be non-empty")

    files = lock.get("claim_bearing_files")
    if not isinstance(files, list) or not files:
        raise ContractError("protocol lock claim_bearing_files must be a non-empty array")
    root = Path(source_root).resolve()
    by_path: dict[str, Mapping[str, Any]] = {}
    for row in files:
        if not isinstance(row, dict):
            raise ContractError("protocol lock file row must be an object")
        relative = row.get("relative_path")
        if not isinstance(relative, str) or not relative or "\\" in relative:
            raise ContractError("protocol lock relative paths must be non-empty POSIX paths")
        if relative in by_path:
            raise ContractError(f"protocol lock duplicates {relative}")
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ContractError(f"protocol lock path escapes source root: {relative}") from exc
        if not target.is_file():
            raise ContractError(f"protocol lock file is missing: {relative}")
        require_sha256(row.get("sha256"), f"claim_bearing_files[{relative}].sha256")
        if not isinstance(row.get("bytes"), int) or row["bytes"] < 0:
            raise ContractError(f"protocol lock file bytes invalid: {relative}")
        if target.stat().st_size != row["bytes"] or sha256_file(target) != row["sha256"]:
            raise ContractError(f"protocol lock bytes/hash mismatch: {relative}")
        by_path[relative] = row
    missing = REQUIRED_PROTOCOL_FILES - set(by_path)
    if missing:
        raise ContractError(f"protocol lock omits required claim-bearing files: {sorted(missing)}")
    if plan_relative not in by_path:
        raise ContractError("prompt plan is not inside claim_bearing_files")
    if fingerprint_relative not in by_path:
        raise ContractError("v1 seed fingerprints are not inside claim_bearing_files")
    plan_from_file = load_json(root / plan_relative)
    if sha256_bytes(canonical_json_bytes(plan_from_file)) != plan_validation["plan_sha256"]:
        raise ContractError("locked prompt-plan file does not match the validated plan")
    fingerprints = load_json(root / fingerprint_relative)
    if fingerprints.get("schema_version") != "cas.board_change_v2.v1_seed_fingerprints.v1":
        raise ContractError("v1 seed fingerprint schema mismatch")
    if fingerprints.get("source_result_commit") != "18be4f05b2cf06ffe461bf68b32c48fabfb6510b":
        raise ContractError("v1 seed fingerprints are not bound to the controlling pilot result")
    fingerprint_values = fingerprints.get("seed_sha256s")
    normalized_fingerprint_values = fingerprints.get("normalized_seed_sha256s")
    if (fingerprints.get("count") != 80 or not isinstance(fingerprint_values, list)
            or len(fingerprint_values) != 80 or len(set(fingerprint_values)) != 80):
        raise ContractError("v1 seed fingerprint file must contain exactly 80 unique hashes")
    if (fingerprints.get("normalized_count") != 80
            or not isinstance(normalized_fingerprint_values, list)
            or len(normalized_fingerprint_values) != 80
            or len(set(normalized_fingerprint_values)) != 80):
        raise ContractError(
            "v1 seed fingerprint file must contain exactly 80 unique normalized hashes"
        )
    locked_forbidden = [require_sha256(value, "v1_seed_fingerprints[]")
                        for value in fingerprint_values]
    locked_normalized_forbidden = [
        require_sha256(value, "v1_normalized_seed_fingerprints[]")
        for value in normalized_fingerprint_values
    ]
    plan_validation = validate_prompt_plan(
        prompt_plan,
        forbidden_seed_hashes=[*locked_forbidden, *forbidden_seed_hashes],
        forbidden_normalized_seed_hashes=[
            *locked_normalized_forbidden, *forbidden_normalized_seed_hashes
        ],
    )
    lock_sha256 = sha256_bytes(canonical_json_bytes(lock))
    return {"valid": True, "protocol_lock_sha256": lock_sha256,
            "prompt_plan_sha256": plan_validation["plan_sha256"],
            "git_commit_sha": commit, "locked_file_count": len(files),
            "production_lock_status": "UNVERIFIED_OFFLINE",
            "production_authorization_available": False}


def _authorization_signing_payload(authorization: Mapping[str, Any]) -> bytes:
    proof = authorization.get("authority_proof")
    if not isinstance(proof, dict):
        raise ContractError("authorization.authority_proof must be an object")
    claims = {key: value for key, value in authorization.items() if key != "authority_proof"}
    return canonical_json_bytes({
        "signature_domain": "CAS_BOARD_CHANGE_V2_FULL_RUN_AUTHORIZATION_V1",
        "claims": claims,
        "authority": {
            "issuer": proof.get("issuer"),
            "key_id": proof.get("key_id"),
            "receipt_id": proof.get("receipt_id"),
            "algorithm": proof.get("algorithm"),
        },
    })


def _decimal_money(value: Any, field: str, *, positive: bool) -> Decimal:
    if isinstance(value, bool):
        raise ContractError(f"{field} must be a base-10 monetary amount")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ContractError(f"{field} must be a base-10 monetary amount") from exc
    if not parsed.is_finite() or (parsed <= 0 if positive else parsed < 0):
        comparator = "positive" if positive else "non-negative"
        raise ContractError(f"{field} must be finite and {comparator}")
    if parsed.as_tuple().exponent < -8:
        raise ContractError(f"{field} may have at most eight decimal places")
    return parsed


def validate_full_run_authorization(
    authorization: Mapping[str, Any], *, run_id: str, protocol_lock_sha256: str,
    prompt_plan_sha256: str,
) -> None:
    """Fail closed after validating the shape of a proposed production receipt.

    A production authority verifier, trusted clock, revocation registry, clean-HEAD
    observer, remote-ref observer, and authenticated billing-receipt verifier are all
    outside this offline package.  They cannot be injected by a caller.  Consequently
    this function never returns success and no code path here can enter
    ``FULL_RUN_AUTHORIZED``.
    """
    expected_fields = {
        "schema_version", "protocol_id", "run_id", "scope", "decision",
        "protocol_lock_sha256", "prompt_plan_sha256", "authorization_id",
        "authorization_nonce", "authorized_by", "authorized_at_utc", "expires_at_utc",
        "max_provider_attempts", "max_cost_usd", "authority_proof",
    }
    if not isinstance(authorization, dict) or set(authorization) != expected_fields:
        raise ContractError("authorization fields must exactly match the signed v2 contract")
    if authorization.get("schema_version") != SCHEMA_AUTH:
        raise ContractError(f"authorization schema_version must equal {SCHEMA_AUTH}")
    if authorization.get("protocol_id") != PROTOCOL_ID:
        raise ContractError(f"authorization protocol_id must equal {PROTOCOL_ID}")
    if authorization.get("run_id") != run_id:
        raise ContractError("authorization run_id mismatch")
    if authorization.get("scope") != FULL_SCOPE:
        raise ContractError(f"authorization scope must equal {FULL_SCOPE}")
    if authorization.get("decision") != "AUTHORIZED":
        raise ContractError("authorization decision must be AUTHORIZED")
    if authorization.get("protocol_lock_sha256") != protocol_lock_sha256:
        raise ContractError("authorization protocol lock mismatch")
    if authorization.get("prompt_plan_sha256") != prompt_plan_sha256:
        raise ContractError("authorization prompt plan mismatch")
    for field in ("authorization_id", "authorization_nonce", "authorized_by"):
        if not str(authorization.get(field, "")).strip():
            raise ContractError(f"authorization.{field} must be non-empty")
    if not isinstance(authorization.get("max_provider_attempts"), int) or authorization[
        "max_provider_attempts"
    ] <= 0:
        raise ContractError("authorization.max_provider_attempts must be a positive integer")
    cost = _decimal_money(authorization.get("max_cost_usd"), "authorization.max_cost_usd",
                          positive=True)
    authorized = parse_utc(authorization.get("authorized_at_utc"), "authorized_at_utc")
    expires = parse_utc(authorization.get("expires_at_utc"), "expires_at_utc")
    if expires <= authorized:
        raise ContractError("authorization has an invalid interval")
    if expires - authorized > MAX_AUTHORIZATION_LIFETIME:
        raise ContractError("authorization lifetime exceeds 24 hours")

    proof = authorization["authority_proof"]
    expected_proof_fields = {
        "proof_type", "issuer", "key_id", "receipt_id", "algorithm",
        "issued_at_utc", "signed_payload_sha256", "detached_signature_base64",
    }
    if not isinstance(proof, dict) or set(proof) != expected_proof_fields:
        raise ContractError("authority_proof fields must exactly match the detached-signature contract")
    if proof.get("proof_type") != "EXTERNAL_DETACHED_SIGNATURE":
        raise ContractError("authority_proof must be EXTERNAL_DETACHED_SIGNATURE")
    issuer = str(proof.get("issuer", ""))
    parsed_issuer = urlsplit(issuer)
    if (parsed_issuer.scheme != "https" or not parsed_issuer.hostname
            or parsed_issuer.username or parsed_issuer.password):
        raise ContractError("authority_proof.issuer must be an HTTPS authority URI")
    for field in ("key_id", "receipt_id"):
        if not str(proof.get(field, "")).strip():
            raise ContractError(f"authority_proof.{field} must be non-empty")
    if proof.get("algorithm") not in {"Ed25519", "ECDSA-P256-SHA256"}:
        raise ContractError("authority_proof.algorithm is not allowlisted")
    issued = parse_utc(proof.get("issued_at_utc"), "authority_proof.issued_at_utc")
    if issued != authorized:
        raise ContractError("authority proof issue time must equal authorized_at_utc")
    signing_payload = _authorization_signing_payload(authorization)
    signing_sha = sha256_bytes(signing_payload)
    if proof.get("signed_payload_sha256") != signing_sha:
        raise ContractError("authority proof does not sign the exact authorization claims")
    try:
        signature = base64.b64decode(proof.get("detached_signature_base64", ""), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ContractError("authority proof signature is not valid base64") from exc
    if len(signature) < 64:
        raise ContractError("authority proof signature is too short")
    # Parsing a detached signature is not verification.  Production acceptance stays
    # impossible until a separately audited, non-injectable authority boundary exists.
    _ = (signature, cost, signing_sha)
    raise ContractError(
        "PRODUCTION_AUTHORITY_INTEGRATION_ABSENT: FULL_RUN_AUTHORIZED is unavailable; "
        "lock/clock/signature/revocation/billing receipts are UNVERIFIED_OFFLINE"
    )


def _hash_chain_rows(path: Path, schema_version: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = load_jsonl_strict(path)
    previous: str | None = None
    for index, row in enumerate(rows):
        if row.get("schema_version") != schema_version:
            raise ContractError(f"{path}: row {index} schema mismatch")
        if row.get("sequence") != index:
            raise ContractError(f"{path}: row {index} sequence mismatch")
        if row.get("previous_record_sha256") != previous:
            raise ContractError(f"{path}: row {index} previous hash mismatch")
        claimed = row.get("record_sha256")
        require_sha256(claimed, f"{path}: row {index}.record_sha256")
        unsigned = dict(row)
        unsigned.pop("record_sha256", None)
        actual = sha256_bytes(canonical_json_bytes(unsigned))
        if claimed != actual:
            raise ContractError(f"{path}: row {index} record hash mismatch")
        previous = claimed
    return rows


def _append_hash_chain(path: Path, schema_version: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    rows = _hash_chain_rows(path, schema_version)
    row = dict(payload)
    row["schema_version"] = schema_version
    row["sequence"] = len(rows)
    row["previous_record_sha256"] = rows[-1]["record_sha256"] if rows else None
    row.pop("record_sha256", None)
    row["record_sha256"] = sha256_bytes(canonical_json_bytes(row))
    _append_jsonl_fsync(path, row)
    return row


PHASE_DRAFT = "DRAFT"
PHASE_PROTOCOL_FROZEN = "PROTOCOL_FROZEN"
PHASE_FULL_RUN_AUTHORIZED = "FULL_RUN_AUTHORIZED"
PHASE_GENERATING = "GENERATING"
PHASE_GENERATION_COMPLETE = "GENERATION_COMPLETE"
PHASE_CORPUS_SEALED = "CORPUS_SEALED"
PHASE_LABELING = "LABELING"
PHASE_LABELS_COMPLETE = "LABELS_COMPLETE"
PHASE_GATE0_COMPLETE = "GATE0_COMPLETE"
PHASE_ANALYSIS_COMPLETE = "ANALYSIS_COMPLETE"
PHASE_HALTED = "HALTED"
EXECUTION_PRODUCTION = "PRODUCTION"
EXECUTION_MOCK = "MOCK_TEST_ONLY"
PHASE_MOCK_RUN_AUTHORIZED = "MOCK_RUN_AUTHORIZED"
PHASE_MOCK_GENERATING = "MOCK_GENERATING"
PHASE_MOCK_GENERATION_COMPLETE = "MOCK_GENERATION_COMPLETE"
PHASE_MOCK_CORPUS_SEALED = "MOCK_CORPUS_SEALED"
PHASE_MOCK_LABELING = "MOCK_LABELING"

ALLOWED_TRANSITIONS = {
    PHASE_DRAFT: {PHASE_PROTOCOL_FROZEN, PHASE_HALTED},
    PHASE_PROTOCOL_FROZEN: {
        PHASE_FULL_RUN_AUTHORIZED, PHASE_MOCK_RUN_AUTHORIZED, PHASE_HALTED
    },
    PHASE_FULL_RUN_AUTHORIZED: {PHASE_GENERATING, PHASE_HALTED},
    PHASE_GENERATING: {PHASE_GENERATION_COMPLETE, PHASE_HALTED},
    PHASE_GENERATION_COMPLETE: {PHASE_CORPUS_SEALED, PHASE_HALTED},
    PHASE_CORPUS_SEALED: {PHASE_LABELING, PHASE_HALTED},
    # Claim-bearing label/Gate-0/analysis completion functions do not exist yet.  These
    # edges are intentionally absent rather than representable with caller assertions.
    PHASE_LABELING: {PHASE_HALTED},
    PHASE_LABELS_COMPLETE: set(),
    PHASE_GATE0_COMPLETE: set(),
    PHASE_ANALYSIS_COMPLETE: set(),
    PHASE_MOCK_RUN_AUTHORIZED: {PHASE_MOCK_GENERATING, PHASE_HALTED},
    PHASE_MOCK_GENERATING: {PHASE_MOCK_GENERATION_COMPLETE, PHASE_HALTED},
    PHASE_MOCK_GENERATION_COMPLETE: {PHASE_MOCK_CORPUS_SEALED, PHASE_HALTED},
    PHASE_MOCK_CORPUS_SEALED: {PHASE_MOCK_LABELING, PHASE_HALTED},
    PHASE_MOCK_LABELING: {PHASE_HALTED},
    PHASE_HALTED: set(),
}

EXPECTED_EVENT_FOR_PHASE = {
    PHASE_DRAFT: "RUN_INITIALIZED",
    PHASE_PROTOCOL_FROZEN: "PROTOCOL_FROZEN",
    PHASE_FULL_RUN_AUTHORIZED: "FULL_RUN_AUTHORIZATION_CONSUMED",
    PHASE_GENERATING: "GENERATION_STARTED",
    PHASE_GENERATION_COMPLETE: "GENERATION_COMPLETED",
    PHASE_CORPUS_SEALED: "CORPUS_SEALED",
    PHASE_LABELING: "LABELING_STARTED",
    PHASE_LABELS_COMPLETE: "LABELS_COMPLETED",
    PHASE_GATE0_COMPLETE: "GATE0_COMPLETED",
    PHASE_ANALYSIS_COMPLETE: "ANALYSIS_COMPLETED",
    PHASE_MOCK_RUN_AUTHORIZED: "MOCK_RUN_AUTHORIZED",
    PHASE_MOCK_GENERATING: "MOCK_GENERATION_STARTED",
    PHASE_MOCK_GENERATION_COMPLETE: "MOCK_GENERATION_COMPLETED",
    PHASE_MOCK_CORPUS_SEALED: "MOCK_CORPUS_SEALED",
    PHASE_MOCK_LABELING: "MOCK_LABELING_STARTED",
    PHASE_HALTED: "RUN_HALTED",
}

_STATE_TRANSITION_SENTINEL = object()


def _exact_mapping(value: Any, fields: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ContractError(f"{label} fields must exactly equal {sorted(fields)}")
    return value


def _validate_state_event_evidence(
    row: Mapping[str, Any], *, run_dir: Path, previous: Mapping[str, Any] | None,
) -> None:
    """Validate phase-specific evidence every time the state ledger is read."""
    phase = row.get("phase_to")
    execution_class = row.get("execution_class")
    evidence = row.get("evidence")
    if execution_class not in {EXECUTION_PRODUCTION, EXECUTION_MOCK}:
        raise ContractError("state event has an invalid execution_class")
    if phase == PHASE_DRAFT:
        _exact_mapping(
            evidence, {"protocol_lock_sha256", "prompt_plan_sha256"},
            "RUN_INITIALIZED evidence",
        )
        require_sha256(evidence["protocol_lock_sha256"], "state protocol_lock_sha256")
        require_sha256(evidence["prompt_plan_sha256"], "state prompt_plan_sha256")
        return
    if phase == PHASE_PROTOCOL_FROZEN:
        _exact_mapping(evidence, {
            "protocol_lock_sha256", "prompt_plan_sha256", "frozen_bundle_sha256",
            "frozen_bundle_relative_path", "plan_contract", "git_commit_sha",
            "locked_file_count", "production_lock_status",
            "production_authorization_available",
        }, "PROTOCOL_FROZEN evidence")
        for field in ("protocol_lock_sha256", "prompt_plan_sha256", "frozen_bundle_sha256"):
            require_sha256(evidence[field], f"PROTOCOL_FROZEN.{field}")
        if evidence["frozen_bundle_relative_path"] != FROZEN_BUNDLE_NAME:
            raise ContractError("PROTOCOL_FROZEN names a non-canonical frozen bundle")
        if evidence["plan_contract"] != {
            "neutral": N_NEUTRAL, "shifting": N_SHIFTING,
            "unique_seeds": N_CONVERSATIONS,
        }:
            raise ContractError("PROTOCOL_FROZEN has a false plan contract")
        if (evidence["production_lock_status"] != "UNVERIFIED_OFFLINE"
                or evidence["production_authorization_available"] is not False):
            raise ContractError("offline protocol freeze cannot claim a production-verified lock")
        for name, expected_hash in (
            (FROZEN_PLAN_NAME, evidence["prompt_plan_sha256"]),
            (FROZEN_LOCK_NAME, evidence["protocol_lock_sha256"]),
            (FROZEN_BUNDLE_NAME, evidence["frozen_bundle_sha256"]),
        ):
            target = run_dir / name
            if not target.is_file() or sha256_file(target) != expected_hash:
                raise ContractError(f"PROTOCOL_FROZEN artifact mismatch: {name}")
        return
    if phase == PHASE_FULL_RUN_AUTHORIZED:
        raise ContractError(
            "FULL_RUN_AUTHORIZED is impossible in this DESIGN_ONLY offline package"
        )
    if phase == PHASE_MOCK_RUN_AUTHORIZED:
        _exact_mapping(evidence, {
            "authorization_sha256", "authorization_id", "authorization_nonce",
            "expires_at_utc", "max_provider_attempts", "max_cost_usd",
            "frozen_bundle_sha256", "execution_class",
            "production_authorization_status",
        }, "MOCK_RUN_AUTHORIZED evidence")
        if execution_class != EXECUTION_MOCK or evidence["execution_class"] != EXECUTION_MOCK:
            raise ContractError("mock authorization may exist only in MOCK_TEST_ONLY state")
        if evidence["production_authorization_status"] != "NOT_AUTHORIZED":
            raise ContractError("mock authorization cannot claim production authorization")
        require_sha256(evidence["authorization_sha256"], "mock authorization_sha256")
        require_sha256(evidence["frozen_bundle_sha256"], "mock frozen_bundle_sha256")
        if not isinstance(evidence["max_provider_attempts"], int) or evidence[
            "max_provider_attempts"
        ] <= 0:
            raise ContractError("mock attempt ceiling must be positive")
        _decimal_money(evidence["max_cost_usd"], "mock max_cost_usd", positive=True)
        parse_utc(evidence["expires_at_utc"], "mock expires_at_utc")
        return
    if phase in {PHASE_GENERATING, PHASE_MOCK_GENERATING}:
        expected_class = EXECUTION_MOCK if phase == PHASE_MOCK_GENERATING else EXECUTION_PRODUCTION
        if execution_class != expected_class:
            raise ContractError("generation phase disagrees with execution_class")
        _exact_mapping(evidence, {
            "authorization_sha256", "authorization_event_sha256",
            "protocol_lock_sha256", "prompt_plan_sha256", "frozen_bundle_sha256",
            "execution_class", "production_authorization_status",
        }, "GENERATION_STARTED evidence")
        for field in ("authorization_sha256", "authorization_event_sha256",
                      "protocol_lock_sha256", "prompt_plan_sha256", "frozen_bundle_sha256"):
            require_sha256(evidence[field], f"GENERATION_STARTED.{field}")
        if evidence["execution_class"] != execution_class:
            raise ContractError("generation evidence changes execution_class")
        expected_status = "NOT_AUTHORIZED" if execution_class == EXECUTION_MOCK else "AUTHORIZED"
        if evidence["production_authorization_status"] != expected_status:
            raise ContractError("generation evidence has an invalid authorization status")
        if previous is None or evidence["authorization_event_sha256"] != previous.get(
            "record_sha256"
        ):
            raise ContractError("generation is not bound to the immediately prior authorization")
        return
    if phase in {PHASE_GENERATION_COMPLETE, PHASE_MOCK_GENERATION_COMPLETE}:
        expected_class = (
            EXECUTION_MOCK if phase == PHASE_MOCK_GENERATION_COMPLETE else EXECUTION_PRODUCTION
        )
        if execution_class != expected_class:
            raise ContractError("generation completion disagrees with execution_class")
        _exact_mapping(evidence, {
            "run_id", "protocol_lock_sha256", "prompt_plan_sha256",
            "frozen_bundle_sha256", "authorization_sha256",
            "accepted_generation_operations", "expected_generation_operations",
            "attempt_ledger_tip_sha256", "attempt_ledger_sha256",
            "attempt_ledger_bytes", "execution_class",
            "production_authorization_status",
        }, "GENERATION_COMPLETED evidence")
        if (evidence["accepted_generation_operations"] != N_CONVERSATIONS * TURNS_PER_CONVERSATION
                or evidence["expected_generation_operations"]
                != N_CONVERSATIONS * TURNS_PER_CONVERSATION):
            raise ContractError("generation completion does not prove all 920 operations")
        ledger_path = run_dir / PRODUCTION_ATTEMPT_NAME
        if (not ledger_path.is_file() or ledger_path.stat().st_size != evidence[
            "attempt_ledger_bytes"
        ] or sha256_file(ledger_path) != evidence["attempt_ledger_sha256"]):
            raise ContractError("generation completion is not bound to current ledger bytes")
        ledger_rows = _hash_chain_rows(ledger_path, SCHEMA_ATTEMPT)
        if (not ledger_rows or ledger_rows[-1]["record_sha256"]
                != evidence["attempt_ledger_tip_sha256"]):
            raise ContractError("generation completion ledger tip mismatch")
        accepted = {
            r.get("operation_id") for r in ledger_rows
            if r.get("operation_kind") == "generation" and r.get("disposition") == "accepted"
        }
        if len(accepted) != N_CONVERSATIONS * TURNS_PER_CONVERSATION:
            raise ContractError("generation completion ledger lacks 920 unique accepted operations")
        return
    if phase in {PHASE_CORPUS_SEALED, PHASE_MOCK_CORPUS_SEALED}:
        expected_class = EXECUTION_MOCK if phase == PHASE_MOCK_CORPUS_SEALED else EXECUTION_PRODUCTION
        if execution_class != expected_class:
            raise ContractError("corpus seal phase disagrees with execution_class")
        _exact_mapping(evidence, {
            "run_id", "protocol_lock_sha256", "prompt_plan_sha256",
            "frozen_bundle_sha256", "authorization_sha256",
            "generation_complete_state_event_sha256", "attempt_ledger_tip_sha256",
            "attempt_ledger_sha256", "corpus_sha256", "seal_sha256",
            "labels_present_before_seal", "execution_class",
            "production_authorization_status",
        }, "CORPUS_SEALED evidence")
        if evidence["labels_present_before_seal"] is not False:
            raise ContractError("corpus seal cannot admit pre-seal labels")
        seal_path = run_dir / "corpus_seal.json"
        corpus_path = run_dir / "corpus.sealed.jsonl"
        if not seal_path.is_file() or not corpus_path.is_file():
            raise ContractError("corpus seal artifacts are missing")
        seal = load_json(seal_path)
        if (seal.get("seal_sha256") != evidence["seal_sha256"]
                or seal.get("corpus_sha256") != evidence["corpus_sha256"]
                or sha256_file(corpus_path) != evidence["corpus_sha256"]):
            raise ContractError("corpus seal artifacts disagree with state evidence")
        return
    if phase in {PHASE_LABELING, PHASE_MOCK_LABELING}:
        expected_class = EXECUTION_MOCK if phase == PHASE_MOCK_LABELING else EXECUTION_PRODUCTION
        if execution_class != expected_class:
            raise ContractError("labeling phase disagrees with execution_class")
        _exact_mapping(evidence, {
            "valid", "run_id", "sealed_at_utc", "corpus_sha256", "seal_sha256",
            "protocol_lock_sha256", "prompt_plan_sha256", "frozen_bundle_sha256",
            "execution_class", "production_authorization_status",
        }, "LABELING_STARTED evidence")
        if evidence["valid"] is not True:
            raise ContractError("labeling lacks a valid corpus seal")
        return
    if phase == PHASE_HALTED:
        _exact_mapping(evidence, {"reason"}, "RUN_HALTED evidence")
        if not str(evidence["reason"]).strip():
            raise ContractError("halt reason must be non-empty")
        return
    raise ContractError(f"state phase {phase!r} has no evidence validator")


class ExperimentState:
    """Production state ledger.  This offline package can freeze, but never authorize."""

    _initial_execution_class = EXECUTION_PRODUCTION

    def __init__(self, run_dir: os.PathLike[str] | str):
        self.run_dir = Path(run_dir)
        self.path = self.run_dir / "state_events.jsonl"
        self._lock = threading.Lock()

    def _trusted_now(self) -> str:
        value = utc_now()
        parse_utc(value, "trusted clock")
        return value

    def initialize(self, *, run_id: str, protocol_lock_sha256: str,
                   prompt_plan_sha256: str) -> dict[str, Any]:
        require_sha256(protocol_lock_sha256, "protocol_lock_sha256")
        require_sha256(prompt_plan_sha256, "prompt_plan_sha256")
        if self.path.exists():
            raise ContractError("state ledger already exists")
        if not run_id.strip():
            raise ContractError("run_id must be non-empty")
        timestamp = self._trusted_now()
        return _append_hash_chain(self.path, SCHEMA_STATE, {
            "run_id": run_id,
            "execution_class": self._initial_execution_class,
            "event_type": "RUN_INITIALIZED",
            "phase_from": None,
            "phase_to": PHASE_DRAFT,
            "occurred_at_utc": timestamp,
            "evidence": {
                "protocol_lock_sha256": protocol_lock_sha256,
                "prompt_plan_sha256": prompt_plan_sha256,
            },
        })

    def events(self) -> list[dict[str, Any]]:
        rows = _hash_chain_rows(self.path, SCHEMA_STATE)
        if not rows:
            return rows
        first = rows[0]
        if (first.get("event_type") != "RUN_INITIALIZED" or first.get("phase_from") is not None
                or first.get("phase_to") != PHASE_DRAFT):
            raise ContractError("state ledger does not begin with RUN_INITIALIZED -> DRAFT")
        run_id = first.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise ContractError("state ledger run_id is missing")
        previous_time: datetime | None = None
        previous_phase: str | None = None
        execution_class = first.get("execution_class")
        for index, row in enumerate(rows):
            exact_fields = {
                "schema_version", "sequence", "previous_record_sha256", "record_sha256",
                "run_id", "execution_class", "event_type", "phase_from", "phase_to",
                "occurred_at_utc", "evidence",
            }
            if set(row) != exact_fields:
                raise ContractError(f"state row {index} has ambiguous/missing fields")
            if row.get("run_id") != run_id:
                raise ContractError(f"state row {index} changes run_id")
            if row.get("execution_class") != execution_class:
                raise ContractError(f"state row {index} changes execution_class")
            occurred = parse_utc(row.get("occurred_at_utc"),
                                 f"state row {index}.occurred_at_utc")
            if previous_time is not None and occurred <= previous_time:
                raise ContractError("state event timestamps must be strictly increasing")
            if index and row.get("phase_from") != previous_phase:
                raise ContractError(f"state row {index} has a broken phase lineage")
            if index and row.get("phase_to") not in ALLOWED_TRANSITIONS.get(previous_phase, set()):
                raise ContractError(f"state row {index} contains an invalid transition")
            if row.get("event_type") != EXPECTED_EVENT_FOR_PHASE.get(row.get("phase_to")):
                raise ContractError(f"state row {index} event_type/phase mismatch")
            _validate_state_event_evidence(
                row, run_dir=self.run_dir, previous=rows[index - 1] if index else None,
            )
            previous_time = occurred
            previous_phase = row.get("phase_to")
        return rows

    def current(self) -> dict[str, Any]:
        rows = self.events()
        if not rows:
            raise ContractError("state ledger is not initialized")
        return rows[-1]

    @property
    def phase(self) -> str:
        return str(self.current()["phase_to"])

    @property
    def execution_class(self) -> str:
        return str(self.events()[0]["execution_class"])

    def _transition(self, phase_to: str, event_type: str, evidence: Mapping[str, Any], *,
                    trusted_timestamp: str | None = None,
                    _permit: object | None = None) -> dict[str, Any]:
        if _permit is not _STATE_TRANSITION_SENTINEL:
            raise ContractError(
                "direct state transitions are forbidden; use an evidence-completing method"
            )
        with self._lock:
            current = self.current()
            phase_from = current["phase_to"]
            if phase_to not in ALLOWED_TRANSITIONS.get(phase_from, set()):
                raise ContractError(f"invalid phase transition {phase_from} -> {phase_to}")
            timestamp = trusted_timestamp or self._trusted_now()
            parsed_timestamp = parse_utc(timestamp, "occurred_at_utc")
            if parsed_timestamp <= parse_utc(current["occurred_at_utc"],
                                              "previous occurred_at_utc"):
                raise ContractError("new state event must be strictly later than the current event")
            candidate = {
                "run_id": current["run_id"],
                "execution_class": current["execution_class"],
                "event_type": event_type,
                "phase_from": phase_from,
                "phase_to": phase_to,
                "occurred_at_utc": timestamp,
                "evidence": dict(evidence),
            }
            _validate_state_event_evidence(
                candidate, run_dir=self.run_dir, previous=current,
            )
            return _append_hash_chain(self.path, SCHEMA_STATE, candidate)

    def freeze_protocol(
        self, *, prompt_plan: Mapping[str, Any], protocol_lock: Mapping[str, Any],
        source_root: os.PathLike[str] | str,
        forbidden_seed_hashes: Iterable[str] = (),
        forbidden_normalized_seed_hashes: Iterable[str] = (),
    ) -> dict[str, Any]:
        if self.phase != PHASE_DRAFT:
            raise ContractError("protocol freezing requires DRAFT")
        # Recompute both validations here. A caller-supplied boolean/digest summary is not
        # evidence and cannot be used to freeze a run.
        plan_validation = validate_prompt_plan(
            prompt_plan, forbidden_seed_hashes=forbidden_seed_hashes,
            forbidden_normalized_seed_hashes=forbidden_normalized_seed_hashes,
        )
        protocol_validation = validate_protocol_lock(
            protocol_lock, source_root=source_root, prompt_plan=prompt_plan,
            forbidden_seed_hashes=forbidden_seed_hashes,
            forbidden_normalized_seed_hashes=forbidden_normalized_seed_hashes,
        )
        protocol_lock_sha256 = protocol_validation["protocol_lock_sha256"]
        prompt_plan_sha256 = plan_validation["plan_sha256"]
        initialized = self.events()[0]
        expected = initialized["evidence"]
        if protocol_lock_sha256 != expected["protocol_lock_sha256"]:
            raise ContractError("protocol lock differs from initialized run")
        if prompt_plan_sha256 != expected["prompt_plan_sha256"]:
            raise ContractError("prompt plan differs from initialized run")
        if plan_validation.get("valid") is not True or plan_validation.get(
            "plan_sha256"
        ) != prompt_plan_sha256:
            raise ContractError("prompt plan has not passed the exact frozen validation")
        if protocol_validation.get("valid") is not True:
            raise ContractError("protocol lock has not passed exact byte validation")
        if protocol_validation.get("protocol_lock_sha256") != protocol_lock_sha256:
            raise ContractError("protocol lock validation is for different bytes")
        if protocol_validation.get("prompt_plan_sha256") != prompt_plan_sha256:
            raise ContractError("protocol lock is bound to a different prompt plan")
        plan_bytes = canonical_json_bytes(prompt_plan)
        lock_bytes = canonical_json_bytes(protocol_lock)
        if sha256_bytes(plan_bytes) != prompt_plan_sha256:
            raise ContractError("the exact prompt plan supplied for freezing has different bytes")
        if sha256_bytes(lock_bytes) != protocol_lock_sha256:
            raise ContractError("the exact protocol lock supplied for freezing has different bytes")
        if protocol_lock.get("prompt_plan_sha256") != prompt_plan_sha256:
            raise ContractError("frozen protocol lock names a different prompt plan")
        bundle = {
            "schema_version": SCHEMA_FROZEN_BUNDLE,
            "protocol_id": PROTOCOL_ID,
            "run_id": initialized["run_id"],
            "state_initial_event_sha256": initialized["record_sha256"],
            "protocol_lock": {
                "relative_path": FROZEN_LOCK_NAME,
                "sha256": protocol_lock_sha256,
                "bytes": len(lock_bytes),
            },
            "prompt_plan": {
                "relative_path": FROZEN_PLAN_NAME,
                "sha256": prompt_plan_sha256,
                "bytes": len(plan_bytes),
            },
        }
        bundle_bytes = canonical_json_bytes(bundle)
        bundle_sha256 = sha256_bytes(bundle_bytes)
        _write_once(self.run_dir / FROZEN_PLAN_NAME, plan_bytes)
        _write_once(self.run_dir / FROZEN_LOCK_NAME, lock_bytes)
        _write_once(self.run_dir / FROZEN_BUNDLE_NAME, bundle_bytes)
        return self._transition(PHASE_PROTOCOL_FROZEN, "PROTOCOL_FROZEN", {
            "protocol_lock_sha256": protocol_lock_sha256,
            "prompt_plan_sha256": prompt_plan_sha256,
            "frozen_bundle_sha256": bundle_sha256,
            "frozen_bundle_relative_path": FROZEN_BUNDLE_NAME,
            "plan_contract": {"neutral": N_NEUTRAL, "shifting": N_SHIFTING,
                              "unique_seeds": N_CONVERSATIONS},
            "git_commit_sha": protocol_validation.get("git_commit_sha"),
            "locked_file_count": protocol_validation.get("locked_file_count"),
            "production_lock_status": protocol_validation["production_lock_status"],
            "production_authorization_available": False,
        }, _permit=_STATE_TRANSITION_SENTINEL)

    def authorize_full(
        self, authorization: Mapping[str, Any],
    ) -> dict[str, Any]:
        if self.phase != PHASE_PROTOCOL_FROZEN:
            raise ContractError("full-run authorization requires PROTOCOL_FROZEN")
        first = self.events()[0]
        evidence = first["evidence"]
        # Always raises.  There is deliberately no caller-supplied verifier or clock.
        validate_full_run_authorization(
            authorization,
            run_id=first["run_id"],
            protocol_lock_sha256=evidence["protocol_lock_sha256"],
            prompt_plan_sha256=evidence["prompt_plan_sha256"],
        )
        raise AssertionError("unreachable production authorization path")

    def start_generation(self, *, authorization_sha256: str) -> dict[str, Any]:
        require_sha256(authorization_sha256, "authorization_sha256")
        current = self.current()
        if current.get("evidence", {}).get("authorization_sha256") != authorization_sha256:
            raise ContractError("generation start is not bound to the consumed authorization")
        bundle = load_frozen_bundle(self)
        return self._transition(PHASE_GENERATING, "GENERATION_STARTED", {
            "authorization_sha256": authorization_sha256,
            "authorization_event_sha256": current["record_sha256"],
            "protocol_lock_sha256": bundle["protocol_lock_sha256"],
            "prompt_plan_sha256": bundle["prompt_plan_sha256"],
            "frozen_bundle_sha256": bundle["frozen_bundle_sha256"],
            "execution_class": EXECUTION_PRODUCTION,
            "production_authorization_status": "AUTHORIZED",
        }, _permit=_STATE_TRANSITION_SENTINEL)

    def halt(self, reason: str) -> dict[str, Any]:
        if not reason.strip():
            raise ContractError("halt reason must be non-empty")
        return self._transition(
            PHASE_HALTED, "RUN_HALTED", {"reason": reason},
            _permit=_STATE_TRANSITION_SENTINEL,
        )


class MockExperimentState(ExperimentState):
    """Explicitly non-production state used only by offline/temp-directory tests.

    It has distinct phases and receipts.  It cannot enter ``FULL_RUN_AUTHORIZED`` and
    its attempt admissions are permanently classified as never-production evidence.
    """

    _initial_execution_class = EXECUTION_MOCK

    def __init__(self, run_dir: os.PathLike[str] | str,
                 clock: Callable[[], str] | None = None):
        super().__init__(run_dir)
        self._mock_clock = clock or utc_now

    def _trusted_now(self) -> str:
        value = self._mock_clock()
        parse_utc(value, "mock clock")
        return value

    def authorize_mock(self, *, max_provider_attempts: int = 5000,
                       max_cost_usd: str = "100.00") -> dict[str, Any]:
        if self.phase != PHASE_PROTOCOL_FROZEN:
            raise ContractError("mock authorization requires PROTOCOL_FROZEN")
        if not isinstance(max_provider_attempts, int) or max_provider_attempts <= 0:
            raise ContractError("mock max_provider_attempts must be positive")
        cost = _decimal_money(max_cost_usd, "mock max_cost_usd", positive=True)
        bundle = load_frozen_bundle(self)
        observed_at = self._trusted_now()
        expires = parse_utc(observed_at, "mock authorization time") + MAX_AUTHORIZATION_LIFETIME
        expires_at = expires.isoformat(timespec="seconds").replace("+00:00", "Z")
        receipt = {
            "classification": "MOCK_ONLY_NEVER_PRODUCTION",
            "execution_class": EXECUTION_MOCK,
            "run_id": bundle["run_id"],
            "protocol_lock_sha256": bundle["protocol_lock_sha256"],
            "prompt_plan_sha256": bundle["prompt_plan_sha256"],
            "frozen_bundle_sha256": bundle["frozen_bundle_sha256"],
            "issued_at_utc": observed_at,
            "expires_at_utc": expires_at,
            "max_provider_attempts": max_provider_attempts,
            "max_cost_usd": format(cost, "f"),
        }
        authorization_sha256 = sha256_bytes(canonical_json_bytes(receipt))
        return self._transition(
            PHASE_MOCK_RUN_AUTHORIZED, "MOCK_RUN_AUTHORIZED", {
                "authorization_sha256": authorization_sha256,
                "authorization_id": f"mock-{authorization_sha256[:16]}",
                "authorization_nonce": authorization_sha256[16:48],
                "expires_at_utc": expires_at,
                "max_provider_attempts": max_provider_attempts,
                "max_cost_usd": format(cost, "f"),
                "frozen_bundle_sha256": bundle["frozen_bundle_sha256"],
                "execution_class": EXECUTION_MOCK,
                "production_authorization_status": "NOT_AUTHORIZED",
            }, trusted_timestamp=observed_at, _permit=_STATE_TRANSITION_SENTINEL,
        )

    def authorize_full(self, authorization: Mapping[str, Any]) -> dict[str, Any]:
        raise ContractError("MOCK_TEST_ONLY state cannot authorize FULL")

    def start_generation(self, *, authorization_sha256: str) -> dict[str, Any]:
        require_sha256(authorization_sha256, "authorization_sha256")
        current = self.current()
        if (self.phase != PHASE_MOCK_RUN_AUTHORIZED
                or current.get("evidence", {}).get("authorization_sha256")
                != authorization_sha256):
            raise ContractError("mock generation start is not bound to mock authorization")
        bundle = load_frozen_bundle(self)
        return self._transition(PHASE_MOCK_GENERATING, "MOCK_GENERATION_STARTED", {
            "authorization_sha256": authorization_sha256,
            "authorization_event_sha256": current["record_sha256"],
            "protocol_lock_sha256": bundle["protocol_lock_sha256"],
            "prompt_plan_sha256": bundle["prompt_plan_sha256"],
            "frozen_bundle_sha256": bundle["frozen_bundle_sha256"],
            "execution_class": EXECUTION_MOCK,
            "production_authorization_status": "NOT_AUTHORIZED",
        }, _permit=_STATE_TRANSITION_SENTINEL)


def load_frozen_bundle(state: ExperimentState) -> dict[str, Any]:
    """Reload and byte-check the only plan/lock a run may ever use."""
    events = state.events()
    if not events:
        raise ContractError("state ledger is not initialized")
    frozen_events = [row for row in events if row.get("event_type") == "PROTOCOL_FROZEN"]
    if len(frozen_events) != 1:
        raise ContractError("run must contain exactly one PROTOCOL_FROZEN event")
    frozen_event = frozen_events[0]
    initial = events[0]
    plan_path = state.run_dir / FROZEN_PLAN_NAME
    lock_path = state.run_dir / FROZEN_LOCK_NAME
    bundle_path = state.run_dir / FROZEN_BUNDLE_NAME
    for path in (plan_path, lock_path, bundle_path):
        if not path.is_file():
            raise ContractError(f"frozen run artifact is missing: {path.name}")
    plan_bytes = plan_path.read_bytes()
    lock_bytes = lock_path.read_bytes()
    bundle_bytes = bundle_path.read_bytes()
    try:
        plan = json.loads(plan_bytes.decode("utf-8"))
        protocol_lock = json.loads(lock_bytes.decode("utf-8"))
        bundle = json.loads(bundle_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("frozen bundle contains invalid UTF-8 JSON") from exc
    if (canonical_json_bytes(plan) != plan_bytes or canonical_json_bytes(protocol_lock) != lock_bytes
            or canonical_json_bytes(bundle) != bundle_bytes):
        raise ContractError("frozen artifacts must retain exact canonical JSON bytes")
    plan_sha = sha256_bytes(plan_bytes)
    lock_sha = sha256_bytes(lock_bytes)
    bundle_sha = sha256_bytes(bundle_bytes)
    expected_plan_sha = initial["evidence"]["prompt_plan_sha256"]
    expected_lock_sha = initial["evidence"]["protocol_lock_sha256"]
    if plan_sha != expected_plan_sha or lock_sha != expected_lock_sha:
        raise ContractError("frozen plan/lock bytes no longer match RUN_INITIALIZED")
    if frozen_event["evidence"].get("prompt_plan_sha256") != plan_sha:
        raise ContractError("PROTOCOL_FROZEN event is bound to different plan bytes")
    if frozen_event["evidence"].get("protocol_lock_sha256") != lock_sha:
        raise ContractError("PROTOCOL_FROZEN event is bound to different lock bytes")
    if frozen_event["evidence"].get("frozen_bundle_sha256") != bundle_sha:
        raise ContractError("PROTOCOL_FROZEN event is bound to a different frozen bundle")
    expected_bundle = {
        "schema_version": SCHEMA_FROZEN_BUNDLE,
        "protocol_id": PROTOCOL_ID,
        "run_id": initial["run_id"],
        "state_initial_event_sha256": initial["record_sha256"],
        "protocol_lock": {
            "relative_path": FROZEN_LOCK_NAME,
            "sha256": lock_sha,
            "bytes": len(lock_bytes),
        },
        "prompt_plan": {
            "relative_path": FROZEN_PLAN_NAME,
            "sha256": plan_sha,
            "bytes": len(plan_bytes),
        },
    }
    if bundle != expected_bundle:
        raise ContractError("frozen bundle manifest is not the exact state-bound manifest")
    validation = validate_prompt_plan(plan)
    if validation["plan_sha256"] != plan_sha:
        raise ContractError("frozen prompt plan failed exact validation")
    if (protocol_lock.get("schema_version") != SCHEMA_PROTOCOL_LOCK
            or protocol_lock.get("protocol_id") != PROTOCOL_ID
            or protocol_lock.get("prompt_plan_sha256") != plan_sha):
        raise ContractError("frozen protocol lock contract/binding is invalid")
    return {
        "valid": True,
        "run_id": initial["run_id"],
        "protocol_lock_sha256": lock_sha,
        "prompt_plan_sha256": plan_sha,
        "frozen_bundle_sha256": bundle_sha,
        "prompt_plan": plan,
        "protocol_lock": protocol_lock,
        "protocol_frozen_event_sha256": frozen_event["record_sha256"],
    }


def _validate_evidence_value(value: Any, field: str) -> None:
    if not isinstance(value, dict) or value.get("status") not in {"present", "unavailable"}:
        raise ContractError(f"{field} must explicitly be present or unavailable")
    if value["status"] == "present":
        if set(value) != {"status", "value"}:
            raise ContractError(f"{field} present value has ambiguous fields")
        if not str(value.get("value", "")).strip():
            raise ContractError(f"{field}.value must be non-empty when present")
        if "reason" in value:
            raise ContractError(f"{field}.reason is forbidden when present")
    else:
        if set(value) != {"status", "reason"}:
            raise ContractError(f"{field} unavailable value has ambiguous fields")
        if not str(value.get("reason", "")).strip():
            raise ContractError(f"{field}.reason must explain unavailability")
        if "value" in value:
            raise ContractError(f"{field}.value is forbidden when unavailable")


def _validate_artifact_ref(value: Any, field: str, artifact_root: Path | None) -> None:
    if not isinstance(value, dict) or value.get("status") not in {"present", "unavailable"}:
        raise ContractError(f"{field} must explicitly be present or unavailable")
    if value["status"] == "unavailable":
        if set(value) != {"status", "reason"}:
            raise ContractError(f"{field} unavailable artifact has ambiguous fields")
        if not str(value.get("reason", "")).strip():
            raise ContractError(f"{field}.reason must explain unavailability")
        return
    if set(value) != {"status", "relative_path", "sha256", "bytes"}:
        raise ContractError(f"{field} present artifact has ambiguous fields")
    relative = value.get("relative_path")
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ContractError(f"{field}.relative_path must be a non-empty relative path")
    require_sha256(value.get("sha256"), f"{field}.sha256")
    if not isinstance(value.get("bytes"), int) or value["bytes"] < 0:
        raise ContractError(f"{field}.bytes must be a non-negative integer")
    if artifact_root is not None:
        root = artifact_root.resolve()
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ContractError(f"{field}.relative_path escapes the artifact root") from exc
        if not target.is_file():
            raise ContractError(f"{field} artifact is missing: {target}")
        if target.stat().st_size != value["bytes"] or sha256_file(target) != value["sha256"]:
            raise ContractError(f"{field} artifact bytes/hash mismatch")


def _artifact_path(reference: Mapping[str, Any], artifact_root: Path, field: str) -> Path:
    _validate_artifact_ref(reference, field, artifact_root)
    if reference.get("status") != "present":
        raise ContractError(f"{field} must be present")
    root = artifact_root.resolve()
    target = (root / str(reference["relative_path"])).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:  # defensive duplicate of _validate_artifact_ref
        raise ContractError(f"{field} escapes artifact root") from exc
    return target


_SECRET_KEYS = {
    "authorization", "proxy-authorization", "x-api-key", "api-key", "apikey",
    "x-goog-api-key", "cookie", "set-cookie", "access-token", "access_token",
    "client-secret", "client_secret",
}
_SECRET_VALUE_PATTERNS = (
    re.compile(r"(?i)\bbearer\s+\S+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bAKIA[A-Z0-9]{12,}"),
)


def _load_canonical_json_artifact(
    reference: Mapping[str, Any], artifact_root: Path, field: str,
) -> Any:
    path = _artifact_path(reference, artifact_root, field)
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{field} must be valid UTF-8 JSON") from exc
    if canonical_json_bytes(value) != raw:
        raise ContractError(f"{field} must use exact canonical JSON bytes")
    return value


def _reject_secret_material(value: Any, field: str, *, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key).strip().casefold()
            if key_text in _SECRET_KEYS:
                raise ContractError(f"{field} contains forbidden secret-bearing key at {path}.{key}")
            _reject_secret_material(child, field, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_secret_material(child, field, path=f"{path}[{index}]")
    elif isinstance(value, str):
        if any(pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS):
            raise ContractError(f"{field} contains secret-bearing material at {path}")


def _validate_transport_receipt(evidence: Mapping[str, Any], root: Path) -> None:
    receipt = _exact_mapping(evidence.get("transport_receipt"), {
        "classification", "method", "endpoint_origin", "request_path",
        "request_body_sha256", "response_body_sha256", "response_headers_sha256",
    }, "provider_evidence.transport_receipt")
    provider = evidence.get("provider")
    if provider not in PROVIDER_ORIGINS:
        raise ContractError("provider_evidence.provider is not allowlisted")
    if evidence.get("endpoint_origin") != PROVIDER_ORIGINS[provider]:
        raise ContractError("endpoint_origin does not equal the exact allowlisted provider origin")
    if (receipt["endpoint_origin"] != PROVIDER_ORIGINS[provider]
            or receipt["request_path"] != PROVIDER_CHAT_PATHS[provider]
            or receipt["method"] != "POST"):
        raise ContractError("transport receipt is not bound to the allowlisted provider endpoint")
    if receipt["classification"] not in {
        "MOCK_CAPTURE_ONLY_NEVER_PRODUCTION", "AUTHENTICATED_PROVIDER_RECEIPT"
    }:
        raise ContractError("transport receipt has an unknown classification")
    bindings = (
        ("request_artifact", "request_body_sha256"),
        ("response_artifact", "response_body_sha256"),
        ("response_headers_artifact", "response_headers_sha256"),
    )
    for artifact_field, receipt_field in bindings:
        reference = evidence[artifact_field]
        _artifact_path(reference, root, f"provider_evidence.{artifact_field}")
        if receipt[receipt_field] != reference["sha256"]:
            raise ContractError(f"transport receipt {receipt_field} mismatch")


def _derive_mock_cost_evidence(evidence: Mapping[str, Any], *, execution_class: str) -> dict[str, Any]:
    if execution_class != EXECUTION_MOCK:
        raise ContractError(
            "AUTHENTICATED_USAGE_AND_PRICING_RECEIPTS_UNAVAILABLE: production cost cannot be derived"
        )
    usage = evidence.get("usage")
    if not isinstance(usage, dict) or usage.get("status") != "present":
        raise ContractError("mock cost derivation requires present token usage")
    provider = evidence.get("provider")
    if provider not in MOCK_USD_PER_MILLION_TOKENS:
        raise ContractError("mock cost derivation has no frozen provider rate")
    rates = MOCK_USD_PER_MILLION_TOKENS[provider]
    input_cost = Decimal(usage["input_tokens"]) * rates["input"] / Decimal(1_000_000)
    output_cost = Decimal(usage["output_tokens"]) * rates["output"] / Decimal(1_000_000)
    derived = (input_cost + output_cost).quantize(Decimal("0.00000001"))
    if usage["total_tokens"] > 0 and derived <= 0:
        raise ContractError("non-zero token usage cannot have zero derived cost")
    return {
        "classification": "MOCK_DERIVED_NOT_BILLING_EVIDENCE",
        "currency": "USD",
        "usage_receipt_status": "MOCK_UNAUTHENTICATED",
        "pricing_receipt_status": "FROZEN_MOCK_RATE_TABLE_NOT_PROVIDER_RECEIPT",
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "input_usd_per_million_tokens": format(rates["input"], "f"),
        "output_usd_per_million_tokens": format(rates["output"], "f"),
        "derived_cost_usd": format(derived, "f"),
    }


def _resolve_json_pointer(document: Any, pointer: str) -> Any:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ContractError("response_extraction.json_pointer must be a non-root JSON pointer")
    current = document
    for raw_token in pointer.split("/")[1:]:
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if "~" in token and re.search(r"~(?![01])", raw_token):
            raise ContractError("response_extraction.json_pointer has invalid escaping")
        if isinstance(current, list):
            if not token.isdigit() or (token.startswith("0") and token != "0"):
                raise ContractError("response_extraction JSON pointer has invalid array index")
            index = int(token)
            if index >= len(current):
                raise ContractError("response_extraction JSON pointer is out of range")
            current = current[index]
        elif isinstance(current, dict):
            if token not in current:
                raise ContractError("response_extraction JSON pointer key is absent")
            current = current[token]
        else:
            raise ContractError("response_extraction JSON pointer traverses a scalar")
    return current


def _validate_label_contract(contract: Any, *, task: str) -> dict[int, str]:
    if not isinstance(contract, dict) or set(contract) != {
        "alias_map", "alias_map_sha256", "accepted_labels_sha256"
    }:
        raise ContractError("label_contract must contain only its three bound fields")
    alias_map = contract.get("alias_map")
    if not isinstance(alias_map, list) or not alias_map:
        raise ContractError("label_contract.alias_map must be a non-empty array")
    mapping: dict[int, str] = {}
    item_ids: set[str] = set()
    for index, row in enumerate(alias_map):
        if not isinstance(row, dict) or set(row) != {"alias_id", "item_id"}:
            raise ContractError(f"label_contract.alias_map[{index}] has invalid fields")
        alias_id = row.get("alias_id")
        item_id = row.get("item_id")
        if not isinstance(alias_id, int) or isinstance(alias_id, bool) or not 1000 <= alias_id <= 9999:
            raise ContractError("label alias ids must be four-digit integers")
        if not isinstance(item_id, str) or not item_id:
            raise ContractError("label item ids must be non-empty strings")
        if alias_id in mapping or item_id in item_ids:
            raise ContractError("label alias map must be one-to-one")
        mapping[alias_id] = item_id
        item_ids.add(item_id)
    if contract.get("alias_map_sha256") != sha256_bytes(canonical_json_bytes(alias_map)):
        raise ContractError("label alias map hash mismatch")
    require_sha256(contract.get("accepted_labels_sha256"),
                   "label_contract.accepted_labels_sha256")
    if task not in ALLOWED_LABELS:
        raise ContractError("label contract has an unknown task")
    return mapping


def extract_response_answer(
    evidence: Mapping[str, Any], *, artifact_root: os.PathLike[str] | str,
    operation_kind: str, label_contract: Mapping[str, Any] | None = None,
    task: str | None = None,
) -> dict[str, Any]:
    """Extract the accepted answer from the hash-verified raw response body."""
    extraction = evidence.get("response_extraction")
    if not isinstance(extraction, dict) or extraction.get("status") != "present":
        raise ContractError("accepted attempts require present response_extraction")
    expected_fields = {
        "status", "kind", "json_pointer", "extracted_text_sha256", "parsed_json_sha256"
    }
    if set(extraction) != expected_fields:
        raise ContractError("response_extraction has ambiguous or missing fields")
    expected_kind = "assistant_text" if operation_kind == "generation" else "label_json"
    if extraction.get("kind") != expected_kind:
        raise ContractError("response_extraction kind does not match operation_kind")
    require_sha256(extraction.get("extracted_text_sha256"),
                   "response_extraction.extracted_text_sha256")
    root = Path(artifact_root)
    response_path = _artifact_path(evidence.get("response_artifact"), root,
                                   "provider_evidence.response_artifact")
    try:
        raw_document = json.loads(response_path.read_bytes().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("raw response artifact is not valid UTF-8 JSON") from exc
    answer = _resolve_json_pointer(raw_document, extraction.get("json_pointer"))
    if not isinstance(answer, str) or not answer.strip():
        raise ContractError("raw response JSON pointer must resolve to non-empty answer text")
    if sha256_text(answer) != extraction["extracted_text_sha256"]:
        raise ContractError("extracted answer text hash does not match raw response")
    parsed_answer: Any = None
    if operation_kind == "generation":
        if extraction.get("parsed_json_sha256") is not None:
            raise ContractError("generation extraction parsed_json_sha256 must be null")
    elif operation_kind == "label":
        mapping = _validate_label_contract(label_contract, task=str(task))
        try:
            parsed_answer = json.loads(answer)
        except json.JSONDecodeError as exc:
            raise ContractError("label answer text is not JSON") from exc
        if not isinstance(parsed_answer, list) or len(parsed_answer) != len(mapping):
            raise ContractError("label answer must have exactly one row per frozen alias")
        observed: dict[int, str] = {}
        canonical_labels: list[dict[str, Any]] = []
        allowed = ALLOWED_LABELS[str(task)]
        for row in parsed_answer:
            if not isinstance(row, dict) or set(row) != {"id", "label"}:
                raise ContractError("every label answer row must contain only id and label")
            alias_id = row.get("id")
            label = row.get("label")
            if (not isinstance(alias_id, int) or isinstance(alias_id, bool)
                    or alias_id not in mapping or alias_id in observed):
                raise ContractError("label answer has a fabricated, duplicate, or missing alias id")
            if not isinstance(label, str) or label not in allowed:
                raise ContractError("label answer contains a non-allowlisted label")
            observed[alias_id] = label
            canonical_labels.append({"id": alias_id, "item_id": mapping[alias_id], "label": label})
        if set(observed) != set(mapping):
            raise ContractError("label answer alias-id set does not exactly match the frozen batch")
        parsed_sha = sha256_bytes(canonical_json_bytes(parsed_answer))
        if extraction.get("parsed_json_sha256") != parsed_sha:
            raise ContractError("parsed label JSON hash mismatch")
        accepted_sha = sha256_bytes(canonical_json_bytes(canonical_labels))
        if label_contract.get("accepted_labels_sha256") != accepted_sha:
            raise ContractError("accepted labels hash does not match raw response JSON")
    else:
        raise ContractError("response extraction requires generation or label operation_kind")
    return {"answer_text": answer, "parsed_answer": parsed_answer}


def validate_provider_evidence(evidence: Mapping[str, Any], *,
                               artifact_root: os.PathLike[str] | str | None = None,
                               accepted: bool = False,
                               operation_kind: str | None = None,
                               label_contract: Mapping[str, Any] | None = None,
                               task: str | None = None) -> dict[str, Any] | None:
    if not isinstance(evidence, dict):
        raise ContractError("provider_evidence must be an object")
    expected_fields = {
        "provider", "endpoint_origin", "requested_model", "resolved_response_model",
        "provider_request_id", "provider_created_at_utc", "request_artifact",
        "response_artifact", "response_headers_artifact", "sdk_name", "sdk_version",
        "started_at_utc", "finished_at_utc", "http_status", "finish_reason", "usage",
        "error", "response_extraction", "transport_receipt",
    }
    if set(evidence) != expected_fields:
        raise ContractError("provider_evidence fields must exactly match the provenance contract")
    for field in ("provider", "requested_model", "sdk_name", "sdk_version"):
        if not str(evidence.get(field, "")).strip():
            raise ContractError(f"provider_evidence.{field} must be non-empty")
    provider = evidence.get("provider")
    if provider not in PROVIDER_ORIGINS:
        raise ContractError("provider_evidence.provider is not allowlisted")
    endpoint = str(evidence.get("endpoint_origin", ""))
    parsed = urlsplit(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ContractError("endpoint_origin must be an HTTPS origin without credentials")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ContractError("endpoint_origin must omit API paths, query strings, and fragments")
    if endpoint != PROVIDER_ORIGINS[provider]:
        raise ContractError("endpoint_origin does not equal the exact allowlisted provider origin")
    started = parse_utc(evidence.get("started_at_utc"), "provider_evidence.started_at_utc")
    finished = parse_utc(evidence.get("finished_at_utc"), "provider_evidence.finished_at_utc")
    if finished < started:
        raise ContractError("provider evidence finishes before it starts")
    status = evidence.get("http_status")
    if status is not None and (not isinstance(status, int) or not 100 <= status <= 599):
        raise ContractError("provider_evidence.http_status must be null or 100..599")
    for field in ("resolved_response_model", "provider_request_id", "provider_created_at_utc",
                  "finish_reason", "error"):
        _validate_evidence_value(evidence.get(field), f"provider_evidence.{field}")
    if evidence["provider_created_at_utc"]["status"] == "present":
        parse_utc(evidence["provider_created_at_utc"]["value"],
                  "provider_evidence.provider_created_at_utc.value")
    root = Path(artifact_root) if artifact_root is not None else None
    for field in ("request_artifact", "response_artifact", "response_headers_artifact"):
        _validate_artifact_ref(evidence.get(field), f"provider_evidence.{field}", root)
    if root is not None:
        raw_request = _load_canonical_json_artifact(
            evidence["request_artifact"], root, "provider_evidence.request_artifact"
        )
        raw_headers = _load_canonical_json_artifact(
            evidence["response_headers_artifact"], root,
            "provider_evidence.response_headers_artifact",
        )
        if not isinstance(raw_request, dict):
            raise ContractError("raw request artifact must contain a JSON object")
        if not isinstance(raw_headers, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in raw_headers.items()
        ):
            raise ContractError("raw response headers artifact must be a string map")
        _reject_secret_material(raw_request, "raw request artifact")
        _reject_secret_material(raw_headers, "raw response headers artifact")
        _validate_transport_receipt(evidence, root)
    extraction = evidence.get("response_extraction")
    if not isinstance(extraction, dict) or extraction.get("status") not in {"present", "unavailable"}:
        raise ContractError("provider_evidence.response_extraction must be present or unavailable")
    if extraction.get("status") == "unavailable":
        if set(extraction) != {"status", "reason"}:
            raise ContractError("unavailable response extraction has ambiguous fields")
        if not str(extraction.get("reason", "")).strip():
            raise ContractError("unavailable response extraction must explain why")
    usage = evidence.get("usage")
    if not isinstance(usage, dict) or usage.get("status") not in {"present", "unavailable"}:
        raise ContractError("provider_evidence.usage must explicitly be present or unavailable")
    if usage["status"] == "present":
        if set(usage) != {"status", "input_tokens", "output_tokens", "total_tokens"}:
            raise ContractError("provider_evidence.usage present value has ambiguous fields")
        for field in ("input_tokens", "output_tokens", "total_tokens"):
            if not isinstance(usage.get(field), int) or usage[field] < 0:
                raise ContractError(f"provider_evidence.usage.{field} must be non-negative")
        if usage["total_tokens"] != usage["input_tokens"] + usage["output_tokens"]:
            raise ContractError("provider_evidence.usage token total mismatch")
    else:
        if set(usage) != {"status", "reason"}:
            raise ContractError("provider_evidence.usage unavailable value has ambiguous fields")
        if not str(usage.get("reason", "")).strip():
            raise ContractError("provider_evidence.usage.reason must explain unavailability")
    if accepted:
        for field in ("request_artifact", "response_artifact", "response_headers_artifact"):
            if evidence[field].get("status") != "present":
                raise ContractError(f"accepted attempts require present {field}")
        if evidence["resolved_response_model"].get("status") != "present":
            raise ContractError("accepted attempts require the resolved response model")
        if evidence.get("http_status") is None or not 200 <= evidence["http_status"] <= 299:
            raise ContractError("accepted attempts require a 2xx HTTP status")
        if evidence["finish_reason"] != {"status": "present", "value": "stop"}:
            raise ContractError("accepted attempts require terminal finish_reason=stop")
        if evidence["error"].get("status") != "unavailable":
            raise ContractError("accepted attempts cannot contain a provider error")
        if root is None:
            raise ContractError("accepted evidence requires an artifact_root for content verification")
        if operation_kind not in {"generation", "label"}:
            raise ContractError("accepted evidence requires an operation_kind")
        return extract_response_answer(
            evidence, artifact_root=root, operation_kind=operation_kind,
            label_contract=label_contract, task=task,
        )
    return None


def label_operation_id(*, task: str, reader: str, repair_round: int,
                       batch_ordinal: int, item_ids: Sequence[str], corpus_sha256: str) -> str:
    if task not in ALLOWED_TASKS:
        raise ContractError(f"unknown label task {task!r}")
    if reader not in GENERATOR_MODELS:
        raise ContractError(f"unknown reader {reader!r}")
    if not isinstance(repair_round, int) or not 0 <= repair_round <= 2:
        raise ContractError("repair_round must be 0, 1, or 2")
    if not isinstance(batch_ordinal, int) or batch_ordinal < 0:
        raise ContractError("batch_ordinal must be non-negative")
    require_sha256(corpus_sha256, "corpus_sha256")
    if not item_ids or len(set(item_ids)) != len(item_ids):
        raise ContractError("item_ids must be non-empty and unique")
    item_hash = sha256_bytes(canonical_json_bytes(sorted(item_ids)))[:20]
    lane = "main" if repair_round == 0 else f"repair-{repair_round}"
    return f"label/{task}/{reader}/{lane}/batch-{batch_ordinal:05d}/{item_hash}/{corpus_sha256[:16]}"


def generation_operation_id(conversation_id: str, turn_index: int) -> str:
    if not CONVERSATION_ID.fullmatch(conversation_id):
        raise ContractError("invalid generation conversation id")
    if not isinstance(turn_index, int) or not 0 <= turn_index < TURNS_PER_CONVERSATION:
        raise ContractError("generation turn index must be 0..9")
    return f"generation/{conversation_id}/turn-{turn_index:02d}"


def expected_generation_request(
    planned: Mapping[str, Any], turn_index: int,
    accepted_prior: Mapping[str, Mapping[str, Any]], *, artifact_root: Path,
) -> dict[str, Any]:
    """Derive the one admissible raw request from frozen text and prior raw responses."""
    conversation_id = str(planned.get("conversation_id", ""))
    generation_operation_id(conversation_id, turn_index)
    messages: list[dict[str, str]] = []
    for prior_turn in range(turn_index + 1):
        user_text = (
            planned["seed_prompt"] if prior_turn == 0
            else planned["followups"][prior_turn - 1]["text"]
        )
        messages.append({"role": "user", "content": user_text})
        if prior_turn < turn_index:
            prior_operation = generation_operation_id(conversation_id, prior_turn)
            prior = accepted_prior.get(prior_operation)
            if prior is None or prior.get("disposition") != "accepted":
                raise ContractError(
                    f"{conversation_id} turn {turn_index} requires accepted turn {prior_turn} first"
                )
            answer = extract_response_answer(
                prior["provider_evidence"], artifact_root=artifact_root,
                operation_kind="generation",
            )["answer_text"]
            messages.append({"role": "assistant", "content": answer})
    return {
        "model": planned["generator"]["requested_model"],
        "messages": messages,
        "temperature": GENERATION_PARAMETERS["temperature"],
        "max_tokens": GENERATION_PARAMETERS["max_tokens"],
    }


def validate_generation_request_artifact(
    evidence: Mapping[str, Any], *, planned: Mapping[str, Any], turn_index: int,
    accepted_prior: Mapping[str, Mapping[str, Any]], artifact_root: Path,
) -> dict[str, Any]:
    raw = _load_canonical_json_artifact(
        evidence.get("request_artifact"), artifact_root,
        "provider_evidence.request_artifact",
    )
    expected = expected_generation_request(
        planned, turn_index, accepted_prior, artifact_root=artifact_root,
    )
    if raw != expected:
        raise ContractError(
            "raw generation request does not equal frozen seed/followup/history/model/parameters"
        )
    if evidence.get("transport_receipt", {}).get("request_body_sha256") != sha256_bytes(
        canonical_json_bytes(expected)
    ):
        raise ContractError("transport receipt is not bound to the exact derived request")
    return expected


def _validate_attempt_operation_binding(row: Mapping[str, Any], field: str) -> None:
    operation_id = str(row.get("operation_id", ""))
    evidence = row.get("provider_evidence") or {}
    if row.get("operation_kind") == "generation":
        match = GENERATION_OPERATION_RE.fullmatch(operation_id)
        if not match or int(match.group(2)) >= TURNS_PER_CONVERSATION:
            raise ContractError(f"{field}: malformed generation operation_id")
        return
    match = LABEL_OPERATION_RE.fullmatch(operation_id)
    if not match:
        raise ContractError(f"{field}: malformed label operation_id")
    task, reader, lane, batch_text, item_hash, corpus_prefix = match.groups()
    expected_round = 0 if lane == "main" else int(lane.rsplit("-", 1)[1])
    if task != row.get("task") or expected_round != row.get("repair_round"):
        raise ContractError(f"{field}: label operation id disagrees with task/repair round")
    if evidence.get("provider") != reader or evidence.get("requested_model") != GENERATOR_MODELS[
        reader
    ]:
        raise ContractError(f"{field}: label operation reader/model mismatch")
    corpus_sha256 = require_sha256(row.get("corpus_sha256"), f"{field}.corpus_sha256")
    if corpus_prefix != corpus_sha256[:16]:
        raise ContractError(f"{field}: label operation is bound to a different corpus")
    mapping = _validate_label_contract(row.get("label_contract"), task=task)
    expected = label_operation_id(
        task=task, reader=reader, repair_round=expected_round,
        batch_ordinal=int(batch_text), item_ids=list(mapping.values()),
        corpus_sha256=corpus_sha256,
    )
    if expected != operation_id or item_hash not in expected:
        raise ContractError(f"{field}: label operation id is not bound to its exact alias map")


_ADMISSION_SENTINEL = object()


class _AttemptAdmission:
    """In-process capability created only after state/authority/chronology checks."""

    __slots__ = ("payload", "max_attempts", "max_cost", "_sentinel")

    def __init__(self, sentinel: object, payload: Mapping[str, Any], *,
                 max_attempts: int, max_cost: Decimal):
        if sentinel is not _ADMISSION_SENTINEL:
            raise ContractError("invalid attempt-admission capability")
        self.payload = dict(payload)
        self.max_attempts = max_attempts
        self.max_cost = max_cost
        self._sentinel = sentinel


class AttemptLedger:
    """Production ledger plus a separate, permanently untrusted import journal."""

    def __init__(self, path: os.PathLike[str] | str,
                 artifact_root: os.PathLike[str] | str | None = None):
        self.path = Path(path)
        self.artifact_root = Path(artifact_root) if artifact_root is not None else None
        self.audit_path = self.path.with_name(self.path.name + ".audit_imports.jsonl")
        self._lock = threading.Lock()
        self._cache: list[dict[str, Any]] | None = None
        self._cache_stat: tuple[int, int] | None = None
        self._semantics_verified_stat: tuple[int, int] | None = None

    @classmethod
    def for_run(cls, state: ExperimentState) -> "AttemptLedger":
        return cls(state.run_dir / PRODUCTION_ATTEMPT_NAME,
                   state.run_dir / ARTIFACT_DIR_NAME)

    def records(self, *, force_verify: bool = False) -> list[dict[str, Any]]:
        stat = self.path.stat() if self.path.exists() else None
        fingerprint = (stat.st_size, stat.st_mtime_ns) if stat else None
        if not force_verify and self._cache is not None and fingerprint == self._cache_stat:
            return list(self._cache)
        rows = _hash_chain_rows(self.path, SCHEMA_ATTEMPT)
        self._cache = rows
        stat = self.path.stat() if self.path.exists() else None
        self._cache_stat = (stat.st_size, stat.st_mtime_ns) if stat else None
        return list(rows)

    def audit_records(self) -> list[dict[str, Any]]:
        return _hash_chain_rows(self.audit_path, SCHEMA_AUDIT_IMPORT)

    def import_audit_only(self, attempt: Mapping[str, Any]) -> dict[str, Any]:
        """Journal arbitrary historical material without admitting it as run evidence."""
        if not isinstance(attempt, Mapping):
            raise ContractError("audit import payload must be an object")
        payload = dict(attempt)
        # Prove serialisability before touching disk.
        payload_sha = sha256_bytes(canonical_json_bytes(payload))
        with self._lock:
            return _append_hash_chain(self.audit_path, SCHEMA_AUDIT_IMPORT, {
                "classification": "AUDIT_ONLY_UNTRUSTED_NEVER_ACCEPTABLE",
                "imported_at_utc": utc_now(),
                "source_payload_sha256": payload_sha,
                "payload": payload,
            })

    def append(self, attempt: Mapping[str, Any]) -> dict[str, Any]:
        """Compatibility name: direct append is audit-only and never production evidence."""
        return self.import_audit_only(attempt)

    def verify(self, *, force_chain: bool = False) -> list[dict[str, Any]]:
        rows = self.records(force_verify=force_chain)
        if not force_chain and self._semantics_verified_stat == self._cache_stat:
            return rows
        seen_attempts: set[str] = set()
        per_operation: dict[str, list[dict[str, Any]]] = defaultdict(list)
        terminal_operations: set[str] = set()
        exact_fields = {
            "schema_version", "sequence", "previous_record_sha256", "record_sha256",
            "attempt_id", "run_id", "operation_id", "operation_kind", "task",
            "repair_round", "attempt_no", "retry_of_attempt_id", "disposition",
            "protocol_lock_sha256", "prompt_plan_sha256", "frozen_bundle_sha256",
            "corpus_sha256", "cost_evidence", "label_contract", "provider_evidence",
            "admission",
        }
        for index, row in enumerate(rows):
            if set(row) != exact_fields:
                raise ContractError(f"attempt ledger row {index} has ambiguous/missing fields")
            attempt_id = row.get("attempt_id")
            operation_id = row.get("operation_id")
            if not isinstance(attempt_id, str) or not attempt_id or attempt_id in seen_attempts:
                raise ContractError(f"attempt ledger row {index} has a missing/duplicate attempt_id")
            seen_attempts.add(attempt_id)
            if not isinstance(operation_id, str) or not operation_id:
                raise ContractError(f"attempt ledger row {index} has no operation_id")
            if operation_id in terminal_operations:
                raise ContractError(f"attempt ledger row {index} follows a terminal operation")
            kind = row.get("operation_kind")
            if kind not in {"generation", "label"}:
                raise ContractError(f"attempt ledger row {index} has invalid operation_kind")
            if row.get("disposition") not in ALLOWED_DISPOSITIONS:
                raise ContractError(f"attempt ledger row {index} has invalid disposition")
            prior = per_operation[operation_id]
            if row.get("attempt_no") != len(prior) + 1:
                raise ContractError(f"attempt ledger row {index} has a broken attempt sequence")
            expected_retry = prior[-1]["attempt_id"] if prior else None
            if row.get("retry_of_attempt_id") != expected_retry:
                raise ContractError(f"attempt ledger row {index} has broken retry lineage")
            if not isinstance(row.get("repair_round"), int) or not 0 <= row["repair_round"] <= 2:
                raise ContractError(f"attempt ledger row {index} has invalid repair_round")
            if kind == "generation":
                if (row.get("task") is not None or row["repair_round"] != 0
                        or row.get("corpus_sha256") is not None
                        or row.get("label_contract") is not None):
                    raise ContractError(f"attempt ledger row {index} violates generation fields")
            else:
                if row.get("task") not in ALLOWED_TASKS:
                    raise ContractError(f"attempt ledger row {index} has invalid label task")
                require_sha256(row.get("corpus_sha256"), f"attempt row {index}.corpus_sha256")
                _validate_label_contract(row.get("label_contract"), task=row["task"])
            require_sha256(row.get("protocol_lock_sha256"),
                           f"attempt row {index}.protocol_lock_sha256")
            require_sha256(row.get("prompt_plan_sha256"),
                           f"attempt row {index}.prompt_plan_sha256")
            require_sha256(row.get("frozen_bundle_sha256"),
                           f"attempt row {index}.frozen_bundle_sha256")
            admission = row.get("admission")
            admission_fields = {
                "status", "authorization_sha256", "authorization_event_sha256",
                "phase_event_sha256", "phase_started_at_utc", "admitted_at_utc",
                "frozen_bundle_sha256", "execution_class",
            }
            if not isinstance(admission, dict) or set(admission) != admission_fields:
                raise ContractError(f"attempt ledger row {index} has invalid admission receipt")
            if (admission.get("status") != "MOCK_ONLY_NEVER_PRODUCTION"
                    or admission.get("execution_class") != EXECUTION_MOCK):
                raise ContractError(
                    f"attempt ledger row {index} is not an explicit mock-only admission"
                )
            for field in ("authorization_sha256", "authorization_event_sha256",
                          "phase_event_sha256", "frozen_bundle_sha256"):
                require_sha256(admission.get(field), f"attempt row {index}.admission.{field}")
            if admission["frozen_bundle_sha256"] != row["frozen_bundle_sha256"]:
                raise ContractError(f"attempt ledger row {index} admission bundle mismatch")
            phase_started = parse_utc(admission.get("phase_started_at_utc"),
                                      f"attempt row {index}.phase_started_at_utc")
            admitted = parse_utc(admission.get("admitted_at_utc"),
                                 f"attempt row {index}.admitted_at_utc")
            evidence = row.get("provider_evidence")
            validate_provider_evidence(
                evidence, artifact_root=self.artifact_root,
                accepted=row["disposition"] == "accepted", operation_kind=kind,
                label_contract=row.get("label_contract"), task=row.get("task"),
            )
            expected_cost = _derive_mock_cost_evidence(
                evidence, execution_class=admission["execution_class"]
            )
            if row.get("cost_evidence") != expected_cost:
                raise ContractError(f"attempt ledger row {index} has non-derived cost evidence")
            started = parse_utc(evidence["started_at_utc"],
                                f"attempt row {index}.provider started")
            finished = parse_utc(evidence["finished_at_utc"],
                                 f"attempt row {index}.provider finished")
            if started < phase_started:
                raise ContractError(f"attempt ledger row {index} predates its authorized phase")
            if finished > admitted:
                raise ContractError(f"attempt ledger row {index} was admitted before evidence finished")
            _validate_attempt_operation_binding(row, f"attempt ledger row {index}")
            prior.append(row)
            if row["disposition"] in {"accepted", "terminal_failure"}:
                terminal_operations.add(operation_id)
        self._semantics_verified_stat = self._cache_stat
        return rows

    def _append_authorized(self, attempt: Mapping[str, Any],
                           capability: _AttemptAdmission) -> dict[str, Any]:
        if not isinstance(capability, _AttemptAdmission) or capability._sentinel is not _ADMISSION_SENTINEL:
            raise ContractError("production append requires an internal authorized capability")
        with self._lock:
            rows = self.verify()
            if len(rows) >= capability.max_attempts:
                raise ContractError("the authorized provider-attempt ceiling is exhausted")
            spent = sum((
                _decimal_money(row["cost_evidence"]["derived_cost_usd"],
                               "derived_cost_usd", positive=False)
                for row in rows
            ), Decimal("0"))
            payload = dict(attempt)
            caller_fields = {
                "attempt_id", "run_id", "operation_id", "operation_kind", "task",
                "repair_round", "attempt_no", "retry_of_attempt_id", "disposition",
                "protocol_lock_sha256", "prompt_plan_sha256", "corpus_sha256",
                "label_contract", "provider_evidence",
            }
            if set(payload) != caller_fields:
                raise ContractError("attempt fields must exactly match the production input contract")
            for forbidden in ("schema_version", "sequence", "previous_record_sha256",
                              "record_sha256", "admission", "frozen_bundle_sha256",
                              "charged_cost_usd", "cost_evidence"):
                if forbidden in payload:
                    raise ContractError(f"caller may not supply derived field {forbidden}")
            if not str(payload.get("attempt_id", "")).strip():
                raise ContractError("attempt_id must be non-empty")
            if any(row.get("attempt_id") == payload["attempt_id"] for row in rows):
                raise ContractError("attempt_id is already present")
            if not str(payload.get("run_id", "")).strip() or not str(
                payload.get("operation_id", "")
            ).strip():
                raise ContractError("run_id and operation_id must be non-empty")
            if payload.get("operation_kind") not in {"generation", "label"}:
                raise ContractError("operation_kind must be generation or label")
            if payload.get("disposition") not in ALLOWED_DISPOSITIONS:
                raise ContractError(f"disposition must be one of {sorted(ALLOWED_DISPOSITIONS)}")
            if not isinstance(payload.get("attempt_no"), int) or payload["attempt_no"] <= 0:
                raise ContractError("attempt_no must be a positive integer")
            if not isinstance(payload.get("repair_round"), int) or not 0 <= payload[
                "repair_round"
            ] <= 2:
                raise ContractError("repair_round must be 0, 1, or 2")
            if payload["operation_kind"] == "generation":
                if payload["repair_round"] != 0 or payload.get("task") is not None:
                    raise ContractError("generation attempts cannot be label repairs/tasks")
                if payload.get("corpus_sha256") is not None or payload.get("label_contract") is not None:
                    raise ContractError("generation attempts cannot claim label/corpus fields")
            else:
                if payload.get("task") not in ALLOWED_TASKS:
                    raise ContractError("label attempts require task board/change/user")
                require_sha256(payload.get("corpus_sha256"), "corpus_sha256")
                _validate_label_contract(payload.get("label_contract"), task=payload["task"])
            require_sha256(payload.get("protocol_lock_sha256"), "protocol_lock_sha256")
            require_sha256(payload.get("prompt_plan_sha256"), "prompt_plan_sha256")
            validate_provider_evidence(
                payload.get("provider_evidence"), artifact_root=self.artifact_root,
                accepted=payload["disposition"] == "accepted",
                operation_kind=payload["operation_kind"],
                label_contract=payload.get("label_contract"), task=payload.get("task"),
            )
            cost_evidence = _derive_mock_cost_evidence(
                payload["provider_evidence"],
                execution_class=capability.payload["execution_class"],
            )
            charge = _decimal_money(
                cost_evidence["derived_cost_usd"], "derived_cost_usd", positive=False
            )
            if spent + charge > capability.max_cost:
                raise ContractError("the authorized provider-cost ceiling would be exceeded")
            phase_started = parse_utc(capability.payload["phase_started_at_utc"],
                                      "admission.phase_started_at_utc")
            admitted = parse_utc(capability.payload["admitted_at_utc"],
                                 "admission.admitted_at_utc")
            started = parse_utc(payload["provider_evidence"]["started_at_utc"],
                                "provider_evidence.started_at_utc")
            finished = parse_utc(payload["provider_evidence"]["finished_at_utc"],
                                 "provider_evidence.finished_at_utc")
            if started < phase_started:
                raise ContractError("provider attempt predates its authorized phase")
            if finished > admitted:
                raise ContractError("provider attempt cannot be admitted before it finishes")
            payload["frozen_bundle_sha256"] = capability.payload["frozen_bundle_sha256"]
            payload["cost_evidence"] = cost_evidence
            payload["admission"] = dict(capability.payload)
            _validate_attempt_operation_binding(payload, "attempt")
            prior = [row for row in rows if row.get("operation_id") == payload["operation_id"]]
            if prior and prior[-1]["disposition"] in {"accepted", "terminal_failure"}:
                raise ContractError("operation is terminal; another attempt is forbidden")
            expected_no = len(prior) + 1
            if payload["attempt_no"] != expected_no:
                raise ContractError(f"attempt_no must be {expected_no} for this operation")
            expected_retry = prior[-1]["attempt_id"] if prior else None
            if payload.get("retry_of_attempt_id") != expected_retry:
                raise ContractError("retry_of_attempt_id must point to the immediately prior attempt")
            row = dict(payload)
            row["schema_version"] = SCHEMA_ATTEMPT
            row["sequence"] = len(rows)
            row["previous_record_sha256"] = rows[-1]["record_sha256"] if rows else None
            row["record_sha256"] = sha256_bytes(canonical_json_bytes(row))
            _append_jsonl_fsync(self.path, row)
            rows.append(row)
            self._cache = rows
            stat = self.path.stat()
            self._cache_stat = (stat.st_size, stat.st_mtime_ns)
            # Every semantic rule applied by verify() has been applied above to the new row,
            # while all prior rows came from the previously verified cache.
            self._semantics_verified_stat = self._cache_stat
            return row

    def verify_for_state(self, state: ExperimentState, *, force_chain: bool = True) -> list[dict[str, Any]]:
        expected_path = (state.run_dir / PRODUCTION_ATTEMPT_NAME).resolve()
        expected_artifacts = (state.run_dir / ARTIFACT_DIR_NAME).resolve()
        if self.path.resolve() != expected_path:
            raise ContractError("production completion requires the run's fixed attempt ledger path")
        if self.artifact_root is None or self.artifact_root.resolve() != expected_artifacts:
            raise ContractError("production completion requires the run's fixed artifact root")
        bundle = load_frozen_bundle(state)
        if state.execution_class != EXECUTION_MOCK:
            raise ContractError("production attempt verification is unavailable in this package")
        events = state.events()
        auth_events = [row for row in events if row["event_type"] == "MOCK_RUN_AUTHORIZED"]
        generation_events = [
            row for row in events if row["event_type"] == "MOCK_GENERATION_STARTED"
        ]
        if len(auth_events) != 1 or len(generation_events) != 1:
            raise ContractError("attempt ledger requires exactly one authority and generation-start event")
        auth_event = auth_events[0]
        generation_event = generation_events[0]
        labeling_events = [row for row in events if row["event_type"] == "MOCK_LABELING_STARTED"]
        seal_events = [row for row in events if row["event_type"] == "MOCK_CORPUS_SEALED"]
        rows = self.verify(force_chain=force_chain)
        total_cost = Decimal("0")
        plan_by_id = {
            row["conversation_id"]: row for row in bundle["prompt_plan"]["conversations"]
        }
        accepted_prior: dict[str, dict[str, Any]] = {}
        for index, row in enumerate(rows):
            if row["run_id"] != bundle["run_id"]:
                raise ContractError(f"attempt row {index} is bound to a different run")
            if row["protocol_lock_sha256"] != bundle["protocol_lock_sha256"]:
                raise ContractError(f"attempt row {index} is bound to a different protocol lock")
            if row["prompt_plan_sha256"] != bundle["prompt_plan_sha256"]:
                raise ContractError(f"attempt row {index} is bound to a different prompt plan")
            if row["frozen_bundle_sha256"] != bundle["frozen_bundle_sha256"]:
                raise ContractError(f"attempt row {index} is bound to a different frozen bundle")
            admission = row["admission"]
            if admission["authorization_sha256"] != auth_event["evidence"]["authorization_sha256"]:
                raise ContractError(f"attempt row {index} has a different authorization")
            if admission["authorization_event_sha256"] != auth_event["record_sha256"]:
                raise ContractError(f"attempt row {index} has a different authority event")
            if (admission["execution_class"] != EXECUTION_MOCK
                    or admission["status"] != "MOCK_ONLY_NEVER_PRODUCTION"):
                raise ContractError(f"attempt row {index} is not structurally mock-only")
            phase_event = generation_event
            if row["operation_kind"] == "generation":
                match = GENERATION_OPERATION_RE.fullmatch(row["operation_id"])
                if not match:
                    raise ContractError(f"attempt row {index} has malformed generation id")
                planned = plan_by_id.get(match.group(1))
                if planned is None:
                    raise ContractError(f"attempt row {index} is absent from frozen plan")
                validate_generation_request_artifact(
                    row["provider_evidence"], planned=planned,
                    turn_index=int(match.group(2)), accepted_prior=accepted_prior,
                    artifact_root=self.artifact_root,
                )
            if row["operation_kind"] == "label":
                if len(labeling_events) != 1 or len(seal_events) != 1:
                    raise ContractError("label attempts require exactly one seal and labeling event")
                phase_event = labeling_events[0]
                seal = verify_corpus_seal(state.run_dir)
                if row["corpus_sha256"] != seal["corpus_sha256"]:
                    raise ContractError(f"attempt row {index} names a different sealed corpus")
                if parse_utc(row["provider_evidence"]["started_at_utc"], "label start") <= parse_utc(
                    seal["sealed_at_utc"], "seal time"
                ):
                    raise ContractError(f"attempt row {index} label evidence predates the seal")
            if (admission["phase_event_sha256"] != phase_event["record_sha256"]
                    or admission["phase_started_at_utc"] != phase_event["occurred_at_utc"]):
                raise ContractError(f"attempt row {index} is bound to a different phase event")
            if parse_utc(admission["admitted_at_utc"], "admitted_at_utc") >= parse_utc(
                auth_event["evidence"]["expires_at_utc"], "authorization expiry"
            ):
                raise ContractError(f"attempt row {index} was admitted after authority expiry")
            total_cost += _decimal_money(
                row["cost_evidence"]["derived_cost_usd"], "derived_cost_usd",
                positive=False,
            )
            if row["operation_kind"] == "generation" and row["disposition"] == "accepted":
                accepted_prior[row["operation_id"]] = row
        if len(rows) > auth_event["evidence"]["max_provider_attempts"]:
            raise ContractError("attempt ledger exceeds the externally authorized attempt ceiling")
        if total_cost > _decimal_money(auth_event["evidence"]["max_cost_usd"],
                                       "max_cost_usd", positive=True):
            raise ContractError("attempt ledger exceeds the externally authorized cost ceiling")
        return rows

    def accepted_operations(self) -> dict[str, dict[str, Any]]:
        return {
            row["operation_id"]: row for row in self.verify()
            if row["disposition"] == "accepted"
        }

    def accepted_operations_for_state(self, state: ExperimentState) -> dict[str, dict[str, Any]]:
        return {
            row["operation_id"]: row for row in self.verify_for_state(state)
            if row["disposition"] == "accepted"
        }

    def incomplete_operations(self) -> set[str]:
        rows = self.verify()
        all_operations = {row["operation_id"] for row in rows}
        accepted = {row["operation_id"] for row in rows if row["disposition"] == "accepted"}
        return all_operations - accepted


def record_authorized_attempt(
    state: ExperimentState, ledger: AttemptLedger, attempt: Mapping[str, Any],
) -> dict[str, Any]:
    """Admit only explicit mock evidence; production admission is unavailable here."""
    if state.execution_class != EXECUTION_MOCK:
        raise ContractError(
            "PRODUCTION_ATTEMPT_ADMISSION_UNAVAILABLE: authenticated authority, usage, "
            "pricing, lock, and transport verifiers are absent"
        )
    bundle = load_frozen_bundle(state)
    events = state.events()
    auth_events = [row for row in events if row["event_type"] == "MOCK_RUN_AUTHORIZED"]
    if len(auth_events) != 1:
        raise ContractError("exactly one explicit mock-only authorization is required")
    auth_event = auth_events[0]
    authorization = auth_event["evidence"]
    admitted_at = state._trusted_now()
    if parse_utc(admitted_at, "admitted_at_utc") >= parse_utc(
        authorization["expires_at_utc"], "expires_at_utc"
    ):
        raise ContractError("the full-run authorization expired before this attempt")
    if attempt.get("run_id") != bundle["run_id"]:
        raise ContractError("attempt run_id does not match frozen state")
    if attempt.get("protocol_lock_sha256") != bundle["protocol_lock_sha256"]:
        raise ContractError("attempt protocol lock does not match frozen state")
    if attempt.get("prompt_plan_sha256") != bundle["prompt_plan_sha256"]:
        raise ContractError("attempt prompt plan does not match frozen state")
    if ledger.path.resolve() != (state.run_dir / PRODUCTION_ATTEMPT_NAME).resolve():
        raise ContractError("authorized attempts must use the fixed run ledger")
    if (ledger.artifact_root is None
            or ledger.artifact_root.resolve() != (state.run_dir / ARTIFACT_DIR_NAME).resolve()):
        raise ContractError("authorized attempts must use the fixed run artifact root")

    operation_kind = attempt.get("operation_kind")
    current = state.current()
    if operation_kind == "generation":
        if (state.phase != PHASE_MOCK_GENERATING
                or current["event_type"] != "MOCK_GENERATION_STARTED"):
            raise ContractError("mock generation attempt is forbidden outside MOCK_GENERATING")
        match = GENERATION_OPERATION_RE.fullmatch(str(attempt.get("operation_id", "")))
        if not match or int(match.group(2)) >= TURNS_PER_CONVERSATION:
            raise ContractError("generation attempt has an invalid operation id")
        planned = {row["conversation_id"]: row for row in bundle["prompt_plan"]["conversations"]}.get(
            match.group(1)
        )
        if planned is None:
            raise ContractError("generation attempt is not present in the frozen prompt plan")
        provider = attempt.get("provider_evidence") or {}
        if (provider.get("provider") != planned["generator"]["provider"]
                or provider.get("requested_model") != planned["generator"]["requested_model"]):
            raise ContractError("generation attempt uses a different frozen generator/model")
        if provider.get("transport_receipt", {}).get(
            "classification"
        ) != "MOCK_CAPTURE_ONLY_NEVER_PRODUCTION":
            raise ContractError("mock attempt requires a mock-only transport receipt")
        prior_rows = ledger.verify()
        accepted_prior = {
            row["operation_id"]: row for row in prior_rows
            if row["operation_kind"] == "generation" and row["disposition"] == "accepted"
        }
        validate_generation_request_artifact(
            provider, planned=planned, turn_index=int(match.group(2)),
            accepted_prior=accepted_prior, artifact_root=ledger.artifact_root,
        )
    elif operation_kind == "label":
        if state.phase != PHASE_MOCK_LABELING or current["event_type"] != "MOCK_LABELING_STARTED":
            raise ContractError("label attempt is forbidden before CORPUS_SEALED/LABELING")
        seal = verify_corpus_seal(state.run_dir)
        if attempt.get("corpus_sha256") != seal["corpus_sha256"]:
            raise ContractError("label attempt is not bound to the sealed corpus")
        if parse_utc((attempt.get("provider_evidence") or {}).get("started_at_utc"),
                     "label provider start") <= parse_utc(seal["sealed_at_utc"], "seal time"):
            raise ContractError("label provider evidence predates the corpus seal")
    else:
        raise ContractError("unknown attempt operation_kind")
    capability = _AttemptAdmission(
        _ADMISSION_SENTINEL,
        {
            "status": "MOCK_ONLY_NEVER_PRODUCTION",
            "authorization_sha256": authorization["authorization_sha256"],
            "authorization_event_sha256": auth_event["record_sha256"],
            "phase_event_sha256": current["record_sha256"],
            "phase_started_at_utc": current["occurred_at_utc"],
            "admitted_at_utc": admitted_at,
            "frozen_bundle_sha256": bundle["frozen_bundle_sha256"],
            "execution_class": EXECUTION_MOCK,
        },
        max_attempts=authorization["max_provider_attempts"],
        max_cost=_decimal_money(authorization["max_cost_usd"], "max_cost_usd", positive=True),
    )
    return ledger._append_authorized(attempt, capability)


def complete_generation_if_ready(state: ExperimentState, ledger: AttemptLedger) -> dict[str, Any]:
    if state.phase != PHASE_MOCK_GENERATING or state.execution_class != EXECUTION_MOCK:
        raise ContractError("offline generation can complete only from MOCK_GENERATING")
    bundle = load_frozen_bundle(state)
    plan = bundle["prompt_plan"]
    verified_records = ledger.verify_for_state(state, force_chain=True)
    if not verified_records:
        raise ContractError("generation cannot complete with an empty provider-attempt ledger")
    if any(row["operation_kind"] != "generation" for row in verified_records):
        raise ContractError("generation completion ledger already contains label operations")
    accepted = {
        row["operation_id"]: row for row in verified_records if row["disposition"] == "accepted"
    }
    expected = {
        generation_operation_id(row["conversation_id"], turn)
        for row in plan["conversations"] for turn in range(TURNS_PER_CONVERSATION)
    }
    accepted_generation = {
        operation_id for operation_id, record in accepted.items()
        if record["operation_kind"] == "generation"
    }
    if accepted_generation != expected:
        missing = sorted(expected - accepted_generation)
        extra = sorted(accepted_generation - expected)
        raise ContractError(
            f"generation is not complete: missing={len(missing)}, extra={len(extra)}"
        )
    for planned in plan["conversations"]:
        generator = planned["generator"]
        for turn in range(TURNS_PER_CONVERSATION):
            operation_id = generation_operation_id(planned["conversation_id"], turn)
            evidence = accepted[operation_id]["provider_evidence"]
            if (evidence["provider"] != generator["provider"]
                    or evidence["requested_model"] != generator["requested_model"]):
                raise ContractError(
                    f"{operation_id}: accepted attempt used the wrong frozen generator/model"
                )
    ledger_sha256 = sha256_file(ledger.path)
    current = state.current()
    return state._transition(PHASE_MOCK_GENERATION_COMPLETE, "MOCK_GENERATION_COMPLETED", {
        "run_id": bundle["run_id"],
        "protocol_lock_sha256": bundle["protocol_lock_sha256"],
        "prompt_plan_sha256": bundle["prompt_plan_sha256"],
        "frozen_bundle_sha256": bundle["frozen_bundle_sha256"],
        "authorization_sha256": current["evidence"]["authorization_sha256"],
        "accepted_generation_operations": len(accepted_generation),
        "expected_generation_operations": N_CONVERSATIONS * TURNS_PER_CONVERSATION,
        "attempt_ledger_tip_sha256": verified_records[-1]["record_sha256"],
        "attempt_ledger_sha256": ledger_sha256,
        "attempt_ledger_bytes": ledger.path.stat().st_size,
        "execution_class": EXECUTION_MOCK,
        "production_authorization_status": "NOT_AUTHORIZED",
    }, _permit=_STATE_TRANSITION_SENTINEL)


def validate_corpus_against_plan(
    corpus_rows: Sequence[Mapping[str, Any]], plan: Mapping[str, Any],
    accepted_generation: Mapping[str, Mapping[str, Any]], *, run_id: str,
    artifact_root: os.PathLike[str] | str,
) -> dict[str, Any]:
    plan_validation = validate_prompt_plan(plan)
    plan_rows = plan["conversations"]
    if len(corpus_rows) != N_CONVERSATIONS:
        raise ContractError(f"corpus must contain exactly {N_CONVERSATIONS} conversations")
    row_hashes: list[str] = []
    for index, (row, planned) in enumerate(zip(corpus_rows, plan_rows)):
        if row.get("schema_version") != SCHEMA_CORPUS or row.get("run_id") != run_id:
            raise ContractError(f"corpus row {index} schema/run mismatch")
        conversation_id = planned["conversation_id"]
        for field in ("conversation_id", "stratum", "family", "seed_prompt_sha256"):
            expected = planned[field]
            if row.get(field) != expected:
                raise ContractError(f"{conversation_id}: corpus {field} mismatch")
        if row.get("generator") != planned["generator"]:
            raise ContractError(f"{conversation_id}: corpus generator mismatch")
        turns = row.get("turns")
        if not isinstance(turns, list) or len(turns) != TURNS_PER_CONVERSATION:
            raise ContractError(f"{conversation_id}: corpus must contain exactly 10 turns")
        for turn_index, turn in enumerate(turns):
            if turn.get("turn_index") != turn_index:
                raise ContractError(f"{conversation_id}: turn index mismatch")
            expected_user = planned["seed_prompt"] if turn_index == 0 else planned[
                "followups"
            ][turn_index - 1]["text"]
            if turn.get("user_text") != expected_user or turn.get(
                "user_text_sha256"
            ) != sha256_text(expected_user):
                raise ContractError(f"{conversation_id}: user text mismatch at turn {turn_index}")
            assistant = turn.get("assistant_text")
            if not isinstance(assistant, str) or not assistant.strip():
                raise ContractError(f"{conversation_id}: empty assistant text at turn {turn_index}")
            if turn.get("assistant_text_sha256") != sha256_text(assistant):
                raise ContractError(f"{conversation_id}: assistant hash mismatch at turn {turn_index}")
            operation_id = generation_operation_id(conversation_id, turn_index)
            if turn.get("operation_id") != operation_id:
                raise ContractError(f"{conversation_id}: operation id mismatch at turn {turn_index}")
            accepted = accepted_generation.get(operation_id)
            if accepted is None or turn.get("attempt_record_sha256") != accepted[
                "record_sha256"
            ]:
                raise ContractError(f"{conversation_id}: unbound generation evidence at turn {turn_index}")
            extracted = extract_response_answer(
                accepted["provider_evidence"], artifact_root=artifact_root,
                operation_kind="generation",
            )["answer_text"]
            if assistant != extracted:
                raise ContractError(
                    f"{conversation_id}: corpus assistant text does not equal raw provider response "
                    f"at turn {turn_index}"
                )
        row_hashes.append(sha256_bytes(canonical_json_bytes(row)))
    return {
        "valid": True,
        "rows": len(corpus_rows),
        "turns": sum(len(row["turns"]) for row in corpus_rows),
        "row_sha256s": row_hashes,
        "prompt_plan_sha256": plan_validation["plan_sha256"],
    }


def seal_corpus(*, state: ExperimentState, ledger: AttemptLedger,
                corpus_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if (state.phase != PHASE_MOCK_GENERATION_COMPLETE
            or state.execution_class != EXECUTION_MOCK):
        raise ContractError("offline corpus sealing requires MOCK_GENERATION_COMPLETE")
    bundle = load_frozen_bundle(state)
    plan = bundle["prompt_plan"]
    records = ledger.verify_for_state(state, force_chain=True)
    if not records:
        raise ContractError("corpus sealing requires a non-empty production attempt ledger")
    if any(row["operation_kind"] == "label" for row in records):
        raise ContractError("label attempts already exist; corpus was not sealed before labels")
    audit_label_rows = [
        row for row in ledger.audit_records()
        if isinstance(row.get("payload"), dict)
        and row["payload"].get("operation_kind") == "label"
    ]
    if audit_label_rows:
        raise ContractError(
            "audit-imported label evidence exists before seal; prospectivity cannot be proven"
        )
    run_id = bundle["run_id"]
    accepted = {
        row["operation_id"]: row for row in records
        if row["disposition"] == "accepted"
        if row["operation_kind"] == "generation"
    }
    validation = validate_corpus_against_plan(
        corpus_rows, plan, accepted, run_id=run_id,
        artifact_root=ledger.artifact_root,
    )
    completion = state.current()
    completion_evidence = completion["evidence"]
    if (completion_evidence.get("run_id") != run_id
            or completion_evidence.get("protocol_lock_sha256") != bundle["protocol_lock_sha256"]
            or completion_evidence.get("prompt_plan_sha256") != bundle["prompt_plan_sha256"]
            or completion_evidence.get("frozen_bundle_sha256") != bundle["frozen_bundle_sha256"]
            or completion_evidence.get("attempt_ledger_tip_sha256") != records[-1]["record_sha256"]
            or completion_evidence.get("attempt_ledger_sha256") != sha256_file(ledger.path)
            or completion_evidence.get("attempt_ledger_bytes") != ledger.path.stat().st_size):
        raise ContractError("GENERATION_COMPLETE is not bound to the exact current run evidence")
    canonical_corpus = b"".join(canonical_json_bytes(row) + b"\n" for row in corpus_rows)
    corpus_sha256 = sha256_bytes(canonical_corpus)
    sealed_at = state._trusted_now()
    if parse_utc(sealed_at, "sealed_at_utc") <= parse_utc(
        completion["occurred_at_utc"], "generation completion time"
    ):
        raise ContractError("corpus seal must be later than generation completion")
    seal = {
        "schema_version": SCHEMA_SEAL,
        "protocol_id": PROTOCOL_ID,
        "run_id": run_id,
        "sealed_at_utc": sealed_at,
        "protocol_lock_sha256": bundle["protocol_lock_sha256"],
        "prompt_plan_sha256": bundle["prompt_plan_sha256"],
        "frozen_bundle_sha256": bundle["frozen_bundle_sha256"],
        "authorization_sha256": completion_evidence["authorization_sha256"],
        "generation_complete_state_event_sha256": completion["record_sha256"],
        "state_ledger_tip_before_seal_sha256": completion["record_sha256"],
        "attempt_ledger_tip_sha256": records[-1]["record_sha256"],
        "attempt_ledger_sha256": sha256_file(ledger.path),
        "attempt_ledger_bytes": ledger.path.stat().st_size,
        "corpus_sha256": corpus_sha256,
        "corpus_bytes": len(canonical_corpus),
        "conversation_count": N_CONVERSATIONS,
        "assistant_turn_count": N_CONVERSATIONS * TURNS_PER_CONVERSATION,
        "row_sha256s": validation["row_sha256s"],
        "labels_present_before_seal": False,
        "execution_class": EXECUTION_MOCK,
        "production_authorization_status": "NOT_AUTHORIZED",
    }
    seal["seal_sha256"] = sha256_bytes(canonical_json_bytes(seal))
    _write_once(state.run_dir / "corpus.sealed.jsonl", canonical_corpus)
    _write_once(state.run_dir / "corpus_seal.json", canonical_json_bytes(seal))
    state._transition(PHASE_MOCK_CORPUS_SEALED, "MOCK_CORPUS_SEALED", {
        "run_id": run_id,
        "protocol_lock_sha256": bundle["protocol_lock_sha256"],
        "prompt_plan_sha256": bundle["prompt_plan_sha256"],
        "frozen_bundle_sha256": bundle["frozen_bundle_sha256"],
        "authorization_sha256": completion_evidence["authorization_sha256"],
        "generation_complete_state_event_sha256": completion["record_sha256"],
        "attempt_ledger_tip_sha256": records[-1]["record_sha256"],
        "attempt_ledger_sha256": seal["attempt_ledger_sha256"],
        "corpus_sha256": corpus_sha256,
        "seal_sha256": seal["seal_sha256"],
        "labels_present_before_seal": False,
        "execution_class": EXECUTION_MOCK,
        "production_authorization_status": "NOT_AUTHORIZED",
    }, trusted_timestamp=sealed_at, _permit=_STATE_TRANSITION_SENTINEL)
    return seal


def verify_corpus_seal(run_dir: os.PathLike[str] | str) -> dict[str, Any]:
    root = Path(run_dir)
    state = ExperimentState(root)
    bundle = load_frozen_bundle(state)
    events = state.events()
    seal = load_json(root / "corpus_seal.json")
    claimed = seal.get("seal_sha256")
    require_sha256(claimed, "seal_sha256")
    unsigned = dict(seal)
    unsigned.pop("seal_sha256", None)
    if sha256_bytes(canonical_json_bytes(unsigned)) != claimed:
        raise ContractError("corpus seal record hash mismatch")
    corpus_path = root / "corpus.sealed.jsonl"
    if sha256_file(corpus_path) != seal.get("corpus_sha256"):
        raise ContractError("sealed corpus bytes no longer match the seal")
    if corpus_path.stat().st_size != seal.get("corpus_bytes"):
        raise ContractError("sealed corpus size no longer matches the seal")
    seal_events = [row for row in events if row["event_type"] == "MOCK_CORPUS_SEALED"]
    if len(seal_events) != 1:
        raise ContractError("state ledger must contain exactly one CORPUS_SEALED event")
    event = seal_events[0]
    if (seal.get("run_id") != bundle["run_id"]
            or seal.get("protocol_lock_sha256") != bundle["protocol_lock_sha256"]
            or seal.get("prompt_plan_sha256") != bundle["prompt_plan_sha256"]
            or seal.get("frozen_bundle_sha256") != bundle["frozen_bundle_sha256"]):
        raise ContractError("corpus seal is bound to a different frozen run")
    if (event.get("occurred_at_utc") != seal.get("sealed_at_utc")
            or event.get("evidence", {}).get("seal_sha256") != claimed
            or event.get("evidence", {}).get("corpus_sha256") != seal.get("corpus_sha256")
            or seal.get("state_ledger_tip_before_seal_sha256") != event.get(
                "previous_record_sha256"
            )
            or seal.get("generation_complete_state_event_sha256") != event.get(
                "previous_record_sha256"
            )):
        raise ContractError("corpus seal and state-event chronology/bindings disagree")
    ledger_path = root / PRODUCTION_ATTEMPT_NAME
    sealed_ledger_bytes = seal.get("attempt_ledger_bytes")
    if (not ledger_path.is_file() or not isinstance(sealed_ledger_bytes, int)
            or ledger_path.stat().st_size < sealed_ledger_bytes
            or sha256_file_prefix(ledger_path, sealed_ledger_bytes) != seal.get(
                "attempt_ledger_sha256"
            )):
        raise ContractError("corpus seal no longer matches the sealed generation-ledger prefix")
    return {
        "valid": True,
        "run_id": seal["run_id"],
        "sealed_at_utc": seal["sealed_at_utc"],
        "corpus_sha256": seal["corpus_sha256"],
        "seal_sha256": claimed,
        "protocol_lock_sha256": seal["protocol_lock_sha256"],
        "prompt_plan_sha256": seal["prompt_plan_sha256"],
        "frozen_bundle_sha256": seal["frozen_bundle_sha256"],
        "execution_class": seal["execution_class"],
        "production_authorization_status": seal["production_authorization_status"],
    }


def start_labeling(state: ExperimentState) -> dict[str, Any]:
    if state.phase != PHASE_MOCK_CORPUS_SEALED or state.execution_class != EXECUTION_MOCK:
        raise ContractError("offline labeling can start only from MOCK_CORPUS_SEALED")
    verified = verify_corpus_seal(state.run_dir)
    return state._transition(
        PHASE_MOCK_LABELING, "MOCK_LABELING_STARTED", verified,
        _permit=_STATE_TRANSITION_SENTINEL,
    )


def f1_change(y_true: Sequence[int], y_pred: Sequence[int]) -> float:
    if len(y_true) != len(y_pred):
        raise ContractError("metric inputs have different lengths")
    tp = sum(1 for y, p in zip(y_true, y_pred) if y == 1 and p == 1)
    fp = sum(1 for y, p in zip(y_true, y_pred) if y == 0 and p == 1)
    fn = sum(1 for y, p in zip(y_true, y_pred) if y == 1 and p == 0)
    denominator = 2 * tp + fp + fn
    return (2 * tp / denominator) if denominator else 0.0


def _default_loco_claim2_predictor(
    features: Sequence[str], labels: Sequence[int], groups: Sequence[str]
) -> list[int]:
    """Fit P1 (`b_N` only) from scratch in every leave-one-conversation-out fold."""
    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import OneHotEncoder
    except ImportError as exc:  # pragma: no cover - explicit environment failure
        raise ContractError("numpy and scikit-learn are required for Claim-2 analysis") from exc

    unique_groups = sorted(set(groups))
    if len(unique_groups) < 2:
        raise ContractError("Claim-2 LOCO needs at least two conversations")
    predictions: list[int | None] = [None] * len(labels)
    for held_out in unique_groups:
        train = [i for i, group in enumerate(groups) if group != held_out]
        test = [i for i, group in enumerate(groups) if group == held_out]
        train_labels = [int(labels[i]) for i in train]
        if len(set(train_labels)) == 1:
            fold_predictions = [train_labels[0]] * len(test)
        else:
            encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
            train_matrix = encoder.fit_transform([[features[i]] for i in train])
            test_matrix = encoder.transform([[features[i]] for i in test])
            model = LogisticRegression(
                C=1.0, max_iter=500, random_state=42, solver="liblinear"
            )
            model.fit(np.asarray(train_matrix), np.asarray(train_labels))
            fold_predictions = [int(x) for x in model.predict(np.asarray(test_matrix))]
        for index, prediction in zip(test, fold_predictions):
            predictions[index] = prediction
    if any(value is None for value in predictions):
        raise ContractError("Claim-2 LOCO did not predict every row")
    return [int(value) for value in predictions]


def block_permute_labels(labels: Sequence[int], groups: Sequence[str], rng: Random) -> list[int]:
    if len(labels) != len(groups):
        raise ContractError("labels and groups have different lengths")
    permuted = list(labels)
    indices: dict[str, list[int]] = defaultdict(list)
    for index, group in enumerate(groups):
        indices[str(group)].append(index)
    for positions in indices.values():
        values = [labels[index] for index in positions]
        rng.shuffle(values)
        for index, value in zip(positions, values):
            permuted[index] = int(value)
    return permuted


Predictor = Callable[[Sequence[str], Sequence[int], Sequence[str]], Sequence[int]]


def claim2_refit_permutation(
    rows: Sequence[Mapping[str, Any]], *, trials: int = CLAIM2_TRIALS,
    seed: int = CLAIM2_SEED, predictor: Predictor | None = None,
    learner_id: str = CLAIM2_LEARNER_ID,
) -> dict[str, Any]:
    """Run Claim 2's null with a fresh learner fit on every permuted outcome.

    A precomputed prediction vector is intentionally not accepted by this API.  Each
    null trial block-permutes outcomes within conversations and calls ``predictor`` with
    those permuted outcomes, forcing the complete learner to be refit before scoring.
    """
    if trials != CLAIM2_TRIALS:
        raise ContractError(f"Claim-2 trials are preregistered at exactly {CLAIM2_TRIALS}")
    if seed != CLAIM2_SEED:
        raise ContractError(f"Claim-2 seed is preregistered at exactly {CLAIM2_SEED}")
    if predictor is not None:
        raise ContractError("Claim-2 claim-bearing entrypoint forbids injected predictors")
    if learner_id != CLAIM2_LEARNER_ID:
        raise ContractError("Claim-2 learner_id is fixed by preregistration")
    if len(rows) < 4:
        raise ContractError("Claim-2 permutation needs at least four rows")
    features: list[str] = []
    labels: list[int] = []
    groups: list[str] = []
    for index, row in enumerate(rows):
        feature = row.get("b_N")
        label = row.get("gt_change")
        group = row.get("conv_id")
        if feature not in {"B0", "B1", "B2", "B3", "B4", "B5"}:
            raise ContractError(f"row {index}: invalid b_N")
        if label not in {0, 1, False, True}:
            raise ContractError(f"row {index}: gt_change must be binary")
        if not str(group).strip():
            raise ContractError(f"row {index}: conv_id must be non-empty")
        features.append(str(feature))
        labels.append(int(label))
        groups.append(str(group))
    if len(set(groups)) < 2 or len(set(labels)) < 2:
        raise ContractError("Claim-2 permutation needs at least two groups and both classes")

    real_predictions = list(_default_loco_claim2_predictor(features, labels, groups))
    if len(real_predictions) != len(labels):
        raise ContractError("predictor returned the wrong number of real predictions")
    if any(value not in {0, 1} or isinstance(value, bool) for value in real_predictions):
        raise ContractError("Claim-2 learner returned non-binary real predictions")
    real = f1_change(labels, real_predictions)
    rng = Random(seed)
    null_scores: list[float] = []
    null_input_hashes: list[str] = []
    for _ in range(trials):
        permuted = block_permute_labels(labels, groups, rng)
        # This call is the load-bearing v2 repair: no real-data predictions are reused.
        permuted_predictions = list(_default_loco_claim2_predictor(features, permuted, groups))
        if len(permuted_predictions) != len(permuted):
            raise ContractError("predictor returned the wrong number of null predictions")
        if any(value not in {0, 1} or isinstance(value, bool) for value in permuted_predictions):
            raise ContractError("Claim-2 learner returned non-binary null predictions")
        null_scores.append(f1_change(permuted, permuted_predictions))
        null_input_hashes.append(sha256_bytes(canonical_json_bytes(permuted)))

    ordered = sorted(null_scores)
    def percentile(p: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        position = (len(ordered) - 1) * p
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[lower]
        weight = position - lower
        return ordered[lower] * (1 - weight) + ordered[upper] * weight

    empirical_p = (sum(score >= real for score in null_scores) + 1) / (trials + 1)
    return {
        "schema_version": SCHEMA_PERMUTATION,
        "claim_status": "NOT_CLAIM_ELIGIBLE_UNTIL_SEALED_LABEL_GATE0_BINDING",
        "algorithm": "WITHIN_CONVERSATION_BLOCK_PERMUTATION_REFIT_EVERY_TRIAL",
        "learner_id": learner_id,
        "learner_contract": {
            "features": ["b_N"],
            "outer_split": "leave-one-conversation-out",
            "logistic_C": 1.0,
            "random_state": 42,
            "refit_on_every_permuted_outcome": True,
        },
        "trials": trials,
        "seed": seed,
        "learner_invocations": trials + 1,
        "null_refit_invocations": trials,
        "real_change_f1": real,
        "null_mean": sum(null_scores) / len(null_scores),
        "null_p95": percentile(0.95),
        "null_p99": percentile(0.99),
        "empirical_p": empirical_p,
        "null_scores": null_scores,
        "null_label_vector_sha256s": null_input_hashes,
        "analysis_input_sha256": sha256_bytes(canonical_json_bytes(list(rows))),
    }
