"""CAS_RDCJT_001: the candidate-specific entrypoint, package and worker.

This is the gap ``course.readiness_report`` named: "no versioned entrypoint, no
resource profile, no package". It closes that gap and nothing else. It does not
launch, reserve, or authorise anything.

Why a separate module rather than "reuse the launcher"
------------------------------------------------------
The proven lifecycle - reservation, launch, wait, verified collection, evidence
contract, cleanup that cannot delete before collection - is reused wholesale from
``graph_training_candidate_launch.execute``. What is NOT reused is the part that
identifies the experiment: the schemas, the job pattern, the worker name, the
result envelope and the evidence contract. Pointing the readout's launcher at a
training candidate would have produced a run whose receipt described the wrong
experiment, which is the specific failure "reuse the launcher" invites.

What this job is
----------------
ONE job trains BOTH arms - one-pass and recurrent - from ONE matched
initialization on the SAME CFC course, then reads the recurrent checkpoint at
every declared depth with its weights frozen. Both arms in one job is not a
convenience: a matched comparison whose halves ran on different instances, at
different times, from separately built frameworks, is not matched.

What this job is NOT
--------------------
* It is not a replication. ONE matched initialization is an exploratory pilot.
  The handoff's own success criterion - "a positive difference in at least two of
  three paired runs" - needs THREE jobs, and this launcher deliberately does not
  pretend one job satisfies it. ``replication_status`` says so in the envelope.
* It is not an independent application test. The panel this course teaches
  against is examined material; the fresh family panel does not exist yet. The
  evidence contract records the payload; ``experiment.panel_provenance`` records
  what it can and cannot support.
* It is not authorised. No request, no authority, no owner record, no
  reservation. ``costed_request`` prints what one job would cost and what the
  declared success criterion would cost; the owner decides.

No torch import here, no network at import time, no model.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPOSITION = HERE.parent
if str(COMPOSITION) not in sys.path:
    sys.path.insert(0, str(COMPOSITION))

from aws.graph_training_curriculum_launch import (  # noqa: E402
    HEX40, HEX64, LEDGER_PATH, RESOURCE_PLAN, RESERVATION_USD,
    WORKER_REQUIREMENTS, WORKER_WHEEL_DIR, build_package, canonical, digest,
    require)
from aws import graph_training_candidate_launch as candidate  # noqa: E402
from aws import run_evidence  # noqa: E402  RUN_EVIDENCE_PRESERVATION_001
from cas_meta2.recurrent_cjt import course as cs  # noqa: E402
from cas_meta2.recurrent_cjt import experiment as ex  # noqa: E402
from cas_meta2.recurrent_cjt import recurrence as rc  # noqa: E402

SCHEMA = "cas-recurrent-cjt-launch/1"
REQUEST_SCHEMA = "cas-recurrent-cjt-request/1"
AUTHORITY_SCHEMA = "cas-recurrent-cjt-authority/1"
PACKAGE_SCHEMA = "cas-recurrent-cjt-source-package/1"
RECEIPT_SCHEMA = "cas-recurrent-cjt-package-receipt/1"
RESULT_SCHEMA = ex.RESULT_SCHEMA
CONFIG_SCHEMA = "cas.recurrent-cjt-config/1"
OWNER_SCHEMA = "cas-recurrent-cjt-owner-authorization/1"
WORKER_NAME = "recurrent_cjt_worker.py"
JOB_PATTERN = r"cas-meta2-rdcjt-\d{14}-[a-f0-9]{8}"
CANDIDATE = "CAS_RDCJT_001"

EXPERIMENT = {
    "profile": "recurrent_cjt_depth_v0_1",
    "candidate": CANDIDATE,
    "title": "Recurrent CJT: does carrying a working state through more passes "
             "change the answer",
    "entrypoint": "cas_meta2.recurrent_cjt.experiment.run",
    "arms": list(ex.ARMS),
    "not_included": (
        "no new trainable matrices, no new answer head, no inference-time solver, "
        "no decoder, no memory system, no pass-level loss, no acceptance gate, and "
        "no change to the planner, the constructor or any active job"),
}

#: Frozen before any run. Changing one of these changes the experiment, so they
#: are bound in the authority rather than read from a config at launch time.
#: THREE declared seeds, one per paired run. This is not decoration. With a
#: single frozen seed the three jobs the criterion asks for would be bit-identical
#: - the same initialization, the same course order, the same answer three times -
#: and reporting that as "a positive difference in two of three paired runs" would
#: be reporting ONE run three times. Each job binds ONE of these in its authority,
#: and no two jobs may bind the same one.
FROZEN_SEEDS = (20260912, 20260913, 20260914)
FROZEN_SEED = FROZEN_SEEDS[0]
FROZEN_LEARNING_RATE = 0.003
FROZEN_ROUND_DEPTHS = tuple(rc.ROUND_DEPTH_SCHEDULE)
FROZEN_EVALUATION_DEPTHS = tuple(rc.EVALUATION_DEPTHS)
FROZEN_ARMS = tuple(ex.ARMS)
#: Two arms, each taking the declared course.
FROZEN_UPDATES_PER_ARM = cs.course_plan()["updates"]
FROZEN_DECISIONS_PER_ARM = cs.course_plan()["decisions"]
FROZEN_TOTAL_UPDATES = FROZEN_UPDATES_PER_ARM * len(FROZEN_ARMS)
#: The wall-clock allowance. The environment install dominates a short job, so it
#: is charged separately rather than hidden inside the training allowance.
FROZEN_MAX_WALL_SECONDS = 2400.0
FROZEN_INSTALL_ALLOWANCE_SECONDS = 600.0
FROZEN_TOTAL_WALL_CLOCK_CEILING = 3000.0


def frozen_cost():
    """The declared arithmetic for BOTH arms, derived rather than copied."""
    cost = rc.course_cost()
    one = cost["one_pass"]
    recurrent = cost["recurrent"]
    return {
        "per_arm": {"one_pass": one, "recurrent": recurrent},
        "total_optimizer_updates": FROZEN_TOTAL_UPDATES,
        "total_sample_level_core_passes": (one["sample_level_core_passes"]
                                           + recurrent["sample_level_core_passes"]),
        "ratio_recurrent_over_one_pass": round(
            recurrent["sample_level_core_passes"]
            / one["sample_level_core_passes"], 4),
        "boundary": (
            "derived planning counts, not measured GPU work. Equal teaching "
            "exposure is not equal training compute, and eight internal passes "
            "are eight sample passes and ONE optimizer update"),
    }


DESIGN = {
    "candidate": CANDIDATE,
    "title": EXPERIMENT["title"],
    "arms": list(FROZEN_ARMS),
    "seeds": list(FROZEN_SEEDS),
    "learning_rate": FROZEN_LEARNING_RATE,
    "round_depths": list(FROZEN_ROUND_DEPTHS),
    "evaluation_depths": list(FROZEN_EVALUATION_DEPTHS),
    "updates_per_arm": FROZEN_UPDATES_PER_ARM,
    "decisions_per_arm": FROZEN_DECISIONS_PER_ARM,
    "declared_cost": frozen_cost(),
    "max_wall_seconds": FROZEN_MAX_WALL_SECONDS,
    "install_allowance_seconds": FROZEN_INSTALL_ALLOWANCE_SECONDS,
    "total_wall_clock_ceiling_seconds": FROZEN_TOTAL_WALL_CLOCK_CEILING,
    "reservation_usd": RESERVATION_USD,
    "training": True,
    "what_one_job_can_support": (
        "a depth reading and a matched arm comparison from ONE initialization, on "
        "examined material"),
    "what_one_job_cannot_support": (
        "the declared success criterion. 'a positive difference in at least two of "
        "three paired runs' needs THREE jobs; one job is an exploratory pilot and "
        "is reported as one"),
    "not_included": EXPERIMENT["not_included"],
}


def seeds_already_used(record_dir):
    """Which declared seeds already have a receipt, so a repeat cannot pass.

    Three jobs on the same seed are ONE job run three times. The launcher reads
    the receipts rather than trusting the caller to remember which seeds went.
    """
    used = {}
    root = Path(record_dir)
    if not root.is_dir():
        return used
    for intent in sorted(root.glob("receipt_*/intent.json")):
        try:
            document = json.loads(intent.read_bytes())
        except (ValueError, OSError):
            continue
        authority = document.get("authority") or {}
        if authority.get("candidate") != CANDIDATE:
            continue
        seed = authority.get("seed")
        if seed is not None:
            used[int(seed)] = authority.get("job")
    return used


def require_unused_seed(seed, record_dir):
    """Refuse a seed that already has a receipt under this candidate."""
    require(int(seed) in FROZEN_SEEDS, "RDCJT_SEED_NOT_DECLARED:" + str(seed))
    used = seeds_already_used(record_dir)
    require(int(seed) not in used,
            "RDCJT_SEED_ALREADY_RUN:%d_by_%s" % (int(seed), used.get(int(seed))))
    return {"seed": int(seed), "seeds_declared": list(FROZEN_SEEDS),
            "seeds_already_used": sorted(used),
            "remaining": sorted(s for s in FROZEN_SEEDS if s not in used)}


def replication_status(jobs_completed=1):
    """How many matched pairs exist, and what that allows to be said."""
    require(int(jobs_completed) >= 0, "RDCJT_JOBS_COMPLETED")
    jobs = int(jobs_completed)
    return {
        "matched_pairs_completed": jobs,
        "matched_pairs_required_by_the_declared_criterion": 3,
        "criterion": ("a positive R8-minus-R1 difference in at least two of three "
                      "paired runs"),
        "satisfied": jobs >= 3,
        "status": ("EXPLORATORY_PILOT" if jobs < 3 else "CRITERION_EVALUABLE"),
        "note": ("one matched initialization is an exploratory pilot, not "
                 "multi-seed replication, and no number from one job may be "
                 "reported as meeting the three-run criterion"),
    }


# --------------------------------------------------------------------------
# request and authority
# --------------------------------------------------------------------------

def validate_request(request):
    require(type(request) is dict and request.get("schema") == REQUEST_SCHEMA,
            "RDCJT_REQUEST_SCHEMA")
    require(set(request) == {"schema", "job", "source_sha", "archive_sha256",
                             "manifest_sha256", "launch_authorized"},
            "RDCJT_REQUEST_FIELDS")
    require(type(request["job"]) is str
            and re.fullmatch(JOB_PATTERN, request["job"]), "RDCJT_REQUEST_JOB")
    require(type(request["source_sha"]) is str
            and bool(HEX40.fullmatch(request["source_sha"])),
            "RDCJT_REQUEST_SOURCE_SHA")
    for key in ("archive_sha256", "manifest_sha256"):
        require(type(request[key]) is str and bool(HEX64.fullmatch(request[key])),
                "RDCJT_REQUEST_HASH:" + key)
    require(request["launch_authorized"] is False, "RDCJT_REQUEST_INERT")
    return request


def validate_authority(authority):
    require(type(authority) is dict and authority.get("schema") == AUTHORITY_SCHEMA,
            "RDCJT_AUTHORITY_SCHEMA")
    require(set(authority) == {
        "schema", "job", "source_sha", "archive_sha256", "manifest_sha256",
        "owner_authorization_sha256", "candidate", "arms", "seed",
        "learning_rate", "round_depths", "evaluation_depths", "updates_per_arm",
        "decisions_per_arm", "max_wall_seconds", "reservation_usd", "training"},
        "RDCJT_AUTHORITY_FIELDS")
    require(type(authority["job"]) is str
            and re.fullmatch(JOB_PATTERN, authority["job"]), "RDCJT_AUTHORITY_JOB")
    require(type(authority["source_sha"]) is str
            and bool(HEX40.fullmatch(authority["source_sha"])),
            "RDCJT_AUTHORITY_SOURCE_SHA")
    for key in ("archive_sha256", "manifest_sha256", "owner_authorization_sha256"):
        require(type(authority[key]) is str and bool(HEX64.fullmatch(authority[key])),
                "RDCJT_AUTHORITY_HASH:" + key)
    require(authority["candidate"] == CANDIDATE, "RDCJT_AUTHORITY_CANDIDATE_FROZEN")
    require(list(authority["arms"]) == list(FROZEN_ARMS),
            "RDCJT_AUTHORITY_ARMS_FROZEN")
    require(authority["seed"] in FROZEN_SEEDS,
            "RDCJT_AUTHORITY_SEED_NOT_DECLARED:" + str(authority["seed"]))
    require(authority["learning_rate"] == FROZEN_LEARNING_RATE,
            "RDCJT_AUTHORITY_LR_FROZEN")
    require(list(authority["round_depths"]) == list(FROZEN_ROUND_DEPTHS),
            "RDCJT_AUTHORITY_ROUND_DEPTHS_FROZEN")
    require(list(authority["evaluation_depths"]) == list(FROZEN_EVALUATION_DEPTHS),
            "RDCJT_AUTHORITY_EVALUATION_DEPTHS_FROZEN")
    require(authority["updates_per_arm"] == FROZEN_UPDATES_PER_ARM,
            "RDCJT_AUTHORITY_UPDATES_FROZEN")
    require(authority["decisions_per_arm"] == FROZEN_DECISIONS_PER_ARM,
            "RDCJT_AUTHORITY_DECISIONS_FROZEN")
    require(authority["max_wall_seconds"] == FROZEN_MAX_WALL_SECONDS,
            "RDCJT_AUTHORITY_WALL_FROZEN")
    require(authority["reservation_usd"] == RESERVATION_USD,
            "RDCJT_AUTHORITY_RESERVATION_FROZEN")
    # Stated rather than implied: this candidate DOES train, unlike the readout.
    require(authority["training"] is True, "RDCJT_AUTHORITY_TRAINING_DECLARED")
    return authority


def validate_owner_authorization(path):
    document = json.loads(Path(path).read_bytes())
    require(document.get("schema") == OWNER_SCHEMA, "RDCJT_OWNER_SCHEMA")
    require(document.get("owner_instruction_raw"), "RDCJT_OWNER_INSTRUCTION_REQUIRED")
    require(document.get("candidate") == CANDIDATE, "RDCJT_OWNER_CANDIDATE")
    return document


# --------------------------------------------------------------------------
# the evidence this run must produce
# --------------------------------------------------------------------------

def evidence_contract():
    """What must arrive for this run to count as delivered.

    RUN_EVIDENCE_PRESERVATION_001: the collector checks REQUIRED against the bytes
    it actually received, independently of anything the worker declares. Attempt
    004 uploaded its measurement and lost it by never declaring it; every payload
    this candidate produces is named here BEFORE the worker starts.

    Declared limitation, carried in the contract rather than left implicit: the
    per-question rows for both arms and every sweep depth live in one JSON
    document. Row-identity completeness - exact item ids per depth, duplicates -
    would need a JSON-lines file per arm per depth, which this worker does not
    write, so the contract requires the payload intact and parseable and does not
    claim row-level coverage.
    """
    return run_evidence.contract(
        EXPERIMENT["profile"],
        [run_evidence.requirement("results/result.json",
                                  "transport marker and result envelope",
                                  kind="json"),
         run_evidence.requirement("results/result.json.sha256",
                                  "sidecar binding the envelope bytes"),
         run_evidence.requirement("results/artifacts/manifest.json",
                                  "the worker's produced-file manifest, as reality"),
         run_evidence.requirement("results/artifacts/experiment.json",
                                  "both arms, the course rows, the accounting and "
                                  "the panel provenance"),
         run_evidence.requirement("results/artifacts/depth_sweep.json",
                                  "every declared depth's answers on the frozen "
                                  "weights, with gains and losses apart"),
         run_evidence.requirement("results/artifacts/checkpoint_one_pass.pt",
                                  "the trained one-pass arm"),
         run_evidence.requirement("results/artifacts/checkpoint_recurrent.pt",
                                  "the trained recurrent arm")],
        notes=["row-identity completeness is not declared for this profile",
               "ONE matched initialization: an exploratory pilot, not a replication",
               "the panel is examined material; a gain on it is not transfer"])


# --------------------------------------------------------------------------
# the packaged worker
# --------------------------------------------------------------------------

def render_worker():
    """The in-package worker: proven scaffolding, thin body.

    The body lives in the packaged module ``cas_meta2.recurrent_cjt.experiment``
    so the rehearsal executes the same code in-process. This script only prepares
    the environment, runs the body under that environment's python, and uploads
    what it wrote - ``result.json`` last, because that is the completion marker.

    The transport is applied by ``run_evidence.unified_transport`` at package
    build time, which also enforces that every definition precedes the entrypoint
    guard and hands the publisher's map to the final upload.
    """
    inner_lines = [
        "import json",
        "import sys",
        "from pathlib import Path",
        "ROOT = Path(sys.argv[1])",
        "sys.path.insert(0, str(ROOT / 'research/CAS_META_2_COMPOSITION'))",
        "from cas_meta2.recurrent_cjt import runner",
        "CONFIG = json.loads((ROOT / 'config.json').read_bytes())",
        "RESULTS = ROOT / 'results'",
        "ARTIFACTS = RESULTS / 'artifacts'",
        "ARTIFACTS.mkdir(parents=True, exist_ok=True)",
        "report = runner.run(CONFIG, results=RESULTS, artifacts=ARTIFACTS,",
        "                    root=ROOT)",
        "print(json.dumps({'inner_status': 'EXPERIMENT_WRITTEN',",
        "                  'status': report['status'],",
        "                  'arms': sorted(report['arms']),",
        "                  'artifacts': len(report['artifacts'])}))",
    ]
    runner_block = ",\n".join(repr(line) for line in inner_lines)
    return "\n".join([
        '"""CAS_RDCJT_001 worker: train both arms, sweep the depths, upload.',
        "",
        "Prepares the environment, runs the packaged experiment under that",
        "environment's python, and uploads what it wrote - result.json last,",
        'because that is the completion marker."""',
        "import hashlib",
        "import json",
        "import shutil",
        "import subprocess",
        "import sys",
        "from pathlib import Path",
        "",
        "RESULT_SCHEMA = %r" % RESULT_SCHEMA,
        "FAILURE_SCHEMA = 'cas.recurrent-cjt-failure/1'",
        "ARTIFACT_MANIFEST_KEY = 'results/artifacts/manifest.json'",
        "MAX_WALL_SECONDS = %.1f" % FROZEN_MAX_WALL_SECONDS,
        "TORCH_INDEX = 'https://download.pytorch.org/whl/cu128'",
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
        "    for name in ('failure.json', 'result_partial.json',",
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
        "                               timeout=MAX_WALL_SECONDS + 1800)",
        "        if inner.returncode != 0:",
        "            detail = (inner.stderr or inner.stdout or '')[-1800:]",
        "            failure = {'type': 'InnerRunnerFailure',",
        "                       'message': 'INNER_RUNNER_EXIT_' + str(inner.returncode)",
        "                                  + '\\n' + detail}",
        "    except BaseException as error:",
        "        failure = {'type': type(error).__name__, 'message': str(error)[:2000]}",
        "    results_dir = results",
        "    if failure is None:",
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
        "                  'artifacts': [], 'arms': {}}",
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


