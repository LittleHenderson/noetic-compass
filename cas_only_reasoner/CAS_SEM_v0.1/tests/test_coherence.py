"""The six coherence laws over semantic documents."""

from cassem.coherence import CoherenceChecker
from cassem.store import SemanticCMB
from conftest import broken_story, good_story


def _laws(doc):
    return [v.law for v in CoherenceChecker(doc).check()]


def test_good_story_is_coherent():
    doc = good_story()
    checker = CoherenceChecker(doc)
    assert checker.check() == []
    cmb = SemanticCMB(doc)
    assert cmb.coherent() is True


def test_unresolved_reference_violates_integrity():
    doc = broken_story(lambda s: s["references"].append(
        {"kind": "name", "id": "bird_9"}))
    assert "referential_integrity" in _laws(doc)


def test_time_contradiction_violates_temporal_consistency():
    doc = broken_story(lambda s: s["time_assertions"].append(
        {"earlier": "t2", "later": "t1"}))
    assert "temporal_consistency" in _laws(doc)


def test_verified_and_contradicted_violates_truth_discipline():
    doc = broken_story(lambda s: s["claims"].append({
        "idea": {"kind": "property", "entity": "cat_1", "property": "gray"},
        "truth": "CONTRADICTED",
        "provenance": {"source": "book"},
        "conflict": {"a": "observation t1", "b": "book page 9"}}))
    assert "truth_discipline" in _laws(doc)


def test_missing_provenance_violates_completeness():
    doc = broken_story(lambda s: s["claims"].append({
        "idea": {"kind": "property", "entity": "cat_1", "property": "quiet"},
        "truth": "UNKNOWN"}))
    assert "provenance_completeness" in _laws(doc)


def test_bad_derivation_violates_derivation_validity():
    doc = broken_story(lambda s: s["claims"].append({
        "idea": {"kind": "property", "entity": "cat_1", "property": "brown"},
        "truth": "DERIVED",
        "provenance": {"source": "prior_proof"},
        "derivation": {
            "propositions": [{"pred": "has", "args": ["cat_1", "gray"]}],
            "rules": [{"rule_id": "r_prop",
                       "premises": [{"pred": "has", "args": ["?X", "?Y"]}],
                       "conclusion": {"pred": "property", "args": ["?X", "?Y"]},
                       "source": "l1_grounding"}],
            "conclusion": {"pred": "property", "args": ["cat_1", "brown"]}}}))
    assert "derivation_validity" in _laws(doc)


def test_bad_roles_violate_relation_schema():
    doc = broken_story(lambda s: s["claims"].append({
        "idea": {"kind": "relation", "pred": "chase",
                 "roles": {"agent": "dog_1"}},
        "truth": "GIVEN",
        "provenance": {"source": "teacher"}}))
    assert "relation_schema" in _laws(doc)


def test_type_discipline_violation():
    doc = broken_story(lambda s: (
        s["entities"].append({"id": "book_1", "type": "book"}),
        s["claims"].append({
            "idea": {"kind": "property", "entity": "book_1",
                     "property": "color"},
            "truth": "GIVEN",
            "provenance": {"source": "teacher"}})))
    assert "type_discipline" in _laws(doc)


def test_checker_is_deterministic():
    a = CoherenceChecker(good_story()).check()
    b = CoherenceChecker(good_story()).check()
    assert [v.to_json() for v in a] == [v.to_json() for v in b]
