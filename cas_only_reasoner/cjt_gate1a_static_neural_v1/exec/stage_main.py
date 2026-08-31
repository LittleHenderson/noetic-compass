"""stage_main.py -- the committed staging entry the frozen bootstrap calls
(GATE 1A.2R section 2). Uses boto3 (pinned) instead of an `aws` CLI the image
does not install. Downloads the detached execution + prep approvals, the prep
receipt, the exact model/tokenizer set, and the S7 table, verifying digests.

Its inputs are S3 URIs the launch configuration injects as environment; the
model/tokenizer digests and S7 digest come from the DETACHED signed execution
approval it downloads first. No unregistered file is written.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exec.staging import default_s3_get, stage_model, stage_object  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", required=True)
    ap.add_argument("--execution-approval-s3", required=True)
    ap.add_argument("--prep-approval-s3", required=True)
    ap.add_argument("--prep-receipt-s3", required=True)
    ap.add_argument("--model-s3", required=True)
    ap.add_argument("--s7-table-s3", required=True)
    ap.add_argument("--detached-dir", required=True)
    ap.add_argument("--package-root", required=True)
    args = ap.parse_args(argv)
    s3_get = default_s3_get(args.region)
    detached = Path(args.detached_dir)
    pkg = Path(args.package_root)

    exec_path = detached / "execution_approval.json"
    stage_object(s3_get, args.execution_approval_s3, exec_path)
    stage_object(s3_get, args.prep_approval_s3,
                 detached / "container_prep_approval.json")
    stage_object(s3_get, args.prep_receipt_s3,
                 detached / "container_prep_receipt.json")
    approval = json.loads(exec_path.read_text(encoding="utf-8"))

    stage_model(s3_get, args.model_s3, Path("/campaign/model"),
                approval["model_weight_sha256s"],
                approval["tokenizer_file_sha256s"],
                approval["model_revision_sha"])
    stage_object(s3_get, args.s7_table_s3,
                 pkg / "derived" / "alternative_taxonomy_table.json",
                 approval["s7_control_table_sha256"])
    print("STAGING_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
