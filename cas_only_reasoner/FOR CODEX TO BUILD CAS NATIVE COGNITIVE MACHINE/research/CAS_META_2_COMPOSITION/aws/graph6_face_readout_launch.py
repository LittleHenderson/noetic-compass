"""Launcher binding for the CFC-pilot readout: recover attempt 004's lost detail.

This is a **binding, not another launcher**, in the same sense as
``graph_training_face_launch``: it supplies its own request and authority schemas,
its own frozen design, its own rendered worker and its own provider subclass, and
reuses the proven lifecycle untouched - the package builder, ``candidate.execute``,
the EC2/S3/IAM provider with verified collection, the ledger reservation, the
cleanup that never deletes an uncollected bucket, and the evidence writer.

What this job is, exactly: it loads the four checkpoints attempt 004 delivered and
answers the frozen panel from them, with **zero optimizer steps**, to regenerate the
per-face breakdowns, the per-question rows, the before/after pairing, the
constant-rule baselines and the milestone report that were uploaded but never
declared as artefacts and so were deleted with the bucket.

Why it can be trusted as a recovery rather than a new measurement:

* the four checkpoint file hashes are bound in the authority, so the job reads the
  delivered weights or fails closed;
* the recomputed per-layer totals must equal the totals attempt 004 published -
  the published numbers are bound in the authority too, and a mismatch is reported
  as a failed recovery, never dressed up as the recovered detail;
* no optimizer is stepped, no checkpoint is written, and no attempt-004 record is
  touched. The readout writes into its own record directory.

No plan here reserves anything. The request it can build is inert
(``launch_authorized: false``) until a separately hash-bound owner instruction
arrives.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
COMPOSITION = HERE.parent
if str(COMPOSITION) not in sys.path:
    sys.path.insert(0, str(COMPOSITION))

from aws.graph_training_curriculum_launch import (  # noqa: E402
    HEX40, HEX64, LEDGER_PATH, RESOURCE_PLAN, RESERVATION_USD, ROOT as REPO_ROOT,
    WORKER_REQUIREMENTS, WORKER_WHEEL_DIR, build_package, canonical, digest,
    require)
from aws import graph_training_candidate_launch as candidate  # noqa: E402
from cas_meta2.graph_teaching import face_readout as readout  # noqa: E402

SCHEMA = "cas-graph-training-face-readout-launch/1"
REQUEST_SCHEMA = "cas-graph-training-face-readout-request/1"
AUTHORITY_SCHEMA = "cas-graph-training-face-readout-authority/1"
PACKAGE_SCHEMA = "cas-graph-training-face-readout-source-package/1"
RECEIPT_SCHEMA = "cas-graph-training-face-readout-package-receipt/1"
RESULT_SCHEMA = "cas.cube-face-readout-result/1"
WORKER_NAME = "graph6_face_readout_worker.py"
JOB_PATTERN = r"cas-meta2-graph6read-\d{14}-[a-f0-9]{8}"
EXPERIMENT = {"profile": "cfc_loop_face_cue_readout",
              "title": "CFC Pilot Readout (attempt 004 recovery)",
              "entrypoint": "cas_meta2.graph_teaching.face_readout.run",
              "selected_schedule": "NONE_ZERO_UPDATES",
              "not_included": ("no training, no optimizer step, no retraining, no "
                               "probe or curriculum change: this job only reads the "
                               "checkpoints attempt 004 already delivered")}

#: The delivered attempt 004 job and the four checkpoints it collected, by hash.
READOUT_OF_JOB = "cas-meta2-graph6face-20260911133305-9723735f"
#: The package member name carries the pilot prefix, because the deployed tree
#: mirrors the repository layout; the local path does not, because this module
#: already sits inside the pilot directory.
FROZEN_CHECKPOINT_SUBDIR = ("records/teaching_cycle_001/graph_first_candidate_001/"
                            "training_mode_001/face_grounding_001/"
                            "receipt_cas-meta2-graph6face-20260911133305-9723735f/"
                            "checkpoints")
FROZEN_CHECKPOINT_DIR = candidate.PILOT.rstrip("/") + "/" + FROZEN_CHECKPOINT_SUBDIR
FROZEN_CHECKPOINTS = {
    "cfc_stable_cues":
        "641dedea7df937c9d6af31aaf2e27f2b1fbe12f7aa3892dc6aa553e03e96842b",
    "cfc_neutral_cue":
        "2cbe25ecef2bf1e255f70a49ada42c9675f8b69cc327e1b14da3ebe6935c1820",
    "mixed_order_stable_cues":
        "38a359613a60748729b01479415668b90c5ab5f21b591aa716e86f5d12db87ee",
    "mixed_order_neutral_cue":
        "93ce1dc27a65780faff0a668980926df7cb9c1323d711eb6f39f5b414d5c8932",
}
FROZEN_CONDITIONS = ("cfc_stable_cues", "cfc_neutral_cue",
                     "mixed_order_stable_cues", "mixed_order_neutral_cue")

#: The totals attempt 004 published, from its collected envelope. The readout must
#: reproduce exactly these, or it reports a failed recovery.
FROZEN_EXPECTED_TOTALS = {
    "cfc_stable_cues": {"role_recognition": {"correct": 55, "total": 96},
                        "role_application": {"correct": 76, "total": 96},
                        "targeted_check": {"correct": 15, "total": 24}},
    "cfc_neutral_cue": {"role_recognition": {"correct": 56, "total": 96},
                        "role_application": {"correct": 75, "total": 96},
                        "targeted_check": {"correct": 15, "total": 24}},
    "mixed_order_stable_cues": {"role_recognition": {"correct": 47, "total": 96},
                                "role_application": {"correct": 74, "total": 96},
                                "targeted_check": {"correct": 16, "total": 24}},
    "mixed_order_neutral_cue": {"role_recognition": {"correct": 52, "total": 96},
                                "role_application": {"correct": 76, "total": 96},
                                "targeted_check": {"correct": 16, "total": 24}},
}
#: The digest of the payload attempt 004 lost. Recorded so the readout's report
#: names what it is replacing; it is not compared against anything, because a
#: regenerated object contains this run's own timings.
FROZEN_LOST_MEASUREMENTS_SHA256 = (
    "796658502cba1d3a03f026d3c7f5c97365de7bb35d7f312a5b105e0fa59dffee")

#: The published totals bound by digest, not by object identity: a shallow copy of
#: a nested dict shares its inner dicts, so an equality check against the constant
#: can be defeated by mutating one through the other. The digest is taken once, at
#: import, and cannot be aliased.
FROZEN_TOTALS_SHA256 = digest(canonical({
    name: {layer: [values["correct"], values["total"]]
           for layer, values in sorted(layers.items())}
    for name, layers in sorted(FROZEN_EXPECTED_TOTALS.items())}))


def frozen_totals():
    """A fresh, unaliased copy of the published totals."""
    return json.loads(json.dumps(FROZEN_EXPECTED_TOTALS))

FROZEN_SEED = 20260912
FROZEN_ENCODER_SEED = 20260909
FROZEN_LEARNING_RATE = 0.003
FROZEN_PANEL_ITEMS = 192
FROZEN_OPTIMIZER_UPDATES = 0

#: Wall-clock bound. No training and no per-condition teaching budget: one encoder
#: fit, four panel passes before and four after, and the environment install. The
#: install is the same scaffolding the proven workers run, so it is allowed for.
FROZEN_MAX_WALL_SECONDS = 1200.0
FROZEN_INSTALL_ALLOWANCE_SECONDS = 600.0
FROZEN_TOTAL_WALL_CLOCK_CEILING = (FROZEN_MAX_WALL_SECONDS
                                   + FROZEN_INSTALL_ALLOWANCE_SECONDS)
FROZEN_BUCKET_PREFIX = "cas-meta2-graph6read"
RECEIPT_PREFIX = "graph6read_"


def validate_bounds(resource_plan=None):
    """The declared job must fit inside the reservation's instance ceiling."""
    resource_plan = RESOURCE_PLAN if resource_plan is None else resource_plan
    ceiling = resource_plan["instance_seconds_max"]
    require(FROZEN_TOTAL_WALL_CLOCK_CEILING <= ceiling,
            "READOUT_DESIGN_WALL_CLOCK_EXCEEDS_RESERVATION:%d>%d"
            % (FROZEN_TOTAL_WALL_CLOCK_CEILING, ceiling))
    return {"readout_seconds": FROZEN_MAX_WALL_SECONDS,
            "install_allowance_seconds": FROZEN_INSTALL_ALLOWANCE_SECONDS,
            "total_ceiling_seconds": FROZEN_TOTAL_WALL_CLOCK_CEILING,
            "instance_ceiling_seconds": ceiling,
            "fits": True}


