# Paper A — Related-Work Citations

**Paper title:** *Bucket-Stratified Synthetic Data with Held-Out Invariance Discipline for Ontology-Constrained Structured Prediction*

This document provides citation-ready related work for the six areas addressed in Paper A. Each section maps to a methodological pillar of the paper's argument: that synthetic training data is most useful when (a) generation is stratified by structural failure mode, (b) eval surface forms are held disjoint from training forms by construction, and (c) eval-overlap filtering operates on joint-key tuples within an ontology-constrained output space.

---

## Section 1: Behavioral / Bucketed Evaluation of NLP Models

Paper A's core eval design — bucketing test cases by structural failure mode and reporting per-bucket metrics — extends a tradition of behavioral testing initiated by CheckList and broadened by multi-scenario frameworks such as HELM and BIG-Bench.

---

- **Ribeiro, M. T., Wu, T., Guestrin, C., and Singh, S. (2020).** *Beyond Accuracy: Behavioral Testing of NLP Models with CheckList.* ACL 2020 (Best Paper). ACL Anthology: 2020.acl-main.442. arXiv: 2005.04118.
  - Anchor reference: introduces the capability-bucket × test-type matrix (MFT / INV / DIR) that Paper A's per-failure-mode eval design inherits.
  - "Inspired by principles of behavioral testing in software engineering, CheckList is a task-agnostic methodology for testing NLP models that includes a matrix of general linguistic capabilities and test types to facilitate comprehensive test ideation." The INV (Invariance) test type directly anticipates Paper A's held-out surface-form invariance discipline.

- **Kiela, D., Bartolo, M., Nie, Y., Kaushik, D., Geiger, A., Wu, Z., … Williams, A. (2021).** *Dynabench: Rethinking Benchmarking in NLP.* NAACL 2021. ACL Anthology: 2021.naacl-main.324. arXiv: 2104.14337.
  - Shows that static benchmarks saturate quickly and that adversarial, human-in-the-loop data collection produces harder, more diagnostic evaluation sets — motivating the iterative failure-mode-stratified generation design of Paper A.
  - "Contemporary models quickly achieve outstanding performance on benchmark tasks but nonetheless fail on simple challenge examples and falter in real-world scenarios." DynaBench's dynamic collection directly addresses the coverage gap that Paper A's bucketed generation is designed to fill.

- **Liang, P., Bommasani, R., Lee, T., et al. (2022).** *Holistic Evaluation of Language Models (HELM).* Transactions on Machine Learning Research (TMLR), 2023. arXiv: 2211.09110.
  - Provides a multi-scenario, multi-metric benchmarking framework that Paper A cites as precedent for multi-axis (bucket × metric) structured reporting of model performance.
  - "HELM measured 7 metrics (accuracy, calibration, robustness, fairness, bias, toxicity, and efficiency) for each of 16 core scenarios." HELM's scenario taxonomy is a direct predecessor to Paper A's failure-bucket taxonomy.

- **Srivastava, A., Rastogi, A., Rao, A., et al. (BIG-bench Collaboration) (2022).** *Beyond the Imitation Game: Quantifying and Extrapolating the Capabilities of Language Models.* TMLR 2023. arXiv: 2206.04615.
  - Demonstrates that a 204-task collaborative benchmark with fine-grained task categorization exposes capability gaps invisible to aggregate metrics — the scale argument for Paper A's per-bucket reporting rather than aggregate accuracy.
  - "Tasks that exhibit 'breakthrough' behavior at a critical scale often involve multiple steps or components"; per-task granularity is required to detect this, analogous to Paper A's per-failure-mode granularity requirement.

---

## Section 2: Held-Out Invariance / Paraphrase Robustness

Paper A requires that eval surface forms be disjoint from training surface forms by construction (held-out invariance discipline). The papers below establish that NLI and related systems exploit surface-form regularities in training data and fail when these regularities are removed.

---

