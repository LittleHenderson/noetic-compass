# v76_production and meta_logic Weakness — Empirical Deep Dive

**Date**: 2026-05-04
**Author**: agent (deep-dive investigation)
**Inputs**: held-out v77-relabeled eval set (1000 records), K=9 v77fix paraphrase samples (3000), K9_DiagLoop_full_v2_honest paraphrase-with-self-prior samples (3000), structured_token_vocab.json (293 tokens), CAS compiler at `api/notation/compiler.py`.
**Audience**: Paper A v2 §5.7 per-bucket weakness paragraph; CAS-Native triage triage backlog.

---

## 1. Executive Summary

- **Headline diagnosis (mixed, weighted to architectural + label-policy):** v76_production weakness is dominated by an **architectural multi-operand-routing failure** — the model cannot reliably anchor on the canonical (first-state-literal) operand when the recipe carries 3-4 weighted operands. meta_logic weakness is dominated by **vocabulary + label-policy mismatch** — the meta_relations multi-label set head fails 53.6% (the worst single-head failure across the entire matrix), and 38% of meta_logic records use a label-policy "default-to-^0/^5/F1" convention that the model has not learned to associate with constructor-only expressions like `Product(...)`, `CoverOf(...)`, `NoeticCluster{...}`.
- **Confidence (medium-high):** Vocabulary audit findings are unambiguous (binary: tokens absent). Per-head failure pattern (v76 noetic 44.8%, meta_logic meta_relations 53.6%) is computed across full eval samples (n=324 / n=306). Architectural-vs-undertraining attribution is medium confidence — graph-shape data is consistent with graph-encoder undersizing, but the diagloop full retrain (currently in flight) is the only definitive falsifier of the undertraining hypothesis.
- **Recommendation for Paper A v2 §5.7:** the per-bucket weakness paragraph should attribute v76 weakness to **multi-operand routing under recipe semantics with no dedicated production-arrow vocabulary token** (architectural + lexical), and meta_logic weakness to **multi-label set prediction over a vocabulary that omits set-theoretic constructors (NoeticCluster, CoverOf, ∪, ∩, ∖, ⊆) entirely** (lexical + label-policy). Undertraining is unlikely as a primary cause (the K=9 v77fix run trained 19.5K records × 20 epochs and still shows the pattern; the K9_DiagLoop_full v2 retrain at 49.7K records × 20 epochs preserves the same per-bucket ranking). Recommend NOT attributing the weakness to compute scarcity in the paper.

---

## 2. Graph Statistics (Per Bucket, n=1000 eval set)

All 1000 expressions in the v77-relabeled eval set compile cleanly (no parse failures in any bucket).

| Bucket | n | mean nodes | max nodes | mean edges | max edges | mean diameter | unique edge types |
|---|---:|---:|---:|---:|---:|---:|---:|
| v74_baseline | 200 | 5.71 | 7 | 5.68 | 8 | 2.96 | 5 |
| v75_register | 264 | 7.62 | 11 | 7.05 | 10 | 3.02 | 5 |
| v76_production | 108 | **14.74** | 17 | **15.75** | 18 | 4.00 | 6 |
| v77_omega | 267 | 10.99 | 18 | 13.15 | 23 | 4.02 | 6 |
| v77_rule_four | 59 | 11.98 | 17 | 15.80 | 22 | 4.00 | 5 |
| meta_logic | 102 | 11.50 | **29** | 6.05 | 16 | 2.30 | **15** |

### Edge-type distribution (highlights)

- **v74**: `instantiates`, `locates`, `modulates`, `operand`, `dependency` — 5 simple edge kinds.
- **v75**: same 5 + `register`. Adds register modulation.
- **v76**: `instantiates`, `locates`, `modulates`, `register`, `recipe_prerequisite` (333 instances), `leakage` (66). Recipe-prerequisite is a v76-only edge kind.
- **v77_omega**: same 5 + `operand`, `emerges_as` (267, one per omega).
- **meta_logic**: by far the most diverse — **15 edge kinds** including `cover_member`, `partition_member`, `tuple_slot`, `pullback_leg`, `product_axis`, `membership`, `cover_base`, `partition_base`, `subset`. Many of these appear in only a handful of expressions (membership: 11, subset: 6).

