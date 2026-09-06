"""Pure new-input and call-identity checks; the AWS runner is not executed."""
from copy import deepcopy
import sys

import pytest

from cas_meta3 import learned_reuse as reuse
from cas_meta3 import learning_evidence as evidence


def public(value=0.1):
    return {"problem": "Synthetic reuse fixture, not a model inference task.",
        "observations": [{"slot": slot, "tag": "FIXTURE_" + str(slot), "values": [value] * 8} for slot in range(3)]}


def test_import_is_pure_and_no_aws_flags_means_no_execution(monkeypatch):
    monkeypatch.delenv("CAS_META3_RUN_GPU_DEMO", raising=False)
    assert "torch" not in sys.modules and "boto3" not in sys.modules
    with pytest.raises(reuse.native_support.NativeDemoError, match="META3_EXPLICIT_AWS_GPU_JOB_REQUIRED"):
        reuse.run_reuse_suite(job="fake-job", store_path="not-read", expected_digest="a" * 64,
            trust_inputs={}, source_public={}, public_cases=[], output="not-created", native_output="not-created")
    assert "torch" not in sys.modules and "boto3" not in sys.modules


def test_distinct_float32_inputs_are_accepted_without_neural_work():
    source = public()
    reuse.check_public_cases(source, [public(0.2), public(-0.3)], 0, evidence.digest(source))


@pytest.mark.parametrize("value", [[], [public()] * 5, None])
def test_case_count_is_bounded(value):
    source = public()
    with pytest.raises(reuse.ReuseError, match="BOUNDED_REUSE_CASES_REQUIRED"):
        reuse.check_public_cases(source, value, 0, evidence.digest(source))


@pytest.mark.parametrize("binding", [True, -1, 3, "0"])
def test_binding_must_be_an_exact_supported_integer(binding):
    source = public()
    with pytest.raises(reuse.ReuseError, match="REUSE_BINDING_INVALID"):
        reuse.check_public_cases(source, [public(0.2)], binding, evidence.digest(source))


def test_source_observations_must_match_the_learning_proof_hash():
    with pytest.raises(reuse.ReuseError, match="SOURCE_PUBLIC_NOT_BOUND_TO_LEARNING"):
        reuse.check_public_cases(public(), [public(0.2)], 0, "d" * 64)


@pytest.mark.parametrize("cases", [[public()], [public(0.2), public(0.2)], [public(0.100000000001)]])
def test_text_or_python_float_changes_are_not_new_native_inputs(cases):
    source = public()
    cases = deepcopy(cases)
    cases[0]["problem"] = "Different words cannot make identical float32 values new."
    with pytest.raises(reuse.ReuseError, match="REUSE_REQUIRES_NEW_SELECTED_INPUT_VALUES"):
        reuse.check_public_cases(source, cases, 0, evidence.digest(source))


def test_changing_only_an_unselected_observation_is_not_new_input():
    source = public()
    case = public()
    case["observations"][1]["values"] = [0.2] * 8
    with pytest.raises(reuse.ReuseError, match="REUSE_REQUIRES_NEW_SELECTED_INPUT_VALUES"):
        reuse.check_public_cases(source, [case], 0, evidence.digest(source))


@pytest.mark.parametrize("source,case", [(public(2), public(0.2)), (public(), public(-2))])
def test_reuse_stays_inside_registered_numeric_domain(source, case):
    with pytest.raises(reuse.ReuseError, match="REUSE_INPUT_DOMAIN_EXCEEDED"):
        reuse.check_public_cases(source, [case], 0, evidence.digest(source))


def events_fixture():
    argument = {"kind": "observation", "slot": 0, "sha256": "b" * 64}
    refs = [{"kind": "effect", "effect_id": "effect-" + str(i)} for i in range(2)]
    events = []
    for i in range(2):
        events.extend([{"kind": "ENTER", "address": "entry/" + str(i), "call_id": "call-" + str(i), "input_reference": deepcopy(argument)},
            {"kind": "RETURN", "address": "entry/" + str(i), "reference": deepcopy(refs[i])}])
    events.append({"kind": "RETURN", "address": "entry", "reference": deepcopy(refs[0])})
    return {"final_reference": deepcopy(refs[0])}, events, {"call_count": 2, "return_call": 0,
        "call_sites": [{"functional_address": "entry:main/steps/0"}, {"functional_address": "entry:main/steps/1"}]}


def test_first_returned_effect_identity_is_preserved_after_second_call():
    result, events, link = events_fixture()
    mapping = reuse.check_root_calls(result, events, link)
    assert mapping["selected_effect_id"] == "effect-0"
    assert mapping["returned_effect_ids"] == ["effect-0", "effect-1"]
    assert mapping["call_ids"] == ["call-0", "call-1"]


@pytest.mark.parametrize("change", ["missing_call", "duplicate_call_id", "changed_input", "duplicate_effect_id", "wrong_final", "wrong_root_return"])
def test_root_call_or_return_mismatch_is_refused(change):
    result, events, link = events_fixture()
    if change == "missing_call":
        events.pop(0)
    elif change == "duplicate_call_id":
        events[2]["call_id"] = events[0]["call_id"]
    elif change == "changed_input":
        events[2]["input_reference"]["slot"] = 1
    elif change == "duplicate_effect_id":
        events[3]["reference"] = deepcopy(events[1]["reference"])
    elif change == "wrong_final":
        result["final_reference"] = deepcopy(events[3]["reference"])
    else:
        events[-1]["reference"] = deepcopy(events[3]["reference"])
    with pytest.raises(reuse.ReuseError):
        reuse.check_root_calls(result, events, link)


