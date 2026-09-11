"""Package rehearsal for the face-grounding pilot: run the delivered artifact.

Two paid attempts were lost to defects that existed only in the packaged layout, so
this unpacks the built ``source.zip`` and executes it: the worker is present and is
byte-for-byte the rendered worker, the repository-relative code imports from the
unpacked tree, the plan and the declared schedule compile there, the worker's own
``main()`` runs with fakes through the environment stage and the uploads, and a
failure it detects writes the result marker and its sidecar while preserving the
completed result.

No AWS, no torch, no model, no network, no reservation.
"""
import ast
import hashlib
import json
import sys
import textwrap
import zipfile
from pathlib import Path

import pytest

from aws import graph_training_face_launch as fl
from aws import graph_training_curriculum_launch as curriculum

RECORD_DIR = (curriculum.ROOT / "records/teaching_cycle_001/"
              "graph_first_candidate_001/training_mode_001/face_grounding_001")


def _package():
    receipts = sorted(RECORD_DIR.glob("candidate_package_*/receipt.json"),
                      key=lambda path: path.stat().st_mtime)
    assert receipts, "no face-grounding package has been built"
    return Path(json.loads(receipts[-1].read_bytes())["archive"])


def _unpack(tmp_path):
    root = tmp_path / "package"
    root.mkdir()
    with zipfile.ZipFile(_package()) as zipped:
        zipped.extractall(root)
    return root


def test_the_package_carries_the_worker_and_the_repo_relative_face_code():
    archive = _package()
    with zipfile.ZipFile(archive) as zipped:
        names = set(zipped.namelist())
    assert fl.WORKER_NAME in names
    for module in ("face_roles", "face_corpus", "face_tasks", "face_schedule",
                   "face_evaluation", "face_experiment", "face_worker"):
        assert ("research/CAS_META_2_COMPOSITION/cas_meta2/graph_teaching/"
                + module + ".py") in names
    assert ("research/CAS_META_2_COMPOSITION/cas_meta2/teaching_cycle/"
            "gpu_adapter.py") in names


def test_the_packaged_worker_is_the_worker_this_rehearsal_exercises():
    with zipfile.ZipFile(_package()) as zipped:
        packaged = zipped.read(fl.WORKER_NAME)
    assert packaged == fl.render_worker().encode("utf-8")
    with zipfile.ZipFile(_package()) as zipped:
        manifest = json.loads(zipped.read(curriculum.MANIFEST_NAME))
    assert manifest["worker_script"] == fl.WORKER_NAME
    assert manifest["files_sha256"][fl.WORKER_NAME] == \
        hashlib.sha256(packaged).hexdigest()


def test_the_unpacked_package_compiles_the_plan_and_the_declared_schedule(tmp_path):
    """The real deployed layout: import the packaged code and compile the plan."""
    root = _unpack(tmp_path)
    script = (
        "import json, sys\n"
        "from pathlib import Path\n"
        "ROOT = Path(sys.argv[1])\n"
        "sys.path.insert(0, str(ROOT / 'research/CAS_META_2_COMPOSITION'))\n"
        "from cas_meta2.graph_teaching import face_worker, face_schedule\n"
        "config = {'schema': 'cas.cube-face-worker-config/1', 'job': 'rehearsal',\n"
        "          'conditions': list(face_schedule.comparison_conditions() and\n"
        "                             [c['condition'] for c in\n"
        "                              face_schedule.comparison_conditions()]),\n"
        "          'batch_size': 8}\n"
        "built, conditions, panel, plan = face_worker.compile_plan(config)\n"
        "counts = plan['counts']\n"
        "print(json.dumps({'conditions': len(plan['conditions']),\n"
        "                  'events_per_condition': sorted(\n"
        "                      {entry['events'] for entry in plan['conditions']}),\n"
        "                  'queries': counts['supervised_query_presentations'],\n"
        "                  'supports': counts['worked_support_presentations'],\n"
        "                  'updates': counts['updates_at_declared_batch'],\n"
        "                  'unbatched': counts['UPDATES_IF_ONE_PER_EPISODE'],\n"
        "                  'cfc_total': counts['cfc_total_decisions'],\n"
        "                  'panel': plan['panel']['primary_items'],\n"
        "                  'families': plan['panel']['base_families']}))\n")
    import subprocess
    result = subprocess.run([sys.executable, "-c", script, str(root)],
                            capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stderr[-2000:]
    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert report == {"conditions": 4, "events_per_condition": [4608],
                      "queries": 9216, "supports": 18432, "updates": 1152,
                      "unbatched": 9216, "cfc_total": 4608, "panel": 192,
                      "families": 16}


def _worker_functions(names):
    """The worker's own function bodies, compiled from the rendered source."""
    source = fl.render_worker()
    namespace = {}
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef) and node.name in names:
            exec(textwrap.dedent(ast.get_source_segment(source, node)), namespace)
            found.append(node.name)
    assert sorted(found) == sorted(names)
    return namespace