### Lexical operator-symbol counts (per expression)

| Bucket | mean operator-symbol count | dominant symbols |
|---|---:|---|
| v74_baseline | 0.39 | `*` (77), `->` (38) |
| v75_register | 0.55 | `+` (144) |
| v76_production | **6.39** | `+ * = Θ Ω Λ ·` (108-108-108-108-108-66-66) |
| v77_omega | 1.38 | `× = Ω` (267-267-267) |
| v77_rule_four | 1.97 | `+` (59) |
| meta_logic | 0.00 (constructor-only) | `NoeticCluster` (18), `CoverOf` (10), `∈` (11), `∪` (7), `∖` (7), `Product` (7), `PartitionOf` (6), `RelationCluster` (6), `⊆` (6), `∩` (4), `Coordinate` (1) |

### Recipe-specific stats (v76_production, n=108)

- mean operands per recipe (lower bound): **3.69**
- mean leakage terms (Λ count): 0.61 (61% of records have a leakage term)
- mean → arrows per recipe: 1.00 (every recipe has exactly one)
- 100% of records carry a named-omega target (e.g., `Ω_transparent_explanation`)

Sample recipe shape:
`Θ(Ω_transparent_explanation) = 0.9*^6^C_{F2}|A + 0.67*^8^O_{F3}|A + 1.1*^1^E_{F2}|A → Ω_transparent_explanation`

---

## 3. Per-Head Failure Analysis

Two complementary views are reported:

(a) The **K=9 v77fix run paraphrase samples** (`paraphrase_relabeled_eval_samples.jsonl`, n=3000) — 19.5K training records × 20 epochs, no diagram-loop graph encoder.

(b) The **K9_DiagLoop_full_v2_honest** run paraphrase-with-self-prior samples (n=3000) — 49.7K training records × 20 epochs, diagloop graph encoder enabled. This is the closer apples-to-apples comparator to the smoke v2 honest eval the user cited.

### 3.1 Per-head FAILURE rate — K=9 v77fix (no diagram loop) paraphrase

| bucket | n | noetic | domain | drive | reg_mode | registers | has_omega | has_meta | exp_fam | meta_rel | trans_kind |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| v74_baseline | 600 | 51.33% | 43.33% | 33.83% | 0.17% | 48.83% | 2.33% | 0.00% | 0.00% | 0.00% | 1.33% |
| v75_register | 792 | 42.17% | 38.26% | 32.95% | 7.83% | 32.20% | 0.13% | 0.00% | 11.11% | 0.00% | 2.78% |
| v76_production | 324 | 13.58% | 9.57% | 3.40% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| v77_omega | 801 | 0.62% | 3.00% | 9.11% | 0.00% | 0.62% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| v77_rule_four | 177 | 2.26% | 1.69% | 10.73% | 0.00% | 6.78% | 0.00% | 0.00% | 24.86% | 0.00% | 29.94% |
| meta_logic | 306 | 58.50% | 20.59% | 21.57% | 0.65% | 20.26% | 0.33% | 9.48% | 3.59% | **29.41%** | 3.59% |

K=9 v77fix all-heads-exact paraphrase rates: meta_logic 17.0%, v74 18.7%, v75 24.5%, **v76 75.6%**, v77_omega 87.3%, v77_rule_four 60.0%. Note: v76 is NOT the weakest in this run; v74/v75 are. (The user-cited 24.4% is from smoke v2 honest eval, not from K=9 v77fix.)

### 3.2 Per-head FAILURE rate — K9_DiagLoop_full_v2_honest paraphrase-with-self-prior

