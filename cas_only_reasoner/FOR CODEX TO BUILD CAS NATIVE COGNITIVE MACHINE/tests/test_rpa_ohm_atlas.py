"""Real local compiler/PCBA to saved atlas; no runtime or model execution."""
from copy import deepcopy
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from cncm.canonical import canonical_json, digest
from cncm.model import ContractError
from cncm import rpa_coordinates as coords
from cncm import rpa_ohm_atlas as api
from cncm.rpa_model import AtlasSnapshot, LinkType, NodeStatus


@pytest.fixture(scope="module")
def document():
    return api.build_demo()


def modify_input(mutator):
    declaration = api.demo_declaration()
    mutator(declaration)
    return declaration


def reseal(document):
    document["document_sha256"] = digest({key: value for key, value in document.items() if key != "document_sha256"})
    return document


def test_real_compiler_and_pcba_exact_results_and_provenance(document):
    atlas = api.validate_ohm_atlas(document)
    assert type(atlas) is AtlasSnapshot
    assert len(atlas.nodes) == 10
    assert atlas.current_state_id == atlas.focus_node_id == "project"
    assert atlas.node_map()["project"].status is NodeStatus.OBSERVED
    assert dict(atlas.node_map()["project"].fields)["present_designation"] == "HOST_DECLARED_FIXTURE"
    receipts = {row["case_id"]: row for row in document["receipts"]}
    for case_id, literal, result in (("case-r4", "4", "3"), ("case-r6", "6", "2")):
        row = receipts[case_id]
        assert row["pcba"]["resistance_literal"] == literal
        assert row["pcba"]["pcba_check"]["structural_status"] == "PASS"
        assert row["pcba"]["quantity_report"]["value"] == result
        assert row["compiler"]["target"]["quantity_report"] == row["pcba"]["quantity_report"]
        assert row["projection"]["nodes"][0]["quantity_report"] == row["pcba"]["quantity_report"]
        assert row["compiler"]["target"]["status"] == "REFERENCE_CALCULATED_NOT_LEARNED"
        assert row["pcba"]["quantity_report"]["measurement_status"] == "NO_MEASUREMENT_PERFORMED"
        assert set(row["compiler"]["observation"]["implementation_sha256_lf"]) == {"compiler.py", "cas_ohm.py"}
    assert document["boundary"]["runtime_status"] == "NOT_CONNECTED"
    assert document["boundary"]["present_status"] == "HOST_DECLARED_FIXTURE_NOT_MEASURED"


def test_demo_is_deterministic_and_round_trips_wire(document):
    assert api.build_demo() == document
    assert api.load_ohm_atlas(canonical_json(document)) == document
    assert api.load_ohm_atlas(canonical_json(document).encode()) == document
    assert api.validate_ohm_atlas(document).to_dict() == document["atlas"]


def test_full_sources_and_expressions_are_preserved(document):
    payload = api.view_payload(document)
    for row in document["declaration"]["items"]:
        assert payload["nodes"][row["node_id"]]["full_cas_description"] == row["cas_description"]
    for receipt in document["receipts"]:
        expression = receipt["compiler"]["observation"]["expression"]
        assert payload["nodes"][receipt["node_ids"][-1]]["full_cas_description"] == expression
        assert len(payload["nodes"][receipt["node_ids"][0]]["case_receipts"]) == 1
    assert payload["nodes"]["project"]["case_receipts"] == []


def test_supplied_observation_unicode_reference_remains_unverified():
    declaration = api.demo_declaration()
    case = declaration["cases"][0]
    case["drive"]["reference"] = 'caller "quoted" reference \\ path ' + chr(0x4E2D)
    case["drive"]["origin"] = "supplied_observation"
    declaration["items"][4]["cas_description"] = api._ohm_expression(case["drive"], case["resistance"], "4")
    document = api.build_ohm_atlas(declaration)
    report = document["receipts"][0]["pcba"]["quantity_report"]
    assert report["inputs"][0]["reference"] == case["drive"]["reference"]
    assert report["inputs"][0]["origin"] == "supplied_observation"
    assert report["measurement_status"] == "NO_MEASUREMENT_PERFORMED"
    assert "UNVERIFIED" in report["inputs"][0]["observation_status"]
    assert report["observation_status"] == "NOT_AN_OBSERVATION"


