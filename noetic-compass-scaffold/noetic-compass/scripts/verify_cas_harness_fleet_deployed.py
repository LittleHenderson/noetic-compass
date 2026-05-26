"""Verify deployed CAS Harness fleet-executor gates.

This script intentionally does not require real model weights. It validates the
control-plane contract that a large-model distributed audit cannot move forward
without worker registration, job leases, and Evidence Packet fragment receipts.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://noetic-compass-api.onrender.com"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--workers", type=int, default=25)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    worker_count = args.workers
    if worker_count < 2:
        raise SystemExit("--workers must be at least 2 for the partial-merge negative test")

    print(f"CAS Harness fleet deploy verification: {base}")
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
    )
    audit_id = session["audit_id"]
    require(session["total_workers"] == worker_count, f"expected {worker_count} workers")
    require(session["verdict"] is None, "distributed session must not invent verdict")
    print(f"created distributed session {audit_id} with {session['total_workers']} workers")

    dispatch = post_json(base, f"/api/cas-harness/audit/distributed/session/{audit_id}/dispatch", None)
    require(dispatch["status"] == "DISPATCHED", "dispatch should mark assignments dispatched")
    print("dispatch ok")

    fleet = post_json(base, f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/prepare", None)
    require(fleet["total_jobs"] == worker_count, f"expected {worker_count} fleet jobs")
    require(fleet["verifier_gate_status"] == "waiting_for_workers", "fleet should wait for workers")
    print("fleet prepare ok")

    first_assignment = dispatch["worker_evidence"][0]
    unregistered = post_json_expect_error(
        base,
        f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/job/lease",
        {"worker_id": first_assignment["worker_id"]},
        expected_status=409,
    )
    require("Worker must register before leasing jobs" in unregistered, "unregistered lease must fail")
    print("unregistered lease blocked")

    register_worker(base, first_assignment, dispatch["plan"]["model_id"])
    leased = post_json(
        base,
        f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/job/lease",
        {"worker_id": first_assignment["worker_id"]},
    )
    require(leased["status"] == "leased", "registered worker should lease one assigned job")
    require(leased["lease_token"], "leased job must include lease token")
    print(f"leased {leased['job_id']}")

    receipt = post_json(
        base,
        f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/job/{leased['job_id']}/receipt",
        {
            "worker_id": first_assignment["worker_id"],
            "lease_token": leased["lease_token"],
            "produced_outputs": leased["expected_outputs"],
            "evidence_packet_fragment_ref": f"deploy-check-fragment://{leased['job_id']}",
        },
    )
    require(receipt["completed_fragments"] == 1, "one fragment should be complete")
    require(receipt["verifier_gate_status"] == "waiting_for_workers", "remaining workers should still block")
    print("one receipt accepted; verifier still blocked")

    blocked_merge = post_json_expect_error(
        base,
        f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/merge",
        None,
        expected_status=409,
    )
    require("every assigned job returns a receipt" in blocked_merge, "partial fleet merge must be blocked")
    print("partial merge blocked")

    merged_distributed = post_json(base, f"/api/cas-harness/audit/distributed/session/{audit_id}/merge", None)
    require(merged_distributed["verdict"] is None, "distributed merge must not accept before all receipts")
    print("distributed merge still has no ACCEPT")
    print("PASS: fleet deploy contract is enforcing registration, leases, receipts, and no fake ACCEPT")
    return 0


def register_worker(base: str, assignment: dict[str, Any], model_id: str) -> dict[str, Any]:
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
    )


def post_json(base: str, path: str, payload: dict[str, Any] | None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"{base}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json_expect_error(
    base: str,
    path: str,
    payload: dict[str, Any] | None,
    *,
    expected_status: int,
) -> str:
    try:
        post_json(base, path, payload)
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        require(exc.code == expected_status, f"expected HTTP {expected_status}, got {exc.code}: {body}")
        return body
    raise AssertionError(f"expected HTTP {expected_status} for {path}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
