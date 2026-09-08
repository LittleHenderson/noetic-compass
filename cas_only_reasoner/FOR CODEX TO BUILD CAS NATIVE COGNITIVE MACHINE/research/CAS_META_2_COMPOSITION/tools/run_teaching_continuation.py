"""One explicit continuation execution; inert without --execute.

The source/preparation/prior/ledger checks precede lazy SDK construction. The
parent then rechecks live facts, reserves once and gates training on restore.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def _live_provider(prepared, profile):
    from aws import teaching_continuation_provider as provider, teaching_continuation_launch as launch
    from botocore.exceptions import ClientError
    return provider.TeachingContinuationProvider(clients=provider.build_clients(profile),
        source_archive=prepared["source_archive"], guest_driver=prepared["guest_driver"],
        pricing_receipt_path=prepared["pricing_receipt_path"], ledger_path=launch.budget.CANONICAL_LEDGER,
        client_error=ClientError, base_guest_driver_path=prepared["base_guest_driver_path"],
        package_validator_path=prepared["package_validator_path"], restore_probe_path=prepared["restore_probe_path"])


def run(preparation, preparation_sha256, receipt_dir, *, profile="default"):
    sys.path.insert(0, str(ROOT))
    from tools.prepare_teaching_continuation import load_preparation
    from aws import teaching_continuation_launch as launch
    directory = launch._safe(receipt_dir)
    launch.require(directory.is_relative_to(ROOT / "records/teaching_cycle_001")
        and not directory.exists() and directory.parent.is_dir(), "FRESH_EXECUTION_RECEIPT_ROOT_REQUIRED")
    prepared, request, authority = load_preparation(preparation, preparation_sha256)
    adapter = _live_provider(prepared, profile)
    return launch.execute(request, authority, adapter, expected_bindings=prepared["bindings"],
        expected_continuation=prepared["continuation"], expected_ledger=prepared["ledger"],
        public_sets_path=prepared["public_sets_path"], prior_state_archive_path=prepared["prior_state_archive_path"],
        prior_state_manifest_path=prepared["prior_state_manifest_path"], receipt_dir=directory)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--preparation")
    parser.add_argument("--preparation-sha256")
    parser.add_argument("--receipt-dir")
    parser.add_argument("--profile", default="default")
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({"status": "NOT_LAUNCHED", "reservation_created": False,
            "required": "--execute --preparation PATH --preparation-sha256 SHA --receipt-dir FRESH_PATH"}))
        return 0
    if not all((args.preparation, args.preparation_sha256, args.receipt_dir)):
        parser.error("--execute requires all three pinned preparation/output arguments")
    result = run(args.preparation, args.preparation_sha256, args.receipt_dir, profile=args.profile)
    print(json.dumps({"status": result["status"], "job": result["job"], "run_id": result["run_id"],
        "receipt_dir": result["receipt_dir"], "learning_results": result["learning_results"]}))
    return 0 if result["status"] == "TEACHING_CONTINUATION_COLLECTED_NOT_SCORED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
