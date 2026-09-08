"""Execute one separately prepared teaching job; inert without --execute.

The preparation digest is mandatory. All source/request/authority bindings and
the current canonical budget are checked again. There is no automatic retry.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


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
    sys.path.insert(0, str(ROOT))
    from aws import teaching_cycle_launch as launch
    from aws import teaching_cycle_provider as provider
    launch.require(all((args.preparation, args.preparation_sha256, args.receipt_dir)), "EXPLICIT_BOUND_INPUTS_REQUIRED")
    raw = launch._raw(args.preparation)
    launch.require(sha256(raw).hexdigest() == args.preparation_sha256, "PREPARATION_DIGEST_MISMATCH")
    prepared = launch._json(raw)
    launch.require(prepared.get("schema") == "cas-teaching-launch-preparation/1"
        and prepared.get("status") == "PREPARED_NOT_RESERVED_NOT_LAUNCHED"
        and prepared.get("new_reservation") is False and prepared.get("paid_execution") is False,
        "PREPARATION_SCHEMA_MISMATCH")
    def bound(name):
        declaration = prepared[name]
        value = launch._raw(declaration["path"])
        launch.require(len(value) == declaration["bytes"] and sha256(value).hexdigest() == declaration["sha256"],
                       "PREPARATION_FILE_CHANGED:" + name)
        return {"raw_utf8": value.decode("utf-8"), "bytes": len(value), "sha256": declaration["sha256"]}
    request = launch.envelope_document(bound("request"))
    authority = bound("authority")
    sources = launch.envelope_document(bound("provider_sources"))
    launch.require(sources == provider.source_dependencies(), "PREPARED_PROVIDER_SOURCES_CHANGED")
    # Only this explicit path imports the SDK. Credentials remain in its normal
    # provider chain and are never included in the request or output records.
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
    config = Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 0})
    session = boto3.Session(profile_name=args.profile, region_name="us-west-2")
    clients = {name: session.client(name, config=config) for name in
               ("sts", "ec2", "s3", "iam", "scheduler", "service-quotas")}
    clients["pricing"] = session.client("pricing", region_name="us-east-1", config=config)
    adapter = provider.TeachingCycleProvider(clients=clients, source_archive=prepared["source_archive"],
        guest_driver=prepared["guest_driver"], pricing_receipt_path=prepared["pricing_receipt_path"],
        ledger_path=launch.budget.CANONICAL_LEDGER, client_error=ClientError)
    result = launch.execute(request, authority, adapter, expected_bindings=prepared["bindings"],
        expected_ledger=prepared["ledger"], public_sets_path=prepared["public_sets_path"],
        receipt_dir=args.receipt_dir)
    print(json.dumps({"status": result["status"], "receipt_dir": result["receipt_dir"],
                      "job": result["job"], "learning_results": result["learning_results"]}))
    return 0 if result["status"] == "TEACHING_CYCLE_COLLECTED_NOT_SCORED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
