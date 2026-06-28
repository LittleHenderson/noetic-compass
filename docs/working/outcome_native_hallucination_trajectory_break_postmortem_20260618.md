# Qwen-0.5B Trajectory-Break Hallucination Detection — Post-Mortem

**Date:** 2026-06-18
**Experiment:** `outcome_native_hallucination_trajectory_break_qwen05_hard_v2`
**Commit:** `e3dba042`
**Verdict:** Useful signal, NOT LICENSED
**Claims:** `claims_licensed=0`, `claims_not_licensed=6`

---

## THE NUMBERS

| Readout | Balanced Accuracy | Margin vs Trajectory |
|---|---|---|
| **trajectory hidden (layer 14)** | **0.819487** | — |
| generated-prefix char BA | 0.734484 | +0.085 |
| W0-static BA | 0.714641 | +0.105 |
| prompt char BA | 0.707217 | +0.112 |
| layer-0 trajectory BA | 0.706876 | +0.113 |

**Pass gate:** trajectory hidden must beat ALL controls by ≥ 0.15.

**Result:** Best margin = 0.112 (vs prompt char BA). Every margin fails the 0.15 gate.

---

## WHY IT FAILED: ROOT CAUSE ANALYSIS

### Cause 1: The generated-prefix baseline is too strong (0.734)

The char-ngram baseline on generated text alone achieves 0.734 — only 0.085 below the hidden trajectory. This means:

- The model's **output tokens themselves** carry most of the hallucination signal. The vocabulary and phrasing patterns of hallucinated vs grounded completions are systematically different enough that a simple char-ngram classifier already captures much of the distinction.
- The hidden state is adding only ~8.5 percentage points beyond what surface text reveals.
- This is the **text-is-winning** pattern from previous harness experiments. The hidden-state readout is, at best, a mirror of visible text patterns, not a pre-existing internal state.

**What this looks like structurally:** A hallucinated completion that says *"The treatment protocol for this condition typically involves..."* uses different character distributions than a grounded completion that says *"There is limited evidence on this, but one small study..."* The char-ngram baseline catches this. The hidden state may simply be encoding the token distribution the model is about to generate.

### Cause 2: The model is too small

Qwen-0.5B has ~500M parameters. At this scale:

- Hidden states are low-dimensional relative to the complexity of the hallucination distinction. The model has limited capacity to encode *why* a token is being generated (grounded recall vs confabulation) separately from *what* token is being generated.
- The internal representation of "I am retrieving a fact" vs "I am producing plausible-sounding text" may simply not be well-separated in a 0.5B model's hidden space.
- The layer-0 trajectory BA (0.707) being essentially at the prompt-char baseline level confirms that early layers carry no hallucination-specific signal — the distinction emerges later (layer 14), but even there it's weak.

**Precedent:** The earlier Qwen-2.5-1.5B injection experiments in the two-bridge spike log showed the same pattern at Pythia-160M (GREY — no separation) but found separation at Qwen-1.5B (p=9e-5). The variable that matters for internal-state readout is model capacity, not prompt design.

### Cause 3: The trajectory definition may not capture the right moment

The "trajectory break" captures hidden state at a specific token position — presumably where the model transitions from grounded generation to hallucination (or vice versa). But:

- The break may not be a clean single-token event. Hallucination onset might be gradual — a slow drift from grounded vocabulary to confabulation over several tokens.
- The break point might be misaligned. If the labeling identifies "this completion is hallucinated" but the break point is placed at the wrong token, the hidden state at that position might be mid-transition and not maximally discriminative.
- A single position might have high variance. Different hallucinated completions might "break" at different points, and averaging over mismatched break positions dilutes the signal.

### Cause 4: Prompt-char baseline rules out clean prompt-level confounds but leaves text-level ones

The prompt char BA (0.707) being the lowest control is good — it means the prompts themselves aren't trivially leaking the label. But the generated-prefix char BA (0.734) suggests that once the model starts generating, the surface text rapidly diverges between conditions. The hidden state is measured at a moment when the text divergence is already partially encoded.

---

## IMPROVEMENT PLAN: RANKED BY EXPECTED IMPACT

### Improvement 1 (HIGHEST LEVERAGE): Scale up the model

