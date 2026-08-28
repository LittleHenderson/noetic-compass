"""The Semantic CMB: queries, lacunae, ablation."""

from cassem.coherence import CoherenceChecker
from cassem.store import SemanticCMB
from conftest import broken_story, good_story


def test_queries_by_entity_and_truth():
    cmb = SemanticCMB(good_story())
    cat_records = cmb.by_entity("cat_1")
    assert any(r.get("truth") == "VERIFIED" for r in cat_records)
    verified = cmb.by_truth("VERIFIED")
    assert len(verified) == 1
    assert verified[0]["idea"]["entity"] == "cat_1"


def test_no_lacunae_in_good_story():
    cmb = SemanticCMB(good_story())
    assert cmb.lacunae() == []


def test_lacuna_for_missing_entity():
    doc = broken_story(lambda s: s["references"].append(
        {"kind": "name", "id": "bird_9"}))
    cmb = SemanticCMB(doc)
    lacunae = cmb.lacunae()
    assert any(l.kind == "ENTITY_MISSING" and "bird_9" in l.detail
               for l in lacunae)


def test_ablation_breaks_coherence():
    doc = good_story()
    cmb = SemanticCMB(doc)
    cmb.registry.remove("dog_1")
    violations = CoherenceChecker(doc, registry=cmb.registry).check()
    assert any(v.law == "referential_integrity" and "dog_1" in v.detail
               for v in violations)


def test_events_ordered_by_timeline():
    from cassem.time import Timeline
    cmb = SemanticCMB(good_story())
    timeline = Timeline()
    timeline.assert_order("t1", "t2")
    at_or_before = cmb.events_at_or_before("t2", timeline)
    assert len(at_or_before) == 2
    assert any(e["pred"] == "hide" for e in at_or_before)