# --------------------------------------------------------------------------
# provider and package
# --------------------------------------------------------------------------

class RecurrentCjtProvider(candidate.CandidateProvider):
    """The proven provider lifecycle, bound to THIS candidate's worker and schemas."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.worker_name = WORKER_NAME
        self.result_schema = RESULT_SCHEMA
        self.failure_statuses = ("WORKER_FAILED", ex.STATUS_FAILED,
                                 "REMOTE_WORKER_FAILED")
        # set from the authority before launch; the default is only a placeholder
        # so an unset seed is visible rather than silently the first one
        self.seed = None

    def bind_seed(self, seed):
        require(int(seed) in FROZEN_SEEDS,
                "RDCJT_SEED_NOT_DECLARED:" + str(seed))
        self.seed = int(seed)
        return self.seed

    def _worker_config(self, bucket):
        return {"schema": CONFIG_SCHEMA,
                "job": self.job, "bucket": bucket, "region": self.region,
                "candidate": CANDIDATE,
                "arms": list(FROZEN_ARMS),
                "seed": (self.seed if self.seed is not None
                         else require(False, "RDCJT_SEED_NOT_BOUND")),
                "learning_rate": FROZEN_LEARNING_RATE,
                "round_depths": list(FROZEN_ROUND_DEPTHS),
                "evaluation_depths": list(FROZEN_EVALUATION_DEPTHS),
                "updates_per_arm": FROZEN_UPDATES_PER_ARM,
                "decisions_per_arm": FROZEN_DECISIONS_PER_ARM,
                "max_wall_seconds": FROZEN_MAX_WALL_SECONDS,
                "install_allowance_seconds": FROZEN_INSTALL_ALLOWANCE_SECONDS,
                "training": True}


def package_data_files():
    """Extra members the deployed tree needs beyond the git-tracked sources."""
    return ()


def build_recurrent_package(output, *, source_sha, git_bytes_fn=None,
                            git_paths_fn=None):
    """The source package for this candidate, through the existing builder."""
    from aws import graph_training_curriculum_launch as curriculum
    return build_package(
        output, source_sha=source_sha,
        git_bytes_fn=git_bytes_fn or curriculum.git_bytes,
        git_paths_fn=git_paths_fn or curriculum.git_tree_paths,
        worker_name=WORKER_NAME, worker_source=render_worker(),
        experiment=EXPERIMENT, package_schema=PACKAGE_SCHEMA, design=DESIGN,
        receipt_schema=RECEIPT_SCHEMA,
        extra_files=package_data_files())


# --------------------------------------------------------------------------
# the costed request: what the owner is being asked to decide
# --------------------------------------------------------------------------

def costed_request(*, free_usd=None):
    """What one job costs, what the declared criterion costs, and the gap.

    Printed rather than assumed, because the handoff's success criterion needs
    three paired runs and the campaign may not have room for three.
    """
    per_job = float(RESERVATION_USD)
    criterion_jobs = replication_status(0)[
        "matched_pairs_required_by_the_declared_criterion"]
    document = {
        "schema": "cas.recurrent-cjt-costed-request/1",
        "candidate": CANDIDATE,
        "authorized": False,
        "reservation_usd_per_job": RESERVATION_USD,
        "one_job": {
            "jobs": 1,
            "usd": "%.2f" % per_job,
            "buys": DESIGN["what_one_job_can_support"],
            "does_not_buy": DESIGN["what_one_job_cannot_support"],
        },
        "declared_criterion": {
            "jobs": criterion_jobs,
            "usd": "%.2f" % (per_job * criterion_jobs),
            "criterion": replication_status(0)["criterion"],
        },
        "instance": {"type": RESOURCE_PLAN["instance_type"],
                     "region": RESOURCE_PLAN["region"],
                     "rate_ceiling_usd_hour": RESOURCE_PLAN["on_demand_rate_ceiling_usd"],
                     "instance_seconds_max": RESOURCE_PLAN["instance_seconds_max"]},
        "wall_clock": {"training_allowance_seconds": FROZEN_MAX_WALL_SECONDS,
                       "install_allowance_seconds": FROZEN_INSTALL_ALLOWANCE_SECONDS,
                       "total_ceiling_seconds": FROZEN_TOTAL_WALL_CLOCK_CEILING},
        "declared_cost": frozen_cost(),
        "what_is_still_absent": {
            "fresh_family_panel": (
                "the panel this course teaches against is EXAMINED material. A "
                "depth effect measured on it is not an application result, and no "
                "number from this job may be reported as transfer"),
            "owner_record": "no owner authorization record exists for this candidate",
            "request_and_authority": "not built; they bind to a package that is "
                                     "built from a commit, and no run is authorised",
        },
        "boundary": ("NOT A LAUNCH AND NOT A RESERVATION. This document states a "
                     "price; it does not spend anything and it does not authorise "
                     "anything"),
    }
    if free_usd is not None:
        free = float(free_usd)
        document["campaign"] = {
            "free_usd": "%.2f" % free,
            "one_job_fits": free >= per_job,
            "criterion_fits": free >= per_job * criterion_jobs,
            "shortfall_for_the_criterion_usd": "%.2f" % max(
                0.0, per_job * criterion_jobs - free),
        }
    return document


# --------------------------------------------------------------------------
# lifecycle and entrypoint
# --------------------------------------------------------------------------

def execute(request, authority, provider, *, ledger_path=LEDGER_PATH,
            receipt_dir=None, owner_authorization_path=None):
    """Reuse the candidate pilot's proven lifecycle with THIS candidate's validators."""
    return candidate.execute(
        request, authority, provider, ledger_path=ledger_path,
        receipt_dir=receipt_dir,
        owner_authorization_path=owner_authorization_path,
        validate_request_fn=validate_request,
        validate_authority_fn=validate_authority,
        evidence_contract=evidence_contract())


def plan_only():
    return {"schema": SCHEMA, "status": "PLAN_ONLY_NOT_EXECUTED",
            "experiment": EXPERIMENT, "design": DESIGN,
            "arms": list(FROZEN_ARMS),
            "replication": replication_status(0),
            "costed_request": costed_request(),
            "readiness": cs.readiness_report(),
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
    parser.add_argument("--free-usd")
    parser.add_argument("--costed-request", action="store_true")
    arguments = parser.parse_args(argv)
    if arguments.costed_request:
        print(json.dumps(costed_request(free_usd=arguments.free_usd),
                         sort_keys=True, indent=2))
        return 0
    if not arguments.execute:
        print(json.dumps(plan_only(), sort_keys=True))
        return 0
    require(all(getattr(arguments, name) for name in
               ("request", "request_sha256", "authority", "authority_sha256",
                "receipt_dir", "owner_authorization")),
            "EXPLICIT_REGISTERED_INPUTS_REQUIRED")
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
    validate_owner_authorization(arguments.owner_authorization)
    session_clients = candidate._clients(arguments.profile)
    provider = RecurrentCjtProvider(
        job=request["job"], source_sha=request["source_sha"],
        archive_sha256=request["archive_sha256"],
        manifest_sha256=request["manifest_sha256"], ledger_path=LEDGER_PATH,
        clients=session_clients, client_error=candidate._client_error(),
        source_archive=candidate._locate_archive(request["archive_sha256"]))
    # BEFORE the reservation: bind this job's seed and refuse one that already
    # has a receipt. Three jobs on the same seed are one job run three times.
    seed_report = require_unused_seed(authority["seed"],
                                      Path(arguments.receipt_dir).parent)
    provider.bind_seed(authority["seed"])
    result = execute(request, authority, provider, ledger_path=LEDGER_PATH,
                     receipt_dir=arguments.receipt_dir,
                     owner_authorization_path=arguments.owner_authorization)
    print(json.dumps({"status": result["status"], "stages": result["stages"],
                      "completed_deliverable": result["completed_deliverable"],
                      "seed": seed_report["seed"],
                      "seeds_remaining": seed_report["remaining"]},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
