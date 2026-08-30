# Label Authority Spec v1

Status: Part of LABEL PHASE 0B. Documentation only; not claim-bearing.

## 1. What this document is

This is the master spec for how labels get authority in the CNCM CAS
label phase. A "label" here is a tag we attach to a word-sense telling us
which CAS cognitive class it belongs to. A "claim-bearing" label is one we
are willing to build a scientific claim on. A non-claim-bearing label is
only a suggestion or a training aid.

This document sets the rules. Other files carry the details. Cross-references
are listed in Section 12.

The short version: models help gather and criticize evidence. A deterministic
program issues the labels. The owner approves the rules and audits a small
blinded sample. No model output, on its own, ever creates a claim-bearing
label.

## 2. The replaced rule (old vs new)

We changed one rule. The intent, stated plainly:

- OLD: "No LLM assigns claim-bearing labels. A human labels each sense."
- NEW: "No LLM OUTPUT ALONE has claim-bearing label authority."

Under the NEW rule, models may retrieve sources, propose mappings, generate
paraphrases, find ambiguity, and criticize candidate labels. Models may NOT
directly write final claim-bearing labels.

A claim-bearing label is EITHER:
- (A) CONSTRUCTION_GOLD, or
- (B) RESOURCE_GOLD (deterministic).

The change is narrow. The old rule required a human to hand-label every sense.
The new rule allows AI assistance in gathering evidence, but keeps the act of
issuing a claim-bearing label in the hands of a deterministic engine that the
owner approves and audits. This is a single-owner, AI-assisted label authority.

## 3. Label authority hierarchy (6 classes)

There are six authority classes. Only three of them are claim-bearing.

| Label | How it is created | Claim-bearing? |
|---|---|---|
| CONSTRUCTION_GOLD | The CAS state/trace exists BEFORE the sentence is generated. We build the sentence from a known CAS operation, then check the parser recovers it. | Yes |
| RESOURCE_GOLD | A frozen external sense id, mapped by an owner-approved deterministic rule. | Yes (after audit) |
| MODEL_PROPOSED | One or more models suggest a label. | Never |
| WEAK_LABEL | Models plus heuristics agree, but no exact rule establishes it. | No. Training only; never used in protected evaluation. |
| ABSTAIN | Ambiguous, conflicting, unsupported, or multi-label. The item is excluded; cas_label = null. | No |
| OWNER_CORRECTED | The owner corrects a verified pipeline error, with provenance recorded. | Yes |

## 4. The enforced invariant (derived in code)

There is one hard rule, and it is computed in code, in
`label_common.make_packet`:

```
claim_bearing == (authority in {CONSTRUCTION_GOLD, RESOURCE_GOLD, OWNER_CORRECTED})
```

Key points:
- `claim_bearing` is DERIVED. It is never passed in by a caller. The engine
  computes it from the authority class. This stops anyone hand-setting a flag.
- A gold authority (CONSTRUCTION_GOLD, RESOURCE_GOLD, OWNER_CORRECTED) requires
  a non-null `cas_label`.
- ABSTAIN requires a null `cas_label`.

## 5. Model consensus grants NO authority

State it plainly: agreement among models does not create authority.

- 3 models agreeing does NOT create a gold label.
- 3 models disagreeing does NOT prove a label false.
- Agreement only changes AUDIT PRIORITY. It decides what the owner looks at
  first. It never decides what the label IS.

A model can retrieve a source, propose a mapping, write a paraphrase, flag an
ambiguity, or criticize a candidate. None of that writes a claim-bearing label.

## 6. Deterministic firing mechanism

The engine that issues RESOURCE_GOLD and ABSTAIN labels is
`deterministic_label_engine.py`, driven by the frozen rule table
`CAS_MAPPING_RULES_v1.yaml`.

Step 1 — Normalize the gloss (plus the frame if one is present):
- lowercase the text,
- apply Unicode NFKD normalization,
- replace runs of non-alphanumeric characters with a single space,
- collapse the result.

("Gloss" = the dictionary-style definition of the sense. "Frame" = a
structured sense descriptor from the source resource, when it exists.)

Step 2 — Test each rule. A rule fires for its class if and only if:
- at least one of its include terms matches on a whole-word or whole-phrase
  basis, AND
- none of its exclude terms match.

Step 3 — Decide across the 4 rules:
- exactly one rule fires -> RESOURCE_GOLD for that class,
- zero rules fire -> ABSTAIN with reason `no_rule`,
- two or more rules fire -> ABSTAIN with reason `multiple_rules`,
- a caller-flagged source disagreement -> ABSTAIN with reason `source_conflict`.

A model's proposed rule id is advisory "evidence" ONLY. The engine ALWAYS
recomputes firing from the frozen text. It never trusts the model's answer.

## 7. The 4 CAS classes and rule ids

