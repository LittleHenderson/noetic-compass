"""watchdog_authority.py -- the watchdog's timeout is DERIVED from the
owner-signed execution approval, not trusted from a self-consistent file
(GATE 1A.2R.2C).

The GATE 1A.2R.2B config authority (exec/watchdog_config.py) validated that a
configuration file was well-shaped and internally consistent. The independent
recheck found that shape is not authority: a self-consistent forged config with a
different positive cap (and a matching `cap * 3600 * 1.1` stale limit) passed,
because nothing tied the numbers to the owner's actual signed approval. This
module closes that:

1.  derive_authority() INDEPENDENTLY VERIFIES the detached execution approval
    against the frozen owner trust root (via the committed verifier
    tools/verify_phase_approval.verify_execution) and DERIVES the stale limit
    from the SIGNED per-job cap. The Ed25519 signature is load-bearing: to raise
    the timeout you would have to forge the owner signature, which is impossible
    without the owner key.

2.  load_verified_authority() re-derives from the verified approval, reads the
    written watchdog_authority.json with FULL envelope totality (dict-only, exact
    key set, arrays/null/scalars/NaN refused), and requires EVERY field of the
    file to EQUAL the derived value. The file is bound EVIDENCE; the approval is
    the authority. A forged authority file is refused because it disagrees with
    the verified approval.

3.  The startup grace and poll interval are FROZEN registered code constants in
    REAL; resolve_timers() ignores caller values in REAL (structural, like the
    driver's _hook()). A caller cannot widen the grace to accept a decades-late
    heartbeat or stretch the poll to disable timely termination.

4.  The protected-lock coordinates are DERIVED from the verified approval
    (authorized_lock_locator), never trusted from a mutable file -- so a
    corrupted locator cannot erase the burn of an active protected campaign.

The authority file is written ATOMICALLY (exec/fsio.write_utf8_lf_atomic) BEFORE
the watchdog starts (bootstrap order), and is IMMUTABLE for the watchdog's
lifetime: the poll loop never re-reads it.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

_PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PKG))
sys.path.insert(0, str(_PKG / "tools"))

from exec.fsio import write_utf8_lf_atomic          # noqa: E402
from exec.watchdog_config import STALE_LIMIT_MULTIPLIER  # noqa: E402  (single source)

AUTHORITY_ID = "WATCHDOG_AUTHORITY"
LOCK_LOCATOR_ID = "PROTECTED_LOCK_LOCATOR"
REGION = "us-east-1"

# REGISTERED IMMUTABLE TIMER CONSTANTS (section 5). In REAL mode the startup
# grace and poll interval are these frozen code values -- never caller-supplied.
STARTUP_GRACE_SECONDS = 900.0
POLL_SECONDS = 60.0
MAX_STARTUP_GRACE_SECONDS = 3600.0        # a registered ceiling; larger is refused
MAX_POLL_SECONDS = 300.0

REQUIRED_AUTHORITY_KEYS = frozenset([
    "authority_id", "campaign_id", "package_commit_sha",
    "execution_approval_sha256", "owner_key_id", "aws_account_id", "region",
    "signed_per_job_cap_hours", "stale_limit_seconds", "startup_grace_seconds",
    "poll_seconds"])

LOCK_LOCATOR_KEYS = frozenset(["locator_id", "table_name", "region", "campaign_id"])

_AUTHORITY_FIELDS = ("campaign_id", "package_commit_sha",
                     "execution_approval_sha256", "owner_key_id",
                     "aws_account_id", "region", "signed_per_job_cap_hours",
                     "stale_limit_seconds", "startup_grace_seconds", "poll_seconds")


class WatchdogAuthorityError(RuntimeError):
    pass


def _reject_non_finite(x):
    raise WatchdogAuthorityError(f"AUTHORITY_JSON_CONSTANT_REFUSED: {x}")


def _pos_finite(v):
    return type(v) in (int, float) and not isinstance(v, bool) \
        and math.isfinite(v) and v > 0


def _hex(v, n):
    return isinstance(v, str) and len(v) == n \
        and all(c in "0123456789abcdef" for c in v)


class AuthorityRecord:
    """The immutable, verified timing law. Constructed ONLY by derive_authority
    from a signature-verified approval; never from a file's declared numbers."""
    __slots__ = _AUTHORITY_FIELDS

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw[k])

    def as_dict(self) -> dict:
        d = {"authority_id": AUTHORITY_ID}
        for k in self.__slots__:
            d[k] = getattr(self, k)
        return d


