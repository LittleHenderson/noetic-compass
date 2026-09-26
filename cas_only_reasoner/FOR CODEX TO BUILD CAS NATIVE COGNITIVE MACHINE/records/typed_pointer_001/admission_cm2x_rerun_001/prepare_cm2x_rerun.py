"""Freeze a distinct second-attempt admission for the corrected HELM critical-mass 2x run.

This is a thin operational wrapper around the already-reviewed 20-pass admission writer. It changes only the
attempt identity, output paths, owner directive, and historical-attempt linkage. The scientific experiment
version and launcher contract remain `cncm.typed-pointer-critical-mass-2x/1`.
"""
import argparse
from hashlib import sha256
from decimal import Decimal
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE_PATH = ROOT / "records/typed_pointer_001/admission_cm2x_001/prepare_cm2x_study.py"
_SPEC = importlib.util.spec_from_file_location("prepare_cm2x_study_attempt1", BASE_PATH)
base = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(base)

RERUN_ADMISSION_VERSION = 2
SEED = base.SEED
VERSION = base.VERSION
STUDY_SCHEMA = "cncm.typed-pointer-critical-mass-2x-rerun-admission/0.1"
SEED_OUTPUT = HERE / "seeds"
PARTIAL_OUTPUT = HERE / "seeds.partial"
OWNER_PROBE = HERE / "owner_probe.json"
OWNER_DIRECTIVE = HERE / "OWNER_AMENDMENT_20260926.md"
OWNER_DIRECTIVE_SHA256 = "d364190935104c04c855d925e5259170f6d9f956e407ce0746c21932f719c68e"
RECEIPT_DIR = ROOT / "records/typed_pointer_001/receipt_cm2x_rerun_20260918"
PRIOR_ADMISSION = ROOT / "records/typed_pointer_001/admission_cm2x_001"
PRIOR_RECEIPT = ROOT / "records/typed_pointer_001/receipt_cm2x_20260918"
PRIOR_JOB = "cas-meta2-tpntr-20260925151836-b981625f-m-20260918"

APPROVAL_CONTEXT = (
    "Owner directed the corrected HELM critical-mass 2x rerun on 2026-09-25: proceed now with one new "
    "20-pass job after the deadline-routing fix, without reusing any failed-attempt identity or record."
)
SCOPE = (
    "ONE fresh second-attempt 20-pass run, seed 20260918, constant LR 0.003; one g7.2xlarge globally, "
    "automatic_retries=0, cleanup required, pass-10 checkpoint evidence mandatory, USD 21.50 all-services cap. "
    "Historical R18 and first-attempt records are read-only."
)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii") + b"\n"


def historical_attempt_snapshot():
    """Read only the byte-bound public closeout, never historical prediction/checkpoint bodies."""
    raw = (HERE / "PRIOR_PUBLIC_CLOSEOUT.json").read_bytes()
    if sha256(raw).hexdigest() != "b0df52a0dc08ea7eff074c9f4502756d082fb150be0b707d2806c75c4e9020a1":
        raise ValueError("CM2X_RERUN_STOPPED:PRIOR_CLOSEOUT_CHANGED")
    record = json.loads(raw)
    if record["job"] != PRIOR_JOB or record["outcome"] != "FAILED_INCOMPLETE_NOT_CERTIFIED":
        raise ValueError("CM2X_RERUN_STOPPED:PRIOR_JOB_IDENTITY")
    return {"job": PRIOR_JOB, "admission_path": str(PRIOR_ADMISSION), "receipt_path": str(PRIOR_RECEIPT),
            "public_closeout_sha256": sha256(raw).hexdigest(),
            "recorded_downloaded_objects": record["preservation"]["downloaded_objects"],
            "recorded_hash_mismatches": record["preservation"]["hash_mismatches"],
            "boundary": "Prior public closeout linkage only; no new historical-body reads or reload claim",
            "preservation_rule": "Historical inputs remain read-only; attempt 2 reuses no output path"}