**What:** Run the identical experiment on Qwen-2.5-1.5B-Instruct or Qwen-2.5-7B-Instruct.

**Why:** The two-bridge spike log established that Pythia-160M (0% injection compliance, GREY on all metrics) flipped to separation on Qwen-1.5B (p=9e-5, rank-biserial 0.695). Model capacity — specifically instruction-following capacity — was the variable that determined whether hidden states carried detectable signal. The same pattern likely applies to hallucination: a 0.5B model's hidden states may simply not encode the grounded-vs-confabulated distinction strongly enough.

**Expected outcome:** If Qwen-1.5B produces hidden trajectory BA ≥ 0.85 with similar controls (generated-prefix ~0.72-0.74), the margin would be ≥ 0.11-0.13 — still possibly below 0.15, but substantially closer. If Qwen-7B pushes hidden trajectory BA ≥ 0.88, the gate passes.

**Cost:** Low — same experiment design, larger model. The trajectory-break pipeline is already built and tested. Just swap the model name.

### Improvement 2: Multi-token trajectory windows instead of single break point

**What:** Instead of capturing hidden state at one token position (the "break"), capture a window of 3-5 tokens around the transition and use:

- **Mean pooling** over the window (average hidden state over the transition zone)
- **Gradient** over the window (first difference between consecutive hidden states — captures the *rate* of change)
- **Curvature** (second difference — where the trajectory bends most sharply)

**Why:** Hallucination onset may not be a clean single-token event. If the "break point" label is off by even one token, the hidden state at that position is mid-transition and its signal is diluted. A window captures the full transition zone. The gradient specifically captures *trajectory change* — the dynamic of "the model is entering a different generative mode" — which may be more discriminative than a static hidden state at any single point.

**Expected outcome:** A well-chosen window and gradient features could add 2-5 percentage points to the hidden trajectory BA by reducing single-position variance and capturing the dynamic of the transition.

**Implementation:** Modify the trajectory-break capture to record `[position-2, position-1, position, position+1, position+2]` hidden states. Train on concatenated or pooled features.

### Improvement 3: CAS-probe features instead of raw hidden states

**What:** Instead of training a linear probe on raw hidden states, train on CAS-relevant features extracted from those hidden states:

- **^6 activation** — is the model internally fact-checking? (Critical Evaluation)
- **^8 activation** — is the model expanding/confabulating? (Expansion without grounding)
- **^3 activation** — is the model grounding in specifics? (Concretization from real knowledge)
- **^2 vs ^3 polarity margin** — is the model abstracting (risk of hallucination) or concretizing (grounded)?
- **^1 activation** — is the model differentiating known from unknown?

**Why:** Raw hidden-state readout gives the model's full internal state, including dimensions irrelevant to hallucination. CAS-probe features focus on the dimensions that structurally distinguish grounded cognition (^3, ^6, ^1) from confabulation (^8 without ^3 grounding, ^2 without ^6 verification). This is the "typed semantic classes" approach the two-bridge spike log flagged as the missing piece.

**Expected outcome:** CAS-probe features could outperform raw hidden states by focusing the classifier on structurally relevant dimensions. If the hallucination signal is present but weak in the raw 896-dim hidden state, a 4-6 dimension CAS-probe subspace might extract it with less noise.

**Implementation:** Train linear probes for each CAS dimension (^2, ^3, ^6, ^8, ^1) on existing harness data (40E, Foundation-28). Use the probed CAS activations as features for the hallucination classifier.

### Improvement 4: Generated-prefix baseline hardening

**What:** The char-ngram baseline (0.734) is the strongest control. Before claiming hidden-state detection, verify that:

- The char-ngram baseline isn't picking up trivial vocabulary confounds (e.g., hallucinated completions use more hedging words, grounded completions use more specific terminology)
- A **token-identity baseline** (first N tokens of the completion as categorical features) doesn't match or exceed the hidden-state readout
- A **semantic baseline** (sentence embeddings of the first 8 tokens) doesn't match the hidden state

**Why:** If any of these baselines approaches or exceeds the hidden trajectory BA, the hidden state is a mirror of generated text, not a pre-existing internal state. This is the Codex audit's W0/W1/W8 window requirement applied to the trajectory-break lane.

