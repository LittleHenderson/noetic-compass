"""Pure source/control-flow checks. Synthetic fixtures never prove GPU/native success."""
import ast
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import time
import tomllib

import pytest

from cas_meta2 import campaign_v3 as campaign

pytestmark = pytest.mark.not_gpu
ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "cas_meta2/campaign_v3.py").read_text()
TREE = ast.parse(SOURCE)
SPEC = json.loads((ROOT / "EXPERIMENT_V3.json").read_text())


def section(name):
    node = next(node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name == name)
    return ast.get_source_segment(SOURCE, node)


def test_older_campaign_and_spec_unchanged():
    assert sha256((ROOT / "cas_meta2/campaign_v2.py").read_bytes()).hexdigest() == "e636e112578aeb30065784ed44992b23c50266f9239be680870c4a2bc6684c09"
    assert sha256((ROOT / "EXPERIMENT_V2.json").read_bytes()).hexdigest() == "173fa1b30982186c10d1032a7f839d13f1c4eca4c7d50862aac827c95e67f454"


def test_spec_matches_registered_source_without_constructing_data():
    assert campaign.validate_experiment(deepcopy(SPEC)) == SPEC
    assert sum(campaign.PHASE_SECONDS.values()) == 6600
    assert SPEC["training"]["policy"]["cas_initial_saturation_per_max_token"] == 2.0
    assert type(SPEC["training"]["policy"]["cas_initial_saturation_per_max_token"]) is float


@pytest.mark.parametrize("path,value", [
    (("schema",), "cas-meta2-experiment/2"), (("profile",), "learning_v2"),
    (("entrypoint",), "cas_meta2.campaign_v2"), (("training", "epochs"), 61),
    (("training", "curriculum_seed"), 20260917), (("training", "batch_size"), 8),
    (("training", "policy", "cas_initial_saturation_per_max_token"), 2),
    (("training", "training_examples_per_depth"), 1023), (("curriculum", "seed"), 9),
    (("curriculum", "exclusions", "combined_count"), 4312),
    (("curriculum", "allowed_cjts"), ["A","B","C","R"]),
    (("execution", "phase_seconds", "native_evaluation"), 100),
    (("execution", "automatic_retries"), 1), (("execution", "hard_resource_cutoff_seconds"), 9000),
    (("gpu_gates", "campaign", "trainer_integration"), 0),
    (("gpu_gates", "preflight"), "cas_meta2.gpu_preflight_v2.run_preflight"),
    (("evaluation", "arms"), ["rule"]), (("evaluation", "checkpoints", "format"), "cas-meta2-candidate-checkpoint/2"),
    (("selection", "train_probe_used_for_selection"), True),
    (("selection", "priority"), ["teacher forcing"]),
    (("loss", "semantic_weight"), 1), (("protected", "executor"), "fake_executor")])
def test_changed_registered_behavior_rejected(path, value):
    spec = deepcopy(SPEC)
    destination = spec
    for key in path[:-1]:
        destination = destination[key]
    destination[path[-1]] = value
    with pytest.raises(ValueError):
        campaign.validate_experiment(spec)


def test_authorization_precedes_any_neural_import():
    run = section("run")
    assert run.index("experiment_identity()") < run.index("from .train_v3 import")
    assert "train_v2" not in SOURCE and "gpu_preflight_v2" not in SOURCE
    for node in TREE.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            assert "torch" not in ast.unparse(node)
    assert "sys.platform" in section("experiment_identity")


def test_identity_has_exact_launcher_fields(monkeypatch):
    monkeypatch.setattr(campaign.sys, "platform", "linux")
    for key, value in {"CAS_META2_EXPERIMENT_PROFILE":"learning_v3",
        "CAS_META2_EXPERIMENT_ENTRYPOINT":"cas_meta2.campaign_v3",
        "CAS_META2_EXPERIMENT_SPEC_SHA256":campaign._hash(ROOT / "EXPERIMENT_V3.json"),
        "CAS_META2_RUN_GPU_TESTS":"1", "CAS_META2_AWS_JOB_ID":"cas-meta2-SYNTHETIC-no-provider"}.items():
        monkeypatch.setenv(key, value)
    identity, spec = campaign.experiment_identity()
    assert set(identity) == {"profile","entrypoint","spec_path","spec_sha256"}
    assert spec == SPEC
    monkeypatch.delenv("CAS_META2_RUN_GPU_TESTS")
    with pytest.raises(ValueError, match="AUTHORIZATION_REQUIRED"):
        campaign.experiment_identity()


