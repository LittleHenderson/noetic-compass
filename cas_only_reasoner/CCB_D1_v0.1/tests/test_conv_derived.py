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
