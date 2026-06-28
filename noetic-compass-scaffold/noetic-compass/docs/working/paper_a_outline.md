# Paper A — CAS-SDG Methodology Paper

**Working title:** *Bucket-Stratified Synthetic Data with Held-Out Invariance Discipline for Ontology-Constrained Structured Prediction*

**Status:** outline only — empirical envelope already strong, awaiting K=9 retrain results to firm up the headline example.

**Target venues:** NeurIPS Datasets & Benchmarks Track, ICLR Tiny Papers, ACL workshop on synthetic data, AAAI applied track.

**Target length:** 8-12 pages.

---

## Thesis (one sentence)

Synthetic training data for structured prediction is most useful when (a) generation is bucketed by structural failure mode, (b) eval surface forms are held disjoint from training surface forms by construction, and (c) eval-overlap filtering operates on joint-key tuples — and the methodology is publishable independent of any particular model architecture.

---

## Abstract (TBD — final draft after K=9 lands)

~150 words. State the problem (eval discipline failures hide model performance and disguise failure modes), the methodology (bucket-stratified generation + template disjointness + multi-key overlap filtering + falsification provenance), the headline empirical example (clean-eval rescore moved a checkpoint from 86.8% → 93.2% canonical with no retrain — a 6.4 pp uplift hidden by a single label contamination class), and the contribution (a reusable methodology, not architecture-specific).

---

## 1. Introduction

- The standard "held-out test set" pattern in ML datasets is too coarse for structured prediction tasks where surface form, label, and structural class can each be sources of leakage.
- Three discipline failures we'll address:
  1. **Mixed buckets:** standard datasets average across structural classes, masking *which kind* of error a model makes.
  2. **Surface-form leakage:** training and eval often draw from overlapping prompt templates, so "held-out" measures memorization not generalization.
  3. **Joint-key contamination:** eval-overlap filtering on a single key (e.g., `id`) misses overlap on `(id, source_id, target_expression)` tuples.
- Our contribution: a synthetic-data-generation methodology that addresses all three by construction, plus an empirical demonstration that even a single discipline failure (a label-class contamination) can hide >6 pp of model performance.

## 2. Related work

- Synthetic data for structured prediction (Geva, Gupta, Berant 2020; Liu et al. 2024).
- Held-out invariance evaluation (Naik et al. 2018; Glockner et al. 2018; the BIG-bench paraphrase studies).
- Bucket-stratified evaluation (CHECKLIST, Ribeiro et al. 2020).
- Multi-axis fairness/robustness gates (HELM, BBQ, StereoSet, CrowS-Pairs, WinoGrande, HolisticBias).
- Position our work as: stricter than CHECKLIST (template disjointness as property invariant, not best-effort), more discipline than HELM-style multi-axis (joint-key filtering, falsification provenance).

## 3. Methodology

### 3.1 Bucket-stratified generation

- Each canonical record carries a `bucket` field naming a specific structural failure mode under test:
  - `v74_baseline`: state-expression composition.
  - `v75_register`: register-axis specification.
  - `v76_production`: stoichiometric production recipes.
  - `v77_omega`: cross-register integration with named emergent.
  - `v77_rule_four`: register multiplicity / co-presence.
  - `meta_logic`: typed cluster + meta-relations.
- Generators are deterministic, seed-reproducible, and each bucket produces records that *would fail* if the corresponding structural rule were violated.
- Reference impl: `cas-synthetic/generator/v77_rule_four.py`, `v77_omega.py`, `meta_logic.py`, etc.

### 3.2 Template disjointness invariant

