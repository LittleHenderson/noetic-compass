"""Read-only final observation of the six authorized study instances."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import boto3

ROOT = Path(__file__).resolve().parents[2]
RECORDS = ROOT / "records/typed_matched_001"
STUDY = json.loads((RECORDS / "admission_001/study.json").read_bytes())
IDS = ["i-0dcbfc8321769d483", "i-025f80988385e8af2", "i-07bb0b2f258fa24d7",
       "i-08be663d12da12976", "i-0b1df34d89ef70d5a", "i-0034bd0ea5fe003a5"]
session = boto3.Session(profile_name="default", region_name="us-west-2")
identity = session.client("sts").get_caller_identity()
assert identity["Account"] == "807562639912"
response = session.client("ec2").describe_instances(InstanceIds=IDS)
rows = []
expected = {j["job"] for j in STUDY["jobs"]}
for reservation in response["Reservations"]:
    assert reservation["OwnerId"] == identity["Account"]
    for instance in reservation["Instances"]:
        tags = {t["Key"]: t["Value"] for t in instance.get("Tags", [])}
        job = tags.get("cas_meta_job")
        assert job in expected
        rows.append({"instance_id": instance["InstanceId"], "state": instance["State"]["Name"], "job": job})
assert {row["instance_id"] for row in rows}.issubset(set(IDS))
assert all(row["state"] == "terminated" for row in rows)
lifecycle_rows = []
for job in STUDY["jobs"]:
    receipt = Path(job["receipt_dir"]) / "result.json"
    raw = receipt.read_bytes()
    cleanup = json.loads(raw)["cleanup"]
    assert cleanup["complete"] and not cleanup["failures"]
    assert cleanup["roles_removed"] and cleanup["security_group_deleted"]
    assert all(v == "CONFIRMED_TERMINATED" for v in cleanup["instances"].values())
    assert all(v["state"] == "terminated" for v in cleanup["post_cleanup_observations"].values())
    lifecycle_rows.append({"job": job["job"], "instances": cleanup["instances"], "lifecycle_sha256": hashlib.sha256(raw).hexdigest()})
home = ROOT.parents[3]
ledger_path = home / "_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/budget/campaign_ledger.json"
ledger_bytes = ledger_path.read_bytes()
ledger = json.loads(ledger_bytes)
result = {
    "schema": "cncm.typed-matched-completion-provider-observation/0.1",
    "observed_utc": datetime.now(timezone.utc).isoformat(),
    "status": "PASS", "provider_mutations": 0,
    "account": identity["Account"], "region": "us-west-2",
    "instances": sorted(rows, key=lambda row: row["job"]),
    "requested_instance_ids": IDS,
    "instance_ids_not_returned_by_fresh_ec2_query": sorted(set(IDS) - {r["instance_id"] for r in rows}),
    "all_returned_instances_terminated": True,
    "all_six_lifecycle_termination_checks_passed": True,
    "lifecycle_checks": lifecycle_rows,
    "prior_observation_attempt": {"outcome": "ASSERTION_FAILED", "reason": "Expected all historical instance IDs to remain in DescribeInstances output; no receipt was written. Revised observation preserves missing IDs without inferring their state."},
    "budget": {k: ledger[k] for k in ["revision", "owner_task_cap_usd", "total_reserved_usd", "remaining_unreserved_usd", "updated_utc"]},
    "budget_ledger_path": str(ledger_path), "budget_ledger_sha256": hashlib.sha256(ledger_bytes).hexdigest(),
    "budget_boundary": "Reservations are spending bounds, not invoiced charges; no refund applied.",
    "cleanup_boundary": "Fresh EC2 query requested all six IDs. An absent ID alone does not establish termination. All six saved lifecycle receipts confirm termination, role and security-group cleanup. Private evidence buckets retained."
}
path = RECORDS / "completion_provider_observation_001.json"
with path.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(result, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps(result))
