"""The checked-component pilot launcher: the curriculum machinery, bound to this run.

This is a **candidate-specific binding**, not another general-purpose launcher. It
reuses the existing curriculum launcher's machinery unchanged — evidence
directories, canonical serialisation, the git-object package builder, the resource
plan and reservation scope, the provider lifecycle (preflight, one reservation,
launch, wait, collect, cleanup with verified collection before evidence deletion) —
and changes only what the new experiment requires:

* its own job pattern, request/authority/package/result schemas and entrypoint;
* its own worker script, which calls
  ``cas_meta2.graph_teaching.candidate_experiment.launch``;
* its own worker config (two conditions, 64 updates each, seed 20260909, the
  44-question probe), supplied through the provider's ``_worker_config`` hook.

The historical curriculum profile is untouched: it keeps its own constants,
schemas, worker and tests. The resource plan is carried forward unchanged, which
is the ``$7.00`` option the owner chose.

Execution remains gated: ``plan_only`` is the default, and ``execute`` needs a
hash-bound request plus an owner authority record.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from aws.graph_training_curriculum_launch import (  # reused machinery
    HEX40, HEX64, LEDGER_PATH, OWNER_AUTHORIZATION_PATH, PILOT, RESOURCE_PLAN,
    RESERVATION_USD, ROOT, WORKER_REQUIREMENTS, WORKER_WHEEL_DIR,
    CurriculumProvider, build_package, canonical, collection_is_verified, digest,
    prepare_evidence, read_ledger, require, scope, validate_preflight,
    validate_reservation_scope, validate_reserved_transition, write_evidence)
from aws import run_evidence  # RUN_EVIDENCE_PRESERVATION_001

SCHEMA = "cas-graph-training-candidate-launch/1"
REQUEST_SCHEMA = "cas-graph-training-candidate-launch-request/1"
AUTHORITY_SCHEMA = "cas-graph-training-candidate-launch-authority/1"
PACKAGE_SCHEMA = "cas-graph-training-candidate-source-package/1"
RECEIPT_SCHEMA = "cas-graph-training-candidate-package-receipt/1"
RESULT_SCHEMA = "cas-graph-training-candidate-result/1"
WORKER_NAME = "graph6_candidate_worker.py"

JOB_PATTERN = r"cas-meta2-graph6cand-\d{14}-[a-f0-9]{8}"

EXPERIMENT = {"profile": "graph_training_candidate_component_pilot",
              "entrypoint": "cas_meta2.graph_teaching.candidate_experiment.launch"}

# The frozen design of AUTHORIZATION_REQUEST_001: two conditions, 64 updates
# each, matched initial weights, one common 44-question probe. Sealed splits and
# any other experiment's records are never read.
FROZEN_CONDITIONS = ("checked_component_teaching", "final_answer_only")
FROZEN_UPDATES_PER_CONDITION = 64
FROZEN_TOTAL_UPDATES = FROZEN_UPDATES_PER_CONDITION * len(FROZEN_CONDITIONS)
FROZEN_SEED = 20260909
FROZEN_ENCODER_SEED = 20260909
FROZEN_ORDERING_MODE = "declared"
FROZEN_PROBE_QUESTIONS = 44
FROZEN_CHECKPOINTS = ("final",)
FROZEN_ARM = "cas"
FROZEN_LEARNING_RATE = 0.003
FROZEN_MAX_WALL_SECONDS = 600.0
FROZEN_BUCKET_PREFIX = "cas-meta2-graph6cand"
RECEIPT_PREFIX = "graph6cand_"

DESIGN = {
    "launch_enabled": False,
    "training": True,
    "arms": [FROZEN_ARM],
    "conditions": list(FROZEN_CONDITIONS),
    "updates_per_condition": FROZEN_UPDATES_PER_CONDITION,
    "total_optimizer_steps": FROZEN_TOTAL_UPDATES,
    "seed": FROZEN_SEED,
    "encoder_seed": FROZEN_ENCODER_SEED,
    "ordering_mode": FROZEN_ORDERING_MODE,
    "probe_questions": FROZEN_PROBE_QUESTIONS,
    "checkpoints": list(FROZEN_CHECKPOINTS),
    "learning_rate": FROZEN_LEARNING_RATE,
    "max_wall_seconds_per_condition": FROZEN_MAX_WALL_SECONDS,
    "reservation_usd": RESERVATION_USD,
}


def validate_request(request):
    require(type(request) is dict and request.get("schema") == REQUEST_SCHEMA,
            "CANDIDATE_REQUEST_SCHEMA")
    require(set(request) == {"schema", "job", "source_sha", "archive_sha256",
                             "manifest_sha256", "launch_authorized"},
            "CANDIDATE_REQUEST_FIELDS")
    require(type(request["job"]) is str and re.fullmatch(JOB_PATTERN, request["job"]),
            "CANDIDATE_REQUEST_JOB")
    require(type(request["source_sha"]) is str and bool(HEX40.fullmatch(request["source_sha"])),
            "CANDIDATE_REQUEST_SOURCE_SHA")
    for key in ("archive_sha256", "manifest_sha256"):
        require(type(request[key]) is str and bool(HEX64.fullmatch(request[key])),
                "CANDIDATE_REQUEST_HASH:" + key)
    require(request["launch_authorized"] is False, "CANDIDATE_REQUEST_INERT")
    return request


def validate_authority(authority):
    require(type(authority) is dict and authority.get("schema") == AUTHORITY_SCHEMA,
            "CANDIDATE_AUTHORITY_SCHEMA")
    require(set(authority) == {
        "schema", "job", "source_sha", "archive_sha256", "manifest_sha256",
        "owner_authorization_sha256", "conditions", "updates_per_condition",
        "total_optimizer_steps", "seed", "encoder_seed", "ordering_mode",
        "probe_questions", "checkpoints", "learning_rate",
        "max_wall_seconds_per_condition", "reservation_usd"},
        "CANDIDATE_AUTHORITY_FIELDS")
    require(type(authority["job"]) is str and re.fullmatch(JOB_PATTERN, authority["job"]),
            "CANDIDATE_AUTHORITY_JOB")
    require(type(authority["source_sha"]) is str and bool(HEX40.fullmatch(authority["source_sha"])),
            "CANDIDATE_AUTHORITY_SOURCE_SHA")
    for key in ("archive_sha256", "manifest_sha256", "owner_authorization_sha256"):
        require(type(authority[key]) is str and bool(HEX64.fullmatch(authority[key])),
                "CANDIDATE_AUTHORITY_HASH:" + key)
    require(list(authority["conditions"]) == list(FROZEN_CONDITIONS),
            "CANDIDATE_AUTHORITY_CONDITIONS_FROZEN")
    require(authority["updates_per_condition"] == FROZEN_UPDATES_PER_CONDITION,
            "CANDIDATE_AUTHORITY_UPDATES_FROZEN")
    require(authority["total_optimizer_steps"] == FROZEN_TOTAL_UPDATES,
            "CANDIDATE_AUTHORITY_TOTAL_STEPS_FROZEN")
    require(authority["seed"] == FROZEN_SEED, "CANDIDATE_AUTHORITY_SEED_FROZEN")
    require(authority["encoder_seed"] == FROZEN_ENCODER_SEED,
            "CANDIDATE_AUTHORITY_ENCODER_SEED_FROZEN")
    require(authority["ordering_mode"] == FROZEN_ORDERING_MODE,
            "CANDIDATE_AUTHORITY_ORDERING_FROZEN")
    require(authority["probe_questions"] == FROZEN_PROBE_QUESTIONS,
            "CANDIDATE_AUTHORITY_PROBE_FROZEN")
    require(list(authority["checkpoints"]) == list(FROZEN_CHECKPOINTS),
            "CANDIDATE_AUTHORITY_CHECKPOINTS_FROZEN")
    require(authority["learning_rate"] == FROZEN_LEARNING_RATE,
            "CANDIDATE_AUTHORITY_BUDGET:learning_rate")
    require(authority["max_wall_seconds_per_condition"] == FROZEN_MAX_WALL_SECONDS,
            "CANDIDATE_AUTHORITY_BUDGET:max_wall_seconds_per_condition")
    require(authority["reservation_usd"] == RESERVATION_USD,
            "CANDIDATE_AUTHORITY_RESERVATION")
    return authority


def plan_only(request=None, authority=None):
    if request is not None:
        validate_request(request)
    if authority is not None:
        validate_authority(authority)
    return {"schema": SCHEMA, "status": "PLAN_ONLY_NOT_EXECUTED",
            "experiment": EXPERIMENT, "design": DESIGN,
            "resource_plan": scope(),
            "job_pattern": JOB_PATTERN, "worker_script": WORKER_NAME,
            "reservation_created": False, "provider_calls": 0,
            "boundary": ("no provider client, reservation, model import, or output "
                         "mutation occurred; execution needs a hash-bound request "
                         "and an owner authority record")}


def render_worker():
    """The in-package worker: two conditions, real checkpoints, verified delivery.

    Built on the **proven** curriculum worker's scaffolding, because the first
    version of this worker was not and it cost a reservation: attempt 005 ran the
    training logic under the *system* python, which has no torch, and died in two
    minutes with ``ModuleNotFoundError: No module named 'torch'``. The order here
    is the order that has actually worked on this instance type:

    1. outer process (system python, which has the AWS SDK): create a venv, install
       ``torch`` from the CUDA wheel index, install the two frozen wheels and the
       requirements;
    2. run the training body as a *subprocess* under that venv's python;
    3. upload from the OUTER process, so the training venv never needs boto3
       (attempt 003 of the curriculum died on exactly that, after the whole run had
       succeeded).

    Delivery follows the same contract the launcher's collector enforces:
    artifacts under ``results/artifacts/`` with a manifest at
    ``results/artifacts/manifest.json``, the result declared in the envelope's
    ``artifacts`` list (an empty list would let verified collection delete the
    checkpoints uncollected), ``results/result.json.sha256`` beside the result,
    and ``results/result.json`` **last**, because it is the completion marker.
    """
    inner_lines = [
        "import hashlib",
        "import json",
        "import sys",
        "from pathlib import Path",
        "ROOT = Path(sys.argv[1])",
        "sys.path.insert(0, str(ROOT / 'research/CAS_META_2_COMPOSITION'))",
        "from cas_meta2.graph_teaching import candidate_experiment as ce",
        "from cas_meta2.teaching_cycle import gpu_adapter",
        "from cas_meta2.graph_teaching.real_framework import (",
        "    build_encoder, build_graph_training_framework, GraphLearner)",
        "from cas_meta2.graph_teaching import adapter",
        "CONFIG = json.loads((ROOT / 'config.json').read_bytes())",
        "RESULTS = ROOT / 'results'",
        "ARTIFACTS = RESULTS / 'artifacts'",
        "ARTIFACTS.mkdir(parents=True, exist_ok=True)",
        "",
        "",
        "# The outer worker has its own copy; this one runs under the venv python.",
        "def sha256_file(path):",
        "    digest = hashlib.sha256()",
        "    with open(path, 'rb') as stream:",
        "        for block in iter(lambda: stream.read(1 << 20), b''):",
        "            digest.update(block)",
        "    return digest.hexdigest()",
        "",
        "",
        "torch, device = gpu_adapter._cuda()",
        "inputs = ce.build_inputs(ordering_mode=CONFIG['ordering_mode'])",
        "records, probe = inputs['records'], inputs['probe']",
        "publics = [adapter.public_records(record, CONFIG['arm'])['public']",
        "           for record in records + probe]",
        "encoder = build_encoder(torch, publics, d_model=64,",
        "                        seed=CONFIG['encoder_seed'], device=device)",
        "condition_order = list(CONFIG['conditions'])",
        "staged = []",
        "",
        "def framework_factory(seed):",
        "    torch.manual_seed(seed)",
        "    framework = build_graph_training_framework(",
        "        torch, device, seed=CONFIG['encoder_seed'], encoder=encoder)",
        "    model = framework.build_decompose_model(seed=seed)",
        "    return framework, model",
        "",
        "def learner_factory(*, framework, model, arm, records, layout):",
        "    tasks = [layout[record['record_id']] for record in records]",
        "    learner = GraphLearner(torch, framework, tasks, device,",
        "                           CONFIG['learning_rate'])",
        "    # conditions run in the frozen order, so the tag follows that order",
        "    learner.condition_tag = condition_order.pop(0)",
        "    return learner",
        "",
        "def checkpoint_writer(learner, identity):",
        "    path = ARTIFACTS / ('checkpoint_%s.pt' % learner.condition_tag)",
        "    torch.save({'schema': 'cas-graph-training-candidate-checkpoint/1',",
        "                'condition': learner.condition_tag,",
        "                'identity': identity,",
        "                # the order the learner's own identity digests them in",
        "                'parameter_order': ce.parameter_order(learner.module),",
        "                'state': learner.module.state_dict()}, str(path))",
        "    staged.append({'name': path.name,",
        "                   'condition': learner.condition_tag,",
        "                   'identity': identity, 'bytes': path.stat().st_size,",
        "                   'sha256': sha256_file(path)})",
        "    return {'path': str(path), 'identity': identity,",
        "            'sha256': sha256_file(path)}",
        "",
        "def checkpoint_verifier(saved, identity):",
        "    loaded = torch.load(saved['path'], map_location='cpu',",
        "                        weights_only=True)",
        "    # Read back from disk and recompute with the learner's own rule. Hashing",
        "    # the parameter names too could never equal the identity, and the run",
        "    # would then fail closed after its whole budget was already spent.",
        "    recomputed = ce.state_digest(loaded['state'], loaded['parameter_order'])",
        "    return (recomputed == identity and loaded['identity'] == identity)",
        "",
        "authorization = {'owner_go': True, 'run_id': CONFIG['job'],",
        "                 'authority_sha256': CONFIG['authority_sha256']}",
        "result = ce.launch(run_id=CONFIG['job'], records=records, probe=probe,",
        "                   groups=inputs['groups'],",
        "                   framework_factory=framework_factory,",
        "                   learner_factory=learner_factory,",
        "                   authorization=authorization,",
        "                   checkpoint_writer=checkpoint_writer,",
        "                   checkpoint_verifier=checkpoint_verifier,",
        "                   view_id=CONFIG['view_id'],",
        "                   ordering_mode=CONFIG['ordering_mode'])",
        "def write_json(path, payload):",
        "    path.write_text(json.dumps(payload, sort_keys=True, indent=2,",
        "                               allow_nan=False) + '\\n')",
        "",
        "write_json(RESULTS / 'measurements.json', result)",
        "write_json(ARTIFACTS / 'manifest.json',",
        "           {'schema': 'cas-graph-training-candidate-artifact-manifest/1',",
        "            'job': CONFIG['job'], 'artifacts': staged})",
        "print(json.dumps({'inner_status': 'MEASUREMENTS_WRITTEN',",
        "                  'conditions': list(result['results']),",
        "                  'artifacts': len(staged)}))",
    ]
    runner_block = ",\n".join(repr(line) for line in inner_lines)
    return "\n".join([
        '"""Rendered candidate worker: the checked-component pilot, one run.',
        "",
        "Environment and delivery follow the proven curriculum worker, step for",
        "step. Attempt 005 died here because the training body ran under the system",
        'python, which has no torch."""',
        "import hashlib",
        "import json",
        "import shutil",
        "import subprocess",
        "import sys",
        "from pathlib import Path",
        "",
        "RESULT_SCHEMA = %r" % RESULT_SCHEMA,
        "FAILURE_SCHEMA = 'cas-graph-training-candidate-failure/1'",
        "DELIVERY_SCHEMA = 'cas-graph-training-candidate-delivery/1'",
        "ARTIFACT_MANIFEST_KEY = 'results/artifacts/manifest.json'",
        "MAX_WALL_SECONDS = %.1f" % FROZEN_MAX_WALL_SECONDS,
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
        "def build_envelope(job, failure, measurements, artifacts):",
        "    if failure is not None:",
        "        return {'schema': RESULT_SCHEMA, 'job': job,",
        "                'status': 'WORKER_FAILED', 'artifacts': [],",
        "                'failure': failure,",
        "                'measurements': None}",
        "    return {'schema': RESULT_SCHEMA, 'job': job,",
        "            'status': 'REMOTE_FINISHED', 'failure': None,",
        "            # Declared, so verified collection collects them instead of",
        "            # deleting a bucket whose checkpoints were never delivered.",
        "            'artifacts': [{'name': entry['name'],",
        "                           'condition': entry.get('condition'),",
        "                           'identity': entry.get('identity'),",
        "                           'bytes': entry.get('bytes'),",
        "                           'sha256': entry.get('sha256')}",
        "                          for entry in artifacts],",
        "            'measurements': measurements}",
        "",
        "",
        "def upload_results(s3, bucket, results):",
        "    \"\"\"Artifacts and manifest, then the sidecar, then the result LAST.",
        "",
        "    Runs in the OUTER process (system python, which has the AWS SDK), so the",
        "    training venv never needs boto3. result.json is the marker the launcher",
        "    waits for, so its presence means every artifact is already there.\"\"\"",
        "    uploaded = {'artifacts': [], 'manifest': False, 'result': False,",
        "                'result_sha256': False}",
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
        "            uploaded[name] = True",
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
        "                               timeout=MAX_WALL_SECONDS * CONDITIONS + 2400)",
        "        if inner.returncode != 0:",
        "            detail = (inner.stderr or inner.stdout or '')[-1800:]",
        "            failure = {'type': 'InnerRunnerFailure',",
        "                       'message': 'INNER_RUNNER_EXIT_' + str(inner.returncode)",
        "                                  + '\\n' + detail}",
        "    except BaseException as error:",
        "        failure = {'type': type(error).__name__, 'message': str(error)[:2000]}",
        "    artifacts_dir = results / 'artifacts'",
        "    manifest = read_json(artifacts_dir / 'manifest.json', {}) or {}",
        "    measurements = read_json(results / 'measurements.json')",
        "    staged = manifest.get('artifacts') or []",
        "    if failure is None and measurements is None:",
        "        failure = {'type': 'DeliveryIncomplete',",
        "                   'message': 'MEASUREMENTS_MISSING_AFTER_INNER_RUN'}",
        "    envelope = build_envelope(job, failure, measurements, staged)",
        "    raw = (json.dumps(envelope, sort_keys=True, indent=2,",
        "                      allow_nan=False) + '\\n').encode('utf-8')",
        "    (results / 'result.json').write_bytes(raw)",
        "    (results / 'result.json.sha256').write_text(",
        "        hashlib.sha256(raw).hexdigest() + '\\n')",
        "    if failure is not None:",
        "        # NEVER destroy a result the run already produced: keep it, and record",
        "        # the failure beside it. The result marker is written even on failure,",
        "        # because the launcher's wait loop only watches result.json: a failure",
        "        # that reported itself nowhere left attempt 004 idling until timeout.",
        "        (results / 'failure.json').write_text(",
        "            json.dumps({'schema': FAILURE_SCHEMA, 'job': job,",
        "                        'failure': failure}, sort_keys=True, indent=2) + '\\n')",
        "        if measurements is not None:",
        "            (results / 'result_partial.json').write_text(",
        "                json.dumps(measurements, sort_keys=True, indent=2,",
        "                           allow_nan=False) + '\\n')",
        "    import boto3",
        "    s3 = boto3.client('s3', region_name=region)",
        "    uploaded = upload_results(s3, bucket, results)",
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