These labels apply to a SENSE-IN-CONTEXT, never to a bare spelling of a word.
The definitions are owner-approved. Their source is the CLAUDE.md 10-Noetics
(verbatim) plus CAS_FOUNDATIONAL_CLARIFICATIONS Clarification 6, with the
master charter in `cas_reasoner.txt`.

- CAS-N2 (^2 Positive) = affinity, attraction, preference, desire, or approach
  TOWARD the object.
- CAS-N3 (^3 Negative) = aversion, repulsion, avoidance, dread, rejection, or
  withdrawal FROM the object.
  - ANTI-DRIFT: ^3 is VISCERAL, not analytical. Critique, scrutiny, and
    assessment are ^6 and are EXCLUDED from ^3.
- CAS-N6 (^6 Male) = decomposition, analysis, separation into parts,
  structural inspection, or testing.
  - ANTI-DRIFT: merely asking a question does NOT qualify. ask, question,
    inquire, query, and wonder are EXCLUDED.
- CAS-N8 (^8 Above/Cause) = one cue, event, or Idea TRIGGERS another Idea or
  response to arise.
  - ANTI-DRIFT: this is not deduction. Mere temporal sequence and ordinary
    communication do NOT qualify. deduce, infer, conclude, prove, say, tell,
    announce, and state are EXCLUDED.

## 8. Abstain discipline and no quota rescue

When an item is ambiguous or conflicting, it gets ABSTAIN and is EXCLUDED.

We NEVER broaden the include sets or the definitions to reach a round-number
sample size. The rule of thumb: "Better 120 clean senses than 240 semantic
puddles."

If the smallest class cannot supply the frozen minimum count without using
ambiguous labels, the pipeline returns `INSUFFICIENT_CLEAN_LABEL_COVERAGE`.
We do not rescue the study by loosening the rules.

## 9. Role separation

Four roles, kept separate on purpose:

- Models ASSEMBLE EVIDENCE. They locate sources, propose mappings, write
  paraphrases, find ambiguity, and criticize candidates. Their output is
  never authoritative.
- The deterministic ENGINE ISSUES LABELS. It recomputes firing from frozen
  text and derives `claim_bearing`.
- The OWNER APPROVES RULES and AUDITS A BLINDED SAMPLE. The owner approves the
  4 class definitions, approves the rule table, inspects every rule once,
  reviews high-risk items, blind-audits a random sample per class, and signs
  the final digests.
- The owner does NOT label the full inventory. The point of the AI-assisted
  design is to remove hand-labeling of every sense. The owner sets and checks
  the rules; the engine applies them.

## 10. LABEL_PACKET fields

Every labeled item is stored as a LABEL_PACKET. The schema is in
`LABEL_PACKET.schema.json`. Fields:

- `packet_id`
- `authority`
- `cas_label`
- `claim_bearing` (derived — see Section 4)
- `sense{ sense_id, lemma, pos, gloss, source, frame }`
- `construction{ construction_seed, noetic, semantic_graph, template_id }`
- `fired_rules[]`
- `blocked_rules[]`
- `abstain_reason` (one of: `no_rule` | `multiple_rules` | `source_conflict`
  | `unverifiable_source` | `ambiguous` | null)
- `evidence{ model_id, model_role, source_locator, exact_gloss, frame_or_class,
  proposed_rule_id }` (NON-authoritative)
- `surface{ sentence, realization_lane (deterministic | ai_paraphrase),
  roundtrip_ok }`
- `provenance{ frozen_resource_digest, rule_table_digest, engine_version,
  created_by, seed }`

## 11. Source verifier

The source verifier is `label_source_verifier.py`. It rejects:

- nonexistent sense ids,
- invented quotes (a gloss that is not verbatim in the frozen resource),
- a paraphrase presented as an exact quote (normalized-equal but not
  byte-equal),
- mismatched frame ids,
- conflicting mappings (the same sense id pointing to different classes),
- duplicate senses within a resource,
- ANY source consulted after protected results are opened (the freeze-time
  gate),
- a resource digest that does not equal the manifest-frozen digest.

## 12. Construction gold

The generator is `construction_gold_generator.py`. The flow:

1. The formal CAS operation is known FIRST.
2. A deterministic template plus a frozen synonym table builds a sentence.
3. A round-trip parser tries to recover the seed operation.
4. The `roundtrip_ok` gate decides the outcome.

Only round-trip-OK items become CONSTRUCTION_GOLD. A round-trip failure is
EXCLUDED, never relabeled.

The primary claim-bearing set uses deterministic realizations. AI paraphrases
are an OPTIONAL, harder transfer stratum. They must pass round-trip plus
semantic-preservation, and they are never the primary set.

CLASS_OPS: ^2 attract, ^3 averse, ^6 decompose, ^8 trigger.

## 13. Owner audit

