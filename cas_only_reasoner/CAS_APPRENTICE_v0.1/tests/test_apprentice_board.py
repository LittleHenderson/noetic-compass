"""CCB-A1: the domain-general teaching board. The teacher proposes;
the CNCM decides; constitutional targets never promote; high-impact
lessons need a second examiner; facts follow the stricter protocol."""

from apprentice.board import (HIGH_IMPACT_DOMAINS, NEVER_AUTONOMOUS,
                              ApprenticeshipBoard, NeverAutonomous)
from apprentice.knowledge import (DESTINATIONS, KnowledgeChannel,
                                  TrustedSourceStore)

import pytest


def _fact_lesson(claim, knowledge_type="stable_fact", **overrides):
    lesson = {"lesson_id": "K001", "domain": "world_knowledge",
              "target": "semantic_memory",
              "claim": claim, "knowledge_type": knowledge_type,
              "source": "teacher_model_output",
              "validity": {"window": None}, "scope": "general",
              "confidence": 0.95,
              "verification_method": "trusted_source_attestation",
              "teacher_model": "qwen-3b",
              "examiner_identity": "trusted_source_store",
              "provenance": "teaching_test"}
    lesson.update(overrides)
    return lesson


def _trusted():
    return TrustedSourceStore({
        "encyclopedia_a": ["water boils at 100 C at sea level",
                           "NOT: the sun orbits the earth"],
        "physics_text_b": ["water boils at 100 C at sea level",
                           "light travels faster than sound"],
        "old_almanac_c": ["the sun orbits the earth"],
    })


# --------------------------------------------- the never-autonomous law
def test_constitutional_targets_never_promote():
    board = ApprenticeshipBoard()
    for target in NEVER_AUTONOMOUS:
        lesson = _fact_lesson("anything", target=target)
        with pytest.raises(NeverAutonomous, match="cannot vote itself"):
            board.teach(lesson, KnowledgeChannel(_trusted()))
    # every refusal is a sealed episode on the record
    assert len(board.episodes) == len(NEVER_AUTONOMOUS)
    assert all(e["outcome"]["verdict"] == "REJECTED_NEVER_AUTONOMOUS"
               for e in board.episodes)


# --------------------------------------------- the faculty-committee law
def test_high_impact_lessons_need_a_second_examiner():
    board = ApprenticeshipBoard()
    assert "world_knowledge" in HIGH_IMPACT_DOMAINS
    solo = _fact_lesson("water boils at 100 C at sea level")
    solo["examiner_identity"] = solo["teacher_model"]   # same identity
    episode = board.teach(solo, KnowledgeChannel(_trusted()))
    assert episode["outcome"]["verdict"] == "REJECTED_SINGLE_EXAMINER"
    proper = _fact_lesson("water boils at 100 C at sea level")
    episode2 = board.teach(proper, KnowledgeChannel(_trusted()))
    assert episode2["outcome"]["verdict"] == "PROMOTED_VERIFIED"


# --------------------------------------------- the stricter fact protocol
def test_model_facts_enter_proposed_never_verified():
    channel = KnowledgeChannel(_trusted())
    board = ApprenticeshipBoard()
    episode = board.teach(
        _fact_lesson("the zorble mountains are in freedonia"), channel)
    assert episode["outcome"]["verdict"] == "STORED_PROPOSED"
    record = episode["outcome"]["record"]
    assert record["truth_status"] == "PROPOSED"
    assert record["teacher_confidence_informational_only"] == 0.95


def test_trusted_sources_verify_or_contradict():
    channel = KnowledgeChannel(_trusted())
    board = ApprenticeshipBoard()
    verified = board.teach(
        _fact_lesson("water boils at 100 C at sea level"), channel)
    assert verified["outcome"]["verdict"] == "PROMOTED_VERIFIED"
    assert verified["outcome"]["record"]["truth_status"] == "VERIFIED"
    assert len(verified["outcome"]["evidence"]["supporting"]) == 2
    contradicted = board.teach(
        _fact_lesson("the sun orbits the earth", lesson_id="K002"),
        channel)
    # one source supports (old almanac), one contradicts -> CONTESTED
    assert contradicted["outcome"]["verdict"] == "STORED_CONTESTED"
    assert contradicted["outcome"]["record"]["truth_status"] == \
        "CONTESTED"


def test_changing_facts_need_current_retrieval_and_window():
    channel = KnowledgeChannel(_trusted())
    board = ApprenticeshipBoard()
    stale = _fact_lesson("the current version is 3.14",
                         knowledge_type="current_fact")
    episode = board.teach(stale, channel)
    assert episode["outcome"]["verdict"] == "REJECTED_STALE_SOURCE"
    no_window = _fact_lesson("the current version is 3.14",
                             knowledge_type="current_fact",
                             source_kind="current_retrieval")
    episode2 = board.teach(no_window, channel)
    assert episode2["outcome"]["verdict"] == "REJECTED_NO_VALIDITY_WINDOW"
    proper = _fact_lesson("the current version is 3.14",
                          knowledge_type="current_fact",
                          source_kind="current_retrieval",
                          validity={"window": "2026-08"})
    episode3 = board.teach(proper, channel)
    assert episode3["outcome"]["verdict"] == "STORED_PROPOSED"
    assert episode3["outcome"]["record"]["destination"] == \
        "source_linked_retrieval_record"


def test_hard_boundaries_never_enter_through_teaching():
    channel = KnowledgeChannel(_trusted())
    board = ApprenticeshipBoard()
    episode = board.teach(
        _fact_lesson("never harm", knowledge_type="hard_boundary"),
        channel)
    assert episode["outcome"]["verdict"] == \
        "REJECTED_SEPARATE_AUTHORIZATION"


def test_typed_destinations_cover_the_doctrine():
    assert DESTINATIONS["stable_fact"] == "semantic_memory"
    assert DESTINATIONS["procedure"] == "procedural_memory"
    assert DESTINATIONS["personal_experience"] == "episodic_memory"
    assert "SEPARATELY_AUTHORIZED" in DESTINATIONS["hard_boundary"]


# --------------------------------------------------- teaching metrics
def test_teaching_metrics():
    board = ApprenticeshipBoard()
    channel = KnowledgeChannel(_trusted())
    board.teach(_fact_lesson("water boils at 100 C at sea level"),
                channel, pre_capability=3.0, post_capability=7.0)
    board.teach(_fact_lesson("light travels faster than sound",
                             lesson_id="K003"),
                channel, pre_capability=7.0, post_capability=7.5)
    metrics = board.metrics(teacher_assisted=2, total_tasks=10,
                            held_out_successes=4, held_out_total=5,
                            teacher_compute_cost=2.0,
                            delayed_capability=7.2)
    assert metrics["episodes"] == 2
    assert metrics["learning_gain"] == 4.5
    assert metrics["transfer_rate"] == 0.8
    assert metrics["teaching_efficiency"] == 2.25
    assert metrics["teacher_dependence"] == 0.2
    assert metrics["retention"] == 0.96
    assert metrics["false_lesson_rate"] == 0.0
