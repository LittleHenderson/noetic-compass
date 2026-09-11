"""Launcher binding for CUBE_FACE_GROUNDING_001 / CFC_LOOP_001.

This is a **binding, not another launcher**. It supplies the four things a new
experiment actually owns - its request and authority schemas, its frozen design,
its rendered worker and its provider subclass - and reuses everything else from the
proven path: the package builder and the whole execution lifecycle
(``candidate.execute``, with these validators injected), the EC2/S3/IAM provider
and its verified collection, the ledger reservation, the cleanup that never deletes
an uncollected bucket, and the evidence writer.

What is new here, and why:

* **the worker is thin.** The environment scaffolding is the part that has actually
  run on an instance (create a venv, install ``torch``, install the two frozen
  wheels, install the requirements, run the body under that python, upload last),
  so it is copied from the proven workers verbatim. The *work* lives in
  ``cas_meta2.graph_teaching.face_worker``, a packaged module that the rehearsal
  executes in-process instead of trusting it to the instance.
* **the design** declares four conditions from the two owner plans, the declared
  schedule arithmetic, the token budget and the wall-clock ceiling, and it refuses
  any request whose bounds differ.
* **no plan here reserves anything.** The request it can build is inert
  (``launch_authorized: false``) until a separately hash-bound owner instruction
  arrives.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
COMPOSITION = HERE.parent
if str(COMPOSITION) not in sys.path:
    sys.path.insert(0, str(COMPOSITION))

from aws.graph_training_curriculum_launch import (  # noqa: E402
    HEX40, HEX64, LEDGER_PATH, RESOURCE_PLAN, RESERVATION_USD, ROOT as REPO_ROOT,
    WORKER_REQUIREMENTS, WORKER_WHEEL_DIR, build_package, canonical, digest,
    prepare_evidence, read_ledger, require, scope, validate_preflight,
    validate_reservation_scope, validate_reserved_transition, write_evidence)
from aws import graph_training_candidate_launch as candidate  # noqa: E402

SCHEMA = "cas-graph-training-face-launch/1"
REQUEST_SCHEMA = "cas-graph-training-face-launch-request/1"
AUTHORITY_SCHEMA = "cas-graph-training-face-launch-authority/1"
PACKAGE_SCHEMA = "cas-graph-training-face-source-package/1"
RECEIPT_SCHEMA = "cas-graph-training-face-package-receipt/1"
RESULT_SCHEMA = "cas.cube-face-result/1"
WORKER_NAME = "graph6_face_worker.py"
JOB_PATTERN = r"cas-meta2-graph6face-\d{14}-[a-f0-9]{8}"
EXPERIMENT = {"profile": "cube_face_grounding_cfc",
              "entrypoint": "cas_meta2.graph_teaching.face_worker.run"}

#: The four conditions the two plans ask about. Both plans proposed one paired
#: two-condition pilot; running all four in one job answers both questions from one
#: reservation and one matched initialization, which is declared here explicitly as
#: a deviation rather than assumed. The ceiling is sized for four conditions on one
#: instance inside one reservation.
FROZEN_CONDITIONS = ("cfc_stable_cues", "cfc_neutral_cue",
                     "mixed_order_stable_cues", "mixed_order_neutral_cue")
FROZEN_ORGANIZATION = {"cfc_stable_cues": "CFC_LOOP",
                       "cfc_neutral_cue": "CFC_LOOP",
                       "mixed_order_stable_cues": "MIXED_ORDER",
                       "mixed_order_neutral_cue": "MIXED_ORDER"}
FROZEN_CUES = {"cfc_stable_cues": "stable", "cfc_neutral_cue": "neutral",
               "mixed_order_stable_cues": "stable",
               "mixed_order_neutral_cue": "neutral"}
FROZEN_SEED = 20260912
FROZEN_ENCODER_SEED = 20260909
FROZEN_LEARNING_RATE = 0.003
FROZEN_BATCH_SIZE = 8
FROZEN_EVENTS_PER_CONDITION = 4608
FROZEN_UPDATES_PER_CONDITION = FROZEN_EVENTS_PER_CONDITION // FROZEN_BATCH_SIZE
FROZEN_TOTAL_UPDATES = FROZEN_UPDATES_PER_CONDITION * len(FROZEN_CONDITIONS)
FROZEN_PANEL_ITEMS = 192
FROZEN_MAX_WALL_SECONDS_PER_CONDITION = 3600.0
FROZEN_BUCKET_PREFIX = "cas-meta2-graph6face"
RECEIPT_PREFIX = "graph6face_"

DESIGN = {
    "launch_enabled": False,
    "training": True,
    "organization": "CFC_LOOP with a mixed-order control",
    "conditions": list(FROZEN_CONDITIONS),
    "organization_per_condition": dict(FROZEN_ORGANIZATION),
    "cue_per_condition": dict(FROZEN_CUES),
    "events_per_condition": FROZEN_EVENTS_PER_CONDITION,
    "updates_per_condition": FROZEN_UPDATES_PER_CONDITION,
    "total_optimizer_steps": FROZEN_TOTAL_UPDATES,
    "batch_size": FROZEN_BATCH_SIZE,
    "seed": FROZEN_SEED,
    "encoder_seed": FROZEN_ENCODER_SEED,
    "learning_rate": FROZEN_LEARNING_RATE,
    "panel_items": FROZEN_PANEL_ITEMS,
    "max_wall_seconds_per_condition": FROZEN_MAX_WALL_SECONDS_PER_CONDITION,
    "reservation_usd": RESERVATION_USD,
    "deviation_from_the_plans": (
        "each plan proposed one paired two-condition pilot; this binding runs the "
        "four cells (loop/mixed x stable/neutral) in one job so both plans' "
        "questions are answered from one initialization and one reservation"),
    "unchanged": ("no architecture change, no new head, no readout change; the "
                  "trainable scope stays the accepted operation:^6 allowlist"),
}


def validate_request(request):
    require(type(request) is dict and request.get("schema") == REQUEST_SCHEMA,
            "FACE_REQUEST_SCHEMA")
    require(set(request) == {"schema", "job", "source_sha", "archive_sha256",
                             "manifest_sha256", "launch_authorized"},
            "FACE_REQUEST_FIELDS")
    require(type(request["job"]) is str and re.fullmatch(JOB_PATTERN, request["job"]),
            "FACE_REQUEST_JOB")
    require(type(request["source_sha"]) is str and bool(HEX40.fullmatch(request["source_sha"])),
            "FACE_REQUEST_SOURCE_SHA")
    for key in ("archive_sha256", "manifest_sha256"):
        require(type(request[key]) is str and bool(HEX64.fullmatch(request[key])),
                "FACE_REQUEST_HASH:" + key)
    require(request["launch_authorized"] is False, "FACE_REQUEST_INERT")
    return request


def validate_authority(authority):
    require(type(authority) is dict and authority.get("schema") == AUTHORITY_SCHEMA,
            "FACE_AUTHORITY_SCHEMA")
    require(set(authority) == {
        "schema", "job", "source_sha", "archive_sha256", "manifest_sha256",
        "owner_authorization_sha256", "conditions", "events_per_condition",
        "updates_per_condition", "total_optimizer_steps", "batch_size", "seed",
        "encoder_seed", "panel_items", "learning_rate",
        "max_wall_seconds_per_condition", "reservation_usd"},
        "FACE_AUTHORITY_FIELDS")
    require(type(authority["job"]) is str and re.fullmatch(JOB_PATTERN, authority["job"]),
            "FACE_AUTHORITY_JOB")
    require(type(authority["source_sha"]) is str
            and bool(HEX40.fullmatch(authority["source_sha"])),
            "FACE_AUTHORITY_SOURCE_SHA")
    for key in ("archive_sha256", "manifest_sha256", "owner_authorization_sha256"):
        require(type(authority[key]) is str and bool(HEX64.fullmatch(authority[key])),
                "FACE_AUTHORITY_HASH:" + key)
    require(list(authority["conditions"]) == list(FROZEN_CONDITIONS),
            "FACE_AUTHORITY_CONDITIONS_FROZEN")
    require(authority["events_per_condition"] == FROZEN_EVENTS_PER_CONDITION,
            "FACE_AUTHORITY_EVENTS_FROZEN")
    require(authority["updates_per_condition"] == FROZEN_UPDATES_PER_CONDITION,
            "FACE_AUTHORITY_UPDATES_FROZEN")
    require(authority["total_optimizer_steps"] == FROZEN_TOTAL_UPDATES,
            "FACE_AUTHORITY_TOTAL_UPDATES_FROZEN")
    require(authority["batch_size"] == FROZEN_BATCH_SIZE,
            "FACE_AUTHORITY_BATCH_FROZEN")
    require(authority["seed"] == FROZEN_SEED, "FACE_AUTHORITY_SEED_FROZEN")
    require(authority["encoder_seed"] == FROZEN_ENCODER_SEED,
            "FACE_AUTHORITY_ENCODER_SEED_FROZEN")
    require(authority["panel_items"] == FROZEN_PANEL_ITEMS,
            "FACE_AUTHORITY_PANEL_FROZEN")
    require(authority["learning_rate"] == FROZEN_LEARNING_RATE,
            "FACE_AUTHORITY_LR_FROZEN")
    require(authority["max_wall_seconds_per_condition"]
            == FROZEN_MAX_WALL_SECONDS_PER_CONDITION,
            "FACE_AUTHORITY_WALL_FROZEN")
    require(authority["reservation_usd"] == RESERVATION_USD,
            "FACE_AUTHORITY_RESERVATION_FROZEN")
    return authority


def render_worker():
    """The in-package worker: proven scaffolding, thin body.

    The environment steps are the ones that have actually run on an instance. The
    body writes its own failure through ``result.json`` so a failed run is seen and
    terminated instead of idling (attempt 004's lesson), and the sidecar so the
    collector's identity check passes (attempt 006's lesson).
    """
    inner_lines = [
        "import json",
        "import sys",
        "from pathlib import Path",
        "ROOT = Path(sys.argv[1])",
        "sys.path.insert(0, str(ROOT / 'research/CAS_META_2_COMPOSITION'))",
        "from cas_meta2.graph_teaching import face_worker",
        "from cas_meta2.teaching_cycle import gpu_adapter",
        "CONFIG = json.loads((ROOT / 'config.json').read_bytes())",
        "torch, device = gpu_adapter._cuda()",
        "RESULTS = ROOT / 'results'",
        "ARTIFACTS = RESULTS / 'artifacts'",
        "ARTIFACTS.mkdir(parents=True, exist_ok=True)",
        "report = face_worker.run(CONFIG, torch=torch, device=device,",
        "                         results=RESULTS, artifacts=ARTIFACTS,",
        "                         outbound=None)",
        "print(json.dumps({'inner_status': 'MEASUREMENTS_WRITTEN',",
        "                  'conditions': list(report['envelope']['conditions']),",
        "                  'artifacts': len(report['envelope']['artifacts'])}))",
    ]
    runner_block = ",\n".join(repr(line) for line in inner_lines)
    return "\n".join([
        '"""GRAPH6 face-grounding worker: four conditions, one run, verified delivery.',
        "",
        "The body lives in the packaged module cas_meta2.graph_teaching.face_worker,",
        "so the rehearsal executes it in-process. This script only prepares the",
        "environment, runs the body under that environment's python, and uploads what",
        'it wrote - result.json last, because that is the completion marker."""',
        "import hashlib",
        "import json",
        "import shutil",
        "import subprocess",
        "import sys",
        "from pathlib import Path",
        "",
        "RESULT_SCHEMA = %r" % RESULT_SCHEMA,
        "FAILURE_SCHEMA = 'cas.cube-face-failure/1'",
        "ARTIFACT_MANIFEST_KEY = 'results/artifacts/manifest.json'",
        "MAX_WALL_SECONDS = %.1f" % FROZEN_MAX_WALL_SECONDS_PER_CONDITION,
        "CONDITIONS = %d" % len(FROZEN_CONDITIONS),
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
        "",
        "def sha256_file(path):",
        "    digest = hashlib.sha256()",
        "    with open(path, 'rb') as stream:",
        "        for block in iter(lambda: stream.read(1 << 20), b''):",
        "            digest.update(block)",
        "    return digest.hexdigest()",
        "",
        "",
        "def run_checked(argv):",
        "    subprocess.run(argv, check=True)",
        "",
        "",
        "def read_json(path, default=None):",
        "    if not path.is_file():",
        "        return default",
        "    return json.loads(path.read_bytes())",
        "",
        "",
        "def upload_results(s3, bucket, results):",
        "    \"\"\"Artifacts and manifest, then the sidecar, then result.json LAST.\"\"\"",
        "    uploaded = {'artifacts': [], 'manifest': False, 'result': False}",
        "    artifacts = results / 'artifacts'",
        "    manifest = read_json(artifacts / 'manifest.json')",
        "    if manifest:",
        "        s3.put_object(Bucket=bucket, Key=ARTIFACT_MANIFEST_KEY,",
        "                      Body=(artifacts / 'manifest.json').read_bytes())",
        "        uploaded['manifest'] = True",
        "        for entry in manifest['artifacts']:",
        "            path = artifacts / entry['name']",
        "            if path.is_file():",
        "                s3.put_object(Bucket=bucket,",
        "                              Key='results/artifacts/' + entry['name'],",
        "                              Body=path.read_bytes())",
        "                uploaded['artifacts'].append(entry['name'])",
        "    for name in ('measurements.json', 'failure.json', 'result_partial.json',",
        "                 'result.json.sha256'):",
        "        path = results / name",
        "        if path.is_file():",
        "            s3.put_object(Bucket=bucket, Key='results/' + name,",
        "                          Body=path.read_bytes())",
        "    path = results / 'result.json'",
        "    if path.is_file():",
        "        s3.put_object(Bucket=bucket, Key='results/result.json',",
        "                      Body=path.read_bytes())",
        "        uploaded['result'] = True",
        "    return uploaded",
        "",
        "",
        "def main():",
        "    root = Path(__file__).resolve().parent",
        "    config = json.loads((root / 'config.json').read_bytes())",
        "    job = config['job']",
        "    bucket = config['bucket']",
        "    region = config['region']",
        "    results = root / 'results'",
        "    results.mkdir(exist_ok=True)",
        "    failure = None",
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
        "        run_checked([python, '-m', 'pip', 'install',",
        "                     '--disable-pip-version-check', 'torch==2.11.0',",
        "                     '--index-url', TORCH_INDEX])",
        "        wheels = [str(root / WHEEL_DIR / name) for name in WHEEL_NAMES]",
        "        run_checked([python, '-m', 'pip', 'install',",
        "                     '--disable-pip-version-check', '--no-deps', *wheels])",
        "        run_checked([python, '-m', 'pip', 'install',",
        "                     '--disable-pip-version-check', '-r',",
        "                     str(root / REQUIREMENTS)])",
        "        runner = root / '_inner_runner.py'",
        "        runner.write_text(INNER_RUNNER)",
        "        inner = subprocess.run([python, '-B', str(runner), str(root)],",
        "                               capture_output=True, text=True,",
        "                               timeout=MAX_WALL_SECONDS * CONDITIONS + 3600)",
        "        if inner.returncode != 0:",
        "            detail = (inner.stderr or inner.stdout or '')[-1800:]",
        "            failure = {'type': 'InnerRunnerFailure',",
        "                       'message': 'INNER_RUNNER_EXIT_' + str(inner.returncode)",
        "                                  + '\\n' + detail}",
        "    except BaseException as error:",
        "        failure = {'type': type(error).__name__, 'message': str(error)[:2000]}",
        "    results_dir = results",
        "    if failure is None:",
        "        # the body wrote result.json and its sidecar; verify them and leave",
        "        # them alone, so a detected failure below can never overwrite a",
        "        # completed result",
        "        try:",
        "            raw = (results_dir / 'result.json').read_bytes()",
        "            sidecar = (results_dir / 'result.json.sha256').read_text().strip()",
        "            if hashlib.sha256(raw).hexdigest() != sidecar:",
        "                failure = {'type': 'ResultMismatch',",
        "                           'message': 'RESULT_SHA_MISMATCH'}",
        "        except BaseException as error:",
        "            failure = {'type': 'DeliveryIncomplete',",
        "                       'message': 'RESULT_MARKER_MISSING:' + str(error)[:200]}",
        "    if failure is not None:",
        "        if (results_dir / 'result.json').is_file():",
        "            preserved = (results_dir / 'result.json').read_bytes()",
        "            (results_dir / 'result_partial.json').write_bytes(preserved)",
        "        report = {'schema': RESULT_SCHEMA, 'job': job,",
        "                  'status': 'WORKER_FAILED', 'failure': failure,",
        "                  'artifacts': [], 'measurements': None}",
        "        raw = (json.dumps(report, sort_keys=True, indent=2,",
        "                          allow_nan=False) + '\\n').encode('utf-8')",
        "        (results_dir / 'result.json').write_bytes(raw)",
        "        (results_dir / 'result.json.sha256').write_text(",
        "            hashlib.sha256(raw).hexdigest() + '\\n')",
        "        (results_dir / 'failure.json').write_text(",
        "            json.dumps({'schema': FAILURE_SCHEMA, 'job': job,",
        "                        'failure': failure}, sort_keys=True, indent=2) + '\\n')",
        "    import boto3",
        "    s3 = boto3.client('s3', region_name=region)",
        "    uploaded = upload_results(s3, bucket, results_dir)",
        "    print(json.dumps({'worker_status': ('REMOTE_FAILED' if failure is not None",
        "                                         else 'REMOTE_FINISHED'),",
        "                      'artifacts': len(uploaded['artifacts']),",
        "                      'result_uploaded': uploaded['result']}))",
        "    if failure is not None:",
        "        raise SystemExit(1)",
        "",
        "",
        "if __name__ == '__main__':",
        "    main()",
        "",
    ])


