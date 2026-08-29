"""THE CONV QUALIFICATION BATTERY - the goal's twenty permanent rows,
driven through the REAL router (no mocks of the system under test).

The cardinal failure this battery exists to catch:
    the machine says it remembered something
    when no committed assertion record exists.
Acknowledgment must occur only after state commit.
"""

import pytest

from cortex.router import HybridRouter


def fresh():
    return HybridRouter(mode="NATIVE_ONLY")


def answer(router, sentence):
    return router.turn(sentence)["answer"]


# 1 ------------------------------------------------- ask before tell
def test_ask_before_tell_is_honest_unknown():
    a = answer(fresh(), "does the cat chase the dog?")
    assert a["status"] == "ANSWERED"
    assert "i do not know" in a["text"]


# 2+3 ------------------------------------- tell then ask + provenance
def test_tell_then_ask_answers_with_user_provenance():
    router = fresh()
    told = answer(router, "the cat chases the dog.")
    assert told["acknowledgment"] \
        == "okay. you told me that the cat chases the dog."
    asked = answer(router, "does the cat chase the dog?")
    assert asked["text"] \
        == "based on what you told me, yes, the cat chases the dog."
    assert asked["source_class"] == "USER_ASSERTED"
    # and no invented symmetry
    other = answer(router, "does the dog chase the cat?")
    assert "i do not know" in other["text"]


# 4 ------------------------------------------------ negative assertion
def test_negative_assertion_preserves_negation_end_to_end():
    router = fresh()
    told = answer(router, "the cat does not chase the bird.")
    assert "does not chase" in told["acknowledgment"]
    asked = answer(router, "does the cat chase the bird?")
    assert asked["text"].startswith("based on what you told me, no")
    assert "does not chase" in asked["text"]


# 5 ------------------------------------------------ pronoun assertion
def test_pronoun_assertion_resolves_then_stores_the_referent():
    router = fresh()
    answer(router, "the cat is quiet.")
    told = answer(router, "it chases the dog.")
    assert told["acknowledgment"] \
        == "okay. you told me that the cat chases the dog."
    asked = answer(router, "does the cat chase the dog?")
    assert asked["text"].startswith("based on what you told me, yes")


# 6 ------------------------------------------------ explicit correction
def test_explicit_correction_supersedes_never_deletes():
    router = fresh()
    answer(router, "the bird is gray.")
    corrected = answer(router, "actually, the bird is brown.")
    assert "i will use 'the bird is brown'" in corrected["text"]
    assert "you previously said 'the bird is gray'" \
        in corrected["text"]
    records = {r["clause"]: r["lifecycle_status"]
               for r in router.dialogue.store.records}
    assert records["the bird is gray"] == "SUPERSEDED"
    assert records["the bird is brown"] == "ACTIVE"


# 7 ------------------------------------------------- unmarked conflict
def test_unmarked_conflict_asks_never_silently_chooses():
    router = fresh()
    answer(router, "the hen is gray.")
    clash = answer(router, "the hen is brown.")
    assert clash["status"] == "CLARIFICATION_REQUESTED"
    assert "is the second statement a correction?" in clash["text"]
    # nothing stored yet for brown
    clauses = [r["clause"] for r in router.dialogue.store.records]
    assert "the hen is brown" not in clauses
    confirmed = answer(router, "yes.")
    assert "i will use 'the hen is brown'" in confirmed["text"]
    asked = answer(router, "is the hen brown?")
    assert asked["text"].startswith("based on what you told me, yes")


def test_unmarked_conflict_denied_contests_both():
    router = fresh()
    answer(router, "the hen is gray.")
    answer(router, "the hen is brown.")
    denied = answer(router, "no.")
    assert "contested" in denied["text"]
    lifecycles = {r["lifecycle_status"]
                  for r in router.dialogue.store.records}
    assert lifecycles == {"CONTESTED"}
    asked = answer(router, "is the hen brown?")
    assert "conflicting statements" in asked["text"]


# 8 ------------------------------------------------------- retraction
def test_retraction_stops_use_but_keeps_the_record():
    router = fresh()
    answer(router, "the cat chases the dog.")
    retracted = answer(router, "forget what i said about the cat.")
    assert "no longer use" in retracted["text"]
    asked = answer(router, "does the cat chase the dog?")
    assert "i do not know" in asked["text"]
    assert router.dialogue.store.records[0]["lifecycle_status"] \
        == "RETRACTED"


# 9 ---------------------------------------------------- fresh session
def test_fresh_session_has_no_leakage():
    router = fresh()
    answer(router, "the cat chases the dog.")
    other = fresh()
    a = answer(other, "does the cat chase the dog?")
    assert "i do not know" in a["text"]
    assert other.dialogue.store.records == []


# 10 -------------------------------------------- verified/user conflict
def test_verified_and_user_conflict_shows_both_launders_neither():
    router = fresh()
    answer(router, "the cat is brown.")
    a = answer(router, "is the cat gray?")
    assert a["source_class"] == "CONFLICT"
    assert "the verified record says the cat is gray" in a["text"]
    assert "you told me the cat is brown" in a["text"]
    # the session record did NOT become verified
    assert router.dialogue.store.records[0]["truth_status"] == "GIVEN"


# 11+12+13 ------------------------------------------------ wh questions
def test_what_question_returns_the_missing_object():
    router = fresh()
    answer(router, "the cat chases the dog.")
    a = answer(router, "what does the cat chase?")
    assert a["text"] == "you told me that the cat chases the dog."


def test_who_question_returns_the_missing_agent():
    router = fresh()
    answer(router, "the cat chases the dog.")
    a = answer(router, "who chases the dog?")
    assert a["text"] == "you told me that the cat chases the dog."


