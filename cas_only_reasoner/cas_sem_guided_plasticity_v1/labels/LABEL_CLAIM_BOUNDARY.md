# Label Claim Boundary

Part of LABEL PHASE 0B. Documentation only; not claim-bearing.

---

## 0. Purpose of this document

This document draws one line. On one side of the line are things a label
authority is allowed to support. On the other side are things it is not.

"Label authority" means the reason a data item carries a CAS label. A "CAS
label" is one of four cognitive-state tags: `^2` Positive, `^3` Negative, `^6`
Male, `^8` Above/Cause (rule ids `CAS-N2`, `CAS-N3`, `CAS-N6`, `CAS-N8`).

"Claim-bearing" means the item is allowed to count in a protected study that
could support a scientific claim. If a label is not claim-bearing, it may still
help training, but it may never be used to argue that any claim is true.

This is a deterministic label backbone. A deterministic backbone is a fixed set
of rules that always produce the same answer from the same input. It sets up
labels. It does not, by itself, prove any CAS claim. Nothing in this document
should be read as evidence that CAS works.

---

## 1. The replaced rule (owner amendment)

The old rule said:

> "No LLM assigns claim-bearing labels. A human labels each sense."

The new rule says:

> "No LLM OUTPUT ALONE has claim-bearing label authority."

"LLM" means a large language model (an AI text model). "Sense" means one
specific meaning of a word in context, not the bare spelling.

Under the new rule, models may help. Models may retrieve sources. Models may
propose mappings. Models may generate paraphrases. Models may find ambiguity.
Models may criticize candidate labels.

Models may NOT directly write a final claim-bearing label. A claim-bearing label
is EITHER (A) `CONSTRUCTION_GOLD` or (B) `RESOURCE_GOLD`, and both of those are
set by a deterministic rule, never by a model's raw output.

---

## 2. Label authority hierarchy (6 classes) — what each may support

There are six authority classes. Each one has a strict boundary.

| Authority | Meaning | May support |
|---|---|---|
| `CONSTRUCTION_GOLD` | The CAS state/trace exists BEFORE the sentence is generated. | Claim-bearing. |
| `RESOURCE_GOLD` | A frozen external sense id, mapped by an owner-approved deterministic rule. | Claim-bearing, after audit. |
| `MODEL_PROPOSED` | One or more models suggest a label. | NEVER claim-bearing. |
| `WEAK_LABEL` | Models plus heuristics agree, but no exact rule establishes it. | TRAINING ONLY. Never protected eval. |
| `ABSTAIN` | Ambiguous, conflicting, unsupported, or multi-label. | Excluded. `cas_label = null`. |
| `OWNER_CORRECTED` | The owner corrects a verified pipeline error. | Claim-bearing, with provenance. |

"Heuristic" means a rough rule of thumb, not an exact rule. "Provenance" means a
recorded trail of where the label came from.

### The enforced invariant (in code)

In `label_common.make_packet` the code enforces this exactly:

```
claim_bearing == (authority in {CONSTRUCTION_GOLD, RESOURCE_GOLD, OWNER_CORRECTED})
```

Read this plainly:

- `claim_bearing` is DERIVED. The code computes it. No caller passes it in.
- A gold authority requires a non-null `cas_label`. An `ABSTAIN` requires a null
  `cas_label`.
- Model consensus grants NO authority. Three models agreeing does not create a
  gold label. Three models disagreeing does not prove a label false. Agreement
  only changes AUDIT PRIORITY (which items a human looks at first).

This is the heart of the boundary: a model can raise or lower how urgently a
human should check something. A model can never set the claim-bearing bit.

---

## 3. The deterministic firing mechanism

Files: `deterministic_label_engine.py` and `CAS_MAPPING_RULES_v1.yaml`.

"Firing" means a rule matches an item and assigns its class.

Steps:

1. Normalize the gloss (and the frame, if present). "Gloss" means the
   dictionary definition text of the sense. "Frame" means a fixed structural
   pattern id from the resource. Normalization: lowercase, apply Unicode NFKD,
   turn every run of non-alphanumeric characters into a single space, then
   collapse spaces.
2. A rule fires for its class only if (at least one include term matches as a
   whole word or phrase) AND (no exclude term matches).
3. Across the 4 rules:
   - Exactly one fires -> `RESOURCE_GOLD` for that class.
   - Zero fire -> `ABSTAIN` with reason `no_rule`.
   - Two or more fire -> `ABSTAIN` with reason `multiple_rules`.
   - Caller-flagged source disagreement -> `ABSTAIN` with reason `source_conflict`.

A model may propose a rule id. That proposal is advisory "evidence" only. The
engine ALWAYS recomputes firing from the frozen text. The model's guess never
substitutes for the computation.

---

## 4. The 4 CAS classes and their anti-drift limits

