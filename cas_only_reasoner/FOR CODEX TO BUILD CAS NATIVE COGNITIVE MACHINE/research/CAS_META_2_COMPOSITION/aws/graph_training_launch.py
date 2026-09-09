"""Minimal AWS launcher for the graph-first ^6 specialist training run.

One self-contained module: frozen resource plan, source-package builder,
rendered worker script, and the AWS provider/launch lifecycle. Plan output is
inert by default; paid execution requires an explicit hash-bound launch
request AND a standing authority naming the job, the exact source/archive/
manifest identities, the owner authorization record, and the frozen budget.
A single $4.00 reservation is created exactly once through
``aws.budget.reserve_budget``; nothing is ever refunded or retried.

Every execution-path fix from the binding-fit rounds is present: pricing
client in us-east-1, bounded verified IAM profile wait, cleanup detach and
inline-policy ordering, bounded termination wait before security-group
deletion, collected-result naming (training_result.json), owner-record path
binding, and worker-side capture of the original inner error.

The worker runs BOTH prompt-framing conditions (cas, generic) sequentially on
one GPU instance: per-arm budget 64 optimizer steps / 600 s (total 128 steps /
1200 s), then the sealed-split evaluation with predictions recorded before
answers are consulted.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import stat
import subprocess
import time
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from aws import budget

ROOT = Path(__file__).resolve().parents[1]
GIT_PREFIX = "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/"
PILOT = "research/CAS_META_2_COMPOSITION/"
WHEEL_PREFIX = "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/"

SCHEMA = "cas-graph-training-launch/1"
REQUEST_SCHEMA = "cas-graph-training-launch-request/1"
AUTHORITY_SCHEMA = "cas-graph-training-launch-authority/1"
PACKAGE_SCHEMA = "cas-graph-training-source-package/1"
MANIFEST_NAME = "graph_training_source_manifest.json"
WORKER_NAME = "graph_training_worker.py"

LEDGER_PATH = ROOT / "records/budget/campaign_ledger.json"
OWNER_AUTHORIZATION_PATH = (ROOT / "records/teaching_cycle_001/graph_first_candidate_001/"
                            "training_mode_001/OWNER_AUTHORIZATION_AWS.json")
CAMPAIGN_CAP_USD = "400.00"
RESERVATION_USD = "4.00"

# Frozen budget (must match cas_meta2.graph_teaching.trainer).
FROZEN_MAX_OPTIMIZER_STEPS = 64
FROZEN_MAX_WALL_SECONDS = 600.0
FROZEN_LEARNING_RATE = 0.003
FROZEN_ARMS = ("cas", "generic")

JOB_PATTERN = r"cas-meta2-teaching-graph-\d{14}-[a-f0-9]{8}"
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
INSTANCE_ID = re.compile(r"i-[0-9a-f]{17}\Z")

EXPERIMENT = {"profile": "graph_training",
              "entrypoint": "cas_meta2.graph_teaching.trainer.launch"}

RESOURCE_PLAN = {
    "schema": "cas-graph-training-resource-plan/1",
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
    "worker_seconds_max": 1800,
    "instance_seconds_max": 3600,
    "automatic_retries": 0,
    "reservation_usd": RESERVATION_USD,
    "training": True,
    "ebs": {"size_gib": 75, "iops": 3000, "throughput_mib_s": 125,
            "encrypted": True, "delete_on_termination": True},
    "network": {"inbound_rules": 0, "egress_tcp_443_only": True},
    "frozen_budget": {
        "learning_rate": FROZEN_LEARNING_RATE,
        "max_optimizer_steps": FROZEN_MAX_OPTIMIZER_STEPS,
        "max_wall_seconds": FROZEN_MAX_WALL_SECONDS,
        "arms": list(FROZEN_ARMS),
        "total_optimizer_steps": 2 * FROZEN_MAX_OPTIMIZER_STEPS,
        "total_wall_seconds": 2 * FROZEN_MAX_WALL_SECONDS,
        "reservation_usd": RESERVATION_USD,
    },
}

EXPLICIT_FILES = (
    PILOT + "cas_meta2/__init__.py",
    PILOT + "cas_meta2/codec.py",
    PILOT + "cas_meta2/features_v2.py",
    PILOT + "cas_meta2/policy.py",
    PILOT + "requirements-gpu.txt",
)
SOURCE_DIRS = (
    PILOT + "cas_meta2/graph_teaching",
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


def scope():
    return json.loads(canonical(RESOURCE_PLAN))


def validate_request(request):
    require(type(request) is dict and request.get("schema") == REQUEST_SCHEMA,
            "GRAPH_TRAINING_REQUEST_SCHEMA")
    require(set(request) == {"schema", "job", "source_sha", "archive_sha256",
                             "manifest_sha256", "launch_authorized"},
            "GRAPH_TRAINING_REQUEST_FIELDS")
    require(type(request["job"]) is str and re.fullmatch(JOB_PATTERN, request["job"]),
            "GRAPH_TRAINING_REQUEST_JOB")
    require(type(request["source_sha"]) is str and bool(HEX40.fullmatch(request["source_sha"])),
            "GRAPH_TRAINING_REQUEST_SOURCE_SHA")
    for key in ("archive_sha256", "manifest_sha256"):
        require(type(request[key]) is str and bool(HEX64.fullmatch(request[key])),
                "GRAPH_TRAINING_REQUEST_HASH:" + key)
    require(request["launch_authorized"] is False, "GRAPH_TRAINING_REQUEST_INERT")
    return request


def validate_authority(authority):
    require(type(authority) is dict and authority.get("schema") == AUTHORITY_SCHEMA,
            "GRAPH_TRAINING_AUTHORITY_SCHEMA")
    require(set(authority) == {
        "schema", "job", "source_sha", "archive_sha256", "manifest_sha256",
        "owner_authorization_sha256", "learning_rate", "max_optimizer_steps",
        "max_wall_seconds", "reservation_usd"}, "GRAPH_TRAINING_AUTHORITY_FIELDS")
    require(type(authority["job"]) is str and re.fullmatch(JOB_PATTERN, authority["job"]),
            "GRAPH_TRAINING_AUTHORITY_JOB")
    require(type(authority["source_sha"]) is str and bool(HEX40.fullmatch(authority["source_sha"])),
            "GRAPH_TRAINING_AUTHORITY_SOURCE_SHA")
    for key in ("archive_sha256", "manifest_sha256", "owner_authorization_sha256"):
        require(type(authority[key]) is str and bool(HEX64.fullmatch(authority[key])),
                "GRAPH_TRAINING_AUTHORITY_HASH:" + key)
    require(authority["learning_rate"] == FROZEN_LEARNING_RATE,
            "GRAPH_TRAINING_AUTHORITY_BUDGET:learning_rate")
    require(authority["max_optimizer_steps"] == FROZEN_MAX_OPTIMIZER_STEPS,
            "GRAPH_TRAINING_AUTHORITY_BUDGET:max_optimizer_steps")
    require(authority["max_wall_seconds"] == FROZEN_MAX_WALL_SECONDS,
            "GRAPH_TRAINING_AUTHORITY_BUDGET:max_wall_seconds")
    require(authority["reservation_usd"] == RESERVATION_USD, "GRAPH_TRAINING_AUTHORITY_RESERVATION")
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


def render_worker():
    """Rendered in-package worker: both arms + sealed evaluation + error capture."""
    inner_lines = [
        "import hashlib",
        "import json",
        "import sys",
        "from pathlib import Path",
        "ROOT = Path(sys.argv[1])",
        "sys.path.insert(0, str(ROOT / 'research/CAS_META_2_COMPOSITION'))",
        "from cas_meta2.graph_teaching import trainer, adapter, lessons",
        "from cas_meta2.graph_teaching.real_framework import (build_encoder,",
        "    build_graph_training_framework, GraphLearner)",
        "from cas_meta2.teaching_cycle import gpu_adapter",
        "config = json.loads((ROOT / 'config.json').read_bytes())",
        "job = config['job']",
        "records = trainer.training_records(20260909)",
        "texts = [r['framings'][arm] for r in records for arm in ('cas', 'generic')]",
        "torch, device = gpu_adapter._cuda()",
        "encoder = build_encoder(torch, texts, d_model=64, seed=20260909)",
        "framework = build_graph_training_framework(torch, device, seed=20260909,",
        "                                           encoder=encoder)",
        "arms = []",
        "for arm in ('cas', 'generic'):",
        "    tasks = [adapter.build_task(r, arm) for r in records]",
        "    def learner_factory(model, arm=arm, learning_rate=0.003):",
        "        return GraphLearner(torch, framework, tasks, device, learning_rate)",
        "    report = trainer.launch(run_id=job + '.' + arm, arm=arm, framework=framework,",
        "                            model=framework.module, learner_factory=learner_factory,",
        "                            learning_rate=0.003, max_optimizer_steps=64,",
        "                            max_wall_seconds=600.0)",
        "    sealed = trainer.evaluate_sealed(learner_factory(framework.module),",
        "                                     seed=20260909)",
        "    arms.append({'arm': arm, 'report': report, 'sealed': sealed})",
        "raw = (json.dumps({'schema': 'cas-graph-training-result/1', 'job': job,",
        "                   'arms': arms}, sort_keys=True, indent=2) + '\\n').encode('utf-8')",
        "results = ROOT / 'results'",
        "results.mkdir(exist_ok=True)",
        "(results / 'result.json').write_bytes(raw)",
        "(results / 'result.json.sha256').write_text(hashlib.sha256(raw).hexdigest() + '\\n')",
    ]
    runner_block = ",\n".join(repr(line) for line in inner_lines)
    lines = [
        "#!/usr/bin/env python3",
        '"""Graph-training worker. One run, no restart. Both framing conditions',
        "sequentially; original inner errors are preserved in the failure report.",
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
        "        inner = subprocess.run([python, '-B', str(runner), str(root)],",
        "                             capture_output=True, text=True,",
        "                             timeout=MAX_WALL_SECONDS * 2 + 1200)",
        "        if inner.returncode != 0:",
        "            detail = (inner.stderr or inner.stdout or '')[-1800:]",
        "            raise SystemExit('INNER_RUNNER_EXIT_' + str(inner.returncode) + '\\n' + detail)",
        "        raw = (results / 'result.json').read_bytes()",
        "        sidecar = (results / 'result.json.sha256').read_text().strip()",
        "        if hashlib.sha256(raw).hexdigest() != sidecar:",
        "            raise SystemExit('RESULT_SHA_MISMATCH')",
        "    except BaseException as error:",
        "        failure = {'type': type(error).__name__, 'message': str(error)[:2000]}",
        "        report = {'schema': 'cas-graph-training-result/1',",
        "                  'status': 'REMOTE_WORKER_FAILED', 'failure': failure, 'job': job}",
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


