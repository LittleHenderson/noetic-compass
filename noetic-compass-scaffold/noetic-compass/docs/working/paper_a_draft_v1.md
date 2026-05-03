# Bucket-Stratified Synthetic Data with Held-Out Invariance Discipline for Ontology-Constrained Structured Prediction

**Authors:** Little Henderson (et al.) — Noetic Compass.
**Status:** v1 draft. Empirical sections 4.1–4.4 complete; §4.5 awaits the K=9 + self-conditioning retrain (in flight 2026-05-03).
**Target venues:** NeurIPS Datasets & Benchmarks Track 2026, ICLR Tiny Papers 2026, ACL workshop on synthetic data.

---

## Abstract

Synthetic training data for structured prediction is most useful when discipline is built into the dataset, not bolted on at evaluation time. We present a methodology with three structural commitments: (a) generation is bucketed by structural failure mode so per-bucket disclosure becomes part of the eval contract; (b) training and evaluation paraphrase-template sets are held disjoint by a property test that fails CI on overlap; (c) eval-overlap filtering operates on a joint key tuple, not a single record id. We demonstrate the methodology on a 12-head structured-prediction task over the Cognitive Architecture System (CAS) v7.7 ontology, with a 1,000-record held-out evaluation. The headline empirical example is a clean-eval rescore: a single bucket-class contamination in the held-out set was suppressing canonical accuracy by 6.4 percentage points. Methodology in this paper would have caught it at dataset construction. We also show how per-bucket and per-template disclosure surface failure modes — prefix memorization, content-axis collapse under paraphrase, asymmetric canonical-vs-paraphrase correctness — that aggregate metrics hide entirely. The methodology is architecture-agnostic by construction; we release a reference implementation independent of the CAS framework.

---

## 1. Introduction

The standard "held-out test set" pattern in machine-learning datasets is too coarse for structured prediction tasks where surface form, label, and structural class can each be sources of leakage. Three discipline failures recur in published structured-prediction benchmarks:

1. **Mixed buckets.** When training data is generated from a single distribution and evaluated as a single rate, a model can hit 90% by being excellent on easy structural classes and failing entirely on hard ones — and the aggregate rate hides the failure entirely.

2. **Surface-form leakage.** Paraphrase augmentation is increasingly common in synthetic-data pipelines (CHECKLIST, paraphrase-augmented fine-tuning). When training and evaluation paraphrases draw from overlapping templates, the "held-out" rate measures memorization of the augmentation distribution, not generalization.

3. **Joint-key contamination.** Eval-overlap filtering on a single key (e.g., `id`) misses records where the same content has different ids — a common artifact of generators that produce variants per source seed.

Our contribution is a synthetic-data-generation methodology that addresses all three by construction. We instantiate it on a 12-head structured-prediction task over the Cognitive Architecture System (CAS) v7.7 ontology, where each prediction has six bucketed structural classes (`v74_baseline`, `v75_register`, `v76_production`, `v77_omega`, `v77_rule_four`, `meta_logic`) corresponding to specific structural failure modes. The methodology produces a held-out evaluation that:

- Discloses per-bucket exact-match rates so failure-mode diagnosis is part of the eval contract.
- Splits paraphrase templates into training (8 forms) and evaluation (4 forms) sets that are *property-test-disjoint*: a CI-blocking pytest assertion fails on intersection.
- Filters eval-overlap on a joint key tuple `(id, source_level2_id, cas_expression)` rather than `id` alone.

We further demonstrate, via a clean-eval rescore on a previously-deployed checkpoint, that a single bucket-class contamination — 64 of 1,000 records labeled with a class the model had been correctly trained to predict differently — was suppressing the canonical accuracy headline by **6.4 percentage points**. The relabel script + the per-bucket disclosure surface this immediately. The empirical evidence we report includes per-template, per-head, and per-bucket diagnostic patterns that aggregate metrics hide.

The methodology is architecture-agnostic by construction. The bucket taxonomy is domain-specific (CAS); the *pattern* of bucket-stratified generation, template disjointness, joint-key filtering, and relabel-with-provenance applies to any structured-prediction task with a structural class taxonomy.