def test_new_output_is_contained_and_never_overwrites(tmp_path, monkeypatch):
    monkeypatch.setattr(campaign, "ROOT", tmp_path.resolve())
    with pytest.raises(ValueError):
        campaign._new_output(tmp_path)
    with pytest.raises(ValueError):
        campaign._new_output(tmp_path.parent / "outside-candidate-fixture")
    created = campaign._new_output(tmp_path / "new")
    assert created.is_dir()
    with pytest.raises(ValueError):
        campaign._new_output(created)


def test_source_inventory_covers_assets_gpu_sources_and_spec():
    inventory = campaign._source_identity()
    assert {"EXPERIMENT_V3.json", "cas_meta2/exclusions_v3.json", "cas_meta2/development_exclusions_v3.json",
        "cas_meta2/campaign_v3.py", "cas_meta2/train_v3.py", "cas_meta2/gpu_preflight_copy_v3.py",
        "cas_meta2/gpu_preflight_v3.py", "tests/test_train_v3_gpu.py",
        "tests/test_gpu_preflight_copy_v3_gpu.py"} <= set(inventory)
    assert all(len(value) == 64 for value in inventory.values())


def test_phase_caps_reserve_real_prediction_and_native_work():
    source = section("run")
    assert "PHASE_SECONDS[\"native_evaluation\"] + PHASE_SECONDS[\"final_evidence\"]" in source
    assert "V3_INSUFFICIENT_TIME_FOR_REGISTERED_LEARNING_AND_EVALUATION_RESERVES" in source
    assert source.index("V3_INSUFFICIENT_TIME_FOR_REGISTERED") < source.index("learned = train_and_seal(")
    assert "_arm_deadline(learning_deadline)" in source
    assert "max_training_seconds" not in source  # Registered config is not silently rewritten.
    assert "signal.SIGKILL" in section("_stop_group")
    assert "start_new_session=os.name == \"posix\"" in section("_run_process")


def test_data_constructor_uses_separate_explicit_exclusions_only(tmp_path, monkeypatch):
    commands=[]
    def fake_process(command, directory, deadline, **kwargs):
        commands.append(command)
        directory.mkdir()
        (directory / "process_receipt.json").write_text('{"SYNTHETIC":true}')
        data = tmp_path / "dataset"
        data.mkdir()
        (data / "dataset_manifest.json").write_text('{"SYNTHETIC":true}')
        return {"returncode":0}
    monkeypatch.setattr(campaign, "_run_process", fake_process)
    assert campaign._construct_data(tmp_path, 123, time.monotonic()+60) == tmp_path/"dataset"
    assert "registered_development_exclusions()" in commands[0][3]
    assert "curriculum_v3" in commands[0][3]
    assert commands[0][-1] == "123"
    receipt=json.loads((tmp_path/"dataset_construction_receipt.json").read_text())
    assert receipt["separate_process"] and receipt["combined_excluded_graphs"] == 4488


def test_public_data_check_hashes_private_without_parsing(tmp_path, monkeypatch):
    import cas_meta2.curriculum_v3 as curriculum
    names=("train.json","validation.json","test_public.json","test_private.json")
    for name in names:
        (tmp_path/name).write_bytes(b"PRIVATE IS NOT JSON" if "private" in name else b"[]")
    manifest={"sha256":{name:campaign._hash(tmp_path/name) for name in names}}
    (tmp_path/"dataset_manifest.json").write_text(json.dumps(manifest))
    calls=[]
    monkeypatch.setattr(curriculum, "validate_manifest", lambda data, **kwargs: calls.append(kwargs) or {"SYNTHETIC":True})
    result=campaign._validate_data_public(tmp_path,SPEC)
    assert result == {"SYNTHETIC":True}
    assert calls[0]["expected_seed"] == 20260919
    assert len(calls[0]["excluded_graph_signatures"]) == 177


@pytest.mark.parametrize("fault", ["failure","error","skipped","too_few","duplicate"])
def test_junit_does_not_promote_partial_or_skipped_checks(tmp_path,fault):
    names=["one","two","three"]
    if fault=="too_few": names=names[:2]
    if fault=="duplicate": names=["one","one","three"]
    content="<testsuites><testsuite>"
    for index,name in enumerate(names):
        inside=("<"+fault+"/>") if index==0 and fault in {"failure","error","skipped"} else ""
        content+='<testcase classname="SYNTHETIC" name="'+name+'">'+inside+"</testcase>"
    content+="</testsuite></testsuites>"
    xml=tmp_path/"junit.xml"
    xml.write_text(content)
    with pytest.raises(RuntimeError,match="FULL_PASS_REQUIRED"):
        campaign._xml_receipt(xml,3)


