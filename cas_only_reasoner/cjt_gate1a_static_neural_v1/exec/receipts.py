"""receipts.py -- the FROZEN per-job execution receipt (REPLICATION_AND_RECEIPT_SPEC).

Every Gate 1B job emits one receipt with EVERY required field; a missing field is
a RECEIPT_INVALID failure, never a silently thin receipt.
"""
from __future__ import annotations

import hashlib
import json

REQUIRED_FIELDS = (
    "job_id", "job_step", "model_revision_sha", "weight_file_sha256s",
    "code_commit_sha", "gate1b_code_manifest_sha256", "dataset_digests",
    "container_image_digest", "seed", "instance_type", "region",
    "start_utc", "end_utc", "wall_clock_seconds", "output_digests",
    "cost_usd_estimate", "quota_and_spot_details")


def build_receipt(**fields) -> dict:
    missing = [k for k in REQUIRED_FIELDS if k not in fields]
    if missing:
        raise ValueError(f"RECEIPT_INVALID: missing {missing}")
    extra = [k for k in fields if k not in REQUIRED_FIELDS]
    if extra:
        raise ValueError(f"RECEIPT_INVALID: unregistered fields {extra}")
    receipt = {k: fields[k] for k in REQUIRED_FIELDS}
    canonical = json.dumps(receipt, sort_keys=True, ensure_ascii=True,
                           separators=(",", ":")).encode("utf-8")
    receipt["receipt_sha256"] = hashlib.sha256(canonical).hexdigest()
    return receipt
