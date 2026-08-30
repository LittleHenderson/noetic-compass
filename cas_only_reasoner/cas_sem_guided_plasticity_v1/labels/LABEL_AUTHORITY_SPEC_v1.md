# Label Authority Spec v1

Status: Part of LABEL PHASE 0B, **amended by PHASE 0C (owner directive 2026-08-30)**.
Documentation only; not claim-bearing.

> PHASE 0C REPAIR: the Phase 0B version of this spec said "claim-bearing after audit" but
> the code made the engine's output claim-bearing IMMEDIATELY. That confusion of
> deterministic derivation with audited authority is fixed. The engine now emits
> CANDIDATE labels only; gold exists only through the owner-gated promotion program.

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
- (B) RESOURCE_GOLD

— and (Phase 0C) BOTH exist only as the output of the owner-gated promotion program.
A deterministic pipeline produces the CANDIDATE (CONSTRUCTION_CANDIDATE or
RESOURCE_RULE_DERIVED); the owner's audit and signed approval produce the gold.

The change is narrow. The old rule required a human to hand-label every sense. The new
rule allows AI assistance in gathering evidence, keeps candidate issuance deterministic,
and keeps claim-bearing authority behind the owner's audit and signature. This is a
single-owner, AI-assisted label authority.

## 3. Label authority hierarchy (Phase 0C: candidates before gold)

The authority flow is now two-stage. Deterministic pipelines emit CANDIDATES. Gold exists
only as the output of the promotion program.

```
RESOURCE_RULE_DERIVED   --owner audit + signed promotion-->   RESOURCE_GOLD
CONSTRUCTION_CANDIDATE  --generator audit + signed promotion--> CONSTRUCTION_GOLD
```

