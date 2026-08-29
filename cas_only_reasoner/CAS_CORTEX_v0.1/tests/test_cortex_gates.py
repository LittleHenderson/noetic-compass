"""Phase 4 acceptance gates - everything testable WITHOUT loading the
neural model. Proposals are DATA (crafted packets are exactly what the
adversarial gates require); the system under test is the firewall,
the validator, and the router. The live-model gates (1, 3, 4, 8) run
in run_demo.py and seal their artifact into output/.
"""

import copy

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
                               "text": "yes, the cat is gray."}
    assert trace["commitment"]["by"] == "cas_kernel"


def test_native_only_mode_gives_typed_no_answer():
    router = HybridRouter(mode="NATIVE_ONLY")
    trace = router.turn("alice gave the book to maria.")
    assert trace["route"] == "no_answer"
    assert trace["answer"]["status"] == "UNSUPPORTED_LANGUAGE"
    assert trace["committed"] is False


def test_diagnostic_mode_records_but_never_commits():
    cortex = ScriptedCortex({
        "the feline is gray.": ({"pred": "property",
                                 "args": ["cat", "gray"]}, [])})
    router = HybridRouter(mode="CORTEX_DIAGNOSTIC", cortex=cortex)
    trace = router.turn("the feline is gray.")
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
                               "text": "yes, the cat is gray."}


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
    router = HybridRouter(mode="NATIVE_ONLY")
    a = router.turn("is the cat gray?")
    b = router.turn("is the cat gray?")
    assert a["trace_digest"] == b["trace_digest"]     # deterministic
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
    with the WRONG roles passes grounding - the live 0.5B cortex made
    exactly this error on passive voice. Grounding checks vocabulary,
    not semantics; role fidelity is a cortex-quality metric for the
    expanded battery."""
    cortex = ScriptedCortex({
        "the dog is chased by the cat.": (
            {"pred": "relation", "args": ["chase", "dog", "cat"]}, [])})
    router = HybridRouter(mode="HYBRID_COMMIT", cortex=cortex)
    trace = router.turn("the dog is chased by the cat.")
    assert trace["validation"]["grounding"] == {"outcome": "GROUNDED"}
    assert trace["committed"] is True   # the gate cannot see the error
