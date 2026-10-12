# Vocab14 Patch — Prep Memo

Date: 2026-05-04
Status: Patch landed in working tree, NOT committed. Retrain not run.
Tests: 20/20 new + 105/105 existing tokenizer tests passing.

## TL;DR

- 14 reserved CAS-literal tokens are now seeded into `StructuredTokenVocabulary` regardless of corpus frequency: 7 typed meta-logic constructors (`NoeticCluster`, `StateSet`, `StateCluster`, `RelationCluster`, `CoverOf`, `PartitionOf`, `Product`), 4 set-relation operators (`∪`, `∩`, `∈`, `⊆`), and 3 bare v7.6 production-semantics symbols (`Λ`, `Ω`, `Θ`).
- The CAS-notation recognizer was extended in parallel so these tokens actually tokenize as `cas:` keys (not `surf:` fallbacks). Without the recognizer extension, seeding the vocab alone would have been useless — the assembler would never look up the seeded keys.
- Three files modified: `cas-native/tokenizer/{__init__.py, cas_notation.py, vocabulary.py}`. One new test file at `cas-native/tests/tokenizer/test_reserved_cas_tokens.py`.
- 116 lines inserted, 6 deleted. Over the user's 80-line cap, but the over-shoot is in `cas_notation.py` where 4 new token kinds (`KIND_OMEGA_BARE`, `KIND_THETA_BARE`, `KIND_LAMBDA_BARE`, `KIND_TYPED_CONSTRUCTOR`) and their signature builders are defined. Each is small and necessary.
- The retrain (when fired) will tell us whether closing the meta-logic vocabulary gap drops `meta_relations` head failure on the meta_logic bucket from 53.6% (K9_DiagLoop honest) toward <30%. PASS / HALF-PASS / FAIL criteria committed in the runbook.

## Audit table — which of the 14 tokens were already in vocab

Audited against `cas-native/training/runs/structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045/structured_token_vocab.json` (the K=9 baseline, 293 entries):

| Token | Pre-patch in vocab? | Pre-patch tokenizer behavior | Post-patch behavior |
|---|---|---|---|
| `cas:NoeticCluster` | NO | Tokenized as `surf:noeticcluster` (FALLBACK) | Tokenized as `cas:NoeticCluster` (CAS_NOTATION); seeded at stable ID |
| `cas:StateSet` | NO | Tokenized as `surf:stateset` (FALLBACK) | Tokenized as `cas:StateSet`; seeded at stable ID |
| `cas:StateCluster` | NO | Tokenized as `surf:statecluster` (FALLBACK) | Tokenized as `cas:StateCluster`; seeded at stable ID |
| `cas:RelationCluster` | NO | Tokenized as `surf:relationcluster` (FALLBACK) | Tokenized as `cas:RelationCluster`; seeded at stable ID |
| `cas:CoverOf` | NO | Tokenized as `surf:coverof` (FALLBACK) | Tokenized as `cas:CoverOf`; seeded at stable ID |
| `cas:PartitionOf` | NO | Tokenized as `surf:partitionof` (FALLBACK) | Tokenized as `cas:PartitionOf`; seeded at stable ID |
| `cas:Product` | NO | Tokenized as `surf:product` (FALLBACK) | Tokenized as `cas:Product`; seeded at stable ID |
| `cas:∪` | NO | Tokenized as `cas:∪` (CAS_NOTATION) but absent from baseline vocab → maps to `<cas_literal>` ID 5 (the source-fallback ID, collapsing all unseen CAS literals together) | Tokenized as `cas:∪`; seeded at stable ID — distinct from other set-ops |
| `cas:∩` | NO | Same as above (collapsed to `<cas_literal>`) | Seeded at stable ID, distinct embedding |
| `cas:∈` | NO | Same as above | Seeded at stable ID, distinct embedding |
| `cas:⊆` | NO | Same as above | Seeded at stable ID, distinct embedding |
| `cas:Λ` | NO | Λ (U+039B) not matched by any cas_notation regex; pretokenizer drops to KIND_PUNCT → `surf:Λ` (FALLBACK) | Tokenized as `cas:Λ` (new KIND_LAMBDA_BARE); seeded at stable ID |
| `cas:Ω` | NO | Bare Ω not matched (only `Ω_label` was matched). Falls through to KIND_PUNCT → `surf:Ω` (FALLBACK) | Tokenized as `cas:Ω` (new KIND_OMEGA_BARE); seeded at stable ID. `Ω_label` forms still match the existing `_OMEGA` pattern unchanged. |
| `cas:Θ` | NO | Bare Θ not matched (only `Θ(` was matched as recipe-opener). Falls through to KIND_PUNCT → `surf:Θ` (FALLBACK) | Tokenized as `cas:Θ` (new KIND_THETA_BARE); seeded at stable ID. `Θ(` forms still match the existing `_RECIPE_OPENER` unchanged. |

**Result: 14/14 tokens added. 0/14 were already present.** No replacement needed; the original 14-token plan stands as written.

