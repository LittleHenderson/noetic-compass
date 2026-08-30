# SCMPE-v1 Generation Spec

Status: Part of LABEL PHASE 0B, amended by PHASE 0C (owner directive 2026-08-30). Documentation only; not claim-bearing.

## 1. What this document is

This document tells you how to build one thing: the SCMPE-v1 control set.

SCMPE stands for Semantic-Cohesion-Matched Partition Ensemble (matching the name used in
`PREREGISTRATION_v0_3A.md`). It is a set of "opponent"
groupings that compete against the CAS grouping. Its job is to answer a fair question: does
the CAS way of sorting word senses into 4 classes carry information beyond what you would get
from plain word properties (dictionary meaning, word frequency, word length, word shape)?

This is a **generation spec**. It tells you how to make the control set. It does NOT run the
study. No hidden-state numbers are opened here. No claim is decided here.

Two plain-English terms defined up front:

- **Sense**: one specific meaning of a word in a specific context, not the bare spelling. The
  word "bank" has several senses. A label attaches to a sense-in-context, never to the spelling.
- **Partition**: one way of splitting all the senses into groups. The CAS partition splits them
  into the 4 CAS classes. An opponent partition splits the same senses into 4 groups a different
  way.

## 2. The hard requirement (read this first)

**The matching representation MUST come from an INDEPENDENT frozen lexical resource. It MUST NOT
come from the target Qwen hidden states being evaluated.**

Plain English: to describe each sense so we can compare partitions, we use an outside dictionary-style
resource that is frozen (fixed, digest-checked). We do NOT use the internal activations of the Qwen
model we are testing. If we described senses using the very model we are judging, the test would be
circular and would prove nothing. The description of a sense and the thing under test must be two
separate sources.

## 3. The 4 CAS classes (exact, for context only)

The CAS partition sorts each sense into exactly one of these 4 classes. Definitions are from the
CLAUDE.md 10-Noetics (verbatim) plus CAS_FOUNDATIONAL_CLARIFICATIONS Clarification 6; master charter
`cas_reasoner.txt`. Labels apply to sense-in-context, never bare spelling.

- **CAS-N2 ^2 Positive** = affinity / attraction / preference / desire / approach TOWARD the object.
- **CAS-N3 ^3 Negative** = aversion / repulsion / avoidance / dread / rejection / withdrawal FROM the object.
  Anti-drift: ^3 is VISCERAL, not analytical. Critique, scrutiny, and assessment are ^6 and are EXCLUDED from ^3.
- **CAS-N6 ^6 Male** = decomposition / analysis / separation into parts / structural inspection / testing.
  Anti-drift: merely asking a question does NOT qualify; ask / question / inquire / query / wonder are EXCLUDED.
- **CAS-N8 ^8 Above/Cause** = one cue / event / Idea TRIGGERS another Idea or response to arise.
  Anti-drift: not deduction; mere temporal sequence and ordinary communication do NOT qualify;
  deduce / infer / conclude / prove / say / tell / announce / state are EXCLUDED.

These class definitions are frozen for the whole SCMPE build. Do not broaden them.

## 4. The 6-step generation procedure

Build the control set in this exact order. All of it happens BEFORE any hidden-state result is opened.

**Step 1 — Freeze an independent lexical resource.**
Pick a dictionary-style lexical resource that is separate from the target Qwen model. Freeze it:
record its content digest in the manifest. This resource is the ONLY source of the matching
description. The target Qwen hidden states are never used to describe senses. (This is the hard
requirement from Section 2, restated as a build step.)

**Step 2 — Represent each sense by measurable lexical properties.**
For every sense, build a description from the frozen resource only: gloss terms (the definition
words), source frame, thematic roles, lexical relations (such as synonym / antonym links), word
frequency, token length, and morphology (word shape / form). No property comes from the target model.

**Step 3 — Compute cohesion and separation of the CAS partition.**
Using the Step 2 descriptions, measure two things for the CAS partition:
- **within-class cohesion**: how similar senses are to each other inside the same CAS class.
- **between-class separation**: how different senses are across the 4 CAS classes.

**Step 4 — Generate at least 1000 balanced alternative 4-way partitions.**
Produce **>= 1000** opponent partitions. Each opponent splits the SAME senses into 4 groups a
different way. Each opponent is **balanced** (4-way, comparable group sizes to the CAS partition).
These are the candidates that will compete against CAS.

**Step 5 — Keep only opponents that match the CAS partition within FROZEN tolerances.**
Measure each opponent on the same properties: within-class cohesion, between-class separation, word
frequency, token length, morphology. Keep an opponent ONLY if its measurable properties match the
CAS partition within tolerances that were **frozen in advance** (fixed before this step runs, not
tuned after). Discard opponents that fall outside tolerance. The survivors are the matched
opponent pool.

**Step 6 — Report where CAS falls in the surviving distribution (percentile).**
After the study is run (elsewhere, later), the CAS partition is placed inside the distribution of
the surviving matched opponents. Report the **CAS partition percentile**: where CAS sits relative
to opponents that are its equal on plain lexical properties. This percentile is the reported number.