def test_saved_versions_share_identity_but_not_node_addresses(document):
    atlas = api.validate_ohm_atlas(document)
    a, b = atlas.node_map()["resistor-r4"], atlas.node_map()["resistor-r6"]
    assert a.idea_id == b.idea_id == "demo-resistor"
    assert a.node_id != b.node_id
    assert dict(a.fields)["version_id"] != dict(b.fields)["version_id"]
    assert b.status is NodeStatus.HYPOTHETICAL
    assert any(edge.relation is LinkType.REFERENCES_SAME_IDEA and edge.source_id == a.node_id and edge.target_id == b.node_id
               for edge in atlas.links)
    aa, ab = api.exact_address(document, a.node_id), api.exact_address(document, b.node_id)
    assert aa != ab
    assert api.resolve_address(document, aa) == a
    assert api.resolve_address(document, api.address_text(ab)) == b
    assert api.parse_address(api.address_text(aa)) == aa


def test_equal_profiles_never_merge_identity(document):
    atlas = api.validate_ohm_atlas(document)
    a, b = atlas.node_map()["board-r4"], atlas.node_map()["calculation-r4"]
    assert a.profile40 == b.profile40
    assert a.idea_id != b.idea_id and a.node_id != b.node_id
    assert api.exact_address(document, a.node_id) != api.exact_address(document, b.node_id)


def test_navigation_and_reference_preserve_present_source_and_saved_addresses(document):
    original = canonical_json(document)
    address = api.exact_address(document, "calculation-r6")
    cursor = api.start_navigation(document)
    cursor = api.enter_node(document, cursor, "board-r6")
    cursor = api.enter_node(document, cursor, "stage-r6")
    cursor = api.enter_node(document, cursor, "resistor-r6")
    cursor = api.inspect_node(document, cursor, "calculation-r6")
    cursor = api.select_reference(document, cursor, "board-r6")
    view = api.navigation_view(document, cursor)
    assert view["breadcrumb"] == ["project", "board-r6", "stage-r6", "resistor-r6"]
    assert view["current_state_id"] == "project"
    assert view["focus_node_id"] == "calculation-r6"
    assert view["inspection"]["address"] == address
    assert view["inspection"]["coordinate_report"]["values"] == [0.0] * 39
    assert view["inspection"]["coordinate_report"]["round_trip"]["status"] == "WITHIN_DECLARED_TOLERANCE"
    cursor = api.return_to(document, cursor, 0)
    assert cursor["path"] == ["project"]
    assert cursor["reference_node_id"] == "board-r6"
    assert canonical_json(document) == original


def test_initial_coordinate_profiles_explicit_and_nonuniform_alternative(document):
    payload = api.view_payload(document)
    assert payload["nodes"]["project"]["coordinate_report"]["values"] == [0.0] * 39
    row = payload["nodes"]["calculation-r6"]
    assert row["profile"]["origin"] == "declared"
    assert row["coordinate_report"]["values"][0] == pytest.approx(math.log(4))
    assert row["coordinate_report"]["round_trip"]["status"] == "WITHIN_DECLARED_TOLERANCE"
    assert row["coordinate_report"]["labels"] == list(coords.COORDINATE_LABELS)
    assert row["coordinate_report"]["denominator_label"] == "^9/O"
    assert payload["nodes"]["note-unprofiled"]["coordinate_report"]["status"] == "NOT_ASSIGNED"


def test_absent_present_profile_stays_absent_until_explicit_reference():
    declaration = api.demo_declaration()
    declaration["items"][0]["profile"] = None
    document = api.build_ohm_atlas(declaration)
    payload = api.view_payload(document)
    assert payload["nodes"]["project"]["coordinate_report"]["values"] is None
    assert payload["nodes"]["board-r6"]["coordinate_report"]["status"] == "REFERENCE_NOT_ASSIGNED"
    cursor = api.inspect_node(document, api.start_navigation(document), "board-r6")
    cursor = api.select_reference(document, cursor, "board-r4")
    assert api.navigation_view(document, cursor)["inspection"]["coordinate_report"]["status"] == "CALCULATED_FROM_DECLARED_PROFILES"
    assert document["profiles"]["project"] is None


def test_incompatible_basis_is_explicit_without_guessing_mapping():
    declaration = api.demo_declaration()
    declaration["items"][1]["profile"]["basis"] = "different-declared-dimensions"
    document = api.build_ohm_atlas(declaration)
    report = api.view_payload(document)["nodes"]["board-r4"]["coordinate_report"]
    assert report["status"] == "INCOMPATIBLE_DECLARED_BASIS"
    assert report["values"] is None


def test_explicit_alternate_order_is_converted_and_retained():
    declaration = api.demo_declaration()
    original = deepcopy(declaration["items"][5]["profile"])
    profile = declaration["items"][5]["profile"]
    profile["values"] = list(coords.reorder_profile(tuple(profile["values"]),
        source_order=coords.CANONICAL_ORDER, target_order=coords.DOMAIN_MAJOR_ORDER))
    profile["order"] = coords.DOMAIN_MAJOR_ORDER
    document = api.build_ohm_atlas(declaration)
    assert document["profiles"]["board-r6"]["values"] == original["values"]
    assert document["profiles"]["board-r6"]["source_order"] == coords.DOMAIN_MAJOR_ORDER
    assert document["declaration"]["items"][5]["profile"]["order"] == coords.DOMAIN_MAJOR_ORDER


