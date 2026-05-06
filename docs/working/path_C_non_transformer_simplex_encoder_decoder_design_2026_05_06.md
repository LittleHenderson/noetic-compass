# Path C Draft: Non-Transformer Simplex Encoder/Decoder

Date: 2026-05-06
Status: Future build draft. Do not implement before Path B conversational v0 ships.
Search tags: CAS-Native, Path C, non-transformer decoder, non-transformer encoder, Delta^o_39, Fisher-Rao, RPM, meta-logic, native NL generation, simplex language model.

## 1. Purpose

This note preserves a future research/build direction:

> Can CAS-Native eventually replace a transformer reasoning backbone with a Simplex Delta^o_39 + Fisher-Rao state engine, while still generating fluent conversational English?

Short answer:

Yes for the CAS reasoning core. Not yet for the entire language generator. The likely winning design is a hybrid-but-non-transformer sequence model:

```text
NL prompt
  -> Simplex CAS encoder
  -> RPM/meta-logic constrained CAS state
  -> non-transformer autoregressive NL decoder
  -> fluent reply + trace
```

The Simplex Delta^o_39 system should become the model's structured mind-state space. The decoder still needs a sequence mechanism to emit English tokens in order. That mechanism does not have to be a transformer, but it must handle recurrence, memory, style, and turn context.

## 2. Non-Goals

This is not the v0 path. Path B remains:

```text
K=9 classifier + CASNativeModel + NLGenerationHead + Tier 3 dialogue corpus
```

This draft should not block:

- the 50K Claude Tier 3 corpus
- B-3 native generation smoke
- B-4 two-stage inference wiring
- any current K=9 production classifier usage

This draft also does not claim that a 39-dimensional simplex alone can speak English. It cannot. The simplex is the state geometry. The decoder is the speech mechanism.

## 3. Core Idea

Replace the opaque hidden-state reasoning middle with a structured CAS state:

```text
p_t in Delta^o_39
```

where `p_t` is an open-simplex distribution over the 40 Cognitive States. Every component is positive and the total sums to 1.

The Fisher-Rao metric supplies the natural distance/learning geometry for this space. RPM supplies prerequisite gating over the state trajectory. Meta-logic supplies inspectable proof/explanation objects above the gate.

The model should maintain:

- `p_state`: 40-state simplex distribution
- `domain`: P/C/E/O distribution or constrained projection
- `drive`: F1-F7 distribution
- `register`: T/A/f/E distribution or register-set distribution
- `rpm_status`: prerequisite pass/fail and broken-node evidence
- `meta_proof`: optional relation/proof object for set/relation expressions
- `dialogue_state`: compact turn memory

## 4. Proposed Architecture

### 4.1 Simplex Encoder

Goal:

Turn English prompt tokens into a CAS state trajectory without transformer self-attention.

Proposed module:

```text
SimplexStateEncoder
```

Input:

- token ids from the existing native tokenizer
- optional CAS prefix tokens
- speaker/turn metadata
- prior dialogue state

Output:

- `p_state_final`: final 40-state open-simplex distribution
- `p_state_trace`: compressed per-step simplex trajectory
- `axis_logits`: noetic/domain/drive/register/register_set projections
- `rpm_trace`: prerequisite gate trace
- `meta_logic_trace`: optional set/relation proof trace

Candidate update rule:

```text
p_{t+1} = normalize_eps(p_t * exp(eta * g(x_t, p_t, m_t)))
```

Plain meaning:

Each token applies a small multiplicative update to the current CAS distribution. Normalization keeps the result inside the open simplex. This is closer to mirror descent/natural-gradient behavior than a free Euclidean hidden-state update.

Where:

- `x_t` = token embedding
- `p_t` = current CAS simplex state
- `m_t` = compact dialogue memory
- `g(...)` = learned update network
- `eta` = learned or scheduled update size
- `normalize_eps` = floor every coordinate at `simplex_floor`, then renormalize

Implementation candidates:

1. Gated recurrent cell over simplex coordinates.
2. State-space model cell conditioned on CAS axes.
3. Small causal convolution feeding a simplex update.
4. Mixture of learned CAS operators: plus, pair, production, omega, meta-relation.

No transformer attention is used in this encoder.

### 4.2 Dialogue Memory Without Attention

A non-transformer conversational model still needs memory. Proposed memory:

```text
DialogueStateMemory
```

Fields:

- last `k` CAS simplex states
- current topic embedding
- speaker profile / demographic / tone metadata
- unresolved question flag
- prior assistant stance
- RPM broken-node history

Memory update can be recurrent:

```text
m_{t+1} = GRU_or_SSM(m_t, [p_state_t, token_summary_t, turn_features])
```

This memory is not the CAS state itself. It is the short-term conversational workspace used to keep replies coherent across turns.

### 4.3 RPM Gate

Current scalar RPM behavior should become a structured gate:

```text
RPMGate(p_state, drive, dialogue_memory) -> rpm_status
```

The gate checks whether prerequisite mass exists in the right order:

```text
A0 -> Dn -> Wn -> Pn
```

For Path C, RPM should operate continuously:

- thresholded mass on prerequisite nodes
- Fisher-Rao distance to the nearest valid prerequisite chain
- broken-node explanation when a chain fails
- repair proposal when a reply would speak from an invalid chain

Training signal:

- penalize replies whose generated CAS state violates RPM
- reward correct refusal/qualification when RPM is incomplete
- log all pass/fail decisions in the generation trace

### 4.4 Meta-Logic Proof Layer

Meta-logic should sit above RPM, not replace it.

Role:

- RPM decides whether a prerequisite chain is structurally valid.
- Meta-logic explains or proves why the chain passed/failed using explicit relations.

Examples:

- `state in NoeticCluster{...}`
- `CoverOf(...)`
- `PartitionOf(...)`
- `Pullback(...)`
- `Product(...)`
- evidence relation between Wn and Pn

Future behavior:

```text
RPMGate says: fail at Wn -> Pn
MetaLogicProof says: no evidence relation covers the required Wn node
Trace says: reply softened/refused because execution authority was unsupported
```

This is a v1.5+ feature, not a v0 blocker.

### 4.5 Non-Transformer NL Decoder

Goal:

Generate fluent English from the CAS state without transformer self-attention.

Proposed module:

```text
SimplexConditionedNLDecoder
```

Inputs:

- `p_state_final`
- `domain`, `drive`, `register`
- `rpm_status`
- `meta_proof_summary`
- `dialogue_memory`
- previous output token

Output:

- next-token distribution over native English/CAS vocabulary
- optional per-token CAS grounding trace

Candidate decoder cell:

```text
h_{t+1} = SSM_or_GRU(h_t, token_embed(y_t), cas_condition, dialogue_memory)
logits_t = vocab_projection(h_{t+1}, cas_condition)
```

Conditioning path:

```text
cas_condition = Project([
  p_state_final,
  domain_dist,
  drive_dist,
  register_dist,
  rpm_status,
  dialogue_memory
])
```

Possible sequence mechanisms:

1. GRU/LSTM baseline: easiest to build and falsify.
2. RWKV-style recurrent mixing: stronger long-context candidate.
3. Mamba/SSM-style selective state-space decoder: best long-context non-transformer candidate, but more engineering.
4. Causal convolution + recurrent state: simple, inspectable, maybe enough for short replies.

The first prototype should use the simplest cell that can pass the fluency gate. Do not jump straight to a complex SSM unless the GRU baseline fails for reasons clearly tied to memory length.

## 5. Training Objective

Minimum loss:

```text
L = L_lm
  + alpha * L_cas_grounding
  + beta  * L_fisher_rao
  + gamma * L_rpm
  + delta * L_trace
```

Where:

- `L_lm`: next-token cross entropy over assistant reply only
- `L_cas_grounding`: generated reply must reclassify to the target CAS state
- `L_fisher_rao`: keep predicted simplex near target simplex under Fisher-Rao distance
- `L_rpm`: penalize invalid prerequisite-chain activation
- `L_trace`: require trace fields to match record provenance and CAS fields

Curriculum:

1. Train encoder only on CAS prediction.
2. Freeze or softly anchor encoder; train decoder on fluent replies.
3. Joint fine-tune with low `alpha/beta/gamma`.
4. Increase structural losses only after replies are fluent enough.

Reason:

If structural losses dominate too early, the model may become CAS-correct but conversationally stiff.

## 6. Data Requirements

Minimum data:

- 50K Tier 3 dialogue records for first serious smoke
- 100K+ for useful comparison against transformer decoder
- explicit meta-logic slice later, not in v0

Record fields needed:

- prompt/reply
- CAS expression
- noetic/domain/drive/register/register_set
- demographic/tone
- conversation_id and turn_index
- trace_id/source/generator_model
- optional RPM/meta-logic annotations when available

The existing 50K Claude Tier 3 run is useful for this future model, but it is not enough to prove the non-transformer path alone. It is enough for first falsification.

## 7. Evaluation Gates

Do not compare this model only by training loss. It must pass practical gates.

### 7.1 Fluency

- blind review: cannot be reliably distinguished from the transformer decoder baseline
- no repetitive loops
- no clipped/telegraphic style
- reply length within 20% of the Tier 3 reference distribution

### 7.2 CAS Grounding

- generated reply reclassifies to intended CAS state at high rate
- no CAS notation leakage unless explicitly requested
- register behavior matches target register

### 7.3 Traceability

Every generated reply must emit:

- final simplex distribution or top-k compressed state
- CAS expression
- RPM pass/fail
- any broken prerequisite node
- generation trace id
- tokenizer/model/checkpoint provenance

