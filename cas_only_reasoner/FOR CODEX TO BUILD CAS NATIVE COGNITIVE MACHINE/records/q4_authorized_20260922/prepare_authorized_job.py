"""Bind the actual current user instruction to a fresh, bounded smoke plan."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
CN = ROOT.parents[1]
LAB = CN / "research/helm_cas_expression_lab"
sys.path.insert(0, str(LAB))
import q4_smoke_job as job
from q4_conversation_authorization import SCHEMA, USER_AUTHORIZATION_QUOTE
from q4_device_capacity import shared_display_policy


def main():
    old_path = CN / "records/cas_reconciliation_20260922/q4_preparation/plan.json"
    old = job._read_json(old_path)
    plan = job.prepare_plan(
        data_dir=LAB / "data/q3_v0_7", data_version=old["data_version"], output=ROOT / "run_001",
        seed=old["seed"], width=old["width"], max_updates=old["max_updates"],
        max_wall_seconds=old["max_wall_seconds"], train_examples=old["train_examples"],
        dev_examples=old["dev_examples"], device=old["device"],
        device_policy=shared_display_policy("GPU-7cfee18b-e83d-b6fb-a946-ae444b329fdd"))
    changes = {key for key in set(old) | set(plan) if old.get(key) != plan.get(key)}
    if changes != {"data_dir", "output", "source_pins", "device_policy"}:
        raise ValueError("Unexpected change to the already presented workload: " + str(changes))
    for name, value in old["source_pins"].items():
        if name not in {"q4_checkpoint.py", "q4_smoke_job.py"} and plan["source_pins"][name] != value:
            raise ValueError("Unexpected model/data implementation change: " + name)
    job.validate_plan(plan)
    plan_hash = job.digest(job.canonical(plan))
    record = {"schema": SCHEMA, "plan_sha256": plan_hash,
              "provenance": {"source_role": "user", "source": "CURRENT_CODEX_CONVERSATION",
                  "source_reference": "Codex task 01a0c5fc-8316-7ce1-b215-b0252bf4684f; user message immediately after the Q4 authorization request; message ID unavailable",
                  "recorded_by": "CODEX_AGENT_TRANSCRIPTION",
                  "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                  "user_quote": USER_AUTHORIZATION_QUOTE,
                  "user_quote_sha256": job.digest(USER_AUTHORIZATION_QUOTE.encode("utf-8"))},
              "execution_scope": {key: plan[key] for key in ("task", "device", "max_updates", "max_wall_seconds")}}
    record["execution_scope"]["no_retries"] = True
    job._write_json(ROOT / "plan.json", plan)
    job._write_json(ROOT / "conversation_authorization.json", record)
    auth_hash = job.digest((ROOT / "conversation_authorization.json").read_bytes())
    receipt = job._authorization_receipt(plan, conversation_authorization=ROOT / "conversation_authorization.json",
                                          conversation_sha256=auth_hash)
    source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=CN, text=True).strip()
    job._write_json(ROOT / "preparation.json", {
        "prepared_utc": datetime.now(timezone.utc).isoformat(), "source_commit": source_commit,
        "preserved_checkpoint": "5f7111d5204e872c18df717badc2e2021f31ad70",
        "old_plan_canonical_sha256": job.digest(job.canonical(old)),
        "new_plan_canonical_sha256": plan_hash, "changed_plan_fields": sorted(changes),
        "authorization": receipt, "torch_imported": "torch" in sys.modules,
        "execution": "NOT_RUN_BY_PREPARATION", "source_pins": plan["source_pins"]})
    print(json.dumps({"plan_sha256": plan_hash, "authorization_sha256": auth_hash,
                      "source_commit": source_commit, "torch_imported": "torch" in sys.modules}))


if __name__ == "__main__":
    main()
