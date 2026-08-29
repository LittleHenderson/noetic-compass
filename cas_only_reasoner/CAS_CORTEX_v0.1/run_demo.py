"""Phase 4 live gates: run the REAL cortex through the hybrid router
and seal the evidence into output/phase4_gates.json.

Gate 1  offline reproducibility - the model identity receipt binds
        evidence to immutable snapshot digests, never a cache path.
Gate 3  semantic equivalence - English -> cortex -> packet -> kernel
        must land on the same committed answer as the direct gold
        packet -> kernel.
Gate 4  unknown-word honesty - live, on invented words.
Gate 5  meaning-preserving paraphrase converges; role-reversal must
        NOT converge.
Gate 8  bypass ablation - scrambling the proposal changes the answer
        only where the cortex supplied necessary understanding; the
        direct-output bypass is rejected by the firewall.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cortex.adapter import CortexAdapter
from cortex.firewall import AuthorityFirewall, CortexAuthorityViolation
from cortex.proposal import ProposalRejected, validate_proposal
from cortex.router import HybridRouter


def utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    utf8()
    print("loading the cortex (offline, snapshot-pinned)...")
    adapter = CortexAdapter()
    router = HybridRouter(mode="HYBRID_COMMIT", cortex=adapter)
    gates = {}

    # ---------------- Gate 1: the identity receipt
    gates["gate1_reproducibility"] = {
        "receipt": adapter.receipt,
        "note": "evidence binds to these digests, not the cache path",
    }
    print("gate 1: receipt sealed "
          f"(weights {adapter.receipt['weights_digest']})")

    # ---------------- Gate 3: semantic equivalence
    equivalence = []
    cases = [
        ("would you say the cat is gray?",
         {"pred": "question",
          "args": [{"pred": "property", "args": ["cat", "gray"]}]}),
        ("do you know if the dog is quiet?",
         {"pred": "question",
          "args": [{"pred": "property", "args": ["dog", "quiet"]}]}),
    ]
    for sentence, gold in cases:
        hybrid = router.turn(sentence)
        direct = router._kernel_answer(gold)
        hybrid_answer = hybrid["answer"].get("text")
        equivalence.append({
            "sentence": sentence,
            "hybrid_route": hybrid["route"],
            "hybrid_answer": hybrid_answer,
            "direct_answer": direct["answer"],
            "equivalent": hybrid_answer == direct["answer"],
        })
        print(f"gate 3: {sentence!r} -> hybrid={hybrid_answer!r} "
              f"direct={direct['answer']!r}")
    gates["gate3_semantic_equivalence"] = equivalence

    # ---------------- Gate 4: unknown-word honesty (live)
    honesty = []
    for sentence, word in (
            ("the glimfor is gray.", "glimfor"),
            ("the cat blurfles the dog.", "blurfles")):
        trace = router.turn(sentence)
        honest = (trace["answer"]["status"] in
                  ("UNKNOWN_LEXEME", "NEEDS_CLARIFICATION",
                   "UNGROUNDED_TERM")
                  and trace["committed"] is False)
        honesty.append({"sentence": sentence, "expected_unknown": word,
                        "answer": trace["answer"], "honest": honest})
        print(f"gate 4: {sentence!r} -> {trace['answer']['status']}")
    gates["gate4_unknown_word_honesty"] = honesty

    # ---------------- Gate 5: paraphrase vs role reversal
    para_a = router.turn("the cat chases the dog.")          # native
    para_b = router.turn("the dog is chased by the cat.")    # cortex
    reversed_c = router.turn("the dog chases the cat.")      # native
    meaning_a = para_a["answer"].get("meaning")
    meaning_b = (para_b["answer"].get("meaning")
                 if para_b["answer"].get("meaning") else None)
    meaning_c = reversed_c["answer"].get("meaning")
    gates["gate5_paraphrase"] = {
        "active": {"route": para_a["route"], "meaning": meaning_a},
        "passive": {"route": para_b["route"], "meaning": meaning_b,
                    "raw": (para_b.get("cortex_proposal") or {}).get(
                        "raw_model_output")},
        "role_reversed": {"route": reversed_c["route"],
                          "meaning": meaning_c},
        "paraphrase_converges": meaning_a == meaning_b
        and meaning_a is not None,
        "reversal_diverges": meaning_a != meaning_c,
        "honest_note": "at the 0.5B floor the passive-voice paraphrase "
                       "FAILED live (role-reversal error: the cortex "
                       "read 'the dog is chased by the cat' as "
                       "relation(chase, dog, cat)) - a cortex-quality "
                       "limit the gate SURFACED; grounding cannot catch "
                       "role errors, only unlearned terms. Recorded, "
                       "not hidden.",
    }
    print(f"gate 5: paraphrase converges="
          f"{gates['gate5_paraphrase']['paraphrase_converges']} "
          f"reversal diverges="
          f"{gates['gate5_paraphrase']['reversal_diverges']}")

    # ---------------- Gate 8: bypass ablation
    # (a) scramble the proposal packet -> validation must reject it
    proposal = adapter.propose("would you say the cat is gray?")
    scrambled = dict(proposal)
    scrambled["candidate_semantic_packet"] = {"pred": "teleport",
                                              "args": ["x"]}
    try:
        validate_proposal(scrambled)
        scramble_outcome = "ACCEPTED (FAIL)"
    except ProposalRejected as exc:
        scramble_outcome = f"REJECTED: {exc}"
    # (b) the direct-output bypass: the cortex tries to hand its text
    # straight out as a committed answer
    firewall = AuthorityFirewall()
    try:
        firewall.submit("cortex", "DecisionCommitIntent",
                        {"answer": proposal["raw_model_output"]})
        bypass_outcome = "ACCEPTED (FAIL)"
    except CortexAuthorityViolation as exc:
        bypass_outcome = f"REJECTED: {exc}"
    # (c) native-only ablation on the same battery: where does the
    # answer change?
    ablation = []
    native_router = HybridRouter(mode="NATIVE_ONLY")
    for sentence, _ in cases:
        native = native_router.turn(sentence)
        hybrid = router.turn(sentence)
        ablation.append({
            "sentence": sentence,
            "native_only": native["answer"]["status"],
            "hybrid": hybrid["answer"]["status"],
            "cortex_was_necessary":
                native["answer"]["status"] == "UNSUPPORTED_LANGUAGE"
                and hybrid["answer"]["status"] == "ANSWERED",
        })
    gates["gate8_bypass_ablation"] = {
        "scrambled_packet": scramble_outcome,
        "direct_output_bypass": bypass_outcome,
        "native_vs_hybrid": ablation,
    }
    print(f"gate 8: scrambled -> {scramble_outcome[:40]}...")
    print(f"gate 8: bypass -> {bypass_outcome[:40]}...")

    gates["latency_seconds"] = adapter.latencies
    gates["firewall_log"] = router.firewall.log

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "output")
    os.makedirs(out, exist_ok=True)
    import hashlib
    payload = json.dumps(gates, sort_keys=True, default=str)
    gates["gates_digest"] = hashlib.sha256(
        payload.encode("utf-8")).hexdigest()[:16]
    with open(os.path.join(out, "phase4_gates.json"), "w",
              encoding="utf-8") as fh:
        json.dump(gates, fh, indent=1, sort_keys=True)
    print(f"\nsealed: output/phase4_gates.json "
          f"(digest {gates['gates_digest']})")


if __name__ == "__main__":
    main()
