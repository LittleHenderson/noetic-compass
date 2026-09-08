"""Minimal AWS launcher for the teaching campaign's binding-fit training check.

One self-contained module: the frozen resource plan, the source-package
builder, the rendered worker script, and the AWS provider/launch lifecycle all
live here. Plan output is inert by default. Paid execution requires an
explicit, hash-bound launch request AND a separate standing authority that
names the job, the exact source/archive/manifest identities, the owner
authorization record, and the frozen budget. A single $4.00 reservation is
created exactly once through ``aws.budget.reserve_budget``; the job id is
refused if it is already reserved, and nothing is ever refunded or retried.

The AWS SDK (boto3/botocore) is imported LAZILY, only inside ``build()``.
Nothing in this module imports boto3, botocore, torch, or any provider at
import time; tests inject fake client stacks and fake git objects and never
reach the real SDK.

The worker script is rendered into the source package. On the instance it
creates (or discovers) an isolated venv, installs ``torch==2.11.0`` from the
repo-wide frozen ``cu128`` index and the two frozen wheels with ``--no-deps``,
then runs ``cas_meta2.binding_fit_training.mode.launch(...)`` with real torch
and the real policy/tokenizer/model construction, writes ``results/result.json``
plus a sha256 sidecar, and uploads both to the job S3 bucket — preserving
evidence on failure too.
"""
from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time
from hashlib import sha256
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from aws import budget

ROOT = Path(__file__).resolve().parents[1]
GIT_PREFIX = "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/"
PILOT = "research/CAS_META_2_COMPOSITION/"
WHEEL_PREFIX = "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/"

SCHEMA = "cas-teaching-binding-fit-launch/1"
REQUEST_SCHEMA = "cas-teaching-binding-fit-launch-request/1"
AUTHORITY_SCHEMA = "cas-teaching-binding-fit-launch-authority/1"
PACKAGE_SCHEMA = "cas-teaching-binding-fit-source-package/1"
MANIFEST_NAME = "binding_fit_source_manifest.json"
WORKER_NAME = "binding_fit_worker.py"

LEDGER_PATH = ROOT / "records/budget/campaign_ledger.json"
OWNER_AUTHORIZATION_PATH = (ROOT / "records/teaching_cycle_001/"
                            "binding_fit_training_check_001/OWNER_AUTHORIZATION.json")
CAMPAIGN_CAP_USD = "400.00"
RESERVATION_USD = "4.00"

# Frozen budget (must match cas_meta2.binding_fit_training.mode defaults).
FROZEN_MAX_OPTIMIZER_STEPS = 48
FROZEN_MAX_WALL_SECONDS = 600.0
FROZEN_LEARNING_RATE = 0.003

JOB_PATTERN = r"cas-meta2-teaching-binding-\d{14}-[a-f0-9]{8}"
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
INSTANCE_ID = re.compile(r"i-[0-9a-f]{17}\Z")

EXPERIMENT = {"profile": "binding_fit_training",
              "entrypoint": "cas_meta2.binding_fit_training.mode.launch"}

RESOURCE_PLAN = {
    "schema": "cas-teaching-binding-fit-resource-plan/1",
    "experiment": EXPERIMENT,
    "account": "807562639912",
    "region": "us-west-2",
    "ami": "ami-0fbbd0facbc9e3cff",
    "instance_type": "g7.2xlarge",
    "instance_count": 1,
    "gpu_name_contains": "RTX PRO 4500",
    "t4_rejected": True,
    "visible_gpu_count": 1,
    "torch_version": "2.11.0+cu128",
    "cuda_version": "12.8",
    "torch_index_url": "https://download.pytorch.org/whl/cu128",
    "on_demand_rate_ceiling_usd": "2.52",
    "worker_seconds_max": 600,
    "instance_seconds_max": 3600,
    "automatic_retries": 0,
    "reservation_usd": RESERVATION_USD,
    "training": True,
    "native_execution": False,
    "ebs": {"size_gib": 75, "iops": 3000, "throughput_mib_s": 125,
            "encrypted": True, "delete_on_termination": True},
    "network": {"inbound_rules": 0, "egress_tcp_443_only": True},
    "frozen_budget": {
        "max_optimizer_steps": FROZEN_MAX_OPTIMIZER_STEPS,
        "max_wall_seconds": FROZEN_MAX_WALL_SECONDS,
        "learning_rate": FROZEN_LEARNING_RATE,
        "reservation_usd": RESERVATION_USD,
    },
}

# Package member set: the teaching mode and its real transitive closure, the
# two frozen wheels, requirements, and the rendered worker script.
EXPLICIT_FILES = (
    PILOT + "cas_meta2/__init__.py",
    PILOT + "cas_meta2/codec.py",
    PILOT + "cas_meta2/features_v2.py",   # LosslessPublicTokenizer (teaching path)
    PILOT + "cas_meta2/policy.py",        # real policy construction for mode.launch
    PILOT + "requirements-gpu.txt",
)
SOURCE_DIRS = (
    PILOT + "cas_meta2/binding_fit_training",
    PILOT + "cas_meta2/teaching_cycle",
)
WHEELS = {
    WHEEL_PREFIX + "casformer_reference-0.1.0-py3-none-any.whl":
        "0487363cc7258c0e07ad65d137987088e01d5b95fc637cb0d63cfe41fd65d2ee",
    WHEEL_PREFIX + "cas_neural_cjt-0.2.0-py3-none-any.whl":
        "6f1ceac9140027a14cecc79fb399ef90a993cd0bd411e47970798860c4217ac9",
}
MAX_MEMBER_BYTES = 4 * 1024**2
MAX_MEMBER_COUNT = 2000
MAX_EXPANDED_BYTES = 96 * 1024**2
MAX_ARCHIVE_BYTES = 24 * 1024**2
WORKER_WHEEL_DIR = "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist"
WORKER_REQUIREMENTS = PILOT + "requirements-gpu.txt"


