# Owner Audit Protocol

Part of LABEL PHASE 0B, amended by PHASE 0C (owner directive 2026-08-30). Documentation only; not claim-bearing.

## 1. What this document is

This is the plan for the owner audit. An audit here means: the owner
looks at a sample of finished labels, decides each one by hand, and we
then check the owner's decisions against the machine's labels.

Plain terms first. A **label** is the CAS class we attach to a word
sense in a specific sentence (a "sense-in-context"). A **claim-bearing
label** is a label we are willing to stand behind as ground truth. The
owner audit is a check on the small part of the label set that is
claim-bearing.

This document does NOT prove anything scientific. It describes a
deterministic label backbone and a single-owner check on it. Read
Section 12 (the required disclaimer) before quoting any result from this
audit.

## 2. The rule this protocol lives under

Old rule: "No LLM assigns claim-bearing labels. A human labels each
sense."

New rule (owner amendment, LABEL PHASE 0B): "No LLM OUTPUT ALONE has
claim-bearing label authority."

Models may retrieve sources, propose mappings, generate paraphrases,
find ambiguity, and criticize candidate labels. Models may NOT directly
write final claim-bearing labels. A claim-bearing label is EITHER (A)
CONSTRUCTION_GOLD or (B) RESOURCE_GOLD — and (Phase 0C) both exist ONLY
as output of the owner-gated promotion program. The deterministic
pipelines emit candidates (RESOURCE_RULE_DERIVED, CONSTRUCTION_CANDIDATE)
which are never claim-bearing. This audit is precisely the step that
stands between candidate and gold.

Model consensus grants NO authority. Three models agreeing does not
create a gold label. Three disagreeing does not prove a label false.
Agreement only changes AUDIT PRIORITY (which items the owner should look
at first).

## 3. The label authority hierarchy (Phase 0C)

Candidates first, gold only via promotion:

```
RESOURCE_RULE_DERIVED   --this audit + signed promotion-->   RESOURCE_GOLD
CONSTRUCTION_CANDIDATE  --generator audit + signed promotion--> CONSTRUCTION_GOLD
```

- **CONSTRUCTION_GOLD / RESOURCE_GOLD** — claim-bearing, and creatable ONLY by
  `owner_gated_promotion.py` with an owner-signed approval (key fingerprint pinned in
  `OWNER_KEY_FINGERPRINT.json`), a passing audit receipt attesting every rule was
  reviewed, and matching digests.
- **OWNER_CORRECTED** — claim-bearing by definition, but NOT yet creatable by any implemented program (fail-closed: make_packet refuses it and PROMOTION_MAP has no entry); a correction path must be added to owner_gated_promotion.py before use.
- **RESOURCE_RULE_DERIVED** — the keyword engine's candidate. Never claim-bearing.
- **CONSTRUCTION_CANDIDATE** — the CAS-trace generator's candidate
  (`CAS_TRACE_GOLD_SPEC_v1.md`). Never claim-bearing.
- **CONTROLLED_TEMPLATE_FIXTURE** — the retired circular template generator.
  Pipeline tests only; promotion refuses it.
- **MODEL_PROPOSED** — one or more models suggest a label. NEVER claim-bearing.
- **WEAK_LABEL** — models plus heuristics agree, no exact rule. TRAINING ONLY.
- **ABSTAIN** — ambiguous/conflicting/unsupported/multi-label. Excluded;
  `cas_label = null`.

Enforced invariant (in code, `label_common.derive_claim_bearing`):
`claim_bearing` is true ONLY when the authority is gold AND
`audit_state == OWNER_APPROVED` AND the approval digests are present AND
`phase_approval_valid` is true. It is DERIVED, never passed in. A gold or
candidate authority requires a non-null `cas_label`; ABSTAIN requires null.

## 4. The 4 CAS classes under audit

Labels apply to a SENSE-IN-CONTEXT, never to bare spelling.

- **CAS-N2** (`^2` Positive) — affinity, attraction, preference, desire,
  approach TOWARD the object.