- **Glockner, M., Shwartz, V., and Goldberg, Y. (2018).** *Breaking NLI Systems with Sentences that Require Simple Lexical Inferences.* ACL 2018 (short paper). ACL Anthology: P18-2103. arXiv: 1805.02266.
  - Establishes that NLI models fail when evaluation sentences differ from training sentences by only one word, directly motivating Paper A's joint-key tuple filter for surface-form overlap.
  - "Performance on this new test set was substantially worse across systems trained on SNLI, demonstrating limited generalization ability." This shows that even single-word surface overlap between train and eval inflates performance, exactly the leakage mode Paper A's held-out discipline addresses.

- **Naik, A., Ravichander, A., Sadeh, N., Rose, C., and Neubig, G. (2018).** *Stress Test Evaluation for Natural Language Inference.* COLING 2018. ACL Anthology: C18-1198. arXiv: 1806.00692.
  - Constructs six stress-test categories for NLI (competence, distraction, noise, etc.) that each isolate a distinct failure mode, establishing the bucket-per-failure-mode eval paradigm Paper A adopts.
  - The authors held evaluation examples disjoint from training by structural category, finding that "state-of-the-art models fail under specific linguistic and semantic conditions," demonstrating that per-category held-out eval reveals failures invisible to held-out accuracy.

- **McCoy, R. T., Pavlick, E., and Linzen, T. (2019).** *Right for the Wrong Reasons: Diagnosing Syntactic Heuristics in Natural Language Inference.* ACL 2019. arXiv: 1902.01007.
  - Introduces HANS (Heuristic Analysis for NLI Systems), a controlled evaluation set in which training heuristics (lexical overlap, subsequence, constituent) are systematically held disjoint from valid inferences — an explicit precursor to Paper A's held-out invariance discipline applied to surface forms.
  - "Models trained on MNLI, including BERT, performed very poorly on HANS, suggesting that they had adopted these [spurious] heuristics." The HANS split methodology — training on heuristic-confounded data, evaluating on heuristic-violated data — is the structural template Paper A generalizes to ontology-constrained structured prediction.

---

## Section 3: Synthetic Data for Structured Prediction

Paper A's generation pipeline produces training data synthetically, stratified by structural failure mode. The papers below establish that synthetic data is tractable for compositional and structured tasks and that how training sets are sampled from a synthetic distribution has large downstream effects.

---

- **Lake, B. M. and Baroni, M. (2018).** *Generalization without Systematicity: On the Compositional Skills of Sequence-to-Sequence Recurrent Networks.* ICML 2018. arXiv: 1711.00350.
  - Introduces the SCAN benchmark, the first large-scale demonstration that synthetic compositional training data can be split to isolate specific structural failure modes, directly motivating Paper A's failure-mode-stratified generation design.
  - "RNNs can learn how to 'run' and to 'run twice' when both occur in training, yet fail to generalize to 'jump twice' when 'jump' but not 'jump twice' is included." Systematic synthetic splits that expose this generalization gap are what Paper A calls failure-mode-bucketed splits.

- **Kuhnle, A. and Copestake, A. (2017).** *ShapeWorld: A New Test Methodology for Multimodal Language Understanding.* arXiv: 1704.04517.
  - Establishes that fully synthetic data generation allows experimenter-controlled coverage of concept combinations, enabling test sets that require "true generalization abilities, in particular the combination of previously introduced concepts in novel ways."
  - Demonstrates that automatic generation of artificial data according to explicit specifications provides finer diagnostic control than naturally collected corpora, a methodological principle Paper A extends to ontology-constrained label spaces.

- **Shin, R., Lin, C., Thomson, S., Chen, C., Roy, S., Platanios, E. A., Pauls, A., Klein, D., Eisner, J., and Van Durme, B. (2021).** *Constrained Language Models Yield Few-Shot Semantic Parsers.* EMNLP 2021. ACL Anthology: 2021.emnlp-main.608. arXiv: 2104.08768.
  - Shows that ontology-constrained decoding can replace large labelled training corpora by guiding a language model to produce only schema-valid outputs, making structural constraints a first-class part of the data generation pipeline.
  - Grammar masks at decode time ensure generated outputs satisfy type and validity constraints without requiring additional annotated data, which Paper A cites as the generative counterpart to its ontology-constrained output space.

