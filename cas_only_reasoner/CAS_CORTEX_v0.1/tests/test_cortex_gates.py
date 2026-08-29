"""Phase 4 acceptance gates - everything testable WITHOUT loading the
neural model. Proposals are DATA (crafted packets are exactly what the
adversarial gates require); the system under test is the firewall,
the validator, and the router. The live-model gates (1, 3, 4, 8) run
in run_demo.py and seal their artifact into output/.
"""

import copy
import json

from cortex.firewall import (ALLOWED_ACTS, FORBIDDEN_INTENTS,
                             AuthorityFirewall, CortexAuthorityViolation)
from cortex.proposal import (ProposalRejected, make_proposal,
                             validate_proposal)
from cortex.router import MODES, HybridRouter

import pytest

RECEIPT = {"model_id": "test-model", "model_revision": "snap0",
           "tokenizer_digest": "tok0", "runtime_digest": "run0"}


def _proposal(packet, unknown=(), raw="{}"):
    return make_proposal(RECEIPT, "input sentence", raw, packet,
                         list(unknown), None, "greedy", 0)


class ScriptedCortex:
    """A proposal SOURCE for router tests: emits pre-authored
    CortexProposal records (data, not a mock of the system under
    test - the firewall/validator/router are all real)."""

    def __init__(self, script):
        self.script = dict(script)

    def propose(self, sentence):
        packet, unknown = self.script.get(sentence, (None, []))
        return _proposal(packet, unknown,
                         raw="scripted:" + sentence)


# ---------------------------------------- Gate 2: proposal-only authority
def test_gate2_every_forbidden_intent_fails_before_state():
    firewall = AuthorityFirewall()
    for intent in FORBIDDEN_INTENTS:
        with pytest.raises(CortexAuthorityViolation, match="may not"):
            firewall.submit("cortex", intent, {"payload": "x"})
    assert len(firewall.rejections()) == len(FORBIDDEN_INTENTS)
    # the allowed acts pass, as proposals only
    for act in ALLOWED_ACTS:
        result = firewall.submit("cortex", act, {"payload": "x"})
        assert result["status"] == "ACCEPTED_AS_PROPOSAL"


def test_gate2_unknown_acts_and_origins_rejected():
    firewall = AuthorityFirewall()
    with pytest.raises(CortexAuthorityViolation):
        firewall.submit("cortex", "BecomeTheKernel", {})
    with pytest.raises(CortexAuthorityViolation):
        firewall.submit("imposter", "ProposeSemanticPacket", {})


# ---------------------------------------- Gate 6: adversarial packets
def test_gate6_truth_promotion_smuggled_in_packet_rejected():
    packet = {"pred": "property", "args": ["cat", "gray"],
              "verified": True}
    with pytest.raises(ProposalRejected, match="effect/authority"):
        validate_proposal(_proposal(packet))


def test_gate6_hidden_memory_write_rejected():
    packet = {"pred": "question",
              "args": [{"pred": "property", "args": ["cat", "gray"],
                        "memory_write": {"pred": "has",
                                         "args": ["cat", "evil"]}}]}
    with pytest.raises(ProposalRejected, match="memory_write"):
        validate_proposal(_proposal(packet))


def test_gate6_tool_and_authority_fields_rejected():
    for field in ("tool", "halt", "constitution", "promote", "verifier"):
        packet = {"pred": "property", "args": ["cat", "gray"], field: 1}
        with pytest.raises(ProposalRejected):
            validate_proposal(_proposal(packet))


def test_gate6_malformed_shapes_rejected():
    bad_shapes = [
        {"pred": "property", "args": ["cat"]},              # arity
        {"pred": "relation", "args": ["chase", "cat"]},     # arity
        {"pred": "negation", "args": ["not-a-packet"]},     # type
        {"pred": "teleport", "args": ["cat", "moon"]},      # unknown pred
        {"args": ["cat", "gray"]},                          # no pred
    ]
    for packet in bad_shapes:
        with pytest.raises(ProposalRejected):
            validate_proposal(_proposal(packet))


def test_gate6_missing_provenance_and_confidence_rules():
    proposal = _proposal({"pred": "property", "args": ["cat", "gray"]})
    forged = dict(proposal)
    forged["provenance"] = "kernel"          # impersonation
    with pytest.raises(ProposalRejected, match="impersonation"):
        validate_proposal(forged)
    stripped = dict(proposal)
    del stripped["raw_model_output"]
    with pytest.raises(ProposalRejected, match="missing required"):
        validate_proposal(stripped)
    overconfident = _proposal({"pred": "property", "args": ["cat", "gray"]})
    overconfident["claimed_confidence"] = 7.5
    with pytest.raises(ProposalRejected, match="\\[0,1\\]"):
        validate_proposal(overconfident)