def require(condition, code):
    if not condition:
        raise ValueError(code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def digest(raw):
    return sha256(raw).hexdigest()


# --------------------------------------------------------------------------- #
# evidence sinks (never a link, never an in-memory-only paid run)
# --------------------------------------------------------------------------- #
def evidence_directory(path):
    path = Path(path).absolute()
    require(".." not in path.parts, "EVIDENCE_PATH_PARENT_COMPONENT")
    for ancestor in (path, *path.parents):
        require(not ancestor.is_symlink() and not getattr(ancestor, "is_junction", lambda: False)(),
                "EVIDENCE_LINKED_PATH")
    return path


def write_evidence(path, raw):
    path = evidence_directory(path)
    require(type(raw) is bytes and len(raw) <= 256 * 1024**2, "EVIDENCE_BYTES_BOUND")
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    require(path.stat().st_nlink == 1 and path.read_bytes() == raw, "EVIDENCE_READBACK_MISMATCH")
    return {"path": str(path), "sha256": digest(raw), "bytes": len(raw)}


def prepare_evidence(path):
    path = evidence_directory(path)
    require(not path.exists() and path.parent.is_dir(), "FRESH_RECEIPT_DIRECTORY_REQUIRED")
    path.mkdir()
    return path


# --------------------------------------------------------------------------- #
# request / authority / preflight validation
# --------------------------------------------------------------------------- #
def scope():
    """Return the frozen resource plan. Plan output is not an authorization."""
    return json.loads(canonical(RESOURCE_PLAN))


def validate_request(request):
    require(type(request) is dict and request.get("schema") == REQUEST_SCHEMA,
            "BINDING_FIT_REQUEST_SCHEMA")
    require(set(request) == {"schema", "job", "source_sha", "archive_sha256",
                             "manifest_sha256", "launch_authorized"},
            "BINDING_FIT_REQUEST_FIELDS")
    require(type(request["job"]) is str
            and re.fullmatch(JOB_PATTERN, request["job"]) is not None,
            "BINDING_FIT_REQUEST_JOB")
    require(type(request["source_sha"]) is str and bool(HEX40.fullmatch(request["source_sha"])),
            "BINDING_FIT_REQUEST_SOURCE_SHA")
    for key in ("archive_sha256", "manifest_sha256"):
        require(type(request[key]) is str and bool(HEX64.fullmatch(request[key])),
                "BINDING_FIT_REQUEST_HASH:" + key)
    require(request["launch_authorized"] is False, "BINDING_FIT_REQUEST_INERT")
    return request


def validate_authority(authority):
    require(type(authority) is dict and authority.get("schema") == AUTHORITY_SCHEMA,
            "BINDING_FIT_AUTHORITY_SCHEMA")
    require(set(authority) == {
        "schema", "job", "source_sha", "archive_sha256", "manifest_sha256",
        "owner_authorization_sha256", "learning_rate", "max_optimizer_steps",
        "max_wall_seconds", "reservation_usd"}, "BINDING_FIT_AUTHORITY_FIELDS")
    require(type(authority["job"]) is str
            and re.fullmatch(JOB_PATTERN, authority["job"]) is not None,
            "BINDING_FIT_AUTHORITY_JOB")
    require(type(authority["source_sha"]) is str and bool(HEX40.fullmatch(authority["source_sha"])),
            "BINDING_FIT_AUTHORITY_SOURCE_SHA")
    for key in ("archive_sha256", "manifest_sha256", "owner_authorization_sha256"):
        require(type(authority[key]) is str and bool(HEX64.fullmatch(authority[key])),
                "BINDING_FIT_AUTHORITY_HASH:" + key)
    # Frozen budget must match the mode declaration points exactly.
    require(authority["learning_rate"] == FROZEN_LEARNING_RATE,
            "BINDING_FIT_AUTHORITY_BUDGET:learning_rate")
    require(authority["max_optimizer_steps"] == FROZEN_MAX_OPTIMIZER_STEPS,
            "BINDING_FIT_AUTHORITY_BUDGET:max_optimizer_steps")
    require(authority["max_wall_seconds"] == FROZEN_MAX_WALL_SECONDS,
            "BINDING_FIT_AUTHORITY_BUDGET:max_wall_seconds")
    require(authority["reservation_usd"] == RESERVATION_USD, "BINDING_FIT_AUTHORITY_RESERVATION")
    return authority


def plan_only(request=None, authority=None):
    if request is not None:
        validate_request(request)
    if authority is not None:
        validate_authority(authority)
    return {"schema": SCHEMA, "status": "PLAN_ONLY_NOT_EXECUTED",
            "experiment": EXPERIMENT, "scope": scope(),
            "reservation_created": False, "provider_calls": 0,
            "boundary": "No provider client, reservation, model import, or output mutation occurred."}


def read_ledger(path=LEDGER_PATH):
    path = Path(path)
    raw = path.read_bytes()
    ledger = budget.validate_state(budget.decoded(raw))
    return {"ledger": ledger, "ledger_sha256": sha256(raw).hexdigest(),
            "ledger_path": str(path.resolve())}


def reservation_plan():
    frozen = RESOURCE_PLAN
    return {"instance_count": frozen["instance_count"],
            "runtime_seconds_max": frozen["instance_seconds_max"],
            "instance_type": frozen["instance_type"], "account_id": frozen["account"],
            "region": frozen["region"], "automatic_retries": frozen["automatic_retries"],
            "on_demand_hourly_usd_max": frozen["on_demand_rate_ceiling_usd"],
            "ancillary_reserved_usd": "1.48",
            "task_scope": "binding_fit_training_check_001",
            "campaign_scope": "cas-meta2-composition-campaign",
            "binding_fit": json.loads(canonical(frozen))}


def validate_reservation_scope(ledger_document, amount=RESERVATION_USD):
    ledger = ledger_document["ledger"]
    amount = budget.amount(amount, positive=True)
    reserved = budget.amount(ledger["total_reserved_usd"])
    unreserved = budget.amount(ledger["remaining_unreserved_usd"])
    cap = budget.amount(ledger["owner_task_cap_usd"])
    require(cap == budget.amount(CAMPAIGN_CAP_USD), "LEDGER_CAP_CHANGED")
    require(reserved + unreserved == cap, "INCONSISTENT_CAMPAIGN_TOTALS")
    require(amount == budget.amount(RESERVATION_USD), "RESERVATION_AMOUNT_FROZEN")
    require(unreserved >= amount and reserved + amount <= cap,
            "RESERVATION_OUTSIDE_CAMPAIGN_BUDGET")
    return {"amount": str(amount), "reserved_before": str(reserved),
            "unreserved_before": str(unreserved), "campaign_cap": str(cap)}


def validate_reserved_transition(before, after, receipt, request):
    prior, current = before["ledger"], after["ledger"]
    require(current["revision"] == prior["revision"] + 1, "RESERVATION_REVISION_MISMATCH")
    require(current["reservations"][:-1] == prior["reservations"], "RESERVATION_NOT_APPEND_ONLY")
    require(current["previous_state_sha256"] == budget.digest(budget.encoded(prior)),
            "RESERVATION_PREDECESSOR_MISMATCH")
    for key in ("approval", "predecessor", "owner_task_cap_usd", "scope", "no_automatic_refund"):
        require(current.get(key) == prior.get(key), "RESERVATION_CONTEXT_CHANGED:" + key)
    entry = current["reservations"][-1]
    for key in ("job", "source_sha", "archive_sha256"):
        require(entry[key] == request[key], "RESERVATION_IDENTITY_MISMATCH:" + key)
    require(entry["status"] == budget.STATUS, "RESERVATION_STATUS_REQUIRED")
    require(entry["plan"] == reservation_plan()
            and entry["plan_sha256"] == budget.digest(budget.encoded(reservation_plan())),
            "RESERVATION_RESOURCE_PLAN_MISMATCH")
    amount = budget.amount(RESERVATION_USD)
    require(budget.amount(entry["reserved_usd"]) == amount, "RESERVATION_AMOUNT_FROZEN")
    require(budget.amount(current["total_reserved_usd"]) == budget.amount(prior["total_reserved_usd"]) + amount
            and budget.amount(current["remaining_unreserved_usd"]) == budget.amount(prior["remaining_unreserved_usd"]) - amount,
            "RESERVATION_TOTAL_DELTA_MISMATCH")
    require(type(receipt) is dict and receipt.get("reservation") == entry,
            "RESERVATION_RECEIPT_ENTRY_MISMATCH")
    require(receipt.get("ledger_sha256") == after["ledger_sha256"], "RESERVATION_RECEIPT_HASH_MISMATCH")
    require(receipt.get("ledger_path") == after["ledger_path"] == before["ledger_path"],
            "RESERVATION_RECEIPT_PATH_MISMATCH")
    for key in ("revision", "total_reserved_usd", "remaining_unreserved_usd"):
        require(receipt.get(key) == current[key], "RESERVATION_RECEIPT_FIELD:" + key)
    return receipt


def validate_preflight(facts):
    frozen = RESOURCE_PLAN
    require(type(facts) is dict, "PREFLIGHT_FACTS_REQUIRED")
    require(facts.get("account") == frozen["account"], "PREFLIGHT_ACCOUNT")
    require(facts.get("region") == frozen["region"], "PREFLIGHT_REGION")
    require(facts.get("ami") == frozen["ami"], "PREFLIGHT_AMI")
    require(facts.get("instance_type") == frozen["instance_type"], "PREFLIGHT_INSTANCE_TYPE")
    require(facts.get("instance_count") == 1, "PREFLIGHT_INSTANCE_COUNT")
    require(facts.get("gpu_name_contains") == frozen["gpu_name_contains"], "PREFLIGHT_GPU_NAME")
    require(facts.get("visible_gpu_count") == 1, "PREFLIGHT_VISIBLE_GPU_COUNT")
    require(facts.get("t4_rejected") is True, "PREFLIGHT_T4")
    require(facts.get("rate_ceiling_usd") == frozen["on_demand_rate_ceiling_usd"],
            "PREFLIGHT_RATE_CEILING")
    require(facts.get("conflicting_resources") in (None, [], {}), "PREFLIGHT_CONFLICTING_RESOURCES")
    return facts


# --------------------------------------------------------------------------- #
# source package builder (exact git objects; never the working tree)
# --------------------------------------------------------------------------- #
def safe_name(name):
    require(type(name) is str and name and "\\" not in name and ":" not in name
            and not any(ord(char) < 32 for char in name)
            and all(part not in ("", ".", "..") and not part.endswith((" ", "."))
                    for part in name.split("/")), "PACKAGE_UNSAFE_MEMBER_PATH")
    return name


def checked_names(names):
    names = [safe_name(name) for name in names]
    folded = {name.casefold() for name in names}
    require(len(names) == len(folded), "PACKAGE_MEMBER_COLLISION")
    require(not any("/".join(name.split("/")[:i]).casefold() in folded
                    for name in names for i in range(1, len(name.split("/")))),
            "PACKAGE_FILE_DIRECTORY_COLLISION")
    return names


def no_links(path):
    path = Path(path).absolute()
    require(".." not in path.parts
            and not any(part.is_symlink() or getattr(part, "is_junction", lambda: False)()
                        for part in (path, *path.parents)), "PACKAGE_PATH_LINK_OR_ESCAPE")
    return path


def file_metadata(path, maximum):
    path = no_links(path)
    metadata = path.stat()
    require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1
            and 0 <= metadata.st_size <= maximum, "PACKAGE_BOUNDED_REGULAR_FILE_REQUIRED")
    return path, metadata


