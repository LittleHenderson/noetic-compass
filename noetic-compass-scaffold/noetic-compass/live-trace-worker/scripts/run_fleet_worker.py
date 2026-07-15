"""Run one CAS Harness distributed Probe Worker daemon.

Example dry-run control-plane check:

    python scripts/run_fleet_worker.py \
      --api-base-url https://cas-harness-customer-api.onrender.com \
      --audit-id cas-dist-... \
      --worker-id probe-worker-001 \
      --model-id customer/open-70b \
      --tenant-id "$CAS_FLEET_TENANT_ID" \
      --service-credential "$CAS_FLEET_SERVICE_CREDENTIAL" \
      --dry-run

Example real executor bridge:

    python scripts/run_fleet_worker.py ... -- python run_probe_shard.py

Everything after ``--`` is executed without a shell and must write JSON to
``CAS_FLEET_RESULT_PATH``.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.runtime.fleet_worker import (  # noqa: E402
    CommandFleetJobExecutor,
    DryRunFleetJobExecutor,
    FleetWorkerConfig,
    FleetWorkerDaemon,
)


DEFAULT_METHODS = (
    "foundation_probe",
    "inversion_scan",
    "blindspot_detection",
    "verification_stack",
    "targeted_ablation",
    "matched_controls",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a CAS Harness fleet Probe Worker.")
    parser.add_argument("--api-base-url", default=os.environ.get("CAS_FLEET_API_BASE_URL"))
    parser.add_argument("--audit-id", default=os.environ.get("CAS_FLEET_AUDIT_ID"))
    parser.add_argument("--worker-id", default=os.environ.get("CAS_FLEET_WORKER_ID"))
    parser.add_argument("--model-id", default=os.environ.get("CAS_FLEET_MODEL_ID"))
    parser.add_argument("--worker-url", default=os.environ.get("CAS_FLEET_WORKER_URL", "http://localhost:8080"))
    parser.add_argument("--gpu-type", default=os.environ.get("CAS_FLEET_GPU_TYPE", "unknown-gpu"))
    parser.add_argument("--tenant-id", default=os.environ.get("CAS_FLEET_TENANT_ID"))
    parser.add_argument(
        "--service-credential",
        default=os.environ.get("CAS_FLEET_SERVICE_CREDENTIAL"),
        help="Server-issued fleet credential (prefer CAS_FLEET_SERVICE_CREDENTIAL over CLI).",
    )
    parser.add_argument("--bearer-token", default=os.environ.get("CAS_HARNESS_API_TOKEN"))
    parser.add_argument("--capacity", type=int, default=int(os.environ.get("CAS_FLEET_CAPACITY", "1")))
    parser.add_argument("--lease-seconds", type=int, default=int(os.environ.get("CAS_FLEET_LEASE_SECONDS", "900")))
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=float(os.environ.get("CAS_FLEET_POLL_INTERVAL_SECONDS", "5")),
    )
    parser.add_argument("--evidence-dir", default=os.environ.get("CAS_FLEET_EVIDENCE_DIR", "fleet-evidence"))
    parser.add_argument("--max-jobs", type=int, default=int(os.environ.get("CAS_FLEET_MAX_JOBS", "1")))
    parser.add_argument(
        "--supported-method",
        action="append",
        dest="supported_methods",
        default=None,
        help="Repeat to override supported methods. Defaults to all current planner methods.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use the control-plane dry-run executor. Does not claim model inference.",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Real probe command to execute after '--'.",
    )
    args = parser.parse_args(argv)

    missing = [
        name
        for name in ("api_base_url", "audit_id", "worker_id", "model_id")
        if not getattr(args, name)
    ]
    if missing:
        parser.error("missing required settings: " + ", ".join("--" + item.replace("_", "-") for item in missing))
    command = tuple(item for item in args.command if item != "--")
    if args.dry_run and command:
        parser.error("choose either --dry-run or a real probe command, not both")
    if not args.dry_run and not command:
        parser.error("provide a real probe command after '--' or pass --dry-run for control-plane verification")

    config = FleetWorkerConfig(
        api_base_url=args.api_base_url,
        audit_id=args.audit_id,
        worker_id=args.worker_id,
        model_id=args.model_id,
        worker_url=args.worker_url,
        gpu_type=args.gpu_type,
        supported_methods=tuple(args.supported_methods or DEFAULT_METHODS),
        tenant_id=args.tenant_id,
        service_credential=args.service_credential,
        bearer_token=args.bearer_token,
        capacity=args.capacity,
        lease_seconds=args.lease_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
        max_jobs=args.max_jobs,
        evidence_dir=Path(args.evidence_dir),
    )
    executor = DryRunFleetJobExecutor() if args.dry_run else CommandFleetJobExecutor(command)
    results = asyncio.run(_run(config, executor))
    for result in results:
        print(
            f"{result.status}"
            + (f" job={result.job_id}" if result.job_id else "")
            + (f" fragment={result.evidence_packet_fragment_ref}" if result.evidence_packet_fragment_ref else "")
            + (f" error={result.error_message}" if result.error_message else "")
        )
    return 0 if all(result.status != "failed" for result in results) else 1


async def _run(config: FleetWorkerConfig, executor) -> list:
    daemon = FleetWorkerDaemon(config, executor)
    try:
        return await daemon.run_loop()
    finally:
        await daemon.close()


if __name__ == "__main__":
    raise SystemExit(main())
