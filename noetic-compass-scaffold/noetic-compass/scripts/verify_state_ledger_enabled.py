"""Verify a deployed customer CAS Harness API has a clean enabled state ledger.

This is the hosted counterpart of the local operational-enable evidence in
``docs/working/production_readiness/14_operational_enable_evidence_2026_06_02.md``.
It drives ONE real distributed CAS Harness audit lifecycle over real HTTP against a
deployed service, then reads ``GET /api/state-ledger/status`` to prove the strangler-fig
``LedgerMirror`` ran clean under real service traffic:

    posture is an ENABLED posture (not "dark"),
    the phase's READ ODOMETER grew under our traffic, and
    divergence_tally.divergences_found == 0  (last_divergence is null).

The read odometer is phase-dependent, because the live read path differs by posture:

    shadow posture          -> divergence_tally.reads_compared   (dict-authoritative; every
                               mirrored read also shadow-compares the ledger, so this climbs)
    read-authority posture  -> divergence_tally.reads_served     (ledger-authoritative; the
                               ledger SERVES the read so there is no shadow-compare -- under
                               read-authority reads_compared is FROZEN and reads_served climbs)

Watching reads_compared after the read-authority flip would wrongly look like a dead system
(it cannot move once the ledger serves reads); this script watches whichever odometer the
OBSERVED posture makes live. Note the honesty asymmetry this implies: the read-FIDELITY
proof (ledger reads MATCH the dicts) comes from the shadow watch, where shadow_compare runs;
the read-authority watch proves the ledger can SERVE as sole read authority (the lifecycle
runs clean on ledger reads) and that the dual-write stayed clean (divergences_found == 0
keeps the dicts a valid rollback target). That is exactly why step 4 is gated behind a clean
shadow watch -- run --require-posture shadow first, then --require-posture read-authority.

It covers BOTH rollout gates with one flag:

    --require-posture shadow          steps 1-3 (NC_STATE_LEDGER_READ_AUTHORITY=false)
                                      expect posture == enabled_shadow_dict_authoritative
                                      watch divergence_tally.reads_compared
    --require-posture read-authority  step 4    (NC_STATE_LEDGER_READ_AUTHORITY=true)
                                      expect posture == enabled_ledger_read_authoritative
                                      watch divergence_tally.reads_served
    --require-posture any-enabled     accept either enabled posture; watch the matching odometer

Auth: it fetches a JWT from POST /auth/token (the server signs with ITS OWN secret),
so it works against a hosted service whose NC_JWT_SECRET we do not know. Pass an
explicit token with --bearer-token / $CAS_HARNESS_API_TOKEN to override.

Standalone on purpose: like scripts/verify_evidence_anchor_deployed.py, it re-implements
the pure fragment-ref builder inline so it needs no PYTHONPATH and no `api` import. The
algorithm must match the deployed server's build_evidence_fragment_ref; run this script
from the same commit that is deployed.

Honesty boundary: this proves the mirror is correct (zero divergence) and durable to the
process's own reads under real hosted traffic. On a Render free instance the SQLite ledger
lives on an EPHEMERAL filesystem (/tmp), so this does NOT prove cross-restart durability;
multi-host Postgres durability was proven separately (commit c32f639, PG 16.4, 10/10).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "https://cas-harness-customer-api.onrender.com"
TOKEN_ENV_VAR = "CAS_HARNESS_API_TOKEN"

POSTURE_SHADOW = "enabled_shadow_dict_authoritative"
POSTURE_READ_AUTHORITY = "enabled_ledger_read_authoritative"
POSTURE_DARK = "dark"

REQUIRED_POSTURES = {
    "shadow": {POSTURE_SHADOW},
    "read-authority": {POSTURE_READ_AUTHORITY},
    "any-enabled": {POSTURE_SHADOW, POSTURE_READ_AUTHORITY},
}


class LedgerWatchFailure(AssertionError):
    """Raised when a named ledger-watch gate fails."""

    def __init__(self, gate: str, message: str) -> None:
        super().__init__(f"{gate}: {message}")
        self.gate = gate
        self.message = message


# Which divergence_tally odometer is the live read denominator for a posture. Shadow
# posture serves reads from the dicts and shadow-compares the ledger on each, so
# reads_compared climbs. Read-authority posture serves reads FROM the ledger (no
# shadow-compare), so reads_compared is frozen and reads_served climbs. The watch must
# follow the posture or it would gate on a deliberately-inert counter -- the exact bug
# this maps around: pre-fix the script always watched reads_compared and so could never
# pass --require-posture read-authority.
READ_ODOMETER_BY_POSTURE = {
    POSTURE_SHADOW: "reads_compared",
    POSTURE_READ_AUTHORITY: "reads_served",
}


def read_odometer_key(posture: str) -> str:
    """The divergence_tally counter that is the live read denominator for ``posture``."""
    key = READ_ODOMETER_BY_POSTURE.get(posture)
    if key is None:
        raise LedgerWatchFailure(
            "read-odometer",
            f"no live read odometer defined for posture {posture!r}; expected one of "
            f"{sorted(READ_ODOMETER_BY_POSTURE)}",
        )
    return key


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify a deployed customer CAS Harness API has a clean enabled state ledger."
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Deployed customer CAS Harness API base URL. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--bearer-token",
        default=None,
        help=f"Bearer token for protected endpoints. Defaults to ${TOKEN_ENV_VAR}.",
    )
    parser.add_argument(
        "--username",
        default="state-ledger-watch",
        help="Username used when fetching a demo JWT from /auth/token.",
    )
    parser.add_argument(
        "--require-posture",
        choices=("shadow", "read-authority", "any-enabled"),
        default="shadow",
        help=(
            "Required ledger posture. 'shadow' = steps 1-3 "
            "(enabled_shadow_dict_authoritative); 'read-authority' = step 4 "
            "(enabled_ledger_read_authoritative); 'any-enabled' = either. Default: shadow."
        ),
    )
    parser.add_argument(
        "--min-reads",
        type=int,
        default=1,
        help=(
            "Fail unless the posture's live read odometer grows by at least this many under "
            "our traffic (reads_compared in shadow, reads_served in read-authority). Default: 1."
        ),
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=3,
        help="How many times to touch every ledger-mirrored read site. Default: 3.",
    )
    parser.add_argument(
        "--health-timeout",
        type=float,
        default=120.0,
        help="Seconds to wait for /health (free dynos cold-start slowly). Default: 120.",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Optional directory to write status_before.json / status_after.json / result.json.",
    )
    args = parser.parse_args(argv)

    base = args.base_url.rstrip("/")
    required = REQUIRED_POSTURES[args.require_posture]

    print("State-ledger ENABLED deployment watch")
    print(f"Base URL: {base}")
    print(f"Required posture: {args.require_posture} -> {sorted(required)}")
    print("Scope: dict-vs-ledger shadow-compare under real HTTP traffic; no real model inference.")
    print()

    step(1, "Wait for the service to be healthy")
    wait_healthy(base, args.health_timeout)
    token = resolve_bearer_token(args.bearer_token)
    token_source = "provided"
    if token is None:
        token = fetch_demo_token(base, args.username)
        token_source = "/auth/token"
    ok(f"healthy; authorization via {token_source}")

    step(2, "Read ledger status BEFORE our traffic")
    status_before = get_status(base, bearer_token=token)
    posture_before = require_string(status_before, "posture", "status-before")
    require_gate(
        "ledger-enabled",
        posture_before in required,
        ledger_posture_hint(posture_before, required),
    )
    # The live read odometer is posture-dependent (shadow -> reads_compared,
    # read-authority -> reads_served); watch the one the observed posture makes live.
    odometer = read_odometer_key(posture_before)
    reads_before = tally_int(status_before, odometer)
    ok(f"posture={posture_before} {odometer}={reads_before}")

    step(3, "Drive one real distributed audit lifecycle")
    audit_id, model_id, workers = create_audit(base, bearer_token=token)
    ok(f"created {audit_id} model={model_id} workers={len(workers)}")
    post_json(base, f"/api/cas-harness/audit/distributed/session/{audit_id}/dispatch", None, bearer_token=token)
    for worker in workers:
        register_worker(base, worker, model_id, bearer_token=token)
    prepared = post_json(
        base,
        f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/prepare",
        None,
        bearer_token=token,
    )
    ok(f"dispatched + registered {len(workers)} workers + prepared total_jobs={prepared.get('total_jobs')}")

    step(4, "Lease + receipt every fleet job")
    receipts = drain_jobs(base, audit_id, workers, model_id, bearer_token=token)
    merged = post_json(
        base,
        f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/merge",
        None,
        bearer_token=token,
    )
    ok(f"receipts={receipts} merged status={merged.get('status')} gate={merged.get('verifier_gate_status')}")

    step(5, f"Touch every ledger-mirrored read site x{args.rounds}")
    touch_read_sites(base, audit_id, rounds=args.rounds, bearer_token=token)
    ok("read sites touched")

    step(6, "Read ledger status AFTER our traffic and assert zero divergence")
    status_after = get_status(base, bearer_token=token)
    posture_after = require_string(status_after, "posture", "status-after")
    require_gate(
        "posture-after",
        posture_after in required,
        f"expected posture in {sorted(required)}, got {posture_after!r}",
    )
    # Pin the odometer to the observed posture. A posture change mid-run would make the
    # before/after delta compare two different counters, so reject it explicitly.
    odometer_after = read_odometer_key(posture_after)
    require_gate(
        "posture-stable",
        odometer_after == odometer,
        f"posture changed under our traffic ({posture_before!r}->{posture_after!r}); read "
        f"odometer moved {odometer!r}->{odometer_after!r}, before/after delta is not comparable",
    )
    reads_after = tally_int(status_after, odometer_after)
    divs_after = tally_int(status_after, "divergences_found")
    last_div = (status_after.get("divergence_tally") or {}).get("last_divergence")

    require_gate(
        "reads-grew",
        reads_after >= reads_before + args.min_reads and reads_after > 0,
        f"expected {odometer_after} to grow by >= {args.min_reads} from {reads_before}; got {reads_after}",
    )
    require_gate(
        "zero-divergence",
        divs_after == 0 and last_div is None,
        f"expected 0 divergences and null last_divergence; got divergences_found={divs_after} last_divergence={last_div!r}",
    )
    ok(
        f"posture={posture_after} {odometer_after}={reads_before}->{reads_after} "
        f"divergences_found={divs_after} last_divergence={last_div!r}"
    )

    tally_after = status_after.get("divergence_tally") or {}
    result = {
        "base_url": base,
        "require_posture": args.require_posture,
        "audit_id": audit_id,
        "posture": posture_after,
        "read_odometer": odometer_after,
        "reads_before": reads_before,
        "reads_after": reads_after,
        "reads_compared": tally_after.get("reads_compared"),
        "reads_served": tally_after.get("reads_served"),
        "divergences_found": divs_after,
        "last_divergence": last_div,
        "audit_count": status_after.get("audit_count"),
        "fleet_counts": status_after.get("fleet_counts"),
        "workers": len(workers),
        "receipts": receipts,
        "pass": True,
    }
    if args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)
        write_json(args.out_dir, "status_before.json", status_before)
        write_json(args.out_dir, "status_after.json", status_after)
        write_json(args.out_dir, "result.json", result)

    print()
    print("STATUS_BEFORE:", json.dumps(status_before))
    print("STATUS_AFTER:", json.dumps(status_after))
    print("LEDGER_WATCH_RESULT:", json.dumps(result))
    print()
    print(
        f"PASS: state-ledger {posture_after}; {odometer_after} {reads_before}->{reads_after} "
        f"(+{reads_after - reads_before} under our traffic), 0 divergences."
    )
    return 0


# --- lifecycle helpers --------------------------------------------------------


def create_audit(base: str, *, bearer_token: str) -> tuple[str, str, list[Mapping[str, Any]]]:
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
            "accept_audit_data_capture": True,
        },
        bearer_token=bearer_token,
    )
    audit_id = require_string(audit, "audit_id", "create-audit")
    plan = require_mapping(audit, "plan", "create-audit")
    model_id = require_string(plan, "model_id", "create-audit")
    workers = require_list(audit, "worker_evidence", "create-audit")
    return audit_id, model_id, workers


def register_worker(base: str, worker: Mapping[str, Any], model_id: str, *, bearer_token: str) -> None:
    worker_id = require_string(worker, "worker_id", "register-worker")
    try:
        post_json(
            base,
            "/api/cas-harness/audit/distributed/fleet/worker/register",
            {
                "worker_id": worker_id,
                "model_id": model_id,
                "worker_url": f"https://{worker_id}.ledger-watch.internal",
                "gpu_type": "ledger-watch",
                "capacity": 1,
                "supported_methods": require_string_list(worker, "assigned_methods", "register-worker"),
            },
            bearer_token=bearer_token,
        )
    except LedgerWatchFailure as exc:
        # Re-running against a warm dyno can hit an already-registered worker; a
        # heartbeat keeps it alive and is a no-op for our purposes.
        if exc.gate != "http-request" or "already registered" not in exc.message.lower():
            raise
        post_json(
            base,
            f"/api/cas-harness/audit/distributed/fleet/worker/{worker_id}/heartbeat",
            None,
            bearer_token=bearer_token,
        )


def drain_jobs(
    base: str,
    audit_id: str,
    workers: list[Mapping[str, Any]],
    model_id: str,
    *,
    bearer_token: str,
) -> int:
    receipts = 0
    for worker in workers:
        worker_id = require_string(worker, "worker_id", "lease-job")
        while True:
            job = post_json(
                base,
                f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/job/lease",
                {"worker_id": worker_id, "lease_seconds": 900},
                bearer_token=bearer_token,
                allow_null=True,
            )
            if job is None:
                break
            produced = require_string_list(job, "expected_outputs", "lease-job")
            assigned_worker_id = require_string(job, "assigned_worker_id", "lease-job")
            job_id = require_string(job, "job_id", "lease-job")
            fragment_ref = build_evidence_fragment_ref(
                audit_id=audit_id,
                job_id=job_id,
                worker_id=assigned_worker_id,
                model_id=model_id,
                layer_start=require_int(job, "layer_start", "lease-job"),
                layer_end=require_int(job, "layer_end", "lease-job"),
                shard_id=require_string(job, "shard_id", "lease-job"),
                expected_outputs=produced,
                produced_outputs=produced,
                missing_outputs=[],
            )
            post_json(
                base,
                f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/job/{job_id}/receipt",
                {
                    "worker_id": assigned_worker_id,
                    "lease_token": require_string(job, "lease_token", "lease-job"),
                    "produced_outputs": produced,
                    "evidence_packet_fragment_ref": fragment_ref,
                    "job_status": "completed",
                },
                bearer_token=bearer_token,
            )
            receipts += 1
    require_gate("receipts", receipts > 0, "no fleet jobs were leased; nothing to receipt")
    return receipts


def touch_read_sites(base: str, audit_id: str, *, rounds: int, bearer_token: str) -> None:
    read_paths = [
        f"/api/cas-harness/audit/distributed/session/{audit_id}",
        "/api/cas-harness/audit/distributed/sessions",
        f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet",
        "/api/cas-harness/audit/distributed/fleet/runs",
        "/api/cas-harness/audit/distributed/fleet/workers",
    ]
    for _ in range(max(rounds, 0)):
        for path in read_paths:
            get_json(base, path, bearer_token=bearer_token)


def get_status(base: str, *, bearer_token: str) -> dict[str, Any]:
    try:
        return get_json(base, "/api/state-ledger/status", bearer_token=bearer_token)
    except LedgerWatchFailure as exc:
        if exc.gate == "http-request" and "HTTP 404" in exc.message:
            raise LedgerWatchFailure(
                "ledger-route-present",
                "GET /api/state-ledger/status returned 404 -> the deployed build does not "
                "include the state-ledger router. Deploy the branch that contains it "
                "(merge to the Render-connected deploy branch), then re-run.",
            ) from exc
        raise


def ledger_posture_hint(posture: str, required: set[str]) -> str:
    if posture == POSTURE_DARK:
        return (
            "ledger posture is 'dark' -> NC_STATE_LEDGER_ENABLED is not true on this "
            "deployment. Set NC_STATE_LEDGER_ENABLED=true (and READ_AUTHORITY per the gate) "
            "in the Render env and redeploy, then re-run."
        )
    return f"expected posture in {sorted(required)}, got {posture!r}"


# --- HTTP plumbing (standalone; mirrors verify_evidence_anchor_deployed.py) ---


def wait_healthy(base: str, timeout_s: float) -> None:
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        try:
            request = Request(f"{base}/health", headers={"Accept": "application/json"}, method="GET")
            with urlopen(request, timeout=30) as response:
                if response.status == 200:
                    return
        except HTTPError as exc:
            last = f"HTTP {exc.code}"
        except (URLError, TimeoutError, OSError) as exc:  # connection refused / cold start
            last = repr(exc)
        time.sleep(2.0)
    raise LedgerWatchFailure("health", f"service did not become healthy in {timeout_s}s; last={last}")


def fetch_demo_token(base: str, username: str) -> str:
    body = post_json(base, "/auth/token", {"username": username}, bearer_token=None)
    return require_string(body, "token", "fetch-demo-token")


def post_json(
    base: str,
    path: str,
    payload: Mapping[str, Any] | None,
    *,
    bearer_token: str | None,
    allow_null: bool = False,
) -> Any:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    authorization = authorization_header(bearer_token)
    if authorization:
        headers["Authorization"] = authorization
    request = Request(f"{base}{path}", data=body, headers=headers, method="POST")
    return read_json(request, allow_null=allow_null)


def get_json(base: str, path: str, *, bearer_token: str | None) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    authorization = authorization_header(bearer_token)
    if authorization:
        headers["Authorization"] = authorization
    request = Request(f"{base}{path}", headers=headers, method="GET")
    return read_json(request)


def read_json(request: Request, *, allow_null: bool = False) -> Any:
    try:
        with urlopen(request, timeout=90) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise LedgerWatchFailure("http-request", f"HTTP {exc.code} for {request.full_url}: {detail}") from exc
    parsed = json.loads(raw) if raw.strip() else None
    if parsed is None and allow_null:
        return None
    if not isinstance(parsed, dict):
        raise LedgerWatchFailure("http-request", f"non-object JSON response from {request.full_url}: {raw[:200]!r}")
    return parsed


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
    if evidence_packet_fragment_payload is not None:
        payload["fragment_payload_sha256"] = hashlib.sha256(
            json.dumps(
                evidence_packet_fragment_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("utf-8")
        ).hexdigest()
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"cas-fragment://{audit_id}/{job_id}/{worker_id}/{shard_id}/sha256:{digest}"


# --- small parse/assert helpers ----------------------------------------------


def tally_int(status: Mapping[str, Any], key: str) -> int:
    tally = status.get("divergence_tally")
    if not isinstance(tally, Mapping):
        raise LedgerWatchFailure("status-shape", f"status missing divergence_tally object: {status!r}")
    value = tally.get(key)
    if not isinstance(value, int):
        raise LedgerWatchFailure("status-shape", f"divergence_tally.{key} must be an integer, got {value!r}")
    return value


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


def require_mapping(payload: Mapping[str, Any], key: str, gate: str) -> Mapping[str, Any]:
    value = payload.get(key)
    require_gate(gate, isinstance(value, Mapping), f"{key!r} must be an object")
    return value


def require_list(payload: Mapping[str, Any], key: str, gate: str) -> list[Any]:
    value = payload.get(key)
    require_gate(gate, isinstance(value, list) and len(value) > 0, f"{key!r} must be a non-empty list")
    return value


def require_string(payload: Mapping[str, Any], key: str, gate: str) -> str:
    value = payload.get(key)
    require_gate(gate, isinstance(value, str) and bool(value.strip()), f"{key!r} must be a non-empty string")
    return value


def require_int(payload: Mapping[str, Any], key: str, gate: str) -> int:
    value = payload.get(key)
    require_gate(gate, isinstance(value, int), f"{key!r} must be an integer")
    return value


def require_string_list(payload: Mapping[str, Any], key: str, gate: str) -> list[str]:
    value = payload.get(key)
    require_gate(gate, isinstance(value, list) and len(value) > 0, f"{key!r} must be a non-empty list")
    cleaned = [item for item in value if isinstance(item, str) and item.strip()]
    require_gate(gate, len(cleaned) == len(value), f"{key!r} must contain only non-empty strings")
    return cleaned


def clean_token(token: str | None) -> str | None:
    if token is None:
        return None
    stripped = token.strip()
    return stripped or None


def write_json(out_dir: str, name: str, obj: Any) -> None:
    with open(os.path.join(out_dir, name), "w", encoding="utf-8") as handle:
        json.dump(obj, handle, indent=2)


def step(number: int, message: str) -> None:
    print(f"[{number:02d}] {message}")


def ok(message: str) -> None:
    print(f"     OK - {message}")


def require_gate(gate: str, condition: bool, message: str) -> None:
    if not condition:
        raise LedgerWatchFailure(gate, message)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LedgerWatchFailure as exc:
        print(f"FAIL GATE: {exc.gate}", file=sys.stderr)
        print(f"DETAIL: {exc.message}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:  # noqa: BLE001 - surface any unexpected error as a clean failure
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