def package_data_files(root=None):
    """Repository data files this pilot's code reads at run time.

    Derived from the constants the deployed code itself resolves, so the package
    cannot drift from where the runtime looks:

    - ``cube_node.pinned_bundle_path()`` — the pinned cube bundle the graph
      operations and the whole-bundle compile read. REQUIRED: without it the
      deployed worker fails closed with ``CUBE_BUNDLE_FILE_MISSING``.
    - ``verified_teaching.pinned_fixture_path()`` — the authored fixture the
      on-instance compile compares itself against. Optional at run time
      (``compare_with_fixture`` reports ``fixture_present: False`` when absent);
      carried so the delivered report contains the comparison.

    Both sit under ``records/``, which is not among ``SOURCE_DIRS``. The package
    rehearsal caught this; no paid attempt had to.
    """
    from cas_meta2.graph_teaching import cube_node, verified_teaching
    base = Path(root or ROOT).resolve()
    names = []
    for path in (cube_node.pinned_bundle_path(),
                 verified_teaching.pinned_fixture_path()):
        relative = Path(path).resolve().relative_to(base).as_posix()
        names.append(PILOT + relative)
    return tuple(sorted(names))


def build_candidate_package(output, *, source_sha, git_bytes_fn=None,
                            git_paths_fn=None):
    """The source package for this pilot, through the existing package builder."""
    from aws import graph_training_curriculum_launch as curriculum
    return build_package(
        output, source_sha=source_sha,
        git_bytes_fn=git_bytes_fn or curriculum.git_bytes,
        git_paths_fn=git_paths_fn or curriculum.git_tree_paths,
        worker_name=WORKER_NAME, worker_source=render_worker(),
        experiment=EXPERIMENT, package_schema=PACKAGE_SCHEMA, design=DESIGN,
        receipt_schema=RECEIPT_SCHEMA, extra_files=package_data_files())