def readout_facts():
    """What the readout will read and what it must reproduce, from the code itself.

    The checkpoints and their hashes come from the delivered receipt, and the
    panel counts from the same evaluation module the worker imports, so the request
    cannot state a job the run would not perform.
    """
    from cas_meta2.graph_teaching import face_corpus as corpus
    from cas_meta2.graph_teaching import face_evaluation as evaluation
    built = corpus.families()
    manifest = evaluation.panel_manifest(built)
    require(manifest["primary_items"] == FROZEN_PANEL_ITEMS,
            "READOUT_DESIGN_PANEL:%d" % manifest["primary_items"])
    checks = []
    base = REPO_ROOT / FROZEN_CHECKPOINT_SUBDIR
    for condition in FROZEN_CONDITIONS:
        path = base / ("checkpoint_%s.pt" % condition)
        require(path.is_file(), "READOUT_DESIGN_CHECKPOINT_MISSING:" + str(path))
        actual = readout.sha256_file(path)
        require(actual == FROZEN_CHECKPOINTS[condition],
                "READOUT_DESIGN_CHECKPOINT_CHANGED:%s:%s" % (condition, actual))
        checks.append({"condition": condition,
                       "checkpoint": "checkpoint_%s.pt" % condition,
                       "sha256": actual, "bytes": path.stat().st_size})
    return {"readout_of_job": READOUT_OF_JOB,
            "lost_measurements_sha256": FROZEN_LOST_MEASUREMENTS_SHA256,
            "checkpoints": checks,
            "checkpoint_dir": FROZEN_CHECKPOINT_DIR,
            "conditions": list(FROZEN_CONDITIONS),
            "panel": {"primary_items": manifest["primary_items"],
                      "by_layer": manifest["by_layer"],
                      "diagnostics": manifest["by_layer"].get("targeted_check")},
            "expected_totals": frozen_totals(),
            "optimizer_updates": FROZEN_OPTIMIZER_UPDATES,
            "training": False}