class _RecordingS3:
    def __init__(self, puts):
        self.puts = puts

    def put_object(self, Bucket=None, Key=None, Body=None):
        self.puts.append(Key)


def _bind(namespace, root, monkeypatch, outcomes, puts):
    """Bind the worker's globals to fakes: no torch, no AWS, no real subprocesses.

    ``outcomes`` carries the inner runner's result; every pip and venv call in the
    environment stage is faked as successful, because those are the calls that have
    already been proven on an instance.
    """
    import types

    def fake_run(argv, **kwargs):
        command = [str(item) for item in argv]
        namespace["_commands"].append(command)
        if any("_inner_runner.py" in item for item in command):
            return outcomes["inner"]
        return _Completed(0)

    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.client = lambda name, region_name=None: _RecordingS3(puts)
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    namespace.update({
        "json": json, "hashlib": hashlib, "sys": sys, "Path": Path,
        "subprocess": type("S", (), {"run": staticmethod(fake_run)}),
        "shutil": type("S", (), {"which": staticmethod(
            lambda name: "/usr/bin/" + name)}),
        "RESULT_SCHEMA": fl.RESULT_SCHEMA,
        "FAILURE_SCHEMA": "cas.cube-face-failure/1",
        "ARTIFACT_MANIFEST_KEY": "results/artifacts/manifest.json",
        "MAX_WALL_SECONDS": fl.FROZEN_MAX_WALL_SECONDS_PER_CONDITION,
        "CONDITIONS": len(fl.FROZEN_CONDITIONS),
        "TORCH_INDEX": "https://download.pytorch.org/whl/cu128",
        "PILOT": "research/CAS_META_2_COMPOSITION",
        "WHEEL_DIR": fl.WORKER_WHEEL_DIR,
        "WHEEL_NAMES": ("casformer_reference-0.1.0-py3-none-any.whl",
                        "cas_neural_cjt-0.2.0-py3-none-any.whl"),
        "REQUIREMENTS": fl.WORKER_REQUIREMENTS,
        "INNER_RUNNER": "print('inner')",
        "__file__": str(root / fl.WORKER_NAME),
        "_commands": [],
    })
    return namespace["_commands"]


class _Completed:
    def __init__(self, returncode=0, stderr=""):
        self.returncode = returncode
        self.stdout = "{}"
        self.stderr = stderr