**Expected outcome:** If the token-identity baseline reaches 0.78+, the experiment is fundamentally a text-classification result dressed as hidden-state detection. If the baselines stay below 0.70 and the hidden trajectory reaches 0.85+, the hidden state is carrying signal beyond visible text.

### Improvement 5: Layer-spanning trajectory features

**What:** Instead of using one best layer (layer 14), concatenate hidden states from multiple layers or compute layer-difference features.

**Why:** The "trajectory break" may manifest as a change in *which layer* carries information, not just the hidden state at one layer. For example:
- Pre-break: layers 8-12 carry most information (semantic processing)
- Post-break: layers 14-18 carry most information (hallucinatory generation)
- The break is detectable as a shift in the layer-wise information profile

**Expected outcome:** Layer-difference features (hidden_state[layer_N] - hidden_state[layer_N-4]) capture the rate of representational change across layers at the break point, which may be more discriminative than any single layer's state.

### Improvement 6: Prompt bank refinement — induce cleaner internal divergence

**What:** The "hard v2" prompt bank may be *too* hard — producing completions where the model is uncertain and the grounded-vs-hallucinated distinction is muddy. Refine to:

- **Clean grounded prompts:** Questions where the model clearly knows the answer from training data and answers directly
- **Clean hallucination prompts:** Questions where the model clearly lacks knowledge AND is pushed to answer anyway (not "I don't know" — the model must produce confident-sounding confabulation)
- **Exclude ambiguous cases:** If the model's behavior is genuinely ambiguous (partial knowledge, mixed signal), those cases dilute the hidden-state separation

**Why:** The stronger the behavioral divergence between conditions, the stronger the internal-state divergence should be. If the prompts produce weak behavioral divergence, the hidden-state signal will be correspondingly weak.

---

## PRIORITIZED NEXT MOVES

| Priority | Action | Expected BA Gain | Blockers |
|---|---|---|---|
| P0 | Scale to Qwen-2.5-1.5B-Instruct | +3-8 pp | None — same pipeline, larger model |
| P1 | Multi-token trajectory windows + gradient features | +2-5 pp | Minor capture code change |
| P2 | CAS-probe features (^2, ^3, ^6, ^8, ^1) | +3-6 pp | Needs CAS-probe training on existing harness data |
| P3 | Generated-prefix + token-identity baselines | Diagnostic (not gain) | Baseline implementation |
| P4 | Layer-spanning features | +1-3 pp | Multi-layer capture |
| P5 | Prompt bank refinement | Variable | Prompt engineering effort |

---

## WHEN TO DECLARE THE CLAIM LICENSED

The claim graduates from OPEN → LICENSED only when:

1. Hidden trajectory BA ≥ 0.75 AND
2. Hidden trajectory beats ALL controls (generated-prefix char, token-identity, W0-static, prompt char, layer-0) by ≥ 0.15 AND
3. The result holds on a held-out prompt set (not used for training or layer selection) AND
4. The result replicates on at least one model from a different family (e.g., Phi, OLMo)

Until then, the "hidden-state hallucination detection" claim stays NOT LICENSED. The honest finding remains: *"trajectory hidden states carry a weak hallucination-correlated signal in Qwen-0.5B, but the signal does not beat text baselines by the required margin and may primarily reflect surface text patterns."*

---

## CJT / PCBA DIAGNOSTIC LENS

Through the CJT framework, what we're measuring is:

- **The trajectory break = a CJT entering a different operating region.** A grounded model operates in the active region (cause→effect proportional, β stable). A hallucinating model may be entering saturation (confidently generating from insufficient cause) or cutoff on the verification CJT (^6 evaluation suppressed, allowing ^8 expansion to run ungrounded).

- **The weak signal = the CJT region transition is subtle in a 0.5B model.** The "break" from active to saturation isn't sharp — the model drifts rather than switches. In a larger model, the CJT might have a sharper characteristic curve (more abrupt saturation knee), producing a clearer internal signal at the break point.

- **The next diagnostic target:** Instead of asking "did the model hallucinate?", ask "did the ^6 verification CJT enter cutoff at the break point?" This is Improvement 3 (CAS-probe features) expressed in CJT terms: measure the CJT's operating region from hidden states, not just the raw state vector.