DESIGN = {
    "launch_enabled": False,
    "training": False,
    "optimizer_updates": FROZEN_OPTIMIZER_UPDATES,
    "title": "CFC Pilot Readout (attempt 004 recovery)",
    "readout_of_job": READOUT_OF_JOB,
    "conditions": list(FROZEN_CONDITIONS),
    "checkpoints": {name: FROZEN_CHECKPOINTS[name] for name in FROZEN_CONDITIONS},
    "checkpoint_dir": FROZEN_CHECKPOINT_DIR,
    "expected_totals": frozen_totals(),
    "lost_measurements_sha256": FROZEN_LOST_MEASUREMENTS_SHA256,
    "to_be_delivered": (
        "per-condition per-face counts and macro accuracy, every per-question row "
        "for 192 primary questions and 24 diagnostics, the before/after pairing, "
        "the constant-rule baselines per layer, the milestone report, and the four "
        "declared paired comparisons - the detail attempt 004 uploaded but did not "
        "declare as an artefact"),
    "panel_items": FROZEN_PANEL_ITEMS,
    "seed": FROZEN_SEED,
    "encoder_seed": FROZEN_ENCODER_SEED,
    "learning_rate": FROZEN_LEARNING_RATE,
    "max_wall_seconds": FROZEN_MAX_WALL_SECONDS,
    "install_allowance_seconds": FROZEN_INSTALL_ALLOWANCE_SECONDS,
    "total_wall_clock_ceiling_seconds": FROZEN_TOTAL_WALL_CLOCK_CEILING,
    "reservation_usd": RESERVATION_USD,
    "why_this_is_a_recovery": (
        "the four checkpoint file hashes and the totals attempt 004 published are "
        "both bound in the authority; the readout reads the delivered weights, "
        "measures that its own parameter digest never changes, and must reproduce "
        "the published totals exactly or report a failed recovery"),
    "not_included": ("no training, no optimizer step, no checkpoint write outside "
                     "this job's own artefact directory, no change to any "
                     "attempt-004 record, no probe replacement, no curriculum "
                     "change"),
}