- **CAS-N3** (`^3` Negative) — aversion, repulsion, avoidance, dread,
  rejection, withdrawal FROM the object.
  ANTI-DRIFT: `^3` is VISCERAL, not analytical. Critique, scrutiny, and
  assessment are `^6` and are EXCLUDED from `^3`.
- **CAS-N6** (`^6` Male) — decomposition, analysis, separation into
  parts, structural inspection, testing.
  ANTI-DRIFT: merely asking a question does NOT qualify; ask, question,
  inquire, query, wonder are EXCLUDED.
- **CAS-N8** (`^8` Above/Cause) — one cue, event, or Idea TRIGGERS
  another Idea/response to arise.
  ANTI-DRIFT: not deduction; mere temporal sequence and ordinary
  communication do NOT qualify; deduce, infer, conclude, prove, say,
  tell, announce, state are EXCLUDED.

Source of these definitions: CLAUDE.md 10-Noetics (verbatim) plus
`CAS_FOUNDATIONAL_CLARIFICATIONS` Clarification 6; master charter
`cas_reasoner.txt`.

## 5. The blinded owner audit queue (Phase 0C: production is risk-based)

**The current 70-item queue from the dev pilot is DEV_AUDIT_FIXTURE_ONLY. Do not spend
owner time judging it.** It mixes synthetic decoys (`adoredissect`, `bringtomind`,
`dreadevoke`), dev-surrogate senses authored to exercise the rules, and circular template
fixtures. It tests the development pipeline, not a production dataset.

The PRODUCTION audit has two parts. Part 1: the owner reviews every mapping rule once
(4 rules) — this is attested in the audit receipt (`rules_reviewed: {rule_id: true}`),
and the promotion program refuses a receipt that does not attest every rule
(`FAILED_AUDIT`). Part 2: the blinded queue, built by
`owner_audit_queue.build_production_queue` over REAL resource candidates once a frozen
production resource exists. The queue contains:

- **8 randomly selected real RESOURCE_RULE_DERIVED items per class** (32 items).
- **ALL high-risk model disagreements** (variable count; never sampled away).
- **8 ABSTAIN boundary cases** (so the owner also checks what the engine refused).
- **8 HIDDEN DUPLICATES** — the same item appears a second time under a different
  blinded id, measuring within-owner consistency.

That is about **48 visible judgments** plus the high-risk items — not 240 and not a
synthetic 70-item ceremony.

### Sequential gate on the audited sample

- **0 major errors** — accept the rule table for the controlled pilot.
- **1 or 2 major errors** — repair the rule, regenerate the data, audit a fresh sample.
- **3 or more** — reject the rule table and redesign it.

These are engineering gates, not a substitute for independent human inter-rater
validation. The gate outcome feeds `owner_gated_promotion.py`: a receipt that is not
PASS blocks promotion (`FAILED_AUDIT`).

### Two-file scheme

- `audit_queue.blinded.json` — the owner sees this. It has NO label and
  an empty `owner_judgment` field. The machine's label is hidden until
  the owner records a judgment.
- `audit_queue.sealed.json` — maps `queue_id` to the true label and to
  the duplicate groups. It is used ONLY to score AFTER the owner has
  recorded judgments. It is not opened during judging.

The point of the two files: the owner judges blind. The programmatic
label stays hidden so it cannot anchor the owner's decision.

## 6. Scoring

After the owner records judgments, we open the sealed file and compute:

- **Owner-vs-engine disagreement** — how often the owner's judgment
  differs from the machine's label.
- **Duplicate consistency** — how often the owner gave the same answer
  to both copies of a hidden-duplicate item.

## 7. Required report fields

The audit report must include, for each, an exact number:

- automatic-label coverage
- abstention rate
- model disagreement rate
- source-verification failure rate
- owner-audit disagreement rate
- duplicate-item consistency
- per-rule error counts

## 8. The owner's 6-step job

1. Approve the 4 class definitions (Section 4).
2. Approve the rule table.
3. Inspect every rule once.
4. Review the high-risk items (items flagged by model disagreement or
   source-verification concerns).
5. Blind-audit a random sample per class (the queue in Section 5).
6. Sign the final digests (rule table digest and frozen resource
   digest).

