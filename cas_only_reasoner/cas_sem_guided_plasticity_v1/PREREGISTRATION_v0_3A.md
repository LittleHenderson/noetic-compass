# CAS-SEM-GUIDED-PLASTICITY v1 — PREREGISTRATION v0.3A (CANDIDATE)

Status: **PREREGISTRATION CANDIDATE — AWAITING OWNER APPROVAL.** No model
loaded, no GPU used, no exploratory run, no claim ledger touched. This
document is written under the standing rules that (a) Claude is NOT the
research governor and may not self-authorize past a gate, and (b) no
neural workload runs on local CPU. Branch: `research/cas-sem-guided-
plasticity-v1`, forked from the clean pre-pivot commit `44128fb2`. The
contaminated `eta_epsilon_weight_learning_v0.1` chain is NOT continued.

## 0. Scope of THIS preregistration

v0.3A registers **Claim A only** (CAS-aligned label decodability) with a
fair control battery. Claims B/C/D (incremental value, causal utility,
learning benefit) are pre-registered in outline (§9) but NOT run. The
central scientific correction stands: **semantic roles (agent/patient/
verb) belong to CAS-Sem, not the 40-simplex**; the 40-simplex returns
later only as a process-state controller (a separate, later phase).

## 1. Data (new inventory; the v0.3 preview's 24 verbs are DEVELOPMENT-ONLY, excluded)

Build a new **verb-SENSE** inventory. Unit of analysis = verb sense, not
sentence.
- >= 40 fit verb senses per CAS class, >= 20 protected verb senses per
  class, 4 CAS classes -> **>= 240 distinct verb senses total.**
- Each item carries: `lemma`, fixed `sense_id`, `sense_gloss`,
  `context_sentence`, `cas_label`, `source_grounded_rationale` (tied to
  the frozen `cas_reasoner.txt` / CLAUDE.md Noetic definitions).
- **No LLM assigns claim-bearing labels.** Sense labels are assigned by a
  human against a frozen sense resource; the rationale cites the source
  definition. Sense-ambiguous verbs (e.g. "questions", "warns") are
  labeled by SENSE-IN-CONTEXT, not spelling.
- Each sense appears in several sentence frames, but inference groups by
  verb sense.

## 2. Splits (group every occurrence of a verb sense into ONE split)

`development`, `readout_fit`, `readout_select`, `validation`,
`protected_lexical` (unseen senses), `protected_contextual` (unseen
frames), `protected_joint` (unseen senses + frames). Protected sets: new
senses, new frames, new noun combos; NO protected item appears in any
development or preview data. Protected read ONCE, in the frozen AWS env,
after all freezes + owner approval.

## 3. Baselines (the fair-comparison fix)

The v0.3 surface baseline was blinded by construction (train-only
bag-of-words vs pretrained hidden states). Corrected registered lexical
family, all with the same probe budget and layer-selection policy:
- character n-gram classifier;
- tokenizer-subword classifier;
- **Qwen input-embedding classifier at the verb token** (the key control:
  does a later hidden layer add abstraction beyond lexical knowledge
  already present pre-Transformer?);
- Qwen layer-0 sentence representation.
A later hidden layer may be called "beyond surface" ONLY if it beats the
FULL registered lexical family.

## 4. Random control (fixed balanced verb-sense partitions, not label shuffle)

The v0.3 "random control" was a per-example label shuffle (broken; 0.05
!= chance 0.25). Corrected: for each seed, assign each verb sense to one
of 4 classes ONCE, equal class sizes, the SAME mapping across all
occurrences and all splits. Run **>= 1000** such partitions; report the
full distribution.

## 5. Matched semantic control — SCMPE-v1