def test_multiple_wh_bindings_are_listed_never_collapsed():
    router = fresh()
    answer(router, "the cat chases the dog.")
    answer(router, "the cat chases the fox.")
    a = answer(router, "what does the cat chase?")
    assert a["text"] \
        == "you told me that the cat chases the dog and the fox."
    assert a["wh_bindings"] == ["dog", "fox"]


def test_wh_unknown_is_honest():
    a = answer(fresh(), "what does the cat chase?")
    assert a["text"] == ("i do not know what the cat chases from "
                         "the information i have.")


# 14 ---------------------------------------------------------- greeting
def test_greeting_is_social_and_writes_no_fact():
    router = fresh()
    a = answer(router, "hello.")
    assert a["text"] == "hello."
    assert a["dialogue_act"] == "GREETING"
    assert router.dialogue.store.records == []
    assert answer(router, "thank you.")["text"] == "you are welcome."
    assert answer(router, "goodbye.")["text"] == "goodbye."


# 15 -------------------------------------------------------- bare yes/no
def test_bare_yes_no_requires_a_pending_question():
    router = fresh()
    a = answer(router, "yes.")
    assert a["status"] == "NO_PENDING_QUESTION"
    b = answer(router, "no.")
    assert b["status"] == "NO_PENDING_QUESTION"


# 16+17 --------------------------------------- hypothetical and quoted
def test_hypothetical_and_quoted_content_never_enter_the_store():
    router = fresh()
    hyp = answer(router, "suppose the cat chases the dog.")
    assert hyp["status"] == "UNSUPPORTED_LANGUAGE"
    quoted = answer(
        router, "the phrase 'the cat chases the dog' has five words.")
    assert quoted["status"] == "UNSUPPORTED_LANGUAGE"
    assert router.dialogue.store.records == []


# 18 ------------------------------------------ instruction-shaped input
def test_instruction_shaped_content_is_data_not_action():
    router = fresh()
    a = answer(router, "give the bone to the dog.")
    assert a["status"] == "UNDERSTOOD"
    assert "acknowledgment" not in a          # not stored as a fact
    assert router.dialogue.store.records == []
    trace = router.traces[-1]
    assert trace["dialogue"]["act"] == "COMMAND"


# 19 ------------------------------------------------ deterministic replay
def test_deterministic_replay_same_traces_same_store():
    script = ["does the cat chase the dog?",
              "the cat chases the dog.",
              "does the cat chase the dog?",
              "actually, the cat chases the fox.",
              "what does the cat chase?",
              "forget what i said about the cat."]
    r1, r2 = fresh(), fresh()
    d1 = [r1.turn(s)["trace_digest"] for s in script]
    d2 = [r2.turn(s)["trace_digest"] for s in script]
    assert d1 == d2
    assert r1.dialogue.store.to_json() == r2.dialogue.store.to_json()


# 20 ------------------------------------------------------- store fault
class _BrokenStore:
    session_id = "session"
    records = []

    def next_id(self):
        return "a1"

    def active(self):
        return []

    def contested(self):
        return []

    def _append_committed(self, record):
        raise IOError("disk gone")


def test_store_fault_is_typed_and_never_fake_acknowledged():
    """THE CARDINAL LAW: no committed record -> no acknowledgment."""
    router = fresh()
    router.dialogue.store = _BrokenStore()
    router.dialogue.coordinator.store = router.dialogue.store
    a = answer(router, "the cat chases the dog.")
    assert a["status"] == "ASSERTION_NOT_RECORDED"
    assert "acknowledgment" not in a
    assert "NOT remembered" in a["detail"]
    trace = router.traces[-1]
    assert trace["conv_flow"]["tp_session_commit"] == "cutoff"


# ---------------------------------------------- the cardinal invariant
def test_acknowledgment_iff_committed_record():
    """Scan a whole conversation: every acknowledgment corresponds to
    a committed record whose digest the trace names."""
    router = fresh()
    script = ["the cat chases the dog.", "hello.",
              "the cat does not chase the bird.",
              "does the cat chase the dog?",
              "give the bone to the dog."]
    for sentence in script:
        router.turn(sentence)
    by_id = {r["assertion_id"]: r
             for r in router.dialogue.store.records}
    for trace in router.traces:
        ack = (trace.get("answer") or {}).get("acknowledgment")
        session = (trace.get("answer") or {}).get("session_assertion")
        if ack:
            assert session is not None
            record = by_id[session["assertion_id"]]
            assert record["record_digest"] \
                == session["record_digest"]
        else:
            assert session is None or "assertion_id" in session


# ---------------------------------------------- CAS-Ohm flow points
def test_conv_flow_distinguishes_memory_write_from_language():
    router = fresh()
    told = router.turn("the cat chases the dog.")
    assert told["conv_flow"]["tp_parse"] == "active"
    assert told["conv_flow"]["tp_write_intent"] == "active"
    assert told["conv_flow"]["tp_session_commit"] == "active"
    asked = router.turn("does the cat chase the dog?")
    assert asked["conv_flow"]["tp_retrieval"] == "active"
    assert asked["conv_flow"]["tp_session_commit"] == "absent"
    failed = router.turn("suppose the cat chases the dog.")
    assert failed["conv_flow"]["tp_parse"] == "cutoff"
    assert failed["conv_flow"]["tp_write_intent"] == "absent"


# ---------------------------------------------- entity summary (1E)
def test_entity_summary_groups_by_provenance():
    router = fresh()
    router.turn("the dog chases the cat.")
    a = answer(router, "tell me about the dog.")
    assert "the verified record says the dog is brown." in a["text"]
    assert "you told me that the dog chases the cat." in a["text"]
    b = answer(router, "tell me about the table.")
    assert b["text"] == "i have no information about the table."