def _stage_delivery(root, *, planned=4608, delivered=4608, status=None):
    results = root / "results"
    artifacts = results / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    checkpoint = artifacts / "checkpoint_cfc_stable_cues.pt"
    checkpoint.write_bytes(b"checkpoint")
    (artifacts / "manifest.json").write_text(json.dumps(
        {"schema": "cas.cube-face-artifact-manifest/1", "job": "job-1",
         "artifacts": [{"name": checkpoint.name, "sha256": "x", "bytes": 10}]}))
    (results / "measurements.json").write_text(json.dumps(
        {"schema": "cas.cube-face-worker/0.1", "job": "job-1"}))
    envelope = {"schema": fl.RESULT_SCHEMA, "job": "job-1",
                "status": status or "REMOTE_FINISHED", "failure": None,
                "artifacts": [checkpoint.name], "conditions": {}}
    raw = (json.dumps(envelope, sort_keys=True, indent=2) + "\n").encode("utf-8")
    (results / "result.json").write_bytes(raw)
    (results / "result.json.sha256").write_text(
        hashlib.sha256(raw).hexdigest() + "\n")
    (root / "config.json").write_text(json.dumps(
        {"schema": "cas.cube-face-worker-config/1", "job": "job-1",
         "bucket": "bucket-1", "region": "us-west-2"}))


def test_the_worker_runs_the_environment_stage_and_uploads_the_marker_last(
        tmp_path, monkeypatch):
    root = tmp_path / "package"
    root.mkdir()
    _stage_delivery(root)
    namespace = _worker_functions({"main", "upload_results", "read_json",
                                   "sha256_file", "run_checked"})
    puts = []
    commands = _bind(namespace, root, monkeypatch, {"inner": _Completed(0)}, puts)
    namespace["main"]()
    assert any("venv" in " ".join(command) for command in commands), commands
    pip_commands = [command for command in commands if "pip" in command]
    assert len(pip_commands) == 3, pip_commands
    training = [command for command in commands
                if any("_inner_runner.py" in item for item in command)]
    assert len(training) == 1, training
    interpreter = training[0][0].replace("\\", "/")
    assert interpreter.endswith("venv/bin/python"), interpreter
    assert puts[-1] == "results/result.json", puts
    assert puts.index("results/result.json.sha256") == len(puts) - 2, puts
    assert "results/artifacts/manifest.json" in puts
    assert ("results/artifacts/checkpoint_cfc_stable_cues.pt") in puts


def test_the_worker_never_overwrites_a_completed_result_it_could_not_verify(
        tmp_path, monkeypatch):
    """A wrong sidecar is a failure, and the completed result is preserved."""
    root = tmp_path / "package"
    root.mkdir()
    _stage_delivery(root)
    (root / "results" / "result.json.sha256").write_text("0" * 64 + "\n")
    namespace = _worker_functions({"main", "upload_results", "read_json",
                                   "sha256_file", "run_checked"})
    puts = []
    _bind(namespace, root, monkeypatch, {"inner": _Completed(0)}, puts)
    with pytest.raises(SystemExit):
        namespace["main"]()
    envelope = json.loads((root / "results" / "result.json").read_bytes())
    assert envelope["status"] == "WORKER_FAILED"
    assert envelope["failure"]["message"] == "RESULT_SHA_MISMATCH"
    assert (root / "results" / "result_partial.json").is_file()
    assert (root / "results" / "failure.json").is_file()
    assert puts[-1] == "results/result.json"


def test_the_worker_reports_an_inner_failure_through_the_result_marker(
        tmp_path, monkeypatch):
    root = tmp_path / "package"
    root.mkdir()
    results = root / "results"
    results.mkdir(parents=True)
    (root / "config.json").write_text(json.dumps(
        {"schema": "cas.cube-face-worker-config/1", "job": "job-1",
         "bucket": "bucket-1", "region": "us-west-2"}))
    namespace = _worker_functions({"main", "upload_results", "read_json",
                                   "sha256_file", "run_checked"})
    puts = []
    _bind(namespace, root, monkeypatch,
          {"inner": _Completed(1, stderr="Traceback: ModuleNotFoundError")}, puts)
    with pytest.raises(SystemExit):
        namespace["main"]()
    envelope = json.loads((results / "result.json").read_bytes())
    assert envelope["status"] == "WORKER_FAILED"
    assert "INNER_RUNNER_EXIT_1" in envelope["failure"]["message"]
    assert "ModuleNotFoundError" in envelope["failure"]["message"]
    assert puts[-1] == "results/result.json"