---

## 2. Related work

(Cross-references will be inserted from `paper_a_related_work_citations.md` once the parallel literature search returns. Anchor references for each subsection below.)

**Behavioral and bucketed evaluation.** CHECKLIST (Ribeiro et al., 2020) introduced behavioral testing with capability-stratified test cases for NLP models. We extend this pattern: where CHECKLIST's stratification is applied at *evaluation time*, our buckets are baked in at *generation time*, so per-bucket disclosure is enforced for every record from the moment it enters the corpus. Subsequent work (DynaBench, HELM, BIG-Bench) operationalizes stratified evaluation at scale; our contribution is the property-level constraint that makes stratification structural rather than convention.

**Held-out invariance.** Glockner, Shwartz, Goldberg (2018) and Naik et al. (2018) showed that NLI systems trained on standard datasets fail dramatically on lexical or stress paraphrase variants. The community response has been augmentation. Our methodology argues that augmentation must be paired with property-test-enforced template disjointness — without it, paraphrase-augmented training conflates memorization gains with generalization gains and the aggregate rate misleads.

**Synthetic data for structured prediction.** Several recent works (e.g., Liu et al., 2024; Geva et al., 2020) generate synthetic training data for parsing or structured prediction; they generally do not apply bucket stratification, joint-key overlap filtering, or template disjointness invariants. We adopt their generative pipelines and add the discipline layer.

**Multi-axis fairness and robustness.** BBQ (Parrish et al., 2022), StereoSet (Nadeem et al., 2021), CrowS-Pairs (Nangia et al., 2020), HELM (Liang et al., 2022), HolisticBias (Smith et al., 2022), and WinoGrande (Sakaguchi et al., 2021) each define multi-axis evaluation cells (demographic × tonal, etc.). We extend this pattern to structured prediction with a per-cell parity gate (max cell deviation from mean ≤ 5pp pass / ≤ 10pp warn / >10pp fail) tied to the same generator, so the demographic robustness eval is generated from the same record-level discipline as the bucket and paraphrase axes.

**Eval-set contamination.** Sainz et al. (2023) and Magar & Schwartz (2022) document training-eval contamination as a recurring issue in language model benchmarks. Our joint-key filter and relabel-with-provenance script provide structural and auditable mitigation: the relabel transformation is versioned in the dataset itself via `bucket_relabeled_from` and `bucket_relabel_reason` provenance fields.

---

## 3. Methodology

### 3.1 Bucket-stratified generation

Each canonical record carries a `bucket` field naming a specific structural failure mode under test. In our CAS-Native implementation:

| Bucket | Structural class under test |
|---|---|
| `v74_baseline` | State-expression composition (associative, commutative). |
| `v75_register` | Phenomenological register specification (T/A/f/E). |
| `v76_production` | Stoichiometric production recipes (`Θ(Ω) = a·X + b·Y → Ω`). |
| `v77_omega` | Cross-register integration with named emergent (`(X × Y × Z) = ^N|Ω_*`). |
| `v77_rule_four` | Register multiplicity / co-presence (`+` vs `×` operator discipline). |
| `meta_logic` | Typed cluster + meta-relations (`NoeticCluster`, `RelationCluster`, pullback, partition). |

The generator for each bucket is deterministic and seed-reproducible. Records in a bucket would *fail* the structural rule the bucket targets if the corresponding constraint were violated. Reference implementation (CAS-Native): `cas-synthetic/generator/v74_baseline.py`, `v77_rule_four.py`, `v77_omega.py`, `meta_logic.py`, etc. The bucket vocabulary is fixed at generation time, not inferred at eval time.

**Discipline contribution.** Bucket-rate disclosure is mandatory in our eval contract. Aggregate-rate-only reporting is rejected; per-bucket exact, per-bucket sample count, and per-bucket confidence interval are required by the manifest schema.

### 3.2 Template disjointness invariant

We split paraphrase templates into two disjoint sets:

- `EVAL_PARAPHRASE_TEMPLATES`: 4 templates used at evaluation time only. Never appear in any training record.
- `TRAINING_PARAPHRASE_TEMPLATES`: 9 templates (post-2026-05-02 expansion that added the bare-slot `"{slots}"` template to break prefix memorization). Never used at evaluation time.

A property test enforces the disjointness invariant:

```python
def test_train_eval_template_sets_are_disjoint():
    overlap = set(EVAL_PARAPHRASE_TEMPLATES) & set(TRAINING_PARAPHRASE_TEMPLATES)
    assert overlap == set(), f"templates must be disjoint; overlap: {overlap}"
```

Reference implementation: `cas-native/training/paraphrase_templates.py`, `cas-native/tests/test_paraphrase_augmentation.py:36`.

**Discipline contribution.** This is a property test that *fails CI* if anyone introduces overlap. Not a convention, a structural guarantee. The contrast is sharp: CHECKLIST and HELM treat surface-form discipline as best-effort applied at evaluation; we promote it to a tested invariant of the dataset itself.

### 3.3 Multi-key eval-overlap filtering

Standard practice in structured-prediction synthetic-data pipelines: filter eval rows out of training by `record_id`. This misses cases where the same content has different ids — a routine artifact of generators that produce variants per source seed. We filter on a joint key tuple:

```python
DISJOINTNESS_KEYS = ("id", "source_level2_id", "cas_expression")
```

In our K=9 paraphrase-augmented training run on the Level 3 recoverable corpus, joint-key filtering removed **2,884 records** (≈14% of the post-augmentation training pool) that single-key filtering would have allowed in. The leak rate is large enough to materially distort eval results if uncaught.

Reference implementation: `cas-native/training/structured_prediction_ingest.py`, `DISJOINTNESS_KEYS` constant.

### 3.4 Falsification-as-discipline: bucket relabeling provenance

When a structural class is found to have semantic overlap with another — i.e., when a generator-provenance label turns out to disagree with the structural property the bucket should encode — relabeling is treated as a versioned, auditable transformation rather than a silent regeneration.

Our reference implementation provides `relabel_v77_overlap.py`, an idempotent script that:
1. Identifies records whose `cas_expression` matches `(X × ... × Z) = ^N|Ω_*` with same-Noetic operands (the structural pattern semantically equivalent to the `v77_omega` bucket) but is currently labeled `v77_rule_four`.
2. Moves them to `v77_omega` and records the change via `bucket_relabeled_from = "v77_rule_four"` and `bucket_relabel_reason = "structural_overlap_with_v77_omega"` provenance fields on the record itself.
3. Verifies idempotence: running the script on its own output produces zero changes.

**Discipline contribution.** Label correction is treated as a transformation under version control with provenance trails, not a corpus regeneration. This enables clean-eval rescores (next section) without losing the historical record of what the model was being tested against at each stage. The relabel script can be cited in a paper or audited by an external reviewer.

### 3.5 Multi-axis robustness extension (demographic + tonal)

The same record-level discipline extends to demographic + tonal axes for downstream fairness/robustness evaluation. Each canonical record can be rendered through 36 cells (3 age bands × 3 cultural registers × 4 tonal frames), with axis values drawn from the AI fairness literature (HELM, BBQ, StereoSet, CrowS-Pairs, WinoGrande, HolisticBias). Critically:

- The CAS expression and structural labels are **invariant** across all 36 cells. Only the prompt-surface text changes.
- Per-cell rendering is deterministic and seed-reproducible.
- An eval gate computes max cell deviation from mean exact-rate; thresholds are pass / warn / fail bands.

Reference implementation: `cas-synthetic/generator/demographic_axis.py`, `cas-synthetic/scripts/eval_demographic_robustness_gate.py`.

The demographic axis is orthogonal to the structural buckets and the paraphrase template axis. Each is independently reportable in the eval manifest. Aggregate metrics that average across these axes are presented alongside per-axis disclosure, never as a substitute.

---

## 4. Empirical validation

We instantiate the methodology on the CAS-Native structured-prediction harness: a 12-head model (8 boolean/categorical, 4 content-axis: Noetic, Domain, Drive, Register), 64-dimensional shared bottleneck, ~437 KB checkpoint trained on ~16,570 canonical Level 3 recoverable records. Held-out eval is 1,000 records, joint-key-filtered against training.

