"""Package rehearsal: run the delivered artifact, not a hope.

Three paid attempts were lost to defects that only appear in the packaged layout:
attempt 003 omitted the source archive entirely, attempt 004 died on
``ModuleNotFoundError: No module named 'cas_meta2'`` because the rendered worker
did not put the package's repository-relative path on ``sys.path`` — exactly what
the proven curriculum worker does — and the packaged worker also had no pinned
cube bundle, because the bundle lives under ``records/`` and ``records/`` is not
among the source directories. That third defect would have consumed a fourth
reservation and died with ``CUBE_BUNDLE_FILE_MISSING``; this rehearsal found it
for free.

This test unpacks the built ``source.zip`` into a temporary directory and executes
the *unpacked* worker's own setup and its real entrypoint with injected stubs. No
AWS, no torch, no network, no reservation.
"""
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from aws import graph_training_candidate_launch as cl
from aws import graph_training_curriculum_launch as curriculum
from cas_meta2.graph_teaching import cube_node, verified_teaching


def _package():
    """The newest built candidate package, whatever its archive hash is."""
    record = (curriculum.ROOT / "records/teaching_cycle_001/"
              "graph_first_candidate_001/training_mode_001/"
              "cube_verified_teaching_001")
    receipts = sorted(record.glob("candidate_package_*/receipt.json"),
                      key=lambda path: path.stat().st_mtime)
    assert receipts, "no candidate package has been built"
    document = json.loads(receipts[-1].read_bytes())
    return Path(document["archive"])


def _unpack(tmp_path):
    root = tmp_path / "package"
    root.mkdir()
    with zipfile.ZipFile(_package()) as zipped:
        zipped.extractall(root)
    return root


def test_the_package_contains_the_worker_and_the_repo_relative_code(tmp_path):
    root = _unpack(tmp_path)
    assert (root / cl.WORKER_NAME).is_file()
    code_root = root / "research" / "CAS_META_2_COMPOSITION"
    assert (code_root / "cas_meta2" / "graph_teaching"
            / "candidate_experiment.py").is_file()
    assert (code_root / "cas_meta2" / "graph_teaching"
            / "candidate_run.py").is_file()
    assert (code_root / "cas_meta2" / "teaching_cycle").is_dir()


def test_the_package_carries_every_file_the_code_reads_at_run_time():
    """The bundle and the fixture, at the paths the deployed code resolves.

    Not a name check: the packaged path is compared with the constant the
    unpacked module computes from its own location, which is what the deployed
    worker actually reads.
    """
    with zipfile.ZipFile(_package()) as zipped:
        members = set(zipped.namelist())
    expected = cl.package_data_files()
    assert expected == tuple(sorted(expected))
    assert set(expected) <= members, sorted(set(expected) - members)
    for path in (cube_node.pinned_bundle_path(),
                 verified_teaching.pinned_fixture_path()):
        relative = Path(path).resolve().relative_to(curriculum.ROOT.resolve())
        assert ("research/CAS_META_2_COMPOSITION/" + relative.as_posix()) in members
    # The bundle is the required one; say so in the same place it is asserted.
    assert (cube_node.pinned_bundle_path().name
            in {Path(name).name for name in expected})