- Two template sets: `EVAL_PARAPHRASE_TEMPLATES` (4 entries) and `TRAINING_PARAPHRASE_TEMPLATES` (9 entries post-PR #2).
- A property test (`test_paraphrase_templates.py::test_train_eval_template_sets_are_disjoint`) enforces `set(EVAL) ∩ set(TRAIN) = ∅`.
- Reference impl: `cas-native/training/paraphrase_templates.py`, `cas-native/tests/test_paraphrase_augmentation.py:36`.
- Discipline contribution: a property test that *fails CI if anyone introduces overlap*. Not a convention, a structural guarantee.

### 3.3 Multi-key eval-overlap filtering

- Standard practice: filter eval rows out of training by `id`. Misses cases where the same content has different IDs.
- Our practice: filter on `(id, source_level2_id, cas_expression)` joint key.
- In the d99810a checkpoint, this removed 2,884 records (≈14% of the training pool) — uncovered by single-key filtering.
- Reference impl: `cas-native/training/structured_prediction_ingest.py`, `DISJOINTNESS_KEYS` constant.

### 3.4 Falsification-as-discipline: bucket relabeling provenance

- When a structural class is found to have semantic overlap with another (e.g., the v77_rule_four / v77_omega overlap discovered 2026-05-02), an idempotent relabel script moves records to the correct class and adds `bucket_relabeled_from` and `bucket_relabel_reason` provenance fields.
- This treats label correction as a **versioned, auditable transformation** rather than a silent re-generation.
- Reference impl: `cas-synthetic/scripts/relabel_v77_overlap.py`.
- Methodological claim: this provenance enables clean-eval rescores (next section) without losing the historical record of what the model was being tested against at each stage.

### 3.5 Multi-axis robustness extension (demographic + tonal)

- Per PR #1 (today): extend the SDG with demographic (age band × cultural register) and tonal (formal/casual/technical/plain-speech) axes.
- Per-cell parity gate: max cell deviation from mean ≤ 5pp pass / ≤ 10pp warn / >10pp fail.
- Axis values drawn from AI-fairness evaluation literature (HELM, BBQ, StereoSet, CrowS-Pairs, WinoGrande, HolisticBias).
- Reference impl: `cas-synthetic/generator/demographic_axis.py`, `cas-synthetic/scripts/eval_demographic_robustness_gate.py` (PR #1).

## 4. Empirical validation

### 4.1 Headline result — clean-eval rescore (commit 3232f05)

- **Before relabel:** 868/1000 = 86.8% canonical exact, 41.3% paraphrase exact.
- **After bucket-relabeling the held-out eval (no retrain):** 932/1000 = **93.2% canonical**, **46.9% paraphrase**.
- The +6.4 pp canonical / +5.6 pp paraphrase uplift is the cost of a single bucket-class contamination that was sitting in the held-out eval set.
- Show: same checkpoint, same eval samples, only the labels changed. The model already had the right predictions; the eval was scoring them wrong.
- This is the strongest single-graphic argument for the methodology.

### 4.2 Per-bucket diagnostic surfaces structural failure mode

- Bucket-rate breakdown on clean eval (d99810a):
  - v77_omega: 99.3% canonical / 87.3% paraphrase (gap 12.0 pp)
  - v74_baseline: 99.5% / 18.7% (gap 80.8 pp)
  - meta_logic: 78.4% / 17.0% (gap 61.4 pp)
- Same model, same eval, vastly different per-bucket gaps. Without bucket stratification this would average out to a single rate that doesn't distinguish "healthy bucket" from "broken bucket."
- Methodology claim: bucket-rate disclosure should be standard, not optional, for structured-prediction benchmarks.

### 4.3 Per-template diagnostic surfaces prefix memorization

- Within a single bucket, eval-template accuracy varies dramatically:
  - v74_baseline template 0: 36.5%, template 1: 2.5%, template 2: 17.0%.
  - 97 pp swing on identical slot content.
- Diagnosis: model memorized prefix → label associations rather than learning slot-content → label.
- Methodology claim: per-template breakdown is a low-cost diagnostic that exposes prefix memorization, which a single aggregate rate hides entirely.

### 4.4 Asymmetry diagnostic surfaces invariance failure

- 657 of 1000 records show canonical-correct / paraphrase-wrong on at least one paraphrase.
- When canonical and paraphrase predictions disagree on a content axis, **canonical is right 95-98% of the time** across all four content axes (Noetic, Domain, Drive, Register).
- Diagnosis: the model has the right answer in canonical form and loses it under paraphrase. Pure invariance failure, not knowledge gap.
- Methodology claim: paraphrase-canonical pair-level analysis is necessary to distinguish *invariance failure* from *knowledge gap* — these need different interventions and aggregate rates can't tell them apart.

### 4.5 K=9 lever validation (slots in once retrain completes)

- TBD — pending K=9 retrain (commit `fe7d389`, currently running).
- Expected: paraphrase exact rises materially (target >55%), v74_baseline + meta_logic close most of the canonical-paraphrase gap.
- If K=9 lifts the buckets the per-template diagnostic predicted, it confirms the methodology *predicted* where the lever should bite — not just measured the result after the fact.

## 5. Discussion

### 5.1 What we are NOT claiming

- We are not claiming a new architecture (architecture is a separate paper).
- We are not claiming SOTA on any public benchmark (custom benchmark, no comparison to BERT/T5/etc. in this paper).
- We are not claiming the methodology eliminates all data-eval leakage — only that it catches a class of failures that single-key filtering and mixed-bucket evals miss.

### 5.2 Limitations

- All empirical examples come from one model architecture (CAS-Native structured-prediction head). The methodology is architecture-agnostic by construction but we have not validated it across architectures.
- The benchmark is custom; methodology applies to any structured-prediction task but we demonstrate on ours.
- Bucket definitions are domain-specific (CAS framework). The *pattern* of bucket-stratified generation is reusable; the specific buckets are not.

### 5.3 Reusability

- Anyone building a structured-prediction dataset for a different ontology can apply: bucket-stratified generation, template disjointness property test, joint-key overlap filter, relabel-with-provenance discipline.
- We will release the methodology code (relabel script, disjointness test, joint-key filter) as a reusable Python package — TBD whether public release is compatible with USPTO #64/037,173 timing (IP attorney consultation flagged).

## 6. Conclusion

- A single discipline failure cost a checkpoint 6.4 pp of headline canonical accuracy. Methodologies in this paper would have caught it earlier.
- The architecture is a separate question. The data-discipline question is independent and immediately publishable.
- Future work: extend the methodology to multi-axis robustness (demographic, tonal — PR #1) and to longitudinal eval drift detection.

---

## Reviewer-anticipation appendix

**Q: "But your held-out 1K is small — how do you know it's representative?"**
A: Bucket-rate disclosure (Section 4.2) shows per-bucket sample counts; smallest bucket has 102 samples, all-bucket median 200. We disclose per-bucket confidence intervals.

**Q: "Why not use a public dataset?"**
A: No public dataset has the bucket-stratified structural-failure-mode taxonomy this work requires. The methodology is the contribution; the dataset is the demonstration.

**Q: "How do we know the K=9 result isn't overfitting?"**
A: Held-out templates are constructed disjoint from training templates by property test. Overfitting under this discipline would manifest as paraphrase-rate plateau, not rate increase. Sec 4.5 will report the per-epoch trajectory.

**Q: "Is this paper just specific to your CAS framework?"**
A: The framework provides our specific bucket taxonomy and label space. The methodology — bucket stratification, template disjointness, joint-key filtering, relabel provenance — applies to any structured-prediction task with a structural class taxonomy. We will release a reference implementation independent of CAS.

---

## Open items before submission

- [ ] K=9 retrain numbers (commit `fe7d389`, ETA ~16:35-16:45 PDT 2026-05-02).
- [ ] Decide single venue and format (NeurIPS D&B vs ICLR vs workshop).
- [ ] IP attorney consultation per CLAUDE.md v7.6/v7.7 rollout flag.
- [ ] Decide what to release as code vs hold for the architecture paper.
- [ ] Write actual abstract once K=9 numbers crystallize the headline.
- [ ] Pull 2-3 named related-work citations into the introduction.
- [ ] Optional: cross-architecture validation pass (apply methodology to a vanilla T5 fine-tune on the same task) — strengthens reusability claim, can be deferred to a follow-up paper.

---

## Working notes

- This paper is *Paper A* in the four-paper sequencing discussed 2026-05-02:
  - Paper A — this one — CAS-SDG methodology, target 1-2 months
  - Paper B — Hand-built structural tokenization, target 3-4 months (after K=9 + ablation)
  - Paper C — Full CAS Transformer architecture, target 6-9 months
  - Paper D — Categorical Hutchinson Theory via Markov Categories, target 9-12+ months
- Paper A is the foundation; B/C/D each cite A for eval discipline, sidestepping the "is your eval real?" reviewer objection by reference.
- Paper A is the least IP-sensitive: no need to disclose the 10 Noetics, 7 Drives, or 4 Registers as definitions. The methodology speaks for itself.
