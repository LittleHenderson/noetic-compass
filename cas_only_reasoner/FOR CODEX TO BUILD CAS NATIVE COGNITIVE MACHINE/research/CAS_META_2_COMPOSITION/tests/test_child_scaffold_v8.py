"""Pure compiler/admission preparation; no native or neural execution."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import sys

import pytest

from cas_meta2 import child_scaffold_v8 as scaffold, native
from cas_meta2.curriculum import graph_signature
from cas_meta2.ir import IRValidationError, validate_program


@pytest.fixture(scope="module")
def enumerated():
    return scaffold.enumerate_candidates()


def test_import_and_enumeration_have_no_neural_or_provider_modules(enumerated):
    assert not {"torch", "casformer", "cas_cjt", "boto3", "botocore"}.intersection(
        name.split(".")[0] for name in sys.modules)
    assert enumerated["no_neural_execution"] and enumerated["no_provider_calls"]


def test_public_catalog_and_full_scopes_exist_before_any_choice():
    public = scaffold.development_scaffold()
    assert set(public["catalog"]) == {"p0", "p1"}
    assert public["choice_spaces"] == {
        "binding": [0, 1, 2], "child": ["p0", "p1"],
        "input": ["arg", "v0", "v1", "v2", "v3"],
        "return": ["arg", "v0", "v1", "v2", "v3", "v4"]}
    assert set(public["public"]) == {"problem", "observations"}
    assert '"p0"' in public["public"]["problem"] and '"p1"' in public["public"]["problem"]
    assert public["has_gold_target"] is False and "target" not in public


def test_all_180_tuples_retained_and_public_admission_counts_exact(enumerated):
    rows = enumerated["candidate_rows"]
    assert len(rows) == 180
    assert len({tuple(row["choice"][k] for k in ("binding", "child", "input", "return")) for row in rows}) == 180
    assert enumerated["counts"] == {"PURE_ADMISSION_PASSED": 90, "TOPOLOGY_REJECTED": 72,
                                   "RETURN_OR_PUBLIC_ADMISSION_REJECTED": 18}
    assert enumerated["static_action_token_range"] == [49, 53]
    assert enumerated["static_native_run_counts"] == [5, 6]
    assert all(row["codec_and_complete_grammar"] and row["ir"]["max_call_depth"] == 2 for row in rows)


def test_arg_and_singleton_trap_inputs_are_reported_not_hidden(enumerated):
    by_input = {name: Counter(row["status"] for row in enumerated["candidate_rows"]
                             if row["choice"]["input"] == name)
                for name in enumerated["per_child_full_input_scope"]}
    for name in ("arg", "v1", "v3"):
        assert by_input[name] == {"PURE_ADMISSION_PASSED": 30, "RETURN_OR_PUBLIC_ADMISSION_REJECTED": 6}
    assert by_input["v0"] == by_input["v2"] == {"TOPOLOGY_REJECTED": 36}
    assert all(row["reason"] == "NATIVE_TOPOLOGY_MISMATCH" for row in enumerated["candidate_rows"]
               if row["status"] == "TOPOLOGY_REJECTED")
    assert all(row["reason"] == "ACCEPTED_EFFECT_RESULT_REQUIRED" for row in enumerated["candidate_rows"]
               if row["status"] == "RETURN_OR_PUBLIC_ADMISSION_REJECTED")


def test_selected_child_only_is_compiled_and_whole_catalog_would_be_unreachable():
    choice = {"binding": 1, "child": "p1", "input": "v3", "return": "v4"}
    action = scaffold.compile_choice(choice)
    assert set(action["program"]["procedures"]) == {"main", "p1"}
    action["program"]["procedures"]["p0"] = scaffold.child_catalog()["p0"]
    with pytest.raises(IRValidationError, match="UNREACHABLE_PROCEDURE"):
        validate_program(action["program"])


def test_six_pairs_change_only_b_versus_r_call_input(enumerated):
    rows = {r["action_sha256"]: r for r in enumerated["candidate_rows"]}
    pairs = enumerated["controlled_input_pairs"]
    assert len(pairs) == 6
    for pair in pairs:
        left, right = [rows[pair[key]] for key in ("left_action_sha256", "right_action_sha256")]
        assert left["input_producer"] == "B" and right["input_producer"] == "R"
        assert left["topology"]["runs"][4]["input_node"] == 1
        assert right["topology"]["runs"][4]["input_node"] == 3
        assert left["graph_signature"] != right["graph_signature"]
        assert left["choice"]["binding"] == right["choice"]["binding"]
        assert left["choice"]["child"] == right["choice"]["child"]
        assert left["choice"]["return"] == right["choice"]["return"] == "v4"
        a, b = deepcopy(left["action"]), deepcopy(right["action"])
        a["program"]["procedures"]["main"]["steps"][4]["input"] = "v3"
        assert a == b
        assert pair["expected_preparation_symbols_if_ACCEPT"] == {"B": "L3", "R": "L1"}
        assert pair["actual_semantic_or_numeric_discrimination"] == "UNEXECUTED"


def test_children_differ_in_cjt_sequence_and_result_producer():
    catalog = scaffold.child_catalog()
    assert [s["cjt_id"] for s in catalog["p0"]["steps"]] == ["C"]
    assert [s["cjt_id"] for s in catalog["p1"]["steps"]] == ["C", "R"]
    assert catalog["p0"]["return"] == "v0" and catalog["p1"]["return"] == "v1"
    a = scaffold.compile_choice({"binding": 0, "child": "p0", "input": "v1", "return": "v4"})
    b = scaffold.compile_choice({"binding": 0, "child": "p1", "input": "v1", "return": "v4"})
    assert graph_signature(a["program"]) != graph_signature(b["program"])


def test_renaming_parent_and_child_names_does_not_create_new_graphs(enumerated):
    renamed = scaffold.enumerate_candidates(parent_names=("v17", "v3", "v12", "v8", "v1"),
                                             child_names=("p12", "p3"))
    assert renamed["counts"] == enumerated["counts"]
    for old, new in zip(enumerated["candidate_rows"], renamed["candidate_rows"], strict=True):
        assert old["status"] == new["status"]
        assert old["graph_signature"] == new["graph_signature"]
        assert old["action_sha256"] != new["action_sha256"]


@pytest.mark.parametrize("key,value", [("binding", True), ("binding", 3), ("child", "p2"),
                                       ("input", "v4"), ("input", "secret"), ("return", "v5")])
def test_choice_outside_public_tuple_is_refused(key, value):
    choice = {"binding": 0, "child": "p0", "input": "v1", "return": "v4"}
    choice[key] = value
    with pytest.raises(ValueError, match="SCAFFOLD_"):
        scaffold.compile_choice(choice)


@pytest.mark.parametrize("kwargs", [
    {"parent_names": ("v0", "v0", "v1", "v2", "v3")},
    {"parent_names": ("v0", "v1", "v2", "v3", "v32")},
    {"child_names": ("p0", "p0")}, {"child_names": ("main", "p1")},
])
def test_unsupported_or_duplicate_output_names_are_refused(kwargs):
    with pytest.raises(ValueError, match="SCAFFOLD_"):
        scaffold.development_scaffold(**kwargs)


def test_invalid_observations_are_rejected_not_used_to_prune_choices():
    observations = scaffold.development_scaffold()["public"]["observations"]
    observations[1]["values"] = observations[0]["values"][:]
    with pytest.raises(ValueError, match="AMBIGUOUS_OBSERVATION_PAYLOADS"):
        scaffold.enumerate_candidates(observations=observations)


def test_original_inputs_are_unchanged_and_no_execution_entrypoint_is_called(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("native/model/verification execution forbidden in preparation")
    monkeypatch.setattr(native, "execute_task", forbidden)
    monkeypatch.setattr(native, "reference_task", forbidden)
    monkeypatch.setattr(native, "verify_task", forbidden)
    monkeypatch.setattr(native, "NativeBackend", forbidden)
    observations = scaffold.development_scaffold()["public"]["observations"]
    before = deepcopy(observations)
    value = scaffold.enumerate_candidates(observations=observations)
    assert observations == before
    assert value["no_guard_change"] and value["no_new_semantics"]


def test_no_numerical_or_native_success_claim_and_training_gate_stays_open(enumerated):
    assert enumerated["training_allowed_by_this_preparation"] is False
    assert enumerated["scored_task_correctness"] is None
    assert enumerated["native_construction_gate"].startswith("UNEXECUTED")
    for row in enumerated["candidate_rows"]:
        assert row["native_execution"] == "UNEXECUTED"
        for field in ("actual_input_tensor_sha256", "actual_output_tensor_sha256", "actual_semantic_content",
                      "actual_compute_plan_units", "native_verifier_result"):
            assert row[field] is None


def test_cli_parser_requires_output_and_help_does_not_enumerate(monkeypatch, capsys):
    monkeypatch.setattr(scaffold, "run_preparation", lambda *a, **k: pytest.fail("must not run"))
    with pytest.raises(SystemExit) as error:
        scaffold.main([])
    assert error.value.code == 2
    with pytest.raises(SystemExit) as error:
        scaffold.main(["--help"])
    assert error.value.code == 0 and "--output" in capsys.readouterr().out


def test_new_output_refuses_existing_root_outside_and_parent_escape(tmp_path, monkeypatch):
    root = tmp_path / "preparation"
    root.mkdir()
    monkeypatch.setattr(scaffold, "PREPARATION_ROOT", root)
    (root / "existing").mkdir()
    for path in (root, root / "existing", tmp_path / "outside", root / "x/../escaped"):
        with pytest.raises(ValueError, match="NEW_IN_SCOPE_OUTPUT"):
            scaffold._new_output(path)
    assert scaffold._new_output(root / "run_001") == root / "run_001"


def test_output_path_rejects_link_and_junction_flags(tmp_path, monkeypatch):
    root = tmp_path / "preparation"
    monkeypatch.setattr(scaffold, "PREPARATION_ROOT", root)
    path_type = type(root)
    for method in ("is_symlink", "is_junction"):
        with monkeypatch.context() as patch:
            patch.setattr(path_type, method, lambda self: True, raising=False)
            with pytest.raises(ValueError, match="NEW_IN_SCOPE_OUTPUT"):
                scaffold._new_output(root / "run_001")


def test_explicit_writer_saves_full_enumeration_and_byte_bound_receipt(tmp_path, monkeypatch, enumerated):
    root = tmp_path / "preparation"
    monkeypatch.setattr(scaffold, "PREPARATION_ROOT", root)
    # This tests custody without rerunning or representing another enumeration.
    monkeypatch.setattr(scaffold, "enumerate_candidates", lambda: deepcopy(enumerated))
    output = root / "run_001"
    receipt = scaffold.run_preparation(output)
    saved = (output / "enumeration.json").read_bytes()
    assert json.loads(saved) == enumerated
    assert receipt == json.loads((output / "receipt.json").read_bytes())
    assert receipt["files"]["enumeration.json"] == {"bytes": len(saved), "sha256": sha256(saved).hexdigest()}
    assert receipt["source_sha256_before"] == receipt["source_sha256_after"] == scaffold.SOURCE_PINS
    assert receipt["self_sha256_before"] == receipt["self_sha256_after"]
    assert receipt["candidate_count"] == 180 and receipt["controlled_input_pairs"] == 6
    assert receipt["neural_execution"] is False and receipt["native_execution"] == "UNEXECUTED"
    assert {p.name for p in output.iterdir()} == {"enumeration.json", "receipt.json"}
    with pytest.raises(ValueError, match="NEW_IN_SCOPE_OUTPUT"):
        scaffold.run_preparation(output)
