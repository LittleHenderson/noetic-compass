"""Package rehearsal for the readout: run the delivered artifact before paying.

The readout's input is four binary checkpoints, and the package builder reads every
member from git. Two failures this rehearsal exists to prevent: a checkpoint whose
stored bytes differ from the delivered hash (the job would fail closed on the
instance), and a deployed path that does not resolve where the code looks for it.
Both are cheap to check here and expensive to discover on a paid run.

No AWS, no torch, no model, no network, no reservation.
"""
import ast
import hashlib
import json
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path

import pytest

from aws import graph6_face_readout_launch as rl
from aws import graph_training_curriculum_launch as curriculum

RECORD_DIR = (curriculum.ROOT / "records/teaching_cycle_001/"
              "graph_first_candidate_001/training_mode_001/face_grounding_001")


def _package():
    receipts = sorted(RECORD_DIR.glob("readout_package_*/receipt.json"),
                      key=lambda path: path.stat().st_mtime)
    assert receipts, "no readout package has been built"
    return Path(json.loads(receipts[-1].read_bytes())["archive"])


def _receipt():
    return json.loads(sorted(RECORD_DIR.glob("readout_package_*/receipt.json"),
                             key=lambda path: path.stat().st_mtime)[-1].read_bytes())


def _unpack(tmp_path):
    root = tmp_path / "package"
    root.mkdir()
    with zipfile.ZipFile(_package()) as zipped:
        zipped.extractall(root)
    return root


def test_the_package_carries_the_readout_code_and_the_delivered_weights():
    with zipfile.ZipFile(_package()) as zipped:
        names = set(zipped.namelist())
        for module in ("face_readout", "face_worker", "face_evaluation",
                       "face_experiment", "face_corpus", "face_schedule",
                       "face_roles", "face_tasks"):
            assert ("research/CAS_META_2_COMPOSITION/cas_meta2/graph_teaching/"
                    + module + ".py") in names
        assert rl.WORKER_NAME in names
        # the weights themselves, byte-for-byte as delivered
        for condition in rl.FROZEN_CONDITIONS:
            member = rl.FROZEN_CHECKPOINT_DIR + "/checkpoint_%s.pt" % condition
            assert member in names, member
            raw = zipped.read(member)
            assert hashlib.sha256(raw).hexdigest() == \
                rl.FROZEN_CHECKPOINTS[condition], member
    receipt = _receipt()
    for condition in rl.FROZEN_CONDITIONS:
        member = rl.FROZEN_CHECKPOINT_DIR + "/checkpoint_%s.pt" % condition
        assert receipt["manifest"]["files_sha256"][member] == \
            rl.FROZEN_CHECKPOINTS[condition]


def test_the_packaged_worker_is_the_worker_this_rehearsal_exercises():
    with zipfile.ZipFile(_package()) as zipped:
        packaged = zipped.read(rl.WORKER_NAME)
        manifest = json.loads(zipped.read(curriculum.MANIFEST_NAME))
    assert packaged == rl.render_worker().encode("utf-8")
    assert manifest["worker_script"] == rl.WORKER_NAME
    assert manifest["files_sha256"][rl.WORKER_NAME] == \
        hashlib.sha256(packaged).hexdigest()
    assert manifest["optimizer_updates"] == 0
    assert manifest["training"] is False
    assert manifest["launch_enabled"] is False


def test_the_declared_plan_compiles_inside_the_unpacked_package_and_finds_its_input(
        tmp_path):
    """The real deployed layout, driven in a subprocess with the packaged code.

    This is the check that matters most for a readout: the plan must resolve the
    four checkpoint paths *inside the deployed tree*, and each file it finds must
    hash to the value the authority binds.
    """
    root = _unpack(tmp_path)
    facts = rl.readout_facts()
    config = {"schema": "cas.cube-face-readout-config/1", "job": "rehearsal",
              "condition_order": list(rl.FROZEN_CONDITIONS),
              "conditions": {entry["condition"]:
                             {"checkpoint": entry["checkpoint"],
                              "sha256": entry["sha256"]}
                             for entry in facts["checkpoints"]},
              "checkpoint_dir": rl.FROZEN_CHECKPOINT_DIR,
              "expected_totals": rl.frozen_totals(),
              "lost_measurements_sha256": rl.FROZEN_LOST_MEASUREMENTS_SHA256}
    script = (
        "import hashlib, json, sys\n"
        "from pathlib import Path\n"
        "ROOT = Path(sys.argv[1])\n"
        "sys.path.insert(0, str(ROOT / 'research/CAS_META_2_COMPOSITION'))\n"
        "from cas_meta2.graph_teaching import face_readout\n"
        "config = json.loads(sys.argv[2])\n"
        "built, conditions, panel, plan = face_readout.compile_plan(config)\n"
        "found = []\n"
        "for entry in conditions:\n"
        "    path = face_readout.checkpoint_path(ROOT, plan['checkpoint_dir'],\n"
        "                                        entry['checkpoint'])\n"
        "    found.append({'condition': entry['condition'],\n"
        "                  'exists': path.is_file(),\n"
        "                  'sha256': face_readout.sha256_file(path)\n"
        "                            if path.is_file() else None,\n"
        "                  'bound': entry['sha256'],\n"
        "                  'bytes': path.stat().st_size if path.is_file() else 0})\n"
        "print(json.dumps({'conditions': len(conditions), 'items': len(panel),\n"
        "                  'updates': plan['optimizer_updates'],\n"
        "                  'training': plan['training'],\n"
        "                  'pairs': len(plan['declared_pairs']),\n"
        "                  'found': found}))\n")
    result = subprocess.run([sys.executable, "-c", script, str(root),
                             json.dumps(config)],
                            capture_output=True, text=True, timeout=600)
    assert result.returncode == 0, result.stderr[-2000:]
    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert report["conditions"] == 4
    assert report["items"] == 216
    assert report["updates"] == 0 and report["training"] is False
    assert report["pairs"] == 4
    for entry in report["found"]:
        assert entry["exists"] is True, entry
        assert entry["sha256"] == entry["bound"], entry
        assert entry["bytes"] > 0


