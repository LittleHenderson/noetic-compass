# CONSTRUCTION_GOLD dataset — FROZEN generation law (four-Noetic restricted slice)

## Label authority (unchanged)

Labels are **CONSTRUCTION_GOLD** under the standing label-authority law:
1. the formal CAS operation exists FIRST;
2. a deterministic template generates the sentence;
3. an INDEPENDENT round-trip parser must recover the seed operation exactly;
4. failed round trips are EXCLUDED, never relabeled.

No LLM output alone has claim-bearing label authority. Models may later help with
paraphrase pools or adversarial probes, but raw model output never creates a
claim-bearing label; the deterministic engine issues labels under owner-approved
rules. NOTE (unresolved owner decision): `CAS_MAPPING_RULES_v1_CANDIDATE.yaml` in
`cas_sem_guided_plasticity_v1/labels/` is still AWAITING_OWNER_APPROVAL — until the
owner approves the mapping rules, everything generated here is a **CANDIDATE**
dataset and non-claim-bearing.

## Formal operation vocabulary (the restricted slice)

| Class | Formal op | Arity |
|---|---|---|
| `^2` | `attract(mind, idea)` | mind is drawn to idea |
| `^3` | `avert(mind, idea)` | mind withdraws from idea |
| `^6` | `decompose(idea, (p1, p2, p3))` | idea splits into exactly 3 parts |
| `^8` | `trigger(mind, idea_a, idea_b)` | idea_a brings idea_b to mind's mind |

## Passage law

- Each passage = **3–6 Ideas (clauses)**; each clause realizes exactly ONE formal op.
- Uniqueness constraints (so every question has exactly one gold answer): per
  passage, at most one `^2` per mind, one `^3` per mind, one `^6` per idea, one
  `^8` per (mind, idea_a).
- Every passage carries ONE question, deterministically answerable from the formal
  trace alone, over a CLOSED candidate set (all entities in the passage):
  - `Q_ATTRACT`: "Which idea was {mind} drawn to?" → the `^2` idea
  - `Q_AVERT`: "Which idea did {mind} withdraw from?" → the `^3` idea
  - `Q_PART`: "What is part {k} of {idea}?" → the k-th `^6` part
  - `Q_TRIGGER`: "What did {idea_a} bring to {mind}'s mind?" → the `^8` idea_b
- Question types cycle deterministically with the frozen 2:2:1:1 weighting
  (ATTRACT, AVERT, PART, ATTRACT, AVERT, TRIGGER) — attract/avert carry the
  clause-type-sensitive signal and get double weight.
- **Registered distractor law (surface-shortcut killer):** every passage contains a
  registered distractor for its question type — Q_ATTRACT adds a `^3` for the SAME
  mind (different idea); Q_AVERT adds a `^2` for the same mind; Q_PART adds a second
  `^6` on a different idea; Q_TRIGGER adds a second `^8` for the same mind with a
  different source and surfaced idea. Verified property: 100% of attract/avert items
  have ≥2 candidate ideas for the questioned mind, so bare entity co-occurrence is
  at chance between the confusable pair. Q_PART/Q_TRIGGER remain largely
  surface-solvable within their clause; results are reported per question type
  against the registered surface baseline (B0).
- **Question-surface note (recorded):** question wording is constant across splits
  (only passage surfaces and vocabulary are held out); the Q_ATTRACT wording shares
  "drawn" with `^2` family A, which appears only in train — a known, recorded
  characteristic of the family-shift design, not a split leak.
- Vocabulary bundles T, V, P have IDENTICAL shapes (6 minds, 8 ideas, 12 parts
  each), so entity-collision statistics match across splits.

## Surface realization

