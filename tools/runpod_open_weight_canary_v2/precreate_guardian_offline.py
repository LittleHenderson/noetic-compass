"""Offline reference state machine for a pre-create RunPod cost guardian.

This module deliberately contains no HTTP, GitHub, subprocess, model, create,
delete, or credential implementation.  A future independent GitHub workflow
must supply an adapter that can only inventory Pods, GET one Pod, and STOP one
Pod.  The create-capable launcher is a separate trust domain.

The guardian closes one operational gap: after a durable arm acknowledgement,
it can recover a newly created Pod's ID by its high-entropy exact name if the
launcher crashes after POST /v1/pods and before retaining the HTTP 201 body.
Its receipts are self-hashed observations, not RunPod signatures, proof of the
request actually sent, or billing-settlement evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import secrets
from typing import Any, Callable, Protocol


ARM_SCHEMA = "cas_runpod_precreate_guardian_arm.v1"
BINDING_SCHEMA = "cas_runpod_precreate_guardian_binding.v1"
TERMINAL_SCHEMA = "cas_runpod_precreate_guardian_terminal.v1"
CREATE_ENDPOINT = "https://rest.runpod.io/v1/pods"
PROTECTED_POD_IDS = frozenset({"q2oqlooejhin7s", "hilj2rzs54gi06"})
POD_ID_PATTERN = re.compile(r"^[a-z0-9]{6,32}$")
POD_NAME_PATTERN = re.compile(
    r"^cas-open-weight-canary-v2-[a-z0-9]+(?:-[a-z0-9]+)*-[0-9a-f]{32}$"
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SOURCE_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
OCI_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MAX_REQUEST_BYTES = 1_000_000
MAX_CREATION_WINDOW_SECONDS = 300
MAX_ARM_TO_DEADLINE_SECONDS = 2_100
MAX_POD_RUN_SECONDS = 1_800
MAX_PROVIDER_CLOCK_SKEW_SECONDS = 30
DEFAULT_STOP_LEAD_SECONDS = 90
DEFAULT_TERMINAL_TIMEOUT_SECONDS = 600


class GuardianError(RuntimeError):
    """Base class for a fail-closed guardian decision."""


class AmbiguousTargetError(GuardianError):
    """The inventory cannot identify exactly one safe target."""


class ProtectedTargetError(GuardianError):
    """The only name-matched target has a protected ID."""


class DeadlineError(GuardianError):
    """A required action can no longer occur by the bound deadline."""


class ProviderAdapter(Protocol):
    """Minimum guardian authority.  There is intentionally no create/delete."""

    def list_pods(self) -> list[dict[str, Any]]: ...

    def get_pod(self, pod_id: str) -> dict[str, Any]: ...

    def stop_pod(self, pod_id: str) -> int: ...


class Clock(Protocol):
    def now(self) -> datetime: ...

    def sleep(self, seconds: float) -> None: ...


@dataclass(frozen=True)
class ArmSpec:
    pod_name: str
    exact_create_request_sha256: str
    source_commit_sha: str
    oci_image_digest: str
    creation_window_start_utc: str
    creation_window_end_utc: str
    hard_stop_deadline_utc: str
    github_repository: str
    github_run_id: str
    github_run_attempt: str
    github_sha: str
    provider_create_endpoint: str = CREATE_ENDPOINT


@dataclass(frozen=True)
class GuardianResult:
    binding_receipt: dict[str, Any] | None
    terminal_receipt: dict[str, Any]


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("UTC timestamp must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("UTC timestamp must contain an offset")
    return parsed.astimezone(timezone.utc)


def _parse_provider_utc(value: str) -> datetime:
    legacy = re.fullmatch(
        r"(?P<date>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) "
        r"(?P<offset>[+-]\d{4}) UTC",
        value,
    )
    if legacy:
        return datetime.strptime(
            f"{legacy.group('date')} {legacy.group('offset')}",
            "%Y-%m-%d %H:%M:%S.%f %z",
        ).astimezone(timezone.utc)
    return _parse_utc(value)


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("datetime must contain an offset")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _strict_json_object(raw: bytes, label: str) -> dict[str, Any]:
    if len(raw) > MAX_REQUEST_BYTES:
        raise ValueError(f"{label} exceeds the size limit")
    duplicate: str | None = None

    def admit_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        nonlocal duplicate
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                duplicate = key
            value[key] = item
        return value

    def reject_constant(value: str) -> None:
        raise ValueError(f"{label} contains non-finite constant {value}")

    def admit_float(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError(f"{label} contains a non-finite number")
        return parsed

    try:
        parsed = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=admit_pairs,
            parse_constant=reject_constant,
            parse_float=admit_float,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"{label} is not strict UTF-8 JSON") from error
    if duplicate is not None:
        raise ValueError(f"{label} contains duplicate key {duplicate!r}")
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must be a JSON object")
    return parsed


def _seal_receipt(unsigned: dict[str, Any]) -> dict[str, Any]:
    if "receipt_sha256" in unsigned:
        raise ValueError("unsigned receipt already contains receipt_sha256")
    sealed = dict(unsigned)
    sealed["receipt_sha256"] = sha256_hex(canonical_json_bytes(unsigned))
    return sealed


def _verify_receipt(receipt: dict[str, Any], schema: str) -> dict[str, Any]:
    if not isinstance(receipt, dict) or receipt.get("schema_version") != schema:
        raise ValueError(f"expected {schema}")
    claimed = receipt.get("receipt_sha256")
    if not isinstance(claimed, str) or not SHA256_PATTERN.fullmatch(claimed):
        raise ValueError("receipt SHA-256 is absent or malformed")
    unsigned = dict(receipt)
    del unsigned["receipt_sha256"]
    if sha256_hex(canonical_json_bytes(unsigned)) != claimed:
        raise ValueError("receipt self-hash mismatch")
    return unsigned


def _validate_arm_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    arm = _verify_receipt(receipt, ARM_SCHEMA)
    expected_keys = {
        "claim_boundary",
        "creation_window_end_utc",
        "creation_window_start_utc",
        "delete_attempted",
        "exact_create_request_sha256",
        "github_repository",
        "github_run_attempt",
        "github_run_id",
        "github_sha",
        "guardian_source_sha256",
        "hard_stop_deadline_utc",
        "oci_image_digest",
        "pod_name",
        "pre_arm_inventory_count",
        "pre_arm_inventory_observed_at_utc",
        "pre_arm_inventory_projection",
        "pre_arm_inventory_sha256",
        "protected_pod_ids",
        "provider_create_endpoint",
        "schema_version",
        "source_commit_sha",
        "status",
    }
    if set(arm) != expected_keys:
        raise ValueError("arm receipt keyset mismatch")
    if arm["status"] != "ARMED_NAME_ABSENT_AND_POLLING_REQUIRED":
        raise ValueError("arm receipt status mismatch")
    if arm["delete_attempted"] is not False:
        raise ValueError("arm receipt reports a forbidden delete attempt")
    if arm["protected_pod_ids"] != sorted(PROTECTED_POD_IDS):
        raise ValueError("arm receipt protected-ID set mismatch")
    if arm["provider_create_endpoint"] != CREATE_ENDPOINT:
        raise ValueError("arm receipt provider endpoint mismatch")
    if not isinstance(arm["pod_name"], str) or not POD_NAME_PATTERN.fullmatch(
        arm["pod_name"]
    ):
        raise ValueError("arm receipt Pod name mismatch")
    if not isinstance(arm["exact_create_request_sha256"], str) or not SHA256_PATTERN.fullmatch(
        arm["exact_create_request_sha256"]
    ):
        raise ValueError("arm receipt request hash mismatch")
    if not isinstance(arm["source_commit_sha"], str) or not SOURCE_COMMIT_PATTERN.fullmatch(
        arm["source_commit_sha"]
    ):
        raise ValueError("arm receipt source commit mismatch")
    if arm["github_sha"] != arm["source_commit_sha"]:
        raise ValueError("arm receipt GitHub SHA mismatch")
    if not isinstance(arm["oci_image_digest"], str) or not OCI_DIGEST_PATTERN.fullmatch(
        arm["oci_image_digest"]
    ):
        raise ValueError("arm receipt OCI digest mismatch")
    if not isinstance(arm["github_repository"], str) or not REPOSITORY_PATTERN.fullmatch(
        arm["github_repository"]
    ):
        raise ValueError("arm receipt GitHub repository mismatch")
    if not all(
        isinstance(arm[key], str) and arm[key].isdecimal()
        for key in ("github_run_id", "github_run_attempt")
    ):
        raise ValueError("arm receipt GitHub run identity mismatch")
    if not isinstance(arm["guardian_source_sha256"], str) or not SHA256_PATTERN.fullmatch(
        arm["guardian_source_sha256"]
    ):
        raise ValueError("arm receipt guardian source hash mismatch")
    observed = _parse_utc(str(arm["pre_arm_inventory_observed_at_utc"]))
    start = _parse_utc(str(arm["creation_window_start_utc"]))
    end = _parse_utc(str(arm["creation_window_end_utc"]))
    deadline = _parse_utc(str(arm["hard_stop_deadline_utc"]))
    if not observed <= start < end < deadline:
        raise ValueError("arm receipt time ordering mismatch")
    if (end - start).total_seconds() > MAX_CREATION_WINDOW_SECONDS:
        raise ValueError("arm receipt creation window exceeds five minutes")
    if (deadline - observed).total_seconds() > MAX_ARM_TO_DEADLINE_SECONDS:
        raise ValueError("arm receipt deadline exceeds 35 minutes")
    if deadline > start + timedelta(seconds=MAX_POD_RUN_SECONDS):
        raise ValueError("arm receipt deadline exceeds 30 minutes from window start")
    projection = _validate_inventory(arm["pre_arm_inventory_projection"])
    if any(set(item) != {"id", "name"} for item in projection):
        raise ValueError("arm receipt inventory projection contains extra fields")
    if (
        type(arm["pre_arm_inventory_count"]) is not int
        or arm["pre_arm_inventory_count"] != len(projection)
    ):
        raise ValueError("arm receipt inventory count mismatch")
    if arm["pre_arm_inventory_sha256"] != sha256_hex(
        canonical_json_bytes(projection)
    ):
        raise ValueError("arm receipt inventory hash mismatch")
    if any(item["name"] == arm["pod_name"] for item in projection):
        raise ValueError("arm receipt projection contains the armed Pod name")
    return arm


def _validate_binding_receipt(
    binding_receipt: dict[str, Any], arm_receipt: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    arm = _validate_arm_receipt(arm_receipt)
    binding = _verify_receipt(binding_receipt, BINDING_SCHEMA)
    expected_keys = {
        "arm_receipt_sha256",
        "bound_at_utc",
        "claim_boundary",
        "delete_attempted",
        "hard_stop_deadline_utc",
        "inventory_sha256",
        "pod_id",
        "pod_name_at_binding",
        "pod_snapshot_sha256",
        "protected_pod_ids",
        "provider_birth_times_utc",
        "schema_version",
        "status",
    }
    if set(binding) != expected_keys:
        raise ValueError("binding receipt keyset mismatch")
    if binding["status"] != "UNIQUE_NEW_IN_WINDOW_ID_BOUND":
        raise ValueError("binding receipt status mismatch")
    if binding["delete_attempted"] is not False:
        raise ValueError("binding receipt reports a forbidden delete attempt")
    if binding["arm_receipt_sha256"] != arm_receipt["receipt_sha256"]:
        raise ValueError("binding receipt does not cross-link the supplied arm receipt")
    binding_deadline = _parse_utc(str(binding["hard_stop_deadline_utc"]))
    armed_deadline = _parse_utc(str(arm["hard_stop_deadline_utc"]))
    if binding_deadline > armed_deadline:
        raise ValueError("binding receipt extended the armed hard-stop deadline")
    if binding["pod_name_at_binding"] != arm["pod_name"]:
        raise ValueError("binding receipt changed the armed Pod name")
    pod_id = binding["pod_id"]
    if not isinstance(pod_id, str) or not POD_ID_PATTERN.fullmatch(pod_id):
        raise ValueError("binding receipt Pod ID mismatch")
    if pod_id in {item["id"] for item in arm["pre_arm_inventory_projection"]}:
        raise ValueError("binding receipt uses a pre-arm Pod ID")
    if pod_id in PROTECTED_POD_IDS:
        raise ProtectedTargetError("binding receipt uses a protected Pod ID")
    if binding["protected_pod_ids"] != sorted(PROTECTED_POD_IDS):
        raise ValueError("binding receipt protected-ID set mismatch")
    if not all(
        isinstance(binding[key], str) and SHA256_PATTERN.fullmatch(binding[key])
        for key in ("inventory_sha256", "pod_snapshot_sha256")
    ):
        raise ValueError("binding receipt observation hash mismatch")
    bound_at = _parse_utc(str(binding["bound_at_utc"]))
    if bound_at > binding_deadline:
        raise DeadlineError("binding receipt was first observed after the deadline")
    birth_times = binding["provider_birth_times_utc"]
    if not isinstance(birth_times, dict) or not birth_times:
        raise ValueError("binding receipt provider birth time is absent")
    if not set(birth_times).issubset({"createdAt", "lastStartedAt"}):
        raise ValueError("binding receipt provider birth time field mismatch")
    start = _parse_utc(str(arm["creation_window_start_utc"]))
    end = _parse_utc(str(arm["creation_window_end_utc"]))
    if any(
        not isinstance(value, str) or not start <= _parse_provider_utc(value) <= end
        for value in birth_times.values()
    ):
        raise ValueError("binding receipt provider birth time is outside the window")
    provider_birth = min(_parse_provider_utc(value) for value in birth_times.values())
    pre_arm_observed = _parse_utc(str(arm["pre_arm_inventory_observed_at_utc"]))
    if bound_at < max(start, pre_arm_observed) or (
        bound_at + timedelta(seconds=MAX_PROVIDER_CLOCK_SKEW_SECONDS)
        < provider_birth
    ):
        raise ValueError("binding receipt chronology precedes arm or provider birth")
    expected_deadline = min(
        armed_deadline, provider_birth + timedelta(seconds=MAX_POD_RUN_SECONDS)
    )
    if binding_deadline != expected_deadline:
        raise ValueError("binding receipt hard-stop deadline is not birth-time bounded")
    return arm, binding


def generate_pod_name(now: datetime, *, entropy_hex: str | None = None) -> str:
    """Generate a name with a 128-bit random suffix; caller retains exact bytes."""

    entropy = entropy_hex if entropy_hex is not None else secrets.token_hex(16)
    if not re.fullmatch(r"[0-9a-f]{32}", entropy):
        raise ValueError("pod-name entropy must be exactly 128 lowercase hex bits")
    stamp = now.astimezone(timezone.utc).strftime("%Y%m%dt%H%M%S%fZ").lower()
    return f"cas-open-weight-canary-v2-{stamp}-{entropy}"


def _validate_inventory(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("provider inventory must be a list")
    admitted: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("provider inventory contains a non-object")
        pod_id = item.get("id")
        name = item.get("name")
        if not isinstance(pod_id, str) or not POD_ID_PATTERN.fullmatch(pod_id):
            raise ValueError("provider inventory contains a malformed Pod ID")
        if not isinstance(name, str):
            raise ValueError("provider inventory contains a malformed Pod name")
        if pod_id in seen_ids:
            raise ValueError("provider inventory contains a duplicate Pod ID")
        seen_ids.add(pod_id)
        admitted.append(dict(item))
    return admitted


def _validate_spec(
    spec: ArmSpec, *, exact_create_request_bytes: bytes, armed_at: datetime
) -> tuple[datetime, datetime, datetime]:
    if not POD_NAME_PATTERN.fullmatch(spec.pod_name):
        raise ValueError("pod name must end in an exact 128-bit lowercase-hex suffix")
    if not SHA256_PATTERN.fullmatch(spec.exact_create_request_sha256):
        raise ValueError("create-request SHA-256 is malformed")
    if sha256_hex(exact_create_request_bytes) != spec.exact_create_request_sha256:
        raise ValueError("exact create-request bytes do not match the bound SHA-256")
    request = _strict_json_object(exact_create_request_bytes, "exact create request")
    if request.get("name") != spec.pod_name:
        raise ValueError("exact create request does not contain the bound Pod name")
    if not SOURCE_COMMIT_PATTERN.fullmatch(spec.source_commit_sha):
        raise ValueError("source commit must be an exact lowercase 40-character SHA")
    if spec.github_sha != spec.source_commit_sha:
        raise ValueError("GitHub SHA does not match the source commit")
    if not OCI_DIGEST_PATTERN.fullmatch(spec.oci_image_digest):
        raise ValueError("OCI image must be bound by an exact sha256 digest")
    if not REPOSITORY_PATTERN.fullmatch(spec.github_repository):
        raise ValueError("GitHub repository must be owner/name")
    if not spec.github_run_id.isdecimal() or not spec.github_run_attempt.isdecimal():
        raise ValueError("GitHub run identity must be decimal")
    if spec.provider_create_endpoint != CREATE_ENDPOINT:
        raise ValueError("provider create endpoint is not the frozen RunPod endpoint")
    start = _parse_utc(spec.creation_window_start_utc)
    end = _parse_utc(spec.creation_window_end_utc)
    deadline = _parse_utc(spec.hard_stop_deadline_utc)
    armed = armed_at.astimezone(timezone.utc)
    if not armed <= start < end < deadline:
        raise ValueError("guardian must arm before a non-empty creation window and deadline")
    if (end - start).total_seconds() > MAX_CREATION_WINDOW_SECONDS:
        raise ValueError("creation window exceeds five minutes")
    if (deadline - armed).total_seconds() > MAX_ARM_TO_DEADLINE_SECONDS:
        raise ValueError("hard-stop deadline is more than 35 minutes after arm")
    if deadline > start + timedelta(seconds=MAX_POD_RUN_SECONDS):
        raise ValueError("hard-stop deadline exceeds 30 minutes from window start")
    return start, end, deadline


def arm_guardian(
    spec: ArmSpec,
    *,
    exact_create_request_bytes: bytes,
    provider: ProviderAdapter,
    armed_at: datetime,
) -> dict[str, Any]:
    """Take the pre-create inventory and return the launcher's arm acknowledgement."""

    _validate_spec(
        spec, exact_create_request_bytes=exact_create_request_bytes, armed_at=armed_at
    )
    inventory = _validate_inventory(provider.list_pods())
    if any(item["name"] == spec.pod_name for item in inventory):
        raise AmbiguousTargetError("bound Pod name was present before guardian arm")
    inventory_projection = sorted(
        ({"id": item["id"], "name": item["name"]} for item in inventory),
        key=lambda item: (item["id"], item["name"]),
    )
    unsigned = {
        "claim_boundary": (
            "Self-hashed GitHub-side inventory observation and containment intent; "
            "not a RunPod signature, proof of the create bytes sent, or billing evidence."
        ),
        "creation_window_end_utc": spec.creation_window_end_utc,
        "creation_window_start_utc": spec.creation_window_start_utc,
        "delete_attempted": False,
        "exact_create_request_sha256": spec.exact_create_request_sha256,
        "github_repository": spec.github_repository,
        "github_run_attempt": spec.github_run_attempt,
        "github_run_id": spec.github_run_id,
        "github_sha": spec.github_sha,
        "guardian_source_sha256": sha256_hex(Path(__file__).read_bytes()),
        "hard_stop_deadline_utc": spec.hard_stop_deadline_utc,
        "oci_image_digest": spec.oci_image_digest,
        "pod_name": spec.pod_name,
        "pre_arm_inventory_count": len(inventory_projection),
        "pre_arm_inventory_observed_at_utc": _iso_utc(armed_at),
        "pre_arm_inventory_projection": inventory_projection,
        "pre_arm_inventory_sha256": sha256_hex(
            canonical_json_bytes(inventory_projection)
        ),
        "protected_pod_ids": sorted(PROTECTED_POD_IDS),
        "provider_create_endpoint": spec.provider_create_endpoint,
        "schema_version": ARM_SCHEMA,
        "source_commit_sha": spec.source_commit_sha,
        "status": "ARMED_NAME_ABSENT_AND_POLLING_REQUIRED",
    }
    return _seal_receipt(unsigned)


