"""Frozen genuine DEVELOPMENT records, with no learner or model execution."""
from copy import deepcopy
from hashlib import sha256
import builtins
import json
from pathlib import Path
import shutil
import sys

import pytest

from cncm.canonical import canonical_json, digest
from cncm.model import ContractError
from cncm.rpa_model import AtlasSnapshot
from cncm import rpa_recorded_helm as api


@pytest.fixture(scope="module")
def document():
    return api.build_demo()


def reseal(value):
    value["document_sha256"] = digest({k: v for k, v in value.items() if k != "document_sha256"})
    return value


def test_genuine_original_correct_and_wrong_development_records(document):
    assert document["schema_version"] == api.SCHEMA
    assert document["identity"]["worker"]["job"] == "cas-meta2-tpntr-20260920210258-20208c92-m-20260917"
    assert document["identity"]["worker"]["source_sha"] == "20208c923d41c24614504d4ecc2b289ecb66eda8"
    assert document["source_selection"]["model_label"] == "Helm 2.0-experimental"
    assert document["identity"]["development_disclosure"]["policy"]["split"] == "development"
    assert document["identity"]["development_disclosure"]["final_questions_constructed"] == 0
    assert document["identity"]["development_disclosure"]["main_targets_constructed"] == 0
    assert document["source_selection"]["exposure"]["posthoc_example_selection"] is True
    correct, wrong = document["examples"]
    assert correct["saved_check"]["correct"] is True
    assert correct["prediction_display"] == "VIA via Dev1Node2"
    assert wrong["saved_check"]["correct"] is False
    assert wrong["prediction_display"] == "(no nodes)"
    assert wrong["checker_replay"]["answer_displays"] == ["Dev1Node2"]
    assert wrong["prediction"]["answer"]["value"] == {"nodes": []}


def test_frozen_files_match_external_anchor_and_original_manifest():
    selection, records, identity = api._retained()
    assert sha256((api.SOURCE_ROOT / "source_selection.json").read_bytes()).hexdigest() == api.SELECTION_SHA256
    manifest = json.loads((api.SOURCE_ROOT / "artifact_manifest.json").read_text())
    by_name = {r["name"]: r for r in manifest["artifacts"]}
    for name, pin in selection["original_files"].items():
        assert by_name[name]["sha256"] == pin["sha256"]
        assert by_name[name]["bytes"] == pin["bytes"]
    assert identity["saved_development_scores"]["public_seal"]["sha256"] == by_name["development_p10_predictions.json"]["sha256"]
    for row in records:
        assert digest(row["packet"]) == row["prediction"]["packet_digest"]
        assert row["prediction"]["prediction_id"] == row["saved_check"]["prediction_id"]


def test_final_checkpoint_original_model_and_run_bindings(document):
    identity = document["identity"]
    final = identity["final_checkpoint"]
    assert final["sha256"] == "c6c49e982c408ced7cae47935f34708e14794d2fcc9789b1bce7900db5bd4ffb"
    assert final["bytes"] == 3670007
    assert final["metadata"]["model_state_identity"] == "c6d0f95d68740834199684cd706ad385ccb040dd91eb13781e60d14ba3cd1ed6"
    for row in document["examples"]:
        assert row["prediction"]["model_revision"] == final["metadata"]["model_revision"] == 1470
        assert row["prediction"]["run_context_digest"] == final["run_identity_digest"]
    assert identity["checkpoint_availability"]["selected_export_includes_weights"] is False
    assert "NOT_DECODED" in identity["checkpoint_availability"]["status"]


def test_original_checker_replay_is_separate_and_identical(document):
    selection, _, _ = api._retained()
    checker = api._checker(selection)
    for row in document["examples"]:
        replay = checker.check_answer(row["packet"]["source"], row["packet"]["record"]["query"],
                                      row["prediction"]["answer"])
        assert replay == row["checker_replay"]["record"]
        assert {**replay, "record_id": row["prediction"]["record_id"],
                "prediction_id": row["prediction"]["prediction_id"]} == row["saved_check"]
    assert selection["checker_sources"][-1]["sha256"] == "57ac0a9f78c46999fac444fc974d3c1b718435b583cbc48701be74c56efa971e"


def test_build_has_no_model_torch_or_teacher_course_import(monkeypatch):
    original = builtins.__import__
    seen = []
    def guarded(name, *args, **kwargs):
        seen.append(name)
        assert name != "torch" and not name.startswith("torch.")
        assert "pointer_learner" not in name and "pointer_contract" not in name
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    api.build_demo()
    assert not any(name.startswith("torch") for name in seen)


def test_wire_and_deterministic_rebuild(document):
    assert api.build_demo() == document
    assert api.load_recorded_atlas(canonical_json(document)) == document
    assert api.load_recorded_atlas(canonical_json(document).encode()) == document
    assert type(api.validate_recorded_atlas(document)) is AtlasSnapshot


