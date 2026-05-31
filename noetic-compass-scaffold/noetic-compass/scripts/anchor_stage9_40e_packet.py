"""WORM-anchor the GPT-NeoX-20B Stage 9 40E scoped-validation Evidence Packet.

This is the one operational step that lets the Audit Console show a *true* green
ACCEPT for the bundled Stage 9 40E packet instead of FLAG_FOR_HUMAN_REVIEW.

It loads the static Stage 9 40E packet, runs it through the same append-only
hash-log + external object-lock anchor that fleet-merged packets use, persists the
anchored copy into the Evidence Packet store, then re-reads the anchor to verify it.

It does not fabricate anything. The anchor receipt comes straight from the
configured anchor mode:

* unset / ``disabled``  -> external anchor status ``disabled``; NOT WORM; the
  console honestly stays at human review. (default, safe, no AWS needed)
* ``local``            -> same-host anchor; NOT WORM; still human review.
* ``s3`` + Object Lock -> a real ``boto3 put_object`` with ObjectLockMode +
  retain-until; re-read and confirmed; THIS is what flips the verdict to ACCEPT.

Run a real WORM anchor with (PowerShell):

    $env:CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR = "<dir the API also reads>"
    $env:CAS_HARNESS_EVIDENCE_ANCHOR_MODE = "s3"
    $env:CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET = "<object-lock-enabled bucket>"
    $env:CAS_HARNESS_EVIDENCE_ANCHOR_S3_REGION = "<region>"
    $env:CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE = "GOVERNANCE"
    $env:CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS = "3650"
    # plus AWS credentials in the environment / profile
    python -m scripts.anchor_stage9_40e_packet --require-object-lock

The bucket MUST have S3 Object Lock enabled at creation time and the credentials
must allow ``s3:PutObject`` with retention. Neither can be faked here.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from api.routes.evidence import load_stage9_40e_packet_payload_for_trace  # noqa: E402
from api.services.cas_harness_static_evidence_anchor import (  # noqa: E402
    anchor_static_evidence_packet,
    verify_anchored_static_packet,
)

_STAGE9_40E_TRACE_ID = "stage9-40e-original-baseline-readout-20260527"


class AnchorStepFailure(RuntimeError):
    """Raised when a named anchoring gate fails."""

    def __init__(self, gate: str, message: str) -> None:
        super().__init__(f"{gate}: {message}")
        self.gate = gate
        self.message = message


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="WORM-anchor the Stage 9 40E scoped-validation Evidence Packet."
    )
    parser.add_argument(
        "--trace-id",
        default=_STAGE9_40E_TRACE_ID,
        help=f"Static packet trace_id to anchor. Default: {_STAGE9_40E_TRACE_ID}",
    )
    parser.add_argument(
        "--require-object-lock",
        action="store_true",
        help=(
            "Fail unless the anchor is a real S3 object with verified Object Lock "
            "retention (i.e. the result actually flips the console to ACCEPT)."
        ),
    )
    args = parser.parse_args(argv)

    mode = os.environ.get("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "disabled").strip().lower() or "disabled"
    store_dir = os.environ.get("CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR", "(default temp dir)")

    print("CAS Harness Stage 9 40E WORM anchor")
    print(f"Trace ID: {args.trace_id}")
    print(f"Anchor mode: {mode}")
    print(f"Evidence Packet store dir: {store_dir}")
    print(
        "Note: this is a scoped project validation packet, not a per-customer "
        "production ACCEPT. WORM anchoring only proves the packet is tamper-evident."
    )
    print()

    packet = load_stage9_40e_packet_payload_for_trace(args.trace_id)
    anchored = anchor_static_evidence_packet(packet)
    anchor = _required_mapping(anchored.get("hashes"), "hashes").get("external_anchor")
    if not isinstance(anchor, Mapping):
        raise AnchorStepFailure("anchor-write", "anchored packet is missing an external_anchor receipt")

    verify = verify_anchored_static_packet(anchored)
    anchor_check = _find_check(verify, "merged_packet_external_anchor")
    notes = anchor_check.get("notes")
    notes_lower = notes.lower() if isinstance(notes, str) else ""

    print(f"Anchor status: {anchor.get('status')}  mode: {anchor.get('mode')}")
    print(f"Anchor URI:    {anchor.get('anchor_uri') or '(none)'}")
    print(f"Verify overall: {verify.get('overall')}")
    print(f"External-anchor check match: {anchor_check.get('match')}")
    print(f"External-anchor notes: {notes}")
    print()

    worm_retained = (
        anchor.get("status") == "anchored"
        and anchor.get("mode") == "s3"
        and verify.get("overall") == "all_match"
        and anchor_check.get("match") is True
        and "object was re-read" in notes_lower
        and "object lock" in notes_lower
        and "retention is active" in notes_lower
    )

    if args.require_object_lock and not worm_retained:
        raise AnchorStepFailure(
            "worm-retention",
            (
                "anchor is not WORM-retained. The console will correctly keep this "
                f"packet at human review. Anchor mode was {anchor.get('mode')!r}, "
                f"status {anchor.get('status')!r}, verify notes {notes!r}. Set "
                "CAS_HARNESS_EVIDENCE_ANCHOR_MODE=s3 with an Object-Lock bucket + "
                "credentials, then re-run."
            ),
        )

    if worm_retained:
        print("PASS: Stage 9 40E packet is WORM-retained. The Audit Console will now show ACCEPT.")
    else:
        print(
            "OK (not WORM): packet anchored at mode "
            f"{anchor.get('mode')!r}. This is the honest default -- the console "
            "stays at FLAG_FOR_HUMAN_REVIEW until a real S3 Object-Lock anchor exists."
        )
    print(f"Anchored packet store path: {anchored.get('hashes', {}).get('hash_log_path')}")
    print(json.dumps({"trace_id": anchored.get("trace_id"), "external_anchor": anchor}, indent=2))
    return 0 if (worm_retained or not args.require_object_lock) else 1


def _required_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AnchorStepFailure("anchor-write", f"{name} must be an object")
    return value


def _find_check(verify_response: Mapping[str, Any], artifact: str) -> Mapping[str, Any]:
    checks = verify_response.get("checks")
    if isinstance(checks, list):
        for check in checks:
            if isinstance(check, Mapping) and check.get("artifact") == artifact:
                return check
    raise AnchorStepFailure("anchor-verify", f"verify response missing {artifact!r} check")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AnchorStepFailure as exc:
        print(f"FAIL GATE: {exc.gate}", file=sys.stderr)
        print(f"DETAIL: {exc.message}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
