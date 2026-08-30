# Construction Gold Spec (Tier A)

Part of LABEL PHASE 0B, amended by PHASE 0C (owner directive 2026-08-30). Documentation only; not claim-bearing.

> **PHASE 0C RETIREMENT NOTICE.** The generator this document originally described
> (`construction_gold_generator.py`) is RETIRED from evaluation. Owner finding: it is
> CIRCULAR — each class selects verbs from its own list, and the round-trip checker uses
> the SAME verb-to-class table to recover the class, so the check proves the lookup table
> agrees with itself. Some `^8` outputs ("The analyst triggered the device.") are generic
> physical causation, not one Idea bringing another Idea to Mind. Its output authority is
> now `CONTROLLED_TEMPLATE_FIXTURE`: pipeline/unit tests only, refused by
> `owner_gated_promotion.py` (`FIXTURE_NOT_PROMOTABLE`). **The replacement Tier A design
> is `CAS_TRACE_GOLD_SPEC_v1.md`** (formal CAS trace -> CAS-Sem graph -> realization ->
> independently implemented preservation check; output `CONSTRUCTION_CANDIDATE`,
> promotable to gold only via the owner-gated path). Sections below describe the
> label-known-first PRINCIPLE, which survives; wherever they describe the retired
> generator's mechanics as claim-bearing, the retirement notice governs.

## 1. What Tier A is (in one sentence)

Tier A is the set of examples where we already know the correct label **before** the sentence exists. We pick a formal CAS operation first. Then we build a sentence to match it. The label is not read out of the sentence by a model. The label is baked in by how the sentence was made. This is what "known by construction" means.

Because the label exists first, we do not need any model to judge it. That is the point of Tier A. But knowing the label first is not enough on its own — the sentence must also be PROVEN to still carry that label by a check that is independent of the generator (Phase 0C lesson).

## 2. Where this sits in the label authority rules

The Phase 0C authority flow is candidate-first; gold exists only via promotion:

```
CONSTRUCTION_CANDIDATE  --generator audit + signed promotion--> CONSTRUCTION_GOLD
RESOURCE_RULE_DERIVED   --owner audit + signed promotion-->     RESOURCE_GOLD
```

- **CONSTRUCTION_CANDIDATE** — the CAS-trace generator's output (label known before the
  sentence; `CAS_TRACE_GOLD_SPEC_v1.md`). Never claim-bearing on its own. This is Tier A's
  candidate stage.
- **CONSTRUCTION_GOLD** — the promoted form. Claim-bearing; creatable only by
  `owner_gated_promotion.py`.
- **CONTROLLED_TEMPLATE_FIXTURE** — the retired Phase 0B generator's output. Pipeline
  tests only; promotion refuses it.
- RESOURCE_RULE_DERIVED / RESOURCE_GOLD — the Tier B counterpart (`RESOURCE_GOLD_SPEC.md`).
- MODEL_PROPOSED — one or more models suggest a label. NEVER claim-bearing.
- WEAK_LABEL — models plus heuristics agree but no exact rule establishes it. Training only, never protected eval.
- ABSTAIN — ambiguous / conflicting / unsupported / multi-label. Excluded, `cas_label = null`.
- OWNER_CORRECTED — owner corrects a verified pipeline error. Claim-bearing, with provenance; defined but NOT yet creatable by any implemented program (fail-closed: make_packet refuses it and PROMOTION_MAP has no entry); a correction path must be added to owner_gated_promotion.py before use.

The replaced rule that governs all of this:

- OLD: "No LLM assigns claim-bearing labels. A human labels each sense."
- NEW: "No LLM OUTPUT ALONE has claim-bearing label authority."

Models may retrieve sources, propose mappings, generate paraphrases, find ambiguity, and criticize candidate labels. Models may NOT directly write final claim-bearing labels. A claim-bearing label is EITHER (A) CONSTRUCTION_GOLD or (B) RESOURCE_GOLD — and both exist only as output of the owner-gated promotion program; the deterministic pipelines emit candidates.

## 3. The enforced invariant (why gold is trusted — Phase 0C)