Each op class has **4 registered template families (A, B, C, D)** with distinct
syntax (`tools/generate_construction_gold.py` is the single registered source).
Family and vocabulary assignment implement the anti-leakage split law in
SPLIT_AND_PROTECTED_EVAL_SPEC.md: train = families {A,B} × vocab bundle T;
validation = family {C} × bundle V; protected = family {D} × bundle P. Held-out
therefore means BOTH unseen surface syntax AND unseen content vocabulary
(the registered defense against template-prefix memorization).

## Sizes (frozen)

- train: 6,000 passages (materialized locally: `data/candidate/train.jsonl`)
- validation: 1,000 passages (materialized locally: `data/candidate/val.jsonl`)
- protected: 1,000 passages (**NOT materialized in Gate 1A** — see
  SPLIT_AND_PROTECTED_EVAL_SPEC.md; content digest pre-registered in
  DATASET_MANIFEST_CANDIDATE.json)

## Determinism (Gate 1A.1 — amendment A1)

- Single frozen seed: `20260831` driving `exec/prng.HashPRNG` — a pure SHA-256
  counter stream with unbiased rejection sampling (no `random.Random` anywhere in
  claim-bearing generation). Regeneration is **byte-identical on every CPython
  ≥ 3.8 by construction**, which removes the owner-flagged cross-version
  dependency (candidate corpus generated under 3.14, training container under
  3.11) at the root. No wall-clock, no OS entropy.
- The Gate 1B AWS job regenerates all splits and MUST match every pre-registered
  digest before any evaluation (`DATASET_INTEGRITY_FAILURE` otherwise) — the
  digest gate remains as belt-and-suspenders.
- Protected derivation is either the public stream (integrity-only; the split is
  publicly reconstructible and is never called secret) or the owner-held salt
  path (`--protected-salt-hex`; commit-and-reveal — see
  SPLIT_AND_PROTECTED_EVAL_SPEC.md). Owner decision, open.

## Surface solvability (recorded fact, not a flaw)

The task is EXACTLY surface-solvable: the registered B1 parser (passage text +
question text only) scores `6000/6000` on train and `1000/1000` on val
(`SURFACE_BASELINES_CANDIDATE.json`). B1 is the task ceiling; B0 is the
class-blind floor (`0.6445` train / `0.6680` val). Any neural reading is bounded
by these two rows. The corpus occurrence audit
(`CANDIDATE_OCCURRENCE_AUDIT.json`) records that 17.4% (train) / 17.9% (val) of
answers first occur outside their target clause — the fact that forced the
context-free candidate-encoding rule.

## Record schema (JSONL, one passage per line)

All surfaces are lowercase in v1. Example (an actual generated record's shape):

```json
{"passage_id": "t000000", "split": "train",
 "seed_trace": [["^3", "mira", "jazz"], ["^2", "mira", "botany"], ["^6", "chess", ["wheels", "solos", "glazes"]]],
 "clauses": [{"text": "mira withdrew from jazz.", "op_index": 0},
             {"text": "botany pulled mira toward it.", "op_index": 1},
             {"text": "chess broke down into wheels, solos, and glazes.", "op_index": 2}],
 "text": "mira withdrew from jazz. botany pulled mira toward it. chess broke down into wheels, solos, and glazes.",
 "question": "which idea was mira drawn to?", "question_type": "Q_ATTRACT",
 "answer": "botany",
 "candidates": ["mira", "jazz", "botany", "chess", "wheels", "solos", "glazes"],
 "idea_labels": ["^3", "^2", "^6"], "template_families": ["A", "B", "A"],
 "vocab_bundle": "T"}
```

`idea_labels[i]` is the construction-gold class of clause i — the CAS stream's
ground truth. `clauses` preserves exact clause text so Gate 1B computes token spans
deterministically under the frozen tokenizer.

## Exclusion law

A passage failing the independent round trip
(`tools/independent_roundtrip_checker.py`) is EXCLUDED and counted in
`DATASET_MANIFEST_CANDIDATE.json.excluded_roundtrip`; the generator never edits a
label to make a round trip pass.
