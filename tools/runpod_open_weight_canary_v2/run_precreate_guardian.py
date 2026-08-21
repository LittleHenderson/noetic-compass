"""GitHub-hosted driver for the pre-create guardian.

This is the entry point the package README named as missing: it runs the
guardian state machine (`precreate_guardian_offline`) against the live RunPod
transport (`precreate_guardian_runpod_adapter`) from an independent host, so a
Pod created but never acknowledged can still be found by its exact name and
stopped.

It has two phases, driven by `--phase`:

  arm        Take the pre-create inventory and write the arm receipt. This must
             complete, and its receipt must be durably published, BEFORE any
             create request is sent. It makes no create call and cannot.
  supervise  Poll independently after the arm, recover the one bound target by
             its exact high-entropy name, and stop it at the deadline.

Authority boundary: the only provider object reachable from here is
`RunPodGuardianAdapter`, which can inventory, GET one Pod, and STOP one Pod.
There is no create or delete path in this file or anything it imports for
transport. Running this can never start billing; it can only end it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# On a CI runner, working-directory does not put this file's own directory on
# sys.path, so its sibling imports must be made resolvable explicitly.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from precreate_guardian_offline import (
    ArmSpec,
    arm_guardian,
    canonical_json_bytes,
    supervise_after_arm,
)
from precreate_guardian_runpod_adapter import (
    GuardianTransportError,
    RunPodGuardianAdapter,
)

MAX_RECEIPT_BYTES = 1_000_000


class SystemClock:
    """Real clock. Separate class so tests can inject a deterministic one."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


def _write_new(path: Path, value: dict[str, Any]) -> None:
    """Write once. Refuses to overwrite, so a receipt can never be replaced."""
    raw = canonical_json_bytes(value)
    if len(raw) > MAX_RECEIPT_BYTES:
        raise SystemExit("RECEIPT_TOO_LARGE")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "xb") as handle:
            handle.write(raw)
    except FileExistsError:
        raise SystemExit("RECEIPT_ALREADY_EXISTS_REFUSING_OVERWRITE") from None


def _required_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value.strip():
        raise SystemExit(f"MISSING_REQUIRED_ENVIRONMENT_{name}")
    return value.strip()


def _read_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > MAX_RECEIPT_BYTES:
        raise SystemExit("INPUT_RECEIPT_TOO_LARGE")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise SystemExit("INPUT_RECEIPT_NOT_AN_OBJECT")
    return value


def _arm(args: argparse.Namespace) -> int:
    request_bytes = Path(args.exact_create_request).read_bytes()
    spec = ArmSpec(
        pod_name=args.pod_name,
        exact_create_request_sha256=args.exact_create_request_sha256,
        source_commit_sha=args.source_commit,
        oci_image_digest=args.oci_image_digest,
        creation_window_start_utc=args.creation_window_start_utc,
        creation_window_end_utc=args.creation_window_end_utc,
        hard_stop_deadline_utc=args.hard_stop_deadline_utc,
        github_repository=_required_env("GITHUB_REPOSITORY"),
        github_run_id=_required_env("GITHUB_RUN_ID"),
        github_run_attempt=_required_env("GITHUB_RUN_ATTEMPT"),
        github_sha=_required_env("GITHUB_SHA"),
    )
    adapter = RunPodGuardianAdapter()
    receipt = arm_guardian(
        spec,
        exact_create_request_bytes=request_bytes,
        provider=adapter,
        armed_at=SystemClock().now(),
    )
    _write_new(Path(args.arm_receipt), receipt)
    print(f"ARMED status={receipt['status']}")
    print(f"ARMED pod_name={receipt['pod_name']}")
    print(f"ARMED receipt_sha256={receipt['receipt_sha256']}")
    print(f"ARMED pre_arm_inventory_count={receipt['pre_arm_inventory_count']}")
    return 0


def _supervise(args: argparse.Namespace) -> int:
    arm_receipt = _read_json(Path(args.arm_receipt))
    adapter = RunPodGuardianAdapter()
    result = supervise_after_arm(
        arm_receipt,
        provider=adapter,
        clock=SystemClock(),
        poll_seconds=args.poll_seconds,
    )
    if result.binding_receipt is not None:
        _write_new(Path(args.binding_receipt), result.binding_receipt)
        print(f"BOUND pod_id={result.binding_receipt.get('pod_id')}")
    else:
        print("BOUND pod_id=NONE_OBSERVED")
    _write_new(Path(args.terminal_receipt), result.terminal_receipt)
    print(f"TERMINAL status={result.terminal_receipt.get('status')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("arm", "supervise"), required=True)
    parser.add_argument("--pod-name")
    parser.add_argument("--exact-create-request", type=Path)
    parser.add_argument("--exact-create-request-sha256")
    parser.add_argument("--source-commit")
    parser.add_argument("--oci-image-digest")
    parser.add_argument("--creation-window-start-utc")
    parser.add_argument("--creation-window-end-utc")
    parser.add_argument("--hard-stop-deadline-utc")
    parser.add_argument("--arm-receipt", type=Path, required=True)
    parser.add_argument("--binding-receipt", type=Path)
    parser.add_argument("--terminal-receipt", type=Path)
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    args = parser.parse_args(argv)

    try:
        if args.phase == "arm":
            required = (
                args.pod_name,
                args.exact_create_request,
                args.exact_create_request_sha256,
                args.source_commit,
                args.oci_image_digest,
                args.creation_window_start_utc,
                args.creation_window_end_utc,
                args.hard_stop_deadline_utc,
            )
            if not all(required):
                print("ARM_REQUIRES_FULL_SPEC")
                return 2
            return _arm(args)
        if not args.binding_receipt or not args.terminal_receipt:
            print("SUPERVISE_REQUIRES_BINDING_AND_TERMINAL_PATHS")
            return 2
        return _supervise(args)
    except GuardianTransportError as error:
        # Transport errors never carry credential material by construction.
        print(f"GUARDIAN_FAIL_CLOSED:{error}")
        return 3
    except SystemExit:
        raise
    except Exception as error:  # noqa: BLE001 - fail closed on the class only
        print(f"GUARDIAN_FAIL_CLOSED:{type(error).__name__}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
