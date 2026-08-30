# Resource Gold Spec (Tier B)

Part of LABEL PHASE 0B, amended by PHASE 0C (owner directive 2026-08-30). Documentation only; not claim-bearing.

## 1. What this document is

This document specifies one kind of label: RESOURCE_GOLD. A label is a
tag we attach to a word sense. It says which CAS class that sense belongs
to. RESOURCE_GOLD is a label produced by a fixed rule, not by a model's
free choice.

Plain-English summary of the idea (Phase 0C): we take a word meaning that
already lives in a frozen outside dictionary. We run one deterministic
rule over the exact text of that meaning. If exactly one rule fires, the
item becomes a CANDIDATE (`RESOURCE_RULE_DERIVED`) — not yet gold. If not,
we abstain. The candidate becomes `RESOURCE_GOLD` ONLY after the owner's
blinded audit passes and the owner signs the promotion
(`owner_gated_promotion.py`). No model writes the final label, and no
deterministic engine promotes its own output. Determinism freezes a
judgment; it does not validate the judgment.

This is a deterministic label backbone. "Deterministic" means the same
input always gives the same output, with no randomness and no model
opinion. This backbone establishes no CAS scientific claim by itself. It
only produces labels that a later study can use.

## 2. Where RESOURCE_GOLD sits (Phase 0C authority hierarchy)

The flow is candidate-first; gold exists only via the promotion program:

```
RESOURCE_RULE_DERIVED   --owner audit + signed promotion-->   RESOURCE_GOLD
CONSTRUCTION_CANDIDATE  --generator audit + signed promotion--> CONSTRUCTION_GOLD
```

- `RESOURCE_RULE_DERIVED` — the engine's output when exactly one rule fires.
  A deterministic candidate filter result, NOT semantic ground truth, never
  claim-bearing. This document specifies this path and its promotion.
- `RESOURCE_GOLD` — the promoted form. Claim-bearing, creatable only by
  `owner_gated_promotion.py`.
- `CONSTRUCTION_CANDIDATE` / `CONSTRUCTION_GOLD` — the Tier A counterpart
  (see `CAS_TRACE_GOLD_SPEC_v1.md`).
- `CONTROLLED_TEMPLATE_FIXTURE` — the retired circular template generator's
  output. Pipeline tests only; promotion refuses it.
- `MODEL_PROPOSED` — one or more models suggest a label. NEVER claim-bearing.
- `WEAK_LABEL` — models plus heuristics agree, no exact rule. TRAINING ONLY,
  never protected eval.
- `ABSTAIN` — ambiguous, conflicting, unsupported, or multi-label. Excluded,
  `cas_label = null`.
- `OWNER_CORRECTED` — the owner corrects a verified pipeline error. Claim-bearing,
  with provenance; defined but NOT yet creatable by any implemented program (fail-closed: make_packet refuses it and PROMOTION_MAP has no entry); a correction path must be added to owner_gated_promotion.py before use.

"Claim-bearing" means the label is allowed to carry weight in a later
scientific claim. Only three classes are claim-bearing — `CONSTRUCTION_GOLD`,
`RESOURCE_GOLD`, `OWNER_CORRECTED` — and each exists only as promoted output.

### The replaced rule

- OLD: "No LLM assigns claim-bearing labels. A human labels each sense."
- NEW: "No LLM OUTPUT ALONE has claim-bearing label authority."

Under the new rule, models may retrieve sources, propose mappings,
generate paraphrases, find ambiguity, and criticize candidate labels.
Models may NOT directly write final claim-bearing labels. A claim-bearing
label is EITHER (A) `CONSTRUCTION_GOLD` or (B) `RESOURCE_GOLD` — and both
exist only as output of the owner-gated promotion program; the
deterministic pipelines emit candidates.

### Enforced invariant (Phase 0C)

The code enforces this in `label_common.derive_claim_bearing` (and via
`make_packet`, the ingest guard, and the promotion program):

```
claim_bearing == (
    authority in {CONSTRUCTION_GOLD, RESOURCE_GOLD, OWNER_CORRECTED}
    AND audit_state == OWNER_APPROVED
    AND the required approval digests are present
    AND phase_approval_valid == True
)
```