def _checked_out_commit(package_root: Path) -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(package_root),
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise WatchdogAuthorityError(
            f"CHECKED_OUT_COMMIT_UNAVAILABLE: {r.stderr.strip()}")
    return r.stdout.strip()


def derive_authority(*, approval_path, prep_receipt_path, package_root,
                     expected_campaign_id, mode, expected_commit=None
                     ) -> AuthorityRecord:
    """Verify the DETACHED execution approval against the frozen owner trust root
    and DERIVE the timing law from the verified approval. Raises on ANY defect
    (bad signature, wrong commit, unpinned owner key, modified tree, missing prep
    receipt, ...). The returned stale limit comes from the SIGNED per-job cap --
    a forged file cannot influence it."""
    from verify_phase_approval import verify_execution     # committed verifier
    package_root = Path(package_root).resolve()
    approval_path = Path(approval_path)
    if not isinstance(expected_campaign_id, str) or not expected_campaign_id:
        raise WatchdogAuthorityError("CAMPAIGN_ID_INVALID")
    if not approval_path.is_file():
        raise WatchdogAuthorityError(
            "EXECUTION_APPROVAL_MISSING: no detached execution approval to verify")
    if expected_commit is None:
        expected_commit = _checked_out_commit(package_root)
    approval_bytes = approval_path.read_bytes()
    record = json.loads(approval_bytes.decode("utf-8"))
    # verify_execution raises (fail closed) on any authority defect
    verify_execution(record, package_root, expected_commit, mode,
                     approval_path=approval_path,
                     prep_receipt_path=prep_receipt_path)
    cap = record["per_job_wall_clock_cap_hours"]
    if not _pos_finite(cap):
        raise WatchdogAuthorityError(f"SIGNED_CAP_INVALID: {cap!r}")
    account = record["aws_account_id"]
    region = record["region"]
    if not (isinstance(account, str) and len(account) == 12 and account.isdigit()):
        raise WatchdogAuthorityError(f"ACCOUNT_ID_INVALID: {account!r}")
    if region != REGION:
        raise WatchdogAuthorityError(f"REGION_INVALID: {region!r}")
    return AuthorityRecord(
        campaign_id=expected_campaign_id,
        package_commit_sha=expected_commit,
        execution_approval_sha256=hashlib.sha256(approval_bytes).hexdigest(),
        owner_key_id=record["owner_key_id"],
        aws_account_id=account,
        region=region,
        signed_per_job_cap_hours=cap,
        stale_limit_seconds=cap * 3600.0 * STALE_LIMIT_MULTIPLIER,
        startup_grace_seconds=STARTUP_GRACE_SECONDS,
        poll_seconds=POLL_SECONDS)


