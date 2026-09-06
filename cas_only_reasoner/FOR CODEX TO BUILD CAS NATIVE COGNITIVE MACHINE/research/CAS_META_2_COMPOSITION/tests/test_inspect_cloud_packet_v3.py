"""Pure/mock v3 evidence checks. No GPU, checkpoint loading or reserved draw."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("outer_v3_under_test", ROOT / "tools/inspect_cloud_packet_v3.py")
v3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v3)
pytestmark = pytest.mark.not_gpu


class Packet:
    def __init__(self, rows):
        self.rows = {name: value if isinstance(value, bytes) else v3.canonical(value) for name, value in rows.items()}
        self.inventory = {name: {"path": name, "bytes": len(raw), "sha256": v3.sha(raw)} for name, raw in self.rows.items()}
    def raw(self, name, *unused):
        return self.rows[name]
    def json(self, name):
        return v3.json_bytes(self.raw(name))
    def same_hash(self, name, expected):
        v3.require(self.inventory[name]["sha256"] == expected, "TEST_PACKET_HASH_MISMATCH")


@pytest.mark.parametrize("size,pattern", [(64, v3.SHA256), (40, v3.SHA1)])
def test_exact_hash_patterns_accept_real_hex_and_reject_bad_suffixes(size, pattern):
    assert pattern.fullmatch("a" * size)
    for bad in ("A" * size, "g" * size, "a" * (size - 1), "a" * (size + 1), "a" * size + "\n", "a" * size + "\\Z"):
        assert not pattern.fullmatch(bad)


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}'])
def test_strict_json_refuses_duplicate_and_nonfinite_values(raw):
    with pytest.raises(ValueError):
        v3.json_bytes(raw)


def cleanup_record(phases=("baseline", "final")):
    return {"runtime_versions": {"torch": "2.11.0+cu128", "cuda": "12.8"},
        "device": "cuda:0", "gpu_name": "TEST_ONLY_GPU", "gpu_total_memory_bytes": 1024,
        "numerical_settings_before": deepcopy(v3.SETTINGS), "numerical_settings_after": deepcopy(v3.SETTINGS),
        "workspace_cleanup_api": {"name": "torch._C._cuda_clearCublasWorkspaces", "callable_verified": True, "documented_version": "2.11"},
        "cleanup": {phase: {"completed": True, "steps": list(v3.CLEANUP_STEPS),
            "before": {"allocated_bytes": 128, "reserved_bytes": 256},
            "after": {"allocated_bytes": 0, "reserved_bytes": 0}} for phase in phases}}


def test_cleanup_requires_exact_two_zero_phases():
    v3._runtime_cleanup(cleanup_record(), {"gpu": "TEST_ONLY_GPU"}, ("baseline", "final"))


@pytest.mark.parametrize("fault", ["allocated", "reserved", "bool_counter", "missing_phase", "steps", "completed",
                                      "settings", "version", "device", "api", "failure", "gpu"])
def test_cleanup_claim_cannot_hide_failed_gate(fault):
    row = cleanup_record()
    if fault in ("allocated", "reserved"):
        row["cleanup"]["final"]["after"][fault + "_bytes"] = 1
    elif fault == "bool_counter":
        row["cleanup"]["final"]["after"]["allocated_bytes"] = False
    elif fault == "missing_phase":
        row["cleanup"].pop("baseline")
    elif fault == "steps":
        row["cleanup"]["final"]["steps"].pop()
    elif fault == "completed":
        row["cleanup"]["final"]["completed"] = False
    elif fault == "settings":
        row["numerical_settings_after"]["tf32_matmul"] = True
    elif fault == "version":
        row["runtime_versions"]["torch"] = "2.10"
    elif fault == "device":
        row["device"] = "cpu"
    elif fault == "api":
        row["workspace_cleanup_api"]["callable_verified"] = False
    elif fault == "failure":
        row["failures"] = [{"message": "failed"}]
    else:
        row["gpu_name"] = "OTHER"
    with pytest.raises(ValueError):
        v3._runtime_cleanup(row, {"gpu": "TEST_ONLY_GPU"}, ("baseline", "final"))


def gate_rows():
    return [{"layer": i, "active_queries_per_head": [96, 95, 100, 99], "valid_queries_per_head": [100] * 4,
             "active_fraction_per_head": [.96, .95, 1., .99], "all_heads_meet_active_fraction": True,
             "valid_queries": 400, "active_queries": 390, "active_fraction": .975} for i in range(2)]


def test_each_head_95_percent_is_verified_not_just_average():
    geometry = {"selected_input_lengths": [100]}
    v3._gate_layers(gate_rows(), geometry)
    rows = gate_rows()
    rows[0].update(active_queries_per_head=[80, 100, 100, 100], active_fraction_per_head=[.8, 1., 1., 1.],
                   active_queries=380, active_fraction=.95)
    with pytest.raises(ValueError, match="EVERY_HEAD"):
        v3._gate_layers(rows, geometry)


@pytest.mark.parametrize("fault", ["bool", "wrong_sum", "wrong_fraction", "missing_layer", "reordered", "valid_count"])
def test_gate_counter_and_layer_tampering_is_rejected(fault):
    rows = gate_rows()
    if fault == "bool":
        rows[0]["active_queries_per_head"][0] = True
    elif fault == "wrong_sum":
        rows[0]["active_queries"] += 1
    elif fault == "wrong_fraction":
        rows[0]["active_fraction_per_head"][0] = .97
    elif fault == "missing_layer":
        rows.pop()
    elif fault == "reordered":
        rows.reverse()
    else:
        rows[0]["valid_queries_per_head"][0] = 101
    with pytest.raises(ValueError):
        v3._gate_layers(rows, {"selected_input_lengths": [100]})


def xml_for(names):
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", tests=str(len(names)), failures="0", errors="0", skipped="0")
    for name in names:
        ET.SubElement(suite, "testcase", name=name, classname="tests.fixture")
    return ET.tostring(root)


@pytest.mark.parametrize("fault", ["missing", "duplicate", "hidden_failure", "skip", "doctype", "count"])
def test_junit_full_case_coverage_is_checked(fault):
    names = ["one", "two"]
    raw = xml_for(names)
    if fault == "missing":
        raw = xml_for(["one"])
    elif fault == "duplicate":
        raw = xml_for(["one", "one"])
    elif fault == "hidden_failure":
        raw = raw.replace(b' /></testsuite>', b'><failure /></testcase></testsuite>')
    elif fault == "skip":
        raw = raw.replace(b'skipped="0"', b'skipped="1"')
    elif fault == "doctype":
        raw = b'<!DOCTYPE x>' + raw
    else:
        raw = raw.replace(b'tests="2"', b'tests="3"')
    if fault == "hidden_failure":
        root = ET.fromstring(xml_for(names))
        ET.SubElement(root.find(".//testcase"), "failure")
        raw = ET.tostring(root)
    with pytest.raises(ValueError):
        v3._xml_cases(raw, set(names))


def test_early_policy_exactly_27_and_explicit_gpu_marker(monkeypatch):
    old = {"old" + str(i) for i in range(4)}
    monkeypatch.setattr(v3, "legacy", SimpleNamespace(GPU_CASES={"policy": old}))
    names = old | v3.COPY_GPU_CASES | v3.LOSS_GPU_CASES
    assert len(names) == 27
    prefix = "cloud_job/gpu_policy"
    command = ["python", "-m", "pytest", "-m", "gpu", "tests/test_policy_gpu.py", "tests/test_policy_v3_gpu.py",
               "tests/test_loss_v3_gpu.py", "-q", "--junitxml", "/root/gpu_policy_tests.xml", "-p", "no:cacheprovider"]
    packet = Packet({prefix + "_receipt.json": {"passed": 27, "tests": 27, "failures": 0, "errors": 0, "skipped": 0},
        prefix + "_tests.xml": xml_for(sorted(names)), prefix + "_command.json": command, prefix + "_tests.log": b"mock"})
    assert v3._gpu_gate(packet, "policy")["passed"] == 27
    packet.rows[prefix + "_command.json"] = v3.canonical(command + ["-k", "single"])
    with pytest.raises(ValueError, match="COMMAND"):
        v3._gpu_gate(packet, "policy")


def test_source_map_checks_new_assets_tests_and_requirements_before_legacy(monkeypatch):
    extras = ("EXPERIMENT_V3.json", "requirements-gpu.txt", "cas_meta2/exclusions_v3.json",
              "cas_meta2/development_exclusions_v3.json", "tests/fixture.py")
    expected = {"cas_meta2/a.py": "a" * 64, "pyproject.toml": "b" * 64}
    source = {**expected, **{name: "c" * 64 for name in extras}}
    campaign = {"experiment": {"profile": "learning_v3"}, "source": source}
    monkeypatch.setattr(v3, "profiles", SimpleNamespace(validate_manifest=lambda m: campaign["experiment"]))
    from cas_meta2 import campaign_v3
    monkeypatch.setattr(campaign_v3, "SOURCE_TESTS", ("fixture.py",))
    checked = []
    monkeypatch.setattr(v3, "source_file", lambda m, n: checked.append(n) or source[n])
    def legacy(view, manifest, sha):
        assert view["source"] == expected
        return {"source_files_bound": 2}
    monkeypatch.setattr(v3, "legacy", SimpleNamespace(_source_binding=legacy))
    before = deepcopy(campaign)
    assert v3._source_binding(campaign, {}, "d" * 40)["source_files_bound"] == 7
    assert campaign == before and set(extras) <= set(checked)


def test_existing_diagnostic_cold_json_uses_explicit_dataset_identity_and_order(tmp_path, monkeypatch):
    # Repeats only a previously exposed seed; it never draws production seed 20260919.
    from cas_meta2 import curriculum_v3 as data
    from cas_meta2.curriculum import graph_signature
    monkeypatch.setattr(v3, "curriculum", data, raising=False)
    target = tmp_path / "already_exposed_914701"
    manifest = data.write_dataset(target, seed=914701, counts={"train": 48, "validation": 6, "test": 6})
    packet = Packet({v3.BASE + "dataset/" + path.name: path.read_bytes() for path in target.iterdir()})
    exposed = data.registered_development_exclusions()
    rows = [task for name in ("train", "validation", "test_private")
            for task in packet.json(v3.BASE + "dataset/" + name + ".json")]
    assert {graph_signature(t["target"]["program"]) for t in rows} <= exposed
    original = dict(packet.rows)
    assert v3._reconstruct_dataset(packet, manifest, None) == manifest
    assert packet.rows == original
    wrong = deepcopy(manifest)
    wrong["dataset_id"] = "0" * 64
    with pytest.raises(ValueError):
        v3._reconstruct_dataset(packet, wrong, None)
    sample_name = v3.BASE + "dataset/train.json"
    tasks = packet.json(sample_name)
    task = next(t for t in tasks if len(t["provenance"]["definition_order"]) > 1)
    task["provenance"]["definition_order"].reverse()
    packet.rows[sample_name] = v3.canonical(tasks)
    with pytest.raises(ValueError):
        v3._reconstruct_dataset(packet, manifest, None)


def test_failed_outer_inspection_writes_new_typed_failure_without_touching_input(tmp_path, monkeypatch):
    monkeypatch.setattr(v3, "ROOT", tmp_path)
    source = tmp_path / "packet.bin"
    source.write_bytes(b"mock-not-zip")
    before = source.read_bytes()
    output = tmp_path / "records/rejected"
    result = v3.inspect_packet(source, expected_sha256="a" * 64, source_sha="b" * 40, job="fixture",
                               output=output, source_manifest={})
    assert result["status"] == "CAS_META_2_V3_PACKET_REJECTED"
    assert result["completed_run_evidence_verified"] is False
    assert result["checkpoint_loading_performed"] is False
    assert (output / "inspection_receipt.json").is_file()
    assert source.read_bytes() == before
    with pytest.raises(ValueError):
        v3.inspect_packet(source, expected_sha256="a" * 64, source_sha="b" * 40, job="fixture",
                          output=output, source_manifest={})


def test_preimport_gate_rejects_manifest_sha_disagreement_before_git(monkeypatch):
    import subprocess
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: pytest.fail("No Git call permitted after invalid identity"))
    with pytest.raises(ValueError, match="EXTERNAL_SOURCE"):
        v3._git_source_precheck({"source_sha": "a" * 40}, "b" * 40)


def test_git_archive_nested_ancestor_directories_are_not_source_entries(tmp_path, monkeypatch):
    import io
    import zipfile
    repo = tmp_path / "repo"
    root = repo / "nested/deep/research/CAS_META_2_COMPOSITION"
    root.mkdir(parents=True)
    monkeypatch.setattr(v3, "ROOT", root)
    prefix = root.relative_to(repo).as_posix() + "/"
    names = ("tools/inspect_cloud_packet_v3.py", "tools/audit_stored_packet_v3.py",
             "tools/experiment_profiles_v3.py", "tools/inspect_cloud_packet.py", "cas_meta2/__init__.py")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("nested/", b"")
        archive.writestr("nested/deep/", b"")
        for name in names:
            archive.writestr(prefix + name, b"# mock committed source\n")
    expected = v3.sha(b"# mock committed source\n")
    manifest = {"source_sha": "a" * 40, "files_sha256": {v3.PILOT + "/" + n: expected for n in names}}
    replies = iter((str(repo), "a" * 40, stream.getvalue()))
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: next(replies))
    monkeypatch.setattr(v3, "source_file", lambda *args: expected)
    result = v3._git_source_precheck(manifest, "a" * 40)
    assert result["python_files_verified_before_import"] == 5


def test_foreign_project_and_neural_preloads_refused_before_dependency_import(monkeypatch):
    monkeypatch.setattr(v3, "_git_source_precheck", lambda *args: {"source_sha": "a" * 40})
    for name in ("cupy", "cas_cjt"):
        monkeypatch.setitem(sys.modules, name, SimpleNamespace())
        with pytest.raises(ValueError, match="PRELOADED"):
            v3._configure({}, "a" * 40)
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setitem(sys.modules, "cas_meta2.foreign_fixture", SimpleNamespace(__file__="/foreign/source.py"))
    with pytest.raises(ValueError, match="PRELOADED"):
        v3._configure({}, "a" * 40)