class FaceProvider(candidate.CandidateProvider):
    """The proven provider lifecycle, bound to this pilot's worker and schemas."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.worker_name = WORKER_NAME
        self.result_schema = RESULT_SCHEMA
        self.failure_statuses = ("WORKER_FAILED", "FACE_WORKER_FAILED",
                                 "REMOTE_WORKER_FAILED")

    def _worker_config(self, bucket):
        return {"schema": "cas.cube-face-worker-config/1",
                "job": self.job, "bucket": bucket, "region": self.region,
                "conditions": list(FROZEN_CONDITIONS),
                "organization_per_condition": dict(FROZEN_ORGANIZATION),
                "cue_per_condition": dict(FROZEN_CUES),
                "batch_size": FROZEN_BATCH_SIZE,
                "seed": FROZEN_SEED, "encoder_seed": FROZEN_ENCODER_SEED,
                "learning_rate": FROZEN_LEARNING_RATE,
                "panel_items": FROZEN_PANEL_ITEMS,
                "events_per_condition": FROZEN_EVENTS_PER_CONDITION,
                "max_wall_seconds_per_condition":
                    FROZEN_MAX_WALL_SECONDS_PER_CONDITION,
                "authority_sha256": self._authority_sha256()}


def build_face_package(output, *, source_sha, git_bytes_fn=None, git_paths_fn=None):
    """The source package for this pilot, through the existing package builder."""
    from aws import graph_training_curriculum_launch as curriculum
    from aws.graph_training_candidate_launch import package_data_files
    return build_package(
        output, source_sha=source_sha,
        git_bytes_fn=git_bytes_fn or curriculum.git_bytes,
        git_paths_fn=git_paths_fn or curriculum.git_tree_paths,
        worker_name=WORKER_NAME, worker_source=render_worker(),
        experiment=EXPERIMENT, package_schema=PACKAGE_SCHEMA, design=DESIGN,
        receipt_schema=RECEIPT_SCHEMA,
        extra_files=package_data_files())


def validate_owner_authorization(path):
    document = json.loads(Path(path).read_bytes())
    require(document.get("schema") == "cas-cube-face-owner-authorization/1",
            "FACE_OWNER_AUTHORIZATION_SCHEMA")
    require(document.get("owner_instruction_raw"), "FACE_OWNER_INSTRUCTION_REQUIRED")
    return document


def execute(request, authority, provider, *, ledger_path=LEDGER_PATH,
            receipt_dir=None, owner_authorization_path=None):
    """Reuse the candidate pilot's proven lifecycle with this pilot's validators."""
    return candidate.execute(
        request, authority, provider, ledger_path=ledger_path,
        receipt_dir=receipt_dir,
        owner_authorization_path=owner_authorization_path,
        validate_request_fn=validate_request,
        validate_authority_fn=validate_authority)


def plan_only():
    return {"schema": SCHEMA, "status": "PLAN_ONLY_NOT_EXECUTED",
            "experiment": EXPERIMENT, "design": DESIGN,
            "conditions": list(FROZEN_CONDITIONS),
            "reservation_created": False, "provider_calls": 0,
            "boundary": ("No provider client, reservation, model import or output "
                         "mutation occurred.")}


def main(argv=None):
    import argparse
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
               ("request", "request_sha256", "authority", "authority_sha256",
                "receipt_dir")), "EXPLICIT_REGISTERED_INPUTS_REQUIRED")
    request_raw = Path(arguments.request).read_bytes()
    authority_raw = Path(arguments.authority).read_bytes()
    require(digest(request_raw) == arguments.request_sha256,
            "REQUEST_FILE_HASH_MISMATCH")
    require(digest(authority_raw) == arguments.authority_sha256,
            "AUTHORITY_FILE_HASH_MISMATCH")
    request = json.loads(request_raw)
    authority = json.loads(authority_raw)
    validate_request(request)
    validate_authority(authority)
    session_clients = candidate._clients(arguments.profile)
    provider = FaceProvider(
        job=request["job"], source_sha=request["source_sha"],
        archive_sha256=request["archive_sha256"],
        manifest_sha256=request["manifest_sha256"], ledger_path=LEDGER_PATH,
        clients=session_clients, client_error=candidate._client_error(),
        source_archive=candidate._locate_archive(request["archive_sha256"]))
    result = execute(request, authority, provider, ledger_path=LEDGER_PATH,
                     receipt_dir=arguments.receipt_dir,
                     owner_authorization_path=arguments.owner_authorization)
    print(json.dumps({"status": result["status"], "stages": result["stages"],
                      "completed_deliverable": result["completed_deliverable"]},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