def test_junit_exact_pass_counts_are_recorded(tmp_path):
    xml=tmp_path/"junit.xml"
    xml.write_text('<testsuites><testsuite><testcase classname="SYNTHETIC" name="a"/><testcase classname="SYNTHETIC" name="b"/></testsuite></testsuites>')
    assert campaign._xml_receipt(xml,2)["passed"] == 2


@pytest.mark.parametrize("exitcode,timedout",[(0,False),(4,False),(None,True)])
def test_process_raw_outputs_and_failures_are_retained(tmp_path,monkeypatch,exitcode,timedout):
    stopped=[]
    class MockProcess:
        pid=123456789
        returncode=exitcode
        def __init__(self,command,**kwargs):
            kwargs["stdout"].write(b"SYNTHETIC stdout")
            kwargs["stderr"].write(b"SYNTHETIC stderr")
        def wait(self,timeout):
            if timedout: raise subprocess.TimeoutExpired("SYNTHETIC",timeout)
            return self.returncode
    monkeypatch.setattr(campaign.subprocess,"Popen",MockProcess)
    monkeypatch.setattr(campaign,"_stop_group",lambda process: stopped.append(process.pid))
    output=tmp_path/"subprocess"
    if exitcode==0:
        assert campaign._run_process(["SYNTHETIC"],output,time.monotonic()+60)["completed"]
    else:
        with pytest.raises(RuntimeError,match="SUBPROCESS_FAILED"):
            campaign._run_process(["SYNTHETIC"],output,time.monotonic()+60)
    receipt=json.loads((output/"process_receipt.json").read_text())
    assert receipt["completed"] is (exitcode==0)
    assert receipt["timed_out"] is timedout
    assert (output/"stdout.txt").read_bytes()==b"SYNTHETIC stdout"
    assert receipt["stdout_sha256"]==campaign._hash(output/"stdout.txt")
    assert bool(stopped) is (exitcode!=0)


def test_campaign_gpu_gate_paths_and_exact_counts():
    assert campaign.GPU_GROUPS == {
        "actual_copy":("tests/test_gpu_preflight_copy_v3_gpu.py",3,"actual_copy_gpu_tests"),
        "trainer":("tests/test_train_v3_gpu.py",2,"trainer_gpu_tests")}
    source=section("run_gpu_gates")
    assert "CAS_META2_COPY_PREFLIGHT_TRAIN_JSON" in source and "CAS_META2_COPY_PREFLIGHT_TRAIN_SHA256" in source
    assert "gpu_gates_v3.json" in source and "basetemp" in source and "junit.xml" in source
    assert "test_private" not in source


def test_gpu_gate_commands_override_project_not_gpu_default(tmp_path, monkeypatch):
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert "not gpu" in project["tool"]["pytest"]["ini_options"]["addopts"]
    data = tmp_path / "dataset"
    data.mkdir()
    (data / "train.json").write_text("[]")
    calls = []
    def fake_process(command, directory, deadline, **kwargs):
        directory.mkdir(parents=True)
        (directory / "process_receipt.json").write_text('{"SYNTHETIC":true}')
        calls.append(command)
        return {"completed": True, "returncode": 0}
    monkeypatch.setattr(campaign, "_run_process", fake_process)
    monkeypatch.setattr(campaign, "_xml_receipt", lambda path, expected: {"passed": expected})
    result = campaign.run_gpu_gates(data, tmp_path / "campaign", time.monotonic() + 60)
    assert result["passed_cases"] == 5 and len(calls) == 2
    for command in calls:
        pytest_start = command.index("pytest")
        pytest_arguments = command[pytest_start + 1:]
        assert pytest_arguments.count("-m") == 1
        assert pytest_arguments[pytest_arguments.index("-m") + 1] == "gpu"


def test_two_authored_gpu_cases_are_guarded_and_do_not_generate_datasets():
    text=(ROOT/"tests/test_train_v3_gpu.py").read_text()
    tree=ast.parse(text)
    cases=[n.name for n in tree.body if isinstance(n,ast.FunctionDef) and n.name.startswith("test_")]
    assert cases==["test_real_paired_update_and_format3_checkpoint_reload",
                   "test_real_cuda_outer_cleanup_with_explicit_mock_inner_frame"]
    assert text.index('CAS_META2_AWS_JOB_ID') < text.index("\nimport torch")
    assert "generate_dataset(" not in text and "write_dataset(" not in text
    assert "test_private.json" not in text and "test_public.json" not in text
    assert "trainer._checkpoint(" in text and "trainer._load_checkpoint(" in text
    assert "optimizer.step()" in text and "torch.equal(actual, expected)" in text
    assert "explicit_mock_inner_frame" in text and 'monkeypatch.setattr(trainer, "_train_and_seal_impl"' in text