def _run_git(args, cwd):
    process = subprocess.run(["git"] + args, cwd=str(cwd), stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=60,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if process.returncode != 0:
        message = process.stderr.decode("utf-8", "replace")[:2000]
        raise ValueError("PACKAGE_GIT_FAILED:" + message)
    return process.stdout


def git_key(path):
    path = safe_name(path)
    require(path.startswith("research/"), "PACKAGE_GIT_MEMBER_SCOPE")
    return GIT_PREFIX + path


def git_bytes(root, commit, path):
    return _run_git(["-c", "core.autocrlf=false", "show", commit + ":" + git_key(path)], root)


def git_tree_paths(root, commit, directory):
    raw = _run_git(["-c", "core.autocrlf=false", "ls-tree", "-rz", "--full-tree",
                    commit, "--", git_key(directory)], root)
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
        raw = render_worker().encode("utf-8") if name == WORKER_NAME \
            else git_bytes_fn(root, commit, name)
        require(len(raw) <= MAX_MEMBER_BYTES, "PACKAGE_MEMBER_TOO_LARGE:" + name)
        members[name] = raw
    require(members and len(members) <= MAX_MEMBER_COUNT
            and sum(map(len, members.values())) <= MAX_EXPANDED_BYTES, "PACKAGE_BOUND")
    for name, expected in WHEELS.items():
        require(name in members and digest(members[name]) == expected,
                "PACKAGE_FROZEN_WHEEL_CHANGED:" + name)
    return members


def manifest_for(members, source_sha):
    return {
        "schema": PACKAGE_SCHEMA, "source_sha": source_sha,
        "root_manifest": MANIFEST_NAME, "experiment": EXPERIMENT,
        "git_path_prefix": GIT_PREFIX, "worker_script": WORKER_NAME,
        "wheels": {name: {"sha256": expected, "bytes": len(members[name])}
                   for name, expected in WHEELS.items()},
        "members": sorted(members),
        "files_sha256": {name: digest(raw) for name, raw in sorted(members.items())},
        "files_bytes": {name: len(raw) for name, raw in sorted(members.items())},
        "member_count": len(members) + 1,
        "expanded_bytes": sum(map(len, members.values())),
        "launch_enabled": False, "training": True,
        "reservation_created": False, "automatic_retries": 0,
        "frozen_budget": RESOURCE_PLAN["frozen_budget"],
        "boundary": ("Source package only; launch_enabled:false. The paid run "
                     "requires a separately hash-bound launch request and owner "
                     "authorization for this exact manifest."),
    }


def build_package(output, *, source_sha, git_bytes_fn=git_bytes,
                  git_paths_fn=git_tree_paths):
    output = Path(output).absolute()
    require(not output.exists() and output.parent.is_dir()
            and output.is_relative_to((ROOT / "records").absolute())
            and output != ROOT / "records", "PACKAGE_NEW_SCOPED_OUTPUT_REQUIRED")
    members = resolve_members(ROOT, source_sha, git_bytes_fn=git_bytes_fn,
                              git_paths_fn=git_paths_fn)
    manifest = manifest_for(members, source_sha)
    members[MANIFEST_NAME] = canonical(manifest)
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED, compresslevel=6) as zipped:
        for name in sorted(members):
            info = ZipInfo(name, date_time=(2026, 9, 9, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zipped.writestr(info, members[name])
    raw = buffer.getvalue()
    require(len(raw) <= MAX_ARCHIVE_BYTES, "PACKAGE_ARCHIVE_BOUND")
    output.mkdir()
    with (output / "source.zip").open("xb") as stream:
        stream.write(raw)
    receipt = {"schema": "cas-graph-training-package-receipt/1",
               "status": "SOURCE_ONLY_NO_LAUNCH",
               "archive": str(output / "source.zip"),
               "archive_sha256": digest(raw), "archive_bytes": len(raw),
               "source_sha": source_sha,
               "manifest_sha256": digest(members[MANIFEST_NAME]),
               "member_count": len(members), "manifest": manifest}
    with (output / "receipt.json").open("xb") as stream:
        stream.write(canonical(receipt))
    return receipt


class _DefaultClientError(Exception):
    def __init__(self, code, message=""):
        super().__init__(message or code)
        self.response = {"Error": {"Code": code, "Message": message}}


class GraphTrainingProvider:
    """Injected provider: preflight, single reservation, launch, wait, collect,
    cleanup — with every binding-fit execution fix applied."""

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
        require(directory.is_dir() and self._evidence is None, "GRAPH_TRAINING_FRESH_EVIDENCE_REQUIRED")
        self._evidence = directory

    def _event(self, operation, state, **details):
        require(self._evidence is not None, "GRAPH_TRAINING_EVIDENCE_REQUIRED")
        number = len([p for p in self._evidence.iterdir() if p.name.startswith("provider_")]) + 1
        return write_evidence(self._evidence / ("provider_%04d.json" % number),
                              canonical({"schema": "cas-graph-training-provider/1",
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
        require(identity.get("Account") == frozen["account"], "GRAPH_TRAINING_PREFLIGHT_ACCOUNT")
        images = ec2.describe_images(ImageIds=[frozen["ami"]]).get("Images", [])
        require(len(images) == 1 and images[0].get("State") == "available",
                "GRAPH_TRAINING_PREFLIGHT_AMI")
        descriptions = ec2.describe_instance_types(
            InstanceTypes=[frozen["instance_type"]]).get("InstanceTypes", [])
        require(len(descriptions) == 1, "GRAPH_TRAINING_PREFLIGHT_INSTANCE_TYPE")
        gpus = descriptions[0].get("GpuInfo", {}).get("Gpus", [])
        require(len(gpus) == 1 and re.search(r"t4", gpus[0].get("Name", ""), re.I) is None
                and frozen["gpu_name_contains"] in gpus[0].get("Name", ""),
                "GRAPH_TRAINING_PREFLIGHT_GPU")
        fields = {"instanceType": frozen["instance_type"], "location": "US West (Oregon)",
                  "operatingSystem": "Linux", "tenancy": "Shared", "preInstalledSw": "NA",
                  "capacitystatus": "Used", "marketoption": "OnDemand",
                  "operation": "RunInstances"}
        price = pricing.get_products(ServiceCode="AmazonEC2", Filters=[
            {"Type": "TERM_MATCH", "Field": key, "Value": value} for key, value in fields.items()])
        require(not price.get("NextToken"), "GRAPH_TRAINING_PREFLIGHT_PAGINATED_PRICE")
        rates = [float(dimension["pricePerUnit"]["USD"])
                 for raw in price.get("PriceList", [])
                 for term in json.loads(raw).get("terms", {}).get("OnDemand", {}).values()
                 for dimension in term.get("priceDimensions", {}).values()
                 if dimension.get("unit") == "Hrs"]
        require(all(0 <= rate <= float(frozen["on_demand_rate_ceiling_usd"]) for rate in rates),
                "GRAPH_TRAINING_PREFLIGHT_RATE_CEILING")
        active = ec2.describe_instances(Filters=[
            {"Name": "tag-key", "Values": ["cas_meta_job"]},
            {"Name": "instance-state-name",
             "Values": ["pending", "running", "stopping", "shutting-down"]}])
        require(not active.get("NextToken") and not any(
            active.get("Reservations", [])), "GRAPH_TRAINING_PREFLIGHT_CONFLICTING_RESOURCES")
        return {"account": identity["Account"], "region": self.region, "ami": frozen["ami"],
                "instance_type": frozen["instance_type"], "instance_count": 1,
                "gpu_name_contains": frozen["gpu_name_contains"],
                "visible_gpu_count": 1, "t4_rejected": True,
                "rate_ceiling_usd": frozen["on_demand_rate_ceiling_usd"],
                "conflicting_resources": []}

    def reserve(self, amount):
        self.calls.append("reserve")
        self._event("budget_reservation", "REQUESTED", amount=amount)
        require(not self._reserved and amount == RESERVATION_USD,
                "GRAPH_TRAINING_RESERVATION_FROZEN")
        receipt = self.budget.reserve_budget(self.job, self.source_sha, self.archive_sha256,
                                             amount, reservation_plan(), self.ledger_path)
        self._reserved = True
        return {**receipt, "aws_side_reservation": self._record_aws_side_reservation(receipt)}

    def _bucket_name(self):
        return self.job + "-" + RESOURCE_PLAN["account"]

    def _ensure_bucket(self, s3):
        bucket = self._bucket_name()
        if "bucket" in self._resources:
            return bucket
        self._effect("create_bucket", s3.create_bucket, Bucket=bucket,
                     CreateBucketConfiguration={"LocationConstraint": self.region})
        s3.put_bucket_tagging(Bucket=bucket, Tagging={"TagSet": [
            {"Key": "cas_meta_job", "Value": self.job}]})
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

    def _await_instance_profile(self, iam, profile_name, role_name, *,
                                timeout=120.0, settle=15.0, poll_interval=2.0):
        deadline = time.monotonic() + timeout
        while True:
            observed = self._effect("verify_instance_profile", iam.get_instance_profile,
                                    InstanceProfileName=profile_name)
            roles = [item.get("RoleName") for item in
                     observed.get("InstanceProfile", {}).get("Roles", [])]
            if role_name in roles:
                time.sleep(settle)
                return observed
            require(time.monotonic() < deadline,
                    "GRAPH_TRAINING_IAM_PROFILE_PROPAGATION_TIMEOUT")
            time.sleep(poll_interval)

    def launch(self, job, permit):
        self.calls.append("launch")
        require(job == self.job and self._reserved and not self._launch_called,
                "GRAPH_TRAINING_LAUNCH_STATE")
        require(permit.get("job") == self.job and permit.get("source_sha") == self.source_sha
                and permit.get("archive_sha256") == self.archive_sha256
                and permit.get("manifest_sha256") == self.manifest_sha256
                and permit.get("resource_plan") == scope()
                and permit.get("reservation", {}).get("reservation", {}).get("status")
                == budget.STATUS, "GRAPH_TRAINING_PERMIT_INVALID")
        self._launch_called = True
        frozen = RESOURCE_PLAN
        ec2, s3, iam = (self.clients[name] for name in ("ec2", "s3", "iam"))
        bucket = self._bucket_name()
        worker_role = self.job + "-worker"
        raw = (Path(self.source_archive).read_bytes() if self.source_archive
               else None)
        if raw is None:
            require(False, "GRAPH_TRAINING_SOURCE_ARCHIVE_REQUIRED")
        require(digest(raw) == self.archive_sha256, "GRAPH_TRAINING_SOURCE_ARCHIVE_HASH")
        write_evidence(self._evidence / "source.zip", raw)
        self._ensure_bucket(s3)
        self._effect("upload_source", s3.put_object, Bucket=bucket,
                     Key="input/source.zip", Body=raw)
        config = {"schema": "cas-graph-training-worker-config/1", "job": self.job,
                  "bucket": bucket, "region": self.region}
        self._effect("upload_config", s3.put_object, Bucket=bucket,
                     Key="input/config.json", Body=canonical(config))
        trust = {"Version": "2012-10-17", "Statement": [
            {"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"},
             "Action": "sts:AssumeRole"}]}
        self._effect("create_role", iam.create_role, RoleName=worker_role,
                     AssumeRolePolicyDocument=json.dumps(trust),
                     Tags=[{"Key": "cas_meta_job", "Value": self.job}])
        self._effect("put_role_policy", iam.put_role_policy, RoleName=worker_role,
                     PolicyName="job-only",
                     PolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": [
                         {"Effect": "Allow", "Action": ["s3:GetObject"],
                          "Resource": ["arn:aws:s3:::" + bucket + "/input/*"]},
                         {"Effect": "Allow", "Action": ["s3:PutObject"],
                          "Resource": ["arn:aws:s3:::" + bucket + "/results/*"]}]}))
        self._effect("create_instance_profile", iam.create_instance_profile,
                     InstanceProfileName=worker_role,
                     Tags=[{"Key": "cas_meta_job", "Value": self.job}])
        self._effect("add_role_to_instance_profile", iam.add_role_to_instance_profile,
                     InstanceProfileName=worker_role, RoleName=worker_role)
        self._await_instance_profile(iam, worker_role, worker_role)
        vpcs = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}]).get("Vpcs", [])
        require(len(vpcs) == 1, "GRAPH_TRAINING_DEFAULT_VPC_REQUIRED")
        subnets = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpcs[0]["VpcId"]]},
                                                {"Name": "default-for-az", "Values": ["true"]}]
                                       ).get("Subnets", [])
        require(subnets, "GRAPH_TRAINING_DEFAULT_SUBNET_REQUIRED")
        group = self._effect("create_security_group", ec2.create_security_group,
                             GroupName=self.job,
                             Description="CAS graph-training outbound HTTPS only",
                             VpcId=vpcs[0]["VpcId"],
                             TagSpecifications=[{"ResourceType": "security-group",
                                                 "Tags": [{"Key": "cas_meta_job",
                                                           "Value": self.job}]}])
        sg = group["GroupId"]
        self._resources["security_group"] = sg
        self._effect("revoke_security_group_egress", ec2.revoke_security_group_egress,
                     GroupId=sg, IpPermissions=[{"IpProtocol": "-1",
                                                 "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        self._effect("authorize_security_group_egress", ec2.authorize_security_group_egress,
                     GroupId=sg, IpPermissions=[{"IpProtocol": "tcp", "FromPort": 443,
                                                 "ToPort": 443,
                                                 "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        bootstrap = "\n".join([
            "#!/bin/bash", "set -eu", "umask 077",
            "export PYTHONDONTWRITEBYTECODE=1 AWS_MAX_ATTEMPTS=1 AWS_PAGER=''",
            "mkdir -p /opt/cas-graph-training/package",
            "exec > /opt/cas-graph-training/bootstrap.log 2>&1",
            "timeout 120 aws s3api get-object --bucket " + bucket
            + " --key input/source.zip /opt/cas-graph-training/package/source.zip --region "
            + self.region,
            "echo '" + self.archive_sha256 + "  /opt/cas-graph-training/package/source.zip' | sha256sum -c -",
            "cd /opt/cas-graph-training/package",
            "unzip -q source.zip",
            "timeout 120 aws s3api get-object --bucket " + bucket
            + " --key input/config.json /opt/cas-graph-training/package/config.json --region "
            + self.region,
            "PY=''",
            "for p in python3.12 python3.11 python3; do",
            "  if command -v \"$p\" >/dev/null 2>&1; then PY=\"$p\"; break; fi",
            "done",
            "test -n \"$PY\" || { echo SUPPORTED_PYTHON_REQUIRED; exit 1; }",
            "\"$PY\" -B /opt/cas-graph-training/package/" + WORKER_NAME,
            "",
        ])
        launched = self._effect("run_instances", ec2.run_instances,
            ImageId=frozen["ami"], InstanceType=frozen["instance_type"],
            MinCount=1, MaxCount=1, ClientToken=self.job,
            IamInstanceProfile={"Arn": "arn:aws:iam::" + frozen["account"]
                                + ":instance-profile/" + worker_role},
            InstanceInitiatedShutdownBehavior="terminate",
            MetadataOptions={"HttpTokens": "required", "HttpEndpoint": "enabled"},
            NetworkInterfaces=[{"DeviceIndex": 0, "SubnetId": subnets[0]["SubnetId"],
                                "Groups": [sg], "AssociatePublicIpAddress": True,
                                "DeleteOnTermination": True}],
            BlockDeviceMappings=[{"DeviceName": "/dev/sda1", "Ebs": {
                "VolumeSize": frozen["ebs"]["size_gib"], "VolumeType": "gp3",
                "Iops": frozen["ebs"]["iops"], "Throughput": frozen["ebs"]["throughput_mib_s"],
                "Encrypted": True, "DeleteOnTermination": True}}],
            TagSpecifications=[{"ResourceType": "instance",
                                "Tags": [{"Key": "cas_meta_job", "Value": self.job}]},
                               {"ResourceType": "volume",
                                "Tags": [{"Key": "cas_meta_job", "Value": self.job}]}],
            UserData=bootstrap)
        require(len(launched.get("Instances", [])) == 1
                and bool(INSTANCE_ID.fullmatch(launched["Instances"][0]["InstanceId"])),
                "GRAPH_TRAINING_ONE_INSTANCE_RESPONSE_REQUIRED")
        self._instance_id = launched["Instances"][0]["InstanceId"]
        self._instance_ids = [self._instance_id]
        self._resources["instance"] = self._instance_id
        self._event("instance_identity", "OBSERVED", instance_id=self._instance_id,
                    client_token=self.job)
        return {"job": self.job, "instance_id": self._instance_id,
                "client_token": self.job, "imdsv2_required": True, "bucket": bucket,
                "automatic_retries": 0}

    def _read_body(self, body, maximum):
        total = 0
        blocks = []
        while True:
            block = body.read(min(1024**2, maximum - total + 1))
            if not block:
                break
            total += len(block)
            require(total <= maximum, "GRAPH_TRAINING_S3_BODY_BOUND")
            blocks.append(block)
        return b"".join(blocks)

    def wait(self, job, timeout, *, poll_interval=5.0):
        self.calls.append("wait")
        require(job == self.job and self._instance_id is not None
                and 0 < timeout <= RESOURCE_PLAN["instance_seconds_max"],
                "GRAPH_TRAINING_WAIT_STATE")
        ec2, s3 = self.clients["ec2"], self.clients["s3"]
        bucket = self._resources["bucket"]
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                response = s3.get_object(Bucket=bucket, Key="results/result.json")
                raw = self._read_body(response["Body"], 8 * 1024**2)
                result = json.loads(raw)
                require(result.get("schema") == "cas-graph-training-result/1",
                        "GRAPH_TRAINING_RESULT_IDENTITY")
                self._result = result
                self._result_raw = raw
                if result.get("status") == "REMOTE_WORKER_FAILED":
                    return {"worker_status": "REMOTE_FAILED"}
                return {"worker_status": "REMOTE_FINISHED"}
            except self._client_error as error:
                if self._error_code(error) not in ("NoSuchKey", "404"):
                    raise
            current = ec2.describe_instances(InstanceIds=[self._instance_id]
                                             )["Reservations"][0]["Instances"][0]
            if current.get("State", {}).get("Name") in ("terminated", "shutting-down"):
                return {"worker_status": "REMOTE_FAILED", "instance_state":
                        current.get("State", {}).get("Name")}
            time.sleep(poll_interval)
        return {"worker_status": "REMOTE_TIMED_OUT"}

    def collect(self, job):
        self.calls.append("collect")
        require(job == self.job and self._instance_id is not None
                and self._result_raw is not None, "GRAPH_TRAINING_COLLECT_STATE")
        s3 = self.clients["s3"]
        response = s3.get_object(Bucket=self._resources["bucket"],
                                 Key="results/result.json.sha256")
        sidecar = self._read_body(response["Body"], 4096).strip()
        require(sidecar.decode("utf-8", "replace") == digest(self._result_raw),
                "GRAPH_TRAINING_RESULT_SHA_MISMATCH")
        write_evidence(self._evidence / "training_result.json", self._result_raw)
        write_evidence(self._evidence / "training_result.json.sha256", sidecar)
        return {"result": str(self._evidence / "training_result.json"),
                "sha256": str(self._evidence / "training_result.json.sha256"),
                "result_sha256": digest(self._result_raw)}

    def _await_terminated(self, ec2, instance_ids, timeout=300.0, poll_interval=5.0):
        pending = list(instance_ids)
        deadline = time.monotonic() + timeout
        while pending and time.monotonic() < deadline:
            for instance_id in list(pending):
                try:
                    current = ec2.describe_instances(InstanceIds=[instance_id]
                                                     )["Reservations"][0]["Instances"][0]
                    if current.get("State", {}).get("Name") == "terminated":
                        pending.remove(instance_id)
                except self._client_error as error:
                    if self._error_code(error) == "InvalidInstanceID.NotFound":
                        pending.remove(instance_id)
                except Exception:
                    pass
            if pending:
                time.sleep(poll_interval)
        return pending

    def cleanup(self, job):
        self.calls.append("cleanup")
        require(job == self.job, "GRAPH_TRAINING_CLEANUP_JOB_MISMATCH")
        failures = []
        status = {"instance_ids": list(self._instance_ids), "instances": {},
                  "security_group_deleted": True, "schedule_removed": True,
                  "roles_removed": True, "bucket_deleted": True,
                  "results_deleted": False, "complete": False, "failures": failures}
        ec2, s3, iam, scheduler = (self.clients.get(name) for name in
                                   ("ec2", "s3", "iam", "scheduler"))

        def failed(label, error):
            failures.append(label + ":" + type(error).__name__ + ":" + str(error)[:1500])

        for instance_id in self._instance_ids:
            try:
                current = ec2.describe_instances(InstanceIds=[instance_id]
                                                 )["Reservations"][0]["Instances"][0]
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
        remaining = self._await_terminated(ec2, [
            instance_id for instance_id in self._instance_ids
            if status["instances"].get(instance_id) != "CONFIRMED_ABSENT"])
        status["instances_termination_pending"] = remaining
        try:
            groups = ec2.describe_security_groups(Filters=[{"Name": "group-name",
                                                            "Values": [self.job]}])
            require(not groups.get("NextToken"), "SECURITY_GROUP_OBSERVATION_TRUNCATED")
            for candidate in groups.get("SecurityGroups", []):
                ec2.delete_security_group(GroupId=candidate["GroupId"])
        except self._client_error as error:
            if self._error_code(error) not in ("InvalidGroup.NotFound",
                                               "InvalidSecurityGroupID.NotFound"):
                failed("SECURITY_GROUP_DELETION_FAILED", error)
                status["security_group_deleted"] = False
        except Exception as error:
            failed("SECURITY_GROUP_DELETION_FAILED", error)
            status["security_group_deleted"] = False
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
        profile_name = self.job + "-worker"
        try:
            iam.remove_role_from_instance_profile(InstanceProfileName=profile_name,
                                                  RoleName=profile_name)
        except self._client_error as error:
            if self._error_code(error) != "NoSuchEntity":
                failed("ROLE_DETACH_FAILED", error)
                status["roles_removed"] = False
        except Exception as error:
            failed("ROLE_DETACH_FAILED", error)
            status["roles_removed"] = False
        try:
            iam.delete_role_policy(RoleName=profile_name, PolicyName="job-only")
        except self._client_error as error:
            if self._error_code(error) != "NoSuchEntity":
                failed("ROLE_POLICY_REMOVAL_FAILED", error)
                status["roles_removed"] = False
        except Exception as error:
            failed("ROLE_POLICY_REMOVAL_FAILED", error)
            status["roles_removed"] = False
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
        bucket = self._resources.get("bucket")
        if bucket is not None:
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


def reservation_plan():
    frozen = RESOURCE_PLAN
    return {"instance_count": frozen["instance_count"],
            "runtime_seconds_max": frozen["instance_seconds_max"],
            "instance_type": frozen["instance_type"], "account_id": frozen["account"],
            "region": frozen["region"], "automatic_retries": frozen["automatic_retries"],
            "on_demand_hourly_usd_max": frozen["on_demand_rate_ceiling_usd"],
            "ancillary_reserved_usd": "1.48",
            "task_scope": "graph_first_teaching_candidate_001",
            "campaign_scope": "cas-meta2-composition-campaign",
            "frozen_budget": json.loads(canonical(frozen["frozen_budget"]))}


def validate_reservation_scope(ledger_document, amount=RESERVATION_USD):
    ledger = ledger_document["ledger"]
    amount = budget.amount(amount, positive=True)
    require(budget.amount(ledger["owner_task_cap_usd"]) == budget.amount(CAMPAIGN_CAP_USD),
            "LEDGER_CAP_CHANGED")
    require(budget.amount(ledger["total_reserved_usd"])
            + budget.amount(ledger["remaining_unreserved_usd"])
            == budget.amount(CAMPAIGN_CAP_USD), "INCONSISTENT_CAMPAIGN_TOTALS")
    require(budget.amount(ledger["remaining_unreserved_usd"]) >= amount,
            "RESERVATION_OUTSIDE_CAMPAIGN_BUDGET")
    return {"amount": str(amount)}


def validate_reserved_transition(before, after, receipt, request):
    prior, current = before["ledger"], after["ledger"]
    require(current["revision"] == prior["revision"] + 1, "RESERVATION_REVISION_MISMATCH")
    require(current["reservations"][:-1] == prior["reservations"], "RESERVATION_NOT_APPEND_ONLY")
    require(current["previous_state_sha256"] == budget.digest(budget.encoded(prior)),
            "RESERVATION_PREDECESSOR_MISMATCH")
    entry = current["reservations"][-1]
    for key in ("job", "source_sha", "archive_sha256"):
        require(entry[key] == request[key], "RESERVATION_IDENTITY_MISMATCH:" + key)
    require(entry["status"] == budget.STATUS
            and budget.amount(entry["reserved_usd"]) == budget.amount(RESERVATION_USD),
            "RESERVATION_AMOUNT_FROZEN")
    require(entry["plan"] == reservation_plan()
            and entry["plan_sha256"] == budget.digest(budget.encoded(reservation_plan())),
            "RESERVATION_RESOURCE_PLAN_MISMATCH")
    require(receipt.get("ledger_sha256") == after["ledger_sha256"],
            "RESERVATION_RECEIPT_HASH_MISMATCH")
    return receipt


def read_ledger(path=LEDGER_PATH):
    raw = Path(path).read_bytes()
    return {"ledger": budget.validate_state(budget.decoded(raw)),
            "ledger_sha256": sha256(raw).hexdigest(), "ledger_path": str(Path(path).resolve())}


def validate_preflight(facts):
    frozen = RESOURCE_PLAN
    require(type(facts) is dict and facts.get("account") == frozen["account"]
            and facts.get("region") == frozen["region"]
            and facts.get("ami") == frozen["ami"]
            and facts.get("instance_type") == frozen["instance_type"]
            and facts.get("instance_count") == 1
            and facts.get("gpu_name_contains") == frozen["gpu_name_contains"]
            and facts.get("visible_gpu_count") == 1
            and facts.get("t4_rejected") is True
            and facts.get("rate_ceiling_usd") == frozen["on_demand_rate_ceiling_usd"]
            and facts.get("conflicting_resources") in (None, [], {}),
            "PREFLIGHT_FACTS_INVALID")
    return facts


def execute(request, authority, provider, *, ledger_path=LEDGER_PATH, receipt_dir=None,
            owner_authorization_path=None):
    validate_request(request)
    validate_authority(authority)
    owner_path = (Path(owner_authorization_path) if owner_authorization_path is not None
                  else OWNER_AUTHORIZATION_PATH)
    require(authority["owner_authorization_sha256"] == digest(owner_path.read_bytes()),
            "OWNER_AUTHORIZATION_RECORD_MISMATCH")
    require(authority["job"] == request["job"] and authority["source_sha"] == request["source_sha"],
            "REQUEST_AUTHORITY_MISMATCH")
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
        Path(ledger_path).parent / ("graph_training_" + request["job"]))
    write_evidence(directory / "intent.json", canonical({
        "schema": SCHEMA, "request": request, "authority": authority,
        "ledger_before": ledger_before, "automatic_retries": 0}))
    provider.configure_evidence(directory)
    preflight = None
    reservation = ledger_after = launched = collected = None
    reservation_valid, reservation_error = False, None
    try:
        preflight = validate_preflight(provider.preflight())
        write_evidence(directory / "preflight.json", canonical(preflight))
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
        status = ("AWS_GRAPH_TRAINING_FINISHED" if outcome.get("worker_status")
                  == "REMOTE_FINISHED" else "AWS_GRAPH_TRAINING_FAILED")
    except BaseException as error:
        status = "AWS_GRAPH_TRAINING_LAUNCH_FAILED"
        outcome = {"exception_type": type(error).__name__, "exception": str(error)[:2000]}
        if not reservation_valid:
            reservation_error = error
        try:
            write_evidence(directory / "failure.json", canonical(outcome))
        except Exception as record_error:
            outcome["failure_record_error"] = (type(record_error).__name__ + ":"
                                               + str(record_error)[:1000])
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
              "claims": {"specialist_claimed": False, "composition_claimed": False,
                         "final_targets_read": False}}
    if not cleanup.get("complete"):
        result["status"] = "AWS_GRAPH_TRAINING_FAILED"
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
    parser.add_argument("--owner-authorization")
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
    import boto3
    from botocore.config import Config
    config = Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 0})
    session = boto3.Session(profile_name=arguments.profile,
                            region_name=RESOURCE_PLAN["region"])
    clients = {name: session.client(name, config=config)
               for name in ("sts", "ec2", "iam", "s3", "scheduler")}
    clients["pricing"] = session.client("pricing", region_name="us-east-1", config=config)
    provider = GraphTrainingProvider(job=request["job"], source_sha=request["source_sha"],
                                     archive_sha256=request["archive_sha256"],
                                     manifest_sha256=request["manifest_sha256"],
                                     ledger_path=LEDGER_PATH, clients=clients,
                                     source_archive=_locate_archive(request["archive_sha256"]))
    result = execute(request, authority, provider, receipt_dir=arguments.receipt_dir,
                     owner_authorization_path=arguments.owner_authorization)
    print(json.dumps({"status": result["status"], "receipt_dir": result["receipt_dir"]},
                     sort_keys=True))
    return 0 if result["status"] == "AWS_GRAPH_TRAINING_FINISHED" else 1


def _locate_archive(archive_sha256):
    for receipt in sorted((ROOT / "records").rglob("receipt.json")):
        try:
            document = json.loads(receipt.read_bytes())
        except (OSError, ValueError):
            continue
        if document.get("archive_sha256") == archive_sha256 and document.get("archive"):
            archive = Path(document["archive"])
            if archive.is_file():
                return archive
    raise ValueError("GRAPH_TRAINING_SOURCE_ARCHIVE_NOT_FOUND")


if __name__ == "__main__":
    raise SystemExit(main())