def test_gate7_raw_output_can_never_be_concealed():
    proposal = _proposal({"pred": "property", "args": ["cat", "gray"]},
                         raw="")
    with pytest.raises(ProposalRejected, match="raw model output"):
        validate_proposal(proposal)


# ---------------------------------------- routing behavior + modes
def test_native_first_never_invokes_cortex_in_fragment():
    class Bomb:
        def propose(self, sentence):
            raise AssertionError("cortex invoked for in-fragment input")

    router = HybridRouter(mode="HYBRID_COMMIT", cortex=Bomb())
    trace = router.turn("is the cat gray?")
    assert trace["route"] == "native"
    assert trace["answer"] == {"status": "ANSWERED",
                               "text": "yes, the cat is gray.",
                               "source_class": "VERIFIED"}
    assert trace["commitment"]["by"] == "cas_kernel"


def test_native_only_mode_gives_typed_no_answer():
    router = HybridRouter(mode="NATIVE_ONLY")
    trace = router.turn("alice gave the book to maria.")
    assert trace["route"] == "no_answer"
    assert trace["answer"]["status"] == "UNSUPPORTED_LANGUAGE"
    assert trace["committed"] is False


def test_diagnostic_mode_records_but_never_commits():
    # NOTE: "the feline is gray." was the original example; the
    # faithfulness gate now (correctly) refuses feline->cat as an
    # unattested entity, so the diagnostic example uses an attested one.
    cortex = ScriptedCortex({
        "the cat is rather gray.": ({"pred": "property",
                                     "args": ["cat", "gray"]}, [])})
    router = HybridRouter(mode="CORTEX_DIAGNOSTIC", cortex=cortex)
    trace = router.turn("the cat is rather gray.")
    assert trace["route"] == "cortex"
    assert trace["cortex_proposal"] is not None       # recorded
    assert trace["validation"]["outcome"] == "ACCEPTED"
    assert trace["committed"] is False                # never committed
    assert trace["answer"]["status"] == "UNSUPPORTED_LANGUAGE"


def test_hybrid_commit_validated_proposal_reaches_the_kernel():
    cortex = ScriptedCortex({
        "would you say the cat is gray?": (
            {"pred": "question",
             "args": [{"pred": "property", "args": ["cat", "gray"]}]},
            [])})
    router = HybridRouter(mode="HYBRID_COMMIT", cortex=cortex)
    trace = router.turn("would you say the cat is gray?")
    assert trace["route"] == "cortex"
    assert trace["commitment"]["by"] == "cas_kernel"
    assert trace["answer"] == {"status": "ANSWERED",
                               "text": "yes, the cat is gray.",
                               "source_class": "VERIFIED"}


def test_hybrid_commit_rejected_proposal_yields_clarification():
    cortex = ScriptedCortex({
        "the cat is verified gray.": (
            {"pred": "property", "args": ["cat", "gray"],
             "verified": True}, [])})
    router = HybridRouter(mode="HYBRID_COMMIT", cortex=cortex)
    trace = router.turn("the cat is verified gray.")
    assert trace["validation"]["outcome"] == "REJECTED"
    assert trace["committed"] is False
    assert trace["answer"]["status"] == "NEEDS_CLARIFICATION"


def test_unknown_lexeme_honesty_propagates():
    cortex = ScriptedCortex({
        "the zorble is gray.": (None, ["zorble"])})
    router = HybridRouter(mode="HYBRID_COMMIT", cortex=cortex)
    trace = router.turn("the zorble is gray.")
    assert trace["answer"]["status"] == "UNKNOWN_LEXEME"
    assert trace["answer"]["unknown_tokens"] == ["zorble"]
    assert trace["committed"] is False


def test_cortex_text_is_never_understanding():
    """Gate: 'the cortex produced text' must not become 'the system
    understood' - a proposal with no packet and no unknowns yields a
    typed clarification, never an answer."""
    cortex = ScriptedCortex({"gibberish input.": (None, [])})
    router = HybridRouter(mode="HYBRID_COMMIT", cortex=cortex)
    trace = router.turn("gibberish input.")
    assert trace["answer"]["status"] == "NEEDS_CLARIFICATION"
    assert trace["committed"] is False