---

## Section 4: Multi-Axis Fairness / Robustness Benchmarks

Paper A includes a demographic-axis section that requires multi-attribute, multi-bucket evaluation covering diverse protected characteristics. The benchmarks below collectively justify the multi-axis design and supply candidate demographic categories.

---

- **Parrish, A., Chen, A., Nangia, N., Padmakumar, V., Phang, J., Thompson, J., Htut, P. M., and Bowman, S. R. (2022).** *BBQ: A Hand-Built Bias Benchmark for Question Answering.* ACL Findings 2022. ACL Anthology: 2022.findings-acl.165. arXiv: 2110.08193.
  - Directly motivates Paper A's demographic-axis evaluation: BBQ tests QA model bias across nine social dimensions in under-informative vs. fully-informative contexts, a two-condition bucket design Paper A adapts.
  - "Models often rely on stereotypes when the context is under-informative"; testing per-demographic-group × context-type bucket separates signal from noise, exactly Paper A's argument for joint-key tuple filtering.

- **Nadeem, M., Bethke, A., and Reddy, S. (2021).** *StereoSet: Measuring Stereotypical Bias in Pretrained Language Models.* ACL 2021. ACL Anthology: 2021.acl-long.416. arXiv: 2004.09456.
  - Introduces a large-scale bias benchmark across gender, profession, race, and religion with a dual metric (bias score + language model score), establishing that demographic-axis evaluation must control for model fluency — a confound Paper A's bucket design avoids by holding output schema constant.
  - "Existing literature evaluates bias on only a small set of artificial sentences while not considering the language modeling ability of models." StereoSet's joint measurement of bias and capability establishes the need for multi-axis reporting that Paper A adopts.

- **Nangia, N., Vania, C., Bhalerao, R., and Bowman, S. R. (2020).** *CrowS-Pairs: A Challenge Dataset for Measuring Social Biases in Masked Language Models.* EMNLP 2020. ACL Anthology: 2020.emnlp-main.154. arXiv: 2010.00133.
  - Provides a minimal-pair construction methodology (stereotyping sentence vs. less-stereotyping sentence differing only in demographic marker) that is the surface-form-controlled variant of Paper A's invariance discipline applied to bias measurement.
  - "All three of the widely-used MLMs substantially favor sentences that express stereotypes in every category." The minimal-pair design isolates the demographic signal by holding all other surface features constant, validating Paper A's joint-key tuple filter approach.

- **Liang, P., Bommasani, R., Lee, T., et al. (2022).** *Holistic Evaluation of Language Models (HELM).* TMLR 2023. arXiv: 2211.09110.
  - (Also cited in Section 1.) Paper A cites HELM for its multi-scenario × multi-metric evaluation matrix, in particular HELM's explicit treatment of fairness, bias, and demographic robustness as first-class evaluation axes alongside accuracy.
  - HELM evaluates 30 models across 42 scenarios including fairness and bias metrics, demonstrating that aggregate metrics obscure per-scenario demographic disparities — the core empirical motivation for Paper A's bucketed demographic reporting.

- **Sakaguchi, K., Le Bras, R., Bhagavatula, C., and Choi, Y. (2019/2020).** *WinoGrande: An Adversarial Winograd Schema Challenge at Scale.* AAAI 2020. arXiv: 1907.10641.
  - Demonstrates that adversarial filtering (AFLITE) to remove bias from crowdsourced data produces harder evaluation sets with 15–35% lower model accuracy, establishing bias-reduction as a construction-time responsibility — a principle Paper A operationalises as eval-overlap filtering.
  - "A novel adversarial filtering algorithm AFLITE for systematic bias reduction" is applied at dataset construction time, establishing a precedent for Paper A's held-out filtering being a mandatory construction step rather than a post-hoc correction.

