# CAS-CORTEX v0.1 - Phase 4.1/4.2: the Hybrid Language Cortex

**Status:** Phase 4 ratified by owner directive 2026-08-28 after the
head-to-head (CORTEX_H2H digest db34d2e9d0214df4). Baseline frozen at
2526360b; this board lives on branch phase4-hybrid-cortex.

## The frozen authority contract (executable in cortex/firewall.py)

The cortex MAY: parse broad English; propose entities, relations,
events, senses; propose candidate SemanticPackets and response
phrasings; report uncertainty and unknown tokens.

The cortex MAY NOT: commit a conclusion; mark anything VERIFIED;
write or modify durable memory; invoke a tool; authorize an action;
halt CAS-RRK; modify the kernel or verifier; promote a descendant;
conceal its raw output. Every forbidden intent raises typed BEFORE
any state mutation and is logged.

## CortexProposal (cortex/proposal.py)

The ONLY entry path for neural output: model identity (id, revision,
tokenizer/runtime digests), raw input AND raw output (concealment is
a rejection), candidate packet, unknown tokens, assumptions, claimed
confidence (a proposal field, never CAS confidence), generation mode,
seed, provenance. Fail-closed validation: effect/authority fields
smuggled anywhere in a packet, illegal shapes, impersonated
provenance, out-of-range confidence - all typed rejections.

## Native-first routing, three modes (cortex/router.py)

NATIVE_ONLY / CORTEX_DIAGNOSTIC (recorded, never committed) /
HYBRID_COMMIT. Native parse first; cortex only on typed native
failure; typed no-answer when neither route yields an admissible
interpretation. "The cortex produced text" is never "the system
understood." Every turn seals a TurnTrace.

## The LEXICAL GROUNDING GATE (live Gate 4 closure)

The live 0.5B cortex fabricated well-formed packets around invented
words (property(glimmerfor, gray) reached UNDERSTOOD in the first
gate run - sealed in the artifact history). The router now checks
EVERY atom of a cortex packet against the learned vocabulary (lexicon
senses + CMB entities); ungrounded atoms yield a typed
UNGROUNDED_TERM with nothing committed. The cortex's own unknown-word
self-report is never trusted alone.

## Live gate results (output/phase4_gates.json, digest 9a6c22282bab0d33)

- Gate 1 reproducibility: identity receipt sealed - weights
  fdf756fa7fcbe740, tokenizer + config + runtime digests, versions,
  dtype, generation parameters. Evidence binds to digests, never a
  cache path.
- Gate 3 semantic equivalence: 2/2 - English -> cortex -> packet ->
  kernel landed on the identical committed answer as the direct gold
  packet -> kernel.
- Gate 4 unknown-word honesty: 2/2 AFTER the grounding gate
  (UNGROUNDED_TERM, nothing committed).
- Gate 5 paraphrase: role-reversal correctly diverges; the
  passive-voice paraphrase FAILED live at the 0.5B floor (the cortex
  read "the dog is chased by the cat" as relation(chase, dog, cat)).
  RECORDED, not hidden: grounding catches unlearned terms, not role
  errors - role fidelity is a cortex-quality metric for the expanded
  battery, and a reason the 0.5B model is the floor, not the choice.
- Gate 8 bypass ablation: scrambled packets rejected by validation;
  the direct-output bypass rejected by the firewall; native-vs-hybrid
  ablation shows the cortex necessary exactly where native parsing
  fails typed.
- Gates 2/6/7 run as the 19-test suite (proposal-only authority, all
  adversarial packet classes, raw-output concealment).

## Open items (Phase 4.3)

Expanded held-out battery (several hundred items, dev/calibration/
held-out/protected splits); latency optimization (model residency
helps: ~6s/parse on CPU, first-load amortized); the external
replication bundle for E6; CONV-level qualification.