def test_the_readout_module_the_package_ships_refuses_a_training_path():
    """The delivered copy carries the same structural guarantee as the local one."""
    with zipfile.ZipFile(_package()) as zipped:
        source = zipped.read("research/CAS_META_2_COMPOSITION/cas_meta2/"
                             "graph_teaching/face_readout.py").decode("utf-8")
    assert source == Path(rl.readout.__file__).read_text(encoding="utf-8")
    for forbidden in ("batch_step", "run_condition", "optimizer.step", ".step()",
                      "loss.backward", "backward()", "torch.save", "import torch"):
        assert forbidden not in source, forbidden


# --------------------------------------------------------------------------
# the delivered worker's own flow, with fakes
# --------------------------------------------------------------------------

def _worker_functions(names):
    """The worker's own function bodies, compiled from the rendered source."""
    source = rl.render_worker()
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


class _Completed:
    def __init__(self, returncode=0, stderr=""):
        self.returncode = returncode
        self.stdout = "{}"
        self.stderr = stderr


def _bind(namespace, root, monkeypatch, outcomes, puts):
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
        "RESULT_SCHEMA": rl.RESULT_SCHEMA,
        "FAILURE_SCHEMA": "cas.cube-face-readout-failure/1",
        "ARTIFACT_MANIFEST_KEY": "results/artifacts/manifest.json",
        "MAX_WALL_SECONDS": rl.FROZEN_MAX_WALL_SECONDS,
        "TORCH_INDEX": "https://download.pytorch.org/whl/cu128",
        "PILOT": "research/CAS_META_2_COMPOSITION",
        "WHEEL_DIR": curriculum.WORKER_WHEEL_DIR,
        "WHEEL_NAMES": ("casformer_reference-0.1.0-py3-none-any.whl",
                        "cas_neural_cjt-0.2.0-py3-none-any.whl"),
        "REQUIREMENTS": curriculum.WORKER_REQUIREMENTS,
        "INNER_RUNNER": "print('inner')",
        "__file__": str(root / rl.WORKER_NAME),
        "_commands": [],
    })
    return namespace["_commands"]


def _stage_delivery(root, *, status="READOUT_COMPLETE"):
    results = root / "results"
    artifacts = results / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    readout = artifacts / "readout.json"
    readout.write_text(json.dumps({"schema": rl.readout.SCHEMA, "job": "job-1"}))
    measurements = artifacts / "measurements.json"
    measurements.write_text(json.dumps({"schema": rl.readout.SCHEMA, "job": "job-1"}))
    staged = [{"name": path.name,
               "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
               "bytes": path.stat().st_size}
              for path in (measurements, readout)]
    (artifacts / "manifest.json").write_text(json.dumps(
        {"schema": "cas.cube-face-artifact-manifest/1", "job": "job-1",
         "artifacts": staged}))
    (results / "measurements.json").write_bytes(measurements.read_bytes())
    envelope = {"schema": rl.RESULT_SCHEMA, "job": "job-1", "status": status,
                "failure": None, "artifacts": staged, "optimizer_updates": 0,
                "reproduction": {"reproduced": status == "READOUT_COMPLETE"}}
    raw = (json.dumps(envelope, sort_keys=True, indent=2) + "\n").encode("utf-8")
    (results / "result.json").write_bytes(raw)
    (results / "result.json.sha256").write_text(hashlib.sha256(raw).hexdigest() + "\n")
    (root / "config.json").write_text(json.dumps(
        {"schema": "cas.cube-face-readout-config/1", "job": "job-1",
         "bucket": "bucket-1", "region": "us-west-2"}))
    return staged


def test_the_worker_uploads_both_payloads_and_the_marker_last(tmp_path, monkeypatch):
    root = tmp_path / "package"
    root.mkdir()
    staged = _stage_delivery(root)
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
    for entry in staged:
        assert "results/artifacts/" + entry["name"] in puts, (entry, puts)
    assert "results/artifacts/manifest.json" in puts
    assert puts.index("results/artifacts/manifest.json") < puts.index(
        "results/artifacts/readout.json")
    assert puts.index("results/result.json.sha256") == len(puts) - 2, puts
    assert puts[-1] == "results/result.json", puts


def test_the_worker_reports_an_inner_failure_through_the_result_marker(
        tmp_path, monkeypatch):
    root = tmp_path / "package"
    root.mkdir()
    results = root / "results"
    results.mkdir(parents=True)
    (root / "config.json").write_text(json.dumps(
        {"schema": "cas.cube-face-readout-config/1", "job": "job-1",
         "bucket": "bucket-1", "region": "us-west-2"}))
    namespace = _worker_functions({"main", "upload_results", "read_json",
                                   "sha256_file", "run_checked"})
    puts = []
    _bind(namespace, root, monkeypatch,
          {"inner": _Completed(1, stderr="Traceback: READOUT_CHECKPOINT_HASH")}, puts)
    with pytest.raises(SystemExit):
        namespace["main"]()
    envelope = json.loads((results / "result.json").read_bytes())
    assert envelope["status"] == "WORKER_FAILED"
    assert "INNER_RUNNER_EXIT_1" in envelope["failure"]["message"]
    assert "READOUT_CHECKPOINT_HASH" in envelope["failure"]["message"]
    assert puts[-1] == "results/result.json"


def test_the_worker_never_overwrites_a_completed_result_it_could_not_verify(
        tmp_path, monkeypatch):
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
