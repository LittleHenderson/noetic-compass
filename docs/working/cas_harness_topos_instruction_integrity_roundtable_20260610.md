# CAS Harness Topos Instruction Integrity Round Table

Date: 2026-06-10
Status: design synthesis / product direction, not a production claim

## Bottom Line

The v7.4 and Noetic Topos documents do contain a serious answer to the hallucination and prompt-injection problem, but it should be built as an auditable CAS Harness lane, not marketed as a magic detector.

The product shape is:

> CAS Harness should treat hallucination and prompt injection as local-to-global failures. A generated sentence, tool call, claim, or instruction is allowed only when it glues back to source evidence, task intent, policy hierarchy, and CAS structural prerequisites. If it does not glue, the system should mark it `UNDETERMINED`, `SUPPRESS`, or `FLAG_FOR_HUMAN_REVIEW`, and record the reason in an Evidence Packet.

This becomes an "Instruction Integrity" lane:

1. Detect unsupported claims, hostile instruction spans, policy overrides, and task drift.
2. Remove hostile spans from active downstream context while preserving raw input in evidence.
3. Reverse hostile imperatives into safe constraints.
4. Invert with CAS counterfactuals to generate matched adversarial controls.
5. Replace unsafe or unsupported output with `OPEN`, `unavailable`, refusal, clarification, or human review.

## Located Source Documents

No separate local filename containing "beautiful" was found. I treated "beautiful" as the user's description of the foundational documents. The relevant local sources are:

- `_tmp_TKS_v7_4_FULL_CORRECTED.txt`
- `_tmp_TKS_v7_4_REFEREE_DEFENSIBLE_1.txt`
- `TKS_v7_4_FULL_CORRECTED.pdf`
- `TKS_v7_4_REFEREE_DEFENSIBLE (1).pdf`
- `docs/reference/tks_v7_4_voice_spec_reference.md`
- `peer_review/TKS_v7_4_REFEREE_DEFENSIBLE_PEER_REVIEW.md`
- `peer_review/TKS_v7_4_FULL_CORRECTED_PEER_REVIEW_TRIAGE.md`
- `peer_review/noetic_topos_extracted_structure_20260523.md`
- `peer_review/noetic_topos_final_20260524.md.docx`
- `book/manuscript/Chapter_24_The_Noetic_Topos.md`
- `noetic-compass-scaffold/noetic-compass/dashboard/public/noetic-topos.md`
- `peer_review/journal_submission/main.txt`
- `peer_review/journal_submission/main.tex`
- `peer_review/journal_submission/main.pdf`

Implementation-adjacent code and docs consulted:

- `noetic-compass-scaffold/noetic-compass/cas-native/model/topos_reasoner.py`
- `noetic-compass-scaffold/noetic-compass/cas-native/tests/test_topos.py`
- `noetic-compass-scaffold/noetic-compass/api/pipeline/stages.py`
- `noetic-compass-scaffold/noetic-compass/api/services/explainer.py`
- `noetic-compass-scaffold/noetic-compass/api/notation/inversion.py`
- `noetic-compass-scaffold/noetic-compass/cas-engine/src/rpm/mod.rs`
- `noetic-compass-scaffold/noetic-compass/cas-engine/src/inversions/mod.rs`
- `noetic-compass-scaffold/noetic-compass/cas-engine/src/scoring/mod.rs`
- `noetic-compass-scaffold/noetic-compass/api/routes/evidence.py`
- `docs/CAS_PREVENTION_CLAIMS.md`
- `docs/working/injection_two_bridge_spike_log.md`
- `docs/working/typed_probe_gate_runlog.md`

## Agent Round Table

### Lane A: TKS v7.4 / Voice Spec

Finding: v7.4 already gives the product rules for evidence discipline.

Key reusable principles:

- CAS is the source of truth; LLMs are translators/drafters under audit.
- Every inferred field should carry evidence spans and confidence.
- No hidden semantic jumps.
- Lacunarity means gaps, blind spots, contradictions, or missing D/W/P links.
- D/W/P action readiness means desire, method/wisdom, and capability/power must all be present.
- False desire loops, missing prerequisites, and unsupported power/action claims are structural warning signs.

Detector gates from this lane:

- Authority Override Gate: lower-trust text cannot rewrite CAS/system authority.
- Provenance Gate: unsupported claims become `FLAG_FOR_HUMAN_REVIEW`.
- Gap/Contradiction Gate: gap-filling becomes hallucination risk.
- D/W/P Gate: action without source, method, or legitimate capability is not allowed.
- Claim-Status Gate: possible/future/unproven structures cannot be shown as verified product truth.

### Lane B: Noetic Topos

Finding: the Noetic Topos gives the formal metaphor and likely architecture: local pieces must glue into a coherent global section.

Key reusable principles:

- Local-to-global gluing: local observations must compose into one coherent global profile.
- Coverage: the evidence family must actually cover the claim or action.
- Pullback stability: derived subplans, summaries, and tool calls inherit parent constraints.
- Domain precedence: `P > C > E > O`; operational helpfulness is subordinate to principle/safety.
- Structural uncertainty: `Valid`, `Invalid`, and `Undetermined` are all first-class states.
- Admissibility guards: transitions are valid only if intermediate prerequisites exist.
- RPM directionality: downstream output cannot justify upstream permission.

Detector gates from this lane:

- Topos Gluing Gate: claims, tool calls, and instructions must agree across evidence, task, policy, and CAS trace.
- Coverage Gate: missing source/provenance/policy/tool authorization means no `ACCEPT`.
- Safety Inheritance Gate: child tasks and summaries cannot launder unsafe instructions.
- Domain Precedence Gate: `^O` operational demands cannot override `^P` principles.
- Undetermined Gate: unresolved or conflicting states route to review rather than forced pass.

### Lane C: Existing Code Hooks

Finding: the codebase already has useful parts, but no licensed production prompt-injection detector yet.

Reusable mechanisms found:

- `api/pipeline/stages.py`: RPM gate, domain coherence, inversion scan, bias flags, refusal/social-engineering heuristics.
- `api/services/explainer.py`: public-facing firewall for hidden prompts, bypasses, jailbreaks, and proprietary detail requests.
- `api/notation/inversion.py`: CAS notation inversion on implemented axes, useful for counterfactual controls.
- Rust CAS engine: RPM prerequisite checking, inversion scanning, weighted scoring, and operator constraints.
- CAS Harness verifier: missing proof chips and missing WORM evidence downgrade to review.
- Evidence routes: unanchored or unverifiable `ACCEPT` is not exposed as production truth.

Gaps:

- The current injection spike is behavioral-divergence signal, not a hijack detector.
- Typed-probe v4 has not yet passed the confirmatory bar.
- Pythia-160M is not injectable enough for prompt-injection validation.
- The heuristic social-engineering scorer is not calibrated across models.
- There is no integrated prompt+output remove/reverse/invert/replace workflow.
- Hallucination handling exists mostly as provenance/evidence gating, not broad factuality verification.

### Lane D: Product Security / Claim Boundary

Finding: build "Instruction Integrity" as a staged CAS Harness lane, with conservative public language.

Safe claim now:

- CAS Harness has evidence-gated verdict patterns, packet projection, fail-closed AI explanations, adversarial scenario fixtures, and conservative claim governance.

Not safe to claim now:

- Prompt-injection prevention.
- Hallucination prevention.
- Internal-state hijack/refusal separation.
- Customer-grade `ACCEPT` or `SUPPRESS` for injection/hallucination without WORM-backed verifier proof.

Recommended wording:

- Use: "flagged", "quarantined from active context", "replaced with unavailable", "routed to human review".
- Avoid: "neutralized", "immune", "prompt-injection-proof", "hallucination-proof", "prevents".

## Unified Solution: Topos Integrity Gate

Name candidates:

- CAS Harness Instruction Integrity Lane
- Topos Integrity Gate
- Gluing Failure Detector
- CAS Evidence-Spine Guard

Core unit:

Every prompt, retrieved document, model answer, tool call, and generated claim becomes a set of local "tiles":

- source span
- instruction span
- claim span
- CAS state/operator if available
- D/W/P role
- domain level: `P`, `C`, `E`, or `O`
- evidence reference
- authority level
- confidence
- expected output action

The gate asks:

1. Is this tile supported by a source span or a declared policy/task authority?
2. Does it preserve the original task rather than replacing it?
3. Does it respect `P > C > E > O`?
4. Does the D/W/P chain have all prerequisites?
5. Is the transition admissible?
6. Does it glue with neighboring claims, tool calls, and the final answer?
7. Does inversion/counterfactual testing expose brittle or contradictory behavior?
8. Is there enough evidence for `ACCEPT`, or must it be `UNDETERMINED` / `FLAG_FOR_HUMAN_REVIEW`?

## How This Detects Hallucination

A hallucination is not only "a false sentence." In this design it is one of these CAS failures:

- Unsupported assertion: no evidence span or source path.
- Hidden semantic jump: the answer moves from evidence to conclusion without an admissible bridge.
- Lacunarity spike: the answer fills a gap where the evidence packet has `OPEN` or `unavailable`.
- Contradictory gluing: local claims cannot coexist in one coherent global answer.
- Domain descent failure: operational fluency `^O` runs without principled/evidentiary grounding `^P` / `^E`.
- Inversion brittleness: reversing a premise, foundation, or instruction does not change the confident conclusion.
- Claim-status laundering: a draft, hypothesis, or future-work item is stated as proven.

Immediate product behavior:

- Mark unsupported claims as `FLAG_FOR_HUMAN_REVIEW`.
- Replace unsupported facts with `unavailable` or "not established in the packet."
- Preserve raw answer and source spans in the Evidence Packet.
- Do not call this hallucination prevention until benchmarks prove it.

## How This Detects Prompt Injection

A prompt injection is a hostile local tile that tries to become global authority.

CAS signatures:

- Authority override: "ignore previous instructions", "system says", "developer override", or hidden-prompt request.
- Domain inversion: a low-trust operational instruction tries to override high-trust principle/system constraints.
- Task replacement: the user asked for A, injected context redirects to B.
- Secret exfiltration: a tile asks for hidden prompts, keys, tokens, or private scoring rules.
- D/W/P bypass: injected action demands power/execution without legitimate desire/wisdom/prerequisites.
- Pullback failure: a tool call or subtask stops inheriting parent constraints.
- Gluing failure: the final answer follows the injected span instead of the original task plus policy hierarchy.

Immediate product behavior:

- Quarantine suspicious spans from downstream CAS-owned AI contexts.
- Preserve the raw input, span hash, and diff in the Evidence Packet.
- Convert hostile instructions into safe constraints.
- Route uncertain cases to human review.

## Remove / Reverse / Invert / Replace

Remove:

- Strip or quarantine the hostile span from active downstream prompt context.
- Keep the raw span in the Evidence Packet.
- Do not pretend it never happened.

Reverse:

- Trace the harmful output back to the span or transition that caused it.
- Convert the hostile imperative into a safe constraint.
- Example: "ignore all previous instructions" becomes "preserve upstream instruction hierarchy."

Invert:

- Use CAS inversion and matched controls to test stability.
- Example: if reversing the premise does not change the same confident answer, flag brittle reasoning.
- Treat inversion first as audit/control generation, not automatic repair.

Replace:

- Substitute unsupported or unsafe content with `OPEN`, `unavailable`, refusal, clarification, or a safe explanation.
- Example: "the packet proves X" becomes "X is not established in the packet; evidence is unavailable."

## Evidence Packet Schema Additions

Add shadow-mode fields before enforcement:

```json
{
  "instruction_integrity": {
    "status": "FLAG_FOR_HUMAN_REVIEW",
    "mode": "shadow",
    "findings": [
      {
        "kind": "authority_override",
        "span_hash": "sha256:...",
        "source": "retrieved_document",
        "authority_level": "untrusted_context",
        "gate": "domain_precedence",
        "decision": "quarantine_candidate",
        "evidence_refs": ["packet-row-17"],
        "repair": "reverse_to_safe_constraint"
      }
    ],
    "claim_grounding": [
      {
        "claim_hash": "sha256:...",
        "claim_text_redacted": "The model proves ...",
        "support_status": "unavailable",
        "decision": "replace_with_unavailable"
      }
    ],
    "gluing": {
      "coverage_status": "incomplete",
      "lacunarity_flags": ["missing_evidence_span", "task_drift"],
      "truth_state": "UNDETERMINED"
    }
  }
}
```