def discover_candidate(
    arm_receipt: dict[str, Any],
    *,
    inventory: list[dict[str, Any]],
    observed_at: datetime,
) -> dict[str, Any] | None:
    """Bind one new ID only from a unique, in-window exact-name observation."""

    arm = _validate_arm_receipt(arm_receipt)
    deadline = _parse_utc(str(arm["hard_stop_deadline_utc"]))
    observed_utc = observed_at.astimezone(timezone.utc)
    if observed_utc > deadline:
        raise DeadlineError("candidate cannot first bind after the hard-stop deadline")
    admitted = _validate_inventory(inventory)
    matches = [item for item in admitted if item["name"] == arm["pod_name"]]
    if not matches:
        return None
    if len(matches) != 1:
        raise AmbiguousTargetError("exact Pod name is not unique in provider inventory")
    candidate = matches[0]
    pod_id = candidate["id"]
    pre_ids = {item["id"] for item in arm["pre_arm_inventory_projection"]}
    if pod_id in pre_ids:
        raise AmbiguousTargetError("name-matched Pod ID existed in the pre-arm inventory")
    if pod_id in PROTECTED_POD_IDS or pod_id in set(arm["protected_pod_ids"]):
        raise ProtectedTargetError("name-matched Pod ID is protected")
    window_start = _parse_utc(str(arm["creation_window_start_utc"]))
    window_end = _parse_utc(str(arm["creation_window_end_utc"]))
    provider_birth_times: dict[str, str] = {}
    for field in ("createdAt", "lastStartedAt"):
        raw = candidate.get(field)
        if raw is None:
            continue
        if not isinstance(raw, str):
            raise AmbiguousTargetError(f"name-matched Pod has malformed {field}")
        try:
            parsed = _parse_provider_utc(raw)
        except Exception as error:
            raise AmbiguousTargetError(
                f"name-matched Pod has malformed {field}"
            ) from error
        if not window_start <= parsed <= window_end:
            raise AmbiguousTargetError(
                f"name-matched Pod {field} is outside the bound window"
            )
        provider_birth_times[field] = raw
    if not provider_birth_times:
        raise AmbiguousTargetError(
            "name-matched Pod omits both createdAt and lastStartedAt"
        )
    provider_birth = min(
        _parse_provider_utc(value) for value in provider_birth_times.values()
    )
    pre_arm_observed = _parse_utc(str(arm["pre_arm_inventory_observed_at_utc"]))
    if observed_utc < max(window_start, pre_arm_observed) or (
        observed_utc + timedelta(seconds=MAX_PROVIDER_CLOCK_SKEW_SECONDS)
        < provider_birth
    ):
        raise AmbiguousTargetError(
            "candidate observation precedes arm, window, or provider birth"
        )
    effective_deadline = min(
        deadline, provider_birth + timedelta(seconds=MAX_POD_RUN_SECONDS)
    )
    unsigned = {
        "arm_receipt_sha256": arm_receipt["receipt_sha256"],
        "bound_at_utc": _iso_utc(observed_utc),
        "claim_boundary": (
            "Inventory-based recovery binding; exact name and time are not proof that "
            "the bound request bytes caused this provider object."
        ),
        "delete_attempted": False,
        "hard_stop_deadline_utc": _iso_utc(effective_deadline),
        "inventory_sha256": sha256_hex(canonical_json_bytes(admitted)),
        "pod_id": pod_id,
        "pod_name_at_binding": candidate["name"],
        "pod_snapshot_sha256": sha256_hex(canonical_json_bytes(candidate)),
        "protected_pod_ids": sorted(PROTECTED_POD_IDS),
        "provider_birth_times_utc": provider_birth_times,
        "schema_version": BINDING_SCHEMA,
        "status": "UNIQUE_NEW_IN_WINDOW_ID_BOUND",
    }
    return _seal_receipt(unsigned)