## 9. How the labels under audit were produced (context)

The deterministic firing mechanism
(`deterministic_label_engine.py` plus `CAS_MAPPING_RULES_v1_CANDIDATE.yaml`):
normalize the gloss (and frame if present) — lowercase, Unicode NFKD,
non-alphanumeric runs to a single space, then collapse. A rule fires for
its class if and only if at least one include term matches whole-word or
whole-phrase AND no exclude term matches. Across the 4 rules: exactly one
fires gives RESOURCE_RULE_DERIVED for that class (a candidate — gold only
via owner-gated promotion); zero fires gives ABSTAIN(no_rule); two or more
give ABSTAIN(multiple_rules); a caller-flagged source disagreement gives
ABSTAIN(source_conflict). A model's proposed rule id is advisory evidence
ONLY; the engine ALWAYS recomputes firing from the frozen text. Keyword
firing is reproducible; it is not semantic ground truth — that is why this
audit exists.

The Phase 0B template generator (`construction_gold_generator.py`) is
RETIRED from evaluation: its round-trip checker shared the generator's own
verb-to-class table (circular). Its output is CONTROLLED_TEMPLATE_FIXTURE,
refused by promotion. The replacement Tier A design is
`CAS_TRACE_GOLD_SPEC_v1.md` (CONSTRUCTION_CANDIDATE from formal CAS traces
with an independently implemented preservation check).

The source verifier (`label_source_verifier.py`) rejects: nonexistent
sense ids; invented quotes; paraphrase presented as an exact quote;
mismatched frame ids; conflicting mappings; duplicate senses in a
resource; any source consulted after protected results opened; and a
resource digest that does not equal the manifest-frozen digest.

## 10. Abstain discipline — no quota rescue

Ambiguous or conflicting items get ABSTAIN and are EXCLUDED. NEVER
broaden include sets or definitions to hit a round-number sample size.
Better 120 clean senses than 240 semantic puddles. If the smallest class
cannot supply the frozen minimum without ambiguous labels, return
INSUFFICIENT_CLEAN_LABEL_COVERAGE. Do not rescue the study.

## 11. Pilot queue counts (SYNTHETIC_PIPELINE_FIXTURE_PASS — do not judge this queue)

The dev pilot run produced the numbers below. Status: DEV_AUDIT_FIXTURE_ONLY. The owner
is NOT asked to judge this queue. The "mismatch vs author intent" figure is a
development-fixture check only (agreement with the author of synthetic fixtures is not
independent validity evidence) and is excluded from scientific reporting. Zero packets
are claim-bearing.

- 46 dev senses to 40 RESOURCE_RULE_DERIVED (candidates, non-claim-bearing) + 6 ABSTAIN (coverage 0.8696,
  abstention 0.1304).
- source-verification failure rate 0.0; cross-class integrity OK; 0
  mismatch vs author intent; per-rule 10/10/10/10; 40 controlled-template fixtures (retired generator);
  86 total packets.
- **Dev fixture queue: 70 items + 4 rules + 4 hidden duplicates — DEV_AUDIT_FIXTURE_ONLY,
  retired un-judged.**
- Tests: 45/45 pass.
- rule table sha256
  `f6db8a8c1d6148491ffbd976d461a794b02d86e3daa17c803863ec6e3b586d07`.
- dev resource sha256
  `38649fe0acf4c17e0229750291534c04cc75970135abda1c516d6fe9bf36b8bc`.

These are development numbers. They prove the machinery runs. They do NOT
establish any CAS claim.

## 12. Required disclaimer (verbatim)

> single-owner audit; NOT independent human inter-rater validation.

This disclaimer must appear on every report produced under this
protocol. One person checking labels is not the same as several
independent people agreeing on labels. This audit measures whether the
owner agrees with the machine, and whether the owner is consistent with
himself. It does not measure agreement between independent human raters.

## 13. Governance

Owner-signed phase approval. Deterministic claim promotion. No
hook-based authorization. No model-written claim status. Claude is NOT
the research governor. This audit does not advance any claim tier; it is
a check on the label backbone only.
