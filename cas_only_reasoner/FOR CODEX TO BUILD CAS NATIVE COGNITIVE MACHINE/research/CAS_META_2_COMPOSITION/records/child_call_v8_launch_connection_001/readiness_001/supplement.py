"""Read-only follow-up for the empty S3 transfer product lookup; retain query 27."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import sys
import importlib.util
import boto3
from botocore.config import Config
spec = importlib.util.spec_from_file_location("readonly_readiness_probe", Path(__file__).resolve().with_name("probe.py"))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

started = datetime.now(timezone.utc).isoformat()
session = boto3.Session(profile_name="default", region_name=probe.REGION)
cfg = Config(connect_timeout=10, read_timeout=20, retries={"max_attempts": 0})
clients = {name: session.client(name, region_name="us-east-1" if name == "pricing" else probe.REGION,
                               config=cfg) for name in ("sts", "pricing")}
identity = probe.call(clients, "28_identity_followup", "sts", "get_caller_identity", {}, probe.selector("Account", "Arn"))
if identity.get("response", {}).get("Account") != probe.ACCOUNT:
    raise SystemExit("ACCOUNT_OR_CREDENTIALS_BLOCKER")
queries = [
    probe.price("29_internet_transfer", "AWSDataTransfer", {"fromLocation": "US West (Oregon)", "toLocation": "External", "transferType": "AWS Outbound"}),
    probe.price("30_ec2_internet_transfer", "AmazonEC2", {"fromLocation": "US West (Oregon)", "toLocation": "External", "transferType": "AWS Outbound"}),
    probe.price("31_scheduler_price", "AWSEvents", {"location": "US West (Oregon)", "group": "SchedulerInvocation"}),
]
results = [probe.call(clients, *query) for query in queries]
receipt = {"schema": "cas-meta2-readonly-pricing-followup/8", "started_utc": started,
    "finished_utc": datetime.now(timezone.utc).isoformat(), "provider_mutations": 0,
    "command": [sys.executable, "-B", str(Path(__file__).resolve())], "cwd": str(Path.cwd()),
    "script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
    "source_probe_sha256": sha256(Path(probe.__file__).read_bytes()).hexdigest(),
    "query_status": {r["label"]: r["status"] for r in [identity, *results]}}
print(json.dumps(probe.save("supplement_receipt.json", receipt)))