@pytest.mark.parametrize("path,value", [
    (("schema_version",), "cas.rpa.ohm-atlas/99"),
    (("boundary", "runtime_status"), "CONNECTED"),
    (("boundary", "measurement_status"), "MEASURED"),
    (("profiles", "project", "reference"), "fabricated-reference"),
    (("receipts", 0, "board_source_sha256"), "0" * 64),
    (("receipts", 0, "expression_sha256"), "0" * 64),
    (("receipts", 0, "receipt_sha256"), "0" * 64),
    (("receipts", 0, "pcba", "quantity_report", "value"), "1000"),
    (("receipts", 0, "pcba", "quantity_report", "observation_status"), "VERIFIED"),
    (("receipts", 0, "compiler", "target", "quantity_report", "value"), "1000"),
    (("receipts", 0, "compiler", "observation", "expression"), "ohm_flow(12, 4)"),
    (("receipts", 0, "compiler", "observation", "implementation_sha256_lf", "compiler.py"), "0" * 64),
    (("receipts", 0, "projection", "authority"), "EXECUTE"),
    (("atlas", "current_state_id"), "board-r6"),
    (("atlas", "focus_node_id"), "board-r6"),
    (("atlas", "nodes", 0, "label"), "forged-label"),
])
def test_resealed_record_tampering_is_rejected(document, path, value):
    bad = deepcopy(document)
    target = bad
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    reseal(bad)
    with pytest.raises(ValueError):
        api.validate_ohm_atlas(bad)


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(schema_version="unknown"),
    lambda d: d["present"].update(designation="MEASURED"),
    lambda d: d["present"].update(node_id="board-r6"),
    lambda d: d["items"].append(deepcopy(d["items"][0])),
    lambda d: d["items"][1].update(item_id="ohm-project", version_id="v1"),
    lambda d: d["items"][1].update(status="verified"),
    lambda d: d["items"][1].update(role="sensor"),
    lambda d: d["items"][5].update(item_id="demo-stage"),
    lambda d: d["items"][1].update(cas_description="not the board"),
    lambda d: d["items"][3].update(cas_description="Resistor<a,R=999>"),
    lambda d: d["items"][4].update(cas_description="ohm_flow(12,999)"),
    lambda d: d["cases"][0].update(resistor_name="missing"),
    lambda d: d["cases"][0]["drive"].update(value=12),
    lambda d: d["cases"][0]["resistance"].update(value="999"),
    lambda d: d["cases"][0]["resistance"]["scale"].update(id="wrong-scale"),
    lambda d: d["cases"][0]["drive"].update(origin="measured"),
    lambda d: d["cases"][1].update(case_id="case-r4"),
    lambda d: d["cases"][1].update(calculation_node_id="calculation-r4"),
    lambda d: d["items"][3].update(version_id="v3"),
    lambda d: d["items"][3].update(status="hypothetical"),
    lambda d: d["links"].pop(1),
    lambda d: d["links"].append(deepcopy(d["links"][0])),
    lambda d: d["links"][0].update(relation="same_coordinates"),
    lambda d: d["links"][-1].update(source_id="calculation-r4", target_id="project"),
    lambda d: d["items"][0]["profile"].update(origin="measured"),
    lambda d: d["items"][0]["profile"].update(order="assume_it"),
    lambda d: d["items"][0]["profile"].update(basis=""),
    lambda d: d["items"][0]["profile"]["values"].__setitem__(0, "0"),
    lambda d: d["items"][0]["profile"]["values"].__setitem__(0, "1/20"),
    lambda d: d["items"][0]["profile"].update(values=["1/40"] * 39),
    lambda d: d["items"][0]["profile"].update(values=[0.025] * 40),
])
def test_invalid_declarations_fail_closed(mutation):
    with pytest.raises(ValueError):
        api.build_ohm_atlas(modify_input(mutation))


@pytest.mark.parametrize("source", [
    b"{}", b"[]", b"null", b"\xff", '{"x":1,"x":2}', '{"x":NaN}',
    '{"x":Infinity}', "[" * 2000 + "]" * 2000, " " * (api.MAX_DOCUMENT_BYTES + 1),
], ids=["object", "list", "null", "utf8", "duplicate-key", "nan", "infinity", "depth", "size"])
def test_wire_decoder_rejects_invalid_unsupported_and_unbounded(source):
    with pytest.raises(ContractError):
        api.load_ohm_atlas(source)