The queue builder is `owner_audit_queue.py`. The blinded queue holds:

- up to 15 accepted items per class,
- an abstain sample,
- HIDDEN DUPLICATES (the same item under a second blinded id) to measure
  within-owner consistency.

Two files:
- `audit_queue.blinded.json` — the owner sees this. It carries NO label and an
  empty `owner_judgment`.
- `audit_queue.sealed.json` — maps `queue_id` to the true label and the
  duplicate groups. It is used only to score AFTER the owner has judged.

The report covers: automatic-label coverage; abstention rate; model
disagreement rate; source-verification failure rate; owner-audit disagreement
rate; duplicate-item consistency; and per-rule error counts.

REQUIRED DISCLAIMER: "single-owner audit; NOT independent human inter-rater
validation."

The owner's job: approve the 4 class definitions; approve the rule table;
inspect every rule once; review high-risk items; blind-audit a random sample
per class; sign the final digests.

## 14. SCMPE-v1 (control generation)

SCMPE-v1 builds the controls BEFORE any hidden-state results are opened. Steps:

1. Freeze an INDEPENDENT lexical resource (NOT the target Qwen hidden states).
2. Represent each sense by its gloss terms, source frame, thematic roles,
   lexical relations, frequency, token length, and morphology.
3. Compute the cohesion and separation of the CAS partition.
4. Generate at least 1000 balanced alternative 4-way partitions.
5. Keep only partitions whose measurable properties match the CAS partition
   within FROZEN tolerances.
6. Report where CAS falls in that distribution (a percentile).

Balanced-random control: map each sense to one class ONCE, and preserve that
mapping across every occurrence and split. No human picks the "best opponent"
after seeing results.

## 15. Claims (kept separate)

The claims are kept separate. Promotion is deterministic and gated by an
owner-signed phase approval.

- Claim A: decodability.
- Claim B: incremental value over lexical and matched-semantic controls. Only
  Claim B licenses the phrase "CAS-specific".
- Claim C: causal intervention utility.
- Claim D: learning benefit.

Tier A proves the mechanism in a controlled CAS-generated domain (NOT
unrestricted English). Tier B tests transfer using frozen source-derived
labels. Do NOT start Tier B until Tier A beats matched controls.

The target model checkpoint MUST NOT assign labels and MUST NOT generate
protected evaluation items.

## 16. Compute

- No local CPU neural workload.
- Deterministic source-verification and dataset scripts MAY run locally on CPU.
- Remote models (Bedrock or other) are for source-location, criticism,
  counterexample, and paraphrase PROPOSALS only. These are non-authoritative.
- AWS GPU is for hidden-state extraction, probing, intervention, training, and
  protected evaluation.
- Bedrock is teacher/proposal language only.

## 17. Governance

- Owner-signed phase approval.
- Deterministic claim promotion.
- No hook-based authorization.
- No model-written claim status.
- Claude is NOT the research governor.

## 18. Pilot result (development-only, not claim-bearing)

This is a development run. It proves nothing scientific. It only shows the
pipeline runs and the numbers are internally consistent.

- 46 dev senses -> 40 RESOURCE_GOLD + 6 ABSTAIN.
- coverage 0.8696, abstention 0.1304.
- source-verification failure rate 0.0.
- cross-class integrity OK.
- 0 mismatch vs author intent.
- per-rule 10/10/10/10.
- 40 construction-gold.
- 86 total packets.
- owner audit queue: 70 items + 4 rules + 4 hidden duplicates.
- tests: 19/19 pass.
- rule table sha256:
  `5599780d2c1e3ffcb0cc71289f0a475d3a712465fdafa37147b8b0ebc256eb86`
- dev resource sha256:
  `740d72da8a6f5cca347ef816b40abcb3952e4a11c09b0c6896497c3d78dc5c24`

## 19. Cross-references

- `CAS_MAPPING_RULES_v1.yaml` — the frozen rule table the engine fires from.
- `RESOURCE_GOLD_SPEC.md` — the RESOURCE_GOLD path in full.
- `CONSTRUCTION_GOLD_SPEC.md` — the CONSTRUCTION_GOLD path in full.
- `AI_LABELER_ROLE_PROMPTS.md` — the non-authoritative model roles.
- `OWNER_AUDIT_PROTOCOL.md` — the blinded owner audit procedure.
- `SCMPE_GENERATION_SPEC.md` — the control generation procedure.
- `LABEL_CLAIM_BOUNDARY.md` — what is and is not claim-bearing.
- `LABEL_PACKET.schema.json` — the LABEL_PACKET field schema.

## 20. Honest scope

This is a deterministic label backbone. It establishes NO CAS claim yet. It
sets who may issue a label and how. It does not prove that the CAS classes
carry any real signal. A model can never set a claim-bearing label. The pilot
proved nothing scientific — it only exercised the pipeline.