Labels apply to the SENSE-IN-CONTEXT, never to the bare spelling of a word.

- `CAS-N2` — `^2` Positive: affinity, attraction, preference, desire, or
  approach TOWARD the object.
- `CAS-N3` — `^3` Negative: aversion, repulsion, avoidance, dread, rejection, or
  withdrawal FROM the object.
  - ANTI-DRIFT: `^3` is VISCERAL, not analytical. Critique, scrutiny, and
    assessment are `^6`, and are EXCLUDED from `^3`.
- `CAS-N6` — `^6` Male: decomposition, analysis, separation into parts,
  structural inspection, or testing.
  - ANTI-DRIFT: merely asking a question does NOT qualify. `ask`, `question`,
    `inquire`, `query`, `wonder` are EXCLUDED.
- `CAS-N8` — `^8` Above/Cause: one cue, event, or Idea TRIGGERS another Idea or
  response to arise.
  - ANTI-DRIFT: this is not deduction. Mere temporal sequence and ordinary
    communication do NOT qualify. `deduce`, `infer`, `conclude`, `prove`, `say`,
    `tell`, `announce`, `state` are EXCLUDED.

Source of these definitions: `CLAUDE.md` 10-Noetics (verbatim) plus
`CAS_FOUNDATIONAL_CLARIFICATIONS` Clarification 6; master charter
`cas_reasoner.txt`.

---

## 5. Abstain discipline and the no-quota-rescue rule

Ambiguous or conflicting items get `ABSTAIN` and are EXCLUDED.

The `INSUFFICIENT_CLEAN_LABEL_COVERAGE` rule: if the smallest class cannot supply
the frozen minimum number of items without using ambiguous labels, the pipeline
returns `INSUFFICIENT_CLEAN_LABEL_COVERAGE`. It does NOT lower the bar to fill
the gap.

The no-quota-rescue rule: NEVER broaden the include sets or the definitions to
reach a round-number sample size. "Better 120 clean senses than 240 semantic
puddles." A study that cannot be filled cleanly is reported as unfillable. It is
not rescued.

---

## 6. Claims A / B / C / D — kept separate

Four claims are tracked separately. They are promoted only by a deterministic
program reading a frozen threshold, under an owner-signed phase gate.

- Claim A — decodability: can a CAS label be read out at all?
- Claim B — incremental value over lexical and matched-semantic controls.
- Claim C — causal intervention utility.
- Claim D — learning benefit.

Only Claim B licenses the word "CAS-specific".

Why: Claim A can pass just because ordinary word features (a "lexical" control,
meaning surface word-form features) already carry the signal. A "matched-semantic
control" is an alternative grouping built to be as strong as the CAS grouping on
plain meaning features. If CAS only beats nothing, it has shown nothing special.
Only when CAS beats BOTH the lexical control AND the matched-semantic control may
anyone say the result is "CAS-specific". A, C, and D never earn that phrase on
their own.

---

## 7. Tier A before Tier B — the ordering rule

- Tier A: prove the mechanism works in a controlled CAS-generated domain. This is
  a built, restricted world, NOT unrestricted English.
- Tier B: test transfer to source-derived natural language, using frozen
  source-derived labels.

Ordering rule: do NOT start Tier B until Tier A beats matched controls. If the
mechanism cannot beat matched controls inside its own controlled domain, there is
nothing to transfer, and Tier B does not begin.

---

## 8. Where CONSTRUCTION_GOLD and RESOURCE_GOLD come from

CONSTRUCTION_GOLD (`construction_gold_generator.py`): the formal CAS operation is
known FIRST. Then a deterministic template plus a frozen synonym table make a
sentence. Then a round-trip parser must recover the seed operation. Only
round-trip-OK items become `CONSTRUCTION_GOLD`. A round-trip failure is EXCLUDED,
never relabeled. The primary claim-bearing set uses deterministic realizations.
AI paraphrases are an OPTIONAL, harder transfer stratum; they must pass round-trip
plus semantic-preservation, and are never the primary set. `CLASS_OPS`: `^2`
attract, `^3` averse, `^6` decompose, `^8` trigger.

RESOURCE_GOLD comes from the deterministic firing mechanism in Section 3, applied
to a frozen external resource, and is claim-bearing only after audit.

The target model checkpoint MUST NOT assign labels and MUST NOT generate
protected evaluation items.

---

## 9. Source verifier — what it rejects

`label_source_verifier.py` rejects:

- Nonexistent sense ids.
- Invented quotes (a gloss that is not verbatim in the frozen resource).
- Paraphrase presented as an exact quote (normalized-equal but not byte-equal).
- Mismatched frame ids.
- Conflicting mappings (the same sense id mapped to different classes).
- Duplicate senses in a resource.
- ANY source consulted after protected results are opened (the freeze-time gate).
- A resource digest that does not equal the manifest-frozen digest.