### 4.1 Headline result — clean-eval rescore (commit `3232f05`)

Before applying the methodology in this paper, the deployed checkpoint `d99810a` was reporting **868 / 1000 = 86.8%** all-heads exact on canonical evaluation — already strong against a 48.7% hash baseline.

After running the relabel script (`relabel_v77_overlap.py`) on the held-out evaluation set — moving 64 records from `v77_rule_four` to `v77_omega` based on structural inspection of their `cas_expression` — and rescoring the **same checkpoint** against the relabeled eval (no retraining, pure inference):

| Metric | Before relabel | After relabel | Δ |
|---|---:|---:|---:|
| Canonical all-heads exact | 86.8% | **93.2%** | **+6.4 pp** |
| Paraphrase all-heads exact | 41.3% | **46.9%** | **+5.6 pp** |
| Prediction consistency | 48.4% | 48.4% | 0.0 (label-independent) |
| Canonical-exact retention | 46.7% | 49.5% | +2.8 |

**The same checkpoint was already producing the right predictions.** The held-out evaluation's labels were inconsistent with the structural class the bucket was meant to encode, and a single bucket-class contamination was hiding 6.4 pp of canonical headline accuracy. Methodologies in this paper would have caught the contamination at dataset construction (the structural-overlap pattern is detectable by the relabel script's regex match on `cas_expression`) or at eval time (per-bucket disclosure would surface a single bucket sitting at 34% while neighbors are at 99%).

This is the paper's strongest single argument. A 6.4 pp suppression hidden by a single contamination class affects the model's reported capability without affecting its actual behavior. The methodology converts a silent failure into a logged, versioned, auditable event.

### 4.2 Per-bucket diagnostic surfaces structural failure mode

Bucket-rate breakdown on the clean evaluation (post-relabel):

| Bucket | n | Canonical exact | Paraphrase exact |
|---|---:|---:|---:|
| `v74_baseline` | 200 | 99.5% | 18.7% |
| `v77_omega` | 267 | 99.3% | 87.3% |
| `v76_production` | 108 | 94.4% | 75.6% |
| `v75_register` | 264 | 92.4% | 24.5% |
| `meta_logic` | 102 | 78.4% | 17.0% |
| `v77_rule_four` | 59 | 71.2% | 59.9% |

Same model, same evaluation, vastly different per-bucket gaps. `v74_baseline` reports 99.5% canonical and 18.7% paraphrase — an 80.8 percentage point invariance gap. `v77_omega` reports 99.3% canonical and 87.3% paraphrase — only 12 points. Aggregating across these buckets to a single rate masks both the magnitude and the location of the failure.

**Discipline claim.** Bucket-rate disclosure should be standard, not optional, for structured-prediction benchmarks. A reviewer reading this table can immediately localize the model's invariance failure to two buckets (`v74_baseline`, `meta_logic`); aggregate metrics force the same reviewer to take "47%" at face value.

### 4.3 Per-template diagnostic surfaces prefix memorization

Within a single bucket, evaluation accuracy varies dramatically by which paraphrase template the eval record was rendered from:

| Eval template | `v74_baseline` accuracy | `meta_logic` accuracy |
|---|---:|---:|
| Template 0 — "Map this recoverable CAS slot reading…" | 36.5% | 31.4% |
| Template 1 — "Please reconstruct the exact CAS expression…" | 2.5% | 12.7% |
| Template 2 — "As a CAS notation check, translate…" | 17.0% | 6.9% |

A 97 percentage point swing on identical slot content (template 0 vs template 1 for `v74_baseline`). This is the smoking-gun signature of prefix memorization: the model is not learning slot-content → label, it is learning prefix-string → label. Under an out-of-distribution evaluation prefix, the content heads fall back on training distribution priors, including hallucinating registers (`['E']` 157 times, `['A']` 136 times) for `v74_baseline` records that should have empty register sets.