| Label | How it is created | Claim-bearing? |
|---|---|---|
| CONSTRUCTION_GOLD | Only via owner-gated promotion of a CONSTRUCTION_CANDIDATE (generator audit + owner-signed approval + matching digests). | Yes, as promoted |
| RESOURCE_GOLD | Only via owner-gated promotion of a RESOURCE_RULE_DERIVED item (owner audit + owner-signed approval + matching digests). | Yes, as promoted |
| OWNER_CORRECTED | The owner corrects a verified pipeline error, with provenance. Currently defined but NOT yet creatable by any implemented program (fail-closed: make_packet refuses it and PROMOTION_MAP has no entry); a correction path must be added to owner_gated_promotion.py before use. | Yes, as promoted (once a path exists) |
| CONSTRUCTION_CANDIDATE | A CAS-trace generator's output (label known before the sentence; see `CAS_TRACE_GOLD_SPEC_v1.md`), before audit. | Never |
| RESOURCE_RULE_DERIVED | The deterministic keyword engine's output (exactly one rule fired), before audit. A deterministic filter, not semantic ground truth. | Never |
| CONTROLLED_TEMPLATE_FIXTURE | The retired Phase 0B template generator (its checker shared the generator's verb table — circular). Pipeline tests only; promotion refuses it. | Never |
| MODEL_PROPOSED | One or more models suggest a label. | Never |
| WEAK_LABEL | Models plus heuristics agree, but no exact rule establishes it. Training only; never protected evaluation. | Never |
| ABSTAIN | Ambiguous, conflicting, unsupported, or multi-label. Excluded; cas_label = null. | Never |

## 4. The enforced invariant (derived in code)

There is one hard rule, computed in `label_common.derive_claim_bearing` and enforced by
`make_packet`, the ingest guard `validate_packet`/`load_packets`, and the promotion
program. FOUR conditions, all required:

```
claim_bearing == (
    authority in {CONSTRUCTION_GOLD, RESOURCE_GOLD, OWNER_CORRECTED}
    AND audit_state == OWNER_APPROVED
    AND the required approval digests are present
        (approval_manifest_digest, owner_approval_digest, plus
         resource_manifest_digest for RESOURCE_GOLD /
         generator_manifest_digest for CONSTRUCTION_GOLD)
    AND phase_approval_valid == True
)
```

Key points:
- `claim_bearing` is DERIVED. It is never passed in by a caller and never by a model.
- `make_packet` REFUSES to construct gold authorities at all. Only
  `owner_gated_promotion.py` creates them, and only after verifying an owner-signed
  approval record, an audit receipt (sequential gate), and matching digests. No
  deterministic labeling engine may promote its own output to gold.
- A gold or candidate authority requires a non-null `cas_label`. ABSTAIN requires null.
- Determinism freezes a judgment; it does not validate the judgment. A fired keyword rule
  is a reproducible judgment, not semantic ground truth.

## 5. Model consensus grants NO authority

State it plainly: agreement among models does not create authority.

- 3 models agreeing does NOT create a gold label.
- 3 models disagreeing does NOT prove a label false.
- Agreement only changes AUDIT PRIORITY. It decides what the owner looks at
  first. It never decides what the label IS.

A model can retrieve a source, propose a mapping, write a paraphrase, flag an
ambiguity, or criticize a candidate. None of that writes a claim-bearing label.

## 6. Deterministic firing mechanism

The engine that issues RESOURCE_RULE_DERIVED candidates and ABSTAIN labels is
`deterministic_label_engine.py`, driven by the CANDIDATE rule table
`CAS_MAPPING_RULES_v1_CANDIDATE.yaml` (status: AWAITING_OWNER_APPROVAL — the owner has
not yet approved these rules).

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
- exactly one rule fires -> RESOURCE_RULE_DERIVED for that class (candidate, NOT claim-bearing),
- zero rules fire -> ABSTAIN with reason `no_rule`,
- two or more rules fire -> ABSTAIN with reason `multiple_rules`,
- a caller-flagged source disagreement -> ABSTAIN with reason `source_conflict`.

A model's proposed rule id is advisory "evidence" ONLY. The engine ALWAYS
recomputes firing from the frozen text. It never trusts the model's answer.

Honest limit of this mechanism: keyword matching over a gloss cannot reliably handle
negation ("to refuse to analyze the issue" contains `analyze` but the central act is
refusal), irony, scope, argument roles, polysemy, metaphor, or which event is central
("to trigger a device" is generic physical causation, not `^8`'s one-Idea-triggers-
another-Idea). That is WHY its output is a candidate and the owner audit exists.

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
- `audit_state` (`UNAUDITED` | `GENERATOR_APPROVED` | `OWNER_APPROVED`)
- `approval_manifest_digest`, `owner_approval_digest`, `resource_manifest_digest`,
  `generator_manifest_digest`, `phase_approval_valid` (set only by the promotion program)
- `sense{ sense_id, lemma, pos, gloss, source, frame }`
- `construction{ construction_seed, noetic, semantic_graph, template_id }`
- `fired_rules[]`
- `blocked_rules[]`
- `abstain_reason` (one of: `no_rule` | `multiple_rules` | `source_conflict`
  | `unverifiable_source` | `ambiguous` | null)
- `evidence{ sense_id, source_locator, exact_gloss, source_frame_id,
  proposed_cas_class, proposed_rule_id, model_id, model_revision, model_role,
  evidence_timestamp, resource_digest }` (NON-authoritative; Phase 0C schema —
  `source_frame_id` and `proposed_cas_class` are SEPARATE fields; the old
  `frame_or_class` overload is retired)
- `surface{ sentence, realization_lane (deterministic | ai_paraphrase),
  roundtrip_ok }`
- `provenance{ frozen_resource_digest, rule_table_digest, engine_version,
  created_by, preservation_check, seed }`

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

## 12. Construction path (Phase 0C: the old generator is retired)

The Phase 0B generator `construction_gold_generator.py` is RETIRED from evaluation. Its
round-trip checker used the same VERB_TO_CLASS table the generator selected verbs from —
a circular check that proves the lookup table agrees with itself. Its output authority is
now CONTROLLED_TEMPLATE_FIXTURE: pipeline/unit tests only, refused by the promotion
program (`FIXTURE_NOT_PROMOTABLE`, also via its provenance marker
`preservation_check = "shared_verb_lookup"`).

The replacement Tier A design is `CAS_TRACE_GOLD_SPEC_v1.md`: formal CAS state or CNCM
trace -> CAS-Sem graph -> surface realization -> an INDEPENDENTLY IMPLEMENTED preservation
check that shares no verb-to-class lookup with the generator. Its output is
CONSTRUCTION_CANDIDATE, promotable to CONSTRUCTION_GOLD only through the owner-gated
promotion path. It is a specification only in this phase — not implemented, not run.

## 13. Owner audit (Phase 0C: risk-based; the dev queue is a fixture)

The current 70-item queue built from the dev pilot is DEV_AUDIT_FIXTURE_ONLY — it mixes
synthetic decoys (`adoredissect`, `dreadevoke`) with fixtures and must NOT consume owner
time. The PRODUCTION audit (see `OWNER_AUDIT_PROTOCOL.md`) is risk-based:

- every mapping rule reviewed once,
- 8 randomly selected real RESOURCE_RULE_DERIVED items per class (32 items),
- ALL high-risk model disagreements,
- 8 ABSTAIN boundary cases,
- 8 HIDDEN DUPLICATES (the same item under a second blinded id) to measure
  within-owner consistency — about 48 visible judgments plus high-risk items.

Sequential gate: 0 major errors -> the rule table may proceed to the controlled pilot;
1–2 -> repair the rule, regenerate, audit a fresh sample; 3+ -> reject the rule table.

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

## 18. Pilot result — SYNTHETIC_PIPELINE_FIXTURE_PASS (not claim-bearing)

This is a software-behavior fixture run. The 46 dev senses were authored by the same
agent that wrote the keyword rules, specifically to exercise them; agreement between the
fixtures and the rules validates the SOFTWARE, not the rules' semantics. Agreement with
the author of synthetic fixtures is not an independent validity measure and is excluded
from scientific reporting.

- claim-bearing packet count: **0** (asserted by the pilot; enforced by the ingest guard).
- 46 dev senses -> 40 RESOURCE_RULE_DERIVED (candidates) + 6 ABSTAIN.
- coverage 0.8696, abstention 0.1304.
- source-verification failure rate 0.0 (over the checks the verifier implements).
- cross-class integrity OK.
- 40 CONTROLLED_TEMPLATE_FIXTURE items (retired generator; not evaluation data).
- 86 total packets, all non-claim-bearing.
- dev audit queue: DEV_AUDIT_FIXTURE_ONLY — the owner is NOT asked to judge it.
- tests: 45/45 pass.
- rule table (CANDIDATE) sha256:
  `f6db8a8c1d6148491ffbd976d461a794b02d86e3daa17c803863ec6e3b586d07`
- dev resource sha256:
  `38649fe0acf4c17e0229750291534c04cc75970135abda1c516d6fe9bf36b8bc`

## 19. Cross-references

- `CAS_MAPPING_RULES_v1_CANDIDATE.yaml` — the CANDIDATE rule table (awaiting owner approval).
- `owner_gated_promotion.py` — the ONLY path from candidate to gold.
- `RESOURCE_GOLD_SPEC.md` — the RESOURCE_RULE_DERIVED -> RESOURCE_GOLD path in full.
- `CONSTRUCTION_GOLD_SPEC.md` — the (retired) template path + pointer to the replacement.
- `CAS_TRACE_GOLD_SPEC_v1.md` — the non-circular Tier A design (spec only).
- `AI_LABELER_ROLE_PROMPTS.md` — the non-authoritative model roles.
- `OWNER_AUDIT_PROTOCOL.md` — the blinded owner audit procedure (production, risk-based).
- `SCMPE_GENERATION_SPEC.md` — the control generation procedure + exact parameters.
- `LABEL_CLAIM_BOUNDARY.md` — what is and is not claim-bearing.
- `LABEL_PACKET.schema.json` — the LABEL_PACKET field schema (Phase 0C).
- `../PREREGISTRATION_v0_3B_CANDIDATE.md` — the append-only preregistration amendment.

## 20. Honest scope

This is a deterministic label backbone. It establishes NO CAS claim yet. It
sets who may issue a label and how. It does not prove that the CAS classes
carry any real signal. A model can never set a claim-bearing label. The pilot
proved nothing scientific — it only exercised the pipeline.