def read_file(path, maximum):
    path, before = file_metadata(path, maximum)
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        require(stat.S_ISREG(opened.st_mode) and opened.st_nlink == 1
                and (opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino)
                and 0 <= opened.st_size <= maximum, "PACKAGE_FILE_CHANGED_BEFORE_READ")
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
    require(len(raw) <= maximum and len(raw) == opened.st_size == after.st_size
            and opened.st_mtime_ns == after.st_mtime_ns and after.st_nlink == 1,
            "PACKAGE_FILE_CHANGED_DURING_READ")
    return raw


def archive_members(raw):
    require(type(raw) is bytes and len(raw) <= MAX_ARCHIVE_BYTES, "PACKAGE_ARCHIVE_BOUND")
    with ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        require(0 < len(infos) <= MAX_MEMBER_COUNT, "PACKAGE_ARCHIVE_MEMBER_COUNT_BOUND")
        checked_names([info.orig_filename for info in infos])
        require(all(info.orig_filename == info.filename for info in infos),
                "PACKAGE_ARCHIVE_NORMALIZED_MEMBER_NAME")
        require(all(not info.is_dir() and stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG)
                    and not info.flag_bits & 1 for info in infos),
                "PACKAGE_ARCHIVE_NONREGULAR_OR_ENCRYPTED_MEMBER")
        require(all(type(info.file_size) is int and 0 <= info.file_size <= MAX_MEMBER_BYTES
                    for info in infos), "PACKAGE_ARCHIVE_MEMBER_SIZE_BOUND")
        require(sum(info.file_size for info in infos) <= MAX_EXPANDED_BYTES,
                "PACKAGE_ARCHIVE_EXPANDED_BOUND")
        members = {}
        for info in infos:
            raw_member = archive.read(info)
            require(len(raw_member) == info.file_size, "PACKAGE_ARCHIVE_MEMBER_SIZE_CHANGED")
            members[info.filename] = raw_member
    return members