def test_shared_model_identity_has_two_containment_paths(document):
    atlas = api.validate_recorded_atlas(document)
    incoming = {e.source_id for e in atlas.links if e.target_id == "model-checkpoint"}
    assert incoming == {"task-correct", "task-wrong"}
    assert sum(n.node_id == "model-checkpoint" for n in atlas.nodes) == 1
    assert len(atlas.nodes) == 10


def test_all_exact_addresses_roundtrip_and_are_distinct(document):
    atlas = api.validate_recorded_atlas(document)
    addresses = [api.exact_address(document, n.node_id) for n in atlas.nodes]
    assert len({canonical_json(a) for a in addresses}) == len(atlas.nodes)
    for address in addresses:
        text = api.address_text(address)
        assert api.parse_address(text) == address
        assert api.resolve_address(document, text).node_id == address["node_id"]


@pytest.mark.parametrize("path,value", [
    (("schema_version",), "unsupported"),
    (("identity", "worker", "status"), "CERTIFIED"),
    (("identity", "worker", "source_sha"), "0" * 40),
    (("identity", "final_checkpoint", "sha256"), "0" * 64),
    (("identity", "development_disclosure", "policy", "split"), "final"),
    (("source_selection_sha256",), "0" * 64),
    (("source_selection", "model_label"), "Helm 3.0"),
    (("boundary", "runtime"), "CONNECTED"),
    (("examples", 1, "saved_check", "correct"), True),
    (("examples", 1, "prediction", "answer", "value", "nodes"), ["forged"]),
    (("examples", 1, "prediction", "packet_digest"), "0" * 64),
    (("examples", 1, "prediction_display"), "Dev1Node2"),
    (("examples", 1, "question_display"), "a different task"),
    (("examples", 1, "packet", "record", "instruction"), "altered input"),
    (("examples", 1, "checker_replay", "record", "correct"), True),
    (("examples", 1, "checker_replay", "answer_displays"), ["invented"]),
    (("atlas", "current_state_id"), "task-correct"),
    (("atlas", "focus_node_id"), "task-correct"),
    (("atlas", "nodes", 0, "label"), "altered label"),
])
def test_tampered_record_is_rejected_even_with_recomputed_outer_hash(document, path, value):
    bad = deepcopy(document)
    dest = bad
    for key in path[:-1]:
        dest = dest[key]
    dest[path[-1]] = value
    with pytest.raises(ContractError):
        api.validate_recorded_atlas(reseal(bad))


def test_mutating_selected_source_and_its_manifest_cannot_replace_external_anchor(monkeypatch, tmp_path):
    source = tmp_path / "retained"
    shutil.copytree(api.SOURCE_ROOT, source)
    records_path = source / "selected_records.json"
    rows = json.loads(records_path.read_text())
    rows[1]["saved_check"]["correct"] = True
    raw = (json.dumps(rows, sort_keys=True, indent=2) + "\n").encode()
    records_path.write_bytes(raw)
    selection_path = source / "source_selection.json"
    selection = json.loads(selection_path.read_text())
    selection["selected_files"]["selected_records.json"] = {"bytes": len(raw), "sha256": sha256(raw).hexdigest()}
    selection_path.write_text(json.dumps(selection, sort_keys=True, indent=2) + "\n")
    monkeypatch.setattr(api, "SOURCE_ROOT", source)
    with pytest.raises(ContractError, match="external source selection anchor"):
        api.build_demo()


def test_changed_checker_bytes_are_refused_even_after_module_cache(monkeypatch, tmp_path, document):
    source = tmp_path / "retained"
    shutil.copytree(api.SOURCE_ROOT, source)
    path = source / "pinned_checker/checker.py"
    path.write_bytes(path.read_bytes() + b"\n# changed\n")
    monkeypatch.setattr(api, "SOURCE_ROOT", source)
    with pytest.raises(ContractError, match="source pin mismatch"):
        api.build_demo()


def test_changed_saved_prediction_refused_before_checker(monkeypatch, tmp_path):
    source = tmp_path / "retained"
    shutil.copytree(api.SOURCE_ROOT, source)
    path = source / "selected_records.json"
    path.write_bytes(path.read_bytes().replace(b'"VIA"', b'"BAD"', 1))
    monkeypatch.setattr(api, "SOURCE_ROOT", source)
    monkeypatch.setattr(api, "_checker", lambda *args: pytest.fail("tampered input reached checker"))
    with pytest.raises(ContractError, match="source pin mismatch"):
        api.build_demo()


