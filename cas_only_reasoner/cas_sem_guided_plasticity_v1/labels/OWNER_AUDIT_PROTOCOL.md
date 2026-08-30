# Owner Audit Protocol

Part of LABEL PHASE 0B. Documentation only; not claim-bearing.

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
CONSTRUCTION_GOLD or (B) RESOURCE_GOLD, both produced deterministically.

Model consensus grants NO authority. Three models agreeing does not
create a gold label. Three disagreeing does not prove a label false.
Agreement only changes AUDIT PRIORITY (which items the owner should look
at first).

## 3. The six label classes (authority hierarchy)

- **CONSTRUCTION_GOLD** — the CAS state/trace existed BEFORE the sentence
  was generated. Claim-bearing.
- **RESOURCE_GOLD** — a frozen external sense id, mapped to a class by an
  owner-approved deterministic rule. Claim-bearing after audit.
- **MODEL_PROPOSED** — one or more models suggest a label. NEVER
  claim-bearing.
- **WEAK_LABEL** — models plus heuristics agree, but no exact rule
  establishes it. TRAINING ONLY, never protected eval.
- **ABSTAIN** — ambiguous, conflicting, unsupported, or multi-label.
  Excluded; `cas_label = null`.
- **OWNER_CORRECTED** — the owner corrects a verified pipeline error.
  Claim-bearing, with provenance.

Enforced invariant (in code, `label_common.make_packet`):
`claim_bearing == (authority in {CONSTRUCTION_GOLD, RESOURCE_GOLD,
OWNER_CORRECTED})`. It is DERIVED, never passed in. A gold authority
requires a non-null `cas_label`; ABSTAIN requires null.

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

## 5. The blinded owner audit queue

The queue is built by `owner_audit_queue.py`. It contains:

- Up to **15 accepted items per class** (a random sample of the
  claim-bearing labels for that class).
- An **abstain sample** (a set of ABSTAIN items, so the owner also
  checks items the machine set aside).
- **HIDDEN DUPLICATES** — the same item appears a second time under a
  different blinded id. This measures within-owner consistency: does the
  owner decide the same item the same way twice?

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
(`deterministic_label_engine.py` plus `CAS_MAPPING_RULES_v1.yaml`):
normalize the gloss (and frame if present) — lowercase, Unicode NFKD,
non-alphanumeric runs to a single space, then collapse. A rule fires for
its class if and only if at least one include term matches whole-word or
whole-phrase AND no exclude term matches. Across the 4 rules: exactly one
fires gives RESOURCE_GOLD for that class; zero fires gives
ABSTAIN(no_rule); two or more give ABSTAIN(multiple_rules); a
caller-flagged source disagreement gives ABSTAIN(source_conflict). A
model's proposed rule id is advisory evidence ONLY; the engine ALWAYS
recomputes firing from the frozen text.

CONSTRUCTION_GOLD (`construction_gold_generator.py`): the formal CAS op
is known first, then a deterministic template plus a frozen synonym table
build a sentence, then a round-trip parser recovers the seed op. Only
round-trip-OK items are CONSTRUCTION_GOLD. A round-trip failure is
EXCLUDED, never relabeled. Class ops: `^2` attract, `^3` averse, `^6`
decompose, `^8` trigger.

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

## 11. Pilot queue counts (development-only, not claim-bearing)

The pilot run produced:

- 46 dev senses to 40 RESOURCE_GOLD + 6 ABSTAIN (coverage 0.8696,
  abstention 0.1304).
- source-verification failure rate 0.0; cross-class integrity OK; 0
  mismatch vs author intent; per-rule 10/10/10/10; 40 construction-gold;
  86 total packets.
- **Owner audit queue: 70 items + 4 rules + 4 hidden duplicates.**
- Tests: 19/19 pass.
- rule table sha256
  `5599780d2c1e3ffcb0cc71289f0a475d3a712465fdafa37147b8b0ebc256eb86`.
- dev resource sha256
  `740d72da8a6f5cca347ef816b40abcb3952e4a11c09b0c6896497c3d78dc5c24`.

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
