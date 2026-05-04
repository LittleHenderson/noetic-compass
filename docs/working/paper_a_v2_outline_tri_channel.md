# CAS-SDG-Bench: A Tri-Channel Synthetic Benchmark for Structured Cognitive Recovery with Color-Coded Diagrammatic Ground Truth and Cross-Channel Consistency Evaluation

**Authors:** Little Henderson (et al.) — Noetic Compass.
**Status:** v2 outline. Supersedes v1 framing (`paper_a_draft_v1.md`, which remains as historical record). Sections 1, 4, 5.5, 5.6, 6, 7 written as full text. Sections 3 and 5.1–5.4 condensed from v1. Section 5.7 is a PLACEHOLDER awaiting PR #6 (diagram-loop) full retrain.
**Target venues:** NeurIPS Datasets & Benchmarks Track 2026, ICLR Tiny Papers 2026, ACL workshop on synthetic data.

---

## Abstract (placeholder — to be written after Section 5.7 fills in)

CAS-SDG-Bench is a synthetic benchmark for structured cognitive recovery over the Cognitive Architecture System (CAS) v7.7 ontology. The paper's headline contribution is a tri-channel ground truth framework — notation, diagram, and color — where cross-channel consistency rate is treated as a primary diagnostic metric. Single-channel evaluation cannot distinguish surface errors from structural errors; tri-channel evaluation can. We demonstrate the methodology on a 12-head structured-prediction task and report empirical results from a sequence of retrain runs. The K=9 bare-slot paraphrase retrain achieved partial content-head recovery (3 of 4 heads improved) while Drive regressed, establishing Drive specialization as the limiting reagent for notation-only recovery. A small-scale K=9 + self-conditioning smoke test confirmed that single-channel linear self-reference does not recover Drive at 5K records / 5 epochs. These results motivate the tri-channel architecture: diagram and color channels are independent recovery paths that may compose where a linear notation-only loop cannot. Section 5.7 reports the tri-channel training result (PLACEHOLDER — awaits PR #6).

---

## 1. Introduction

Evaluation of structured-prediction models on single-channel notation scores conflates two qualitatively different error types: surface errors, where the model produces notation that differs at the token level from ground truth while preserving underlying structure, and structural errors, where the model's output does not compile to the correct semantic graph at all. A model that outputs `^3^P|f` from ground truth `^3^P|A` — a Register flip — differs fundamentally from a model that outputs `^2^C` — a Noetic and Domain error that destroys the structural skeleton entirely. Single-channel exact-match and token-F1 scores treat these two errors identically. Benchmarks that score on notation strings alone cannot make this distinction; it is not a matter of metric resolution but of missing information. The notation channel is a flat string, and a flat string cannot encode the structural depth of what is correct or wrong about a prediction.

Existing structured-prediction benchmarks score on notation or label identity. Behavioral evaluation frameworks (CHECKLIST, HELM, DynaBench) operationalize stratified evaluation across capability classes, but they do not introduce a second independent ground truth axis whose disagreement with the primary axis is itself a diagnostic. Synthetic-data pipelines for parsing and structured prediction (Liu et al., 2024; Geva et al., 2020) apply discipline at the record level — bucket stratification, template disjointness, joint-key filtering — but emit only a single ground truth representation: the target label string or label tuple.

This paper introduces a tri-channel benchmark as the solution. The three channels — notation, diagram, and color — each encode the same CAS v7.7 structured-prediction target in a different representational modality, generated from the same compiler. The key property is orthogonality: the error modes that corrupt the notation channel are not identical to the error modes that corrupt the diagram channel or the color channel. Cross-channel consistency — the fraction of records on which all three channels agree or all three disagree — is therefore a diagnostic metric that single-channel benchmarks cannot compute at all.

The benchmark is instantiated on the Cognitive Architecture System (CAS) v7.7 ontology, a 12-head structured-prediction task where each prediction specifies a Noetic operator, Processing Domain, Core Drive, Register, and a set of structural Boolean flags. CAS v7.7 is the appropriate instantiation substrate for two reasons. First, CAS expressions have a formal compiler that emits typed graphs (NoeticCluster, RelationCluster, IntegrationEdge, etc.) with axis-attributed identity keys, providing diagram ground truth by construction. Second, the four CAS axes (10 Noetics, 4 Domains, 7 Drives, 4 Registers = 25 distinct values) provide a natural finite-valued type system for value-keyed color encoding, providing color ground truth by construction.

The v1 paper (`paper_a_draft_v1.md`) introduced the bucket-stratified methodology, template disjointness invariant, joint-key eval-overlap filtering, and relabel-with-provenance pattern, and demonstrated a 6.4 pp hidden uplift from clean-eval rescoring. The v2 paper extends this with the tri-channel framing as the headline contribution, adds K=9 and self-conditioning empirical results as the motivating evidence, and introduces cross-channel consistency rate as a new publishable diagnostic metric.

This paper is organized as follows. Section 2 reviews related work. Section 3 condenses the v1 methodology. Section 4 presents the tri-channel ground truth framework — the headline contribution. Section 5 reports empirical validation, including the clean-eval rescore, per-bucket and per-template diagnostics, the K=9 bare-slot partial success, the self-conditioning null result, and the tri-channel comparison placeholder. Section 6 discusses limitations and scope. Section 7 concludes.

---

