"""CCB-D1 unit laws: the store, the intent validator (anti-laundering
lives here), sound entailment, conflicts, rendering."""

import pytest

from dialogue import (DialogueBoard, IntentRejected,
                      SessionAssertionStore, TransactionCoordinator,
                      make_lifecycle_intent, make_write_intent,
                      validate_intent)
from dialogue.assertions import AssertionStoreError


def _intent(prop=None, **overrides):
    intent = make_write_intent(
        prop or {"pred": "relation", "args": ["chase", "cat", "dog"]},
        "the cat chases the dog", "present", "positive", None,
        "user", "session", "t1", 1, "user_turn:t1")
    intent.update(overrides)
    return intent


# ------------------------------------------------- the intent validator
def test_write_intent_valid():
    assert validate_intent(_intent()) == []


def test_anti_laundering_verified_refused():
    """THE LAW: a session assertion may never claim VERIFIED."""
    defects = validate_intent(_intent(truth_status="VERIFIED"))
    assert any("never claim" in d for d in defects)


def test_unknown_source_class_refused():
    assert validate_intent(_intent(source_class="ORACLE"))


def test_forbidden_authority_fields_refused():
    for field in ("verified", "promote", "tool", "memory_write"):
        assert validate_intent(_intent(**{field: True}))


def test_lifecycle_intent_cannot_reactivate():
    defects = validate_intent(make_lifecycle_intent(
        "a1", "ACTIVE", "sneaky", "t2"))
    assert any("re-activate" in d for d in defects)


# ------------------------------------------------- the coordinator
def test_only_coordinator_commits_and_ids_are_sequential():
    store = SessionAssertionStore()
    coord = TransactionCoordinator(store)
    r1 = coord.commit(_intent())
    assert r1["assertion_id"] == "a1"
    assert r1["lifecycle_status"] == "ACTIVE"
    assert r1["truth_status"] == "GIVEN"
    with pytest.raises(AssertionStoreError):
        store._append_committed(dict(r1, assertion_id="a9"))


def test_rejected_intent_leaves_no_state():
    store = SessionAssertionStore()
    coord = TransactionCoordinator(store)
    with pytest.raises(IntentRejected):
        coord.commit(_intent(truth_status="VERIFIED"))
    assert store.records == []


def test_retracted_records_are_immutable_history():
    store = SessionAssertionStore()
    coord = TransactionCoordinator(store)
    record = coord.commit(_intent())
    coord.commit(make_lifecycle_intent(record["assertion_id"],
                                       "RETRACTED", "user", "t2"))
    with pytest.raises(AssertionStoreError):
        coord.commit(make_lifecycle_intent(record["assertion_id"],
                                           "SUPERSEDED", "again",
                                           "t3"))
    assert store.get("a1")["lifecycle_status"] == "RETRACTED"


# ------------------------------------------------- sound entailment
def _board_with(*props):
    board = DialogueBoard()
    for i, (prop, tense) in enumerate(props, 1):
        board.begin_turn()
        board.record_assertion(prop, f"clause {i}", tense,
                               "positive", None, f"t{i}",
                               f"user_turn:t{i}")
    return board


REL = {"pred": "relation", "args": ["chase", "cat", "dog"]}
REL_REV = {"pred": "relation", "args": ["chase", "dog", "cat"]}
NEG = {"pred": "negation", "args": [REL]}


def test_equality_supports_yes_and_symmetry_is_never_inferred():
    board = _board_with((REL, "present"))
    assert board.support_for(REL, "present")["verdict"] == "yes"
    assert board.support_for(REL_REV, "present") is None


def test_negation_supports_no():
    board = _board_with((NEG, "present"))
    assert board.support_for(REL, "present")["verdict"] == "no"


def test_tense_is_strict_when_both_known():
    board = _board_with((REL, "past"))
    assert board.support_for(REL, "present") is None
    assert board.support_for(REL, "past")["verdict"] == "yes"


def test_conjunction_membership_supports_disjunction_never():
    conj = {"pred": "conjunction", "args": [REL, NEG]}
    board = _board_with(({"pred": "conjunction",
                          "args": [REL_REV, REL]}, "present"))
    assert board.support_for(REL, "present")["verdict"] == "yes"
    disj_board = _board_with(({"pred": "disjunction",
                               "args": [REL, REL_REV]}, "present"))
    assert disj_board.support_for(REL, "present") is None
    del conj


def test_prohibition_and_quantifier_support_nothing_singular():
    board = _board_with(
        (({"pred": "prohibition", "args": [REL]}), "present"),
        (({"pred": "quantified",
           "args": ["every", REL_REV]}), "present"))
    assert board.support_for(REL, "present") is None
    assert board.support_for(REL_REV, "present") is None


# ------------------------------------------------- conflicts
def test_polarity_conflict_same_tense_only():
    board = _board_with((REL, "past"))
    assert board.conflicting_active(NEG, "present") == []
    board2 = _board_with((REL, "present"))
    assert len(board2.conflicting_active(NEG, "present")) == 1


def test_exclusive_attribute_conflict():
    gray = {"pred": "property", "args": ["cat", "gray"]}
    brown = {"pred": "property", "args": ["cat", "brown"]}
    quiet = {"pred": "property", "args": ["cat", "quiet"]}
    board = _board_with((gray, "present"))
    assert len(board.conflicting_active(brown, "present")) == 1
    assert board.conflicting_active(quiet, "present") == []


# ------------------------------------------------- rendering
def test_clause_rendering_preserves_negation_and_norms():
    board = DialogueBoard()
    assert board.packet_to_clause(NEG, "present") \
        == "the cat does not chase the dog"
    assert board.packet_to_clause(NEG, "past") \
        == "the cat did not chase the dog"
    assert board.packet_to_clause(
        {"pred": "prohibition", "args": [REL]}) \
        == "the cat must not chase the dog"
    assert board.packet_to_clause(
        {"pred": "quantified", "args": ["no", REL]}) \
        == "no cat chases the dog"
