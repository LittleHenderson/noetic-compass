"""Regression locks for the TEN adversarial-audit findings
(workflow wf_b6ba36b7, 2026-08-29): every confirmed defect gets the
test that would have caught it."""

from cortex.router import HybridRouter


def fresh():
    return HybridRouter(mode="NATIVE_ONLY")


def answer(router, sentence):
    return router.turn(sentence)["answer"]


# audit 1+3+7: retraction between clarification and 'yes.' must never
# crash, never ghost-commit, never claim a supersession that did not
# happen
def test_stale_confirmation_after_retraction_never_crashes_or_ghosts():
    router = fresh()
    answer(router, "the hen is gray.")
    answer(router, "the hen is brown.")           # clarification
    answer(router, "forget what i said about the hen.")
    late = answer(router, "yes.")                 # must NOT crash
    assert late["status"] == "NO_PENDING_QUESTION"
    clauses = {r["clause"]: r["lifecycle_status"]
               for r in router.dialogue.store.records}
    assert clauses == {"the hen is gray": "RETRACTED"}
    # every turn sealed - no untraced mutation
    assert len(router.traces) == 4
    asked = answer(router, "is the hen brown?")
    assert "i do not know" in asked["text"]


# audit 5: a pending clarification drops when the user moves on
def test_pending_clarification_drops_when_user_moves_on():
    router = fresh()
    answer(router, "the hen is gray.")
    answer(router, "the hen is brown.")           # clarification
    moved = router.turn("does the cat chase the dog?")
    assert moved["dialogue"]["pending_dropped"] \
        == "correction_confirmation"
    late = answer(router, "yes.")
    assert late["status"] == "NO_PENDING_QUESTION"
    clauses = [r["clause"] for r in router.dialogue.store.records]
    assert "the hen is brown" not in clauses      # never committed


# audit 2: wrapper-masked contradictions are caught at tell time,
# in BOTH orders
def test_wrapped_contradiction_caught_at_tell_both_orders():
    router = fresh()
    answer(router, "the gray cat chases the brown dog.")
    clash = answer(router, "the cat does not chase the dog.")
    assert clash["status"] == "CLARIFICATION_REQUESTED"
    other = fresh()
    answer(other, "the cat does not chase the dog.")
    clash2 = answer(other, "the gray cat chases the brown dog.")
    assert clash2["status"] == "CLARIFICATION_REQUESTED"


# audit 2 (quantifier face): 'no cat chases the dog' stands against
# 'the cat chases the dog'
def test_quantified_no_conflicts_with_bare_assertion():
    router = fresh()
    answer(router, "no cat chases the dog.")
    clash = answer(router, "the cat chases the dog.")
    assert clash["status"] == "CLARIFICATION_REQUESTED"


# audit 8: restricted (conjunction) questions surface conflicts
def test_conjunction_question_surfaces_verified_user_conflict():
    router = fresh()
    answer(router, "the cat is brown.")           # verified says gray
    asked = answer(router, "is the gray cat quiet?")
    assert asked["source_class"] == "CONFLICT"
    assert "the verified record says the cat is gray" in asked["text"]
    assert "you told me the cat is brown" in asked["text"]


# audit 9, CLOSED BY CONV v0.2: an explicit relation correction now
# SUPERSEDES the matching prior relation (same predicate + subject,
# different object); with truly nothing to supersede, the disclosure
# stands
def test_relation_correction_supersedes_the_matching_relation():
    router = fresh()
    answer(router, "the cat chases the dog.")
    corrected = answer(router, "actually, the cat chases the fox.")
    assert "you previously said 'the cat chases the dog'" \
        in corrected["text"]
    states = {r["clause"]: r["lifecycle_status"]
              for r in router.dialogue.store.records}
    assert states["the cat chases the dog"] == "SUPERSEDED"
    assert states["the cat chases the fox"] == "ACTIVE"
    asked = answer(router, "what does the cat chase?")
    assert asked["text"] == "you told me that the cat chases the fox."


def test_correction_without_target_is_still_disclosed():
    router = fresh()
    corrected = answer(router, "actually, the cat chases the fox.")
    assert "nothing was superseded" in corrected["text"]
    trace = router.traces[-1]
    assert trace["dialogue"]["correction_without_target"] is True


# audit 10: coordination tense is derived, never a wildcard
def test_coordination_tense_never_wildcards_to_past():
    router = fresh()
    told = answer(router,
                  "the cat chases the dog and the fox carries "
                  "the bone.")
    assert "carries" in told["acknowledgment"]    # not 'carrys'
    record = router.dialogue.store.records[0]
    assert record["tense"] == "present"
    asked = answer(router, "did the cat chase the dog?")
    assert "i do not know" in asked["text"]
    # present question still supported through conjunction membership
    now = answer(router, "does the cat chase the dog?")
    assert now["text"].startswith("based on what you told me, yes")


# audit 4: CONTESTED records are visible to retraction and summary
def test_contested_records_visible_to_retraction_and_summary():
    router = fresh()
    answer(router, "the hen is gray.")
    answer(router, "the hen is brown.")           # clarification
    answer(router, "no.")                         # both CONTESTED
    summary = answer(router, "tell me about the hen.")
    assert "conflicting statements" in summary["text"]
    assert "unsettled" in summary["text"]
    gone = answer(router, "forget what i said about the hen.")
    assert "no longer use" in gone["text"]
    assert all(r["lifecycle_status"] == "RETRACTED"
               for r in router.dialogue.store.records)
    asked = answer(router, "is the hen brown?")
    assert "i do not know" in asked["text"]


# audit 6: a store fault during confirmation is TYPED, never a crash
def test_store_fault_on_confirmation_is_typed_never_a_crash():
    router = fresh()
    answer(router, "the hen is gray.")
    answer(router, "the hen is brown.")           # clarification

    def broken(*args, **kwargs):
        raise IOError("disk gone")

    router.dialogue.record_assertion = broken
    late = answer(router, "yes.")
    assert late["status"] == "ASSERTION_NOT_RECORDED"
    assert "NOT completed" in late["detail"]
    assert len(router.traces) == 3                # turn still sealed


# audit 6 (retraction face): a store fault mid-retraction is typed
# and says exactly how far it got
def test_store_fault_on_retraction_is_typed_and_partial_disclosed():
    router = fresh()
    answer(router, "the hen is gray.")

    def broken(*args, **kwargs):
        raise IOError("disk gone")

    router.dialogue.apply_lifecycle = broken
    gone = answer(router, "forget what i said about the hen.")
    assert gone["status"] == "ASSERTION_NOT_RECORDED"
    assert "retracted so far: nothing" in gone["detail"]
    assert router.dialogue.store.records[0]["lifecycle_status"] \
        == "ACTIVE"