- **Smith, E. M., Hall, M., Kambadur, M., Presani, E., and Williams, A. (2022).** *"I'm sorry to hear that": Finding New Biases in Language Models with a Holistic Descriptor Dataset.* EMNLP 2022. ACL Anthology: 2022.emnlp-main.625. arXiv: 2205.09209.
  - Introduces HolisticBias, with ~600 descriptors across 13 demographic axes producing 450k+ sentence prompts, directly establishing the vocabulary of demographic axes that Paper A's demographic-axis bucket design draws on.
  - "HolisticBias is effective at measuring previously undetectable biases in token likelihoods from language models" by exhaustive cross-product coverage of demographic descriptors — the combinatorial axis design Paper A echoes in its bucket construction.

---

## Section 5: Eval-Set Contamination / Leakage

Paper A's held-out invariance discipline and joint-key tuple filter are responses to the contamination problem: eval sets that share surface forms with training data yield inflated, uninterpretable metrics. The papers below establish the scope and mechanisms of this problem.

---

- **Brown, T. B., Mann, B., Ryder, N., et al. (2020).** *Language Models are Few-Shot Learners (GPT-3).* NeurIPS 2020. arXiv: 2005.14165. (See §4, "Data Contamination.")
  - The GPT-3 paper is the first large-scale empirical treatment of eval contamination in a massively pre-trained model, establishing the contamination taxonomy (clean subset vs. full benchmark) that later work refines.
  - "A major methodological concern with language models pretrained on a broad swath of internet data … is potential contamination of downstream tasks by having their test or development sets inadvertently seen during pre-training." GPT-3's §4 defines the train–eval surface-form overlap problem that Paper A's construction-time filtering directly addresses.

- **Magar, I. and Schwartz, R. (2022).** *Data Contamination: From Memorization to Exploitation.* ACL 2022. arXiv: 2203.08242.
  - Distinguishes memorization (the model has seen test data) from exploitation (the model uses it to improve downstream performance), showing contamination effects depend on model size, data position, and learning rate — establishing that preventing contamination requires construction-time discipline, not post-hoc detection.
  - "Exploitation of contaminated data is influenced by factors like model size, learning rate, and the position of contaminated data, suggesting that memorization does not always lead to exploitation." Paper A's preventive filtering design sidesteps this variability entirely.

- **Sainz, O., Campos, J. A., García-Ferrero, I., Etxaniz, J., Lopez de Lacalle, O., and Agirre, E. (2023).** *NLP Evaluation in Trouble: On the Need to Measure LLM Data Contamination for Each Benchmark.* EMNLP Findings 2023. ACL Anthology: 2023.findings-emnlp.722. arXiv: 2310.18018.
  - Argues that per-benchmark contamination measurement is required because contamination causes inflated performance and wrong scientific conclusions, directly motivating Paper A's design-time disjointness guarantee rather than post-hoc contamination auditing.
  - "The worst kind of data contamination happens when an LLM is trained on the test split of a benchmark and then evaluated in the same benchmark." Paper A's joint-key tuple filter makes this impossible by construction.

- **Li, C. and Flanigan, J. (2023/2024).** *Task Contamination: Language Models May Not Be Few-Shot Anymore.* AAAI 2024. arXiv: 2312.16337.
  - Shows that LLMs perform significantly better on benchmarks released before their training data cutoff than on benchmarks released after, providing empirical evidence that temporal surface-form overlap is a widespread contamination source, and motivating temporal as well as surface-form disjointness guarantees.
  - "On datasets released before the LLM training data creation date, LLMs perform surprisingly better … strongly indicating task contamination on zero-shot and few-shot evaluation." Paper A's held-out invariance discipline prevents this by requiring construction-time surface disjointness rather than relying on temporal boundaries.

---

## Section 6: Ontology-Constrained or Schema-Aware Prediction

Paper A targets a structured prediction setting where the output space is defined by an ontology. The papers below span knowledge-injection pre-training, grammar-constrained decoding, and retrieval-augmented structured generation — the key techniques that constrain outputs to a schema-defined space.

---