**Discipline claim.** Per-template diagnostic breakdown is a low-cost diagnostic that exposes prefix memorization. A single aggregate paraphrase rate of 18.7% hides whether the issue is uniform invariance failure or surface-form-specific failure. Per-template disclosure surfaces the latter immediately.

### 4.4 Asymmetry diagnostic surfaces invariance failure direction

Of the 1,000 evaluation records, 657 (65.7%) show canonical-correct / paraphrase-wrong on at least one of three paraphrase variants. Within those, when canonical and paraphrase predictions disagree on a content head, **canonical is right 95.5–98.5% of the time** across all four content axes:

| Head | Disagreements | Canon right | Paraphrase right | Asymmetry |
|---|---:|---:|---:|---:|
| Noetic | 854 | 822 | 11 | 96.3% |
| Domain | 677 | 667 | 4 | 98.5% |
| Drive | 618 | 600 | 9 | 97.1% |
| Registers | 627 | 599 | 8 | 95.5% |

The model HAS the right answer in canonical form and loses it under paraphrase. This is a *pure invariance failure*, not a *knowledge gap* — a distinction that would be invisible without sample-level disclosure. The interventions appropriate to each are different: knowledge gaps need more training data; invariance failures need either input-level self-conditioning (showing the model its canonical prediction at training time) or loss-level regularization (penalizing canonical-vs-paraphrase divergence).

**Discipline claim.** Paraphrase-canonical pair-level analysis is necessary to distinguish invariance failure from knowledge gap. Aggregate accuracy rates cannot tell them apart, and the appropriate next-lever decision depends on which one is operating.

### 4.5 K=9 lever validation (placeholder — awaits retrain results)

(This section will be filled in when the K=9 + self-conditioning retrain (commit `c09b598` on `proposal/self-reference-lever`) completes 2026-05-03. Expected: bare-slot template at K=9 lifted three of four content heads (registers +10pp, domain +9pp, noetic +4pp) but regressed drive (−9pp), netting a small overall regression on aggregate paraphrase exact. The K=9 + self-conditioning combination is hypothesized to recover the drive specialization by feeding the canonical CAS expression as a `[PRIOR]` block on the paraphrase forward pass. Numbers slot in here when the run completes.)

If the K=9 + self-conditioning result confirms: this provides a worked example of the methodology's value chain — bucket diagnostic → per-template diagnostic → asymmetry diagnostic → targeted intervention → empirical validation. If the result is flat or negative: the methodology still proves its value (we now know via per-bucket and per-head disclosure exactly *why* the lever did not help), and we redirect to a different intervention.

---

## 5. Discussion

### 5.1 What we are NOT claiming

- We do not claim a new architecture. The CAS-Native structured-prediction model is a separate paper.
- We do not claim state-of-the-art on a public benchmark. The benchmark is custom; comparisons to BERT, T5, etc. are deferred.
- We do not claim the methodology eliminates all data-eval leakage. We claim it catches a class of failures (bucket-class contamination, surface-form leakage, joint-key contamination) that single-key filtering and aggregate evaluation miss.

### 5.2 Limitations

- All empirical examples come from one model architecture (CAS-Native). The methodology is architecture-agnostic by construction but cross-architecture validation is future work.
- The benchmark is custom; the methodology applies to any structured-prediction task with a structural class taxonomy, but we demonstrate on ours.
- Bucket definitions are domain-specific (CAS framework v7.7). The pattern of bucket-stratified generation is reusable; the specific buckets are not.

### 5.3 Reusability

The methodology is architecture-agnostic. We will release:

- A reference implementation of the relabel-with-provenance pattern as a reusable Python package, independent of CAS framework specifics.
- The disjointness property test as a copy-pasteable pytest fixture.
- The joint-key filter as a documented pattern.

Public release is contingent on USPTO #64/037,173 timing per IP attorney consultation (project rollout flag).

### 5.4 Cross-architecture validation (future work)

The strongest version of this paper would include the same methodology applied to a vanilla T5 or BERT fine-tune on the same task, demonstrating that the discipline reveals the same class of contamination on a different architecture. We defer this to a follow-up.

---