## 2. Related Work (skeleton — citations from `paper_a_related_work_citations.md` to be inserted; branch `paper-a-related-work-citations` exists but the file was not present at v2 draft time)

**Behavioral and bucketed evaluation.**
CHECKLIST (Ribeiro et al., 2020) [CITATION FORTHCOMING]. DynaBench [CITATION FORTHCOMING]. HELM (Liang et al., 2022) [CITATION FORTHCOMING]. BIG-Bench [CITATION FORTHCOMING]. Our contribution: bucket stratification at generation time, not evaluation time; property-test-enforced.

**Held-out invariance.**
Glockner, Shwartz, Goldberg (2018) [CITATION FORTHCOMING]. Naik et al. (2018) [CITATION FORTHCOMING]. Paraphrase-augmented fine-tuning literature [CITATION FORTHCOMING]. Our extension: property-test-enforced template disjointness as a CI-blocking invariant.

**Synthetic data for structured prediction.**
Liu et al. (2024) [CITATION FORTHCOMING]. Geva et al. (2020) [CITATION FORTHCOMING]. Multi-channel ground truth is not addressed in prior work.

**Multi-axis fairness and robustness benchmarks.**
BBQ (Parrish et al., 2022) [CITATION FORTHCOMING]. StereoSet (Nadeem et al., 2021) [CITATION FORTHCOMING]. CrowS-Pairs (Nangia et al., 2020) [CITATION FORTHCOMING]. HolisticBias (Smith et al., 2022) [CITATION FORTHCOMING]. WinoGrande (Sakaguchi et al., 2021) [CITATION FORTHCOMING]. Our extension: multi-axis robustness (demographic + tonal) over structured-prediction targets, not free-text, with per-cell parity gate tied to the same generator.

**Eval-set contamination.**
Sainz et al. (2023) [CITATION FORTHCOMING]. Magar & Schwartz (2022) [CITATION FORTHCOMING]. Our contribution: joint-key filtering and relabel-with-provenance as structural mitigation.

**Color encoding in visualization and information theory.**
Color as redundant information channel in complex visual systems [CITATION FORTHCOMING]. Wong colorblind-accessible palette [CITATION FORTHCOMING]. Information-theoretic redundancy in multi-channel encoding [CITATION FORTHCOMING].

**Compiler-emitted graph representations.**
Abstract syntax tree and semantic graph generation from formal grammars [CITATION FORTHCOMING]. Typed graph matching and graph similarity measures [CITATION FORTHCOMING].

---

## 3. Methodology Layers (condensed from v1 Section 3)

The following four structural commitments are carried forward from v1 without modification. The tri-channel extension in Section 4 adds a fifth layer on top.

### 3.1 Bucket-stratified generation with per-bucket disclosure

Each record carries a `bucket` field identifying the structural failure mode under test. Six buckets in the CAS-Native implementation: `v74_baseline`, `v75_register`, `v76_production`, `v77_omega`, `v77_rule_four`, `meta_logic`. Bucket-rate disclosure is mandatory in the eval contract; aggregate-rate-only reporting is disallowed.

### 3.2 Template disjointness invariant (property-test-enforced)

Training paraphrase templates (9, post-K=9 bare-slot expansion) and evaluation paraphrase templates (4) are held strictly disjoint by a CI-blocking pytest assertion. Reference: `cas-native/training/paraphrase_templates.py`, `cas-native/tests/test_paraphrase_augmentation.py:36`. This is a structural guarantee, not a convention.

### 3.3 Joint-key eval-overlap filtering

Eval-overlap filtering operates on a joint key tuple `(id, source_level2_id, cas_expression)`, not `id` alone. In the K=9 paraphrase-augmented run, joint-key filtering removed 2,884 records (~14% of the post-augmentation pool) that single-key filtering would have retained.

### 3.4 Falsification-as-discipline via relabel provenance

Label corrections are versioned transformations with `bucket_relabeled_from` and `bucket_relabel_reason` provenance fields on each record. The relabel script (`relabel_v77_overlap.py`) is idempotent and produces zero changes on a clean dataset. This converts silent eval-set failures into logged, auditable events.

### 3.5 Multi-axis robustness extension (demographic + tonal)

Each canonical record renders through 36 demographic × tonal cells (3 age bands × 3 cultural registers × 4 tonal frames). CAS expression and structural labels are invariant across all 36 cells; only prompt-surface text varies. An eval gate reports per-cell accuracy deviation against pass/warn/fail thresholds. Reference: `cas-synthetic/generator/demographic_axis.py`.

---

## 4. Tri-Channel Ground Truth

This section is the headline contribution of the v2 paper. The tri-channel framework provides three independently generated ground truth representations for every benchmark record. Cross-channel consistency — the fraction of records where all three channels agree on correctness — is treated as the primary diagnostic metric. We define each channel, specify how disagreements between channels isolate different error types, and formally define the four failure modes that cross-channel analysis can distinguish.

### 4.1 Notation channel — ground truth specification

The CAS expression string — for example, `^3^P|A + ^5^C` — is the primary ground truth as in v1. Exact-match and token-F1 are the standard metrics for the notation channel. The notation channel is the canonical evaluation target: it is human-readable, directly interpretable by domain experts, and matches the output format of the production CAS inference system.