`claim_bearing` is DERIVED. It is never passed in by a caller.
`make_packet` refuses to construct gold authorities at all — only the
promotion program creates them. A gold or candidate authority requires a
non-null `cas_label`. An `ABSTAIN` requires a null `cas_label`.

Model consensus grants NO authority. Three models agreeing does not
create a gold label. Three models disagreeing does not prove a label
false. Agreement only changes AUDIT PRIORITY (which items a human looks
at first).

## 3. The deterministic mapping (Tier B core)

Tier B is a deterministic mapping from a FROZEN external sense/frame id to
ONE CAS class, via a mapping rule (the current table is a CANDIDATE
awaiting owner approval). The engine is
`deterministic_label_engine.py` with the rule table
`CAS_MAPPING_RULES_v1_CANDIDATE.yaml`.

### Firing mechanism

Step 1 — Normalize the gloss (plus the frame text if present). A "gloss"
is the dictionary definition text of the sense. Normalization:

- lowercase
- Unicode NFKD form
- replace any run of non-alphanumeric characters with a single space
- collapse spaces

Step 2 — Test each rule. A rule fires for its class if and only if:

- at least one INCLUDE term matches on a whole-word or whole-phrase
  boundary, AND
- no EXCLUDE term matches.

Step 3 — Count fired rules across the 4 rules:

- exactly one fires -> `RESOURCE_RULE_DERIVED` (that class; candidate — gold only via owner-gated promotion)
- zero fire -> `ABSTAIN` with reason `no_rule`
- two or more fire -> `ABSTAIN` with reason `multiple_rules`
- caller-flagged source disagreement -> `ABSTAIN` with reason
  `source_conflict`

A model's proposed rule id is advisory "evidence" ONLY. The engine ALWAYS
recomputes firing from the frozen text. It never trusts the model's
suggestion.

## 4. The 4 CAS classes and rule ids

These labels apply to the SENSE-IN-CONTEXT, never to the bare spelling of
a word.

- `CAS-N2` (`^2` Positive) — affinity, attraction, preference, desire, or
  approach TOWARD the object.
- `CAS-N3` (`^3` Negative) — aversion, repulsion, avoidance, dread,
  rejection, or withdrawal FROM the object.
  - ANTI-DRIFT: `^3` is VISCERAL, not analytical. Critique, scrutiny, and
    assessment are `^6` and are EXCLUDED from `^3`.
- `CAS-N6` (`^6` Male) — decomposition, analysis, separation into parts,
  structural inspection, or testing.
  - ANTI-DRIFT: merely asking a question does NOT qualify. `ask`,
    `question`, `inquire`, `query`, `wonder` are EXCLUDED.
- `CAS-N8` (`^8` Above/Cause) — one cue, event, or Idea TRIGGERS another
  Idea or response to arise.
  - ANTI-DRIFT: not deduction. Mere temporal sequence and ordinary
    communication do NOT qualify. `deduce`, `infer`, `conclude`, `prove`,
    `say`, `tell`, `announce`, `state` are EXCLUDED.

Source of these definitions: `CLAUDE.md` 10-Noetics (verbatim) plus
`CAS_FOUNDATIONAL_CLARIFICATIONS` Clarification 6. Master charter:
`cas_reasoner.txt`.

## 5. Abstain discipline and no quota rescue

Ambiguous or conflicting items get `ABSTAIN` and are EXCLUDED. NEVER
broaden the include sets or the definitions to hit a round-number sample
size. "Better 120 clean senses than 240 semantic puddles."

If the smallest class cannot supply the frozen minimum without ambiguous
labels, return `INSUFFICIENT_CLEAN_LABEL_COVERAGE`. Do not rescue the
study.

## 6. Required provenance for a RESOURCE_GOLD label

Every RESOURCE_GOLD label must carry all of this:

- frozen resource version and digest
- the exact sense/frame id
- the exact source gloss (verbatim)
- the exact mapping-rule id that fired
- proof that exactly one rule fired
- proof that no exclusion term fired
- complete provenance (all fields below present)
- the owner-approved rule-table digest (the CANDIDATE table becomes
  owner-approved only when the owner signs it)
- **the promotion record**: `audit_state = OWNER_APPROVED`, the approval
  manifest digest, the owner-approval digest, the resource manifest
  digest, and `phase_approval_valid = True` — all set by
  `owner_gated_promotion.py` after verifying the owner's signature, the
  audit receipt (sequential gate PASS), and every digest match.