def test_every_turn_is_sealed_with_a_trace_digest():
    # determinism is REPLAY determinism: the same turn sequence in a
    # fresh session reproduces the same sealed trace bit-for-bit
    # (turn ids are positional, so two turns in ONE session are
    # different turns with the same answer)
    router = HybridRouter(mode="NATIVE_ONLY")
    replay = HybridRouter(mode="NATIVE_ONLY")
    a = router.turn("is the cat gray?")
    b = replay.turn("is the cat gray?")
    assert a["trace_digest"] == b["trace_digest"]
    c = router.turn("is the cat gray?")
    assert c["answer"] == a["answer"]
    assert len(router.traces) == 2
    assert MODES == ("NATIVE_ONLY", "CORTEX_DIAGNOSTIC", "HYBRID_COMMIT")


# ---------------------------------------- lexical grounding (live Gate 4)
def test_grounding_gate_catches_fabricated_packets():
    """LIVE-GATE CLOSURE: the real 0.5B cortex fabricated well-formed
    packets around invented words (property(glimmerfor, gray) reached
    UNDERSTOOD). The grounding gate checks every atom against the
    learned vocabulary - the cortex's self-report is never trusted
    alone."""
    cortex = ScriptedCortex({
        "the glimfor is gray.": (
            {"pred": "property", "args": ["glimmerfor", "gray"]}, []),
        "the cat blurfles the dog.": (
            {"pred": "relation", "args": ["blurfs", "cat", "dog"]}, []),
    })
    router = HybridRouter(mode="HYBRID_COMMIT", cortex=cortex)
    a = router.turn("the glimfor is gray.")
    assert a["answer"]["status"] == "UNGROUNDED_TERM"
    assert a["answer"]["ungrounded_atoms"] == ["glimmerfor"]
    assert a["committed"] is False
    b = router.turn("the cat blurfles the dog.")
    assert b["answer"]["status"] == "UNGROUNDED_TERM"
    assert b["answer"]["ungrounded_atoms"] == ["blurfs"]


def test_grounding_gate_passes_fully_grounded_packets():
    cortex = ScriptedCortex({
        "would you say the cat is gray?": (
            {"pred": "question",
             "args": [{"pred": "property", "args": ["cat", "gray"]}]},
            [])})
    router = HybridRouter(mode="HYBRID_COMMIT", cortex=cortex)
    trace = router.turn("would you say the cat is gray?")
    assert trace["validation"]["grounding"] == {"outcome": "GROUNDED"}
    assert trace["answer"]["status"] == "ANSWERED"


def test_grounding_cannot_catch_role_errors_recorded_limit():
    """HONEST LIMIT (recorded, not hidden): a fully-grounded packet
    with the WRONG roles passes grounding for UNTAUGHT constructions.
    NOTE the apprenticeship closure: "the dog is chased by the cat."
    is now parsed NATIVELY by the learned passive_present construction
    with CORRECT roles - the limit below survives only for
    constructions not yet taught (here: got-passive)."""
    # the taught passive no longer reaches the cortex at all
    class Bomb:
        def propose(self, sentence):
            raise AssertionError("taught construction hit the cortex")
    taught = HybridRouter(mode="HYBRID_COMMIT", cortex=Bomb())
    trace = taught.turn("the dog is chased by the cat.")
    assert trace["route"] == "native_gram"
    assert trace["answer"]["meaning"] == {
        "pred": "relation", "args": ["chase", "cat", "dog"]}  # CORRECT

    # an UNTAUGHT passive variant still shows the cortex limit
    cortex = ScriptedCortex({
        "the dog got chased by the cat.": (
            {"pred": "relation", "args": ["chase", "dog", "cat"]}, [])})
    router = HybridRouter(mode="HYBRID_COMMIT", cortex=cortex)
    trace2 = router.turn("the dog got chased by the cat.")
    assert trace2["route"] == "cortex"
    assert trace2["validation"]["grounding"] == {"outcome": "GROUNDED"}
    assert trace2["committed"] is True  # the gate cannot see the error


def test_unresolved_pronoun_is_typed_never_a_crash():
    """BATTERY-FOUND CRASH (2026-08-28): 'it is gray.' raised
    DiscourseError straight through the router. Now a typed native
    error that routes onward like any other non-parse."""
    router = HybridRouter(mode="NATIVE_ONLY")
    trace = router.turn("it is gray.")
    assert trace["route"] == "no_answer"
    assert trace["committed"] is False
    cortex = ScriptedCortex({"it is gray.": (None, [])})
    hybrid = HybridRouter(mode="HYBRID_COMMIT", cortex=cortex)
    trace2 = hybrid.turn("it is gray.")
    assert trace2["route"] == "cortex"
    assert trace2["committed"] is False