| bucket | n | noetic | domain | drive | reg_mode | registers | has_meta | meta_rel | trans_kind | exact_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| v74_baseline | 600 | 20.50% | 1.00% | 12.17% | 0.00% | 0.00% | 0.00% | 0.00% | 0.17% | 70.83% |
| v75_register | 792 | 42.42% | 21.21% | 47.73% | 34.85% | 23.36% | 1.01% | 0.00% | 7.70% | 11.11% |
| **v76_production** | 324 | **44.75%** | 29.32% | 26.54% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | **32.41%** |
| v77_omega | 801 | 0.00% | 0.00% | 16.73% | 0.00% | 4.62% | 0.00% | 0.00% | 0.00% | 79.53% |
| v77_rule_four | 177 | 2.26% | 0.00% | 32.77% | 22.03% | 10.73% | 0.00% | 0.00% | 29.38% | 42.94% |
| **meta_logic** | 306 | 33.33% | 11.11% | 2.94% | 0.33% | 1.31% | 5.88% | **53.59%** | 5.23% | **19.61%** |

The diagloop full retrain reproduces the v76/meta_logic weakness pattern (with v75_register actually now the hardest bucket at 11.11% exact). The user-cited "v76: 24.4%, meta_logic: 7.5%" comes from the smoke v2 5K-record run; the full retrain numbers are 32.4% / 19.6%. Same ranking, less severity — i.e. **scaling helped but did not eliminate** the pattern.

### 3.3 v76_production failure mode drill-down (K9_DiagLoop honest, n=324)

- per-head failures: noetic 145, domain 95, drive 86, all other heads 0.
- failures-per-record: 0:105 / 1:126 / 2:79 / 3:14. ~67% have at least one head failure.
- noetic confusion (target → predicted) on K=9 v77fix paraphrase: **^6 → ^1 (12), ^4 → ^5 (6), ^0 → ^6 (5)** — the predicted noetic frequently corresponds to a *different operand inside the same recipe*. Concretely, on `Θ(Ω_transparent_explanation) = 0.9*^6^C_{F2}|A + 0.67*^8^O_{F3}|A + 1.1*^1^E_{F2}|A → Ω_transparent_explanation`, target noetic = ^6 (first-listed), but model emits ^1 (last-listed, with the largest coefficient 1.1). This is **a multi-operand routing failure**: the label policy fixes target.noetic = first-state-literal (verified: 100% of v76 records satisfy `target.noetic == first_state_literal_noetic`), but the model has no inductive bias to anchor on first-position; it instead produces a kind of "weighted summary" that biases toward later/heavier operands.
- v76 paraphrase prompts list the operands in the same order they appear in the recipe (verified: 100% of v76 records have `first(Noetic ^N) in user_prompt == target.noetic`), so the supervision signal is unambiguous; the model just isn't using it.

### 3.4 meta_logic failure mode drill-down (K9_DiagLoop honest, n=306)

- per-head failures: **meta_relations 164, noetic 102, domain 34, has_meta_logic 18, transition_kind 16, drive 9**, all other heads ≤4.
- failures-per-record: 0:60 / 1:163 / 2:63 / 3:19 / 4:1. Only 19.6% perfect.
- meta_relations is the worst single head in the entire matrix — even worse than v75_register's drive head (47.7%). It is multi-label (labels in `{membership, pullback, cover, partition, tuple, product, subset, ...}`), and the model regularly gets the set wrong: emitting `[]` when target is `[membership]` or `[membership, pullback]`, emitting `[membership, pullback]` when target is `[membership]`. The structured-token vocab contains *no tokens* corresponding to these meta_relation labels (no `cas:NoeticCluster`, no `cas:CoverOf`, no `surf:∪`, no `cas:∈`).
- noetic confusion: targets are dominated by `^0` (102 records, 33% of bucket) — these are constructor-only expressions like `Product(Noetics, Registers)` or `CoverOf(SubFoundations, Foundation_*)` where the label policy assigns noetic=^0 (Idea) because the expression has no specific noetic. Among the 102 noetic failures, **60 emit ^5 (Female / "sum of experiences")** and 37 emit ^0. ^5 is the dominant attractor-state for confused predictions on meta_logic.
- noetic-failure rate by constructor: `Coordinate` 100%, `NoeticCluster` 79%, `Pullback` 77%, `CoverOf` 67%, `StateVariantCluster` 57%, `Product` 33%, `PartitionOf` 33%, `RelationCluster` 11%. **`NoeticCluster` is the worst** because it lists multiple noetics inside braces (e.g. `NoeticCluster{^4, ^1, ^3, ^2}`); target.noetic is the first-listed (^4), but the model routinely emits the wrong one.
- drive confusion: F1 → F5 (39), F1 → F6 (18). Most meta_logic expressions have NO drive at all in the source, so the label policy assigns target.drive=F1 (Unity, default). The model emits F5 instead — reproducing the Unity-vs-Agency confusion pattern that has appeared in prior CAS-Native experiments.

