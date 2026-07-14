"""Verify deployed CAS Harness Evidence Packet external anchoring.

This script performs a small end-to-end fleet smoke run against a deployed
noetic-compass-api service:

1. create a 1-worker distributed audit;
2. register, lease, and receipt the assigned worker job;
3. submit a Stage19/Stage20 verifier fragment payload;
4. merge the fleet Evidence Packet;
5. run the verifier decision layer;
6. fetch the packet and /verify response;
7. fail unless the packet is externally anchored in the requested mode and
   /verify can re-read the S3 anchor object when mode=s3.

It does not load real model weights. Its purpose is deployment verification:
prove that packet hash-log anchoring is configured and visible in production.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
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


DEFAULT_BASE_URL = "https://noetic-compass-api.onrender.com"
TOKEN_ENV_VAR = "CAS_HARNESS_API_TOKEN"


class AnchorSmokeFailure(AssertionError):
    """Raised when a named anchor smoke gate fails."""

    def __init__(self, gate: str, message: str) -> None:
        super().__init__(f"{gate}: {message}")
        self.gate = gate
        self.message = message


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a deployed CAS Harness Evidence Packet anchor smoke test."
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Deployed noetic-compass-api base URL. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--bearer-token",
        default=None,
        help=f"Bearer token for protected endpoints. Defaults to ${TOKEN_ENV_VAR}.",
    )
    parser.add_argument(
        "--username",
        default="anchor-smoke",
        help="Username used when fetching a demo JWT from /auth/token.",
    )
    parser.add_argument(
        "--require-anchor-mode",
        choices=("s3", "local", "disabled", "any"),
        default="s3",
        help="Required packet hashes.external_anchor.mode. Default: s3.",
    )
    parser.add_argument(
        "--require-object-lock",
        action="store_true",
        help="Fail unless the S3 anchor object has verified Object Lock retention metadata.",
    )
    args = parser.parse_args(argv)

    base = args.base_url.rstrip("/")
    token = resolve_bearer_token(args.bearer_token)
    token_source = "provided"
    if token is None:
        token = fetch_demo_token(base, args.username)
        token_source = "/auth/token"

    print("CAS Harness Evidence Packet anchor smoke")
    print(f"Base URL: {base}")
    print(f"Authorization: bearer token from {token_source}")
    print(f"Required anchor mode: {args.require_anchor_mode}")
    print(f"Require Object Lock: {'yes' if args.require_object_lock else 'no'}")
    print("Scope: packet anchoring/control-plane smoke only; no real model inference is performed.")
    print()

    step(1, "Create a distributed audit")
    audit = post_json(
        base,
        "/api/cas-harness/audit/distributed/session",
        {
            "model_id": "deploy-check/open-weight-ledger-watch-20b",
            "weight_access": "open_weight",
            "parameter_count_b": 20,
            "num_layers": 8,
            "precision": "bf16",
            "available_gpu_memory_gb": 80,
            "minimum_worker_count": 1,
            "accept_audit_data_capture": True,
        },
        bearer_token=token,
    )
    audit_id = required_string(audit, "audit_id", "create-audit")
    total_workers = audit.get("total_workers")
    require_gate(
        "create-audit",
        isinstance(total_workers, int) and total_workers >= 1,
        f"expected at least one worker, got {total_workers!r}",
    )
    ok(f"created {audit_id} with {total_workers} planned worker(s)")

    step(2, "Dispatch and prepare fleet")
    dispatched = post_json(
        base,
        f"/api/cas-harness/audit/distributed/session/{audit_id}/dispatch",
        None,
        bearer_token=token,
    )
    workers = required_list(dispatched, "worker_evidence", "dispatch-workers")
    plan = required_mapping(dispatched, "plan", "dispatch-workers")
    model_id = required_string(plan, "model_id", "dispatch-workers")
    for worker in workers:
        require_gate("dispatch-workers", isinstance(worker, Mapping), "worker entry must be an object")
        register_worker(base, worker, model_id, bearer_token=token)
    prepared = post_json(
        base,
        f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/prepare",
        None,
        bearer_token=token,
    )
    require_gate(
        "prepare-fleet",
        prepared.get("total_jobs") == len(workers),
        f"expected {len(workers)} fleet job(s), got {prepared.get('total_jobs')!r}",
    )
    ok("fleet prepared")

    step(3, "Lease every job and submit verifier fragment receipts")
    verifier_fragment = stage19_stage20_verifier_fragment()
    final_gate_status = None
    submitted_receipts = 0
    for worker in workers:
        worker_id = required_string(worker, "worker_id", "dispatch-workers")
        leased = post_json(
            base,
            f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/job/lease",
            {"worker_id": worker_id},
            bearer_token=token,
        )
        job_id = required_string(leased, "job_id", "lease-job")
        lease_token = required_string(leased, "lease_token", "lease-job")
        expected_outputs = required_string_list(leased, "expected_outputs", "lease-job")
        fragment_ref = build_evidence_fragment_ref(
            audit_id=audit_id,
            job_id=job_id,
            worker_id=worker_id,
            model_id=model_id,
            layer_start=required_int(leased, "layer_start", "lease-job"),
            layer_end=required_int(leased, "layer_end", "lease-job"),
            shard_id=required_string(leased, "shard_id", "lease-job"),
            expected_outputs=expected_outputs,
            produced_outputs=expected_outputs,
            missing_outputs=[],
            evidence_packet_fragment_payload=verifier_fragment,
        )
        receipt = post_json(
            base,
            f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/job/{job_id}/receipt",
            {
                "worker_id": worker_id,
                "lease_token": lease_token,
                "produced_outputs": expected_outputs,
                "evidence_packet_fragment_ref": fragment_ref,
                "evidence_packet_fragment_payload": verifier_fragment,
            },
            bearer_token=token,
        )
        final_gate_status = receipt.get("verifier_gate_status")
        require_gate(
            "submit-receipt",
            final_gate_status in {"waiting_for_receipts", "ready_for_verifier"},
            f"unexpected verifier gate status after receipt: {final_gate_status!r}",
        )
        submitted_receipts += 1
    require_gate(
        "submit-receipt",
        final_gate_status == "ready_for_verifier",
        f"expected ready_for_verifier after all receipts, got {final_gate_status!r}",
    )
    ok(f"{submitted_receipts} receipt(s) accepted")

    step(4, "Merge packet and run verifier")
    merged = post_json(
        base,
        f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/merge",
        None,
        bearer_token=token,
    )
    trace_id = required_string(merged, "merged_packet_trace_id", "merge-fleet")
    verifier = post_json(
        base,
        f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/verifier",
        None,
        bearer_token=token,
    )
    require_gate(
        "verifier-decision",
        verifier.get("verdict") == "ACCEPT",
        f"expected ACCEPT from submitted Stage19/20 verifier fragment, got {verifier.get('verdict')!r}",
    )
    ok(f"merged packet {trace_id}; verifier ACCEPT")

    step(5, "Fetch Evidence Packet and verify anchor")
    packet = get_json(base, f"/evidence/{trace_id}", bearer_token=token)
    verify = post_json(base, f"/evidence/{trace_id}/verify", None, bearer_token=token)
    hashes = required_mapping(packet, "hashes", "fetch-packet")
    anchor = required_mapping(hashes, "external_anchor", "fetch-packet")
    anchor_status = required_string(anchor, "status", "fetch-packet")
    anchor_mode = required_string(anchor, "mode", "fetch-packet")
    anchor_uri = anchor.get("anchor_uri")
    verify_check = find_check(verify, "merged_packet_external_anchor")

    if args.require_anchor_mode != "any":
        require_gate(
            "anchor-mode",
            anchor_mode == args.require_anchor_mode,
            (
                f"expected anchor mode {args.require_anchor_mode!r}, got {anchor_mode!r}. "
                "Set Render env CAS_HARNESS_EVIDENCE_ANCHOR_MODE=s3 plus S3 bucket/credentials, then redeploy."
            ),
        )
    if args.require_anchor_mode not in {"disabled", "any"}:
        require_gate(
            "anchor-status",
            anchor_status == "anchored",
            (
                f"expected anchored status, got {anchor_status!r}. "
                f"Anchor reason: {anchor.get('reason')!r}"
            ),
        )
    require_gate(
        "anchor-verify",
        verify.get("overall") == "all_match" and bool(verify_check.get("match")),
        f"expected /verify all_match with external anchor match; got {verify}",
    )
    if anchor_mode == "s3":
        manifest_sha = anchor.get("manifest_sha256")
        require_gate(
            "anchor-reread",
            isinstance(manifest_sha, str)
            and bool(manifest_sha)
            and verify_check.get("expected") == manifest_sha
            and verify_check.get("actual") == manifest_sha,
            (
                "expected /verify to re-read the exact S3 anchor manifest; "
                f"manifest={manifest_sha!r} expected={verify_check.get('expected')!r} "
                f"actual={verify_check.get('actual')!r}."
            ),
        )
        if args.require_object_lock:
            try:
                proof = validate_object_lock_receipt(anchor, verify_check)
            except ObjectLockReceiptError as exc:
                raise AnchorSmokeFailure("object-lock-verify", str(exc)) from exc
            ok(
                "structured Object Lock receipt verified "
                f"mode={proof['mode']} version_id={proof['version_id']} "
                f"remaining_days={proof['remaining'].total_seconds() / 86400:.3f}"
            )
    elif args.require_object_lock:
        raise AnchorSmokeFailure(
            "object-lock-mode",
            f"Object Lock verification requires S3 anchor mode, got {anchor_mode!r}.",
        )
    ok(f"anchor status={anchor_status} mode={anchor_mode} uri={anchor_uri or '(none)'}")
    print()
    print("PASS: deployed Evidence Packet anchor smoke passed.")
    print(f"Trace ID: {trace_id}")
    return 0


def stage19_stage20_verifier_fragment() -> dict[str, Any]:
    return {
        "schema_version": "cas_harness_evidence_fragment.v1",
        "provenance": {
            "source_reports": [
                "stage19_verification_stack_anchor_smoke.json",
                "stage20_generation_readiness_anchor_smoke.json",
            ],
        },
        "verification": {
            "accepted": True,
            "mode": "BALANCED",
            "mode_profile": {
                "accepted_accuracy": 0.91,
                "coverage": 0.74,
            },
            "proof_chips": [
                {"id": "model_proof", "status": "verified", "detail": "Model shard loaded."},
                {"id": "cas_readout", "status": "verified", "detail": "CAS readout present."},
                {"id": "causal_proof", "status": "verified", "detail": "Causal proof present."},
                {"id": "control_proof", "status": "verified", "detail": "Control proof present."},
                {"id": "output_proof", "status": "verified", "detail": "Output proof present."},
                {"id": "packet_proof", "status": "present", "detail": "Packet proof present."},
            ],
        },
        "generation_readiness": {
            "generation_readiness": "allow",
            "risk_score": 0.09,
            "policy_version": "stage20_anchor_smoke_v1",
        },
    }


def register_worker(
    base: str,
    assignment: Mapping[str, Any],
    model_id: str,
    *,
    bearer_token: str,
) -> dict[str, Any]:
    worker_id = required_string(assignment, "worker_id", "register-worker")
    try:
        return post_json(
            base,
            "/api/cas-harness/audit/distributed/fleet/worker/register",
            {
                "worker_id": worker_id,
                "model_id": model_id,
                "worker_url": f"https://{worker_id}.anchor-smoke.internal",
                "gpu_type": "anchor-smoke",
                "capacity": 1,
                "supported_methods": required_string_list(
                    assignment,
                    "assigned_methods",
                    "register-worker",
                ),
            },
            bearer_token=bearer_token,
        )
    except AnchorSmokeFailure as exc:
        if exc.gate != "http-request" or "Worker ID is already registered" not in exc.message:
            raise
        return post_json(
            base,
            f"/api/cas-harness/audit/distributed/fleet/worker/{worker_id}/heartbeat",
            None,
            bearer_token=bearer_token,
        )


def fetch_demo_token(base: str, username: str) -> str:
    body = post_json(base, "/auth/token", {"username": username}, bearer_token=None)
    return required_string(body, "token", "fetch-demo-token")


def post_json(
    base: str,
    path: str,
    payload: Mapping[str, Any] | None,
    *,
    bearer_token: str | None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    authorization = authorization_header(bearer_token)
    if authorization:
        headers["Authorization"] = authorization
    request = Request(f"{base}{path}", data=body, headers=headers, method="POST")
    return read_json(request)


def get_json(base: str, path: str, *, bearer_token: str | None) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    authorization = authorization_header(bearer_token)
    if authorization:
        headers["Authorization"] = authorization
    request = Request(f"{base}{path}", headers=headers, method="GET")
    return read_json(request)


def read_json(request: Request) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=90) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise AnchorSmokeFailure(
            "http-request",
            f"HTTP {exc.code} for {request.full_url}: {body}",
        ) from exc
    if not isinstance(payload, dict):
        raise AnchorSmokeFailure("http-request", f"non-object JSON response from {request.full_url}")
    return payload


def resolve_bearer_token(cli_token: str | None) -> str | None:
    token = clean_token(cli_token)
    if token:
        return token
    return clean_token(os.environ.get(TOKEN_ENV_VAR))


def authorization_header(token: str | None) -> str | None:
    cleaned = clean_token(token)
    if not cleaned:
        return None
    if cleaned.lower().startswith("bearer "):
        return cleaned
    return f"Bearer {cleaned}"


def build_evidence_fragment_ref(
    *,
    audit_id: str,
    job_id: str,
    worker_id: str,
    model_id: str,
    layer_start: int,
    layer_end: int,
    shard_id: str,
    expected_outputs: list[str] | tuple[str, ...],
    produced_outputs: list[str] | tuple[str, ...],
    missing_outputs: list[str] | tuple[str, ...] = (),
    evidence_packet_fragment_payload: Mapping[str, Any] | None = None,
) -> str:
    payload: dict[str, object] = {
        "schema_version": "cas_harness_evidence_fragment.v1",
        "audit_id": audit_id,
        "job_id": job_id,
        "worker_id": worker_id,
        "model_id": model_id,
        "layer_start": layer_start,
        "layer_end": layer_end,
        "shard_id": shard_id,
        "expected_outputs": list(expected_outputs),
        "produced_outputs": list(produced_outputs),
        "missing_outputs": list(missing_outputs),
    }
    fragment_payload_hash = fragment_payload_sha256(evidence_packet_fragment_payload)
    if fragment_payload_hash is not None:
        payload["fragment_payload_sha256"] = fragment_payload_hash
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"cas-fragment://{audit_id}/{job_id}/{worker_id}/{shard_id}/sha256:{digest}"


def fragment_payload_sha256(payload: Mapping[str, Any] | None) -> str | None:
    if payload is None:
        return None
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def find_check(verify_response: Mapping[str, Any], artifact: str) -> Mapping[str, Any]:
    checks = verify_response.get("checks")
    if isinstance(checks, list):
        for check in checks:
            if isinstance(check, Mapping) and check.get("artifact") == artifact:
                return check
    raise AnchorSmokeFailure("anchor-verify", f"/verify response missing {artifact!r} check")


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


def required_int(payload: Mapping[str, Any], key: str, gate: str) -> int:
    value = payload.get(key)
    require_gate(gate, isinstance(value, int), f"{key!r} must be an integer")
    return value


def required_string_list(payload: Mapping[str, Any], key: str, gate: str) -> list[str]:
    value = payload.get(key)
    require_gate(gate, isinstance(value, list), f"{key!r} must be a list")
    cleaned = [item for item in value if isinstance(item, str) and item.strip()]
    require_gate(gate, len(cleaned) == len(value) and len(cleaned) > 0, f"{key!r} must contain non-empty strings")
    return cleaned


def clean_token(token: str | None) -> str | None:
    if token is None:
        return None
    stripped = token.strip()
    return stripped or None


def step(number: int, message: str) -> None:
    print(f"[{number:02d}] {message}")


def ok(message: str) -> None:
    print(f"     OK - {message}")


def require_gate(gate: str, condition: bool, message: str) -> None:
    if not condition:
        raise AnchorSmokeFailure(gate, message)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AnchorSmokeFailure as exc:
        print(f"FAIL GATE: {exc.gate}", file=sys.stderr)
        print(f"DETAIL: {exc.message}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