def validate_request(request):
    require(type(request) is dict and request.get("schema") == REQUEST_SCHEMA,
            "READOUT_REQUEST_SCHEMA")
    require(set(request) == {"schema", "job", "source_sha", "archive_sha256",
                             "manifest_sha256", "launch_authorized"},
            "READOUT_REQUEST_FIELDS")
    require(type(request["job"]) is str and re.fullmatch(JOB_PATTERN, request["job"]),
            "READOUT_REQUEST_JOB")
    require(type(request["source_sha"]) is str
            and bool(HEX40.fullmatch(request["source_sha"])),
            "READOUT_REQUEST_SOURCE_SHA")
    for key in ("archive_sha256", "manifest_sha256"):
        require(type(request[key]) is str and bool(HEX64.fullmatch(request[key])),
                "READOUT_REQUEST_HASH:" + key)
    require(request["launch_authorized"] is False, "READOUT_REQUEST_INERT")
    return request


def validate_authority(authority):
    require(type(authority) is dict and authority.get("schema") == AUTHORITY_SCHEMA,
            "READOUT_AUTHORITY_SCHEMA")
    require(set(authority) == {
        "schema", "job", "source_sha", "archive_sha256", "manifest_sha256",
        "owner_authorization_sha256", "readout_of_job", "conditions",
        "checkpoints", "expected_totals", "lost_measurements_sha256",
        "optimizer_updates", "panel_items", "seed", "encoder_seed",
        "learning_rate", "max_wall_seconds", "reservation_usd"},
        "READOUT_AUTHORITY_FIELDS")
    require(type(authority["job"]) is str
            and re.fullmatch(JOB_PATTERN, authority["job"]),
            "READOUT_AUTHORITY_JOB")
    require(type(authority["source_sha"]) is str
            and bool(HEX40.fullmatch(authority["source_sha"])),
            "READOUT_AUTHORITY_SOURCE_SHA")
    for key in ("archive_sha256", "manifest_sha256", "owner_authorization_sha256",
                "lost_measurements_sha256"):
        require(type(authority[key]) is str and bool(HEX64.fullmatch(authority[key])),
                "READOUT_AUTHORITY_HASH:" + key)
    require(authority["readout_of_job"] == READOUT_OF_JOB,
            "READOUT_AUTHORITY_OF_JOB_FROZEN")
    require(list(authority["conditions"]) == list(FROZEN_CONDITIONS),
            "READOUT_AUTHORITY_CONDITIONS_FROZEN")
    require(authority["checkpoints"] == {name: FROZEN_CHECKPOINTS[name]
                                         for name in FROZEN_CONDITIONS},
            "READOUT_AUTHORITY_CHECKPOINTS_FROZEN")
    require(digest(canonical({name: {layer: [values["correct"], values["total"]]
                                     for layer, values in sorted(layers.items())}
                              for name, layers
                              in sorted(authority["expected_totals"].items())}))
            == FROZEN_TOTALS_SHA256,
            "READOUT_AUTHORITY_TOTALS_FROZEN")
    require(authority["lost_measurements_sha256"] == FROZEN_LOST_MEASUREMENTS_SHA256,
            "READOUT_AUTHORITY_LOST_DIGEST_FROZEN")
    require(authority["optimizer_updates"] == FROZEN_OPTIMIZER_UPDATES,
            "READOUT_AUTHORITY_ZERO_UPDATES_FROZEN")
    require(authority["panel_items"] == FROZEN_PANEL_ITEMS,
            "READOUT_AUTHORITY_PANEL_FROZEN")
    require(authority["seed"] == FROZEN_SEED, "READOUT_AUTHORITY_SEED_FROZEN")
    require(authority["encoder_seed"] == FROZEN_ENCODER_SEED,
            "READOUT_AUTHORITY_ENCODER_SEED_FROZEN")
    require(authority["learning_rate"] == FROZEN_LEARNING_RATE,
            "READOUT_AUTHORITY_LR_FROZEN")
    require(authority["max_wall_seconds"] == FROZEN_MAX_WALL_SECONDS,
            "READOUT_AUTHORITY_WALL_FROZEN")
    require(authority["reservation_usd"] == RESERVATION_USD,
            "READOUT_AUTHORITY_RESERVATION_FROZEN")
    return authority