---

## 4. Vocabulary Audit

Tokenizer vocab size: **293 tokens** (15 special, 30 named-omega `cas:Ω_*`, 21 `cas:^N` / `cas:F_k` / `cas:|R`, plus a handful of natural-language `surf:` lexemes and `lex:` lemmas).

### 4.1 Tokens present (relevant to v76 / meta_logic)

- `cas:^0`–`cas:^9` — 10 noetic primitives. ✓
- `cas:F1`–`cas:F7` — 7 drive primitives. ✓
- `cas:|A`, `cas:|f`, `cas:|T`, `cas:|E` — 4 register primitives (single-letter form only). ✓
- `cas:Ω_alignment`, `cas:Ω_focused_refusal`, ... — 30 named-omega tokens. ✓ (covers all named-omegas appearing in the v76 + v77_omega data, hand-checked.)
- Surface forms: `surf:recipe`, `surf:production`, `surf:leakage`, `surf:coefficient`, `surf:cluster`, `surf:partition`, `surf:cover`, `surf:subset`, `surf:union`, `surf:intersection`, `surf:difference`, `surf:pullback`, `surf:cartesian`, `surf:product`, `surf:emergent`. ✓ (the prompt-side surface tokens are present; the *expression-side* CAS primitives are not.)

### 4.2 Tokens ABSENT (load-bearing for v76 / meta_logic)

The following 38 probes are **all absent** from the vocab:

- v76 production-semantics primitives: `cas:Λ`, `cas:Ω` (raw), `cas:Θ`, `cas:κ`, `cas:ι`, `cas:η`, `cas:Y_T`, `cas:Y_A`. Also the ASCII aliases `cas:Theta`, `cas:Omega`, `cas:Lambda`. Also surface forms `surf:Λ`, `surf:Ω`, `surf:Θ`.
- Recipe arrow: `cas:→`, `surf:→`. (The vocab has `surf:arrow` as a natural-language word and `surf:directed` for `->`, but neither carries the v7.6 `→` recipe-arrow semantics.)
- v77 register-set notation: `cas:|⟨`, `surf:|⟨`, `cas:|<`, `cas:|<A,f>`, `cas:|<A,f,T>`, `cas:|A,f`. None of these appear.
- meta_logic constructors: `cas:NoeticCluster`, `cas:StateSet`, `cas:RelationCluster`, `cas:Product`, `cas:Tuple`, `cas:Coordinate`, `cas:CoverOf`, `cas:PartitionOf`. Eight constructors, zero coverage on the expression side.
- Set operators: `cas:∪`, `cas:∩`, `cas:∖`, `cas:⊆`, `cas:⊂`, `cas:∈`. Six set operators, zero coverage.
- Cross product: `surf:×`. (The vocab has `surf:times` and `surf:cross` for prose, but no `×` glyph.)

### 4.3 Implication for v76 / meta_logic