def _run_git(args, cwd):
    process = subprocess.run(["git"] + args, cwd=str(cwd), stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=60,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if process.returncode != 0:
        message = process.stderr.decode("utf-8", "replace")[:2000]
        raise ValueError("PACKAGE_GIT_FAILED:" + message)
    return 0, process.stdout


def git_key(path):
    path = safe_name(path)
    require(path.startswith("research/"), "PACKAGE_GIT_MEMBER_SCOPE")
    return GIT_PREFIX + path


def git_bytes(root, commit, path):
    code, raw = _run_git(["-c", "core.autocrlf=false", "show", commit + ":" + git_key(path)], root)
    require(code == 0, "PACKAGE_GIT_SHOW_FAILED:" + path)
    return raw


def git_tree_paths(root, commit, directory):
    code, raw = _run_git(["-c", "core.autocrlf=false", "ls-tree", "-rz", "--full-tree",
                          commit, "--", git_key(directory)], root)
    require(code == 0, "PACKAGE_GIT_LS_TREE_FAILED:" + directory)
    paths = []
    for record in raw.decode("utf-8").split("\0"):
        if not record:
            continue
        metadata, name = record.split("\t", 1)
        mode, kind, _ = metadata.split(" ", 2)
        require(mode in ("100644", "100755") and kind == "blob", "PACKAGE_GIT_REGULAR_FILE_REQUIRED")
        require(name.startswith(GIT_PREFIX + directory + "/"), "PACKAGE_GIT_TREE_SCOPE")
        paths.append(name.removeprefix(GIT_PREFIX))
    require(paths, "PACKAGE_GIT_SOURCE_DIRECTORY_EMPTY:" + directory)
    return checked_names(paths)


def render_worker():
    """Render the self-contained in-package worker script (deterministic text)."""
    inner_lines = [
        "import hashlib",
        "import json",
        "import sys",
        "from pathlib import Path",
        "ROOT = Path(sys.argv[1])",
        "sys.path.insert(0, str(ROOT / 'research/CAS_META_2_COMPOSITION'))",
        "from cas_meta2.binding_fit_training import mode",
        "config = json.loads((ROOT / 'config.json').read_bytes())",
        "job = config['job']",
        ("report = mode.launch(run_id=job, max_optimizer_steps=%d, "
         "max_wall_seconds=%.1f, learning_rate=%r)"
         % (FROZEN_MAX_OPTIMIZER_STEPS, FROZEN_MAX_WALL_SECONDS, FROZEN_LEARNING_RATE)),
        "raw = (json.dumps(report, sort_keys=True, indent=2) + '\\n').encode('utf-8')",
        "results = ROOT / 'results'",
        "results.mkdir(exist_ok=True)",
        "(results / 'result.json').write_bytes(raw)",
        "(results / 'result.json.sha256').write_text(hashlib.sha256(raw).hexdigest() + '\\n')",
    ]
    runner_block = ",\n".join(repr(line) for line in inner_lines)
    lines = [
        "#!/usr/bin/env python3",
        '"""Binding-fit training worker for the teaching campaign. One run, no restart.',
        "",
        "Rendered into the source package by aws/binding_fit_launch.render_worker().",
        "Reads job/bucket/region from config.json, creates (or discovers) the isolated",
        "task venv, installs torch==2.11.0 from the cu128 index and the two frozen",
        "wheels with --no-deps, runs the real cas_meta2.binding_fit_training.mode.launch,",
        "writes results/result.json plus a sha256 sidecar, and uploads both to the job",
        "bucket. Evidence is written on failure too.",
        '"""',
        "import hashlib",
        "import json",
        "import shutil",
        "import subprocess",
        "from pathlib import Path",
        "",
        "MAX_OPTIMIZER_STEPS = %d" % FROZEN_MAX_OPTIMIZER_STEPS,
        "MAX_WALL_SECONDS = %.1f" % FROZEN_MAX_WALL_SECONDS,
        "LEARNING_RATE = %r" % FROZEN_LEARNING_RATE,
        "TORCH_INDEX = 'https://download.pytorch.org/whl/cu128'",
        "PILOT = 'research/CAS_META_2_COMPOSITION'",
        "WHEEL_DIR = %r" % WORKER_WHEEL_DIR,
        "WHEEL_NAMES = (",
        "    'casformer_reference-0.1.0-py3-none-any.whl',",
        "    'cas_neural_cjt-0.2.0-py3-none-any.whl',",
        ")",
        "REQUIREMENTS = %r" % WORKER_REQUIREMENTS,
        "",
        "INNER_RUNNER = \"\\n\".join((",
        "    " + runner_block,
        "))",
        "",
        "def run_checked(argv):",
        "    subprocess.run(argv, check=True)",
        "",
        "def main():",
        "    root = Path(__file__).resolve().parent",
        "    config = json.loads((root / 'config.json').read_bytes())",
        "    job = config['job']",
        "    bucket = config['bucket']",
        "    region = config['region']",
        "    results = root / 'results'",
        "    results.mkdir(exist_ok=True)",
        "    try:",
        "        venv = root / 'venv'",
        "        venv_py = venv / 'bin' / 'python'",
        "        if not venv_py.exists():",
        "            base = next((c for c in ('python3.12', 'python3.11', 'python3')",
        "                         if shutil.which(c)), None)",
        "            if base is None:",
        "                raise SystemExit('SUPPORTED_PYTHON_REQUIRED')",
        "            run_checked([base, '-m', 'venv', str(venv)])",
        "        python = str(venv_py)",
        "        run_checked([python, '-m', 'pip', 'install', '--disable-pip-version-check',",
        "                     'torch==2.11.0', '--index-url', TORCH_INDEX])",
        "        wheels = [str(root / WHEEL_DIR / name) for name in WHEEL_NAMES]",
        "        run_checked([python, '-m', 'pip', 'install', '--disable-pip-version-check',",
        "                     '--no-deps', *wheels])",
        "        run_checked([python, '-m', 'pip', 'install', '--disable-pip-version-check',",
        "                     '-r', str(root / REQUIREMENTS)])",
        "        runner = root / '_inner_runner.py'",
        "        runner.write_text(INNER_RUNNER)",
        "        run_checked([python, '-B', str(runner), str(root)])",
        "        raw = (results / 'result.json').read_bytes()",
        "        sidecar = (results / 'result.json.sha256').read_text().strip()",
        "        if hashlib.sha256(raw).hexdigest() != sidecar:",
        "            raise SystemExit('RESULT_SHA_MISMATCH')",
        "    except BaseException as error:",
        "        failure = {'type': type(error).__name__, 'message': str(error)[:2000]}",
        "        report = {'schema': 'cas-teaching-binding-fit-training/1',",
        "                  'status': 'REMOTE_WORKER_FAILED', 'failure': failure, 'run_id': job}",
        "        raw = (json.dumps(report, sort_keys=True, indent=2) + '\\n').encode('utf-8')",
        "        (results / 'result.json').write_bytes(raw)",
        "        (results / 'result.json.sha256').write_text(hashlib.sha256(raw).hexdigest() + '\\n')",
        "    import boto3",
        "    s3 = boto3.client('s3', region_name=region)",
        "    s3.put_object(Bucket=bucket, Key='results/result.json',",
        "                  Body=(results / 'result.json').read_bytes())",
        "    s3.put_object(Bucket=bucket, Key='results/result.json.sha256',",
        "                  Body=(results / 'result.json.sha256').read_bytes())",
        "",
        "if __name__ == '__main__':",
        "    main()",
        "",
    ]
    return "\n".join(lines)


def resolve_members(root, commit, *, git_bytes_fn=git_bytes, git_paths_fn=git_tree_paths):
    require(type(commit) is str and bool(HEX40.fullmatch(commit)), "PACKAGE_EXACT_COMMIT_REQUIRED")
    names = set(EXPLICIT_FILES)
    for directory in SOURCE_DIRS:
        names.update(git_paths_fn(root, commit, directory))
    names.update(WHEELS)
    names.add(WORKER_NAME)
    checked_names(names)
    members = {}
    for name in sorted(names):
        if name == WORKER_NAME:
            raw = render_worker().encode("utf-8")
        else:
            raw = git_bytes_fn(root, commit, name)
        require(len(raw) <= MAX_MEMBER_BYTES, "PACKAGE_MEMBER_TOO_LARGE:" + name)
        members[name] = raw
    require(members, "PACKAGE_EMPTY_MEMBERS")
    require(len(members) <= MAX_MEMBER_COUNT, "PACKAGE_MEMBER_COUNT_BOUND")
    require(sum(map(len, members.values())) <= MAX_EXPANDED_BYTES, "PACKAGE_EXPANDED_BOUND")
    for name, expected in WHEELS.items():
        require(name in members and digest(members[name]) == expected,
                "PACKAGE_FROZEN_WHEEL_CHANGED:" + name)
    return members


def manifest_for(members, source_sha):
    return {
        "schema": PACKAGE_SCHEMA,
        "source_sha": source_sha,
        "root_manifest": MANIFEST_NAME,
        "experiment": EXPERIMENT,
        "git_path_prefix": GIT_PREFIX,
        "worker_script": WORKER_NAME,
        "wheels": {name: {"sha256": expected, "bytes": len(members[name])}
                   for name, expected in WHEELS.items()},
        "members": sorted(members),
        "files_sha256": {name: digest(raw) for name, raw in sorted(members.items())},
        "files_bytes": {name: len(raw) for name, raw in sorted(members.items())},
        "member_count": len(members) + 1,
        "expanded_bytes": sum(map(len, members.values())),
        "launch_enabled": False,
        "training": True,
        "native_execution": False,
        "reservation_created": False,
        "automatic_retries": 0,
        "frozen_budget": {
            "max_optimizer_steps": FROZEN_MAX_OPTIMIZER_STEPS,
            "max_wall_seconds": FROZEN_MAX_WALL_SECONDS,
            "learning_rate": FROZEN_LEARNING_RATE,
            "reservation_usd": RESERVATION_USD,
        },
        "boundary": ("Source package only; launch_enabled:false. The paid run requires a "
                     "separately hash-bound launch request and owner authorization for this "
                     "exact manifest. No final evaluation target is read; the training answer "
                     "supplies the correction."),
    }


def validate_members(members, *, source_sha, manifest_sha256):
    require(type(members) is dict and members, "PACKAGE_MEMBERS_REQUIRED")
    require(len(members) <= MAX_MEMBER_COUNT
            and all(type(raw) is bytes and len(raw) <= MAX_MEMBER_BYTES for raw in members.values())
            and sum(map(len, members.values())) <= MAX_EXPANDED_BYTES, "PACKAGE_MEMBERS_BOUND")
    checked_names(members)
    raw = members.get(MANIFEST_NAME, b"")
    require(digest(raw) == manifest_sha256, "PACKAGE_ROOT_MANIFEST_HASH")
    document = json.loads(raw.decode("utf-8"))
    require(type(document.get("source_sha")) is str and bool(HEX40.fullmatch(document["source_sha"])),
            "PACKAGE_MANIFEST_SOURCE_SHA")
    require(document["source_sha"] == source_sha, "PACKAGE_SOURCE_SHA_MISMATCH")
    content = {name: value for name, value in members.items() if name != MANIFEST_NAME}
    require(set(EXPLICIT_FILES).issubset(content), "PACKAGE_EXPLICIT_MEMBER_MISSING")
    require(WORKER_NAME in content, "PACKAGE_WORKER_MISSING")
    require(document == manifest_for(content, source_sha), "PACKAGE_SOURCE_CLOSURE_CHANGED")
    return document


def build_package(output, *, source_sha, git_bytes_fn=git_bytes, git_paths_fn=git_tree_paths):
    output = Path(output).absolute()
    require(not output.exists() and output.parent.is_dir()
            and output.is_relative_to((ROOT / "records").absolute())
            and output != ROOT / "records", "PACKAGE_NEW_SCOPED_OUTPUT_REQUIRED")
    members = resolve_members(ROOT, source_sha, git_bytes_fn=git_bytes_fn,
                              git_paths_fn=git_paths_fn)
    manifest = manifest_for(members, source_sha)
    members[MANIFEST_NAME] = canonical(manifest)
    require(sum(map(len, members.values())) <= MAX_EXPANDED_BYTES, "PACKAGE_EXPANDED_BOUND")
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED, compresslevel=6) as zipped:
        for name in sorted(members):
            info = ZipInfo(name, date_time=(2026, 9, 8, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zipped.writestr(info, members[name])
    raw = buffer.getvalue()
    require(len(raw) <= MAX_ARCHIVE_BYTES, "PACKAGE_ARCHIVE_BOUND")
    readback = archive_members(raw)
    require(readback == members, "PACKAGE_ARCHIVE_READBACK")
    validate_members(members, source_sha=source_sha, manifest_sha256=digest(members[MANIFEST_NAME]))
    output.mkdir()
    with (output / "source.zip").open("xb") as stream:
        stream.write(raw)
    receipt = {"schema": "cas-teaching-binding-fit-package-receipt/1",
               "status": "SOURCE_ONLY_NO_LAUNCH",
               "archive": str(output / "source.zip"),
               "archive_sha256": digest(raw), "archive_bytes": len(raw),
               "source_sha": source_sha,
               "manifest_sha256": digest(members[MANIFEST_NAME]),
               "member_count": len(members), "manifest": manifest}
    with (output / "receipt.json").open("xb") as stream:
        stream.write(canonical(receipt))
    return receipt


def inspect_archive(path, *, expected_sha256, expected_source_sha, expected_manifest_sha256):
    raw = read_file(path, MAX_ARCHIVE_BYTES)
    require(digest(raw) == expected_sha256, "PACKAGE_ARCHIVE_HASH")
    members = archive_members(raw)
    return validate_members(members, source_sha=expected_source_sha,
                            manifest_sha256=expected_manifest_sha256)


# --------------------------------------------------------------------------- #
# AWS provider (boto3 imported lazily, only inside build())
# --------------------------------------------------------------------------- #
class _DefaultClientError(Exception):
    def __init__(self, code, message=""):
        super().__init__(message or code)
        self.response = {"Error": {"Code": code, "Message": message}}


def _import_boto3():
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
    return boto3, Config, ClientError


def _resolve_identity(arguments, *, job, source_sha, archive_sha256, manifest_sha256):
    provided = (job, source_sha, archive_sha256, manifest_sha256)
    if all(value is not None for value in provided):
        require(type(job) is str and re.fullmatch(JOB_PATTERN, job) is not None,
                "BINDING_FIT_JOB")
        require(type(source_sha) is str and bool(HEX40.fullmatch(source_sha)),
                "BINDING_FIT_SOURCE_SHA")
        require(type(archive_sha256) is str and bool(HEX64.fullmatch(archive_sha256)),
                "BINDING_FIT_ARCHIVE_SHA")
        require(type(manifest_sha256) is str and bool(HEX64.fullmatch(manifest_sha256)),
                "BINDING_FIT_MANIFEST_SHA")
        return {"job": job, "source_sha": source_sha, "archive_sha256": archive_sha256,
                "manifest_sha256": manifest_sha256}
    require(all(value is None for value in provided), "BINDING_FIT_PARTIAL_IDENTITY_INJECTION")
    require(getattr(arguments, "request", None) and getattr(arguments, "request_sha256", None),
            "BINDING_FIT_REQUEST_INPUTS_REQUIRED")
    raw = Path(arguments.request).read_bytes()
    require(digest(raw) == arguments.request_sha256, "BINDING_FIT_REQUEST_HASH_MISMATCH")
    request = validate_request(json.loads(raw))
    return {"job": request["job"], "source_sha": request["source_sha"],
            "archive_sha256": request["archive_sha256"],
            "manifest_sha256": request["manifest_sha256"]}


def _locate_source_archive(archive_sha256):
    require(type(archive_sha256) is str and bool(HEX64.fullmatch(archive_sha256)),
            "BINDING_FIT_ARCHIVE_SHA")
    for receipt in sorted((ROOT / "records").rglob("receipt.json")):
        try:
            document = json.loads(receipt.read_bytes())
        except (OSError, ValueError):
            continue
        if document.get("archive_sha256") == archive_sha256 and document.get("archive"):
            archive = Path(document["archive"])
            if archive.is_file():
                return archive
    raise ValueError("BINDING_FIT_SOURCE_ARCHIVE_NOT_FOUND")


def build(arguments, boto3_module=None, *, job=None, source_sha=None, archive_sha256=None,
          manifest_sha256=None, ledger_path=None, clients=None, source_archive=None,
          client_error=None):
    profile = getattr(arguments, "profile", "default")
    identity = _resolve_identity(arguments, job=job, source_sha=source_sha,
                                 archive_sha256=archive_sha256, manifest_sha256=manifest_sha256)
    if clients is None:
        if boto3_module is None:
            boto3_module, Config, client_error = _import_boto3()
        else:
            Config = getattr(boto3_module, "Config", None)
            client_error = getattr(boto3_module, "ClientError", None)
            require(Config is not None and client_error is not None,
                    "BINDING_FIT_INJECTED_SDK_MISSING_BOTOCORE")
        config = Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 0})
        session = boto3_module.Session(profile_name=profile, region_name=RESOURCE_PLAN["region"])
        clients = {name: session.client(name, config=config)
                   for name in ("sts", "ec2", "iam", "s3", "scheduler")}
        # The AWS Price List API only serves its bulk endpoint from us-east-1
        # (and ap-south-1); a us-west-2 pricing client gets AccessDenied.
        clients["pricing"] = session.client("pricing", region_name="us-east-1", config=config)
    return BindingFitProvider(job=identity["job"], source_sha=identity["source_sha"],
                              archive_sha256=identity["archive_sha256"],
                              manifest_sha256=identity["manifest_sha256"],
                              ledger_path=ledger_path if ledger_path is not None else LEDGER_PATH,
                              clients=clients, source_archive=source_archive,
                              client_error=client_error)


