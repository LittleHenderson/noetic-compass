"""Reproduce both historical studies using immutable anchors and saved predictions."""
import hashlib
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
HERE = ROOT / "records/typed_pointer_001"
SOURCE = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE
runs = [
    ("helm1", HERE/"study_helm1_certified.json", HERE/"trust_anchor_helm1_certified.json",
     HERE/"admission_helm1_certified/gate_reading.json", "receipt_helm1_certified_"),
    ("helm2", HERE/"admission_001/study.json", HERE/"trust_anchor_helm2_experimental_20208c92.json",
     HERE/"admission_001/gate_reading.json", "receipt_"),
]
for name,study,anchor,gate,prefix in runs:
    output = OUT / (name+"_rescore.json")
    if output.exists():
        raise SystemExit("Refusing to replace acceptance record: "+str(output))
    command = [sys.executable, "-B", str(HERE/"trusted_rescore.py"),
               "--study",str(study),"--anchor",str(anchor),"--frozen-reading",str(gate),"--out",str(output)]
    for seed in ("20260917","20260918","20260919"):
        command += ["--receipt",seed+"="+str(SOURCE/(prefix+seed))]
    job = {"command":command,"cpu_only":True,"timeout_seconds":900,"new_model_executions":0,
           "authority":"docs/OWNER_RUN_AUTHORIZATION_20260922.md and current 2026-09-23 repair request",
           "study_sha256":hashlib.sha256(study.read_bytes()).hexdigest(),
           "anchor_sha256":hashlib.sha256(anchor.read_bytes()).hexdigest(),
           "tool_sha256":hashlib.sha256((HERE/"trusted_rescore.py").read_bytes()).hexdigest()}
    (OUT/(name+"_rescore_job.json")).write_text(json.dumps(job,indent=2)+"\n",encoding="utf-8")
    start=time.monotonic()
    with (OUT/(name+"_rescore_stdout.txt")).open("x",encoding="utf-8") as stdout, (OUT/(name+"_rescore_stderr.txt")).open("x",encoding="utf-8") as stderr:
        try:
            result=subprocess.run(command,stdout=stdout,stderr=stderr,timeout=900)
            exit_code=result.returncode
        except subprocess.TimeoutExpired:
            exit_code="TIMEOUT"
    receipt={"elapsed_seconds":time.monotonic()-start,"exit_code":exit_code}
    (OUT/(name+"_rescore_execution.json")).write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(name,receipt,flush=True)
    if exit_code != 0:
        raise SystemExit(1)