def write_authority_atomic(path, record: AuthorityRecord) -> str:
    """Write the immutable authority file ATOMICALLY (section 4). Returns its
    sha256."""
    text = json.dumps(record.as_dict(), indent=2, sort_keys=True) + "\n"
    write_utf8_lf_atomic(path, text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_authority_envelope(obj) -> dict:
    """Dict-only exact-schema envelope totality on the authority FILE (carrying
    the GATE 1A.2R.2B principle onto the new authority surface): arrays, null,
    scalars, wrong key sets, list-valued/NaN limits, non-frozen timers are all
    refused. Raises WatchdogAuthorityError on any defect."""
    if not isinstance(obj, dict):
        raise WatchdogAuthorityError(
            f"AUTHORITY_NOT_A_DICT: got {type(obj).__name__}")
    if set(obj) != REQUIRED_AUTHORITY_KEYS:
        raise WatchdogAuthorityError(f"AUTHORITY_KEY_SET_INVALID: {sorted(obj)}")
    if obj["authority_id"] != AUTHORITY_ID:
        raise WatchdogAuthorityError("AUTHORITY_ID_MISMATCH")
    if not isinstance(obj["campaign_id"], str) or not obj["campaign_id"]:
        raise WatchdogAuthorityError("AUTHORITY_CAMPAIGN_ID_INVALID")
    if not _hex(obj["package_commit_sha"], 40):
        raise WatchdogAuthorityError("AUTHORITY_PACKAGE_COMMIT_INVALID")
    if not _hex(obj["execution_approval_sha256"], 64):
        raise WatchdogAuthorityError("AUTHORITY_APPROVAL_DIGEST_INVALID")
    if not isinstance(obj["owner_key_id"], str) or len(obj["owner_key_id"]) < 4:
        raise WatchdogAuthorityError("AUTHORITY_OWNER_KEY_ID_INVALID")
    acct = obj["aws_account_id"]
    if not (isinstance(acct, str) and len(acct) == 12 and acct.isdigit()):
        raise WatchdogAuthorityError("AUTHORITY_ACCOUNT_ID_INVALID")
    if obj["region"] != REGION:
        raise WatchdogAuthorityError("AUTHORITY_REGION_INVALID")
    for k in ("signed_per_job_cap_hours", "stale_limit_seconds",
              "startup_grace_seconds", "poll_seconds"):
        if not _pos_finite(obj[k]):            # list-valued / bool / NaN refused
            raise WatchdogAuthorityError(f"AUTHORITY_{k.upper()}_INVALID")
    exp_stale = obj["signed_per_job_cap_hours"] * 3600.0 * STALE_LIMIT_MULTIPLIER
    if abs(obj["stale_limit_seconds"] - exp_stale) > 1e-6:
        raise WatchdogAuthorityError("AUTHORITY_STALE_LIMIT_NOT_DERIVED")
    if abs(obj["startup_grace_seconds"] - STARTUP_GRACE_SECONDS) > 1e-6:
        raise WatchdogAuthorityError("AUTHORITY_STARTUP_GRACE_NOT_FROZEN")
    if abs(obj["poll_seconds"] - POLL_SECONDS) > 1e-6:
        raise WatchdogAuthorityError("AUTHORITY_POLL_NOT_FROZEN")
    return obj


def load_verified_authority(*, mode, approval_path, prep_receipt_path,
                            package_root, expected_campaign_id, authority_path,
                            expected_commit=None) -> AuthorityRecord:
    """The watchdog's startup authority load. (1) DERIVE the timing law from the
    signature-verified approval (the trustworthy source). (2) Read the written
    authority file with envelope totality. (3) Require EVERY field of the file to
    EQUAL the derived value. Returns the DERIVED record (never the file numbers).
    Raises on ANY defect -- a missing/forged/malformed authority fails closed."""
    derived = derive_authority(
        approval_path=approval_path, prep_receipt_path=prep_receipt_path,
        package_root=package_root, expected_campaign_id=expected_campaign_id,
        mode=mode, expected_commit=expected_commit)
    path = Path(authority_path)
    if not path.is_file():
        raise WatchdogAuthorityError(
            "AUTHORITY_FILE_MISSING: the watchdog authority file must be written "
            "(atomically) BEFORE the watchdog starts")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"),
                         parse_constant=_reject_non_finite)
    except (OSError, ValueError) as exc:
        raise WatchdogAuthorityError(
            f"AUTHORITY_UNREADABLE: {type(exc).__name__}") from exc
    validate_authority_envelope(obj)
    for k, v in derived.as_dict().items():
        fv = obj[k]
        if isinstance(v, float):
            if not (isinstance(fv, (int, float)) and not isinstance(fv, bool)
                    and abs(float(fv) - v) <= 1e-6):
                raise WatchdogAuthorityError(
                    f"AUTHORITY_FIELD_MISMATCH: {k} file={fv!r} != derived={v!r}")
        elif fv != v:
            raise WatchdogAuthorityError(
                f"AUTHORITY_FIELD_MISMATCH: {k} file={fv!r} != derived={v!r}")
    return derived


