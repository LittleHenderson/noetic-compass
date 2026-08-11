"""Archive a broken paper-proof evidence chain and start a clean one.

The July concurrent-writer defect left the index_tsmom_126 chain permanently
unverifiable (broken_link at record 11): the proof gate requires the WHOLE
chain to verify, so every day appended to that store is spent on a proof that
can never pass. This script implements the honest remediation:

  1. The broken store is MOVED (never deleted, never rewritten) into
     archive/<timestamp>/ next to its state sidecar, with a defect record
     capturing verify_chain_report() at archive time.
  2. A fresh, empty store takes its place. Day counting restarts at 0 - the
     price of a chain that can pass, and this script says so out loud.

It refuses to run when the chain verifies (nothing to remediate), and requires
the exact confirmation phrase, because restarting the counter is an owner
decision, not an operator convenience.

Boundary: this orchestrates local evidence files only. It does not place
trades, create broker ACCEPT, move money, or change any authority gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from cas_forex.evidence_store import EvidenceStore  # noqa: E402
from cas_forex.paper_proof import (  # noqa: E402
    build_index_tsmom_126_paper_proof_plan,
    paper_proof_store_path,
)
from cas_forex.time_utils import utc_now  # noqa: E402

CONFIRM_PHRASE = "RESTART PAPER PROOF CHAIN"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "index_tsmom_126_paper_proof"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument(
        "--confirm",
        default="",
        help=f'Type exactly: "{CONFIRM_PHRASE}" - restarting the 30-day counter is an owner decision.',
    )
    args = parser.parse_args()

    plan = build_index_tsmom_126_paper_proof_plan()
    store_path = Path(paper_proof_store_path(plan, args.output_dir))
    state_path = store_path.with_suffix(store_path.suffix + ".state")

    if not store_path.exists():
        print(json.dumps({"status": "NOTHING_TO_ARCHIVE", "store": str(store_path)}, indent=2))
        return 1

    report = EvidenceStore(store_path, run_id=plan.plan_id).verify_chain_report()
    if report["verified"]:
        print(json.dumps({
            "status": "REFUSED_CHAIN_VERIFIES",
            "detail": "The chain verifies - there is nothing to remediate, and archiving a healthy chain would discard valid proof days.",
            "record_count": report["record_count"],
        }, indent=2))
        return 1

    if args.confirm != CONFIRM_PHRASE:
        print(json.dumps({
            "status": "CONFIRMATION_REQUIRED",
            "chain": report,
            "consequence": (
                f"Archiving resets the 30-day proof counter to 0. The broken store keeps "
                f"its verified prefix of {report['verified_prefix_records']} records as history, "
                "but none of its days count toward the proof gate afterwards."
            ),
            "to_proceed": f'--confirm "{CONFIRM_PHRASE}"',
        }, indent=2))
        return 1

    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    archive_dir = store_path.parent / "archive" / f"broken-chain-{stamp}"
    archive_dir.mkdir(parents=True, exist_ok=False)

    defect = {
        "report_kind": "cas_forex_paper_proof_chain_defect",
        "archived_at": utc_now().isoformat(),
        "reason": "Chain permanently unverifiable; archived to restart the 30-day proof on a clean store.",
        "verify_chain_report": report,
        "original_store": str(store_path),
        "claim_boundary": (
            "This defect record preserves a broken local evidence chain as history. "
            "It does not repair, rehash, or revalidate any record, and grants no authority."
        ),
    }
    (archive_dir / "chain-defect.json").write_text(json.dumps(defect, indent=2), encoding="utf-8")
    store_path.rename(archive_dir / store_path.name)
    if state_path.exists():
        state_path.rename(archive_dir / state_path.name)

    print(json.dumps({
        "status": "ARCHIVED_AND_RESTARTED",
        "archive": str(archive_dir),
        "defect_record": str(archive_dir / "chain-defect.json"),
        "fresh_store": str(store_path),
        "next_action": "Run the daily paper bundle on the next trading day to append day 1 of 30.",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
