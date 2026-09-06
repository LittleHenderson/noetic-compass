"""Register a new read-only AWS inspection under existing authority; no launch."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from aws import launch_native_failure_inspection_v8 as launch
from aws import budget


def write_new(path, value):
    with path.open("xb") as stream:
        stream.write(launch.encoded(value))


def main():
    target = HERE / "registration_001"
    if target.exists():
        raise ValueError("REGISTRATION_ALREADY_EXISTS")
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    request = launch.build_request(source, "subnet-0eb3ca4bf5ca98f24",
        ROOT / "records/aws_child_qualification_v8_001/execution_001/cloud_artifacts.zip")
    ledger = budget.read_ledger()
    request_hash = sha256(launch.encoded(request)).hexdigest()
    authority = {"schema": "cas-meta2-native-failure-inspection-standing-authority/8",
        "standing_campaign_authorization": True, "campaign_cap_usd": "400.00", "max_job_cost_usd": "4.00",
        "experiment": launch.EXPERIMENT, "training": False, "native_execution": False, "sqlite_read_only": True,
        "launch_request_sha256": request_hash,
        **{key: request[key] for key in ("job", "parent_source_sha", "worker_source_sha", "source_archive_sha256",
            "source_manifest_sha256", "original_job")},
        "campaign_approval": {key: ledger["approval"][key] for key in ("path", "sha256")},
        "standing_user_message": {"path": str(ROOT / "records/aws_prefix_diagnostic_v8_001/authorization_001/user_message_full.txt"),
            "sha256": launch.STANDING_MESSAGE_SHA256}}
    authority_hash = sha256(launch.encoded(authority)).hexdigest()
    template_path = ROOT / "records/aws_child_qualification_v8_001/registration_001/capture_parent.py"
    template = launch.read_pinned(template_path, "9d92311d10b93aa72738de8b59754193e1f0bb782f2a43a2ae453f05f66472b1").decode()
    replacements = {
        "one registered qualification launch": "one registered read-only failure inspection",
        "aws.launch_child_qualification_v8": "aws.launch_native_failure_inspection_v8",
        "cas-meta2-child-qualification-parent-capture/8": "cas-meta2-native-inspection-parent-capture/8",
        "0b1b73e0b750c3c657eed42686e5aebdcd2b768786f7240134ac4d67899bf861": request_hash,
        "3c7e5dcfd574257aed2a6e855284f5f6183e6ff89272b4ff737fefb803adcf49": authority_hash}
    for old, new in replacements.items():
        if template.count(old) != 1:
            raise ValueError("CAPTURE_TEMPLATE_CHANGED:" + old)
        template = template.replace(old, new)
    compile(template, "capture_parent.py", "exec")
    target.mkdir(parents=True, exist_ok=False)
    write_new(target / "launch_request.json", request)
    write_new(target / "standing_authority.json", authority)
    write_new(target / "ledger_observation.json", ledger)
    with (target / "capture_parent.py").open("xb") as stream:
        stream.write(template.encode())
    launch.validate_authority(target / "standing_authority.json", authority_hash, request, request_hash, ledger)
    receipt = {"job": request["job"], "source_sha": source, "request_sha256": request_hash,
        "authority_sha256": authority_hash, "source_archive_sha256": request["source_archive_sha256"],
        "source_manifest_sha256": request["source_manifest_sha256"],
        "files": {p.name: sha256(p.read_bytes()).hexdigest() for p in target.iterdir()},
        "provider_calls": False, "new_reservation": False, "training": False,
        "native_execution": False, "sqlite_read_only": True}
    write_new(target / "registration_receipt.json", receipt)
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