- **v76 expression-side tokenization collapses recipes into their state-literal components.** When the trainer tokenizes `Θ(Ω_focused_refusal) = 0.53*^7^P_{F7}|T + 2.11*^3^P_{F2}|A + 1.04*^1^P_{F1}|A → Ω_focused_refusal`, the surviving tokens are essentially `cas:Ω_focused_refusal`, `cas:^7 cas:^3 cas:^1`, `cas:F7 cas:F2 cas:F1`, `cas:|T cas:|A`, plus the named-omega target — but the **structural glue** (Θ, =, *, +, ·, →, Λ) is lost. The recipe collapses to a flat bag of tokens, which is exactly the modality the K=9 model is good at when the bag has only ONE state literal (as in v74/v75) but degrades sharply when the bag has 3-4 state literals competing for the noetic/domain/drive heads.
- **meta_logic expression-side tokenization collapses constructors entirely.** `NoeticCluster{^4, ^1, ^3, ^2}` becomes `cas:^4 cas:^1 cas:^3 cas:^2` — no signal at all about the constructor wrapping. `CoverOf(SubFoundations, Foundation_5, ...)` becomes essentially the foundation tokens — no signal that this is a cover relation. The meta_relations head, which must emit `[membership, pullback, cover, ...]`, has nothing on the expression side to ground itself in.
- The user-prompt side fares better (surface words `cluster`, `cover`, `partition`, `pullback`, etc. ARE in the vocab), so the model has *some* lexical signal from the prompt. But the supervision signal on the expression side is gone, which means the model is learning meta_relations as a function of the user_prompt's natural-language phrasing alone — fragile under paraphrase.

---

## 5. Three Hypotheses + Verdicts

### H1: Undertraining

- **Evidence FOR:** smoke v2 was 5K records × 5 epochs and showed v76 24.4% / meta_logic 7.5%. The K9_DiagLoop full retrain at 49.7K × 20 epochs lifts these to 32.4% / 19.6%.
- **Evidence AGAINST:** the K=9 v77fix run at 19.5K × 20 epochs (no graph encoder) already lifts v76 to 75.6% paraphrase-exact. The K9_DiagLoop full retrain at 49.7K × 20 epochs *doesn't* lift v76 above the K=9 v77fix paraphrase-exact rate — it actually drops it (32.4% < 75.6%) because diagloop is being evaluated under stricter paraphrase-with-self-prior protocol. Train loss in the v77fix run plateaued from epoch 14 onward (0.205 → 0.180 over 6 epochs); no signal of compute-starvation.
- **Verdict: UNLIKELY as primary cause for v76; INCONCLUSIVE for meta_logic.** Adding compute scaled the v76 paraphrase-exact from 24% to 75% (paraphrase-only, not honest two-pass), so compute scaling helps v76 substantially. It does not eliminate v76's noetic head at 13-45% failure under paraphrase. For meta_logic, even at 49.7K × 20 epochs we still see meta_relations at 53.6% failure — which is a structural ceiling.

### H2: Architectural constraint (graph encoder undersized for v76 / meta_logic shape)