def resolve_timers(mode, caller_grace=None, caller_poll=None):
    """In REAL the startup grace and poll interval are the FROZEN registered
    constants -- a caller value is IGNORED (structural). Only the non-claim-bearing
    conformance postures may override, within registered finite bounds; a
    negative / NaN / infinite / over-ceiling value fails closed."""
    if mode == "REAL":
        return STARTUP_GRACE_SECONDS, POLL_SECONDS
    grace = STARTUP_GRACE_SECONDS if caller_grace is None else caller_grace
    poll = POLL_SECONDS if caller_poll is None else caller_poll
    for name, val, hi in (("startup_grace_seconds", grace, MAX_STARTUP_GRACE_SECONDS),
                          ("poll_seconds", poll, MAX_POLL_SECONDS)):
        if isinstance(val, bool) or type(val) not in (int, float) \
                or not math.isfinite(val) or val < 0 or val > hi:
            raise WatchdogAuthorityError(f"TIMER_INVALID: {name}={val!r}")
    return float(grace), float(poll)


def authorized_lock_locator(record: AuthorityRecord) -> dict:
    """The protected-lock coordinates AUTHORIZED by the verified approval -- the
    table naming law binds the signed AWS account id, region, and campaign."""
    return {"locator_id": LOCK_LOCATOR_ID,
            "table_name": f"cjt-protected-lock-{record.aws_account_id}",
            "region": record.region,
            "campaign_id": record.campaign_id}


def validate_lock_locator(obj, record: AuthorityRecord) -> dict:
    """The on-disk locator must EXACTLY match the locator authorized by the
    verified approval: dict-only, exact keys, nonempty strings, region == signed
    region, nested campaign_id == the authorized (top-level) campaign, table
    naming law. Raises on any mismatch."""
    want = authorized_lock_locator(record)
    if not isinstance(obj, dict):
        raise WatchdogAuthorityError(f"LOCATOR_NOT_A_DICT: {type(obj).__name__}")
    if set(obj) != LOCK_LOCATOR_KEYS:
        raise WatchdogAuthorityError(f"LOCATOR_KEY_SET_INVALID: {sorted(obj)}")
    for k, v in obj.items():
        if not isinstance(v, str) or not v:
            raise WatchdogAuthorityError(f"LOCATOR_FIELD_NOT_STRING: {k}")
    if obj != want:
        raise WatchdogAuthorityError(f"LOCATOR_MISMATCH: {obj} != authorized {want}")
    return obj


def write_lock_locator_atomic(path, record: AuthorityRecord) -> str:
    text = json.dumps(authorized_lock_locator(record), indent=2,
                      sort_keys=True) + "\n"
    write_utf8_lf_atomic(path, text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():
    """The PRE-WATCHDOG authority-write step (bootstrap order section 1): verify
    the approval and atomically write the immutable authority file BEFORE the
    watchdog starts. Fail-closed with a named reason; the bootstrap's `set -e`
    aborts (and the instance terminates) if this refuses."""
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True,
                    choices=["REAL", "SYNTHETIC_CONFORMANCE"])
    ap.add_argument("--approval", required=True)
    ap.add_argument("--prep-receipt", required=True)
    ap.add_argument("--package-root", required=True)
    ap.add_argument("--campaign-id", required=True)
    ap.add_argument("--authority-out", required=True)
    ap.add_argument("--expected-commit", default=None)
    args = ap.parse_args()
    try:
        record = derive_authority(
            approval_path=args.approval, prep_receipt_path=args.prep_receipt,
            package_root=args.package_root, expected_campaign_id=args.campaign_id,
            mode=args.mode, expected_commit=args.expected_commit)
        sha = write_authority_atomic(args.authority_out, record)
    except Exception as exc:                         # fail closed, name the reason
        print(f"AUTHORITY_DERIVATION_REFUSED: {type(exc).__name__}: {exc}")
        return 1
    print(f"WATCHDOG_AUTHORITY_WRITTEN sha256={sha} "
          f"stale_limit_seconds={record.stale_limit_seconds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