If any of these is missing, the item is not a RESOURCE_GOLD label — at
most it is a RESOURCE_RULE_DERIVED candidate.

## 7. The LABEL_PACKET

Schema: `LABEL_PACKET.schema.json`. Fields:

- `packet_id`
- `authority`
- `cas_label`
- `claim_bearing` (DERIVED, never passed in)
- `audit_state` (`UNAUDITED` | `GENERATOR_APPROVED` | `OWNER_APPROVED`)
- `approval_manifest_digest`, `owner_approval_digest`,
  `resource_manifest_digest`, `generator_manifest_digest`,
  `phase_approval_valid` (set only by the promotion program)
- `sense` = { `sense_id`, `lemma`, `pos`, `gloss`, `source`, `frame` }
- `construction` = { `construction_seed`, `noetic`, `semantic_graph`,
  `template_id` }
- `fired_rules[]`
- `blocked_rules[]`
- `abstain_reason` (`no_rule` | `multiple_rules` | `source_conflict` |
  `unverifiable_source` | `ambiguous` | `null`)
- `evidence` = { `sense_id`, `source_locator`, `exact_gloss`,
  `source_frame_id`, `proposed_cas_class`, `proposed_rule_id`,
  `model_id`, `model_revision`, `model_role`, `evidence_timestamp`,
  `resource_digest` } — NON-authoritative (Phase 0C schema; the old
  `frame_or_class` overload is retired)
- `surface` = { `sentence`, `realization_lane`
  (`deterministic` | `ai_paraphrase`), `roundtrip_ok` }
- `provenance` = { `frozen_resource_digest`, `rule_table_digest`,
  `engine_version`, `created_by`, `preservation_check`, `seed` }

The `evidence` block records what a model said. It is NON-authoritative.
It never sets the label.

## 8. Production and dev resources

Production resources (the frozen external dictionaries):

- WordNet 3.1 — digest OWNER_TO_FREEZE
- VerbNet 3.4 — digest OWNER_TO_FREEZE
- FrameNet 1.7 — digest OWNER_TO_FREEZE

"OWNER_TO_FREEZE" means the owner must record the exact digest before any
production run. A digest is a fixed fingerprint of the file. It proves the
file did not change.

Dev surrogate: a small development-only stand-in resource. Pilot-only. It
must never produce a claim-bearing production label.

## 9. Source verifier

Engine: `label_source_verifier.py`. Manifest: `SOURCE_RESOURCE_MANIFEST.json`.

The verifier REJECTS an item for any of these:

- nonexistent sense ids
- invented quotes (a gloss that is not verbatim in the frozen resource)
- a paraphrase presented as an exact quote (normalized-equal but not
  byte-equal)
- mismatched frame ids
- conflicting mappings (the same sense id pointing to a different class)
- duplicate senses inside one resource
- ANY source consulted AFTER protected results are opened (the
  freeze-time gate)
- a resource digest that does not equal the manifest-frozen digest

The freeze-time gate means: once protected evaluation results are opened,
no new source lookup may enter the pipeline. This stops after-the-fact
cherry-picking.

## 10. Construction path (for contrast — Phase 0C)

The Phase 0B generator `construction_gold_generator.py` is RETIRED from
evaluation: its round-trip checker used the generator's own verb-to-class
table (circular). Its output is `CONTROLLED_TEMPLATE_FIXTURE` — pipeline
tests only, refused by promotion (`FIXTURE_NOT_PROMOTABLE`).

The replacement Tier A design is `CAS_TRACE_GOLD_SPEC_v1.md`: formal CAS
trace -> CAS-Sem graph -> surface realization -> an INDEPENDENTLY
implemented preservation check (no shared verb-to-class lookup). Its
output is `CONSTRUCTION_CANDIDATE`, promotable to `CONSTRUCTION_GOLD`
only via the owner-gated promotion path.

## 11. Owner audit

Queue builder: `owner_audit_queue.py`; the production queue is RISK-BASED (Phase 0C): every mapping rule reviewed once;
8 randomly selected real RESOURCE_RULE_DERIVED items per class (32); ALL high-risk
model disagreements; 8 ABSTAIN boundary cases; 8 HIDDEN DUPLICATES (the same item
under a second blinded id, measuring within-owner consistency) -- about 48 visible
judgments plus high-risk. The current 70-item dev queue is DEV_AUDIT_FIXTURE_ONLY
and is NOT judged by the owner. Sequential gate: 0 major errors PASS; 1-2
repair-and-resample; 3+ reject.