Claim-bearing status is DERIVED in code (`label_common.derive_claim_bearing`), never
passed in. Four conditions, all required:

```
claim_bearing == (
    authority in {CONSTRUCTION_GOLD, RESOURCE_GOLD, OWNER_CORRECTED}
    AND audit_state == OWNER_APPROVED
    AND the required approval digests are present
    AND phase_approval_valid == True
)
```

`make_packet` refuses to construct gold authorities at all — only the promotion program
creates them, after verifying the owner's signature, the audit receipt, and every digest.
Gold or candidate authority requires a non-null `cas_label`. ABSTAIN requires a null
`cas_label`. Model consensus grants NO authority: 3 models agreeing does not create a gold
label, and 3 models disagreeing does not prove a label false. Agreement only changes
AUDIT PRIORITY, nothing else.

## 4. The 4 CAS classes Tier A builds (CLASS_OPS)

Tier A generates examples for exactly these four CAS operations. Labels apply to the SENSE-IN-CONTEXT, never to the bare spelling of a word.

- **CAS-N2  ^2 Positive (attract)** — affinity / attraction / preference / desire / approach TOWARD the object.
- **CAS-N3  ^3 Negative (averse)** — aversion / repulsion / avoidance / dread / rejection / withdrawal FROM the object.
  - ANTI-DRIFT: ^3 is VISCERAL, not analytical. Critique, scrutiny, and assessment are ^6 and are EXCLUDED from ^3.
- **CAS-N6  ^6 Male (decompose)** — decomposition / analysis / separation into parts / structural inspection / testing.
  - ANTI-DRIFT: merely asking a question does NOT qualify; ask / question / inquire / query / wonder are EXCLUDED.
- **CAS-N8  ^8 Above/Cause (trigger)** — one cue / event / Idea TRIGGERS another Idea or response to arise.
  - ANTI-DRIFT: not deduction; mere temporal sequence and ordinary communication do NOT qualify; deduce / infer / conclude / prove / say / tell / announce / state are EXCLUDED.

Source of these definitions: `CLAUDE.md` 10-Noetics (verbatim) plus `CAS_FOUNDATIONAL_CLARIFICATIONS` Clarification 6; master charter `cas_reasoner.txt`.

## 5. How the RETIRED Phase 0B generator made items (`construction_gold_generator.py` — fixture only)

The order of steps is fixed and cannot be reversed:

1. Choose the formal CAS operation first. This is the `construction_seed` (one of `^2`, `^3`, `^6`, `^8`). The label is now fixed.
2. Fill a deterministic **template** using a frozen **synonym table**. A template is a fixed sentence skeleton with blanks. A synonym table is a frozen list of words allowed in each blank. Nothing here is invented at run time.
3. This produces the surface **sentence**.
4. Run the **round-trip parser** on that sentence. It reads the sentence back and tries to recover the seed operation.
5. If the parser recovers the same operation that was seeded, `roundtrip_ok = true`.

Phase 0C: because that parser shares the generator's verb table, round-trip-OK items become
CONTROLLED_TEMPLATE_FIXTURE (never gold, never promotable). The non-circular replacement
is specified in `CAS_TRACE_GOLD_SPEC_v1.md`.

## 6. The round-trip gate (and the exclusion rule)

The round-trip gate is the one check that makes construction labels honest. It asks: does an independent parser, reading only the finished sentence, get back the operation we started from?

- If yes (Phase 0C): the item is a CONTROLLED_TEMPLATE_FIXTURE — because this particular
  checker is not independent of the generator, passing it earns fixture status only.
- If no: the item is **EXCLUDED**. It is thrown out. It is **never relabeled** to some other class to save it.

A round-trip failure means the sentence did not clearly carry the operation we intended. We do not keep it under a different label. We drop it. This protects the set from quietly filling up with ambiguous sentences.

## 7. The two realization lanes

There are two ways a Tier A sentence can be written. Both must pass the round-trip gate.

**Primary lane — deterministic (`realization_lane = deterministic`).** Template plus frozen synonym table. No model writes the sentence. This is the strongest authority and it is the ONLY lane the primary claim-bearing set uses.