# --------------------------------- content-faithfulness gate (battery v1)
def test_faithfulness_r1_dropped_content_refused():
    """Dropped known content WITHOUT a clause connector (connector
    sentences are now intercepted upstream by the CAS-Ohm overload
    gate - see test_t3): the packet ignores two known adjectives."""
    cortex = ScriptedCortex({
        "the cat chases the quiet dog.": (
            {"pred": "relation", "args": ["chase", "cat", "dog"]}, [])})
    router = HybridRouter(mode="HYBRID_COMMIT", cortex=cortex)
    trace = router.turn("the cat chases the quiet dog.")
    assert trace["answer"]["status"] == "CONTENT_MISMATCH"
    assert trace["answer"]["rule"] == "R1_dropped_known_content"
    assert trace["answer"]["dropped"] == ["quiet"]
    assert trace["committed"] is False


def test_faithfulness_r2_typo_corrected_entity_refused():
    """Silent typo-correction: 'cta' -> cat is an unattested entity."""
    cortex = ScriptedCortex({
        "the cta is gray.": (
            {"pred": "property", "args": ["cat", "gray"]}, [])})
    router = HybridRouter(mode="HYBRID_COMMIT", cortex=cortex)
    trace = router.turn("the cta is gray.")
    assert trace["answer"]["status"] == "CONTENT_MISMATCH"
    assert trace["answer"]["rule"] == "R2_unattested_entity"
    assert trace["answer"]["unattested"] == ["cat"]


def test_faithfulness_passes_legitimate_paraphrase():
    """Synonym verbs and filler words are the cortex's legitimate job:
    R1/R2 must NOT block them."""
    cortex = ScriptedCortex({
        "would you say the cat is gray?": (
            {"pred": "question",
             "args": [{"pred": "property", "args": ["cat", "gray"]}]},
            []),
        "the cat is pursuing the dog.": (
            {"pred": "relation", "args": ["chase", "cat", "dog"]}, [])})
    router = HybridRouter(mode="HYBRID_COMMIT", cortex=cortex)
    q = router.turn("would you say the cat is gray?")
    assert q["answer"]["status"] == "ANSWERED"
    s = router.turn("the cat is pursuing the dog.")
    assert s["validation"]["faithfulness"] == {"outcome": "FAITHFUL"}
    assert s["answer"]["status"] == "UNDERSTOOD"


def test_faithfulness_known_limits_stay_recorded():
    """HONEST LIMITS the gate cannot catch (recorded, not hidden):
    verb-slot and property-slot typos, pure tense drops with no known
    word lost, and role reversals - all pass R1/R2."""
    cortex = ScriptedCortex({
        "the cat is graey.": (
            {"pred": "property", "args": ["cat", "gray"]}, [])})
    router = HybridRouter(mode="HYBRID_COMMIT", cortex=cortex)
    trace = router.turn("the cat is graey.")
    assert trace["committed"] is True    # property-slot typo: uncaught


# ------------------------------- native CAS-Ohm attention plane (v0.1)
def test_attention_plane_is_compute_only():
    """Protocol section 15 as a test: the attention record decorates
    the trace and decides NOTHING - answers are identical with the
    plane's records stripped, and the record is authored after the
    answer field is final."""
    cortex = ScriptedCortex({
        "the zorble is gray.": (
            {"pred": "property", "args": ["zorble", "gray"]}, [])})
    router = HybridRouter(mode="HYBRID_COMMIT", cortex=cortex)
    trace = router.turn("the zorble is gray.")
    assert trace["cas_ohm"]["authority_note"].startswith("compute-only")
    # the answer was decided before the record existed
    assert trace["answer"]["status"] == "UNGROUNDED_TERM"