### 7.4 RPM

- invalid RPM chains are blocked, softened, or repaired
- RPM failure explanation is stable across paraphrases
- no "Power without Wisdom" pattern in controlled tests

### 7.5 Meta-Logic

For the future meta-logic slice:

- relation operators correctly identified
- proof/explanation is faithful to the relation
- no false proof when relation is absent

## 8. Prototype Phases

### Phase 0: Paper Design Only

This document. No implementation.

Exit:

- Path B v0 conversational model exists
- 50K+ Tier 3 corpus validated
- transformer baseline metrics available

### Phase A: Encoder-Only Simplex Smoke

Build:

- `SimplexStateEncoder`
- Fisher-Rao distance/loss
- RPM trace stub

Train:

- prompt -> CAS labels

Compare against:

- K=9 classifier
- structured-token classifier

Pass:

- within 5-10 pp of K=9 on canonical eval after matched data
- better trace quality than K=9
- no Drive collapse worse than known K=9 baseline

Fail:

- cannot learn CAS state prediction
- Drive/domain/register collapse
- unstable simplex boundary behavior

### Phase B: Decoder-Only Conditioning Smoke

Build:

- `SimplexConditionedNLDecoder`
- teacher-forced reply generation

Use:

- gold CAS state from dataset, not predicted encoder state

Pass:

- fluent short replies
- no CAS notation leakage
- reply-only loss decreases cleanly

Fail:

- repetitive loops
- flat/telegraphic replies
- cannot maintain sentence-level grammar

### Phase C: End-to-End Non-Transformer v0.1

Connect:

```text
SimplexStateEncoder -> RPMGate -> SimplexConditionedNLDecoder
```

Pass:

- generated replies remain fluent
- CAS grounding remains above baseline threshold
- trace is complete

Fail:

- encoder noise destabilizes decoder
- RPM gating causes evasive or stiff language

### Phase D: Head-to-Head Against Transformer Baseline

Compare:

- current transformer decoder baseline from Path B
- non-transformer simplex decoder
- hybrid transformer decoder conditioned on simplex state

Metrics:

- fluency blind review
- CAS grounding
- trace completeness
- inference cost
- train stability
- parameter count

Only promote if it wins on traceability and does not materially lose fluency.

## 9. Likely File Targets When Implemented

Potential new files:

```text
noetic-compass-scaffold/noetic-compass/cas-native/model/simplex_state_encoder.py
noetic-compass-scaffold/noetic-compass/cas-native/model/simplex_nl_decoder.py
noetic-compass-scaffold/noetic-compass/cas-native/model/simplex_rpm_gate.py
noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_native_nl.py
noetic-compass-scaffold/noetic-compass/cas-native/training/simplex_losses.py
noetic-compass-scaffold/noetic-compass/cas-native/tests/model/test_simplex_state_encoder.py
noetic-compass-scaffold/noetic-compass/cas-native/tests/model/test_simplex_nl_decoder.py
```

Potential reused files:

```text
noetic-compass-scaffold/noetic-compass/cas-native/training/datasets/native_nl_collator.py
noetic-compass-scaffold/noetic-compass/cas-native/training/masked_ce_loss.py
noetic-compass-scaffold/noetic-compass/cas-native/trace/generation_trace.py
docs/working/path_B2_native_nl_collator_design_2026_05_06.md
docs/working/native_nl_sdg_strategy_2026_05_04.md
```

## 10. Hard Rules

- No foreign pretrained weights in production.
- Do not use the 48-dimensional photonics/TKS coincidence as model dimension.
- Keep 40-state simplex / 39-dimensional open-simplex geometry as the structural base unless the formal framework changes.
- Do not replace the Path B transformer/generation work until a working v0 exists.
- Do not promote any non-transformer result without blind fluency review.
- Every generated reply must remain traceable.

## 11. Open Questions

1. Should the first decoder be GRU-based for simplicity or SSM-based for longer context?
2. Should `p_state` be token-updated at every input token or only at phrase/span boundaries?
3. Should RPM gating be hard during generation or soft during early training?
4. How much dialogue memory can remain non-transformer before fluency suffers?
5. Should meta-logic proof objects be generated by rules first, then learned later?
6. What is the minimum corpus size where a from-scratch non-transformer decoder stops sounding flat?

## 12. Recommended Future Execution Order

After Path B v0:

1. Freeze current transformer-based conversational baseline metrics.
2. Implement encoder-only `SimplexStateEncoder`.
3. Train/evaluate it on CAS prediction before touching generation.
4. Implement decoder-only `SimplexConditionedNLDecoder` using gold CAS state.
5. Run short-response generation smoke on 50K Tier 3.
6. Connect encoder + RPM + decoder end to end.
7. Add meta-logic proof layer only after RPM behavior is stable.
8. Compare against transformer baseline and decide whether this becomes Path C mainline.