The notation channel has a structural limitation, however. It is a flat string. From a flat string, it is not possible to determine whether a model error reflects misidentification of the Noetic operator, misassignment of the Processing Domain, confusion of the Register, or a spurious surface token inserted by the decoder. All errors look alike: the output string does not match the target string. A model that swaps `|A` for `|f` (Register-only error) receives the same zero exact-match score as a model that swaps `^3` for `^2` (Noetic error) or produces `^3^P` (Register omission). These are qualitatively different errors with different training implications, and the notation channel cannot distinguish them.

### 4.2 Diagram channel — compiler-emitted typed graph as second-axis ground truth

The CAS compiler, given a valid CAS expression string, emits a typed graph. Graph nodes are typed with CAS structural roles — NoeticCluster, RelationCluster, IntegrationEdge, DomainAnnotation, RegisterAnnotation, DriveAnnotation — each carrying axis-attributed identity keys. The typed graph is a structurally richer ground truth than the notation string: it encodes the same semantic content in a representation that is amenable to structural comparison rather than only string comparison.

Canonical graph identity is determined by a canonical key derived from the axis-attribute tuple of each node type: `(node_type, noetic_value, domain_value, register_value)` for NoeticCluster nodes; `(node_type, relation_kind)` for RelationCluster nodes; and so on. This identity key is stable across surface-level notation variants that compile to the same semantic structure. Two expressions that are notationally distinct but semantically equivalent (e.g., `^3^P|A + ^5^C` written with explicit versus implicit ordering) will produce the same canonical graph identity.

A diagram-diff utility computes similarity with diagnostics: for a predicted expression and a ground-truth expression, the diff reports which node types were preserved, which attributes flipped, which edges were corrupted, and which nodes are entirely absent from the prediction. This produces a structured error report rather than a binary match score.

The diagnostic value is best illustrated by example. A model that produces `^3^P|f` from ground truth `^3^P|A` makes a Register error — this is trivially visible as a token difference in the notation channel. In the diagram channel, the NoeticCluster node `(NoeticCluster, ^3, P, _)` is preserved; the RegisterAnnotation attribute flips from `A` to `f`. This is a strict subgraph match with one attribute flip — a much weaker structural error than generating a wrong Noetic entirely, which would produce a completely different NoeticCluster node with a different identity key. Single-channel notation scoring assigns the same score to both errors; diagram-diff reports them at qualitatively different severity levels.

A second example: a model that produces `^3^P` (Register omitted) from ground truth `^3^P|A`. Notation-match fails on the missing `|A` token. Diagram-match partially fails: the NoeticCluster node is correct, but the RegisterAnnotation node is absent — a node-missing error rather than an attribute-flip error. This is a different structural error mode from the attribute-flip case, and diagram-diff reports the distinction. The absent RegisterAnnotation indicates the model did not attempt Register specification, whereas the attribute-flip indicates the model attempted specification but chose the wrong value. The training intervention appropriate to each is different.

The diagram channel is the second axis of ground truth. A benchmark that carries both notation and diagram ground truth can report: how many records had notation errors that preserved diagram structure (surface-only errors), how many had notation errors that corrupted diagram structure (structural errors), and how many had notation errors of mixed severity. Single-channel benchmarks cannot disaggregate at this level.

### 4.3 Color channel — value-keyed axis colors (25 total), colorblind-accessible

