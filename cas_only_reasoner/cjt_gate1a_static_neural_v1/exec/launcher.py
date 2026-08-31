"""launcher.py -- the Gate 1B campaign launcher (cost caps + auto-termination).

REFUSAL LAW: the FIRST act of this launcher is full approval verification via
tools/verify_phase_approval.verify_full() -- the signed record's phase, commit,
manifest-equality, tree digests, identities, and Ed25519 signature must ALL
verify against the pinned public key and the checked-out tree, or NOTHING
launches. There is no --force, no skip flag, no partial mode.

Cost law (COST_AND_AUTOTERMINATION_POLICY.md): a job may not START if the
running campaign estimate plus that job's cap-priced cost would exceed the
signed cost_ceiling_usd; every job carries the signed per-job wall-clock cap;
the instance self-terminates at campaign end and on any cap breach.

ON-INSTANCE RE-VERIFICATION: before training, the launcher recomputes the
resolved model revision, weight digests, tokenizer digest, container digest,
and dependency-lock digest and REQUIRES equality with the signed record
(MODEL_IDENTITY_MISMATCH / CONTAINER_IDENTITY_MISMATCH otherwise). The
alternative-taxonomy table constructed at step 3 must hash to the signed
s7_control_table_sha256 (TAXONOMY_IDENTITY_MISMATCH otherwise).

Nothing here runs at Gate 1A. No AWS call exists outside main().
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def checked_out_commit(repo_root: Path) -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root,
                          capture_output=True, text=True,
                          check=True).stdout.strip()


def campaign_budget_gate(spent_usd: float, next_job_cap_hours: float,
                         hourly_rate_usd: float, ceiling_usd: float) -> None:
    """Refuse to start a job whose cap-priced cost could breach the ceiling."""
    projected = spent_usd + next_job_cap_hours * hourly_rate_usd
    if projected > ceiling_usd:
        raise RuntimeError(
            f"COST_CEILING_REFUSAL: spent {spent_usd:.2f} + capped job "
            f"{next_job_cap_hours * hourly_rate_usd:.2f} would reach "
            f"{projected:.2f} > ceiling {ceiling_usd:.2f}")


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--approval", required=True, help="OWNER_PHASE_APPROVAL_SIGNED.json")
    ap.add_argument("--pinned-pubkey-hex", required=True)
    ap.add_argument("--package-root", required=True)
    ap.add_argument("--hourly-rate-usd", type=float, required=True,
                    help="verified instance price at launch time (estimate law)")
    args = ap.parse_args(argv)
    pkg = Path(args.package_root).resolve()
    sys.path.insert(0, str(pkg / "tools"))
    from verify_phase_approval import verify_full          # the ONE authority
    record = json.loads(Path(args.approval).read_text(encoding="utf-8"))
    verify_full(record, args.pinned_pubkey_hex, pkg,
                checked_out_commit(pkg))                   # raises on ANY defect
    print("APPROVAL_VERIFIED: execution authority bound to this tree")
    # job sequence per AWS_EXECUTION_MANIFEST.yaml steps 1-8; each job:
    #   campaign_budget_gate(...) -> run -> receipt (exec/receipts.py) -> account
    # auto-termination: the bootstrap installs a hard wall-clock alarm at the
    # signed per_job cap and the campaign driver shuts the instance down at the
    # end of step 8 or on the first breach.
    raise SystemExit("LAUNCHER_STUB_GUARD: the job-sequence body is enabled by "
                     "the Gate 1B container build; local execution is refused")


if __name__ == "__main__":
    main()