def _configure_base():
    base.STUDY_SCHEMA = STUDY_SCHEMA
    base.SEED_OUTPUT = SEED_OUTPUT
    base.PARTIAL_OUTPUT = PARTIAL_OUTPUT
    base.OWNER_PROBE = OWNER_PROBE
    base.OWNER_DIRECTIVE = OWNER_DIRECTIVE
    base.OWNER_DIRECTIVE_SHA256 = OWNER_DIRECTIVE_SHA256
    base.RECEIPT_DIR = RECEIPT_DIR
    base.APPROVAL_CONTEXT = APPROVAL_CONTEXT
    base.SCOPE = SCOPE
    base.ALL_SERVICES_CAP_USD = "21.50"
    base.OWNER_SCHEMA_NOTE = "Owner amendment transcribed by Codex; not a signature. One fresh 20-pass job; USD21.50 finite total; zero automatic retries."
    base.cost_bound = cost_bound
    base.tolerated = tolerated


_BASE_COST_BOUND = base.cost_bound
_BASE_TOLERATED = base.tolerated
_BASE_BUILD = base.build
_BASE_STUDY_RECORD = base.study_record

def cost_bound():
    bound = _BASE_COST_BOUND()
    prior = Decimal("0.60") + Decimal("0.10")
    preparation = Decimal("1.20")  # Two distinct immutable CPU preparation reservations.
    total = Decimal(bound["reservation_plus_allowance_usd"]) + prior + preparation
    base.stop_unless(total <= Decimal("21.50"), "TOTAL_RERUN_CAP_EXCEEDED")
    bound.update({"historical_prerequisite_reservations_usd": str(prior),
                  "corrected_preparation_reservation_usd": str(preparation),
                  "all_services_prospective_total_usd": str(total),
                  "all_services_cap_usd": "21.50", "headroom_to_cap_usd": str(Decimal("21.50") - total)})
    return bound


def tolerated(source_sha):
    # Generated CPU receipts and downloaded package are declared operational outputs.
    return _BASE_TOLERATED(source_sha) + (
        base.launch.shared.GIT_PREFIX + "records/typed_pointer_001/rerun_20260926_corrected_preparation/jobs/",
    )


def build(source_sha, package, job, *, owner_question):
    owner_raw, request, authority = _BASE_BUILD(source_sha, package, job, owner_question=owner_question)
    owner = json.loads(owner_raw)
    owner.update({
        "owner_instruction_raw": "Proceed now with the corrected HELM critical-mass 2x rerun.",
        "owner_message_full_raw": OWNER_DIRECTIVE.read_text(encoding="utf-8"),
        "owner_directive_sha256": OWNER_DIRECTIVE_SHA256,
        "owner_directive_file": OWNER_DIRECTIVE.name,
        "approval_context": APPROVAL_CONTEXT,
        "scope": SCOPE,
        "rerun_admission_version": RERUN_ADMISSION_VERSION,
        "prior_failed_attempt": historical_attempt_snapshot(),
        "prior_failed_attempt_untouched": True,
    })
    owner_raw = base.canonical(owner)
    authority["owner_authorization_sha256"] = base.digest(owner_raw)
    base.launch.validate_request(request)
    base.launch.validate_authority(authority)
    base.validate_owner_record(owner_raw, authority)
    return owner_raw, request, authority


def study_record(source_sha, package, bindings, job, *, owner_question):
    study = _BASE_STUDY_RECORD(source_sha, package, bindings, job, owner_question=owner_question)
    study.update({
        "schema": STUDY_SCHEMA,
        "rerun_admission_version": RERUN_ADMISSION_VERSION,
        "attempt": 2,
        "prior_failed_attempt": historical_attempt_snapshot(),
        "prior_failed_attempt_untouched": True,
        "new_identity_required": True,
        "automatic_retry_of_prior_attempt": False,
        "scientific_experiment_version_unchanged": VERSION,
        "operational_fix_source_base": "a5fcf527b5f2c47a3a9b1f170977c55371845af0",
        "supersedes": (
            "operational attempt 1 only; the scientific experiment remains %s; historical R18 and failed "
            "attempt admission, reservation and receipt bytes are not modified" % VERSION
        ),
    })
    return study


def prepare(source_sha, *, write, owner_question=None):
    _configure_base()
    base.build = build
    base.study_record = study_record
    return base.prepare(source_sha, write=write, owner_question=owner_question)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source-sha", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--owner-question")
    args = parser.parse_args(argv)
    return prepare(args.source_sha, write=args.write, owner_question=args.owner_question)


_configure_base()
launch = base.launch
contract = base.contract
canonical = base.canonical
digest = base.digest
package_dir = base.package_dir
check_source = base.check_source


if __name__ == "__main__":
    raise SystemExit(main())