**Secondary lane — AI-paraphrase (`realization_lane = ai_paraphrase`). OPTIONAL.** A model rewrites a deterministic sentence into more natural or varied wording. This is a HARDER transfer stratum (a more demanding test layer). It must pass BOTH the round-trip gate AND a semantic-preservation check (proof the paraphrase kept the same meaning). It is NEVER the primary claim-bearing set. It exists only to test whether the mechanism survives more varied surface wording.

Rule: the primary claim rests on deterministic realizations. AI paraphrases are an add-on stratum, always secondary, and any paraphrase that fails round-trip or semantic-preservation is excluded like any other failure.

## 8. LABEL_PACKET fields relevant to Tier A

Defined in `LABEL_PACKET.schema.json`. A Tier A packet carries:

- `packet_id`
- `authority` — `CONSTRUCTION_CANDIDATE` for new Tier A items (per `CAS_TRACE_GOLD_SPEC_v1.md`);
  `CONTROLLED_TEMPLATE_FIXTURE` for the retired generator's items; `CONSTRUCTION_GOLD`
  only after owner-gated promotion.
- `cas_label` — the seeded class (`^2` / `^3` / `^6` / `^8`); non-null for gold.
- `claim_bearing` — DERIVED (see Section 3), never passed in.
- `sense` — `{sense_id, lemma, pos, gloss, source, frame}`.
- `construction` — `{construction_seed, noetic, semantic_graph, template_id}`. This block is what makes the label known-first.
- `fired_rules[]`, `blocked_rules[]`
- `abstain_reason` — one of `no_rule | multiple_rules | source_conflict | unverifiable_source | ambiguous | null`. Null for a valid gold item.
- `evidence` — `{sense_id, source_locator, exact_gloss, source_frame_id, proposed_cas_class, proposed_rule_id, model_id, model_revision, model_role, evidence_timestamp, resource_digest}`. NON-authoritative (Phase 0C schema). Model input lives here and never sets the label.
- `surface` — `{sentence, realization_lane (deterministic | ai_paraphrase), roundtrip_ok}`.
- `provenance` — `{frozen_resource_digest, rule_table_digest, engine_version, created_by, preservation_check, seed}` (`preservation_check = "shared_verb_lookup"` marks the retired circular generator; promotion refuses it).

## 9. The claim boundary (do not overstate)

Tier A proves the mechanism **only in a controlled, CAS-generated domain**. It does NOT establish anything about unrestricted English. The sentences are built by us, from our own templates and synonym table. A result on Tier A is a result on that controlled domain and nothing wider.

- Tier A proves the mechanism in a controlled CAS-generated domain (NOT unrestricted English).
- Tier B tests transfer using frozen source-derived labels (RESOURCE_GOLD).
- Do NOT start Tier B until Tier A beats matched controls.
- The target model checkpoint MUST NOT assign labels or generate protected evaluation items.

Claims stay separate and are promoted only by a deterministic program plus an owner-signed phase gate: (A) decodability, (B) incremental value over lexical and matched-semantic controls — only B licenses the phrase "CAS-specific" — (C) causal intervention utility, (D) learning benefit.

## 10. Abstain discipline and no quota rescue

Ambiguous items get ABSTAIN and are EXCLUDED. We NEVER broaden include sets or loosen definitions to reach a round-number sample size. "Better 120 clean senses than 240 semantic puddles." If the smallest class cannot supply the frozen minimum without ambiguous labels, the pipeline returns `INSUFFICIENT_CLEAN_LABEL_COVERAGE`. We do not rescue the study.

## 11. Governance

Owner-signed phase approval. Deterministic claim promotion. No hook-based authorization. No model-written claim status. Claude is NOT the research governor. Remote models (Bedrock or other) may propose source locations, criticism, counterexamples, and paraphrases only, and all such output is non-authoritative.

---

Reference implementation: `construction_gold_generator.py`. Related: `label_common.make_packet`, `LABEL_PACKET.schema.json`, `deterministic_label_engine.py`, `label_source_verifier.py`.