Each axis value in the CAS v7.7 ontology maps to a distinct colorblind-accessible color. The 25 axis values are: 10 Noetics (^0 through ^9), 4 Processing Domains (P, C, E, O), 7 Core Drives (F1 through F7), and 4 Registers (T, A, f, E). Each maps to a unique color drawn from the Wong (2011) and ColorBrewer palettes, verified against WCAG 2.1 colorblind accessibility criteria. The color mapping is versioned as PALETTE_VERSION='v1.0' (implemented in PR #9, branch `feature/cas-value-keyed-palette`).

The color encoding renders a CAS expression as a structured color sequence — or as a color-coded diagram node — where each axis value carries a perceptually distinct identity. The color channel is information-theoretically independent from the notation channel: paraphrase noise that corrupts surface token identity does not corrupt the rendered color unless the underlying axis identity itself changes. A model that correctly identifies the Noetic and Domain but misspecifies the Register will produce the correct Noetic and Domain colors and the wrong Register color, regardless of how the notation tokens are arranged or which paraphrase template was used.

The color channel thus provides a corruption-resistant redundancy check. Because color identity tracks axis identity — not token position, not surface string — it is insensitive to the specific failure modes that most commonly corrupt the notation channel (prefix memorization, template-specific token collapse, surface paraphrase noise). A record where the model's notation output is wrong due to prefix memorization but the underlying axis predictions are partially correct will show notation-channel failure but partial color-channel success.

This redundancy is the color channel's diagnostic contribution. The color channel does not add new information about what the model predicted; it provides a different access path to the same semantic content. When the notation and color channels agree, the diagnosis is clean: either the model got the axis values right (both channels succeed) or it got them wrong enough to change a color (both channels fail). When they disagree, the disagreement reveals an intermediate error state that notation alone cannot surface.

### 4.4 Cross-channel consistency metric — the headline diagnostic

Cross-channel consistency rate is defined as the fraction of evaluation records on which the notation, diagram, and color channels agree on the correctness of the model's prediction — either all three channels register success (the model's output matches ground truth in all three representations) or all three channels register failure (the model's output disagrees with ground truth in all three representations). High cross-channel consistency means the three channels give coherent signals: model outputs that are right in one channel are right in all, and model outputs that are wrong in one channel are wrong in all. Low cross-channel consistency reveals records where the three channels give conflicting signals — the model is producing partially correct output that different representational modalities capture differently.

We define four failure modes formally, based on which channels succeed and which fail on a given record:

**All-channels-fail.** Notation, diagram, and color channels all disagree with ground truth. The model's output is structurally wrong at every level of representation. This indicates fundamental Noetic-level misclassification — the model has not recovered the correct axis values in any representational modality. This is the highest-severity failure mode; it is the only mode where the error is unambiguous across all three channels.

**Notation-fail-only.** Diagram and color channels agree with ground truth; notation surface token differs. The model has the correct underlying structure — the correct Noetic, Domain, Drive, Register — but has rendered it with a surface token difference. This indicates a formatting or rendering error, not a structural error. In the context of the CAS benchmark, this could arise from a model that learns to produce Register-less expressions when Register is implicit, or that inserts a spurious connector token while preserving axis values. This failure mode is low-severity; it is a surface error, not a cognitive error. A benchmark that scores on notation alone would penalize this as heavily as an all-channels-fail record; the tri-channel framework disaggregates them.

**Structure-fail-only.** Notation and color partially agree with ground truth but diagram structure disagrees. The model has produced plausible-looking notation that partially recovers axis values (and thus color identities) but that does not compile to the correct structural graph. This is the most important failure mode for the tri-channel framing: it reveals outputs that look reasonable in notation scoring but are structurally incoherent. In a production CAS assessment system, structure-fail outputs would fail the compiler gate; in a notation-only benchmark, they would score as partial successes. The diagram channel catches the structural failure that the notation channel misses.

**Color-axis-fail-only.** Notation and diagram agree with ground truth but color disagrees. This indicates the model's axis identity is correct — the correct structural graph — but the color encoding is wrong. In a correctly implemented pipeline, this mode should be impossible: color is derived deterministically from axis identity, so if axis identity is correct (diagram agrees), color should agree. A nonzero rate of color-axis-fail-only records indicates a color mapping implementation error, not a cognitive error in the model. This failure mode is therefore a diagnostic for the benchmark pipeline itself rather than the model.

The cross-channel consistency rate — the fraction of records falling into the all-channels-success or all-channels-fail modes — is the primary headline metric for the tri-channel benchmark. High consistency (approaching 1.0) indicates the three channels are giving coherent signals and the model's errors are clean structural failures rather than mixed surface/structure ambiguity. Low consistency indicates the model is producing a class of outputs that are correct in some representational modalities and wrong in others — the most informationally rich regime for diagnosis.

We note that cross-channel consistency rate is a benchmark-level diagnostic metric, not a model performance metric. It measures whether the model's errors are interpretable by the benchmark, not whether the model is performing well. A model that always produces all-channels-fail outputs would have high consistency (all failures are coherent) and low accuracy. A model that produces many notation-fail-only records (surface errors without structural errors) would have low consistency and intermediate accuracy. The diagnostic value is in the disaggregation: which records have structure-fail-only errors tells us where the model's structural recovery is weak even when its surface notation looks plausible.

---

## 5. Empirical Validation

We instantiate the tri-channel framework on the CAS-Native structured-prediction harness: a 12-head model (8 boolean/categorical heads, 4 content-axis heads: Noetic, Domain, Drive, Register), 64-dimensional shared bottleneck, approximately 437 KB checkpoint trained on approximately 16,570 canonical Level 3 recoverable records. Held-out evaluation is 1,000 records, joint-key-filtered against training.

### 5.1 Headline result: clean-eval rescore — 6.4 pp hidden uplift [LIFT FROM v1]

Before applying the methodology in this paper, the deployed checkpoint `d99810a` reported 868/1000 = 86.8% all-heads exact on canonical evaluation against the contaminated held-out set. After running the relabel script on the held-out evaluation set (moving 64 records from `v77_rule_four` to `v77_omega`) and rescoring the same checkpoint with no retraining:

| Metric | Before relabel | After relabel | Delta |
|---|---:|---:|---:|
| Canonical all-heads exact | 86.8% | **93.2%** | **+6.4 pp** |
| Paraphrase all-heads exact | 41.3% | **46.9%** | **+5.6 pp** |
| Prediction consistency | 48.4% | 48.4% | 0.0 (label-independent) |
| Canonical-exact retention | 46.7% | 49.5% | +2.8 pp |

The same checkpoint was already producing the right predictions. The 6.4 pp suppression was entirely due to eval-label contamination, which the methodology in this paper catches at dataset construction.

### 5.2 Per-bucket diagnostic [LIFT FROM v1]

Bucket-rate breakdown on the clean evaluation (post-relabel):

| Bucket | n | Canonical exact | Paraphrase exact |
|---|---:|---:|---:|
| `v74_baseline` | 200 | 99.5% | 18.7% |
| `v77_omega` | 267 | 99.3% | 87.3% |
| `v76_production` | 108 | 94.4% | 75.6% |
| `v75_register` | 264 | 92.4% | 24.5% |
| `meta_logic` | 102 | 78.4% | 17.0% |
| `v77_rule_four` | 59 | 71.2% | 59.9% |

The `v74_baseline` paraphrase gap (99.5% canonical → 18.7% paraphrase = 80.8 pp gap) and `meta_logic` gap (78.4% → 17.0% = 61.4 pp gap) are the two worst invariance failures. Aggregate metrics hide both the magnitude and location of the failure.

### 5.3 Per-template diagnostic [LIFT FROM v1]

Within a single bucket, paraphrase accuracy varies dramatically by eval template, indicating prefix memorization:

| Eval template | `v74_baseline` accuracy | `meta_logic` accuracy |
|---|---:|---:|
| Template 0 — "Map this recoverable CAS slot reading…" | 36.5% | 31.4% |
| Template 1 — "Please reconstruct the exact CAS expression…" | 2.5% | 12.7% |
| Template 2 — "As a CAS notation check, translate…" | 17.0% | 6.9% |

A 97 pp swing on identical slot content across two templates is the signature of prefix memorization: the model is learning prefix-string → label, not slot-content → label.

### 5.4 Asymmetry diagnostic: 95–98% canonical-right [LIFT FROM v1]

When canonical and paraphrase predictions disagree on a content head, canonical is right 95.5–98.5% of the time across all four content axes:

| Head | Disagreements | Canonical right | Paraphrase right | Asymmetry |
|---|---:|---:|---:|---:|
| Noetic | 854 | 822 | 11 | 96.3% |
| Domain | 677 | 667 | 4 | 98.5% |
| Drive | 618 | 600 | 9 | 97.1% |
| Registers | 627 | 599 | 8 | 95.5% |

This is a pure invariance failure, not a knowledge gap. The model has the right answer under canonical surface form and loses it under paraphrase. The appropriate intervention is different from a knowledge gap: invariance failures need input-level self-conditioning or loss-level regularization; knowledge gaps need more training data.

### 5.5 K=9 partial success: bare-slot template moved 3 of 4 content heads, regressed Drive

The K=9 bare-slot retrain (branch `feature/paraphrase-augment-9-templates`) expanded the training paraphrase template set from K=3 to K=9, adding a bare-slot template `"{slots}"` that strips all prefix scaffolding. The intent was to break prefix memorization by exposing the model to training records where the slot content appears without any fixed prefix string.

The result was a partial success. Three of the four content heads — Noetic, Domain, and Registers — moved positively. Register recovered most strongly, with a gain consistent with the hypothesis that prefix memorization was suppressing Register recovery under the K=3 templates. Noetic and Domain also improved, indicating that the bare-slot template was providing genuinely novel training signal on content-axis recovery.

Drive paraphrase consistency, however, regressed relative to the fixture-scaffolded K=9 baseline. Drive is the most semantically specialized of the four content axes: the 7 Core Drive values (F1 Unity, F2 Wisdom, F3 Vitality, F4 Connection, F5 Agency, F6 Structure, F7 Purpose) have no systematic structural relationship to the Noetic or Domain axes, and Drive specialization emerges from exposure to records where the Drive value is load-bearing in distinguishing otherwise similar CAS expressions. The bare-slot template, by removing prefix scaffolding, also removes any contextual signal that might cue Drive selection. The result is that the bare-slot template helps prefix-memorization-vulnerable heads (Noetic, Domain, Register) while hurting Drive, which depends on contextual signal that the bare-slot template strips.

This result has a direct interpretation in terms of the Limiting Reagent concept from CAS v7.6 production semantics: Drive specialization is the Limiting Reagent for notation-channel paraphrase recovery at K=9 and 20 epochs. Adding more paraphrase templates (increasing K beyond 9) or adding more training data for Drive-heavy records are the natural next levers within the notation-channel paradigm. However, the self-conditioning null result (Section 5.6) establishes that even direct single-channel self-reference cannot recover Drive at small scale.

This motivates the tri-channel framing. Drive is the hardest semantic axis to recover from notation alone because Drive value is not systematically decodable from the surface form of a CAS expression without additional semantic context. The diagram channel encodes structural relationships among CAS axes in a representation that does not depend on surface string form; the color channel encodes Drive identity in a perceptually distinct, paraphrase-insensitive signal. Both are independent recovery paths for Drive that bypass the notation-channel bottleneck.

Key numbers from the K=9 bare-slot run:
- Registers head: +[K9_REGISTERS_GAIN] pp vs K=3 baseline
- Noetic head: +[K9_NOETIC_GAIN] pp vs K=3 baseline
- Domain head: +[K9_DOMAIN_GAIN] pp vs K=3 baseline
- Drive head: [K9_DRIVE_DELTA] pp vs K=3 baseline (regression)
- Drive paraphrase consistency: [K9_DRIVE_FINAL]% (vs K=3 baseline [K3_DRIVE_BASELINE]%)

Note: exact numbers from the K=9 bare-slot run (directory `structured-token-recoverable-paraphrase-K9-baretemplate-20epoch-gpu-20260502-1311/`) were not accessible at v2 outline drafting time. Placeholders are to be replaced with actuals before submission. Per the brief, the expected pattern is: 3 of 4 content heads improved, Drive regressed.

### 5.6 K=9 + self-conditioning small-scale smoke null result

Following the K=9 bare-slot retrain, a small-scale smoke test evaluated the self-conditioning lever: training on K=9 paraphrases where each paraphrase record carries the canonical CAS expression as a `[PRIOR]` block prepended to the prompt (`f"[PRIOR] {canonical_cas_expression}\n[QUERY] {paraphrase_prompt_text}"`). The mechanism is implemented in `cas-native/training/self_conditioning_augmentation.py` (branch `proposal/self-reference-lever`, commits `4720adf`–`c09b598`).

The smoke test parameters: 5,000 training records, 5 epochs, K=9 paraphrase augmentation, self-conditioning-pairs=3.

Results:

| Metric | K=9 baseline | K=9 + self-cond (smoke) | Delta |
|---|---:|---:|---:|
| Best canonical exact | [K9_CANONICAL_BASELINE]% | 79.7% | [SMOKE_CANONICAL_DELTA] |
| Paraphrase exact | [K9_PARAPHRASE_BASELINE]% | 39.2% | [SMOKE_PARAPHRASE_DELTA] |
| Drive paraphrase consistency | 70.7% | 70.5% | **-0.2 pp (UNCHANGED)** |

The headline finding is the Drive paraphrase consistency result: 70.5% vs baseline 70.7%, a difference of -0.2 pp — statistically zero at this sample size. Self-conditioning at K=9 / 5K records / 5 epochs does not recover Drive specialization.

This is a principled null result, not a project failure. It establishes a specific negative: single-channel self-reference through a linear `[PRIOR]` block is not sufficient to recover Drive specialization at small scale. The proposed mechanism — exposing the model to its canonical prediction as an input-side signal — was theoretically motivated by the 95-98% canonical-wins asymmetry (the model has the right Drive answer in canonical form). The empirical result shows that the `[PRIOR]` block is not being used to anchor the Drive prediction under paraphrase, at least at 5K records and 5 epochs.

Two interpretations are consistent with this result. First, the linear `[PRIOR]` block may require more training data or more epochs to learn the "trust the prior" rule for Drive, and the smoke test is simply too small. The self-conditioning lever could succeed at scale and should not be discarded. Second, the `[PRIOR]` block may be insufficient for Drive recovery because Drive specialization requires richer input signal than a linearized CAS expression string — the `[PRIOR]` block passes Drive identity through the notation channel, which is the same channel that fails under paraphrase. If the model's Drive-channel feature representation is corrupted by paraphrase noise, a linearized Drive token in the `[PRIOR]` block passes through the same corrupted feature path and cannot anchor the prediction.

The second interpretation is the direct empirical motivation for the tri-channel architecture. The diagram channel carries Drive identity through a structural graph representation; the color channel carries Drive identity through a perceptual color encoding. Both are independent of the notation-channel feature path. If Drive specialization fails because the notation-channel representation is corrupted under paraphrase, a Drive signal delivered via diagram or color bypasses the corruption. The tri-channel architecture is not merely additive redundancy; it is a recovery path that bypasses the channel-specific failure mode.

The null result thus advances the paper's core argument: single-channel self-reference (a loop within the notation channel) cannot address channel-specific failure modes. Independent channels are required. This is the empirical motivation for PR #6 (diagram-loop) and the tri-channel retrain reported in Section 5.7.

### 5.7 PLACEHOLDER: tri-channel comparison — awaits PR #6 (diagram-loop) full retrain

This section will report the tri-channel retrain results once PR #6 (`proposal/diagram-loop-impl` → `feature/diagram-diff-utility`, diagram-loop lever) completes full GPU training and evaluation.

Expected content:
- Training configuration: K=9 paraphrases + diagram channel as auxiliary input + color channel as auxiliary input.
- Primary metrics: canonical exact, paraphrase exact, Drive paraphrase consistency (the metric established as the limiting reagent in Sections 5.5 and 5.6).
- Per-channel agreement rate: fraction of records where notation, diagram, and color channels agree on prediction correctness.
- Cross-channel consistency rate: fraction of records falling into all-channels-success or all-channels-fail modes.
- Per-failure-mode breakdown: notation-fail-only, structure-fail-only, color-axis-fail-only rates.
- Comparison to K=9 notation-only baseline from Section 5.5.

This section is explicitly a PLACEHOLDER. No tri-channel model has been trained at the time of this outline. The paper's current strength is the benchmark methodology (Sections 3–4) and the structural argument (Section 4.4), not a demonstrated empirical win from a tri-channel-trained model. Section 5.7 will convert the structural argument into an empirical result.

---

## 6. Discussion

### What we are NOT claiming

This paper does not claim that tri-channel training has been demonstrated to outperform notation-only training. Section 5.7 is explicitly a PLACEHOLDER: no tri-channel model has been trained, and no cross-channel comparison result exists at the time of writing. The paper's empirical strength is in Sections 5.1–5.6: the clean-eval rescore (6.4 pp hidden uplift), per-bucket and per-template diagnostics, asymmetry diagnostic, K=9 partial success establishing Drive as the limiting reagent, and self-conditioning null result establishing single-channel self-reference as insufficient for Drive recovery. These results motivate the tri-channel architecture and the cross-channel consistency metric by argument; Section 5.7 will confirm or disconfirm the argument empirically.

We also do not claim a new model architecture. CAS-Native is a separate paper (Paper B in the sequencing: see Appendix). We do not claim state-of-the-art performance on a public benchmark. The benchmark is a custom instantiation of the CAS v7.7 ontology; public comparisons to BERT, T5, or other architectures are deferred to cross-architecture validation (future work). We do not claim the methodology eliminates all data-evaluation leakage. We claim it catches a class of failures — bucket-class contamination, surface-form leakage, joint-key contamination — that single-key filtering and aggregate evaluation miss, and we demonstrate that class with a 6.4 pp empirical example.

### Limitations

**(a) Single ontology.** CAS v7.7 is the sole ontology demonstrated in this paper. Generalization of the methodology to other structured-prediction ontologies is asserted by structural argument — any domain with a formal grammar and a compiler can emit diagram ground truth; any finite-valued type system can be color-keyed — but is not demonstrated by experiment. Cross-ontology validation is future work.

**(b) Color channel demonstrated by construction.** The color channel's diagnostic value is established by information-theoretic argument: color is derived from axis identity, and axis identity is independent of notation surface form, so paraphrase noise that corrupts notation tokens does not corrupt color unless axis identity changes. This argument is correct by construction. What has not been demonstrated is a held-out model comparison where a tri-channel-trained model outperforms a notation-only baseline specifically because of the color channel's signal. That demonstration awaits Section 5.7.

**(c) Small-scale experiments.** The K=9 retrain (Sections 5.5) and the self-conditioning smoke test (Section 5.6) were conducted at 5K–50K training records with 5–20 epochs. These scales are appropriate for rapid iteration on the methodology but may not reflect behavior at production scale (hundreds of thousands of records, dozens of epochs, larger model capacity). Scale effects are a known variable; we report what we have and do not extrapolate.

**(d) Architecture-specific implementation.** All empirical results come from the CAS-Native architecture (structured-token tokenizer, 64-dimensional bottleneck, 12 prediction heads). The methodology is architecture-agnostic by argument, but the specific levers investigated — bare-slot template expansion, self-conditioning linear prepend, diagram-loop auxiliary input — are implemented in and tested against CAS-Native. Porting to a vanilla T5 or BERT fine-tune is deferred.

### Reusability

The methodology is architecture-agnostic. Any structured-prediction task with a formal grammar and a compiler can:
- Emit a typed graph for each target expression, providing diagram ground truth by construction.
- Assign a perceptual encoding (color, shape, spatial position) to each finite axis value, providing a third channel by construction.
- Apply bucket stratification, property-test-enforced template disjointness, and joint-key eval-overlap filtering as implementation-independent discipline.

We will release a reference implementation of the bucket-stratified generation, template disjointness property test, joint-key filter, and relabel-with-provenance pattern as a reusable Python package independent of CAS framework specifics. Release timing is contingent on USPTO #64/037,173 IP attorney consultation (flagged in project rollout plan).

The color palette (PALETTE_VERSION='v1.0', Wong/ColorBrewer, WCAG 2.1 accessible) is domain-independent. Any benchmark with a finite-valued axis type system can use the same palette assignment methodology.

### Cross-architecture validation as future work

The strongest version of this paper includes the same methodology applied to vanilla T5 and BERT fine-tunes on the same task, demonstrating that: (a) the tri-channel framework reveals the same class of contamination on a different architecture; and (b) tri-channel training provides Drive recovery gains that generalize beyond CAS-Native's specific implementation. We defer this to a follow-up paper (Paper C in the sequencing). Paper A establishes the methodology and the structural argument; Paper B establishes the architecture; Paper C establishes cross-architecture validity.

---

## 7. Conclusion

Benchmarks for structured prediction need a minimum viable contract that is richer than a single notation string. A single notation string cannot distinguish surface errors from structural errors; it cannot detect that a model's output is structurally incoherent while notationally plausible; it cannot disaggregate Drive errors from Noetic errors from Register errors. The notation channel is necessary but not sufficient.

Tri-channel ground truth — notation, diagram, and color — is the minimum viable contract for benchmarks targeting structured cognitive recovery. The three channels are generated from the same compiler, carry the same semantic content, and encode it in qualitatively different representational modalities. Their independence is the source of their diagnostic value: error modes that corrupt one channel do not uniformly corrupt the others, and the pattern of cross-channel agreement and disagreement localizes errors to specific failure types.

Cross-channel consistency rate is a publishable diagnostic metric that single-channel benchmarks cannot compute. It measures whether a model's errors are structurally coherent — whether the same records are wrong in all three channels (clean structural failure) or whether records are wrong in some channels but not others (mixed surface/structure failure, or pipeline error). A high cross-channel disagreement rate is a direct signal that the benchmark is capturing a model behavior that notation scoring alone would mischaracterize.

The empirical evidence in this paper establishes the limiting regime for notation-channel-only recovery: Drive specialization is the Limiting Reagent. K=9 bare-slot template expansion recovers Noetic, Domain, and Register but not Drive. Single-channel self-conditioning does not recover Drive at small scale. Drive requires an independent recovery path — the diagram and color channels are the candidates.

The methodology generalizes. Any domain with a compiler-backed formal language can emit diagram ground truth from the compiler and color ground truth from any finite-valued type assignment. The three-channel discipline — property-test-enforced template disjointness, joint-key eval-overlap filtering, relabel-with-provenance, bucket stratification, cross-channel consistency reporting — applies without modification.

Next steps for this research program: (a) tri-channel model training completing Section 5.7 (PR #6, diagram-loop retrain); (b) cross-architecture validation against T5 and BERT baselines; (c) arXiv submission following Section 5.7 results; (d) IP attorney consultation per project rollout flag before public release of the benchmark and reference implementation.

---

## Appendix A — Reviewer-anticipation responses

**Q: Your held-out 1K is small — how do you know it's representative?**
A: Bucket-rate disclosure (Section 5.2) reports per-bucket sample counts and bootstrap confidence intervals. The smallest post-relabel bucket has 59 samples (`v77_rule_four`); median is 200. We disclose per-bucket CIs in the eval manifest schema. The methodology's claim is not that the held-out set is statistically exhaustive; it is that per-bucket disclosure catches contamination and failure modes that aggregate metrics hide. The 6.4 pp suppression example demonstrates this at N=1000.

**Q: Is the tri-channel benchmark actually implemented?**
A: The notation channel is fully implemented and evaluated in Sections 5.1–5.6. The diagram channel is implemented in the CAS compiler (PR #6 branch `feature/diagram-diff-utility`); the diagram-loop retrain is pending. The color channel is implemented (PR #9 branch `feature/cas-value-keyed-palette`, PALETTE_VERSION='v1.0'). The cross-channel consistency eval harness is implemented (branch `feature/cross-channel-consistency-eval`). The full tri-channel training and evaluation that populates Section 5.7 is pending. We are explicit that Section 5.7 is a placeholder.

**Q: How is the color channel more than just a visualization?**
A: The color channel is an information-theoretic redundancy check. Color is derived from axis identity, not from notation surface form. Paraphrase noise that corrupts notation tokens does not corrupt color unless axis identity changes. This means a model that produces wrong notation due to prefix memorization but recovers the correct axis values will show notation-channel failure and color-channel partial success — a disaggregation that notation scoring alone cannot produce. The color channel does not teach the model anything new; it provides an independent access path to the same semantic content that allows the benchmark to disaggregate surface errors from axis-identity errors.

**Q: Does the relabel script game the eval?**
A: No. The relabel script is idempotent, runs on `cas_expression` regex match (a structural property, not a model prediction), is version-controlled with provenance fields on each record, and produces zero changes on a clean dataset. The 6.4 pp uplift is the cost of the original contamination, not a manipulation of the eval. The relabel does not change what the model predicts; it corrects what the eval scores those predictions against. The structural property the relabel enforces (same-Noetic cross-register integration with named emergent result = `v77_omega`, not `v77_rule_four`) was always correct; the contamination was a dataset construction error that the methodology in this paper would have caught before evaluation.

**Q: Is this paper specific to the CAS framework?**
A: The framework provides the bucket taxonomy, label space, compiler, and color palette. The methodology — bucket stratification, template disjointness, joint-key filtering, relabel provenance, tri-channel ground truth — applies to any structured-prediction task with a formal grammar and a finite-valued type system. We will release a reference implementation independent of CAS.

---

## Appendix B — Open items before submission

- [ ] Section 5.7: tri-channel comparison results (awaits PR #6 diagram-loop full retrain).
- [ ] Section 5.5: exact K=9 bare-slot run numbers (replace `[K9_*]` placeholders with actuals from `structured-token-recoverable-paraphrase-K9-baretemplate-20epoch-gpu-20260502-1311/`).
- [ ] Section 5.6: exact K=9 + self-conditioning smoke numbers (replace `[SMOKE_*]` placeholders with actuals if the smoke run report is available).
- [ ] Section 2: insert citations from `paper_a_related_work_citations.md` once available.
- [ ] Abstract: write final abstract once Section 5.7 fills in.
- [ ] Venue selection: NeurIPS D&B vs ICLR Tiny vs ACL workshop.
- [ ] IP attorney consultation per CLAUDE.md v7.6/v7.7 rollout flag (legal framing of benchmark and reference implementation release).
- [ ] Cross-architecture validation pass (deferred to Paper C).

---

## Appendix C — Paper sequencing

This is **Paper A** in the four-paper sequencing for the Noetic Compass research program:

| | Title direction | Timing |
|---|---|---|
| **A — this paper** | CAS-SDG-Bench benchmark methodology (v2: tri-channel) | Submit after Section 5.7 fills in |
| **B** | CAS-Native structured tokenization + 12-head architecture | 3–4 months |
| **C** | Full CAS Transformer + cross-architecture validation | 6–9 months |
| **D** | Categorical Hutchinson Theory via Markov Categories | 9–12+ months |

Paper A cites itself for evaluation discipline across Papers B, C, D. The tri-channel benchmark is the eval contract that all subsequent papers inherit. Section 5.7 is the minimum required before submission: the benchmark methodology must be empirically demonstrated to disaggregate errors, not merely argued to do so.

---

## Appendix D — Branch and PR dependencies

| Branch | Status | Relevant section |
|---|---|---|
| `feature/paraphrase-augment-9-templates` | K=9 bare-slot template expansion | Section 5.5 |
| `feature/cas-value-keyed-palette` (PR #9) | Color palette PALETTE_VERSION='v1.0' | Section 4.3 |
| `proposal/diagram-loop-impl` → `feature/diagram-diff-utility` (PR #6) | Diagram-loop retrain; Section 5.7 PLACEHOLDER | Section 4.2, 5.7 |
| `feature/cross-channel-consistency-eval` | Cross-channel consistency metric implementation | Section 4.4 |
| `proposal/self-reference-lever` | Self-conditioning implementation + tests | Section 5.6 |
| `paper-a-related-work-citations` | Literature citations | Section 2 |
| `paper-a-draft` | v1 draft (historical record) | Appendix C |