def _require_bound_get(value: Any, pod_id: str) -> str:
    if not isinstance(value, dict) or value.get("id") != pod_id:
        raise ValueError("provider GET does not match the immutable bound Pod ID")
    status = value.get("desiredStatus")
    if status not in {"RUNNING", "EXITED", "TERMINATED"}:
        raise ValueError("provider GET contains an unadmitted desiredStatus")
    return str(status)


def _terminal_receipt(
    binding_receipt: dict[str, Any],
    *,
    before_status: str,
    terminal_status: str,
    stop_attempts: int,
    stop_http_status: int | None,
    stop_requested_at: datetime | None,
    terminal_observed_at: datetime,
    terminal_polls: int,
    get_error_count: int,
) -> dict[str, Any]:
    binding = _verify_receipt(binding_receipt, BINDING_SCHEMA)
    unsigned = {
        "binding_receipt_sha256": binding_receipt["receipt_sha256"],
        "claim_boundary": (
            "Self-reported guardian STOP/terminal observation; not a provider "
            "signature or billing-settlement record."
        ),
        "delete_attempted": False,
        "hard_stop_deadline_utc": binding["hard_stop_deadline_utc"],
        "get_error_count": get_error_count,
        "observed_before_stop": before_status,
        "observed_terminal_status": terminal_status,
        "pod_id": binding["pod_id"],
        "schema_version": TERMINAL_SCHEMA,
        "status": "STOPPED_OR_ALREADY_TERMINAL_CONFIRMED",
        "stop_attempts": stop_attempts,
        "stop_http_status": stop_http_status,
        "stop_requested_at_utc": (
            _iso_utc(stop_requested_at) if stop_requested_at is not None else None
        ),
        "terminal_observed_at_utc": _iso_utc(terminal_observed_at),
        "terminal_poll_count": terminal_polls,
    }
    return _seal_receipt(unsigned)


