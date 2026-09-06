"""One quota request for the user's H100 preference; never launch compute."""
from datetime import datetime, timezone
import json
from pathlib import Path

import boto3
from botocore.config import Config

ROOT = Path(__file__).resolve().parent


def main():
    receipt_path = ROOT / "request_receipt.json"
    if receipt_path.exists():
        raise RuntimeError("REQUEST_RECEIPT_EXISTS: inspect status; do not resubmit")
    session = boto3.Session(profile_name="default", region_name="us-west-2")
    cfg = Config(connect_timeout=10, read_timeout=30, retries={"max_attempts": 0})
    account = session.client("sts", config=cfg).get_caller_identity()["Account"]
    assert account == "807562639912"
    client = session.client("service-quotas", config=cfg)
    quota = client.get_service_quota(ServiceCode="ec2", QuotaCode="L-417A185B")
    history, token = [], None
    while True:
        args = {"ServiceCode": "ec2", "QuotaCode": "L-417A185B", "MaxResults": 100}
        if token:
            args["NextToken"] = token
        page = client.list_requested_service_quota_change_history_by_quota(**args)
        history.extend(page.get("RequestedQuotas", []))
        token = page.get("NextToken")
        if not token:
            break
    record = {"schema": "cas-meta2-h100-quota-request/0.1", "utc": datetime.now(timezone.utc).isoformat(),
        "account": account, "region": "us-west-2", "purpose": "One user-requested H100 p5.4xlarge",
        "desired_p_vcpus": 16, "quota_before": quota, "prior_requests": history,
        "gpu_launched": False, "spending_cap_changed": False, "automatic_retry": False}
    pending = [row for row in history if row.get("Status") in ("PENDING", "CASE_OPENED")]
    if quota["Quota"]["Value"] >= 16:
        record["status"] = "QUOTA_ALREADY_SUFFICIENT_NO_REQUEST"
    elif pending:
        record["status"] = "PENDING_REQUEST_EXISTS_NO_DUPLICATE"
    else:
        # Save the attempted operation before sending it. An uncertain response
        # must be resolved by reading history, not by automatically retrying.
        record["status"] = "REQUEST_ATTEMPTED"
        receipt_path.write_text(json.dumps(record, default=str, indent=2) + "\n", encoding="utf-8")
        try:
            record["response"] = client.request_service_quota_increase(
                ServiceCode="ec2", QuotaCode="L-417A185B", DesiredValue=16.0)
            record["status"] = "REQUEST_SUBMITTED"
        except Exception as error:
            record["status"] = "REQUEST_FAILED_OR_UNCERTAIN"
            record["error"] = {"type": type(error).__name__, "message": str(error)}
            if hasattr(error, "response"):
                record["error"]["provider_response"] = error.response
    receipt_path.write_text(json.dumps(record, default=str, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": record["status"], "response": record.get("response"),
        "error": record.get("error"), "receipt": str(receipt_path)}, default=str, indent=2))


if __name__ == "__main__":
    main()
