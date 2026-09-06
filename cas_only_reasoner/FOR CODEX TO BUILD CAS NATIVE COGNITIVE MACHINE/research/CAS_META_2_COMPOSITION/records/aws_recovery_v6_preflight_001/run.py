"""Read-only source, packet and budget preflight. This cannot launch a job."""
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SOURCE="bd3341b0da893d0a68cfc05fb454848d2f027cd7"
ARCHIVE="110c3f2d5ead8dbc0d241e7b01824af5d4a10d8e7bba414d0b2e00b70dfb1cad"
def write(name,value):
    with (HERE/name).open("xb") as f:
        f.write((json.dumps(value,sort_keys=True,indent=2)+"\n").encode())
def main():
    if (HERE/"receipt.json").exists(): raise ValueError("NEW_PREFLIGHT_REQUIRED")
    launcher=ROOT/"aws/launch_recovery_v6.py"
    spec=importlib.util.spec_from_file_location("read_only_recovery_preflight",launcher)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    before=m.verify_cli_source_before_helper_import(SOURCE)
    plan=json.loads(m.PLAN_FILE.read_bytes())
    m.validate_approval("400.00",plan)
    manifest=m.validate_archive(ROOT/"records/aws_recovery_v6_source_001",ARCHIVE,SOURCE,plan)
    local=m.verify_launcher_identity(manifest)
    packet=m.validate_prior_packet(ROOT/"records/aws_contrast_v6_001/cloud_artifacts.zip",manifest)
    ledger=m.budget.read_ledger()
    command=[sys.executable,"-B",str(launcher),"--archive",str(ROOT/"records/aws_recovery_v6_source_001"),
             "--sha256",ARCHIVE,"--source-sha",SOURCE,
             "--prior-packet",str(ROOT/"records/aws_contrast_v6_001/cloud_artifacts.zip")]
    write("command.json",command)
    with (HERE/"stdout.txt").open("xb") as out,(HERE/"stderr.txt").open("xb") as err:
        process=subprocess.run(command,cwd=ROOT,stdout=out,stderr=err,timeout=120)
    if process.returncode != 0: raise ValueError("PLAN_ONLY_CLI_FAILED")
    record=json.loads((HERE/"stdout.txt").read_bytes())
    if record.get("aws_actions_performed") is not False or record.get("archive_verified") is not True:
        raise ValueError("PLAN_ONLY_RECEIPT_MISMATCH")
    if m.verify_cli_source_before_helper_import(SOURCE)!=before: raise ValueError("PREFLIGHT_SOURCE_CHANGED")
    write("receipt.json",{"status":"RECOVERY_SOURCE_AND_PRIOR_PACKET_VERIFIED_NO_LAUNCH","utc":datetime.now(timezone.utc).isoformat(),
        "source_sha":SOURCE,"archive_sha256":ARCHIVE,"archive_bytes":(ROOT/"records/aws_recovery_v6_source_001").stat().st_size,
        "files_verified":len(local),"protected_files":manifest["protected_baseline_files"],
        "prior_packet":packet,"runtime_source_manifest_sha256":manifest["recovery"]["source_manifest_sha256"],
        "preimport_source":before,"source_files_sha256":local,"plan":plan,
        "canonical_budget_before":{"revision":ledger["revision"],"total_reserved_usd":ledger["total_reserved_usd"],
                                  "remaining_unreserved_usd":ledger["remaining_unreserved_usd"]},
        "requested_new_reservation_usd":plan["per_launch_reserved_cap_usd"],
        "new_reservation_performed":False,"provider_calls":False,"neural_execution":False,
        "command":command,"returncode":process.returncode,
        "stdout_sha256":sha256((HERE/"stdout.txt").read_bytes()).hexdigest(),
        "stderr_sha256":sha256((HERE/"stderr.txt").read_bytes()).hexdigest(),
        "script_sha256":sha256(Path(__file__).read_bytes()).hexdigest()})
    print(json.dumps({"status":"RECOVERY_SOURCE_AND_PRIOR_PACKET_VERIFIED_NO_LAUNCH","files_verified":len(local),
                      "source_sha":SOURCE,"remaining_unreserved_usd":ledger["remaining_unreserved_usd"]}))
if __name__=="__main__": main()

