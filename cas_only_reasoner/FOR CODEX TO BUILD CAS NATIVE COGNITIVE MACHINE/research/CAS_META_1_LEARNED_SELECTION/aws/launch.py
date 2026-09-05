"""Plan by default. Explicit capped execution creates only a new CAS-META-1 job.

No torch import or neural work occurs on the client. This launcher has not been
cloud-executed merely because its pure contract tests pass.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import inspect
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import stat
import sys
import time
import tempfile
import uuid
import zipfile

PILOT_ROOT = Path(__file__).resolve().parents[1]
PLAN_FILE = Path(__file__).with_name("launch_plan.json")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SHA1 = re.compile(r"[0-9a-f]{40}\Z")
ACCEPTED_BASELINE = "0917267b1354e5d036263eaa6ba9a7197eafb776"


class LaunchRefused(ValueError):
    pass


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_relative(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise LaunchRefused("UNSAFE_ARCHIVE_PATH")
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in (".", "..", "") for x in value.split("/")):
        raise LaunchRefused("UNSAFE_ARCHIVE_PATH")
    return str(p)


def validate_archive(path: Path, expected_sha: str, source_sha: str, plan: dict) -> dict:
    if not SHA256.fullmatch(expected_sha) or not SHA1.fullmatch(source_sha):
        raise LaunchRefused("FULL_SHA_REQUIRED")
    if digest(path) != expected_sha:
        raise LaunchRefused("ARCHIVE_SHA_MISMATCH")
    with zipfile.ZipFile(path) as archive:
        names, total = set(), 0
        for info in archive.infolist():
            name = safe_relative(info.filename.rstrip("/"))
            if name in names or stat.S_ISLNK(info.external_attr >> 16):
                raise LaunchRefused("DUPLICATE_OR_SYMLINK_ARCHIVE_ENTRY")
            names.add(name)
            total += info.file_size
            if total > plan["archive_expanded_bytes_max"]:
                raise LaunchRefused("ARCHIVE_SIZE_CEILING")
        manifest = json.loads(archive.read("launch_manifest.json"))
        if manifest.get("schema_version") != 1 or manifest.get("source_sha") != source_sha:
            raise LaunchRefused("SOURCE_IDENTITY_MISMATCH")
        if manifest.get("baseline_sha") != ACCEPTED_BASELINE:
            raise LaunchRefused("ACCEPTED_BASELINE_REQUIRED")
        for key in ("pilot_dir", "data_dir", "dependency_lock"):
            safe_relative(manifest[key])
        wheels = manifest.get("wheel_paths", [])
        if len(wheels) != 2 or len(set(wheels)) != 2 or any(not safe_relative(w).endswith(".whl") for w in wheels):
            raise LaunchRefused("TWO_FROZEN_WHEELS_REQUIRED")
        hashes = manifest.get("files_sha256", {})
        actual = {i.filename for i in archive.infolist() if not i.is_dir()} - {"launch_manifest.json"}
        if set(hashes) != actual:
            raise LaunchRefused("ARCHIVE_MANIFEST_COVERAGE_MISMATCH")
        for name, sha in hashes.items():
            safe_relative(name)
            if not SHA256.fullmatch(sha) or hashlib.sha256(archive.read(name)).hexdigest() != sha:
                raise LaunchRefused("ARCHIVE_MEMBER_HASH_MISMATCH")
        if not all(w in actual for w in wheels) or manifest["dependency_lock"] not in actual:
            raise LaunchRefused("DECLARED_INPUT_MISSING")
        for key in ("pilot_dir", "data_dir"):
            if not any(n.startswith(manifest[key] + "/") for n in actual):
                raise LaunchRefused("DECLARED_DIRECTORY_MISSING")
        lock = archive.read(manifest["dependency_lock"]).decode("utf-8")
        for line in lock.splitlines():
            pin = line.strip()
            if not pin or pin.startswith("#"): continue
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*==[A-Za-z0-9_.+!-]+",pin) or pin.lower().startswith("torch==") or "+cpu" in pin:
                raise LaunchRefused("GPU_LOCK_REQUIRES_EXACT_PINS_AND_SEPARATE_TORCH")
        return manifest


def validate_approval(cap: str | None, plan: dict) -> None:
    try:
        supplied = Decimal(cap or "NaN")
        if not supplied.is_finite() or supplied != Decimal(plan["approved_cap_usd_required"]):
            raise LaunchRefused("EXPLICIT_100_USD_TASK_APPROVAL_REQUIRED")
    except InvalidOperation as exc:
        raise LaunchRefused("INVALID_APPROVAL_CAP") from exc
    if (plan["instance_count"], plan["runtime_seconds_max"], plan["automatic_retries"], plan["ebs_gb"]) != (1, 3600, 0, 75):
        raise LaunchRefused("UNREGISTERED_RESOURCE_PLAN")
    fixed = {"approved_cap_usd_required":"100.00","owner_task_cap_usd":"100.00","per_launch_reserved_cap_usd":"2.00","account_id":"807562639912","region":"us-west-2","instance_type":"g4dn.xlarge",
             "ami_id":"ami-0c779ec711a581954","training_seconds_max":2700,"ebs_type":"gp3",
             "ebs_encrypted":True,"delete_on_termination":True,"artifact_bytes_max":1073741824,
             "archive_expanded_bytes_max":536870912,"s3_retention_days":7,
             "torch_version":"2.11.0","torch_cuda_version":"12.8",
             "torch_index_url":"https://download.pytorch.org/whl/cu128"}
    if any(plan.get(k) != v for k,v in fixed.items()):
        raise LaunchRefused("UNREGISTERED_RESOURCE_PLAN")


def reserve_budget(ledger_path: Path, job: str, source_sha: str, archive_sha: str, plan: dict) -> dict:
    """Exclusive, atomic $2 reservation; never auto-refund an attempted job."""
    validate_approval("100.00",plan)
    if not re.fullmatch(r"cas-meta1-[a-zA-Z0-9-]+",job):
        raise LaunchRefused("BUDGET_JOB_ID_REQUIRED")
    ledger_path.parent.mkdir(parents=True,exist_ok=True)
    lock_path = ledger_path.with_suffix(ledger_path.suffix+".lock")
    try:
        lock = lock_path.open("x",encoding="utf-8")
    except FileExistsError as exc:
        raise LaunchRefused("BUDGET_LEDGER_LOCKED_FAIL_CLOSED") from exc
    temporary = None
    try:
        with lock:
            lock.write(json.dumps({"job":job,"pid":os.getpid()})); lock.flush(); os.fsync(lock.fileno())
            if ledger_path.exists():
                ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            else:
                ledger = {"schema_version":1,"task":"CAS-META-1 learned selection","owner_task_cap_usd":"100.00","reservations":[]}
            if ledger.get("schema_version") != 1 or ledger.get("owner_task_cap_usd") != "100.00" or type(ledger.get("reservations")) is not list:
                raise LaunchRefused("INVALID_BUDGET_LEDGER")
            reservations = ledger["reservations"]
            if any(r.get("reserved_usd") != "2.00" for r in reservations) or len({r.get("job") for r in reservations}) != len(reservations):
                raise LaunchRefused("INVALID_BUDGET_RESERVATIONS")
            if any(r["job"] == job for r in reservations):
                raise LaunchRefused("BUDGET_JOB_ALREADY_RESERVED_NO_RETRY")
            total = Decimal(2) * (len(reservations)+1)
            if total > Decimal(100): raise LaunchRefused("TASK_BUDGET_EXHAUSTED")
            reservation = {"job":job,"reserved_usd":"2.00","source_sha":source_sha,"archive_sha256":archive_sha,
                           "reserved_utc":datetime.now(timezone.utc).isoformat(),"status":"RESERVED_NO_AUTOMATIC_REFUND"}
            reservations.append(reservation)
            ledger["total_reserved_usd"] = str(total)
            ledger["remaining_unreserved_usd"] = str(Decimal(100)-total)
            with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=ledger_path.parent,prefix=".budget-",suffix=".tmp",delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(ledger,stream,indent=2); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary,ledger_path)
            temporary = None
            return {"reservation":reservation,"ledger_path":str(ledger_path),"total_reserved_usd":str(total),"remaining_unreserved_usd":str(Decimal(100)-total)}
    finally:
        if temporary is not None and temporary.exists(): temporary.unlink()
        lock_path.unlink()


def check_tag(tags: list[dict], job: str) -> None:
    if {t["Key"]: t["Value"] for t in tags}.get("cas_meta_job") != job:
        raise LaunchRefused("RESOURCE_OWNERSHIP_MISMATCH")


def verify_launcher_identity(manifest: dict) -> dict:
    records = {}
    for path in (Path(__file__).resolve(),PLAN_FILE):
        key = manifest["pilot_dir"]+"/aws/"+path.name
        actual = digest(path)
        if manifest["files_sha256"].get(key) != actual:
            raise LaunchRefused("LOCAL_LAUNCHER_ARCHIVE_IDENTITY_MISMATCH")
        records[key] = actual
    return records


def reconcile_instance(ec2, job: str) -> dict:
    """Recover an uncertain RunInstances response; no match is not proof of absence."""
    response = ec2.describe_instances(Filters=[{"Name":"tag:cas_meta_job","Values":[job]},
                                              {"Name":"client-token","Values":[job]}])
    if response.get("NextToken"):
        raise LaunchRefused("TERMINATION_UNCONFIRMED:PAGINATED_JOB_IDENTITY")
    instances = [i for r in response["Reservations"] for i in r["Instances"]]
    if len(instances) != 1:
        raise LaunchRefused("TERMINATION_UNCONFIRMED:EXPECTED_EXACTLY_ONE_JOB_INSTANCE")
    instance = instances[0]
    check_tag(instance.get("Tags",[]),job)
    if instance.get("ClientToken") != job:
        raise LaunchRefused("TERMINATION_UNCONFIRMED:CLIENT_TOKEN_MISMATCH")
    return instance


def verify_schedule(confirmed: dict, target: dict, expression: str) -> None:
    if (confirmed.get("State") != "ENABLED" or confirmed.get("ScheduleExpression") != expression
            or confirmed.get("ScheduleExpressionTimezone") != "UTC"
            or confirmed.get("FlexibleTimeWindow") != {"Mode":"OFF"}
            or confirmed.get("ActionAfterCompletion") != "DELETE"
            or any(confirmed.get("Target",{}).get(k) != v for k,v in target.items())):
        raise LaunchRefused("CLOUD_DEADLINE_NOT_CONFIRMED")


def build_evidence_bundle(artifact_root, bundle, limit, job_record):
    """Pure file packaging: oversize output becomes an explicit bounded failure packet."""
    import hashlib, json, pathlib, zipfile
    artifact_root, bundle = pathlib.Path(artifact_root), pathlib.Path(bundle)
    files = sorted(p for p in artifact_root.rglob('*') if p.is_file() or p.is_symlink())
    index, index_hash, total, unsafe = [], hashlib.sha256(), 0, 0
    for path in files:
        entry = {'path':path.relative_to(artifact_root).as_posix()}
        if path.is_symlink():
            entry.update(status='SYMLINK_OMITTED'); unsafe += 1
        else:
            entry['bytes'] = path.stat().st_size
            total += entry['bytes']
            h = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda:stream.read(1048576),b''): h.update(block)
            entry['sha256'] = h.hexdigest()
        index_hash.update(json.dumps(entry,sort_keys=True,separators=(',',':')).encode()+b'\n')
        index.append(entry)
    # Space for ZIP framing, receipt and manifest; logs from bootstrap are separate.
    payload_limit = limit - 2097152
    partial = total > payload_limit or unsafe > 0
    selected, selected_bytes = [], 0
    if not partial:
        selected = [p for p in files if not p.is_symlink()]
    else:
        # Keep small receipts and candidate weights when they fit. Never alter originals.
        priorities = sorted((p for p in files if not p.is_symlink()),
                            key=lambda p:(p.suffix != '.pt',p.suffix not in ('.json','.xml'),str(p)))
        fallback_limit = min(64*1024*1024,payload_limit) - 2097152
        for path in priorities:
            size = path.stat().st_size
            if path.suffix == '.pt' or (path.suffix in ('.json','.xml','.txt') and size <= 262144):
                if selected_bytes + size <= fallback_limit:
                    selected.append(path); selected_bytes += size
    selected_names = {p.relative_to(artifact_root).as_posix() for p in selected}
    record = dict(job_record)
    record.update(partial_evidence=partial, original_file_count=len(files), original_bytes=total,
                  included_full_file_count=len(selected), omitted_full_file_count=len(files)-len(selected),
                  original_file_index_sha256=index_hash.hexdigest(),
                  index_hash_format='SHA256 of canonical JSON entry plus LF for every sorted original path',
                  index_entries=index[:1000], index_entries_omitted=max(0,len(index)-1000),
                  artifact_bytes_max=limit)
    if partial:
        record.update(returncode=1,failure='ARTIFACT_CEILING_OR_UNSAFE_ENTRY; bounded evidence preserved')
    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in selected: archive.write(path,path.relative_to(artifact_root).as_posix())
        if partial:
            for index_number,path in enumerate(p for p in files if p.suffix == '.log' and not p.is_symlink()):
                if index_number >= 2: break
                with path.open('rb') as stream:
                    stream.seek(max(0,path.stat().st_size-1048576))
                    archive.writestr('failure_log_tails/'+path.name,stream.read(1048576))
        archive.writestr('artifact_collection_receipt.json',json.dumps(record,sort_keys=True,indent=2))
    if bundle.stat().st_size > limit:
        raise RuntimeError('BOUNDED_FAILURE_PACKET_EXCEEDED_CEILING')
    return record


def sample_artifact_bytes(root):
    """SQLite WAL/SHM files can disappear as a completed task closes its store."""
    total = 0
    for path in root.rglob('*'):
        try:
            if path.is_file(): total += path.stat().st_size
        except FileNotFoundError:
            continue
    return total


def remote_program(config: dict) -> str:
    """Return remote-only bookkeeping/bootstrap. It never executes on the client."""
    return "CONFIG = " + repr(config) + "\n" + inspect.getsource(build_evidence_bundle) + "\n" + inspect.getsource(sample_artifact_bytes) + "\n" + r'''
import hashlib, json, os, pathlib, platform, subprocess, sys, time, traceback, zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
root = pathlib.Path('/opt/cas-meta1')
payload = root / 'payload.zip'
def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1048576), b''): h.update(block)
    return h.hexdigest()
def run(argv, **kwargs):
    print(json.dumps({'command': argv}), flush=True)
    return subprocess.run(argv, check=True, **kwargs)
def s3_get(key, target):
    run(['aws','s3','cp','s3://'+CONFIG['bucket']+'/'+key,str(target),'--region',CONFIG['region']])
start = time.time()
returncode = 1
out = root/'early_failure'
out.mkdir(parents=True,exist_ok=True)
artifact_root = out
m = CONFIG['manifest']

def bounded_process(argv, log_path, *, env, cwd, seconds, deadline):
    stage_start = time.time()
    with log_path.open('w') as log:
        process = subprocess.Popen(argv,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            while process.poll() is None:
                size = sample_artifact_bytes(artifact_root)
                if size > CONFIG['artifact_bytes_max'] - 2097152 or time.time()-stage_start > seconds or time.time() > deadline-120:
                    raise RuntimeError('PROCESS_TIME_OR_ARTIFACT_CEILING')
                time.sleep(2)
            return process.returncode
        finally:
            # Even a monitor error must stop the writer before evidence packaging.
            if process.poll() is None:
                try: process.terminate()
                except ProcessLookupError: pass
                try: process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    try: process.kill()
                    except ProcessLookupError: pass
                    process.wait(timeout=15)

try:
    # No training or dependency installation before the external deadline is confirmed.
    permit = root / 'permit.json'
    for attempt in range(60):
        try:
            s3_get('input/permit.json', permit)
            p = json.loads(permit.read_text())
            if p['job'] != CONFIG['job'] or p['archive_sha256'] != CONFIG['archive_sha256'] or not p['cloud_deadline_confirmed']:
                raise RuntimeError('INVALID_CLOUD_DEADLINE_PERMIT')
            break
        except subprocess.CalledProcessError: time.sleep(5)
    else: raise RuntimeError('CLOUD_DEADLINE_NOT_CONFIRMED')
    deadline = datetime.fromisoformat(p['deadline']).timestamp()
    if deadline - time.time() < 300: raise RuntimeError('INSUFFICIENT_REMAINING_CLOUD_TIME')
    s3_get('input/payload.zip', payload)
    if sha(payload) != CONFIG['archive_sha256']: raise RuntimeError('ARCHIVE_SHA_MISMATCH')
    with zipfile.ZipFile(payload) as z:
        m = json.loads(z.read('launch_manifest.json'))
        if m != CONFIG['manifest']: raise RuntimeError('MANIFEST_MISMATCH')
        for name, expected in m['files_sha256'].items():
            if hashlib.sha256(z.read(name)).hexdigest() != expected: raise RuntimeError('MEMBER_HASH_MISMATCH')
        z.extractall(root / 'package') # names and membership were checked before publication
    package = root / 'package'
    out = package / m['pilot_dir'] / 'runs' / 'cloud_job'
    out.mkdir(parents=True)
    artifact_root = out.parent # Also preserve the four GPU contract tests' durable evidence.
    py = root / 'venv' / 'bin' / 'python'
    run([sys.executable,'-m','venv',str(root / 'venv')],timeout=max(1,deadline-time.time()-240))
    run([str(py),'-m','pip','install','--disable-pip-version-check','torch==2.11.0','--index-url',CONFIG['torch_index_url'],'--report',str(out/'torch_install.json')],timeout=max(1,deadline-time.time()-240))
    run([str(py),'-m','pip','install','--disable-pip-version-check','-r',str(package/m['dependency_lock']),'--report',str(out/'dependency_install.json')],timeout=max(1,deadline-time.time()-240))
    run([str(py),'-m','pip','install','--no-deps',*[str(package/w) for w in m['wheel_paths']],'--report',str(out/'frozen_wheel_install.json')],timeout=max(1,deadline-time.time()-240))
    probe = "import torch,json,sys,platform; assert torch.__version__=='2.11.0+cu128'; assert torch.version.cuda=='12.8'; assert torch.cuda.is_available(); assert torch.cuda.device_count()==1; print(json.dumps({'python':sys.version,'platform':platform.platform(),'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0)}))"
    with (out/'runtime.json').open('w') as f: run([str(py),'-c',probe],stdout=f,timeout=60)
    with (out/'pip_freeze.txt').open('w') as f: run([str(py),'-m','pip','freeze','--all'],stdout=f,timeout=30)
    env = dict(os.environ)
    env['PYTHONPATH'] = str(package/m['pilot_dir']) + ':' + str(package/'research/CASFORMER_v0_3_META_LOGIC_WIP')
    env['CUDA_VISIBLE_DEVICES'] = '0'
    env['CAS_META1_AWS_JOB_ID'] = CONFIG['job']
    env['CAS_META1_SOURCE_SHA'] = m['source_sha']
    env['CAS_META1_RUN_GPU_TESTS'] = '1'
    gpu_argv = [str(py),'-m','pytest','-m','gpu','tests/test_execution_contract.py','-q','--junitxml',str(out/'gpu_contract_tests.xml'),'-p','no:cacheprovider']
    (out/'gpu_contract_command.json').write_text(json.dumps(gpu_argv,indent=2))
    if deadline-time.time() < 300: raise RuntimeError('INSUFFICIENT_GPU_PREFLIGHT_TIME')
    gpu_code = bounded_process(gpu_argv,out/'gpu_contract_tests.log',env=env,cwd=package/m['pilot_dir'],seconds=600,deadline=deadline)
    suites = list(ET.parse(out/'gpu_contract_tests.xml').getroot().iter('testsuite'))
    totals = {key:sum(int(s.get(key,'0')) for s in suites) for key in ('tests','failures','errors','skipped')}
    if gpu_code != 0 or totals != {'tests':4,'failures':0,'errors':0,'skipped':0}:
        raise RuntimeError('GPU_CONTRACT_TESTS_MUST_REPORT_EXACTLY_FOUR_PASSED:'+str(totals))
    (out/'gpu_contract_receipt.json').write_text(json.dumps({'passed':4,**totals}))
    env.pop('CAS_META1_RUN_GPU_TESTS')
    argv = [str(py),'-m','cas_meta1.train','--data',str(package/m['data_dir']),'--output',str(out/'training')]
    (out/'command.json').write_text(json.dumps(argv,indent=2))
    if deadline - time.time() < 180: raise RuntimeError('INSUFFICIENT_TRAINING_TIME_AFTER_INSTALL')
    returncode = bounded_process(argv,out/'training.log',env=env,cwd=package/m['pilot_dir'],seconds=CONFIG['training_seconds_max'],deadline=deadline)
except BaseException as exc:
    (out/'remote_failure.json').write_text(json.dumps({'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()},indent=2))
finally:
    job_record = {'job':CONFIG['job'],'source_sha':m['source_sha'],'baseline_sha':m['baseline_sha'],'archive_sha256':CONFIG['archive_sha256'],'returncode':returncode,'remote_wall_seconds':time.time()-start}
    (out/'job.json').write_text(json.dumps(job_record,indent=2))
    bundle = root/'artifacts.zip'
    collected = build_evidence_bundle(artifact_root,bundle,CONFIG['artifact_bytes_max']-1048576,job_record)
    returncode = collected['returncode']
    run(['aws','s3','cp',str(bundle),'s3://'+CONFIG['bucket']+'/results/artifacts.zip','--region',CONFIG['region']])
    complete = {'sha256':sha(bundle),'bytes':bundle.stat().st_size,'returncode':returncode,'job':CONFIG['job'],'partial_evidence':collected['partial_evidence'],'omitted_full_file_count':collected['omitted_full_file_count']}
    (root/'complete.json').write_text(json.dumps(complete))
    run(['aws','s3','cp',str(root/'complete.json'),'s3://'+CONFIG['bucket']+'/results/complete.json','--region',CONFIG['region']])
sys.exit(returncode)
'''


def user_data(config: dict, remote_sha256: str | None = None) -> str:
    remote_sha256 = remote_sha256 or hashlib.sha256(remote_program(config).encode()).hexdigest()
    if not SHA256.fullmatch(remote_sha256): raise LaunchRefused("REMOTE_SCRIPT_SHA_REQUIRED")
    # Timer is armed before network access; EXIT covers bootstrap errors as well.
    text = "\n".join([
        "#!/bin/bash", "set -eu", "umask 077", "export PYTHONDONTWRITEBYTECODE=1",
        "trap 'test ! -f /opt/cas-meta1/bootstrap.log || { tail -c 1048576 /opt/cas-meta1/bootstrap.log > /opt/cas-meta1/bootstrap-tail.log; aws s3 cp /opt/cas-meta1/bootstrap-tail.log " + shlex.quote("s3://" + config["bucket"] + "/results/bootstrap.log") + " --region " + shlex.quote(config["region"]) + " || true; }; shutdown -h now' EXIT",
        "( sleep 3500; shutdown -h now ) >/dev/null 2>&1 &",
        "mkdir -p /opt/cas-meta1",
        "exec > /opt/cas-meta1/bootstrap.log 2>&1",
        "command -v aws >/dev/null || { echo AWS_CLI_REQUIRED; exit 1; }",
        "PY=''",
        "for p in python3.12 python3.11 /opt/conda/bin/python /opt/pytorch/bin/python /home/ubuntu/anaconda3/bin/python /home/ubuntu/miniconda3/bin/python python3; do",
        "  if command -v \"$p\" >/dev/null 2>&1 && \"$p\" -c 'import sys; assert (3,11) <= sys.version_info[:2] <= (3,12)' 2>/dev/null; then PY=\"$p\"; break; fi",
        "done",
        "test -n \"$PY\" || { echo SUPPORTED_PYTHON_REQUIRED; exit 1; }",
        "aws s3 cp " + shlex.quote("s3://"+config["bucket"]+"/input/remote.py") + " /opt/cas-meta1/remote.py --region " + shlex.quote(config["region"]),
        "echo '" + remote_sha256 + "  /opt/cas-meta1/remote.py' | sha256sum -c -",
        '"$PY" /opt/cas-meta1/remote.py', "",
    ])
    if len(text.encode()) > 16384:
        raise LaunchRefused("EC2_USER_DATA_SIZE_CEILING")
    return text


def execute(args: argparse.Namespace, plan: dict, manifest: dict) -> dict:
    validate_approval(args.approved_cap_usd, plan)
    launcher_identity = verify_launcher_identity(manifest)
    # boto3 is intentionally unavailable to the plan/contract-test path.
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError

    if not re.fullmatch(r"subnet-[0-9a-f]+", args.subnet_id or ""):
        raise LaunchRefused("EXPLICIT_SUBNET_REQUIRED")
    output = Path(args.receipt_dir).resolve()
    if not output.is_relative_to(PILOT_ROOT) or output == PILOT_ROOT or output.exists():
        raise LaunchRefused("NEW_RECEIPT_DIRECTORY_INSIDE_PILOT_REQUIRED")
    cfg = Config(connect_timeout=10, read_timeout=30, retries={"max_attempts": 0})
    session = boto3.Session(profile_name=args.profile, region_name=plan["region"])
    clients = {s: session.client(s, config=cfg) for s in ("sts", "ec2", "iam", "s3", "scheduler")}
    sts, ec2, iam, s3, scheduler = (clients[s] for s in clients)
    identity = sts.get_caller_identity()
    if identity["Account"] != plan["account_id"]:
        raise LaunchRefused("AWS_ACCOUNT_MISMATCH")
    subnet = ec2.describe_subnets(SubnetIds=[args.subnet_id])["Subnets"][0]
    images = ec2.describe_images(ImageIds=[plan["ami_id"]])["Images"]
    if len(images) != 1 or images[0]["State"] != "available" or images[0].get("RootDeviceName") != "/dev/sda1":
        raise LaunchRefused("PINNED_AMI_UNAVAILABLE")
    pricing = session.client("pricing", region_name="us-east-1", config=cfg)
    fields = {"instanceType": plan["instance_type"], "location": "US West (Oregon)", "operatingSystem": "Linux", "tenancy": "Shared", "preInstalledSw": "NA", "capacitystatus": "Used"}
    prices = pricing.get_products(ServiceCode="AmazonEC2", Filters=[{"Type":"TERM_MATCH","Field":k,"Value":v} for k,v in fields.items()])["PriceList"]
    rates = [Decimal(d["pricePerUnit"]["USD"]) for raw in prices for t in json.loads(raw)["terms"]["OnDemand"].values() for d in t["priceDimensions"].values() if d["unit"] == "Hrs"]
    if rates != [Decimal(plan["on_demand_hourly_usd_max"])]:
        raise LaunchRefused("CURRENT_PRICE_REQUIRES_NEW_PLAN")
    job = "cas-meta1-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:8]
    budget_reservation = reserve_budget(PILOT_ROOT/"records"/"aws_budget_ledger.json",job,args.source_sha,args.sha256,plan)
    bucket = job + "-" + plan["account_id"]
    worker_role, timer_role = job + "-worker", job + "-timer"
    tags = [{"Key":"cas_meta_job","Value":job}]
    receipt = {"status":"STARTING","job":job,"plan":plan,"explicit_approved_cap_argument_usd":args.approved_cap_usd,"task_budget_reservation":budget_reservation,"local_launcher_identity":launcher_identity,"source_sha":args.source_sha,"archive_sha256":args.sha256,"manifest":manifest,"caller_arn":identity["Arn"],"official_price_response":prices,"resources":{},"events":[],"cleanup_errors":[]}
    output.mkdir(parents=True)
    def save():
        (output / "launch_receipt.json").write_text(json.dumps(receipt, indent=2, default=str), encoding="utf-8")
    def record(event, **details):
        receipt["events"].append({"time":datetime.now(timezone.utc).isoformat(),"event":event,**details}); save()
    def role(name, service, statements):
        trust = {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":service},"Action":"sts:AssumeRole"}]}
        created = iam.create_role(RoleName=name, AssumeRolePolicyDocument=json.dumps(trust), Tags=tags)["Role"]
        receipt["resources"][name] = created["Arn"]; save()
        iam.put_role_policy(RoleName=name, PolicyName="job-only", PolicyDocument=json.dumps({"Version":"2012-10-17","Statement":statements}))
        return created["Arn"]
    iid = None
    launch_attempted = False
    try:
        s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint":plan["region"]})
        receipt["resources"]["bucket"] = bucket; save()
        s3.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration={k:True for k in ("BlockPublicAcls","IgnorePublicAcls","BlockPublicPolicy","RestrictPublicBuckets")})
        s3.put_bucket_encryption(Bucket=bucket,ServerSideEncryptionConfiguration={"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]})
        s3.put_bucket_lifecycle_configuration(Bucket=bucket,LifecycleConfiguration={"Rules":[{"ID":"job-seven-days","Status":"Enabled","Filter":{"Prefix":""},"Expiration":{"Days":7},"AbortIncompleteMultipartUpload":{"DaysAfterInitiation":1}}]})
        role(worker_role,"ec2.amazonaws.com",[{"Effect":"Allow","Action":["s3:GetObject"],"Resource":f"arn:aws:s3:::{bucket}/input/*"},{"Effect":"Allow","Action":["s3:PutObject"],"Resource":f"arn:aws:s3:::{bucket}/results/*"}])
        iam.create_instance_profile(InstanceProfileName=worker_role, Tags=tags)
        receipt["resources"]["instance_profile"] = worker_role; save()
        iam.add_role_to_instance_profile(InstanceProfileName=worker_role,RoleName=worker_role)
        timer_arn = role(timer_role,"scheduler.amazonaws.com",[{"Effect":"Allow","Action":"ec2:TerminateInstances","Resource":f"arn:aws:ec2:{plan['region']}:{plan['account_id']}:instance/*","Condition":{"StringEquals":{"ec2:ResourceTag/cas_meta_job":job}}}])
        sg = ec2.create_security_group(GroupName=job, Description="CAS-META-1 outbound HTTPS only", VpcId=subnet["VpcId"], TagSpecifications=[{"ResourceType":"security-group","Tags":tags}])["GroupId"]
        receipt["resources"]["security_group"] = sg; save()
        ec2.revoke_security_group_egress(GroupId=sg,IpPermissions=[{"IpProtocol":"-1","IpRanges":[{"CidrIp":"0.0.0.0/0"}]}])
        ec2.authorize_security_group_egress(GroupId=sg,IpPermissions=[{"IpProtocol":"tcp","FromPort":443,"ToPort":443,"IpRanges":[{"CidrIp":"0.0.0.0/0"}]}])
        s3.upload_file(str(Path(args.archive).resolve()),bucket,"input/payload.zip")
        config = {**plan,"job":job,"bucket":bucket,"archive_sha256":args.sha256,"manifest":manifest}
        # Put the complete manifest outside EC2's 16KiB user-data limit.
        remote = remote_program(config)
        s3.put_object(Bucket=bucket,Key="input/remote.py",Body=remote.encode())
        script_sha = hashlib.sha256(remote.encode()).hexdigest()
        bootstrap = user_data(config,script_sha)
        if len(bootstrap.encode()) > 16384: raise LaunchRefused("EC2_USER_DATA_SIZE_CEILING")
        record("BOOTSTRAP_PINNED",sha256=hashlib.sha256(bootstrap.encode()).hexdigest(),remote_sha256=script_sha)
        time.sleep(10) # IAM propagation, not a retry of a job.
        launch_time = datetime.now(timezone.utc)
        deadline = launch_time + timedelta(seconds=plan["runtime_seconds_max"])
        launch_attempted = True
        receipt["run_instances_client_token"] = job
        record("INSTANCE_LAUNCH_ATTEMPTED",client_token=job)
        launched = ec2.run_instances(ImageId=plan["ami_id"],InstanceType=plan["instance_type"],MinCount=1,MaxCount=1,ClientToken=job,IamInstanceProfile={"Name":worker_role},InstanceInitiatedShutdownBehavior="terminate",MetadataOptions={"HttpTokens":"required","HttpEndpoint":"enabled"},NetworkInterfaces=[{"DeviceIndex":0,"SubnetId":args.subnet_id,"Groups":[sg],"AssociatePublicIpAddress":True,"DeleteOnTermination":True}],BlockDeviceMappings=[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":75,"VolumeType":"gp3","Encrypted":True,"DeleteOnTermination":True}}],TagSpecifications=[{"ResourceType":"instance","Tags":tags},{"ResourceType":"volume","Tags":tags}],UserData=bootstrap)
        iid = launched["Instances"][0]["InstanceId"]
        receipt["provider_launch_time"] = launched["Instances"][0].get("LaunchTime",launch_time).isoformat()
        receipt["resources"]["instance"] = iid; record("INSTANCE_CREATED",instance_id=iid,deadline=deadline.isoformat())
        target = {"Arn":"arn:aws:scheduler:::aws-sdk:ec2:terminateInstances","RoleArn":timer_arn,"Input":json.dumps({"InstanceIds":[iid]}),"RetryPolicy":{"MaximumRetryAttempts":0,"MaximumEventAgeInSeconds":60}}
        expression = "at("+deadline.strftime("%Y-%m-%dT%H:%M:%S")+")"
        # Record the exact name before creation so a lost response cannot orphan it.
        receipt["resources"]["schedule"] = job; save()
        scheduler.create_schedule(Name=job,ScheduleExpression=expression,ScheduleExpressionTimezone="UTC",FlexibleTimeWindow={"Mode":"OFF"},Target=target,ActionAfterCompletion="DELETE")
        confirmed = scheduler.get_schedule(Name=job)
        verify_schedule(confirmed,target,expression)
        record("CLOUD_DEADLINE_CONFIRMED",schedule=job,target=target)
        s3.put_object(Bucket=bucket,Key="input/permit.json",Body=json.dumps({"job":job,"archive_sha256":args.sha256,"cloud_deadline_confirmed":True,"deadline":deadline.isoformat()}).encode())
        while datetime.now(timezone.utc) < deadline:
            try:
                result = json.loads(s3.get_object(Bucket=bucket,Key="results/complete.json")["Body"].read())
                if result["job"] != job or not SHA256.fullmatch(result["sha256"]) or not 0 < result["bytes"] <= plan["artifact_bytes_max"]:
                    raise LaunchRefused("REMOTE_RESULT_IDENTITY_OR_SIZE")
                head = s3.head_object(Bucket=bucket,Key="results/artifacts.zip")
                if head["ContentLength"] != result["bytes"]: raise LaunchRefused("REMOTE_RESULT_SIZE_MISMATCH")
                artifact = output / "cloud_artifacts.zip"
                s3.download_file(bucket,"results/artifacts.zip",str(artifact))
                if digest(artifact) != result["sha256"]: raise LaunchRefused("DOWNLOADED_ARTIFACT_HASH_MISMATCH")
                receipt["result"] = result
                receipt["status"] = "AWS_JOB_FINISHED" if result["returncode"] == 0 else "AWS_JOB_FAILED"
                record("ARTIFACT_DOWNLOADED_AND_HASH_VERIFIED",path=str(artifact),sha256=result["sha256"])
                break
            except ClientError as exc:
                if exc.response["Error"]["Code"] not in ("NoSuchKey","404"): raise
            state = ec2.describe_instances(InstanceIds=[iid])["Reservations"][0]["Instances"][0]["State"]["Name"]
            if state in ("terminated","shutting-down"):
                raise LaunchRefused("INSTANCE_ENDED_WITHOUT_COMPLETION_RECEIPT")
            time.sleep(15)
        else: raise LaunchRefused("LOCAL_WATCHDOG_DEADLINE")
    except BaseException as exc:
        receipt["status"] = "AWS_JOB_BLOCKED_OR_FAILED"
        record("ERROR",error=type(exc).__name__,message=str(exc))
    finally:
        # A missing RunInstances response is not evidence that no instance exists.
        terminated = not launch_attempted
        if launch_attempted and iid is None:
            try:
                recovered = reconcile_instance(ec2,job)
                iid = recovered["InstanceId"]
                receipt["resources"]["instance"] = iid
                receipt["provider_launch_time"] = recovered["LaunchTime"].isoformat()
                record("INSTANCE_IDENTITY_RECOVERED",instance_id=iid,client_token=job)
            except Exception as exc:
                receipt["cleanup_errors"].append("TERMINATION_UNCONFIRMED: "+str(exc))
                record("INSTANCE_IDENTITY_UNCONFIRMED_RESOURCES_RETAINED")
        if iid:
            try:
                instance = ec2.describe_instances(InstanceIds=[iid])["Reservations"][0]["Instances"][0]
                check_tag(instance.get("Tags",[]),job)
                if instance["State"]["Name"] != "terminated": ec2.terminate_instances(InstanceIds=[iid])
                ec2.get_waiter("instance_terminated").wait(InstanceIds=[iid],WaiterConfig={"Delay":5,"MaxAttempts":24})
                terminated = True; record("INSTANCE_TERMINATION_CONFIRMED",instance_id=iid)
                seconds = (datetime.now(timezone.utc)-datetime.fromisoformat(receipt["provider_launch_time"])).total_seconds()
                receipt["cost_estimate"] = {"instance_wall_clock_seconds_upper_observation":seconds,"compute_ebs_ipv4_usd_estimate":str((Decimal(str(seconds))/Decimal(3600))*(Decimal("0.526")+Decimal(75)*Decimal("0.08")/Decimal(720)+Decimal("0.005"))),"excluded":"S3 requests and retention, transfer, taxes; not an AWS invoice"}
            except Exception as exc: receipt["cleanup_errors"].append("TERMINATION_UNCONFIRMED: "+str(exc))
        if terminated:
            if iid:
                try:
                    volumes = ec2.describe_volumes(Filters=[{"Name":"tag:cas_meta_job","Values":[job]}])["Volumes"]
                    receipt["remaining_job_volumes"] = [v["VolumeId"] for v in volumes if v["State"] != "deleted"]
                    if receipt["remaining_job_volumes"]: receipt["cleanup_errors"].append("EBS_DELETION_NOT_YET_CONFIRMED")
                except Exception as exc: receipt["cleanup_errors"].append("EBS_CHECK_FAILED: "+str(exc))
            cleanup = []
            if "schedule" in receipt["resources"]: cleanup.append(lambda: scheduler.delete_schedule(Name=job))
            if "instance_profile" in receipt["resources"]:
                cleanup.extend([lambda:iam.remove_role_from_instance_profile(InstanceProfileName=worker_role,RoleName=worker_role),lambda:iam.delete_instance_profile(InstanceProfileName=worker_role)])
            for name in (worker_role,timer_role):
                if name in receipt["resources"]:
                    cleanup.extend([lambda n=name:iam.delete_role_policy(RoleName=n,PolicyName="job-only"),lambda n=name:iam.delete_role(RoleName=n)])
            if "security_group" in receipt["resources"]:
                cleanup.append(lambda:ec2.delete_security_group(GroupId=receipt["resources"]["security_group"]))
            for action in cleanup:
                try: action()
                except Exception as exc:
                    absent = isinstance(exc,ClientError) and exc.response["Error"]["Code"] in ("ResourceNotFoundException","NoSuchEntity")
                    if not absent: receipt["cleanup_errors"].append(type(exc).__name__+": "+str(exc))
                finally: save()
        if "bucket" in receipt["resources"]:
            try:
                head = s3.head_object(Bucket=bucket,Key="results/bootstrap.log")
                if head["ContentLength"] > 1048576: raise LaunchRefused("BOOTSTRAP_LOG_CEILING")
                bootstrap_log = output / "bootstrap.log"
                s3.download_file(bucket,"results/bootstrap.log",str(bootstrap_log))
                receipt["bootstrap_log_sha256"] = digest(bootstrap_log)
            except ClientError as exc:
                receipt["bootstrap_log_status"] = exc.response["Error"]["Code"]
            except Exception as exc:
                receipt["bootstrap_log_status"] = type(exc).__name__ + ": " + str(exc)
        receipt["termination_confirmed"] = terminated
        receipt["s3_retention"] = "Dedicated job bucket objects expire after 7 days; empty bucket may remain without storage charges. Local evidence is retained."
        if receipt["cleanup_errors"]: receipt["status"] = "CLEANUP_REQUIRES_ATTENTION"
        save()
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--archive")
    parser.add_argument("--sha256")
    parser.add_argument("--source-sha")
    parser.add_argument("--approved-cap-usd")
    parser.add_argument("--profile", default="default")
    parser.add_argument("--subnet-id")
    parser.add_argument("--receipt-dir")
    args = parser.parse_args(argv)
    plan = json.loads(PLAN_FILE.read_text(encoding="utf-8"))
    try:
        manifest = None
        if args.archive:
            manifest = validate_archive(Path(args.archive),args.sha256 or "",args.source_sha or "",plan)
        if not args.execute:
            print(json.dumps({"plan":plan,"archive_verified":manifest is not None,"aws_actions_performed":False},indent=2)); return 0
        validate_approval(args.approved_cap_usd,plan)
        if manifest is None or not args.receipt_dir:
            raise LaunchRefused("PINNED_ARCHIVE_AND_RECEIPT_DIRECTORY_REQUIRED")
        receipt = execute(args,plan,manifest)
        print(json.dumps({"status":receipt["status"],"receipt_dir":args.receipt_dir},indent=2))
        return 0 if receipt["status"] == "AWS_JOB_FINISHED" else 1
    except (LaunchRefused,KeyError,OSError,zipfile.BadZipFile,json.JSONDecodeError) as exc:
        print(json.dumps({"status":"LAUNCH_REFUSED","reason":str(exc)})); return 2


if __name__ == "__main__":
    raise SystemExit(main())
