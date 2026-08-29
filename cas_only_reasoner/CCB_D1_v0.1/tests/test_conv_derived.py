"""CONV v0.2 - DERIVED COMMON GROUND: session assertions enter
inference through EXPLICIT rules only; derived answers carry their
whole source chain; derived never becomes verified."""

from cortex.router import HybridRouter


def fresh():
    return HybridRouter(mode="NATIVE_ONLY")


def answer(router, sentence):
    return router.turn(sentence)


def test_milo_derivation_with_full_source_chain():
    router = fresh()
    assert "i do not know" in answer(
        router, "is milo an animal?")["answer"]["text"]
    answer(router, "every cat is an animal.")
    answer(router, "milo is a cat.")
    trace = answer(router, "is milo an animal?")
    assert trace["answer"]["text"] \
        == "given the two things you told me, yes, milo is an animal."
    derivation = trace["answer_derivation"]
    assert derivation["status"] == "DERIVED"
    assert derivation["source_class"] == "USER_ASSERTED_PREMISES"
    assert derivation["rule"] == "class_inheritance"
    assert len(derivation["premises"]) == 2


def test_two_hop_chain_and_premise_count():
    router = fresh()
    answer(router, "every cat is an animal.")
    answer(router, "every animal is a creature.")
    answer(router, "milo is a cat.")
    trace = answer(router, "is milo a creature?")
    assert "given the three things you told me, yes" \
        in trace["answer"]["text"]
    assert len(trace["answer_derivation"]["premises"]) == 3


def test_no_symmetry_or_free_transitivity():
    router = fresh()
    answer(router, "milo is a cat.")
    assert "i do not know" in answer(
        router, "is the cat a milo?")["answer"]["text"]
    # membership does NOT chain through membership (only through
    # explicit class rules): 'the dog is a cat' + 'milo is a dog'
    # derives nothing about milo being a cat
    other = fresh()
    answer(other, "the dog is a cat.")
    answer(other, "milo is a dog.")
    assert "i do not know" in answer(
        other, "is milo a cat?")["answer"]["text"]


def test_derived_stays_distinct_from_verified():
    router = fresh()
    answer(router, "every cat is an animal.")
    answer(router, "milo is a cat.")
    trace = answer(router, "is milo an animal?")
    assert trace["answer"]["source_class"] \
        == "USER_ASSERTED_PREMISES"
    assert "given the" in trace["answer"]["text"]  # never a bare yes
    for record in router.dialogue.store.records:
        assert record["truth_status"] == "GIVEN"
    # the verified store is untouched
    assert all(fact["pred"] == "has"
               for fact in router.seed["cmb_facts"])


def test_direct_membership_answers_without_derivation():
    router = fresh()
    answer(router, "milo is a cat.")
    trace = answer(router, "is milo a cat?")
    assert trace["answer"]["text"] \
        == "based on what you told me, yes, milo is a cat."
    assert trace["answer"]["source_class"] == "USER_ASSERTED"


# ---------------- CONV correction-path audit regressions
def test_correction_preserves_negation_in_clause_and_store():
    router = fresh()
    answer(router, "the cat chases the dog.")
    corrected = answer(router,
                       "actually, the cat does not chase the dog.")
    text = corrected["answer"]["text"]
    assert "does not chase" in text
    active = [r for r in router.dialogue.store.records
              if r["lifecycle_status"] == "ACTIVE"]
    assert len(active) == 1
    assert "does not chase" in active[0]["clause"]
    summary = answer(router, "tell me about the dog.")
    assert "does not chase" in summary["answer"]["text"]


def test_correction_preserves_prohibition():
    router = fresh()
    answer(router, "the cat chases the dog.")
    corrected = answer(router,
                       "actually, the cat must not chase the dog.")
    assert "must not chase" in corrected["answer"]["text"]


def test_coordination_correction_does_not_wildcard_tense():
    router = fresh()
    answer(router, "the cat chases the bird.")
    answer(router, "actually, the cat chases the dog and the fox "
                   "chases the hen.")
    record = [r for r in router.dialogue.store.records
              if r["lifecycle_status"] == "ACTIVE"][0]
    assert record["tense"] == "present"
    past = answer(router, "did the cat chase the dog?")
    assert "i do not know" in past["answer"]["text"]


def test_question_after_actually_is_not_committed():
    router = fresh()
    result = answer(router, "actually, is the dog brown?")
    assert result["answer"]["status"] == "UNSUPPORTED_LANGUAGE"
    assert router.dialogue.store.records == []


def test_relation_correction_supersedes_matching_relation():
    router = fresh()
    answer(router, "the cat chases the dog.")
    answer(router, "actually, the cat chases the fox.")
    states = {r["clause"]: r["lifecycle_status"]
              for r in router.dialogue.store.records}
    assert states["the cat chases the dog"] == "SUPERSEDED"
    assert states["the cat chases the fox"] == "ACTIVE"


def test_class_correction_supersedes_and_derivation_follows():
    router = fresh()
    answer(router, "milo is a cat.")
    answer(router, "every cat is an animal.")
    answer(router, "actually, milo is a dog.")
    # the corrected-away membership must not drive a derivation
    states = {}
    for r in router.dialogue.store.records:
        if r["proposition"].get("pred") == "is_a":
            states[r["proposition"]["args"][1]] = r["lifecycle_status"]
    assert states.get("cat") == "SUPERSEDED"
    assert states.get("dog") == "ACTIVE"
    trace = answer(router, "is milo an animal?")
    # milo is now a dog, and no rule says dogs are animals
    assert "i do not know" in trace["answer"]["text"]