**Semantic-Cohesion-Matched Partition Ensemble v1.** Four families:
- **A. Pretrained lexical baseline** — Qwen input-embedding at the verb
  token + same-budget linear classifier (controls "already in lexical
  embeddings").
- **B. Established non-CAS verb taxonomy** — one frozen external system
  (balanced VerbNet- or FrameNet-derived 4-class taxonomy): 4 classes,
  same senses-per-class, same examples, same grouping, same probe, same
  layer policy, same stats. Classes/mappings frozen before any model
  result is seen.
- **C. Semantic-cohesion-matched partitions** — >= 1000 balanced 4-way
  partitions of the same senses, retained only if within-class
  similarity, between-class separation, word-frequency, token length, and
  morphological complexity match the CAS partition within pre-registered
  tolerances. Matching representation comes from an INDEPENDENT frozen
  lexical resource, NOT the Qwen layer under evaluation. Report the CAS
  partition's percentile in the matched distribution.
- **D. Balanced random partitions** — >= 1000 fixed verb-sense->class
  mappings (as §4), full distribution reported.
Owner picks the control battery, not one convenient taxonomy. Animacy /
concreteness are rejected as sole controls (they ride on the nouns, not
the verb-carried CAS label).

## 6. Layer selection (independent, not inherited)

Capture layer 0 and ALL transformer layers. Fit on `readout_fit`, select
the layer on `readout_select` by macro-F1, freeze it, evaluate on
`validation`, read protected ONCE. Ties within one standard error ->
earliest layer. Layer 12 is NOT assumed.

## 7. Statistics

>= 10 claim-bearing seeds. Report accuracy AND macro-F1. **Group bootstrap
by verb sense** (never treat repeated sentences of one sense as
independent). Report effect sizes + confidence intervals.

## 8. Claim boundaries (separated; deterministic promotion)

- **Claim A — CAS-aligned decodability:** a linear readout predicts the
  frozen 4-way CAS labels on held-out verb senses. Establishes A ONLY.
- **Claim B — incremental CAS value:** CAS adds held-out predictive value
  BEYOND the pretrained-lexical and matched-semantic controls (nested:
  generic-semantic features vs generic + CAS). Only B licenses the word
  "CAS-specific".
- **Claim C — causal utility:** a CAS-derived intervention changes a
  SEPARATE held-out behavior more than matched-control-derived
  interventions. (eta-hat becomes relevant here.)
- **Claim D — learning benefit:** CAS-guided training reduces
  examples-to-threshold / optimizer steps / forgetting vs generic-semantic
  guidance under matched data/params/compute/seeds.
Status is emitted by a DETERMINISTIC program from (raw result, frozen
threshold, controls, hard gates) -> {EMPIRICALLY_SUPPORTED, REFUTED,
INCONCLUSIVE}. Claude may NOT hand-write status or "PASS with caveats". A
failed hard gate is REFUTED. No metric may be swapped via "or".

## 9. Second-stage utility test (pre-registered, NOT executed here)

Conditions: no-aux-structure; generic semantic taxonomy; CAS Noetic
taxonomy; generic+CAS; shuffled-CAS; random matched-dimensional. Primary
outcome = a separate held-out BEHAVIORAL task. CAS-specific value requires
CAS or generic+CAS to beat generic-alone AND shuffled-CAS under matched
data/params/compute/seeds. This is where CAS-Sem-guided plasticity + the
40-simplex-as-process-controller test live; each is its own future phase.

## 10. COMPUTE section (GPU-first / cloud-first — conforms to the owner compute law)

- Every neural script fails closed: `if not torch.cuda.is_available():
  raise RuntimeError("GPU_REQUIRED")`. Never silent CPU fallback.
- Local CPU: only hashing, JSON/YAML, deterministic dataset generation,
  tiny synthetic tests, manifests, git.
- Local RTX 4070: smoke / one-seed dev / shape-debug only; NEVER the
  claim-bearing sweep.
- **AWS GPU (SageMaker Training PyTorch, or EC2 GPU frozen DLAMI/container)
  for ALL claim-bearing runs**, all >=10 seeds, all-layer extraction,
  intervention, LoRA/weight work, protected eval, replication.
- **Bedrock is teacher-language only**; never hidden-state / gradient /
  Jacobian / LoRA / weight work.
- **Cached activations:** load frozen model once on AWS GPU, extract all
  registered layers once per frozen dataset, save split-separated tensors,
  hash each, upload to S3; fit CAS + all controls against the SAME cached
  tensors. Do not rerun the model per control.
- Every job records a full receipt (service/region/instance, GPU, CUDA/
  torch/transformers, dtype, container digest, code+model+tokenizer+data
  digests, seed, timestamps, wall-clock, peak mem, exit status, artifacts,
  est+actual cost). Cost ceiling + auto-terminate on success/failure/
  timeout/cancel/upload; no idle resource.

## Governance (to be BUILT before any claim-bearing run — spec, not built here)

- **Owner-signed phase gate:** a signed record {study_id, phase,
  preregistration_sha256, previous_receipt_sha256, approved_by, decision,
  signature}. The phase runner refuses unless the signature is valid, the
  prereg hash matches, the previous phase permits continuation, no hard
  gate failed, and the requested phase is exactly the next one -> else
  exit `OWNER_APPROVAL_REQUIRED` / `PREVIOUS_GATE_FAILED`. Signing key
  stays outside the agent env. No `/goal` hook overrides it.
- **Deterministic claim promotion:** a program reads raw+threshold+
  controls+gates and emits only {EMPIRICALLY_SUPPORTED, REFUTED,
  INCONCLUSIVE}. Claude does not edit the ledger by hand.

## Seed list (proposed)

data_generation, data_split, intervention_basis, bootstrap, and 10
claim-bearing training seeds [0..9]. Exact values frozen at owner sign-off.

## Unresolved owner decisions (must close before v0.3A runs)

1. Approve the CAS class set + the frozen sense resource for labels.
2. Approve SCMPE-v1 (the matching lexical resource + tolerances) and the
   external VerbNet/FrameNet taxonomy for control B.
3. Approve thresholds (decodability margin, CI rule) and the claim-A gate.
4. Confirm the human labeler / label-provenance process (no LLM labels).
5. Sign the phase-approval record and provide the signing-key location.
6. Confirm AWS execution env (SageMaker vs EC2) + cost ceiling.

## STOP

Committed once as a candidate. No execution. No ledger change. Awaiting
explicit owner approval and an owner-signed phase-0 record before any run.
