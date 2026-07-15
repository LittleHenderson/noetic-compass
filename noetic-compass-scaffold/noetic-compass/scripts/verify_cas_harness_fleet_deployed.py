"""Verify deployed CAS Harness fleet-executor gates.

This script is a control-plane verifier only. It intentionally does not load,
probe, or run inference through a real 300B model. It validates the deployed API
contract that a large-model distributed audit cannot move forward without worker
registration, job leases, and Evidence Packet fragment receipts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://cas-harness-customer-api.onrender.com"
DEFAULT_WORKERS = 25
TOKEN_ENV_VAR = "CAS_HARNESS_API_TOKEN"


class GateFailure(AssertionError):
    """Raised when a named deployment gate fails."""

    def __init__(self, gate: str, message: str) -> None:
        super().__init__(f"{gate}: {message}")
        self.gate = gate
        self.message = message


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify deployed CAS Harness fleet control-plane gates. "
            "This does not perform real 300B model inference."
        )
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Deployed customer CAS Harness API base URL. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=(
            "Requested worker count for the control-plane test. "
            f"Default: {DEFAULT_WORKERS}."
        ),
    )
    parser.add_argument(
        "--bearer-token",
        default=None,
        help=(
            "Bearer token for protected distributed/fleet endpoints. "
            f"Defaults to ${TOKEN_ENV_VAR} when omitted."
        ),
    )
    args = parser.parse_args(argv)

    base = args.base_url.rstrip("/")
    worker_count = args.workers
    bearer_token = resolve_bearer_token(args.bearer_token)
    if worker_count < 2:
        raise SystemExit("--workers must be at least 2 for the partial-merge negative test")

    print("CAS Harness deployed fleet verification")
    print(f"Base URL: {base}")
    print(f"Requested workers: {worker_count}")
    if bearer_token:
        print("Authorization: bearer token configured")
    else:
        print("Authorization: none configured; protected deployments will return HTTP 401")
    print("Scope: control-plane/fleet receipt path only; no 300B model weights or inference are exercised.")
    print()

    step(1, "Create a 300B-scale distributed session")
    session = post_json(
        base,
        "/api/cas-harness/audit/distributed/session",
        {
            "model_id": "deploy-check/open-weight-300b",
            "weight_access": "open_weight",
            "parameter_count_b": 300,
            "num_layers": 3,
            "precision": "int4",
            "available_gpu_memory_gb": 80,
            "minimum_worker_count": worker_count,
        },
        bearer_token=bearer_token,
    )
    audit_id = session["audit_id"]
    require_gate(
        "create-distributed-session",
        session["total_workers"] == worker_count,
        f"expected {worker_count} workers, got {session['total_workers']}",
    )
    require_gate(
        "create-distributed-session",
        session["verdict"] is None,
        f"distributed session invented verdict {session['verdict']!r}",
    )
    ok(f"created control-plane session {audit_id} with {session['total_workers']} worker assignments")

    step(2, "Dispatch worker assignments")
    dispatch = post_json(
        base,
        f"/api/cas-harness/audit/distributed/session/{audit_id}/dispatch",
        None,
        bearer_token=bearer_token,
    )
    require_gate(
        "dispatch-workers",
        dispatch["status"] == "DISPATCHED",
        f"expected DISPATCHED, got {dispatch['status']!r}",
    )
    ok("assignments dispatched")

    step(3, "Prepare fleet jobs from assignments")
    fleet = post_json(
        base,
        f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/prepare",
        None,
        bearer_token=bearer_token,
    )
    require_no_lease_token_exposed("prepare-fleet-jobs", fleet)
    require_gate(
        "prepare-fleet-jobs",
        fleet["total_jobs"] == worker_count,
        f"expected {worker_count} fleet jobs, got {fleet['total_jobs']}",
    )
    require_gate(
        "prepare-fleet-jobs",
        fleet["verifier_gate_status"] == "waiting_for_workers",
        f"expected waiting_for_workers, got {fleet['verifier_gate_status']!r}",
    )
    ok("fleet jobs prepared; verifier is correctly waiting for workers")

    step(4, "Reject an unregistered worker lease")
    first_assignment = dispatch["worker_evidence"][0]
    unregistered = post_json_expect_error(
        base,
        f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/job/lease",
        {"worker_id": first_assignment["worker_id"]},
        gate="block-unregistered-lease",
        expected_status=409,
        bearer_token=bearer_token,
    )
    require_gate(
        "block-unregistered-lease",
        "Worker must register before leasing jobs" in unregistered,
        f"unexpected error body: {unregistered}",
    )
    ok("unregistered worker lease blocked")

    step(5, "Register one worker and lease one job")
    register_worker(base, first_assignment, dispatch["plan"]["model_id"], bearer_token=bearer_token)
    leased = post_json(
        base,
        f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/job/lease",
        {"worker_id": first_assignment["worker_id"]},
        bearer_token=bearer_token,
    )
    require_gate(
        "lease-registered-worker",
        leased["status"] == "leased",
        f"expected leased status, got {leased['status']!r}",
    )
    lease_token = leased.get("lease_token")
    require_gate(
        "lease-registered-worker",
        isinstance(lease_token, str) and bool(lease_token.strip()),
        "leased job did not include a lease token",
    )
    ok(f"leased {leased['job_id']}")

    step(6, "Reject a forged Evidence Packet fragment ref")
    forged = post_json_expect_error(
        base,
        f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/job/{leased['job_id']}/receipt",
        {
            "worker_id": first_assignment["worker_id"],
            "lease_token": lease_token,
            "produced_outputs": leased["expected_outputs"],
            "evidence_packet_fragment_ref": f"deploy-check-fragment://{leased['job_id']}",
        },
        gate="reject-forged-fragment-ref",
        expected_status=409,
        bearer_token=bearer_token,
    )
    require_gate(
        "reject-forged-fragment-ref",
        "fragment ref failed hash/assignment validation" in forged,
        f"unexpected error body: {forged}",
    )
    ok("forged fragment ref rejected")

    step(7, "Submit one content-addressed Evidence Packet fragment receipt")
    fragment_ref = build_evidence_fragment_ref(
        audit_id=audit_id,
        job_id=leased["job_id"],
        worker_id=first_assignment["worker_id"],
        model_id=dispatch["plan"]["model_id"],
        layer_start=leased["layer_start"],
        layer_end=leased["layer_end"],
        shard_id=leased["shard_id"],
        expected_outputs=leased["expected_outputs"],
        produced_outputs=leased["expected_outputs"],
        missing_outputs=[],
    )
    receipt = post_json(
        base,
        f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/job/{leased['job_id']}/receipt",
        {
            "worker_id": first_assignment["worker_id"],
            "lease_token": lease_token,
            "produced_outputs": leased["expected_outputs"],
            "evidence_packet_fragment_ref": fragment_ref,
        },
        bearer_token=bearer_token,
    )
    require_no_lease_token_exposed("submit-fragment-receipt", receipt)
    require_gate(
        "submit-fragment-receipt",
        receipt["completed_fragments"] == 1,
        f"expected one completed fragment, got {receipt['completed_fragments']}",
    )
    require_gate(
        "submit-fragment-receipt",
        receipt["verifier_gate_status"] == "waiting_for_workers",
        f"expected waiting_for_workers, got {receipt['verifier_gate_status']!r}",
    )
    ok("one fragment accepted; verifier remains blocked until all workers report")

    step(8, "Prove partial fleet merge is blocked")
    blocked_merge = post_json_expect_error(
        base,
        f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/merge",
        None,
        gate="block-partial-fleet-merge",
        expected_status=409,
        bearer_token=bearer_token,
    )
    require_gate(
        "block-partial-fleet-merge",
        "every assigned job returns a receipt" in blocked_merge,
        f"unexpected error body: {blocked_merge}",
    )
    ok("partial fleet merge blocked")

    step(9, "Confirm distributed merge still cannot fake ACCEPT")
    merged_distributed = post_json(
        base,
        f"/api/cas-harness/audit/distributed/session/{audit_id}/merge",
        None,
        bearer_token=bearer_token,
    )
    require_gate(
        "block-fake-accept",
        merged_distributed["verdict"] is None,
        f"distributed merge invented verdict {merged_distributed['verdict']!r}",
    )
    ok("distributed merge still has no ACCEPT")
    print()
    print("PASS: deployed fleet control-plane receipt path enforces registration, leases, receipts, and no fake ACCEPT.")
    print("PASS SCOPE: control-plane/fleet receipt path only; no real 300B inference was claimed or performed.")
    return 0


def register_worker(
    base: str,
    assignment: dict[str, Any],
    model_id: str,
    *,
    bearer_token: str | None = None,
) -> dict[str, Any]:
    return post_json(
        base,
        "/api/cas-harness/audit/distributed/fleet/worker/register",
        {
            "worker_id": assignment["worker_id"],
            "model_id": model_id,
            "worker_url": f"https://{assignment['worker_id']}.deploy-check.internal",
            "gpu_type": "deploy-check",
            "capacity": 1,
            "supported_methods": assignment["assigned_methods"],
        },
        bearer_token=bearer_token,
    )


def post_json(
    base: str,
    path: str,
    payload: dict[str, Any] | None,
    *,
    bearer_token: str | None = None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    authorization = authorization_header(bearer_token)
    if authorization:
        headers["Authorization"] = authorization
    request = Request(
        f"{base}{path}",
        data=body,
        headers=headers,
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json_expect_error(
    base: str,
    path: str,
    payload: dict[str, Any] | None,
    *,
    gate: str,
    expected_status: int,
    bearer_token: str | None = None,
) -> str:
    try:
        post_json(base, path, payload, bearer_token=bearer_token)
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        require_gate(
            gate,
            exc.code == expected_status,
            f"expected HTTP {expected_status}, got {exc.code}: {body}",
        )
        return body
    raise GateFailure(gate, f"expected HTTP {expected_status} for {path}")


def resolve_bearer_token(cli_token: str | None) -> str | None:
    token = _clean_token(cli_token)
    if token:
        return token
    return _clean_token(os.environ.get(TOKEN_ENV_VAR))


def authorization_header(token: str | None) -> str | None:
    cleaned = _clean_token(token)
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
) -> str:
    payload = {
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
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"cas-fragment://{audit_id}/{job_id}/{worker_id}/{shard_id}/sha256:{digest}"


def require_no_lease_token_exposed(gate: str, payload: Any) -> None:
    paths = _find_key_paths(payload, "lease_token")
    require_gate(
        gate,
        not paths,
        f"non-lease fleet response exposed lease_token at {', '.join(paths[:5])}",
    )


def _find_key_paths(value: Any, target_key: str, path: str = "$") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key == target_key:
                paths.append(child_path)
            paths.extend(_find_key_paths(child, target_key, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(_find_key_paths(child, target_key, f"{path}[{index}]"))
    return paths


def _clean_token(token: str | None) -> str | None:
    if token is None:
        return None
    stripped = token.strip()
    return stripped or None


def step(number: int, message: str) -> None:
    print(f"[{number:02d}] {message}")


def ok(message: str) -> None:
    print(f"     OK - {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def require_gate(gate: str, condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(gate, message)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateFailure as exc:
        print(f"FAIL GATE: {exc.gate}", file=sys.stderr)
        print(f"DETAIL: {exc.message}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