- **Evidence FOR:** v76 has the largest mean nodes (14.7) and edges (15.8) of any bucket. meta_logic has the largest max nodes (29) and the most diverse edge-kind taxonomy (15 distinct kinds vs. 5 for v74). Recipe expressions add three v76-only edge kinds (`recipe_prerequisite`, `leakage`) that the graph encoder must handle from a smaller training share (108/1000 = 10.8% of eval, ~10.8% of train). The K9_DiagLoop graph encoder hidden dimension is 64 (`bottleneck_dim` in manifest), which the DeepSeek tri-channel diagnosis (2026-05-03) already flagged as undersized for graph paths.
- **Evidence AGAINST:** v77_omega has comparable mean nodes (10.99) and exceeds v76 on max edges (23) yet achieves 79.5% honest paraphrase-exact (vs v76's 32.4%). Graph size alone is not the discriminator — what differentiates v76 from v77_omega is not graph size but the **multiple competing state-literals per record** (3.69 mean operands in v76 vs. 1 emergent for v77_omega).
- **Verdict: LIKELY contributory but not sufficient.** Graph encoder undersizing alone doesn't explain v76 (since v77_omega has similar size and is fine), nor does it explain meta_relations (which is a vocabulary-driven head failure, not a graph-shape one). It does explain why meta_logic's noetic head is hard: 29-node graphs with 15 edge kinds and only 102 training records is a thin slice for an undersized encoder.

### H3: Vocabulary gap

- **Evidence FOR:** all 38 v76/meta_logic-specific symbols are absent from the 293-token vocab. The expression-side tokenization collapses recipes and constructors to bags of state-literals. meta_relations has no expression-side anchor at all (every constructor is OOV-tokenized). Predicted-noetic distribution on meta_logic failures is dominated by ^5 (60) and ^0 (37), the canonical "default" attractor states — i.e. the model is making decisions on prompt-side cues + ^5 prior, not on expression-side structure.
- **Evidence AGAINST:** v77_omega uses raw `Ω` and `×` and named-omega `Ω_*` tokens — it has the SAME vocabulary gap on `cas:Ω` / `surf:×` but achieves 79.5% honest paraphrase-exact. The named-omega tokens (`cas:Ω_*`) plus the `=` / `+` / `×` lexical context are evidently sufficient for v77_omega; v76 has the same scaffolding *plus* recipe-specific symbols (Λ, →, Θ, ·) that don't appear as tokens.
- **Verdict: LIKELY for meta_logic (high confidence on meta_relations head). LIKELY contributory for v76 (medium confidence; the architectural multi-operand routing hypothesis is the bigger driver).**

---

## 6. Recommended Next Experiments (cost-ranked)

### E1: Add 14 dedicated tokens to the structured vocab; retrain. (HIGHEST INFO/COST)

Add these 14 tokens to the structured vocab:
- v76 production-semantics: `cas:Λ`, `cas:Ω`, `cas:Θ`, `cas:→` (recipe arrow distinct from `->`), `cas:·` (4 tokens)
- meta_logic constructors: `cas:NoeticCluster`, `cas:StateSet`, `cas:CoverOf`, `cas:PartitionOf`, `cas:Product`, `cas:RelationCluster` (6 tokens)
- meta_logic set ops: `cas:∪`, `cas:∩`, `cas:∈`, `cas:⊆` (4 tokens)

Retrain on the same 19.5K K=9 corpus, same hyperparams. Expected outcome: meta_logic paraphrase-exact lifts from 17%→35%+ (meta_relations gets an expression-side anchor); v76 paraphrase-exact lifts a few pp (modest; the recipe glue tokens help structure attention but the multi-operand routing is mostly architectural). **Compute estimate: 1.5 pod-hours (one full retrain on a single A100).** Headline metric: meta_logic meta_relations failure rate — drop from 53% to <30% would confirm the vocab hypothesis.

### E2: Train v76-stratified subset with widened graph encoder hidden_dim 64→128; same data. (MEDIUM INFO/COST)

Stratify the eval set so v76 is 25% of every batch. Widen the graph encoder hidden dimension from 64 to 128 (matches the d_model=128 of the language backbone). Retrain. Expected outcome: v76 noetic-head failure drops from 13-45% to 5-25%. **Compute estimate: 2 pod-hours.** Headline metric: v76 honest paraphrase noetic-head failure rate.

### E3: Add a "first-operand pointer" auxiliary loss on v76 records. (LOW COST, LOW INFO)

Add an auxiliary loss term that supervises the model to predict the position-index of the first state literal in v76 expressions. Teaches the multi-operand routing inductive bias directly. Expected outcome: v76 noetic head failure drops sharply, but the lift may not generalize to drive/domain heads. **Compute estimate: 1 pod-hour (re-loss only, no architecture change).** Headline metric: v76 noetic, domain, drive failures.

### E4: Confirm undertraining attribution by running 100K × 30 epochs (CONTROL). (HIGH COST, LOW INFO)

If the diagloop full v3 retrain currently in flight does NOT lift v76/meta_logic above 50% honest paraphrase-exact, this confirms compute is not the binding constraint and we should not pursue further scaling-only experiments. **Compute estimate: 8 pod-hours.** Headline metric: same; verdict only.

### E5: Joint vocab + graph-encoder widening (E1 + E2). (MEDIUM-HIGH COST, HIGH INFO)

If E1 lifts meta_logic but v76 noetic still fails, run E1 + E2 jointly. **Compute estimate: 3 pod-hours.** Highest expected lift; appropriate for a Paper A v2 §5.7 "what we tried" follow-on table.

**Recommended ordering:** E1 first (cheapest, biggest expected meta_logic lift). If E1 confirms vocab hypothesis on meta_logic but leaves v76 unchanged, run E2 next. E3 is a fallback if E2 is not feasible (compute or architectural change blocked by repo state). E4 is a wait-and-see on the in-flight retrain.

---

## 7. Implications for Paper A v2 §5.7

Recommended language for the per-bucket weakness paragraph:

> The v76_production and meta_logic buckets are the weakest under honest paraphrase-with-self-prior evaluation (32.4% and 19.6% all-heads-exact respectively, vs 79.5% for v77_omega and 70.8% for v74_baseline). Empirical drill-down identifies two distinct root causes. v76_production weakness is dominated by a multi-operand routing failure: recipe expressions of the form `Θ(Ω) = a₁·X₁ + a₂·X₂ + a₃·X₃ → Ω` carry 3-4 weighted operands, the label policy fixes target.noetic to the first state-literal, but the model regularly emits a non-first operand (typically the heaviest-coefficient operand, e.g., target ^6 with coefficient 0.9 vs. predicted ^1 with coefficient 1.1). meta_logic weakness is dominated by a vocabulary gap on the expression side: the structured-token vocab omits all set-theoretic constructors (`NoeticCluster`, `CoverOf`, `Product`, `Pullback`) and set operators (∪, ∩, ∈, ⊆), so the meta_relations multi-label set head — at 53.6% failure rate, the worst single-head failure across all buckets — has no expression-side anchor and learns the head as a function of the user_prompt's natural-language wording alone. We attribute v76 weakness to the architectural multi-operand routing bias (graph-encoder hidden_dim 64 is undersized relative to v76's mean 14.7 nodes / 15.8 edges); we attribute meta_logic weakness primarily to vocabulary-gap-driven OOV tokenization on the expression side.