- **Zhang, Z., Han, X., Liu, Z., Jiang, X., Sun, M., and Liu, Q. (2019).** *ERNIE: Enhanced Language Representation with Informative Entities.* ACL 2019. ACL Anthology: P19-1139. arXiv: 1905.07129.
  - Demonstrates that injecting knowledge-graph entities into BERT pre-training improves performance on knowledge-driven tasks, establishing that ontology structure can be a first-class training signal — Paper A's ontology-constrained output space generalises this injection principle to the label schema.
  - "ERNIE fuses lexical, syntactic, and knowledge information by stacking a textual T-Encoder with a knowledge K-Encoder to represent word tokens and entities in a unified feature space." The fusion architecture shows that schema constraints and language representations can be jointly trained.

- **Peters, M. E., Neumann, M., Logan, R., Schwartz, R., Joshi, V., Singh, S., and Smith, N. A. (2019).** *Knowledge Enhanced Contextual Word Representations (KnowBert).* EMNLP 2019. ACL Anthology: D19-1005. arXiv: 1909.04164.
  - Introduces a general method for embedding multiple knowledge bases into large-scale models via entity linking and word-to-entity attention, demonstrating that ontology-grounded supervision can be injected at any transformer layer — directly relevant to Paper A's ontology-constrained decoding design.
  - "After integrating WordNet and a subset of Wikipedia into BERT, KnowBert demonstrates improved perplexity, ability to recall facts, and downstream performance on relationship extraction, entity typing, and word sense disambiguation." This shows that structured ontology constraints improve performance on precisely the tasks Paper A targets.

- **Scholak, T., Schucher, N., and Bahdanau, D. (2021).** *PICARD: Parsing Incrementally for Constrained Auto-Regressive Decoding from Language Models.* EMNLP 2021. ACL Anthology: 2021.emnlp-main.779. arXiv: 2109.05093.
  - Shows that incremental schema-validity checking at every decoding step eliminates invalid structured outputs without requiring additional labelled training data, establishing the principle of hard ontology enforcement at generation time that Paper A's output gate implements.
  - "PICARD transforms fine-tuned T5 models with passable performance into state-of-the-art solutions" on Spider and CoSQL by rejecting inadmissible tokens at each decoding step. Paper A's admissibility-guarded output gate follows the same architectural commitment.

- **Izacard, G., Lewis, P., Lomeli, M., Hosseini, L., Petroni, F., Schick, T., … Grave, E. (2022).** *Atlas: Few-Shot Learning with Retrieval Augmented Language Models.* Journal of Machine Learning Research (JMLR) 24, 2023. arXiv: 2208.03299.
  - Demonstrates that a small retrieval-augmented model can match or exceed a model 50× larger on knowledge-intensive tasks by grounding generation in a structured document index, showing that ontological structure in the retrieval corpus acts as an implicit schema constraint.
  - "Atlas reached over 42% accuracy on Natural Questions using only 64 examples, outperforming a 540B parameter model by 3%." Structured knowledge as a retrieval index provides the same schema grounding that explicit ontology constraints provide in Paper A's setting.

---

## Gaps in the Literature

Existing work does not address the following, which Paper A fills:

1. **Joint-key tuple overlap filtering across synthetic splits.** Contamination literature (Section 5) identifies the problem; benchmark construction literature (Section 1–2) avoids it ad hoc. No existing work formalises filtering on joint (surface-form, structural-class) tuples as a construction-time invariant for synthetic datasets.

2. **Generation bucketed explicitly by structural failure mode.** Lake & Baroni (2018) and SCAN-family work create *evaluation* splits by failure mode; Paper A applies bucket stratification to *generation*, not just evaluation, so training data coverage is calibrated against a failure-mode taxonomy.

3. **Held-out invariance as a formal contractual guarantee, not a post-hoc audit.** Existing contamination auditing (Brown et al. 2020, Sainz et al. 2023) detects leakage after the fact. Paper A requires disjointness by construction, making contamination structurally impossible for the classes of leakage it targets.

4. **Combining all three (bucketed generation + held-out surface forms + joint-key filtering) in an ontology-constrained output space.** Section 1–6 papers each address one or two of these properties in isolation. No prior work integrates all three within a single synthetic data pipeline constrained by a formal output ontology.