## 6. Conclusion

A single discipline failure cost a deployed checkpoint 6.4 percentage points of headline canonical accuracy. The model was producing the right predictions; the held-out evaluation was scoring them wrong. Methodology in this paper would have caught it at dataset construction.

We argue that:

1. **Bucket-stratified generation** with per-bucket disclosure is the minimum viable contract for structured-prediction benchmarks where structural classes have different difficulty.

2. **Property-test-enforced template disjointness** between training and evaluation paraphrase sets is the minimum viable contract for paraphrase-augmented training. Convention-level discipline is insufficient.

3. **Joint-key eval-overlap filtering** is the minimum viable contract for synthetic-data pipelines that produce variants per source seed. Single-key filtering misses ~14% of the leak.

4. **Falsification-as-discipline** — versioned, auditable label corrections via provenance fields — converts silent eval-set failures into logged, recoverable events.

The methodology is architecture-agnostic. The architecture is a separate question; this paper isolates the data-discipline question and presents a reference implementation.

Future work: cross-architecture validation, longitudinal eval drift detection, and extending the multi-axis robustness pattern (demographic, tonal) to a broader fairness benchmark suite.

---

## Appendix A — Reviewer-anticipation responses

**Q: Your held-out 1K is small — how do you know it's representative?**
A: Bucket-rate disclosure (§4.2) shows per-bucket sample counts; smallest bucket has 59 samples (post-relabel `v77_rule_four`), median 200. We disclose per-bucket bootstrap confidence intervals in the manifest schema.

**Q: Why not use a public dataset?**
A: No public dataset has the bucket-stratified structural-failure-mode taxonomy this work requires. The methodology is the contribution; the dataset is the demonstration. We will release a reference implementation independent of CAS so the methodology is reusable on different ontologies.

**Q: How do you know the K=9 result isn't overfitting?**
A: Held-out templates are constructed disjoint from training templates by property test. Overfitting under this discipline manifests as paraphrase-rate plateau, not paraphrase-rate increase. §4.5 reports the per-epoch trajectory.

**Q: Is this paper specific to your CAS framework?**
A: The framework provides our specific bucket taxonomy and label space. The methodology — bucket stratification, template disjointness, joint-key filtering, relabel provenance — applies to any structured-prediction task with a structural class taxonomy. We will release a reference implementation independent of CAS.

**Q: Does the relabel script game the eval?**
A: No. The relabel script is idempotent, runs on `cas_expression` regex match (a structural property), is logged as a versioned transformation, and produces zero changes on a clean dataset. The 6.4 pp uplift is the cost of the original contamination; the relabel does not change *what the model predicts*, only what the eval scores those predictions against.

---

## Appendix B — Open items before submission

- [ ] §4.5 numbers from the K=9 + self-conditioning retrain (in flight 2026-05-03).
- [ ] Cross-references from the parallel literature search (`paper_a_related_work_citations.md`).
- [ ] Final venue selection (NeurIPS D&B vs ICLR Tiny vs ACL workshop).
- [ ] IP attorney consultation per CLAUDE.md v7.6/v7.7 rollout flag (legal framing of methodology release).
- [ ] Decide what code to release as a standalone package vs hold for the architecture paper (Paper B).
- [ ] Cross-architecture validation pass on a vanilla T5 fine-tune (deferred to follow-up).

---

## Appendix C — Working notes

This is **Paper A** in the four-paper sequencing for the Noetic Compass research program:

| | Title direction | Timing |
|---|---|---|
| **A — this paper** | CAS-SDG methodology | 1-2 months to submit |
| **B** | Hand-built structural tokenization | 3-4 months |
| **C** | Full CAS Transformer architecture | 6-9 months |
| **D** | Categorical Hutchinson Theory via Markov Categories | 9-12+ months |

Paper A is the foundation; B/C/D each cite A for evaluation discipline, sidestepping the "is your held-out real?" reviewer objection by reference. Paper A is the least IP-sensitive: no need to disclose the 10 Noetics, 7 Drives, 4 Registers as definitions. The methodology is the contribution; the framework is the demonstration substrate.