def test_inspection_reference_and_breadcrumbs_preserve_saved_present(document):
    before = canonical_json(document)
    cursor = api.start_navigation(document)
    cursor = api.enter_node(document, cursor, "task-wrong")
    cursor = api.inspect_node(document, cursor, "prediction-wrong")
    cursor = api.select_reference(document, cursor, "task-correct")
    view = api.navigation_view(document, cursor)
    assert view["current_state_id"] == "recorded-run"
    assert view["breadcrumb"] == ["recorded-run", "task-wrong"]
    assert view["focus_node_id"] == "prediction-wrong"
    assert view["profile_status"] == "NOT_ASSIGNED" and view["ohm_status"] == "NOT_RECORDED"
    cursor = api.return_to(document, cursor, 0)
    assert cursor["path"] == ["recorded-run"] and cursor["reference_node_id"] == "task-correct"
    assert canonical_json(document) == before


@pytest.mark.parametrize("change", [
    {"path": ["recorded-run", "input-wrong"]},
    {"path": ["recorded-run", "task-wrong", "model-checkpoint"]},
    {"path": ["recorded-run", "recorded-run"]},
    {"document_sha256": "0" * 64}, {"focus_node_id": "missing"},
    {"reference_node_id": "missing"}, {"schema_version": "other"},
])
def test_invalid_or_stale_navigation_refused(document, change):
    cursor = {**api.start_navigation(document), **change}
    with pytest.raises(ContractError):
        api.navigation_view(document, cursor)


@pytest.mark.parametrize("key,value", [
    ("document_sha256", "0" * 64), ("context_sha256", "0" * 64),
    ("item_id", "different"), ("version_id", "other"), ("schema_version", "other")
])
def test_exact_address_binding_refuses_altered_versions(document, key, value):
    address = api.exact_address(document, "task-wrong")
    address[key] = value
    with pytest.raises(ContractError):
        api.resolve_address(document, address)


@pytest.mark.parametrize("wire", [
    "null", "[]", "{}", '{"x":1,"x":2}', '{"x":NaN}', '{"x":1e9999}',
    "[" * 2000 + "]" * 2000, " " * (api.MAX_BYTES + 1), b"\xff",
], ids=["null", "array", "object", "duplicates", "nan", "overflow", "depth", "size", "utf8"])
def test_wire_decoder_rejects_malformed_and_unbounded_records(wire):
    with pytest.raises(ContractError):
        api.load_recorded_atlas(wire)


def test_integer_and_float_token_conversion_is_bounded_before_parsing(monkeypatch):
    monkeypatch.setattr(api, "Decimal", lambda *args: pytest.fail("oversized integer converted"))
    with pytest.raises(ContractError, match="integer token"):
        api.load_recorded_atlas('{"x":' + "9" * 100000 + "}")
    with pytest.raises(ContractError, match="floating token"):
        api.load_recorded_atlas('{"x":0.' + "1" * 100000 + "}")


def test_in_memory_cycles_huge_keys_and_non_json_objects_refused():
    value = []
    value.append(value)
    for bad in (value, {"x" * (api.MAX_BYTES + 1): 1}, {"object": object()}, {"huge": 1 << 4097}):
        with pytest.raises(ContractError):
            api.validate_recorded_atlas(bad)


def test_complete_record_panels_keep_originals_and_absence_explicit(document):
    payload = api.view_payload(document)
    assert payload["profiles"] == payload["calculations"] == {}
    assert type(payload["presentation"]["boundary_details"]) is str
    assert all(row["cas_description"] is None for row in payload["items"])
    for example in document["examples"]:
        panels = payload["record_panels"]["task-" + example["example_id"]]
        by_title = {p["title"]: p for p in panels}
        assert by_title["Original Helm prediction"]["record"] == example["prediction"]
        assert by_title["Original saved checker result"]["record"] == example["saved_check"]
        assert by_title["Original saved model input"]["record"] == example["packet"]
        assert by_title["Original focus-world graph"]["record"] == example["focus_world"]
        assert "Dev1Node7 contains Dev1Node2" in by_title["Original focus-world graph"]["value"]
        assert by_title["Independent replay of saved checker"]["record"] == example["checker_replay"]
        availability = by_title["Saved evidence limits"]["value"]
        for expected in ("CAS profile: Not assigned", "CAS-Ohm measurement: Not available",
                         "Original prediction: Available", "Checker result: Available",
                         "Internal thought trace: Not recorded"):
            assert expected in availability


def test_payload_detached_and_contains_no_full_protocol_or_weights(document):
    before = canonical_json(document)
    payload = api.view_payload(document)
    payload["record_panels"]["task-wrong"][0]["record"]["instruction"] = "changed UI copy"
    payload["identity"]["worker"]["job"] = "changed UI copy"
    assert canonical_json(document) == before
    assert "protocol_material" not in document
    assert set(document["examples"][0]["packet"]) == {"record", "source"}
    assert document["identity"]["checkpoint_availability"]["selected_export_includes_weights"] is False