def render_worker():
    """The in-package worker: proven scaffolding, thin body.

    The environment steps are the ones that have actually run on an instance. The
    body writes its own failure through ``result.json`` so a failed run is seen and
    terminated instead of idling, and the sidecar so the collector's identity check
    passes.
    """
    inner_lines = [
        "import json",
        "import sys",
        "from pathlib import Path",
        "ROOT = Path(sys.argv[1])",
        "sys.path.insert(0, str(ROOT / 'research/CAS_META_2_COMPOSITION'))",
        "from cas_meta2.graph_teaching import face_readout",
        "from cas_meta2.teaching_cycle import gpu_adapter",
        "CONFIG = json.loads((ROOT / 'config.json').read_bytes())",
        "torch, device = gpu_adapter._cuda()",
        "RESULTS = ROOT / 'results'",
        "ARTIFACTS = RESULTS / 'artifacts'",
        "ARTIFACTS.mkdir(parents=True, exist_ok=True)",
        "report = face_readout.run(CONFIG, torch=torch, device=device,",
        "                          results=RESULTS, artifacts=ARTIFACTS,",
        "                          root=ROOT, outbound=None)",
        "print(json.dumps({'inner_status': 'READOUT_WRITTEN',",
        "                  'status': report['envelope']['status'],",
        "                  'reproduced': report['envelope']['reproduction']",
        "                                ['reproduced'],",
        "                  'artifacts': len(report['envelope']['artifacts'])}))",
    ]
    runner_block = ",\n".join(repr(line) for line in inner_lines)
    return "\n".join([
        '"""GRAPH6 face-readout worker: read the delivered checkpoints, train nothing.',
        "",
        "The body lives in the packaged module cas_meta2.graph_teaching.face_readout,",
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
        "FAILURE_SCHEMA = 'cas.cube-face-readout-failure/1'",
        "ARTIFACT_MANIFEST_KEY = 'results/artifacts/manifest.json'",
        "MAX_WALL_SECONDS = %.1f" % FROZEN_MAX_WALL_SECONDS,
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


class FaceReadoutProvider(candidate.CandidateProvider):
    """The proven provider lifecycle, bound to this readout's worker and schemas."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.worker_name = WORKER_NAME
        self.result_schema = RESULT_SCHEMA
        self.failure_statuses = ("WORKER_FAILED", "READOUT_FAILED",
                                 "REMOTE_WORKER_FAILED")

    def _worker_config(self, bucket):
        facts = readout_facts()
        return {"schema": "cas.cube-face-readout-config/1",
                "job": self.job, "bucket": bucket, "region": self.region,
                "condition_order": list(FROZEN_CONDITIONS),
                "conditions": {entry["condition"]:
                               {"checkpoint": entry["checkpoint"],
                                "sha256": entry["sha256"]}
                               for entry in facts["checkpoints"]},
                "checkpoint_dir": FROZEN_CHECKPOINT_DIR,
                "expected_totals": frozen_totals(),
                "lost_measurements_sha256": FROZEN_LOST_MEASUREMENTS_SHA256,
                "seed": FROZEN_SEED, "encoder_seed": FROZEN_ENCODER_SEED,
                "learning_rate": FROZEN_LEARNING_RATE,
                "panel_items": FROZEN_PANEL_ITEMS,
                "optimizer_updates": FROZEN_OPTIMIZER_UPDATES,
                "max_wall_seconds": FROZEN_MAX_WALL_SECONDS,
                "authority_sha256": self._authority_sha256()}


def package_data_files():
    """Repository files this readout's code reads at run time.

    The four delivered checkpoints, read from git at the packaged commit exactly as
    every other member is. They are the job's input: a package without them would
    deploy code that fails closed on its own missing evidence. The pinned cube
    bundle and fixture are carried too, because the panel compilation reads the same
    graph and teaching modules the training worker did.
    """
    names = [FROZEN_CHECKPOINT_DIR + "/checkpoint_%s.pt" % condition
             for condition in FROZEN_CONDITIONS]
    return tuple(sorted(names + list(candidate.package_data_files())))


def build_readout_package(output, *, source_sha, git_bytes_fn=None,
                          git_paths_fn=None):
    """The source package for this readout, through the existing package builder."""
    from aws import graph_training_curriculum_launch as curriculum
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
    require(document.get("schema") == "cas-cube-face-readout-owner-authorization/1",
            "READOUT_OWNER_AUTHORIZATION_SCHEMA")
    require(document.get("owner_instruction_raw"), "READOUT_OWNER_INSTRUCTION_REQUIRED")
    return document


def execute(request, authority, provider, *, ledger_path=LEDGER_PATH,
            receipt_dir=None, owner_authorization_path=None):
    """Reuse the candidate pilot's proven lifecycle with this readout's validators."""
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
            "readout_facts": readout_facts(),
            "bounds": validate_bounds(),
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
    provider = FaceReadoutProvider(
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