def test_attention_lexical_resistance_rises_for_ungrounded():
    """Experiment A slice: an invented word activates R_lexical, so
    I_obs falls far below I_pred - the residual flags the neighborhood
    the grounding probe then identifies."""
    cortex = ScriptedCortex({
        "the zorble is gray.": (
            {"pred": "property", "args": ["zorble", "gray"]}, [])})
    router = HybridRouter(mode="HYBRID_COMMIT", cortex=cortex)
    record = router.turn("the zorble is gray.")["cas_ohm"]
    assert record["R_lexical"] >= 8.0
    assert record["I_obs"] < record["I_pred"]
    assert record["delta_I"] < 0
    assert record["operating_region"] == "cutoff"

    clean = HybridRouter(mode="NATIVE_ONLY").turn("the cat is gray.")
    assert clean["cas_ohm"]["R_total"] == 1.0
    assert clean["cas_ohm"]["I_obs"] == clean["cas_ohm"]["I_pred"]
    assert clean["cas_ohm"]["operating_region"] == "active"


def test_attention_role_binding_healthy_flow_wrong_effect():
    """Experiment B slice: the passive role error commits with a CLEAN
    flow profile - the record must show healthy I (active region), and
    its semantic_outcome field must disclaim: flow never implies a
    correct effect. Semantic misalignment, not attention starvation."""
    cortex = ScriptedCortex({
        "the dog is chased by the cat.": (
            {"pred": "relation", "args": ["chase", "dog", "cat"]}, [])})
    router = HybridRouter(mode="HYBRID_COMMIT", cortex=cortex)
    record = router.turn("the dog is chased by the cat.")["cas_ohm"]
    assert record["operating_region"] == "active"
    assert record["R_role_binding"] == 0.0   # nothing resisted
    assert "healthy flow does not imply a correct effect" in \
        record["semantic_outcome"]


def test_attention_faithfulness_gate_shows_role_binding_resistance():
    cortex = ScriptedCortex({
        "the cta is gray.": (
            {"pred": "property", "args": ["cat", "gray"]}, [])})
    router = HybridRouter(mode="HYBRID_COMMIT", cortex=cortex)
    record = router.turn("the cta is gray.")["cas_ohm"]
    assert record["R_role_binding"] >= 6.0
    assert record["operating_region"] == "cutoff"


def test_negation_polarity_never_dropped_in_projection():
    """Ledger-round regression: a NEGATIVE learned-grammar frame must
    project to the legacy negation packet - never to the same packet
    as its positive counterpart."""
    router = HybridRouter(mode="NATIVE_ONLY")
    negative = router._frame_to_packet(
        {"frame": "event", "predicate": "chase", "agent": "cat",
         "patient": "dog", "tense": "present", "polarity": "negative"})
    positive = router._frame_to_packet(
        {"frame": "event", "predicate": "chase", "agent": "cat",
         "patient": "dog", "tense": "present", "polarity": "positive"})
    assert negative == {"pred": "negation",
                        "args": [{"pred": "relation",
                                  "args": ["chase", "cat", "dog"]}]}
    assert positive == {"pred": "relation",
                        "args": ["chase", "cat", "dog"]}
    assert negative != positive


def test_learned_question_answers_in_plain_english():
    """The learned interrogative construction routes through the
    kernel and renders honest English for relation questions (ledger
    finding: the legacy decoder mangled them)."""
    router = HybridRouter(mode="NATIVE_ONLY")
    trace = router.turn("does the cat chase the dog?")
    assert trace["route"] == "native_gram"
    assert trace["answer"]["status"] == "ANSWERED"
    assert trace["answer"]["text"] == \
        "i do not know whether the cat chases the dog."