Two files:

- `audit_queue.blinded.json` — the owner sees this. NO label. Empty
  `owner_judgment`.
- `audit_queue.sealed.json` — maps `queue_id` to the true label and the
  duplicate groups. Used only to score AFTER the owner judges.

Report metrics: automatic-label coverage; abstention rate; model
disagreement rate; source-verification failure rate; owner-audit
disagreement rate; duplicate-item consistency; per-rule error counts.

REQUIRED DISCLAIMER: "single-owner audit; NOT independent human
inter-rater validation."

Owner job: approve the 4 class definitions; approve the rule table;
inspect every rule once; review high-risk items; blind-audit a random
sample per class; sign the final digests.

## 12. Controls (SCMPE-v1)

SCMPE-v1 generates controls. It is built BEFORE any hidden-state result is
opened. Steps:

1. Freeze an INDEPENDENT lexical resource (NOT the target Qwen hidden
   states).
2. Represent each sense by gloss terms, source frame, thematic roles,
   lexical relations, frequency, token length, and morphology.
3. Compute cohesion and separation of the CAS partition.
4. Generate at least 1000 balanced alternative 4-way partitions.
5. Keep only partitions whose measurable properties match the CAS
   partition within FROZEN tolerances.
6. Report where CAS falls in that distribution (a percentile).

Balanced-random control: map each sense to one class ONCE and keep that
mapping across every occurrence and split. No human picks the "best
opponent" after seeing results.

## 13. Claims and tier order

The claims are kept separate. Promotion is deterministic and gated by an
owner-signed phase record.

- A — decodability
- B — incremental value over lexical and matched-semantic controls (only B
  licenses the phrase "CAS-specific")
- C — causal intervention utility
- D — learning benefit

Tier A proves the mechanism in a controlled CAS-generated domain (NOT
unrestricted English). Tier B tests transfer via frozen source-derived
labels. Do NOT start Tier B until Tier A beats matched controls.

HARD RULE: The target model checkpoint MUST NOT assign labels or generate
protected evaluation items.

## 14. Compute

No local CPU neural workload. Deterministic source-verification and
dataset scripts may run locally on CPU. Remote models (Bedrock or other)
are for source-location, criticism, counterexample, and paraphrase
PROPOSALS only (all non-authoritative). AWS GPU is for hidden-state
extraction, probing, intervention, training, and protected eval. Bedrock
is teacher/proposal language only.

## 15. Governance

Owner-signed phase approval. Deterministic claim promotion. No hook-based
authorization. No model-written claim status. Claude is NOT the research
governor.

## 16. Pilot result — SYNTHETIC_PIPELINE_FIXTURE_PASS (not claim-bearing)

This pilot proved nothing scientific. It only checked that the pipeline
runs and stays internally consistent (0 claim-bearing packets, asserted).

- 46 dev senses -> 40 `RESOURCE_RULE_DERIVED` (candidates, non-claim-bearing) + 6 `ABSTAIN`
- coverage 0.8696, abstention 0.1304
- source-verification failure rate 0.0
- cross-class integrity OK
- 0 mismatch vs author intent (development-fixture check ONLY — agreement with the
  author of synthetic fixtures is not independent validity evidence; excluded from
  scientific reporting)
- per-rule 10/10/10/10
- 40 controlled-template fixtures (retired generator)
- 86 total packets
- dev fixture queue 70 items + 4 rules + 4 hidden duplicates (DEV_AUDIT_FIXTURE_ONLY,
  retired un-judged)
- tests 45/45 pass
- rule table sha256
  `f6db8a8c1d6148491ffbd976d461a794b02d86e3daa17c803863ec6e3b586d07`
- dev resource sha256
  `38649fe0acf4c17e0229750291534c04cc75970135abda1c516d6fe9bf36b8bc`

## 17. Referenced files

- `deterministic_label_engine.py` — recomputes rule firing from frozen text
- `label_source_verifier.py` — rejects bad or unverifiable sources
- `SOURCE_RESOURCE_MANIFEST.json` — the frozen resource digest manifest