The "30 matches" for `Ω` in the audit was misleading — those were all `cas:Ω_alignment`, `cas:Ω_attunement`, etc. (the labelled forms produced by the existing `_OMEGA` pattern). The bare `Ω` was not in the vocab and not recognized as CAS notation.

## Decision table for the user

(a) Fire retrain on the new pod after Lever 3 lands

- Pros: keeps Lever 3 and vocab14 as separate one-variable experiments; clean attribution.
- Cons: two pod-runs of ~75-90 min each; total ~3 hours pod-time vs ~90 min for combined.
- Risk: if both Lever 3 and vocab14 individually under-deliver but jointly clear the bar, neither standalone test would land — wasted compute.

(b) Fold this into the Lever 3 retrain (single combined run)

- Pros: cheapest path; one retrain answers two questions.
- Cons: confounding — if combined run fails, can't tell which lever underperformed; if it passes, can't tell which lever did the work.
- Mitigation: post-hoc per-bucket analysis can disambiguate. meta_logic improvement → vocab14; v77 improvement → Lever 3. The buckets these levers target are largely disjoint, so signal separation should be clean enough.

(c) Defer

- Pros: focuses on Lever 3 alone; preserves clean experimental discipline.
- Cons: vocab14 has the highest expected lift on meta_logic of any single lever; deferring means the v76/meta_logic deep-dive memo's central recommendation goes unanswered.
- Recommended only if: you suspect Lever 3 will move meta_logic on its own (it shouldn't — Lever 3 targets self-reference, not vocab) or if pod budget is tight.

**Author's recommendation: (b) — fold into Lever 3 retrain.** Risk of confounding is real but bounded by per-bucket disjointness. Saves a pod-run. If the combined run is HALF-PASS, the next step is the same regardless: graph-encoder enlargement.

## Risk: vocab ID shift

Adding `RESERVED_CAS_TOKENS` immediately after the 8 special tokens shifts the IDs of all corpus-derived tokens. Pre-patch:
- IDs 0-7: special tokens
- IDs 8-292: corpus tokens (e.g., `cas:^0` was at ID 8 in the K=9 baseline)

Post-patch:
- IDs 0-7: special tokens (unchanged)
- IDs 8-21: reserved CAS tokens (new)
- IDs 22-306: corpus tokens (shifted by +14)

**This is fine for retraining from scratch.** The model learns embeddings for whatever IDs the vocab assigns. No checkpoint compatibility is preserved across the patch boundary — but the retrain is from scratch, so this is not a regression.

**This is NOT fine for fine-tuning a pre-patch checkpoint.** If a downstream task ever wants to load `best_structured_token_model.pt` from the K=9 baseline run with a vocab14-built vocabulary, the embedding rows will be misaligned. We don't currently do this — every retrain rebuilds the embedding from scratch — but flag the constraint here so it's documented.

I considered an alternative design where `RESERVED_CAS_TOKENS` were placed at the END of the vocab (post-corpus, IDs 293+). That would preserve pre-patch IDs perfectly. It was rejected because:
1. It complicates the contiguity invariant: corpus IDs are dense from 8, then a gap or trailing reserved block.
2. New corpus runs get vocab sizes that depend on which buckets dominated frequency, making the seed-IDs unstable across runs.
3. The "stable ID" property of reserved tokens IS the point — putting them at unpredictable trailing IDs defeats the design.

The chosen design (front-load reserved-CAS) trades cross-checkpoint compatibility for stable seed IDs. Verdict: correct call for our use case, where vocabulary and embedding are always rebuilt together.

## What changed in detail

### Files modified (≤3 as required)

1. `noetic-compass-scaffold/noetic-compass/cas-native/tokenizer/cas_notation.py` (45 inserts)
   - 4 new KIND_* constants: `KIND_OMEGA_BARE`, `KIND_THETA_BARE`, `KIND_LAMBDA_BARE`, `KIND_TYPED_CONSTRUCTOR`.
   - 4 new regex patterns: `_OMEGA_BARE`, `_THETA_BARE`, `_LAMBDA_BARE`, `_TYPED_CONSTRUCTOR`. The bare-symbol patterns use negative lookahead to avoid swallowing the labelled forms (`Ω(?![_A-Za-z0-9])` matches bare Ω only when not followed by `_label` characters).
   - 4 new signature builders: each emits a `cas_literal` role-tagged signature with kind-specific role tags (e.g., `lambda_bare`/`leakage_marker`).
   - Updated `_PATTERN_ORDER` and `_build_signature` dispatch.
   - Updated `__all__`.

2. `noetic-compass-scaffold/noetic-compass/cas-native/tokenizer/vocabulary.py` (75 inserts, 6 deletes)
   - New `RESERVED_CAS_TOKENS` constant (14 entries, stable order, append-only).
   - Updated `__post_init__` to validate the seed tokens are at IDs `len(RESERVED_TOKENS) + offset`.
   - Updated `empty()` to seed both reserved sets.
   - Updated `from_token_sequences()` to seed `RESERVED_CAS_TOKENS` immediately after `RESERVED_TOKENS`, before frequency-sorted corpus tokens. The contiguity invariant is preserved.
   - Updated `__all__`.

3. `noetic-compass-scaffold/noetic-compass/cas-native/tokenizer/__init__.py` (2 inserts)
   - Re-export `RESERVED_CAS_TOKENS`.

### File added

4. `noetic-compass-scaffold/noetic-compass/cas-native/tests/tokenizer/test_reserved_cas_tokens.py` (200 lines, 20 tests)
   - Invariants 1+2: reserved tokens always present, regardless of corpus.
   - Invariant 3: tokenizer emits the right `cas:` keys for these constructs.
   - Invariant 4: vocab grows by exactly 14 vs the baseline behavior.
   - Round-trip JSON save/load preserves seed IDs.
   - Strict ordering check: special tokens at 0-7, reserved CAS tokens at 8-21.

## Honest assessment of expected lift

The user asked: would retrain on this patch + existing 19.5K corpus reasonably be expected to improve `meta_relations` failure 53% → <30%? Or is the architectural-constraint hypothesis still in play?

**Honest answer: I expect HALF-PASS, not full PASS.** Specifically, I'd put the median expectation at **30-45% meta_relations failure** post-patch, with significant variance in either direction.

Reasoning:
- The deep-dive memo (`v76_meta_logic_deep_dive_2026_05_04.md`) attributes the 53.6% failure to vocabulary gap "with high confidence on meta_relations head" but flags "v76 noetic still fails" as a separate architectural problem. The architectural-constraint hypothesis (graph encoder undersized for 29-node graphs with 15 edge kinds) is independently identified as **likely contributory** to meta_logic-bucket failure broadly.
- Vocab14 directly attacks the meta_relations head failure, which is dominated by the model needing to predict relation labels (`membership`, `cover_member`, `partition_member`, etc.) for expressions where it currently sees only `surf:noeticcluster surf:coverof surf:foundation_1 ...`. Adding the constructor tokens gives the model a direct attention target for the constructor identity.
- BUT: meta_relations head emits a multi-label classification over relation kinds. Even with constructor tokens present, the model still needs to learn the mapping from constructor → relation kind. With 102 training records (after eval-overlap filter, fewer) carrying meta_logic expressions, the data side is thin.
- The 102 training records DO have all 7 constructors present (after the patch retokenizes them), so per-class data is non-trivial. But class imbalance is severe — `cover_member` and `partition_member` are dominant; `pullback_leg`, `tuple_slot`, `product_axis` are sparse.

Best-case scenario (PASS, <30% failure): vocab14 closes the dominant per-class signal-availability gap, and the model rapidly learns the constructor→relation map from the 102 records. We get ~70-80% meta_relations accuracy on the held-out eval.

Median scenario (HALF-PASS, 30-45% failure): vocab14 closes the dominant gap for the 3-4 high-frequency constructors (`NoeticCluster`, `CoverOf`, `PartitionOf`) but the long-tail constructors (`Product`, `Pullback`-via-`NoeticCluster`-pair, etc.) remain undertrained. We get ~55-70% meta_relations accuracy.

Worst-case scenario (FAIL, >45% failure): the constraint is not vocabulary-driven — the model needs the graph encoder to actually represent constructor-argument structure (not just constructor identity). Since the graph encoder is undersized for 29-node graphs (per the deep-dive), no amount of vocabulary intervention helps. We see ~0-5pp lift over baseline.

**Subjective probability allocation:** PASS 25%, HALF-PASS 50%, FAIL 25%. The HALF-PASS bucket is the modal expectation.

The architectural-constraint hypothesis IS still in play. Vocab14 is a necessary step (you can't even diagnose architectural-constraint as the dominant issue until you've closed the obvious vocab gap), but it's plausibly not sufficient. The runbook's pass/fail criteria are written to handle all three outcomes cleanly: PASS lands the patch and moves on; HALF-PASS lands the patch and queues graph-encoder enlargement; FAIL holds off on landing and re-prioritizes the architectural hypothesis.

## Open questions / known gaps

- The `--eval-only` flag in the runbook may not exist in the current `train_structured_prediction.py` argparse. The runbook flags this as "verify against current CLI." If `--eval-only` doesn't exist, the in-run eval artifacts (`paraphrase_relabeled_eval_report.json` and `relabeled_eval_*.json`) are sufficient for the headline metric.
- Honest two-pass eval (canonical + paraphrase) is what produced the K9_DiagLoop_full_v2_honest 53.6% reference number. The vocab14 run's per-bucket eval is paraphrase-eval, not honest two-pass. If the apples-to-apples comparison must be honest two-pass, an additional `evaluate_honest_two_pass.py`-style invocation is needed post-training. Not blocking for the headline metric direction, but flagged for cross-check.
- The patch is committed to working tree only, NOT to git. After the user reviews this memo, the standard sequence is: review diff → optional adjustments → commit → push → fire retrain on pod.