class BindingFitProvider:
    """Injected provider implementing the binding-fit launch lifecycle."""

    def __init__(self, *, job, source_sha, archive_sha256, manifest_sha256,
                 ledger_path, clients, source_archive=None, client_error=None,
                 budget_module=budget):
        self.job = job
        self.source_sha = source_sha
        self.archive_sha256 = archive_sha256
        self.manifest_sha256 = manifest_sha256
        self.ledger_path = ledger_path
        self.region = RESOURCE_PLAN["region"]
        self.clients = clients
        self.source_archive = source_archive
        self.budget = budget_module
        self._client_error = client_error or _DefaultClientError
        self.calls = []
        self._reserved = False
        self._launch_called = False
        self._instance_id = None
        self._instance_ids = []
        self._resources = {}
        self._evidence = None
        self._result = None
        self._result_raw = None

    def configure_evidence(self, directory):
        directory = evidence_directory(directory)
        require(directory.is_dir() and self._evidence is None, "BINDING_FIT_FRESH_EVIDENCE_REQUIRED")
        self._evidence = directory

    def _event(self, operation, state, **details):
        require(self._evidence is not None, "BINDING_FIT_EVIDENCE_REQUIRED")
        number = len([p for p in self._evidence.iterdir() if p.name.startswith("provider_")]) + 1
        return write_evidence(self._evidence / ("provider_%04d.json" % number),
                              canonical({"schema": "cas-teaching-binding-fit-provider/1",
                                         "job": self.job, "operation": operation,
                                         "state": state, **details}))

    def _effect(self, operation, callback, **arguments):
        self._event(operation, "REQUESTED")
        try:
            result = callback(**arguments)
        except BaseException as error:
            self._event(operation, "FAILED", error=type(error).__name__ + ":" + str(error)[:2000])
            raise
        self._event(operation, "RETURNED",
                    request_id=result.get("ResponseMetadata", {}).get("RequestId"))
        return result

    @staticmethod
    def _error_code(error):
        return getattr(error, "response", {}).get("Error", {}).get("Code")

    def preflight(self):
        self.calls.append("preflight")
        frozen = RESOURCE_PLAN
        ec2, sts, pricing = (self.clients[name] for name in ("ec2", "sts", "pricing"))

        identity = sts.get_caller_identity()
        require(type(identity.get("Account")) is str and identity["Account"] == frozen["account"],
                "BINDING_FIT_PREFLIGHT_ACCOUNT")
        require(self.region == frozen["region"], "BINDING_FIT_PREFLIGHT_REGION")

        images = ec2.describe_images(ImageIds=[frozen["ami"]]).get("Images", [])
        require(len(images) == 1 and images[0].get("State") == "available",
                "BINDING_FIT_PREFLIGHT_AMI")

        descriptions = ec2.describe_instance_types(
            InstanceTypes=[frozen["instance_type"]]).get("InstanceTypes", [])
        require(len(descriptions) == 1
                and descriptions[0].get("InstanceType") == frozen["instance_type"],
                "BINDING_FIT_PREFLIGHT_INSTANCE_TYPE")
        gpus = descriptions[0].get("GpuInfo", {}).get("Gpus", [])
        require(len(gpus) == 1, "BINDING_FIT_PREFLIGHT_GPU_COUNT")
        gpu_name = gpus[0].get("Name", "")
        require(re.search(r"t4", gpu_name, re.IGNORECASE) is None, "BINDING_FIT_PREFLIGHT_T4")
        require(frozen["gpu_name_contains"] in gpu_name, "BINDING_FIT_PREFLIGHT_GPU_NAME")
        visible_gpu_count = sum(gpu.get("Count", 1) for gpu in gpus)
        require(visible_gpu_count == frozen["visible_gpu_count"],
                "BINDING_FIT_PREFLIGHT_VISIBLE_GPU_COUNT")

        offerings = ec2.describe_instance_type_offerings(LocationType="region", Filters=[
            {"Name": "instance-type", "Values": [frozen["instance_type"]]}]
        ).get("InstanceTypeOfferings", [])
        require(len(offerings) >= 1, "BINDING_FIT_PREFLIGHT_OFFERINGS")

        fields = {"instanceType": frozen["instance_type"], "location": "US West (Oregon)",
                  "operatingSystem": "Linux", "tenancy": "Shared", "preInstalledSw": "NA",
                  "capacitystatus": "Used", "marketoption": "OnDemand",
                  "operation": "RunInstances"}
        price = pricing.get_products(ServiceCode="AmazonEC2", Filters=[
            {"Type": "TERM_MATCH", "Field": key, "Value": value} for key, value in fields.items()])
        require(not price.get("NextToken"), "BINDING_FIT_PREFLIGHT_PAGINATED_PRICE")
        # Minimal rate ceiling: any quoted Hrs dimension must stay under the ceiling.
        rates = [float(dimension["pricePerUnit"]["USD"])
                 for raw in price.get("PriceList", [])
                 for term in json.loads(raw).get("terms", {}).get("OnDemand", {}).values()
                 for dimension in term.get("priceDimensions", {}).values()
                 if dimension.get("unit") == "Hrs"]
        require(all(0 <= rate <= float(frozen["on_demand_rate_ceiling_usd"]) for rate in rates),
                "BINDING_FIT_PREFLIGHT_RATE_CEILING")

        active = ec2.describe_instances(Filters=[
            {"Name": "tag-key", "Values": ["cas_meta_job"]},
            {"Name": "instance-state-name",
             "Values": ["pending", "running", "stopping", "shutting-down"]}])
        require(not active.get("NextToken"), "BINDING_FIT_PREFLIGHT_PAGINATED_CONFLICTS")
        conflicting = [instance.get("InstanceId")
                       for reservation in active.get("Reservations", [])
                       for instance in reservation.get("Instances", [])]
        require(not conflicting, "BINDING_FIT_PREFLIGHT_CONFLICTING_RESOURCES")

        return {"account": identity["Account"], "region": self.region, "ami": frozen["ami"],
                "instance_type": frozen["instance_type"], "instance_count": 1,
                "gpu_name_contains": frozen["gpu_name_contains"],
                "visible_gpu_count": visible_gpu_count, "t4_rejected": True,
                "rate_ceiling_usd": frozen["on_demand_rate_ceiling_usd"],
                "conflicting_resources": []}

    def reserve(self, amount):
        self.calls.append("reserve")
        self._event("budget_reservation", "REQUESTED", amount=amount)
        require(not self._reserved, "BINDING_FIT_RESERVATION_ALREADY_ATTEMPTED")
        require(type(amount) is str and amount == RESERVATION_USD,
                "BINDING_FIT_RESERVATION_AMOUNT_FROZEN")
        receipt = self.budget.reserve_budget(self.job, self.source_sha, self.archive_sha256,
                                             amount, reservation_plan(), self.ledger_path)
        self._reserved = True
        return {**receipt, "aws_side_reservation": self._record_aws_side_reservation(receipt)}

    def _bucket_name(self):
        return self.job + "-" + RESOURCE_PLAN["account"]

    def _ensure_bucket(self, s3, tags=None):
        tags = tags or [{"Key": "cas_meta_job", "Value": self.job}]
        bucket = self._bucket_name()
        if "bucket" in self._resources:
            return bucket
        self._effect("create_bucket", s3.create_bucket, Bucket=bucket,
                     CreateBucketConfiguration={"LocationConstraint": self.region})
        s3.put_bucket_tagging(Bucket=bucket, Tagging={"TagSet": tags})
        s3.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration={
            "BlockPublicAcls": True, "IgnorePublicAcls": True,
            "BlockPublicPolicy": True, "RestrictPublicBuckets": True})
        self._resources["bucket"] = bucket
        return bucket

    def _record_aws_side_reservation(self, receipt):
        s3 = self.clients.get("s3")
        if s3 is None:
            return {"status": "NOT_RECORDED", "reason": "NO_S3_CLIENT"}
        bucket = self._bucket_name()
        try:
            self._ensure_bucket(s3)
            s3.put_object(Bucket=bucket, Key="reservation/reservation_receipt.json",
                          Body=canonical(receipt))
            snapshot = budget.validate_state(budget.decoded(Path(self.ledger_path).read_bytes()))
            s3.put_object(Bucket=bucket, Key="reservation/ledger_snapshot.json",
                          Body=canonical(snapshot))
            return {"status": "RECORDED", "bucket": bucket,
                    "key": "reservation/reservation_receipt.json"}
        except Exception as error:  # noqa: BLE001 - report, never refund/retry
            return {"status": "FAILED", "bucket": bucket,
                    "failure": type(error).__name__ + ":" + str(error)[:2000]}

    def _validate_permit(self, permit):
        require(type(permit) is dict, "BINDING_FIT_PERMIT_REQUIRED")
        require(permit.get("job") == self.job and permit.get("source_sha") == self.source_sha
                and permit.get("archive_sha256") == self.archive_sha256
                and permit.get("manifest_sha256") == self.manifest_sha256,
                "BINDING_FIT_PERMIT_IDENTITY_MISMATCH")
        reservation = permit.get("reservation")
        require(type(reservation) is dict
                and reservation.get("reservation", {}).get("job") == self.job
                and reservation.get("reservation", {}).get("status") == budget.STATUS,
                "BINDING_FIT_PERMIT_RESERVATION_MISMATCH")
        require(permit.get("resource_plan") == scope(), "BINDING_FIT_PERMIT_RESOURCE_PLAN_MISMATCH")
        validate_preflight(permit.get("preflight"))

    def _source_bytes(self):
        if self.source_archive is None:
            raw = _locate_source_archive(self.archive_sha256).read_bytes()
        elif isinstance(self.source_archive, (bytes, bytearray, memoryview)):
            raw = bytes(self.source_archive)
        else:
            raw = Path(self.source_archive).read_bytes()
        require(digest(raw) == self.archive_sha256, "BINDING_FIT_SOURCE_ARCHIVE_HASH_MISMATCH")
        return raw

    def _user_data(self, bucket):
        text = "\n".join([
            "#!/bin/bash", "set -eu", "umask 077",
            "export PYTHONDONTWRITEBYTECODE=1 AWS_MAX_ATTEMPTS=1 AWS_PAGER=''",
            "mkdir -p /opt/cas-binding-fit/package",
            "exec > /opt/cas-binding-fit/bootstrap.log 2>&1",
            "command -v aws >/dev/null || { echo AWS_CLI_REQUIRED; exit 1; }",
            "timeout 120 aws s3api get-object --bucket " + bucket
            + " --key input/source.zip /opt/cas-binding-fit/package/source.zip --region "
            + self.region,
            "echo '" + self.archive_sha256 + "  /opt/cas-binding-fit/package/source.zip' | sha256sum -c -",
            "cd /opt/cas-binding-fit/package",
            "unzip -q source.zip",
            "timeout 120 aws s3api get-object --bucket " + bucket
            + " --key input/config.json /opt/cas-binding-fit/package/config.json --region "
            + self.region,
            "PY=''",
            "for p in python3.12 python3.11 python3; do",
            "  if command -v \"$p\" >/dev/null 2>&1; then PY=\"$p\"; break; fi",
            "done",
            "test -n \"$PY\" || { echo SUPPORTED_PYTHON_REQUIRED; exit 1; }",
            "\"$PY\" -B /opt/cas-binding-fit/package/" + WORKER_NAME,
            "",
        ])
        require(len(text.encode("utf-8")) <= 16384, "BINDING_FIT_USER_DATA_BOUND")
        return text

    def _default_network(self, ec2):
        vpcs = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}]
                                 ).get("Vpcs", [])
        require(len(vpcs) == 1, "BINDING_FIT_DEFAULT_VPC_REQUIRED")
        vpc_id = vpcs[0]["VpcId"]
        subnets = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]},
                                                {"Name": "default-for-az", "Values": ["true"]}]
                                       ).get("Subnets", [])
        require(subnets, "BINDING_FIT_DEFAULT_SUBNET_REQUIRED")
        return vpc_id, subnets[0]["SubnetId"]

    def launch(self, job, permit):
        self.calls.append("launch")
        require(job == self.job, "BINDING_FIT_LAUNCH_JOB_MISMATCH")
        require(self._reserved, "BINDING_FIT_LAUNCH_REQUIRES_RESERVATION")
        require(not self._launch_called, "BINDING_FIT_SINGLE_LAUNCH_ONLY")
        self._validate_permit(permit)
        self._launch_called = True
        frozen = RESOURCE_PLAN
        ec2, s3, iam = (self.clients[name] for name in ("ec2", "s3", "iam"))
        bucket = self._bucket_name()
        tags = [{"Key": "cas_meta_job", "Value": self.job}]
        worker_role = self.job + "-worker"

        raw = self._source_bytes()
        require(0 < len(raw) <= MAX_ARCHIVE_BYTES, "BINDING_FIT_SOURCE_ARCHIVE_BOUND")
        write_evidence(self._evidence / "source.zip", raw)

        self._ensure_bucket(s3, tags)
        self._effect("upload_source", s3.put_object, Bucket=bucket, Key="input/source.zip", Body=raw)
        config = {"schema": "cas-teaching-binding-fit-worker-config/1", "job": self.job,
                  "bucket": bucket, "region": self.region}
        self._effect("upload_config", s3.put_object, Bucket=bucket, Key="input/config.json",
                     Body=canonical(config))

        def create_role(name, service, statements):
            trust = {"Version": "2012-10-17", "Statement": [
                {"Effect": "Allow", "Principal": {"Service": service}, "Action": "sts:AssumeRole"}]}
            response = self._effect("create_role", iam.create_role, RoleName=name,
                                    AssumeRolePolicyDocument=json.dumps(trust), Tags=tags)
            arn = response.get("Role", {}).get("Arn")
            require(arn == "arn:aws:iam::" + frozen["account"] + ":role/" + name,
                    "BINDING_FIT_ROLE_ARN")
            self._effect("put_role_policy", iam.put_role_policy, RoleName=name, PolicyName="job-only",
                         PolicyDocument=json.dumps({"Version": "2012-10-17",
                                                    "Statement": statements}))
            return arn

        worker_arn = create_role(worker_role, "ec2.amazonaws.com", [
            {"Effect": "Allow", "Action": ["s3:GetObject"],
             "Resource": ["arn:aws:s3:::" + bucket + "/input/*"]},
            {"Effect": "Allow", "Action": ["s3:PutObject"],
             "Resource": ["arn:aws:s3:::" + bucket + "/results/*"]}])
        self._resources["instance_profile"] = worker_role
        profile = self._effect("create_instance_profile", iam.create_instance_profile,
                               InstanceProfileName=worker_role, Tags=tags)["InstanceProfile"]
        profile_arn = profile.get("Arn")
        require(profile_arn == "arn:aws:iam::" + frozen["account"]
                + ":instance-profile/" + worker_role, "BINDING_FIT_PROFILE_ARN")
        self._effect("add_role_to_instance_profile", iam.add_role_to_instance_profile,
                     InstanceProfileName=worker_role, RoleName=worker_role)

        _, subnet_id = self._default_network(ec2)
        group = self._effect("create_security_group", ec2.create_security_group, GroupName=self.job,
                             Description="CAS binding-fit outbound HTTPS only",
                             VpcId=ec2.describe_vpcs(Filters=[
                                 {"Name": "isDefault", "Values": ["true"]}]
                             )["Vpcs"][0]["VpcId"],
                             TagSpecifications=[{"ResourceType": "security-group", "Tags": tags}])
        sg = group["GroupId"]
        self._resources["security_group"] = sg
        self._effect("revoke_security_group_egress", ec2.revoke_security_group_egress, GroupId=sg,
                     IpPermissions=[{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        self._effect("authorize_security_group_egress", ec2.authorize_security_group_egress,
                     GroupId=sg, IpPermissions=[{"IpProtocol": "tcp", "FromPort": 443,
                                                 "ToPort": 443,
                                                 "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])

        bootstrap = self._user_data(bucket)
        launched = self._effect("run_instances", ec2.run_instances,
            ImageId=frozen["ami"], InstanceType=frozen["instance_type"],
            MinCount=1, MaxCount=1, ClientToken=self.job,
            IamInstanceProfile={"Arn": profile_arn},
            InstanceInitiatedShutdownBehavior="terminate",
            MetadataOptions={"HttpTokens": "required", "HttpEndpoint": "enabled"},
            NetworkInterfaces=[{"DeviceIndex": 0, "SubnetId": subnet_id, "Groups": [sg],
                                "AssociatePublicIpAddress": True, "DeleteOnTermination": True}],
            BlockDeviceMappings=[{"DeviceName": "/dev/sda1", "Ebs": {
                "VolumeSize": frozen["ebs"]["size_gib"], "VolumeType": "gp3",
                "Iops": frozen["ebs"]["iops"], "Throughput": frozen["ebs"]["throughput_mib_s"],
                "Encrypted": True, "DeleteOnTermination": True}}],
            TagSpecifications=[{"ResourceType": "instance", "Tags": tags},
                               {"ResourceType": "volume", "Tags": tags}],
            UserData=bootstrap)
        require(len(launched.get("Instances", [])) == 1,
                "BINDING_FIT_ONE_INSTANCE_RESPONSE_REQUIRED")
        self._instance_id = launched["Instances"][0]["InstanceId"]
        require(type(self._instance_id) is str and bool(INSTANCE_ID.fullmatch(self._instance_id)),
                "BINDING_FIT_REAL_INSTANCE_ID_REQUIRED")
        self._resources["instance"] = self._instance_id
        self._instance_ids = [self._instance_id]
        self._event("instance_identity", "OBSERVED", instance_id=self._instance_id,
                    client_token=self.job)
        return {"job": self.job, "instance_id": self._instance_id, "client_token": self.job,
                "imdsv2_required": True, "bucket": bucket, "automatic_retries": 0,
                "identity_note": ("Launch-side receipt records the observed InstanceId and "
                                  "ClientToken=job with IMDSv2 HttpTokens=required.")}

    def _read_body(self, body, maximum):
        total = 0
        blocks = []
        while True:
            block = body.read(min(1024**2, maximum - total + 1))
            if not block:
                break
            total += len(block)
            require(total <= maximum, "BINDING_FIT_S3_BODY_BOUND")
            blocks.append(block)
        return b"".join(blocks)

    def wait(self, job, timeout, *, poll_interval=5.0):
        self.calls.append("wait")
        require(job == self.job, "BINDING_FIT_WAIT_JOB_MISMATCH")
        require(self._instance_id is not None, "BINDING_FIT_WAIT_REQUIRES_LAUNCH")
        require(type(timeout) in (int, float) and 0 < timeout
                <= RESOURCE_PLAN["instance_seconds_max"], "BINDING_FIT_WAIT_TIMEOUT_BOUND")
        ec2, s3 = self.clients["ec2"], self.clients["s3"]
        bucket = self._resources["bucket"]
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                response = s3.get_object(Bucket=bucket, Key="results/result.json")
                raw = self._read_body(response["Body"], 1024**2)
                result = json.loads(raw)
                require(result.get("schema") == "cas-teaching-binding-fit-training/1",
                        "BINDING_FIT_RESULT_IDENTITY")
                self._result = result
                self._result_raw = raw
                status = result.get("status", "REMOTE_FAILED")
                if status == "REMOTE_WORKER_FAILED":
                    return {"worker_status": "REMOTE_FAILED"}
                return {"worker_status": "REMOTE_FINISHED"}
            except self._client_error as error:
                code = self._error_code(error)
                if code not in ("NoSuchKey", "404"):
                    raise
            current = ec2.describe_instances(InstanceIds=[self._instance_id]
                                             )["Reservations"][0]["Instances"][0]
            state = current.get("State", {}).get("Name")
            if state in ("terminated", "shutting-down"):
                return {"worker_status": "REMOTE_FAILED", "instance_state": state}
            time.sleep(poll_interval)
        return {"worker_status": "REMOTE_TIMED_OUT"}

    def collect(self, job):
        self.calls.append("collect")
        require(job == self.job, "BINDING_FIT_COLLECT_JOB_MISMATCH")
        require(self._instance_id is not None, "BINDING_FIT_COLLECT_REQUIRES_LAUNCH")
        s3 = self.clients["s3"]
        bucket = self._resources["bucket"]
        require(self._result_raw is not None, "BINDING_FIT_COLLECT_REQUIRES_RESULT")
        response = s3.get_object(Bucket=bucket, Key="results/result.json.sha256")
        sidecar = self._read_body(response["Body"], 4096).strip()
        require(sidecar.decode("utf-8", "replace") == digest(self._result_raw),
                "BINDING_FIT_RESULT_SHA_MISMATCH")
        result_path = write_evidence(self._evidence / "result.json", self._result_raw)
        sidecar_path = write_evidence(self._evidence / "result.json.sha256", sidecar)
        return {"result": result_path, "sha256": sidecar_path,
                "result_sha256": digest(self._result_raw)}

    def cleanup(self, job):
        self.calls.append("cleanup")
        require(job == self.job, "BINDING_FIT_CLEANUP_JOB_MISMATCH")
        failures = []
        status = {"instance_ids": list(self._instance_ids), "instances": {},
                  "security_group_deleted": True, "schedule_removed": True,
                  "roles_removed": True, "bucket_deleted": True,
                  "results_deleted": False, "complete": False, "failures": failures}
        ec2, s3, iam, scheduler = (self.clients.get(name) for name in
                                   ("ec2", "s3", "iam", "scheduler"))

        def failed(label, error):
            failures.append(label + ":" + type(error).__name__ + ":" + str(error)[:1500])

        # terminate instances (already-absent tolerated)
        for instance_id in self._instance_ids:
            try:
                current = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"][0]["Instances"][0]
                if current.get("State", {}).get("Name") != "terminated":
                    ec2.terminate_instances(InstanceIds=[instance_id])
                status["instances"][instance_id] = "CONFIRMED_TERMINATED"
            except self._client_error as error:
                if self._error_code(error) == "InvalidInstanceID.NotFound":
                    status["instances"][instance_id] = "CONFIRMED_ABSENT"
                else:
                    failed("INSTANCE_TERMINATION_FAILED", error)
                    status["instances"][instance_id] = "UNKNOWN"
            except Exception as error:
                failed("INSTANCE_TERMINATION_FAILED", error)
                status["instances"][instance_id] = "UNKNOWN"

        # security group deletion (already-absent tolerated)
        try:
            groups = ec2.describe_security_groups(Filters=[{"Name": "group-name",
                                                            "Values": [self.job]}])
            require(not groups.get("NextToken"), "SECURITY_GROUP_OBSERVATION_TRUNCATED")
            for candidate in groups.get("SecurityGroups", []):
                ec2.delete_security_group(GroupId=candidate["GroupId"])
        except self._client_error as error:
            if self._error_code(error) not in ("InvalidGroup.NotFound", "InvalidSecurityGroupID.NotFound"):
                failed("SECURITY_GROUP_DELETION_FAILED", error)
                status["security_group_deleted"] = False
        except Exception as error:
            failed("SECURITY_GROUP_DELETION_FAILED", error)
            status["security_group_deleted"] = False

        # schedule removal (already-absent tolerated)
        try:
            scheduler.get_schedule(Name=self.job)
            scheduler.delete_schedule(Name=self.job)
        except self._client_error as error:
            if self._error_code(error) != "ResourceNotFoundException":
                failed("SCHEDULE_REMOVAL_FAILED", error)
                status["schedule_removed"] = False
        except Exception as error:
            failed("SCHEDULE_REMOVAL_FAILED", error)
            status["schedule_removed"] = False

        # roles + instance profile removal (already-absent tolerated)
        profile_name = self.job + "-worker"
        for role_name in (profile_name, self.job + "-timer"):
            try:
                iam.get_role(RoleName=role_name)
                iam.delete_role(RoleName=role_name)
            except self._client_error as error:
                if self._error_code(error) != "NoSuchEntity":
                    failed("ROLE_REMOVAL_FAILED", error)
                    status["roles_removed"] = False
            except Exception as error:
                failed("ROLE_REMOVAL_FAILED", error)
                status["roles_removed"] = False
        try:
            iam.get_instance_profile(InstanceProfileName=profile_name)
            iam.delete_instance_profile(InstanceProfileName=profile_name)
        except self._client_error as error:
            if self._error_code(error) != "NoSuchEntity":
                failed("INSTANCE_PROFILE_REMOVAL_FAILED", error)
                status["roles_removed"] = False
        except Exception as error:
            failed("INSTANCE_PROFILE_REMOVAL_FAILED", error)
            status["roles_removed"] = False

        # delete objects (incl. results/*), then the bucket (already-absent tolerated)
        bucket = self._resources.get("bucket")
        if bucket is None:
            status["bucket_deleted"] = True
        else:
            try:
                listing = s3.list_objects_v2(Bucket=bucket)
                keys = [item["Key"] for item in listing.get("Contents", [])]
                if keys:
                    deleted = s3.delete_objects(Bucket=bucket, Delete={"Objects": [
                        {"Key": key} for key in keys]})
                    require(not deleted.get("Errors"), "S3_PARTIAL_DELETION_FAILED")
                status["results_deleted"] = any(key.startswith("results/") for key in keys)
                s3.delete_bucket(Bucket=bucket)
            except self._client_error as error:
                if self._error_code(error) not in ("NoSuchBucket", "404"):
                    failed("EVIDENCE_CLEANUP_FAILED", error)
                    status["bucket_deleted"] = False
            except Exception as error:
                failed("EVIDENCE_CLEANUP_FAILED", error)
                status["bucket_deleted"] = False

        status["complete"] = not failures
        return status


# --------------------------------------------------------------------------- #
# launch lifecycle (plan-only by default; evidence on every exit)
# --------------------------------------------------------------------------- #
def execute(request, authority, provider, *, ledger_path=LEDGER_PATH, receipt_dir=None):
    validate_request(request)
    validate_authority(authority)
    require(authority["owner_authorization_sha256"] == digest(OWNER_AUTHORIZATION_PATH.read_bytes()),
            "OWNER_AUTHORIZATION_RECORD_MISMATCH")
    require(authority["job"] == request["job"], "REQUEST_AUTHORITY_JOB_MISMATCH")
    require(authority["source_sha"] == request["source_sha"], "REQUEST_AUTHORITY_SOURCE_MISMATCH")
    for key in ("archive_sha256", "manifest_sha256"):
        require(authority[key] == request[key], "REQUEST_AUTHORITY_HASH_MISMATCH:" + key)
    require(provider is not None, "PROVIDER_ADAPTER_REQUIRED")
    started = time.monotonic()
    ledger_before = read_ledger(ledger_path)
    reservation_scope = validate_reservation_scope(ledger_before)
    require(not any(entry["job"] == request["job"] for entry in
                    ledger_before["ledger"]["reservations"]),
            "JOB_ALREADY_RESERVED_NO_AUTOMATIC_RETRY")
    directory = prepare_evidence(receipt_dir if receipt_dir is not None else
        Path(ledger_path).parent / ("binding_fit_" + request["job"]))
    write_evidence(directory / "intent.json", canonical({
        "schema": SCHEMA, "request": request, "authority": authority,
        "ledger_before": ledger_before, "automatic_retries": 0}))
    provider.configure_evidence(directory)
    try:
        preflight = validate_preflight(provider.preflight())
    except BaseException as error:
        write_evidence(directory / "failure.json", canonical({"stage": "preflight",
            "exception_type": type(error).__name__, "exception": str(error)[:2000]}))
        raise
    write_evidence(directory / "preflight.json", canonical(preflight))
    reservation, ledger_after, launched, collected = None, None, None, None
    reservation_valid, reservation_error = False, None
    try:
        reservation = provider.reserve(RESERVATION_USD)
        ledger_after = read_ledger(ledger_path)
        validate_reserved_transition(ledger_before, ledger_after, reservation, request)
        require(reservation.get("aws_side_reservation", {}).get("status") == "RECORDED",
                "AWS_RESERVATION_RECORD_REQUIRED")
        write_evidence(directory / "reservation.json", canonical(reservation))
        reservation_valid = True
        permit = {"job": request["job"], "source_sha": request["source_sha"],
                  "archive_sha256": request["archive_sha256"],
                  "manifest_sha256": request["manifest_sha256"],
                  "reservation": reservation, "preflight": preflight,
                  "resource_plan": scope()}
        launched = provider.launch(request["job"], permit)
        write_evidence(directory / "launch.json", canonical(launched))
        outcome = provider.wait(request["job"], timeout=RESOURCE_PLAN["instance_seconds_max"])
        collected = provider.collect(request["job"])
        status = ("AWS_BINDING_FIT_FINISHED" if outcome.get("worker_status") == "REMOTE_FINISHED"
                  else "AWS_BINDING_FIT_FAILED")
    except BaseException as error:
        status = "AWS_BINDING_FIT_LAUNCH_FAILED"
        outcome = {"exception_type": type(error).__name__, "exception": str(error)[:2000]}
        if not reservation_valid:
            reservation_error = error
        try:
            write_evidence(directory / "failure.json", canonical(outcome))
        except Exception as record_error:
            outcome["failure_record_error"] = type(record_error).__name__ + ":" + str(record_error)[:1000]
    finally:
        try:
            cleanup = provider.cleanup(request["job"])
        except BaseException as error:
            cleanup = {"complete": False, "failures": [
                "CLEANUP_EXCEPTION:" + type(error).__name__ + ":" + str(error)[:2000]]}
    result = {"schema": SCHEMA, "status": status, "job": request["job"],
              "request": request, "authority": authority,
              "ledger_before": ledger_before, "ledger_after": ledger_after,
              "reservation_scope": reservation_scope, "reservation": reservation,
              "preflight": preflight, "launch": launched, "outcome": outcome,
              "collected": collected, "receipt_dir": str(directory),
              "cleanup": cleanup, "elapsed_seconds": time.monotonic() - started,
              "claims": {"training_fit_claimed": False, "composition_claimed": False,
                         "final_targets_read": False}}
    if not cleanup.get("complete"):
        result["status"] = "AWS_BINDING_FIT_FAILED"
        result["cleanup_incomplete_reason"] = cleanup.get("failures")
    write_evidence(directory / "result.json", canonical(result))
    if reservation_error is not None:
        raise reservation_error
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--request")
    parser.add_argument("--request-sha256")
    parser.add_argument("--authority")
    parser.add_argument("--authority-sha256")
    parser.add_argument("--receipt-dir")
    parser.add_argument("--profile", default="default")
    arguments = parser.parse_args(argv)
    if not arguments.execute:
        print(json.dumps(plan_only(), sort_keys=True))
        return 0
    require(all(getattr(arguments, name) for name in
               ("request", "request_sha256", "authority", "authority_sha256", "receipt_dir")),
            "EXPLICIT_REGISTERED_INPUTS_REQUIRED")
    request_raw = Path(arguments.request).read_bytes()
    authority_raw = Path(arguments.authority).read_bytes()
    require(digest(request_raw) == arguments.request_sha256, "REQUEST_HASH_MISMATCH")
    require(digest(authority_raw) == arguments.authority_sha256, "AUTHORITY_HASH_MISMATCH")
    request = validate_request(json.loads(request_raw))
    authority = validate_authority(json.loads(authority_raw))
    provider = build(arguments)
    result = execute(request, authority, provider, receipt_dir=arguments.receipt_dir)
    print(json.dumps({"status": result["status"], "receipt_dir": result["receipt_dir"]}, sort_keys=True))
    return 0 if result["status"] == "AWS_BINDING_FIT_FINISHED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