def test_the_unpacked_package_resolves_the_bundle_where_it_ships(tmp_path):
    """The bundle path computed inside the unpacked package must exist there."""
    root = _unpack(tmp_path)
    script = (
        "import sys\n"
        "from pathlib import Path\n"
        "ROOT = Path(sys.argv[1])\n"
        "sys.path.insert(0, str(ROOT / 'research/CAS_META_2_COMPOSITION'))\n"
        "from cas_meta2.graph_teaching import cube_node, verified_teaching\n"
        "print(cube_node.pinned_bundle_path().is_file())\n"
        "print(verified_teaching.pinned_fixture_path().is_file())\n"
        "print(cube_node.load_bundle()['schema_version'])\n"
    )
    result = subprocess.run([sys.executable, "-c", script, str(root)],
                            capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.split() == ["True", "True",
                                     cube_node.CUBE_BUNDLE_SCHEMA]


def test_the_worker_resolves_its_import_root_like_the_proven_worker():
    worker = cl.render_worker()
    assert "sys.path.insert(0, str(ROOT / 'research/CAS_META_2_COMPOSITION'))" in worker
    assert "ROOT = Path(__file__).resolve().parent" in worker
    assert worker.index("sys.path.insert") < worker.index(
        "from cas_meta2.graph_teaching import candidate_experiment as ce")
    assert "status': 'WORKER_FAILED'" in worker
    assert worker.count("result.json") >= 3


def test_the_unpacked_package_imports_and_builds_the_pilot_inputs(tmp_path):
    """The real deployed layout, executed: import plus the frozen inputs."""
    root = _unpack(tmp_path)
    script = (
        "import json, sys\n"
        "from pathlib import Path\n"
        "ROOT = Path(sys.argv[1])\n"
        "sys.path.insert(0, str(ROOT / 'research/CAS_META_2_COMPOSITION'))\n"
        "from cas_meta2.graph_teaching import candidate_experiment as ce\n"
        "from cas_meta2.graph_teaching import candidate_run as cr\n"
        "inputs = ce.build_inputs()\n"
        "print(json.dumps({'records': len(inputs['records']),\n"
        "                  'probe': len(inputs['probe']),\n"
        "                  'groups': {k: len(v) for k, v in inputs['groups'].items()},\n"
        "                  'conditions': list(ce.CONDITIONS),\n"
        "                  'updates': ce.UPDATES_PER_CONDITION}))\n"
    )
    result = subprocess.run([sys.executable, "-c", script, str(root)],
                            capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stderr[-2000:]
    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert report == {"records": 8, "probe": 44,
                      "groups": {"taught_whole_answer": 3, "taught_component": 5,
                                 "untaught_probe": 44},
                      "conditions": ["checked_component_teaching",
                                     "final_answer_only"],
                      "updates": 64}


def test_the_unpacked_package_runs_both_conditions_with_stub_learners(tmp_path):
    """The full two-condition pilot, executed from the unpacked artifact."""
    root = _unpack(tmp_path)
    driver = tmp_path / "driver.py"
    driver.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "ROOT = Path(sys.argv[1])\n"
        "sys.path.insert(0, str(ROOT / 'research/CAS_META_2_COMPOSITION'))\n"
        "from cas_meta2.graph_teaching import candidate_experiment as ce\n"
        "\n"
        "class Param:\n"
        "    def __init__(self, v=1.0): self.value = v\n"
        "    def requires_grad_(self, f): return self\n"
        "class Reg: contract_id = 'cas.cjt.operation.^6.decompose/0.2'\n"
        "class Contract:\n"
        "    contract_id = 'cas.cjt.operation.^6.decompose/0.2'\n"
        "    plasticity_groups = ('operation:^6',)\n"
        "class Model:\n"
        "    def __init__(self, fw): self.fw = fw\n"
        "    def named_parameters(self): return sorted(self.fw.parameters.items())\n"
        "class Framework:\n"
        "    def __init__(self):\n"
        "        self.parameters = {'module.left.weight': Param(),\n"
        "                           'module.right.weight': Param(),\n"
        "                           'encoder.projection': Param()}\n"
        "        self.operation_registrations = [Reg()]\n"
        "        self.module = Model(self)\n"
        "    def build_decompose_model(self, seed=None): return self.module\n"
        "    def contract_for(self, cid): return Contract()\n"
        "    def resolve_plasticity_groups(self, model, role, contract):\n"
        "        return ['module.left.weight', 'module.right.weight']\n"
        "    def tensor_bytes(self, parameter):\n"
        "        return json.dumps(parameter.value).encode('utf-8')\n"
        "class Learner:\n"
        "    def __init__(self, layout): self.layout = layout; self.steps = 0\n"
        "    def predict(self, task):\n"
        "        enc = self.layout.get(task['record_id']) or task\n"
        "        return enc['encoded_options'][enc['encoded_correct_index']]\n"
        "    def step(self, task): self.steps += 1; return 0.5\n"
        "    def checkpoint_identity(self): return 'STUB-%d' % self.steps\n"
        "inputs = ce.build_inputs()\n"
        "def framework_factory(seed):\n"
        "    fw = Framework(); return fw, fw.module\n"
        "def learner_factory(*, framework, model, arm, records, layout):\n"
        "    return Learner(layout)\n"
        "def writer(learner, identity):\n"
        "    return {'path': 'memory://' + identity, 'identity': identity}\n"
        "def verifier(saved, identity): return saved['identity'] == identity\n"
        "result = ce.launch(run_id='package-rehearsal',\n"
        "                   records=inputs['records'], probe=inputs['probe'],\n"
        "                   groups=inputs['groups'],\n"
        "                   framework_factory=framework_factory,\n"
        "                   learner_factory=learner_factory,\n"
        "                   authorization={'owner_go': True,\n"
        "                                  'run_id': 'package-rehearsal'},\n"
        "                   checkpoint_writer=writer,\n"
        "                   checkpoint_verifier=verifier)\n"
        "print(json.dumps({'matched': result['matched_initial_weights'],\n"
        "                  'updates': result['counters']['actual_optimizer_updates'],\n"
        "                  'probe_questions': result['probe_questions'],\n"
        "                  'primary_total': result['results']\n"
        "                      ['checked_component_teaching']['primary_measure']\n"
        "                      ['after_total'],\n"
        "                  'probe_total': result['results']\n"
        "                      ['final_answer_only']['probe_measure']['after_total'],\n"
        "                  'stages': len(result['results']\n"
        "                      ['checked_component_teaching']['predictions'])}))\n",
        encoding="utf-8")
    result = subprocess.run([sys.executable, str(driver), str(root)],
                            capture_output=True, text=True, timeout=600)
    assert result.returncode == 0, result.stderr[-3000:]
    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert report["matched"] is True
    assert report["updates"] == 128
    assert report["probe_questions"] == 44
    assert report["primary_total"] == 3
    assert report["probe_total"] == 44
    assert report["stages"] == 64


@pytest.mark.parametrize("needle", ["REMOTE_FINISHED", "results/result.json"])
def test_the_worker_reports_completion_and_uploads_the_marker_last(needle):
    worker = cl.render_worker()
    assert needle in worker
    assert worker.index("results/manifest.json") < worker.index("results/result.json")
