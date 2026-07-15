"""No-SSH hosted CAS Harness live-worker + WORM smoke.

This script proves the launch-critical hosted path without touching the worker
host directly over SSH:

1. direct worker real-health proof;
2. direct worker token rejection without X-Atlas-Worker-Token;
3. direct worker token success with X-Atlas-Worker-Token;
4. API-side token send through a CAS Harness audit run;
5. Evidence Packet write and /verify overall all_match;
6. S3 Object Lock truth when --require-object-lock is set;
7. proof-chip statuses derived from packet evidence, never a fabricated ACCEPT.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from urllib.error import HTTPError
from urllib.request import Request, urlopen

try:
    from .object_lock_smoke_validation import (
        ObjectLockReceiptError,
        validate_object_lock_receipt,
    )
except ImportError:  # Direct ``python scripts/...`` execution.
    from object_lock_smoke_validation import (
        ObjectLockReceiptError,
        validate_object_lock_receipt,
    )


DEFAULT_BASE_URL = "https://cas-harness-customer-api.onrender.com"
MODEL_ID = "EleutherAI/pythia-160m"
REALMODE_PASS = "REAL_PYTHIA_WEIGHTS_LOADED"
WORKER_TOKEN_HEADER = "X-Atlas-Worker-Token"
USER_AGENT = "CAS-Harness-Hosted-Smoke/1.0"
API_TOKEN_ENV_VAR = "CAS_HARNESS_API_TOKEN"
WORKER_TOKEN_ENV_VAR = "ATLAS_LIVE_WORKER_TOKEN"
WORKER_URL_ENV_VARS = ("ATLAS_LIVE_WORKER_URL", "NC_ATLAS_LIVE_WORKER_URL")
PRESENT_STATUSES = {"present", "verified"}
MIN_CONFIGURED_RETENTION_DAYS = 31
MIN_REMAINING_RETENTION = timedelta(days=30)


class HostedSmokeFailure(AssertionError):
    """Raised when a named hosted smoke gate fails."""

    def __init__(self, gate: str, message: str) -> None:
        super().__init__(f"{gate}: {message}")
        self.gate = gate
        self.message = message


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    base = args.base_url.rstrip("/")
    worker = resolve_worker_url(args.worker_url)
    worker_token = clean_token(args.worker_token) or clean_token(os.environ.get(WORKER_TOKEN_ENV_VAR))
    bearer_token = clean_token(args.bearer_token) or clean_token(os.environ.get(API_TOKEN_ENV_VAR))
    run_nonce = uuid.uuid4().hex

    require_gate("worker-url", bool(worker), "--worker-url or ATLAS_LIVE_WORKER_URL is required")
    require_gate("worker-token", bool(worker_token), "--worker-token or ATLAS_LIVE_WORKER_TOKEN is required")

    print("CAS Harness hosted live-worker/WORM smoke")
    print(f"Base URL: {base}")
    print(f"Worker URL: {worker}")
    print(f"Authorization: {'provided bearer token' if bearer_token else 'none/demo-token fallback'}")
    print(f"Require Object Lock: {'yes' if args.require_object_lock else 'no'}")
    print(f"Run nonce: {run_nonce}")
    print("Claim boundary: a live open-weight audit remains FLAG_FOR_HUMAN_REVIEW, never ACCEPT.")
    print()

    step(1, "Check direct worker real health")
    worker_health = get_json(worker, "/health/realmode", bearer_token=None, extra_headers=None, gate="worker-health")
    assert_realmode("worker-health", worker_health)
    ok(f"worker realmode={worker_health.get('verdict')} model_id={worker_health.get('model_id')}")

    step(2, "Prove worker token rejects requests without X-Atlas-Worker-Token")
    status, body = request_json(
        worker,
        "/sessions",
        method="POST",
        payload=worker_session_payload(),
        bearer_token=None,
        extra_headers=None,
        expected_statuses={401},
        gate="worker-token-reject",
    )
    require_gate("worker-token-reject", status == 401, f"expected HTTP 401, got {status}: {body}")
    ok("worker returned HTTP 401 without X-Atlas-Worker-Token")

    step(3, "Prove worker token succeeds with X-Atlas-Worker-Token")
    worker_session = post_json(
        worker,
        "/sessions",
        worker_session_payload(),
        bearer_token=None,
        extra_headers={WORKER_TOKEN_HEADER: worker_token},
        gate="worker-token-success",
    )
    worker_session_id = required_string(worker_session, "session_id", "worker-token-success")
    ok(f"worker accepted token and created session {worker_session_id}")

    step(4, "Check API live-worker health chip")
    api_health = get_json(
        base,
        "/api/cas-harness/live-worker/health",
        bearer_token=bearer_token,
        extra_headers=None,
        gate="api-live-worker-health",
    )
    require_gate("api-live-worker-health", api_health.get("configured") is True, f"not configured: {api_health}")
    require_gate("api-live-worker-health", api_health.get("reachable") is True, f"not reachable: {api_health}")
    require_gate("api-live-worker-health", api_health.get("real_weights") is True, f"not real weights: {api_health}")
    ok(f"API reports real worker model_id={api_health.get('model_id')}")

    step(5, "Run CAS Harness audit through the API")
    if bearer_token is None:
        bearer_token = fetch_demo_token(base, args.username)
        ok("fetched demo bearer token from /auth/token")
    created = post_json(
        base,
        "/api/cas-harness/audit/session",
        {
            "model_id": MODEL_ID,
            "audit_mode": "BALANCED",
            "prompt": build_audit_prompt(run_nonce),
            "selected_modules": ["active_trace", "confidence_margin"],
        },
        bearer_token=bearer_token,
        extra_headers=None,
        gate="create-audit",
    )
    audit_id = required_string(created, "audit_id", "create-audit")
    ran = post_json(
        base,
        f"/api/cas-harness/audit/session/{audit_id}/run",
        None,
        bearer_token=bearer_token,
        extra_headers=None,
        gate="run-audit",
    )
    require_gate("run-audit", ran.get("status") == "COMPLETE", f"expected COMPLETE, got {ran.get('status')!r}")
    require_gate(
        "run-audit",
        ran.get("verdict") == "FLAG_FOR_HUMAN_REVIEW",
        f"live worker audit must remain FLAG_FOR_HUMAN_REVIEW, got {ran.get('verdict')!r}",
    )
    require_gate("run-audit", ran.get("verdict") != "ACCEPT", "FLAG_FOR_HUMAN_REVIEW must not be called ACCEPT")
    trace_id = required_string(ran, "evidence_packet_trace_id", "run-audit")
    ok(f"API-side worker-token send proved by completed live audit {audit_id}; trace_id={trace_id}")

    step(6, "Fetch Evidence Packet and run /verify")
    packet = get_json(base, f"/evidence/{trace_id}", bearer_token=bearer_token, extra_headers=None, gate="fetch-packet")
    require_gate("fetch-packet", packet.get("trace_id") == trace_id, f"packet trace_id mismatch: {packet.get('trace_id')!r}")
    assert_packet_is_real_live_trace(packet)
    verify = post_json(
        base,
        f"/evidence/{trace_id}/verify",
        None,
        bearer_token=bearer_token,
        extra_headers=None,
        gate="verify-packet",
    )
    require_gate("verify-packet", verify.get("overall") == "all_match", f"expected /verify overall all_match, got {verify}")
    external_anchor_check = find_check(verify, "merged_packet_external_anchor")
    require_gate("verify-packet", bool(external_anchor_check.get("match")), f"external anchor check did not match: {external_anchor_check}")
    ok("/verify overall all_match")

    step(7, "Check S3 Object Lock truth")
    anchor = required_mapping(required_mapping(packet, "hashes", "object-lock"), "external_anchor", "object-lock")
    anchor_status = required_string(anchor, "status", "object-lock")
    anchor_mode = required_string(anchor, "mode", "object-lock")
    object_lock_mode = anchor.get("object_lock_mode")
    if args.require_object_lock:
        require_gate("object-lock", anchor_status == "anchored", f"expected anchored status, got {anchor_status!r}")
        require_gate("object-lock", anchor_mode == "s3", f"expected s3 anchor mode, got {anchor_mode!r}")
        require_gate(
            "object-lock",
            object_lock_mode in {"GOVERNANCE", "COMPLIANCE"},
            f"expected Object Lock mode GOVERNANCE or COMPLIANCE, got {object_lock_mode!r}",
        )
        retention_days, requested_at, retain_until, remaining = (
            assert_customer_production_retention(anchor)
        )
        try:
            structured_proof = validate_object_lock_receipt(anchor, external_anchor_check)
        except ObjectLockReceiptError as exc:
            raise HostedSmokeFailure("object-lock", str(exc)) from exc
        require_gate(
            "object-lock",
            structured_proof["requested_at"] == requested_at
            and structured_proof["retain_until"] == retain_until,
            "structured receipt and packet retention boundaries disagree",
        )
        print(
            "     OK - "
            f"Object Lock mode={object_lock_mode} configured_retention_days={retention_days} "
            f"requested_at={requested_at.isoformat()} retain_until={retain_until.isoformat()} "
            f"remaining_days={remaining.total_seconds() / 86400:.3f}"
        )
    else:
        print(
            "     OK - "
            f"anchor status={anchor_status} mode={anchor_mode} object_lock_mode={object_lock_mode or 'unavailable'}"
        )

    step(8, "Check proof chips mirror packet evidence")
    assert_proof_chips_truth(packet=packet, run_response=ran, verify=verify)
    ok("proof chips are truthful: present/unavailable mirrors packet evidence")

    print()
    print("PASS: hosted live-worker/WORM smoke passed.")
    print(f"Audit ID: {audit_id}")
    print(f"Trace ID: {trace_id}")
    if object_lock_mode in {"GOVERNANCE", "COMPLIANCE"}:
        print(f"S3 Object Lock: {object_lock_mode}")
    print("Verdict: FLAG_FOR_HUMAN_REVIEW")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a no-SSH hosted CAS Harness live-worker + WORM smoke."
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Deployed customer CAS Harness API base URL. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--bearer-token",
        default=None,
        help=f"Bearer token for API endpoints. Defaults to ${API_TOKEN_ENV_VAR}, then /auth/token.",
    )
    parser.add_argument(
        "--worker-url",
        default=None,
        help="Hosted live worker URL. Defaults to ATLAS_LIVE_WORKER_URL/NC_ATLAS_LIVE_WORKER_URL.",
    )
    parser.add_argument(
        "--worker-token",
        default=None,
        help=f"Worker shared secret. Defaults to ${WORKER_TOKEN_ENV_VAR}.",
    )
    parser.add_argument(
        "--require-object-lock",
        action="store_true",
        help=(
            "Fail unless the packet anchor proves S3 Object Lock GOVERNANCE or COMPLIANCE, "
            "configured retention of at least 31 days, and at least 30 days remaining."
        ),
    )
    parser.add_argument(
        "--username",
        default="hosted-live-worker-worm-smoke",
        help="Username used only when fetching a fallback demo JWT from /auth/token.",
    )
    return parser


def assert_customer_production_retention(
    anchor: Mapping[str, Any],
    *,
    verified_at: datetime | None = None,
) -> tuple[int, datetime, datetime, timedelta]:
    """Require the customer-production retention window on one verified anchor.

    ``retention_days`` and ``retention_requested_at`` prove the configured
    policy spans the promised window. ``object_lock_retain_until`` also proves
    enough of that policy remains when this smoke verifies the object. Both
    checks are necessary because an old receipt can still describe a 31-day
    policy after most of its immutable window has elapsed.
    """

    retention_days = anchor.get("retention_days")
    require_gate(
        "object-lock-retention",
        isinstance(retention_days, int)
        and not isinstance(retention_days, bool)
        and retention_days >= MIN_CONFIGURED_RETENTION_DAYS,
        (
            f"customer-production requires configured retention_days >= "
            f"{MIN_CONFIGURED_RETENTION_DAYS}, got {retention_days!r}"
        ),
    )

    requested_at = parse_timezone_aware_timestamp(
        anchor.get("retention_requested_at"),
        field="retention_requested_at",
    )
    retain_until = parse_timezone_aware_timestamp(
        anchor.get("object_lock_retain_until"),
        field="object_lock_retain_until",
    )
    require_gate(
        "object-lock-retention",
        retain_until >= requested_at + timedelta(days=retention_days),
        (
            "object_lock_retain_until is shorter than the configured retention window; "
            f"retention_requested_at={requested_at.isoformat()} "
            f"retention_days={retention_days} retain_until={retain_until.isoformat()}"
        ),
    )
    checked_at = verified_at or datetime.now(timezone.utc)
    require_gate(
        "object-lock-retention",
        isinstance(checked_at, datetime)
        and checked_at.tzinfo is not None
        and checked_at.utcoffset() is not None,
        "verification time must be a timezone-aware datetime",
    )
    checked_at_utc = checked_at.astimezone(timezone.utc)
    require_gate(
        "object-lock-retention",
        checked_at_utc >= requested_at,
        (
            "verification time predates the Object Lock request boundary; "
            f"retention_requested_at={requested_at.isoformat()} "
            f"verified_at={checked_at_utc.isoformat()}"
        ),
    )
    remaining = retain_until - checked_at_utc
    require_gate(
        "object-lock-retention",
        remaining >= MIN_REMAINING_RETENTION,
        (
            "customer-production requires at least 30 days of Object Lock retention "
            f"remaining at verification; retain_until={retain_until.isoformat()} "
            f"verified_at={checked_at_utc.isoformat()} "
            f"remaining_seconds={remaining.total_seconds():.6f}"
        ),
    )
    return retention_days, requested_at, retain_until, remaining


def parse_timezone_aware_timestamp(value: Any, *, field: str) -> datetime:
    """Parse an ISO-8601 timestamp and normalize it to UTC, rejecting ambiguity."""

    require_gate(
        "object-lock-retention",
        isinstance(value, str) and bool(value.strip()),
        f"{field} must be a non-empty timezone-aware ISO-8601 timestamp, got {value!r}",
    )
    candidate = value.strip()
    if candidate.endswith(("Z", "z")):
        candidate = f"{candidate[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise HostedSmokeFailure(
            "object-lock-retention",
            f"{field} must be a timezone-aware ISO-8601 timestamp, got {value!r}",
        ) from exc
    require_gate(
        "object-lock-retention",
        parsed.tzinfo is not None and parsed.utcoffset() is not None,
        f"{field} must include Z or a numeric UTC offset, got {value!r}",
    )
    return parsed.astimezone(timezone.utc)


def worker_session_payload() -> dict[str, Any]:
    return {
        "prompt": "Worker token smoke.",
        "model_id": MODEL_ID,
        "max_new_tokens": 1,
        "temperature": 0.0,
        "probes": ["active_trace"],
        "method_config": {"source": "hosted_live_worker_worm_smoke"},
    }


def build_audit_prompt(run_nonce: str) -> str:
    """Build an intentionally unique prompt so each smoke writes a fresh packet."""
    require_gate("run-nonce", bool(run_nonce.strip()), "run nonce must be non-empty")
    return (
        "Hosted no-SSH live-worker WORM smoke. Return a short factual trace. "
        f"run_nonce={run_nonce.strip()}"
    )


def assert_realmode(gate: str, payload: Mapping[str, Any]) -> None:
    require_gate(gate, payload.get("verdict") == REALMODE_PASS, f"expected {REALMODE_PASS}, got {payload}")
    require_gate(gate, payload.get("is_real_model") is True, f"is_real_model is not true: {payload}")
    require_gate(gate, payload.get("fake_runtime_env") is False, f"fake_runtime_env is not false: {payload}")
    require_gate(gate, payload.get("model_loaded") is True, f"model_loaded is not true: {payload}")
    require_gate(gate, payload.get("load_error") is None, f"load_error is not null: {payload}")
    require_gate(gate, payload.get("manifest_is_real_model") is True, f"manifest_is_real_model is not true: {payload}")
    require_gate(gate, payload.get("model_id") == MODEL_ID, f"expected model_id {MODEL_ID}, got {payload.get('model_id')!r}")


def assert_packet_is_real_live_trace(packet: Mapping[str, Any]) -> None:
    model = required_mapping(packet, "model", "packet-real-trace")
    manifest = model.get("manifest")
    require_gate("packet-real-trace", isinstance(manifest, Mapping), "packet model.manifest must be present")
    require_gate("packet-real-trace", manifest.get("is_real_model") is True, f"packet manifest is not real: {manifest}")
    scope = required_mapping(packet, "audit_scope", "packet-real-trace")
    require_gate("packet-real-trace", scope.get("kind") == "open_weight_live_trace", f"unexpected audit_scope: {scope}")
    require_gate(
        "packet-real-trace",
        scope.get("verdict_disposition") == "held_for_human_review",
        f"unexpected verdict disposition: {scope}",
    )
    output = required_mapping(packet, "output", "packet-real-trace")
    require_gate("packet-real-trace", bool(output.get("text")), "packet output.text must be present")


def assert_proof_chips_truth(
    *,
    packet: Mapping[str, Any],
    run_response: Mapping[str, Any],
    verify: Mapping[str, Any],
) -> None:
    packet_chips = chips_by_id(
        required_list(required_mapping(packet, "verification", "proof-chips"), "proof_chips", "proof-chips")
    )
    run_chips = chips_by_id(required_list(run_response, "provenance_chips", "proof-chips"))
    require_gate("proof-chips", set(packet_chips) == set(run_chips), f"run chips and packet chips differ: {set(run_chips)} vs {set(packet_chips)}")

    output = packet.get("output") if isinstance(packet.get("output"), Mapping) else {}
    readout = packet.get("readout") if isinstance(packet.get("readout"), Mapping) else {}
    ablation = packet.get("ablation") if isinstance(packet.get("ablation"), Mapping) else {}
    controls = packet.get("matched_controls") if isinstance(packet.get("matched_controls"), Mapping) else {}

    expected = {
        "model_proof": True,
        "cas_readout": bool(readout),
        "causal_proof": ablation.get("status") in {"present", "verified"},
        "control_proof": controls.get("status") in {"present", "verified"},
        "output_proof": bool(output.get("text")),
        "packet_proof": verify.get("overall") == "all_match",
    }
    for chip_id, should_be_present in expected.items():
        packet_present = chip_present(packet_chips, chip_id)
        run_present = chip_present(run_chips, chip_id)
        require_gate(
            "proof-chips",
            packet_present == should_be_present,
            f"packet {chip_id} status {packet_chips.get(chip_id)!r} does not mirror evidence present={should_be_present}",
        )
        require_gate(
            "proof-chips",
            run_present == should_be_present,
            f"run {chip_id} status {run_chips.get(chip_id)!r} does not mirror evidence present={should_be_present}",
        )


def chips_by_id(chips: list[Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for chip in chips:
        require_gate("proof-chips", isinstance(chip, Mapping), f"chip must be an object: {chip!r}")
        chip_id = required_string(chip, "id", "proof-chips")
        status = required_string(chip, "status", "proof-chips")
        out[chip_id] = status
    return out


def chip_present(chips: Mapping[str, str], chip_id: str) -> bool:
    require_gate("proof-chips", chip_id in chips, f"missing chip {chip_id!r}")
    status = chips[chip_id]
    require_gate(
        "proof-chips",
        status in PRESENT_STATUSES or status == "unavailable",
        f"unexpected {chip_id} status {status!r}",
    )
    return status in PRESENT_STATUSES


def fetch_demo_token(base: str, username: str) -> str:
    body = post_json(base, "/auth/token", {"username": username}, bearer_token=None, extra_headers=None, gate="fetch-demo-token")
    return required_string(body, "token", "fetch-demo-token")


def get_json(
    base: str,
    path: str,
    *,
    bearer_token: str | None,
    extra_headers: Mapping[str, str] | None,
    gate: str,
) -> dict[str, Any]:
    _status, payload = request_json(
        base,
        path,
        method="GET",
        payload=None,
        bearer_token=bearer_token,
        extra_headers=extra_headers,
        expected_statuses={200},
        gate=gate,
    )
    return payload


def post_json(
    base: str,
    path: str,
    payload: Mapping[str, Any] | None,
    *,
    bearer_token: str | None,
    extra_headers: Mapping[str, str] | None,
    gate: str,
) -> dict[str, Any]:
    _status, response = request_json(
        base,
        path,
        method="POST",
        payload=payload,
        bearer_token=bearer_token,
        extra_headers=extra_headers,
        expected_statuses={200},
        gate=gate,
    )
    return response


def request_json(
    base: str,
    path: str,
    *,
    method: str,
    payload: Mapping[str, Any] | None,
    bearer_token: str | None,
    extra_headers: Mapping[str, str] | None,
    expected_statuses: set[int],
    gate: str,
) -> tuple[int, dict[str, Any]]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    # RunPod's Cloudflare-backed proxy rejects Python urllib's default
    # browser signature (HTTP 403 / error 1010).  Identify this operational
    # probe explicitly so the no-SSH production smoke reaches the worker.
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    authorization = authorization_header(bearer_token)
    if authorization:
        headers["Authorization"] = authorization
    if extra_headers:
        headers.update(dict(extra_headers))
    request = Request(f"{base.rstrip('/')}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=120) as response:
            status = int(response.status)
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        status = int(exc.code)
        raw = exc.read().decode("utf-8")
        if status not in expected_statuses:
            raise HostedSmokeFailure(gate, f"HTTP {status} for {request.full_url}: {raw}") from exc
    if status not in expected_statuses:
        raise HostedSmokeFailure(gate, f"HTTP {status} for {request.full_url}: {raw}")
    try:
        parsed = json.loads(raw) if raw else {}
    except ValueError as exc:
        raise HostedSmokeFailure(gate, f"non-JSON response from {request.full_url}: {raw[:200]!r}") from exc
    require_gate(gate, isinstance(parsed, dict), f"expected object JSON from {request.full_url}")
    return status, parsed


def find_check(verify_response: Mapping[str, Any], artifact: str) -> Mapping[str, Any]:
    checks = verify_response.get("checks")
    if isinstance(checks, list):
        for check in checks:
            if isinstance(check, Mapping) and check.get("artifact") == artifact:
                return check
    raise HostedSmokeFailure("verify-packet", f"/verify response missing {artifact!r} check")


def resolve_worker_url(cli_value: str | None) -> str:
    value = clean_token(cli_value)
    if value:
        return value.rstrip("/")
    for name in WORKER_URL_ENV_VARS:
        value = clean_token(os.environ.get(name))
        if value:
            return value.rstrip("/")
    return ""


def authorization_header(token: str | None) -> str | None:
    cleaned = clean_token(token)
    if not cleaned:
        return None
    if cleaned.lower().startswith("bearer "):
        return cleaned
    return f"Bearer {cleaned}"


def clean_token(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def required_mapping(payload: Mapping[str, Any], key: str, gate: str) -> Mapping[str, Any]:
    value = payload.get(key)
    require_gate(gate, isinstance(value, Mapping), f"{key!r} must be an object")
    return value


def required_list(payload: Mapping[str, Any], key: str, gate: str) -> list[Any]:
    value = payload.get(key)
    require_gate(gate, isinstance(value, list) and len(value) > 0, f"{key!r} must be a non-empty list")
    return value


def required_string(payload: Mapping[str, Any], key: str, gate: str) -> str:
    value = payload.get(key)
    require_gate(gate, isinstance(value, str) and bool(value.strip()), f"{key!r} must be a non-empty string")
    return value


def step(number: int, message: str) -> None:
    print(f"[{number:02d}] {message}")


def ok(message: str) -> None:
    print(f"     OK - {message}")


def require_gate(gate: str, condition: bool, message: str) -> None:
    if not condition:
        raise HostedSmokeFailure(gate, message)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HostedSmokeFailure as exc:
        print(f"FAIL GATE: {exc.gate}", file=sys.stderr)
        print(f"DETAIL: {exc.message}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