A "digest" here is a sha256 checksum, a fixed fingerprint of a file's exact bytes.

---

## 10. LABEL_PACKET fields

Schema: `LABEL_PACKET.schema.json`. Fields:

- `packet_id`, `authority`, `cas_label`, `claim_bearing` (derived).
- `sense{ sense_id, lemma, pos, gloss, source, frame }`.
- `construction{ construction_seed, noetic, semantic_graph, template_id }`.
- `fired_rules[]`, `blocked_rules[]`.
- `abstain_reason` (one of `no_rule`, `multiple_rules`, `source_conflict`,
  `unverifiable_source`, `ambiguous`, `null`).
- `evidence{ model_id, model_role, source_locator, exact_gloss, frame_or_class,
  proposed_rule_id }` — NON-authoritative.
- `surface{ sentence, realization_lane (deterministic | ai_paraphrase),
  roundtrip_ok }`.
- `provenance{ frozen_resource_digest, rule_table_digest, engine_version,
  created_by, seed }`.

The `evidence` block records what a model said. It carries no authority. It only
sets audit priority.

---

## 11. Owner audit

`owner_audit_queue.py` builds a blinded queue: up to 15 accepted items per class,
plus an abstain sample, plus HIDDEN DUPLICATES (the same item under a second
blinded id) to measure the owner's own consistency.

Two files:

- `audit_queue.blinded.json` — the owner sees this. No label. Empty
  `owner_judgment`.
- `audit_queue.sealed.json` — maps `queue_id` to the true label and the duplicate
  groups. Used only to score AFTER the owner judges.

Report contents: automatic-label coverage; abstention rate; model disagreement
rate; source-verification failure rate; owner-audit disagreement rate;
duplicate-item consistency; per-rule error counts.

DISCLAIMER REQUIRED on every such report:

> "single-owner audit; NOT independent human inter-rater validation."

Owner job: approve the 4 class definitions; approve the rule table; inspect every
rule once; review high-risk items; blind-audit a random sample per class; sign the
final digests.

---

## 12. SCMPE-v1 — the matched-semantic control

`SCMPE-v1` builds control groupings BEFORE any hidden-state results are opened.
Steps:

1. Freeze an INDEPENDENT lexical resource (NOT the target Qwen hidden states).
2. Represent each sense by gloss terms, source frame, thematic roles, lexical
   relations, frequency, token length, and morphology.
3. Compute cohesion and separation of the CAS partition. ("Cohesion" = how alike
   items in a group are; "separation" = how different the groups are.)
4. Generate at least 1000 balanced alternative 4-way partitions.
5. Keep only partitions whose measurable properties match the CAS partition
   within FROZEN tolerances.
6. Report where CAS falls in that distribution (its percentile).

Balanced-random control: map each sense to one class ONCE, and preserve that
mapping across every occurrence and every split. No human picks the "best
opponent" after seeing results.

---

## 13. Compute boundary

- No local CPU neural workload.
- Deterministic source-verification and dataset scripts MAY run locally on CPU.
- Remote models (Bedrock or other) are for source-location, criticism,
  counterexample, and paraphrase PROPOSALS only. These are non-authoritative.
- AWS GPU is for hidden-state extraction, probing, intervention, training, and
  protected eval.
- Bedrock is teacher and proposal language only.

---

## 14. Governance — unchanged

- Owner-signed phase approval.
- Deterministic claim promotion (a program reads the raw result and a frozen
  threshold and emits the status).
- No hook-based authorization.
- No model-written claim status.
- Claude is NOT the research governor.

The owner-signed phase gate and the deterministic claim-promotion program are
unchanged by this document.

---

## 15. Pilot result — development only, establishes nothing claim-bearing

The pilot was a development-only run. It is NOT claim-bearing. It proves nothing
scientific about CAS. It only checks that the plumbing works.

Numbers:

- 46 dev senses -> 40 `RESOURCE_GOLD` + 6 `ABSTAIN`.
- Coverage 0.8696. Abstention 0.1304.
- Source-verification failure rate 0.0.
- Cross-class integrity OK. 0 mismatch vs author intent.
- Per-rule counts 10 / 10 / 10 / 10.
- 40 construction-gold. 86 total packets.
- Owner audit queue: 70 items + 4 rules + 4 hidden duplicates.
- Tests: 19/19 pass.
- Rule table sha256:
  `5599780d2c1e3ffcb0cc71289f0a475d3a712465fdafa37147b8b0ebc256eb86`.
- Dev resource sha256:
  `740d72da8a6f5cca347ef816b40abcb3952e4a11c09b0c6896497c3d78dc5c24`.

---

## 16. Status of the claim-bearing study

The claim-bearing readout study is NOT begun. It awaits owner approval and a
signed phase-0 record. Until that record exists, there is no claim-bearing run,
no protected eval, and no CAS claim of any kind supported by this work.