class CandidateProvider(CurriculumProvider):
    """The same provider lifecycle, bound to this pilot's worker and schemas."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.worker_name = WORKER_NAME
        self.result_schema = RESULT_SCHEMA
        # The candidate worker writes WORKER_FAILED; the inherited word alone
        # would report a failed run as REMOTE_FINISHED.
        self.failure_statuses = ("WORKER_FAILED", "REMOTE_WORKER_FAILED")

    def _worker_config(self, bucket):
        return {"schema": "cas-graph-training-candidate-worker-config/1",
                "job": self.job, "bucket": bucket, "region": self.region,
                "arm": FROZEN_ARM, "view_id": "view_context",
                "ordering_mode": FROZEN_ORDERING_MODE,
                "conditions": list(FROZEN_CONDITIONS),
                "updates_per_condition": FROZEN_UPDATES_PER_CONDITION,
                "seed": FROZEN_SEED, "encoder_seed": FROZEN_ENCODER_SEED,
                "learning_rate": FROZEN_LEARNING_RATE,
                "probe_questions": FROZEN_PROBE_QUESTIONS,
                "authority_sha256": self._authority_sha256()}

    def set_authority_sha256(self, value):
        require(type(value) is str and bool(HEX64.fullmatch(value)),
                "CANDIDATE_PROVIDER_AUTHORITY_HASH")
        self._authority = value
        return value

    def _authority_sha256(self):
        require(getattr(self, "_authority", None), "CANDIDATE_PROVIDER_AUTHORITY_HASH")
        return self._authority

    def collect(self, job):
        """Collect, even when the run died before it could read a result.

        The inherited collect requires a result object, which a terminated
        instance never produced (attempt 004: CURRICULUM_COLLECT_STATE, so nothing
        was collected). Here a missing result collects whatever ``results/``
        objects exist instead, reports the reason, and leaves the bucket in place
        because collection is not verified.
        """
        if self._result_raw is not None:
            return super().collect(job)
        self.calls.append("collect")
        require(job == self.job and self._instance_id is not None,
                "CANDIDATE_COLLECT_STATE")
        s3 = self.clients["s3"]
        bucket = self._resources["bucket"]
        collected = {"result": None, "result_sha256": None, "artifacts": [],
                     "artifacts_collected": [], "artifacts_missing": [],
                     "artifacts_available": False,
                     "reason": "NO_RESULT_OBJECT_COLLECTED_WHAT_EXISTS"}
        listing = s3.list_objects_v2(Bucket=bucket)
        for entry in sorted(listing.get("Contents", []), key=lambda item: item["Key"]):
            key = entry["Key"]
            if not key.startswith("results/"):
                continue
            name = key.split("/", 1)[1]
            try:
                body = self._read_body(s3.get_object(Bucket=bucket, Key=key)["Body"],
                                       256 * 1024**2)
            except Exception:                     # noqa: BLE001 - best effort
                continue
            receipt = write_evidence(self._evidence / ("remote_" + name), body)
            collected["artifacts_collected"].append(
                {"key": key, "path": receipt["path"], "sha256": receipt["sha256"],
                 "bytes": receipt["bytes"]})
        return collected


def execute(request, authority, provider, *, ledger_path=LEDGER_PATH,
            receipt_dir=None, owner_authorization_path=None,
            validate_request_fn=None, validate_authority_fn=None,
            evidence_contract=None):
    """One reservation, one launch, verified collection, then cleanup.

    The two validators are injectable so a later experiment can reuse this proven
    lifecycle with its own schema and bounds instead of copying it. They default to
    this pilot's own validators, so nothing about this pilot changes.

    ``evidence_contract`` is the experiment's pre-run evidence requirement
    (RUN_EVIDENCE_PRESERVATION_001): frozen before the worker starts and held here
    independently of anything the worker uploads.
    """
    validate_request_fn = validate_request_fn or validate_request
    validate_authority_fn = validate_authority_fn or validate_authority
    validate_request_fn(request)
    validate_authority_fn(authority)
    owner_path = (Path(owner_authorization_path) if owner_authorization_path is not None
                  else OWNER_AUTHORIZATION_PATH)
    require(authority["owner_authorization_sha256"] == digest(owner_path.read_bytes()),
            "OWNER_AUTHORIZATION_RECORD_MISMATCH")
    require(authority["job"] == request["job"]
            and authority["source_sha"] == request["source_sha"],
            "REQUEST_AUTHORITY_MISMATCH")
    for key in ("archive_sha256", "manifest_sha256"):
        require(authority[key] == request[key], "REQUEST_AUTHORITY_HASH_MISMATCH:" + key)
    require(provider is not None, "PROVIDER_ADAPTER_REQUIRED")
    # Fail closed BEFORE the reservation. Attempt 003 spent its $7.00 reservation
    # and then failed inside launch() on a source archive the caller never
    # supplied; this check makes that impossible to repeat.
    archive = getattr(provider, "source_archive", None)
    require(archive is not None, "CANDIDATE_SOURCE_ARCHIVE_REQUIRED_BEFORE_RESERVATION")
    archive_path = Path(archive)
    require(archive_path.is_file(),
            "CANDIDATE_SOURCE_ARCHIVE_MISSING_BEFORE_RESERVATION:" + str(archive_path))
    require(digest(archive_path.read_bytes()) == request["archive_sha256"],
            "CANDIDATE_SOURCE_ARCHIVE_HASH_BEFORE_RESERVATION")
    started = time.monotonic()
    ledger_before = read_ledger(ledger_path)
    reservation_scope = validate_reservation_scope(ledger_before)
    require(not any(entry["job"] == request["job"]
                    for entry in ledger_before["ledger"]["reservations"]),
            "JOB_ALREADY_RESERVED_NO_AUTOMATIC_RETRY")
    directory = prepare_evidence(receipt_dir if receipt_dir is not None else
                                 Path(ledger_path).parent / (RECEIPT_PREFIX + request["job"]))
    write_evidence(directory / "intent.json", canonical({
        "schema": SCHEMA, "request": request, "authority": authority,
        "ledger_before": ledger_before, "automatic_retries": 0}))
    # The pre-run evidence requirement, frozen before the worker starts and held
    # here independently of anything the worker later uploads
    # (RUN_EVIDENCE_PRESERVATION_001).
    if evidence_contract is not None:
        require(evidence_contract.get("schema") == run_evidence.CONTRACT_SCHEMA,
                "EVIDENCE_CONTRACT_SCHEMA")
        if authority.get("evidence_contract_sha256"):
            require(run_evidence.contract_digest(evidence_contract)
                    == authority["evidence_contract_sha256"],
                    "EVIDENCE_CONTRACT_AUTHORITY_MISMATCH")
        write_evidence(directory / "evidence_contract.json",
                       canonical(evidence_contract))
    provider.configure_evidence(directory, evidence_contract)
    if hasattr(provider, "set_authority_sha256"):
        provider.set_authority_sha256(authority["owner_authorization_sha256"])
    preflight = reservation = ledger_after = launched = collected = None
    reservation_valid, reservation_error = False, None
    verified = False
    cleanup = {"complete": False, "failures": ["NOT_ATTEMPTED"]}
    outcome = {}
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
        outcome = provider.wait(request["job"],
                                timeout=RESOURCE_PLAN["instance_seconds_max"])
        collected = provider.collect(request["job"])
        receipt = (collected or {}).get("receiver_receipt")
        provider._receipt = receipt                 # what the deletion decision reads
        verified = bool(receipt and receipt.get("collection") == "COMPLETE_VERIFIED")
        status = ("AWS_CANDIDATE_FINISHED"
                  if outcome.get("worker_status") == "REMOTE_FINISHED"
                  else "AWS_CANDIDATE_FAILED")
    except BaseException as error:
        status = "AWS_CANDIDATE_LAUNCH_FAILED"
        outcome = {"exception_type": type(error).__name__,
                   "exception": str(error)[:2000]}
        if not reservation_valid:
            reservation_error = error
        try:
            write_evidence(directory / "failure.json", canonical(outcome))
        except Exception as record_error:
            outcome["failure_record_error"] = (type(record_error).__name__ + ":"
                                               + str(record_error)[:1000])
    finally:
        try:
            cleanup = provider.cleanup(request["job"], collection_verified=verified)
        except BaseException as error:
            cleanup = {"complete": False, "failures": [
                "CLEANUP_EXCEPTION:" + type(error).__name__ + ":" + str(error)[:2000]]}
    byte_verdict = (collected or {}).get("byte_integrity") or {}
    completeness_verdict = (collected or {}).get("measurement_completeness") or {}
    compute_state = "COMPLETE" if cleanup.get("complete") else "INCOMPLETE"
    stages = run_evidence.stage_states(
        execution=("FINISHED" if outcome.get("worker_status") == "REMOTE_FINISHED"
                   else "FAILED"),
        byte_verdict=byte_verdict, completeness_verdict=completeness_verdict,
        backup=None, compute={"state": compute_state},
        retention=getattr(provider, "_retention", None),
        measurement_keys=("results/artifacts/measurements.json",
                          "results/artifacts/readout.json"),
        document=evidence_contract)
    result = {"schema": SCHEMA, "status": status, "job": request["job"],
              "request": request, "authority": authority,
              "ledger_before": ledger_before, "ledger_after": ledger_after,
              "reservation_scope": reservation_scope, "reservation": reservation,
              "preflight": preflight, "launch": launched, "outcome": outcome,
              "collected": collected, "receipt_dir": str(directory),
              "cleanup": cleanup, "elapsed_seconds": time.monotonic() - started,
              "evidence_contract": ({"profile": evidence_contract.get("profile"),
                                     "required_count":
                                         evidence_contract.get("required_count"),
                                     "sha256":
                                         run_evidence.contract_digest(evidence_contract)}
                                    if evidence_contract else None),
              "stages": stages,
              "completed_deliverable": run_evidence.completed_deliverable(
                  execution=stages["execution"], byte_verdict=byte_verdict,
                  completeness_verdict=completeness_verdict, receipt=receipt,
                  compute={"state": compute_state}, document=evidence_contract),
              "claims": {"seven_stage_program_claimed": False,
                         "component_teaching_claimed": "pending the measured result"}}
    if not cleanup.get("complete"):
        result["status"] = "AWS_CANDIDATE_FAILED"
        result["cleanup_incomplete_reason"] = cleanup.get("failures")
    write_evidence(directory / "result.json", canonical(result))
    if reservation_error is not None:
        raise reservation_error
    return result


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
    session_clients = _clients(arguments.profile)
    provider = CandidateProvider(
        job=request["job"], source_sha=request["source_sha"],
        archive_sha256=request["archive_sha256"],
        manifest_sha256=request["manifest_sha256"], ledger_path=LEDGER_PATH,
        clients=session_clients, client_error=_client_error(),
        source_archive=_locate_archive(request["archive_sha256"]))
    result = execute(request, authority, provider, ledger_path=LEDGER_PATH,
                     receipt_dir=arguments.receipt_dir,
                     owner_authorization_path=arguments.owner_authorization)
    print(json.dumps({"status": result["status"], "stages": result["stages"],
                      "completed_deliverable": result["completed_deliverable"]},
                     sort_keys=True))
    return 0


# Every client name the reused provider lifecycle asks for. The first attempt at
# this pilot failed at preflight with KeyError: 'sts' because only three of the
# five were created; a test now checks this set against the reused source.
CLIENT_NAMES = ("ec2", "s3", "iam", "sts", "pricing")


def _client_error():
    """The botocore ClientError type, without importing botocore at module level."""
    from botocore.exceptions import ClientError
    return ClientError


def _locate_archive(archive_sha256):
    """The built package's own source.zip, found by the hash the request binds.

    The candidate file's own bytes are hashed before it is accepted: some scratch
    receipts elsewhere in ``records/`` carry synthetic hashes, and a receipt field
    is not evidence about the file it points at.
    """
    for receipt in sorted((ROOT / "records").rglob("receipt.json")):
        try:
            document = json.loads(receipt.read_bytes())
        except (OSError, ValueError):
            continue
        if document.get("archive_sha256") == archive_sha256 and document.get("archive"):
            archive = Path(document["archive"])
            if archive.is_file() and digest(archive.read_bytes()) == archive_sha256:
                return archive
    raise ValueError("CANDIDATE_SOURCE_ARCHIVE_NOT_FOUND")


def _clients(profile):
    """The same client construction the working curriculum path uses.

    Two details matter and both cost a preflight failure to learn: every client
    needs the frozen region, and the **Pricing** client must be built in
    ``us-east-1`` (its only usable endpoint), or ``get_products`` answers
    ``AccessDeniedException``.
    """
    import boto3
    from botocore.config import Config
    config = Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 0})
    session = boto3.Session(profile_name=profile, region_name=RESOURCE_PLAN["region"])
    clients = {name: session.client(name, config=config) for name in CLIENT_NAMES}
    clients["pricing"] = session.client("pricing", region_name="us-east-1",
                                        config=config)
    return clients


if __name__ == "__main__":
    raise SystemExit(main())