## 5. The balanced-random control (mapping rule)

The balanced-random control is one specific kind of opponent. Its rule:

- Map each sense to one class **ONCE**.
- **Preserve** that mapping across every occurrence of the sense and across every data split.

Plain English: a sense keeps the same opponent-class assignment everywhere it appears. You do not
re-roll a sense's group from one occurrence to the next, and you do not re-roll it between train and
eval splits. This keeps the control honest: it varies the grouping, not the bookkeeping.

## 6. Opponent-pool timing rule (no cherry-picking)

**The opponent pool is built BEFORE any hidden-state result is opened.**

No human looks at the outcome and then picks the "best" opponent. The >= 1000 opponents, the frozen
tolerances, and the surviving matched pool are all fixed while the hidden-state numbers are still
sealed. Choosing an opponent after seeing results is forbidden. This rule is what makes the
percentile in Step 6 meaningful.

## 6b. Exact parameters (Phase 0C completion — CANDIDATE values, owner to freeze)

Before any claim-bearing run, every slot below must hold an exact frozen value. The
values marked PROPOSED are candidates I am putting forward for the owner's decision;
none is frozen until the owner signs it. None of these may change after hidden-state
results exist.

1. **Independent lexical resource:** PROPOSED — WordNet 3.1 (glosses + lexical
   relations). Never the target Qwen model in any form.
2. **Resource version and digest:** WordNet 3.1; sha256 = OWNER_TO_FREEZE in
   `SOURCE_RESOURCE_MANIFEST.json` before generation.
3. **Feature representation per sense:** PROPOSED — TF-IDF over lemmatized gloss terms
   + one-hot source frame + multi-hot thematic roles + log word frequency + token length
   + morphological complexity (character length and affix count under a frozen rule
   list). All from the frozen resource + frozen frequency source; nothing from Qwen.
4. **Similarity metric:** PROPOSED — cosine similarity on the Step-3 vectors.
   Cohesion = mean pairwise within-class cosine; separation = mean between-class
   centroid distance.
5. **Frequency source:** PROPOSED — a pinned release of the `wordfreq` package (exact
   version + digest recorded at freeze), log10 Zipf scale.
6. **Morphology representation:** PROPOSED — character length + counted affixes from a
   frozen affix list; no learned morphology model.
7. **Matching tolerances (per property, opponent vs CAS partition):** PROPOSED —
   |Δ within-class cohesion| <= 0.05; |Δ between-class separation| <= 0.05;
   |Δ mean log-frequency per class| <= 0.25; |Δ mean token length per class| <= 1.0;
   |Δ mean morphological complexity per class| <= 0.5. Frozen before generation; never
   widened after results.
8. **Partition-generation algorithm:** PROPOSED — seeded uniform balanced 4-way
   assignments (each sense assigned once, mapping preserved across occurrences and
   splits), search budget 200,000 candidate partitions, fixed seed list recorded.
9. **Minimum surviving matched partitions:** **200.** Fewer than 200 survivors from the
   preregistered search budget returns **`SCMPE_MATCHING_FAILED`**. Do not loosen
   tolerances after seeing model results — the study stops and the failure is recorded.
10. **CAS percentile gate (Claim B support):** PROPOSED — CAS must place at or above the
    **95th percentile** of the surviving matched-opponent distribution for the
    matched-semantic-control leg of Claim B. The exact percentile is an owner decision.
11. **Failure condition:** `SCMPE_MATCHING_FAILED` (see item 9) is a recorded negative
    outcome, never a license to re-tune.

## 7. Where SCMPE-v1 sits among the claims (context)

SCMPE-v1 supports one claim and does not by itself decide any claim. The claims are kept separate,
promoted only by a deterministic program reading, behind an owner-signed phase gate:

- **A — decodability**: can the CAS classes be read out at all, in a controlled CAS-generated domain
  (NOT unrestricted English).
- **B — incremental value over lexical + matched-semantic controls**: only claim B licenses the
  phrase "CAS-specific". SCMPE-v1 is the matched-semantic control that claim B is tested against.
- **C — causal intervention utility**.
- **D — learning benefit**.

Order rule: do NOT start Tier B until Tier A beats matched controls. The target model checkpoint MUST
NOT assign labels and MUST NOT generate protected evaluation items.

## 8. Compute placement

- Building SCMPE-v1 is deterministic dataset work. Deterministic source-verification and dataset
  scripts MAY run locally on CPU. This is not neural work.
- No local CPU neural workload.
- Remote models (Bedrock or other) may only PROPOSE (source location, criticism, counterexamples,
  paraphrases). Their output is non-authoritative. Bedrock is teacher / proposal language only.
- AWS GPU is for hidden-state extraction, probing, intervention, training, and protected eval. Those
  steps are not part of this generation spec.

## 9. Governance

Owner-signed phase approval. Deterministic claim promotion. No hook-based authorization. No
model-written claim status. Claude is NOT the research governor. This document is documentation only;
it establishes no CAS claim and grants no label authority. No model output alone has claim-bearing
label authority.