def contain_bound_target(
    binding_receipt: dict[str, Any],
    *,
    arm_receipt: dict[str, Any],
    provider: ProviderAdapter,
    clock: Clock,
    poll_seconds: float = 5.0,
    stop_lead_seconds: int = DEFAULT_STOP_LEAD_SECONDS,
    terminal_timeout_seconds: int = DEFAULT_TERMINAL_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """STOP only the recovered immutable ID, at or before its hard deadline."""

    arm, binding = _validate_binding_receipt(binding_receipt, arm_receipt)
    pod_id = str(binding["pod_id"])
    if pod_id in PROTECTED_POD_IDS:
        raise ProtectedTargetError("bound Pod ID is protected")
    deadline = _parse_utc(str(binding["hard_stop_deadline_utc"]))
    if poll_seconds <= 0 or not 1 <= stop_lead_seconds <= 300:
        raise ValueError("poll interval and stop lead are outside admitted bounds")
    if terminal_timeout_seconds <= 0:
        raise ValueError("terminal poll timeout must be positive")
    stop_boundary = deadline - timedelta(seconds=stop_lead_seconds)
    before_status = "UNAVAILABLE"
    get_error_count = 0
    while True:
        now = clock.now().astimezone(timezone.utc)
        try:
            value = provider.get_pod(pod_id)
            before_status = _require_bound_get(value, pod_id)
            if before_status in {"EXITED", "TERMINATED"}:
                return _terminal_receipt(
                    binding_receipt,
                    before_status=before_status,
                    terminal_status=before_status,
                    stop_attempts=0,
                    stop_http_status=None,
                    stop_requested_at=None,
                    terminal_observed_at=now,
                    terminal_polls=1,
                    get_error_count=get_error_count,
                )
        except Exception:
            get_error_count += 1
        if now >= stop_boundary:
            break
        clock.sleep(max(0.001, min(poll_seconds, (stop_boundary - now).total_seconds())))

    stop_attempts = 0
    stop_status: int | None = None
    stop_requested_at: datetime | None = None
    while clock.now().astimezone(timezone.utc) <= deadline:
        stop_attempts += 1
        attempted_at = clock.now().astimezone(timezone.utc)
        try:
            observed_status = provider.stop_pod(pod_id)
            if observed_status != 200:
                raise GuardianError(f"provider STOP returned HTTP {observed_status}")
            stop_status = observed_status
            stop_requested_at = attempted_at
            break
        except Exception as error:
            remaining = (deadline - clock.now().astimezone(timezone.utc)).total_seconds()
            if remaining <= 0:
                raise DeadlineError("all STOP attempts failed by the hard deadline") from error
            clock.sleep(max(0.001, min(poll_seconds, remaining)))
    if stop_status != 200 or stop_requested_at is None or stop_requested_at > deadline:
        raise DeadlineError("no successful STOP request occurred by the hard deadline")

    terminal_by = clock.now().astimezone(timezone.utc) + timedelta(
        seconds=terminal_timeout_seconds
    )
    terminal_polls = 0
    while clock.now().astimezone(timezone.utc) <= terminal_by:
        terminal_polls += 1
        now = clock.now().astimezone(timezone.utc)
        try:
            status = _require_bound_get(provider.get_pod(pod_id), pod_id)
            if status in {"EXITED", "TERMINATED"}:
                return _terminal_receipt(
                    binding_receipt,
                    before_status=before_status,
                    terminal_status=status,
                    stop_attempts=stop_attempts,
                    stop_http_status=stop_status,
                    stop_requested_at=stop_requested_at,
                    terminal_observed_at=now,
                    terminal_polls=terminal_polls,
                    get_error_count=get_error_count,
                )
        except Exception:
            get_error_count += 1
        clock.sleep(
            max(
                0.001,
                min(
                    poll_seconds,
                    (terminal_by - clock.now().astimezone(timezone.utc)).total_seconds(),
                ),
            )
        )
    raise GuardianError("STOP succeeded but terminal provider state was not observed")


def supervise_after_arm(
    arm_receipt: dict[str, Any],
    *,
    provider: ProviderAdapter,
    clock: Clock,
    poll_seconds: float = 5.0,
    stop_lead_seconds: int = DEFAULT_STOP_LEAD_SECONDS,
) -> GuardianResult:
    """Poll independently after arm, recover one target, and contain its cost."""

    arm = _validate_arm_receipt(arm_receipt)
    deadline = _parse_utc(str(arm["hard_stop_deadline_utc"]))
    inventory_errors = 0
    while clock.now().astimezone(timezone.utc) <= deadline:
        observed_at = clock.now().astimezone(timezone.utc)
        try:
            binding = discover_candidate(
                arm_receipt,
                inventory=provider.list_pods(),
                observed_at=observed_at,
            )
        except (AmbiguousTargetError, ProtectedTargetError):
            raise
        except Exception:
            inventory_errors += 1
            binding = None
        if binding is not None:
            terminal = contain_bound_target(
                binding,
                arm_receipt=arm_receipt,
                provider=provider,
                clock=clock,
                poll_seconds=poll_seconds,
                stop_lead_seconds=stop_lead_seconds,
            )
            return GuardianResult(binding, terminal)
        remaining = (deadline - clock.now().astimezone(timezone.utc)).total_seconds()
        if remaining <= 0:
            break
        clock.sleep(max(0.001, min(poll_seconds, remaining)))

    unsigned = {
        "arm_receipt_sha256": arm_receipt["receipt_sha256"],
        "claim_boundary": (
            "No unique target was bound; this does not prove that no Pod was created."
        ),
        "containment_proven": False,
        "delete_attempted": False,
        "hard_stop_deadline_utc": arm["hard_stop_deadline_utc"],
        "inventory_error_count": inventory_errors,
        "schema_version": TERMINAL_SCHEMA,
        "status": "UNRESOLVED_NO_UNIQUE_TARGET_BY_DEADLINE",
        "written_at_utc": _iso_utc(clock.now()),
    }
    return GuardianResult(None, _seal_receipt(unsigned))


def arm_and_supervise_offline(
    spec: ArmSpec,
    *,
    exact_create_request_bytes: bytes,
    provider: ProviderAdapter,
    clock: Clock,
    publish_arm_receipt: Callable[[dict[str, Any]], None],
    poll_seconds: float = 5.0,
    stop_lead_seconds: int = DEFAULT_STOP_LEAD_SECONDS,
) -> GuardianResult:
    """Refuse to turn a same-process callback into live launch authority.

    A callback can return before a durable, independently supervised polling
    process is known to be alive.  A crash in that gap would recreate the exact
    unguarded create/HTTP-201-loss window this design is meant to close.  The
    offline reference therefore exposes the arm and supervision state-machine
    functions separately but never publishes an acknowledgement that a live
    launcher may use to send POST /v1/pods.
    """

    del (
        spec,
        exact_create_request_bytes,
        provider,
        clock,
        publish_arm_receipt,
        poll_seconds,
        stop_lead_seconds,
    )
    raise GuardianError("OFFLINE_REFERENCE_CANNOT_AUTHORIZE_LIVE_CREATE")
