"""watchdog_main.py -- the SEPARATE watchdog process (GATE 1A.2 s.9 + 1A.2R s.3
+ 1A.2R.2 + 1A.2R.2A + 1A.2R.2B + 1A.2R.2C).

Runs beside the campaign driver (started by infra/bootstrap.sh). Its timeout is
DERIVED from the owner-signed execution approval, not trusted from a
self-consistent file (1A.2R.2C):

STARTUP (once, inside the fail-closed boundary): the watchdog INDEPENDENTLY
verifies the detached execution approval against the frozen owner trust root and
derives the stale limit from the SIGNED per-job cap. It also binds the immutable
watchdog_authority.json that the pre-watchdog step wrote BEFORE it started, and
requires every field of that file to equal the derived value. The startup grace
and poll interval are FROZEN registered constants in REAL. A missing, forged, or
malformed authority fails closed (marker + termination + nonzero exit).

POLL LOOP: the authority is immutable in memory -- the loop never re-reads it
(so a rewrite can never be read half-written); each poll reads ONLY the atomic
heartbeat, and the sleep is INSIDE the boundary.

TERMINATION: an active protected lock is burned using coordinates DERIVED from
the verified approval (never from a mutable file, so a corrupted locator cannot
erase the burn); every burn outcome is recorded durably and NEVER swallowed.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exec.watchdog import Watchdog                      # noqa: E402
from exec.watchdog_authority import (authorized_lock_locator,  # noqa: E402
                                     load_verified_authority, resolve_timers,
                                     validate_lock_locator)
from exec.shutdown import ShutdownPath                  # noqa: E402


def _write_json_marker(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(payload, indent=2) + "\n")


def _write_termination_marker(evidence_dir: Path, reason: str, detail=None) -> None:
    payload = {"reason": reason}
    if detail is not None:
        payload["detail"] = detail
    _write_json_marker(evidence_dir / "WATCHDOG_TERMINATION.json", payload)


def _burn_if_protected(record, evidence_dir: Path, mode: str) -> None:
    """On a REAL termination, burn an ACTIVE protected lock using coordinates
    DERIVED from the verified approval (record) -- never from a mutable file, so a
    corrupted locator cannot erase the burn. The on-disk locator, if present, is a
    secondary confirmation validated against the authorized locator. Every outcome
    is recorded durably; NO burn exception is silently swallowed."""
    if mode != "REAL" or record is None:
        return
    authorized = authorized_lock_locator(record)
    locator_path = evidence_dir / "protected_lock_locator.json"
    if locator_path.is_file():                         # secondary confirmation
        try:
            validate_lock_locator(
                json.loads(locator_path.read_text(encoding="utf-8")), record)
        except Exception as exc:                        # noqa: BLE001
            _write_json_marker(
                evidence_dir / "WATCHDOG_LOCK_LOCATOR_INVALID.json",
                {"error": f"{type(exc).__name__}: {exc}", "authorized": authorized})
            # continue: burn via the AUTHORIZED coordinates regardless
    try:
        from exec.protected_lock import AwsProtectedLock
        awl = AwsProtectedLock(authorized["table_name"], authorized["region"])
        if awl.state(authorized["campaign_id"]) != "PROTECTED_RUNNING":
            _write_json_marker(
                evidence_dir / "WATCHDOG_BURN_SKIPPED.json",
                {"reason": "NO_ACTIVE_PROTECTED_LOCK",
                 "campaign_id": authorized["campaign_id"]})
            return
        rec = awl.burn(authorized["campaign_id"],
                       final_state_reason="WATCHDOG_ABANDONED",
                       result_or_failure_sha256="0" * 64)
        _write_json_marker(
            evidence_dir / "WATCHDOG_BURN_RECEIPT.json",
            {"outcome": "BURNED",
             "lock_receipt_sha256": rec.get("lock_receipt_sha256"),
             "campaign_id": authorized["campaign_id"]})
    except Exception as exc:                            # noqa: BLE001 -- record it
        _write_json_marker(
            evidence_dir / "WATCHDOG_BURN_FAILED.json",
            {"outcome": "BURN_FAILED", "error": f"{type(exc).__name__}: {exc}",
             "campaign_id": authorized["campaign_id"]})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True,
                    choices=["REAL", "SYNTHETIC_CONFORMANCE"])
    ap.add_argument("--heartbeat", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--approval", required=True,
                    help="the DETACHED execution approval (the authority source)")
    ap.add_argument("--prep-receipt", required=True)
    ap.add_argument("--package-root", required=True)
    ap.add_argument("--campaign-id", required=True)
    ap.add_argument("--authority", required=True,
                    help="watchdog_authority.json written BEFORE this process")
    ap.add_argument("--expected-commit", default=None)
    # honored ONLY in a conformance posture; IGNORED in REAL (frozen constants)
    ap.add_argument("--startup-grace-seconds", type=float, default=None)
    ap.add_argument("--poll-seconds", type=float, default=None)
    args = ap.parse_args()
    evidence = Path(args.evidence)
    shutdown = ShutdownPath(args.mode, evidence)
    launched_at = time.time()
    # STARTUP (once): verify the approval, derive the immutable timing law, bind
    # the authority file, resolve the frozen timers -- ALL inside the boundary.
    record = None
    try:
        record = load_verified_authority(
            mode=args.mode, approval_path=args.approval,
            prep_receipt_path=args.prep_receipt, package_root=args.package_root,
            expected_campaign_id=args.campaign_id, authority_path=args.authority,
            expected_commit=args.expected_commit)
        grace, poll = resolve_timers(args.mode, args.startup_grace_seconds,
                                     args.poll_seconds)
    except Exception as exc:                            # noqa: BLE001 -- fail closed
        _write_termination_marker(evidence, "WATCHDOG_INTERNAL_ERROR",
                                  type(exc).__name__)
        _burn_if_protected(record, evidence, args.mode)   # record None -> no-op
        shutdown.request_termination("WATCHDOG_INTERNAL_ERROR")
        return 2
    # POLL LOOP: the authority is immutable; each poll reads ONLY the atomic
    # heartbeat, and time.sleep is INSIDE the fail-closed boundary.
    while True:
        try:
            wd = Watchdog(Path(args.heartbeat), evidence,
                          record.stale_limit_seconds,
                          startup_grace_seconds=grace, launched_at=launched_at)
            alive = wd.poll_once(time.time())
            if not alive:
                _burn_if_protected(record, evidence, args.mode)
                shutdown.request_termination("WATCHDOG_TERMINATION")
                return 1
            time.sleep(poll)
        except Exception as exc:                        # noqa: BLE001 -- fail closed
            _write_termination_marker(evidence, "WATCHDOG_INTERNAL_ERROR",
                                      type(exc).__name__)
            _burn_if_protected(record, evidence, args.mode)
            shutdown.request_termination("WATCHDOG_INTERNAL_ERROR")
            return 2


if __name__ == "__main__":
    raise SystemExit(main())