def test_structural_budget_and_cycles_rejected_before_build():
    circular = []
    circular.append(circular)
    with pytest.raises(ContractError):
        api.build_ohm_atlas(circular)
    with pytest.raises(ContractError):
        api.build_ohm_atlas({"x" * (api.MAX_DOCUMENT_BYTES + 1): 1})
    with pytest.raises(ContractError):
        api.build_ohm_atlas({"arbitrary": object()})
    with pytest.raises(ContractError):
        api.build_ohm_atlas({"integer": 1 << 4097})


def test_integer_tokens_are_bounded_before_conversion_when_host_guard_disabled(monkeypatch):
    original = sys.get_int_max_str_digits()
    def forbidden_conversion(value):
        pytest.fail("oversized integer reached decimal conversion")
    monkeypatch.setattr(api, "Decimal", forbidden_conversion)
    try:
        sys.set_int_max_str_digits(0)
        with pytest.raises(ContractError, match="integer token exceeds"):
            api.load_ohm_atlas('{"number":' + "9" * 100000 + "}")
    finally:
        sys.set_int_max_str_digits(original)


@pytest.mark.parametrize("key,value", [
    ("document_sha256", "0" * 64), ("context_sha256", "0" * 64),
    ("version_id", "v999"), ("item_id", "wrong"), ("schema_version", "old")
])
def test_wrong_address_bindings_rejected(document, key, value):
    address = api.exact_address(document, "calculation-r4")
    address[key] = value
    with pytest.raises(ContractError):
        api.resolve_address(document, address)


def test_stale_snapshot_address_and_cursor_rejected(document):
    address = api.exact_address(document, "calculation-r4")
    cursor = api.start_navigation(document)
    declaration = deepcopy(document["declaration"])
    declaration["context"]["record_version"] += 1
    new = api.build_ohm_atlas(declaration)
    with pytest.raises(ContractError):
        api.resolve_address(new, address)
    with pytest.raises(ContractError):
        api.navigation_view(new, cursor)


@pytest.mark.parametrize("operation", [
    lambda d, c: api.enter_node(d, c, "stage-r4"),
    lambda d, c: api.enter_node(d, c, "note-unprofiled"),
    lambda d, c: api.inspect_node(d, c, "absent"),
    lambda d, c: api.select_reference(d, c, "absent"),
    lambda d, c: api.return_to(d, c, -1),
    lambda d, c: api.return_to(d, c, True),
    lambda d, c: api.navigation_view(d, {**c, "path": ["project", "board-r4", "board-r6"]}),
    lambda d, c: api.navigation_view(d, {**c, "path": ["project", "project"]}),
    lambda d, c: api.navigation_view(d, {**c, "path": ["project", "note-unprofiled"]}),
    lambda d, c: api.navigation_view(d, {**c, "path": ["board-r4"]}),
])
def test_invalid_navigation_cannot_change_saved_document(document, operation):
    original = canonical_json(document)
    with pytest.raises(ContractError):
        operation(document, api.start_navigation(document))
    assert canonical_json(document) == original


@pytest.mark.parametrize("suffix", ["#fragment", "&item=duplicate", "&extra=x"])
def test_noncanonical_address_text_refused(document, suffix):
    value = api.address_text(api.exact_address(document, "calculation-r4"))
    with pytest.raises(ContractError):
        api.parse_address(value + suffix)


def test_maximum_identifiers_have_round_trippable_exact_addresses():
    address = {"schema_version": api.ADDRESS_SCHEMA, "document_sha256": "a" * 64,
               "context_sha256": "b" * 64, "node_id": "n" + ":" * 127,
               "item_id": "i" + ":" * 127, "version_id": "v" + ":" * 127}
    assert api.parse_address(api.address_text(address)) == address


def test_cross_checkout_lab_module_is_refused(monkeypatch):
    monkeypatch.setitem(sys.modules, "pcba_check", SimpleNamespace(__file__=str(Path(__file__).parent / "pcba_check.py")))
    with pytest.raises(ContractError, match="another checkout"):
        api.build_demo()


def test_view_payload_is_detached_and_contains_all_bound_nodes(document):
    before = canonical_json(document)
    payload = api.view_payload(document)
    assert set(payload["nodes"]) == {row["node_id"] for row in document["atlas"]["nodes"]}
    payload["nodes"]["project"]["profile"]["values"][0] = "1"
    payload["nodes"]["board-r4"]["case_receipts"][0]["pcba"]["quantity_report"]["value"] = "999"
    assert canonical_json(document) == before


def test_payload_validation_runs_once(monkeypatch, document):
    original, calls = api.validate_ohm_atlas, []
    def validate(value):
        calls.append(value)
        return original(value)
    monkeypatch.setattr(api, "validate_ohm_atlas", validate)
    api.view_payload(document)
    assert len(calls) == 1