def seal_fixture(tmp_path):
    data=tmp_path/"data"; output=tmp_path/"output"; data.mkdir();output.mkdir()
    publics=[{"problem":"SYNTHETIC public "+str(i),"observations":[]} for i in range(72)]
    (data/"test_public.json").write_text(json.dumps(publics))
    (data/"test_private.json").write_bytes(b"PRIVATE_MUST_NOT_BE_PARSED_BEFORE_SEAL")
    predictions=[{"case_index":i,"public_sha256":campaign.canonical_sha256(public),
        "actions":{arm:{"SYNTHETIC_INVALID_ACTION":True} for arm in campaign.ARMS}} for i,public in enumerate(publics)]
    (output/"predictions.jsonl").write_text("\n".join(json.dumps(row) for row in predictions))
    seal={"schema":"cas-meta2-prediction-seal/1","arms":list(campaign.ARMS),"test_examples":72,
        "prediction_count":360,"sha256":campaign._hash(output/"predictions.jsonl"),
        "test_private_labels_loaded":False,"sealed_utc":"2000-01-01T00:00:00+00:00",
        "test_public_sha256":campaign._hash(data/"test_public.json"),
        "test_private_sha256":campaign._hash(data/"test_private.json")}
    return data,output,seal


@pytest.mark.parametrize("field,value",[("prediction_count",359),("test_examples",71),
    ("arms",["rule"]),("test_private_labels_loaded",True),("sha256","0"*64),
    ("test_public_sha256","0"*64),("test_private_sha256","0"*64)])
def test_partial_or_changed_seal_never_opens_private(tmp_path,monkeypatch,field,value):
    data,output,seal=seal_fixture(tmp_path)
    seal[field]=value
    read=campaign._read
    def guarded(path):
        if Path(path).name=="test_private.json": pytest.fail("Private JSON opened before complete seal")
        return read(path)
    monkeypatch.setattr(campaign,"_read",guarded)
    with pytest.raises(RuntimeError):
        campaign.evaluate_sealed(data,output,seal,time.monotonic()+60)
    assert not (output/"test_gold_opening_receipt.json").exists()


def test_complete_seal_opening_receipt_precedes_private_parse(tmp_path,monkeypatch):
    data,output,seal=seal_fixture(tmp_path)
    read=campaign._read
    def guarded(path):
        if Path(path).name=="test_private.json":
            receipt=json.loads((output/"test_gold_opening_receipt.json").read_text())
            assert receipt["prediction_sha256_before_opening"]==seal["sha256"]
            raise RuntimeError("SYNTHETIC_PRIVATE_PARSE_BOUNDARY_REACHED")
        return read(path)
    monkeypatch.setattr(campaign,"_read",guarded)
    with pytest.raises(RuntimeError,match="SYNTHETIC_PRIVATE_PARSE_BOUNDARY_REACHED"):
        campaign.evaluate_sealed(data,output,seal,time.monotonic()+60)


def test_full_dataset_audit_only_after_private_opening():
    source=section("evaluate_sealed")
    assert source.index('tasks = _read(data / "test_private.json")') > source.index('test_gold_opening_receipt.json')
    assert source.index("validate_dataset(") > source.index('tasks = _read(data / "test_private.json")')
    assert "registered_development_exclusions()" in source
    assert "parse_problem(public)" not in source  # Never replace predicted actions with the rule target.
    worker=section("_case_worker")
    assert "admission_error(action, permitted_view(task))" in worker
    assert "ADMITTED_PROGRAM_NATIVE_FAILURE" in worker
    assert "verify_task(task, result, reference)" in worker


def test_full_denominators_and_no_retry_are_explicit():
    assert len(campaign.ARMS)==5
    assert "V3_FINAL_FULL_DENOMINATORS_REQUIRED" in section("run")
    assert 'evaluation["arm_verdicts"] != 360' in section("run")
    assert "evaluation_partial.json" in section("evaluate_sealed")
    assert "process.terminate()" in section("evaluate_sealed")
    assert "V3_TRAINING_CLEANUP_REQUIRED_BEFORE_NATIVE_EVALUATION" in section("run")
    assert '"CAS_META_2_V3_AWS_CAMPAIGN_BLOCKED"' in section("run")
