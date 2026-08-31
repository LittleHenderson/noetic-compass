"""launcher.py -- the thin CLI over the ONE campaign driver (GATE 1A.2 s.4).

The LAUNCHER_STUB_GUARD is REMOVED: exec/campaign_driver.py is the real,
complete orchestration body, and this file only parses arguments and hands them
to it. There is NO --hourly-rate argument and NO --pinned-pubkey-hex argument:
every rate and ceiling comes from the SIGNED detached approval, and the owner
key comes only from the structural trust root (exec/trust_root.py).

REAL mode can only complete inside the Gate 1B container on verified AWS
identity with the signed approvals present; on this development machine it
fails closed at the first guarded step. SYNTHETIC_CONFORMANCE traverses the
same driver with committed fixtures and is permanently non-claim-bearing.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exec.campaign_driver import CampaignDriver  # noqa: E402


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True,
                    choices=["REAL", "SYNTHETIC_CONFORMANCE"])
    ap.add_argument("--package-root", required=True)
    ap.add_argument("--campaign-id", required=True)
    ap.add_argument("--approval", required=True,
                    help="the DETACHED signed execution approval")
    ap.add_argument("--prep-approval", required=True,
                    help="the DETACHED signed container-prep approval")
    ap.add_argument("--prep-receipt", required=True)
    ap.add_argument("--evidence-root", required=True)
    ap.add_argument("--synthetic-root", default=None)
    args = ap.parse_args(argv)
    driver = CampaignDriver(
        mode=args.mode, package_root=Path(args.package_root),
        campaign_id=args.campaign_id,
        execution_approval_path=Path(args.approval),
        prep_approval_path=Path(args.prep_approval),
        prep_receipt_path=Path(args.prep_receipt),
        evidence_root=Path(args.evidence_root),
        synthetic_root=Path(args.synthetic_root) if args.synthetic_root else None)
    out = driver.run()
    print(f"CAMPAIGN_{out['final_state']}: {out['campaign_id']} "
          f"chain={out['chain_digest'][:16]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