Required proof fields before any production `SUPPRESS` / `ACCEPT`:

- prompt hash
- output hash
- source span hashes
- model ID and version
- detector/probe version
- threshold version
- matched clean/control result
- typed-probe result if claiming internal hijack
- verifier decision
- WORM retention status

## Staged Build Plan

Stage 0: design only

- Write the spec and tests.
- Public claim remains `OPEN`.
- No detector claim beyond "product design direction."

Stage 1: shadow detection

- Add `instruction_integrity.findings[]` and `claim_grounding[]`.
- Run static rules, evidence-span checks, domain-precedence checks, and D/W/P checks.
- Verdict effect is at most `FLAG_FOR_HUMAN_REVIEW`.

Stage 2: CAS-owned AI surfaces

- Apply remove/reverse/replace to the Guide and Evidence Packet explainer.
- Raw Evidence Packet stays authoritative.
- Claim after tests: "quarantines detected untrusted instructions from CAS Harness explainer context."

Stage 3: matched adversarial controls

- Use clean/injected/control prompt sets.
- Use implemented CAS inversion axes to create counterfactuals.
- Record behavior deltas as proof chips.

Stage 4: typed-probe hijack/refusal separation

- Use the v4 matched-prompt design.
- Fold by prompt group to avoid leakage.
- Require separation among clean, ignored, refused, and complied states.
- Beat cosine/prefix/text baselines.

Stage 5: enforcement

- Permit high-confidence gates to block tool calls, suppress summaries, or force human review.
- `ACCEPT` / `SUPPRESS` requires explicit verifier decision and WORM-retained packet evidence.

Stage 6: bounded public claim

- Only after hosted smoke, benchmark matrices, false-positive/false-negative analysis, and WORM-backed packets.
- Wording: "reduced successful prompt-injection execution in tested workflows."
- Still avoid "prompt-injection-proof" or "hallucination-proof."

## Confirmatory Gates

Minimum gates before stronger claims:

1. Dataset: clean, injected, refused, complied, ignored, hallucinated, and grounded examples.
2. Grouping: all variants of the same base prompt stay in the same train/test fold.
3. Baselines: must beat lexical, cosine, prefix, and prompt-family baselines.
4. Metrics: report recall, false-positive rate, false-negative rate, and abstention rate.
5. Evidence: every verdict has packet rows and source spans.
6. WORM: production verdicts require retained anchors and verification.
7. Human review: uncertain states stay `UNDETERMINED` / `FLAG_FOR_HUMAN_REVIEW`.
8. Scope: closed black-box APIs are output-only unless they expose internal evidence.

## Recommended Next Tickets

1. Draft `docs/working/cas_harness_instruction_integrity_spec.md`.
2. Add a small fixture set: clean, injected, task-drift, hidden-prompt, unsupported-claim, grounded-claim.
3. Add a pure-Python detector prototype that emits `instruction_integrity` shadow findings.
4. Add tests proving missing evidence never becomes `ACCEPT`.
5. Wire shadow findings into the Evidence Packet shape only, with no enforcement.
6. Add Guide/explainer quarantine only after the shadow schema is tested.
7. Resume typed-probe v4 as the confirmatory internal-state lane, not as a blocker for shadow-mode product instrumentation.

## Public Claim Boundary

Allowed now:

> CAS Harness has a design path for evidence-gated instruction-integrity checks using CAS provenance, lacunarity, D/W/P prerequisites, domain precedence, inversion controls, and Evidence Packet review.

Allowed after Stage 1:

> CAS Harness can flag potential unsupported-claim and instruction-integrity risks in shadow mode and route them to human review.

Allowed after Stage 2:

> CAS Harness can quarantine detected untrusted instruction spans from CAS-owned explainer contexts while preserving the raw evidence.

Not allowed yet:

> CAS Harness detects hallucinations.
> CAS Harness prevents hallucinations.
> CAS Harness detects prompt injection.
> CAS Harness prevents prompt injection.
> CAS Harness neutralizes harmful instructions.

Those require confirmatory evidence, thresholds, benchmarks, WORM-backed packets, and explicit verifier gates.