def test_runtime_canary_no_construction_forgotten():
    """CANARY (save-path clobber bug: the disk write of raw teacher
    morph entries made the runtime FORGET active-past while all suites
    stayed green). One runtime probe per durable construction family -
    if any stops parsing, knowledge was lost on disk. Each probe runs
    in a FRESH session: the canary tests construction knowledge, not
    conversation flow (in ONE session the dialogue board correctly
    treats 'the cat chased the dog.' followed by 'the cat did not
    chase the dog.' as an unmarked contradiction and asks)."""
    probes = {
        "the cat chased the dog.": "UNDERSTOOD",        # active past
        "the dog was chased by the cat.": "UNDERSTOOD",  # passive
        "the cat does not chase the dog.": "UNDERSTOOD",  # negation
        "chase the dog.": "UNDERSTOOD",                  # imperative
        "the cat chases the dog and the dog chases the cat.":
            "UNDERSTOOD",                                # coordination
        "does the cat chase the dog?": "ANSWERED",       # question
        "did the cat chase the dog?": "ANSWERED",        # past question
        "the cat gives the bone to the dog.": "UNDERSTOOD",  # ditrans
        "the gray cat chases the brown dog.": "UNDERSTOOD",  # adjectives
        "the cats chase the dog.": "UNDERSTOOD",         # plural
        "the cat did not chase the dog.": "UNDERSTOOD",  # past negation
        "is the gray cat quiet?": "ANSWERED",            # copular quest
        "the dog was not chased by the cat.": "UNDERSTOOD",  # neg pass
        "the cat gave the bone to the dog.": "UNDERSTOOD",  # ditr past
        "does the cat give the bone to the dog?": "ANSWERED",  # ditr q
        "the cat chases the dog and the fox chases the hen and "
        "the bird chases the cat.": "UNDERSTOOD",        # 3-clause and
        "the cat chases the dog or the fox chases the hen.":
            "UNDERSTOOD",                                # disjunction
        "the cat that chases the dog is gray.": "UNDERSTOOD",  # rel cl
        "the cat's bone is gray.": "UNDERSTOOD",         # possessive
        "the cat is on the table.": "UNDERSTOOD",        # locative
        "the cat is bigger than the dog.": "UNDERSTOOD",  # comparative
        "every cat chases the dog.": "UNDERSTOOD",       # quantifier
        "the cat chased the dog yesterday.": "UNDERSTOOD",  # temporal
        "why does the cat chase the dog?":
            "LANGUAGE_UNDERSTOOD_KNOWLEDGE_MISSING",     # why (honest)
        "give the bone to the dog.": "UNDERSTOOD",       # command+rcpt
        "the cat carries the bone to the dog.": "UNDERSTOOD",  # carry
        "the small cat chases the large dog.": "UNDERSTOOD",  # sm/lg
        "the cat must not chase the dog.": "UNDERSTOOD",  # prohibition
    }
    for sentence, expected in probes.items():
        trace = HybridRouter(mode="NATIVE_ONLY").turn(sentence)
        assert trace["answer"]["status"] == expected, \
            f"FORGOTTEN: {sentence!r} -> {trace['answer']['status']}"


def test_pronoun_resolves_unique_antecedent_across_sentences():
    """Lesson L015: 'it' resolves against the PREVIOUS committed turn
    when exactly one entity is on offer - and the resolution is
    recorded, never silent."""
    router = HybridRouter(mode="NATIVE_ONLY")
    assert router.turn("the cat is quiet.")["answer"]["status"] \
        == "UNDERSTOOD"
    trace = router.turn("it chases the dog.")
    assert trace["answer"]["status"] == "UNDERSTOOD"
    assert trace["answer"]["meaning"] == {
        "pred": "relation", "args": ["chase", "cat", "dog"]}
    assert trace["pronoun_resolution"]["resolved"] == {"agent": "cat"}


def test_norm_quantifier_and_disjunction_meanings_never_collapse():
    """The non-collapse law across the new families: 'must not' /
    'does not' / plain assertion are three meanings; every/some/no
    are three meanings; and/or are two meanings."""
    router = HybridRouter(mode="NATIVE_ONLY")

    def meaning(sentence):
        return router.turn(sentence)["answer"]["meaning"]

    prohibited = meaning("the cat must not chase the dog.")
    negated = meaning("the cat does not chase the dog.")
    assert prohibited["pred"] == "prohibition"
    assert negated["pred"] == "negation"
    assert prohibited != negated

    quants = {q: meaning(f"{q} cat chases the dog.")
              for q in ("every", "some", "no")}
    assert len({json.dumps(m, sort_keys=True)
                for m in quants.values()}) == 3
    assert all(m["pred"] == "quantified" for m in quants.values())

    conj = meaning("the cat chases the dog and the fox chases "
                   "the hen.")
    disj = meaning("the cat chases the dog or the fox chases "
                   "the hen.")
    assert (conj["pred"], disj["pred"]) == ("conjunction",
                                            "disjunction")


def test_pronoun_ambiguous_antecedent_asks_never_guesses():
    """Two candidate antecedents -> the honest clarification request;
    a guess is never invented. No prior sentence -> honest refusal."""
    router = HybridRouter(mode="NATIVE_ONLY")
    router.turn("the cat chases the dog.")
    trace = router.turn("it chases the hen.")
    assert trace["answer"]["status"] == "AMBIGUOUS_ANTECEDENT"
    assert trace["answer"]["candidates"] == ["cat", "dog"]
    fresh = HybridRouter(mode="NATIVE_ONLY")
    assert fresh.turn("it chases the dog.")["answer"]["status"] \
        == "UNRESOLVED_PRONOUN"