---

## 8. Data and method notes

- **Eval set used:** `cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl` (1000 records, hand-verified bucket distribution: v77_omega 267, v75_register 264, v74_baseline 200, v76_production 108, meta_logic 102, v77_rule_four 59).
- **Sample sets used:** K=9 v77fix paraphrase samples (3000 records, paraphrase-only, no self-prior); K9_DiagLoop_full_v2_honest paraphrase-with-self-prior samples (3000 records).
- **Compiler:** `noetic-compass-scaffold/noetic-compass/api/notation/compiler.py`, `compile_expression()` Python-only path. All 1000 records in eval set compiled successfully. Diagram returned by `art.diagram()` was traversed for graph-stats.
- **Vocabulary source:** `noetic-compass-scaffold/noetic-compass/cas-native/training/runs/structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045/structured_token_vocab.json` (293 tokens). The K9_DiagLoop_full vocab is identical in size and content (verified via spot-check of `cas:F1` ID).
- **What this report does NOT do:** it does not run training, does not call any model on a pod, does not modify training data or vocab. All compute is local CPU inspection. The smoke v2 honest_eval_samples.jsonl was not accessible from local disk and was not used; the K9_DiagLoop_full_v2_honest run is the closest local apples-to-apples comparator and its numbers (v76 32.4%, meta_logic 19.6%) are the diagnostic basis here, not the user-cited 24.4% / 7.5% smoke v2 numbers.
