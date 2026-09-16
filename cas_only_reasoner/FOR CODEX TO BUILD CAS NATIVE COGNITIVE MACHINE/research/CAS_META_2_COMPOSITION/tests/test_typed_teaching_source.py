"""Pure public source admission; no teacher, final constructor or neural runtime."""
from collections import Counter
from copy import deepcopy
import builtins
import sys

import pytest

from cas_meta2.typed_teaching import source

DENIED = {"torch", "numpy", "tensorflow", "jax", "cas_cjt", "casformer", "boto3", "botocore",
          "requests", "httpx", "openai", "anthropic", "transformers"}


@pytest.fixture(autouse=True)
def denied_execution(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in DENIED or name.startswith("cas_meta2.graph_teaching"):
            raise AssertionError("PROHIBITED_IMPORT:" + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    yield
    assert not DENIED.intersection(name.split(".")[0] for name in sys.modules)


@pytest.fixture(scope="module")
def families():
    return source.training_families(expected_source_profile_digest=source.source_profile()["profile_digest"])


@pytest.fixture(scope="module")
def bank(families):
    return source.freeze_bank(families)


@pytest.fixture(scope="module")
def envelope(families, bank):
    return source.compile_source(families[0], bank=bank)


def test_training_literal_constructor_never_imports_all_split_modules(families):
    assert len(families) == 64
    assert all(f["split"] == "training" for f in families)
    assert families[0]["family_id"] == "family:mechanical:00"
    assert families[-1]["family_id"] == "family:container:15"
    assert Counter(f["domain"] for f in families) == {
        "mechanical": 16, "grammatical": 16, "procedural": 16, "container": 16}
    assert "cas_meta2.graph_teaching.face_corpus" not in sys.modules
    assert "cas_meta2.graph_teaching.face_tasks" not in sys.modules
    assert families[0]["labels"] == ("Bicycle", "Wheel", "Rim")
    assert families[0]["branches"] == ({"source": "Bicycle", "target": "Wheel"}, {"source": "Wheel", "target": "Rim"})


def test_changed_code_pin_refuses_training_construction():
    with pytest.raises(ValueError, match="PROFILE_CHANGED"):
        source.training_families(expected_source_profile_digest="0" * 64)


def test_full_bank_and_all_focuses_preserve_same_public_source_membership(families, bank):
    assert len(bank["worlds"]) == len(bank["bank"]["world_ids"]) == 64
    assert source.freeze_bank(tuple(reversed(families))) == bank
    for family in families:
        packet = source.public_source(source.compile_source(family, bank=bank))
        assert packet["bank"] == bank["bank"]
        assert packet["worlds"] == bank["worlds"]
        assert packet["focus_world_id"] in bank["bank"]["world_ids"]


def test_public_validation_needs_no_private_compilation_or_source_files(envelope, monkeypatch):
    public = deepcopy(envelope["public"])
    def forbidden(*args, **kwargs):
        raise AssertionError("PRIVATE_OR_SOURCE_ACCESS")
    for name in ("compile_source", "training_families", "source_profile", "_material"):
        monkeypatch.setattr(source, name, forbidden)
    assert source.validate_public(public) == public
    assert source.public_digest(public) == source.digest(public)
    assert source.public_source(envelope) == public


def test_all_six_face_material_is_published_equally_and_honestly(families, bank):
    by_id = {world["world_id"]: world for world in bank["worlds"]}
    procedural_order_differences = 0
    for family in families:
        compiled = source.compile_source(family, bank=bank)
        world = by_id[compiled["public"]["focus_world_id"]]
        labels = {node["ref"]: node["label"] for node in world["nodes"]}
        declarations = world["declarations"]
        for field in ("domain", "kind", "function", "setting"):
            assert declarations[field] == family[field]
        assert [labels[ref] for ref in declarations["primary_labels"]] == list(family["labels"][:3])
        assert declarations["participants"] == declarations["primary_labels"]
        assert declarations["participants_basis"] == source.PARTICIPANTS_BASIS
        assert world["source_status"]["field_origins"]["participants"].startswith("PRESENTATION_DERIVED")
        assert world["source_status"]["authorship_authenticated"] is False
        assert world["source_status"]["world_truth_established"] is False
        edges = [(labels[e["source"]], labels[e["target"]]) for e in world["contains"]]
        assert edges == [(e["source"], e["target"]) for e in family["branches"]]
        assert world["contains_inventory_complete"] is True
        assert world["branch_order"]["process_order"] is None
        assert world["branch_order"]["order_basis"] == source.ORDER_BASIS
        if family["domain"] == "procedural" and edges != sorted(edges):
            procedural_order_differences += 1
    assert procedural_order_differences == 13


def test_no_teacher_fields_partner_mapping_or_traversal_answers(envelope):
    banned = {"correct", "expected_answer", "teacher_target", "options", "encoded_options", "encoded_correct_index",
              "partner", "analogy_partner", "pairs", "answer_refs", "direct_parts", "reach_kind", "preserved_branches"}
    def walk(value):
        if isinstance(value, dict):
            assert not banned.intersection(value)
            for child in value.values(): walk(child)
        elif isinstance(value, list):
            for child in value: walk(child)
    walk(envelope)


def test_identical_labels_in_different_worlds_keep_distinct_scoped_refs(families):
    first, second = deepcopy(families[0]), deepcopy(families[0])
    second["domain"] = "another declared domain"
    frozen = source.freeze_bank([first, second])
    a, b = frozen["worlds"]
    assert [n["label"] for n in a["nodes"]] == [n["label"] for n in b["nodes"]]
    assert not {n["ref"] for n in a["nodes"]}.intersection(n["ref"] for n in b["nodes"])


def test_metadata_not_in_public_identity(families, bank):
    changed = deepcopy(families[0])
    changed.update(family_id="caller-renamed", archetype="caller-shape-name", rendering=3)
    original = source.compile_source(families[0], bank=bank)
    renamed = source.compile_source(changed, bank=bank)
    assert source.public_source(original) == source.public_source(renamed)
    assert original["source_digest"] != renamed["source_digest"]


def test_caller_assertion_is_accepted_without_authenticity_or_training_corpus_claim(families, bank):
    declared = deepcopy(families[0]); declared["kind"] = "a caller asserted kind"
    result = source.compile_source(declared, bank=bank)
    public = source.public_source(result)
    assert len(public["worlds"]) == 65
    assert public["focus_world_id"] not in public["bank"]["world_ids"]
    assert result["provenance"]["authority"] == "CALLER_SUPPLIED_DECLARATIONS_SYNTAX_CHECKED_ONLY"


@pytest.mark.parametrize("field", ["correct", "teacher_target", "expected_answer", "options", "partner"])
def test_private_or_unsupported_family_fields_refused(families, bank, field):
    changed = deepcopy(families[0]); changed[field] = "no"
    with pytest.raises(ValueError, match="FAMILY_FIELDS"):
        source.compile_source(changed, bank=bank)


@pytest.mark.parametrize("changed", ["split", "rendering_bool", "duplicate_label", "foreign_edge", "cycle", "duplicate_edge", "eleven_nodes"])
def test_malformed_authored_sources_refused(families, changed):
    row = deepcopy(families[0])
    if changed == "split": row["split"] = "final_held_out"
    elif changed == "rendering_bool": row["rendering"] = True
    elif changed == "duplicate_label": row["labels"] = ("Bicycle", "Wheel", "Wheel")
    elif changed == "foreign_edge": row["branches"] = ({"source": "Bicycle", "target": "Foreign"},)
    elif changed == "cycle": row["branches"] += ({"source": "Rim", "target": "Bicycle"},)
    elif changed == "duplicate_edge": row["branches"] += (row["branches"][0],)
    else: row["labels"] = tuple("N%d" % i for i in range(11))
    with pytest.raises(ValueError): source.freeze_bank([row])


@pytest.mark.parametrize("changed", ["world_id", "node_ref", "edge_ref", "foreign_endpoint", "kind", "participants", "complete_bool_alias", "process_order", "authority", "extra", "bank_drop", "world_drop"])
def test_forged_public_structure_and_claims_refused(envelope, changed):
    public = deepcopy(envelope["public"])
    world = public["worlds"][0]
    if changed == "world_id": world["world_id"] += "0"
    elif changed == "node_ref": world["nodes"][0]["ref"] += "0"
    elif changed == "edge_ref": world["contains"][0]["ref"] += "0"
    elif changed == "foreign_endpoint": world["contains"][0]["source"] = public["worlds"][1]["nodes"][0]["ref"]
    elif changed == "kind": world["declarations"]["kind"] = "changed"
    elif changed == "participants": world["declarations"]["participants"] = []
    elif changed == "complete_bool_alias": world["contains_inventory_complete"] = 1
    elif changed == "process_order": world["branch_order"]["process_order"] = world["branch_order"]["source_order"]
    elif changed == "authority": world["source_status"]["world_truth_established"] = True
    elif changed == "extra": public["correct"] = "no"
    elif changed == "bank_drop": public["bank"]["world_ids"].pop()
    else: public["worlds"].pop()
    with pytest.raises((ValueError, KeyError)): source.validate_public(public)


def test_mutation_isolation_and_bank_bounds(families, bank, envelope):
    packet = source.public_source(envelope)
    packet["worlds"][0]["declarations"]["kind"] = "mutated"
    assert source.public_source(envelope) != packet
    with pytest.raises(ValueError, match="BANK_BOUND"): source.freeze_bank(list(families) + [families[0]])
    with pytest.raises(ValueError, match="DUPLICATE_WORLD"): source.freeze_bank([families[0], families[0]])
    changed = deepcopy(bank); changed["worlds"].reverse()
    with pytest.raises(ValueError, match="WORLD_ORDER"): source.validate_bank(changed)


def test_source_envelope_and_provenance_are_closed(envelope):
    changed = deepcopy(envelope); changed["correct"] = "no"
    with pytest.raises(ValueError, match="ENVELOPE_FIELDS"): source.public_source(changed)
    changed = deepcopy(envelope); changed["provenance"]["source_profile"]["teacher_target"] = "no"
    changed["source_digest"] = source.digest({k: v for k, v in changed.items() if k != "source_digest"})
    with pytest.raises(ValueError, match="PROFILE_FIELDS"): source.public_source(changed)


def test_cycle_and_excessive_depth_refused_without_recursion_error():
    cycle = {}; cycle["self"] = cycle
    with pytest.raises(ValueError, match="CYCLE"): source.validate_public(cycle)
    deep = {}
    for _ in range(22): deep = {"inner": deep}
    with pytest.raises(ValueError, match="TREE_BOUND"): source.validate_public(deep)


def test_non_json_tuple_alias_rejected_in_public_wire(envelope):
    public = deepcopy(envelope["public"])
    world = public["worlds"][0]
    world["branch_order"]["source_order"] = tuple(world["branch_order"]["source_order"])
    with pytest.raises(ValueError, match="JSON_TYPE"): source.validate_public(public)