def test_source_identity_includes_every_new_execution_dependency():
    identity = reuse.source_identity()
    assert set(identity["learned_files_sha256"]) == set(reuse.SOURCE_FILES)
    assert identity["native"]["protected_files"] == 316
    assert "torch" not in sys.modules


@pytest.mark.parametrize("failure", [None, "reference", "compatibility", "candidate", "run_count"])
def test_runner_protocol_with_explicitly_mocked_native_backend(tmp_path, monkeypatch, failure):
    # This tests orchestration only. Native functions and AWS hardware are fake.
    # The real store, evidence reader, linker and new-input checks still run.
    from types import SimpleNamespace
    from test_learning_evidence import Fixture
    from test_learned_package import fixture as package_fixture, arguments
    from test_learned_store import trust
    from cas_meta3.learned_store import LearnedCandidateStore
    from cas_meta3 import learned_package as packages

    source = public()
    fixture = Fixture()
    fixture.source = packages.META2_SOURCE_SHA
    for item in (fixture.manifest, fixture.inspection, fixture.audit):
        item["source_sha"] = fixture.source
    fixture.predictions[0]["public_sha256"] = evidence.digest(source)
    inputs = fixture.inputs()
    proof = evidence.bind_learning_evidence(**inputs)
    package = package_fixture()
    package["program"] = deepcopy(fixture.action["program"])
    package["binding"] = package["io"]["input"]["slot"] = 0
    package["io"]["output"]["producer_cjt_id"] = "C"
    for name in ("source_program_sha256", "policy_source_sha256", "policy_checkpoint_sha256", "producer_source_sha"):
        package["provenance"][name] = proof[name]
    package["provenance"]["producer_evidence_sha256"] = proof["receipt_sha256"]
    del inputs["expected_action"]
    inputs.update(arguments(package))
    path = tmp_path / "records" / "candidate.sqlite"
    LearnedCandidateStore(path).save(package, **inputs)
    store_before = path.read_bytes()
    output, native_output = tmp_path / "result", tmp_path / "native"
    alarms = []
    fake_signal = SimpleNamespace(SIGALRM=1, ITIMER_REAL=0, getitimer=lambda _: (0.0, 0.0),
        getsignal=lambda _: None, signal=lambda *_: None, alarm=lambda value: alarms.append(value))
    monkeypatch.setattr(reuse, "signal", fake_signal)
    monkeypatch.setattr(reuse, "os", SimpleNamespace(name="posix", getpid=lambda: 12345))
    monkeypatch.setattr(reuse, "ROOT", tmp_path)
    monkeypatch.setattr(reuse.native_support, "aws_guard", lambda job: job)
    monkeypatch.setattr(reuse, "source_identity", lambda: {"synthetic_mock_only": True})
    monkeypatch.setattr(reuse.native_support, "checked_paths", lambda *args, **kwargs: (output, native_output))
    monkeypatch.setattr(reuse, "reference_compatibility", lambda *_: {} if failure == "compatibility" else inputs["trusted_compatibility"])

    class FakeNative:
        calls = []

        def reference_task(self, task, path, device):
            self.calls.append("reference")
            return {"synthetic_mock_only": True, "reference": True}

        def verify_reference_task(self, task, reference):
            self.calls.append("reference_check")
            return {"task_correct": failure != "reference", "native_runs": 6}

        def execute_task(self, public, action, path, device):
            self.calls.append("candidate")
            path.mkdir()
            result, events, _ = events_fixture()
            reuse.native_support.save(path / "composition_events.json", events)
            return result

        def verify_task(self, task, candidate, reference):
            self.calls.append("candidate_check")
            return {"task_correct": failure != "candidate", "native_runs": 5 if failure == "run_count" else 6,
                    "stored_call_tree_verified": True}

    native = FakeNative()
    monkeypatch.setattr(reuse.native_support, "cuda_runtime", lambda job: (native, "MOCK_NOT_CUDA", {"synthetic_mock_only": True}))
    kwargs = dict(job="mock-only", store_path=path, expected_digest=inputs["expected_digest"],
        trust_inputs=trust(inputs), source_public=source, public_cases=[public(0.2), public(0.3)],
        output=output, native_output=native_output)
    if failure is None:
        result = reuse.run_reuse_suite(**kwargs)
        assert result["native_runs"] == 24 and len(result["cases"]) == 2
        assert result["environment"] == {"synthetic_mock_only": True}
        assert result["qualification_status"] == "UNQUALIFIED"
        assert not any(result[key] for key in ("promotion_granted", "learning_performed", "learned_retrieval_performed",
            "writer_exit_independently_verified", "retention_tested", "rollback_tested"))
        assert native.calls == ["reference", "reference_check", "candidate", "candidate_check"] * 2
    else:
        with pytest.raises(reuse.ReuseError):
            reuse.run_reuse_suite(**kwargs)
        assert (output / "reuse_failure.json").is_file()
        assert not (output / "reuse_receipt.json").exists()
        if failure in ("reference", "compatibility"):
            assert "candidate" not in native.calls
    assert path.read_bytes() == store_before
    assert alarms == [reuse.MAX_WALL_SECONDS, 0]
    assert "torch" not in sys.modules and "boto3" not in sys.modules
