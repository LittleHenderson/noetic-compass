# CAS-Native Redesign — Unified Synthesis (5 Specialist Notes)

**Date:** 2026-05-05
**Author:** Synthesizer (slice 6 of 5 — consolidator)
**Status:** SIDE PROJECT. **No production code touched. No commits. Live v1 retrain on the pod (PID 14170) untouched.** Read + write a unified synthesis note only.
**Inputs:** Specialists #107 (embedding), #108 (attention/layer), #109 (heads/loss), #110 (optimizer), #111 (state-space).
**Hard rules respected:** No foreign pretrained weights anywhere; every component surfaces inspectable internal state; every claim cross-cited; plain language; conflicts surfaced honestly.

---

## §1 Executive summary

Five specialists looked at five different slices of CAS-Native and proposed redesigns. Read together, they describe **one model**, not five — because each slice's "structured replacement" lands on the same four CAS primitives: the open probability simplex Δ°₃₉ (Correction 4), the involution-pair structure (CO-2↔CO-3, etc.), the domain precedence preorder P ≻ C ≻ E ≻ O, and the section-retraction RPM chain (Correction 2). When these primitives are pushed all the way through — embedding → bottleneck → attention → heads → loss → optimizer — the redundancies collapse and the model becomes structurally consistent end-to-end. There is no slice where "make it more CAS-shaped" loses parameters or signal; every slice gets smaller, more interpretable, or both.

Headline numbers if all phases land: **embedding stack ~92% smaller** (#107: 16.5M → 1.30M); **per-layer transformer block ~27-40% smaller** (#108: 49.1M → ~30M static; ~−60% inference compute when RPM dynamic-depth halt fires); **prediction head +13% (~5K params) but jointly admissible** (#109); **optimizer state 6-7× smaller** (#110: ~200M → ~30M floats); **bottleneck 64 → 39 dim** (#111). Combined: **~30-40% total static parameter reduction, ~50-60% inference compute reduction, ~6-7× optimizer-state reduction**, with a predicted **+1.5-3 pp canonical-exact gain at the same training budget** primarily from structurally-honest gradients (Fisher-Rao optimizer + simplex bottleneck + admissibility loss). The qualitative win — every internal state is named in CAS coordinates, so Mode 7 traceability becomes a printout of the activations, not a probe — is the bigger story.

---

## §2 Coherence map (5×5)

The matrix below uses **synergy** (amplify each other), **orthogonal** (independent), **tension** (touch the same surface, need reconciliation), **conflict** (incompatible claim).

|             | #107 Embed | #108 Attn/Layer | #109 Heads/Loss | #110 Optimizer | #111 Statespace |
|-------------|------------|-----------------|------------------|-----------------|------------------|
| **#107 Embed** | — | synergy | synergy | strong synergy | strong synergy |
| **#108 Attn/Layer** | synergy | — | tension | tension | orthogonal |
| **#109 Heads/Loss** | synergy | tension | — | **TENSION (Fisher-Rao double-use)** | synergy |
| **#110 Optimizer** | strong synergy | tension | tension | — | strong synergy |
| **#111 Statespace** | strong synergy | orthogonal | synergy | strong synergy | — |

Cell-by-cell:

- **#107 ↔ #108.** *Synergy.* #107's simplex embedding produces a token-level 40-dim CAS distribution that #108's domain-descent routing α(t) ∈ Δ₃ over {P,C,E,O} (#108 §3 Prop A) can read directly. With unstructured embeddings the routing has to be inferred; with #107 it is given.
- **#107 ↔ #109.** *Synergy.* #109's Topos head reads operand slot logits over a 25-dim typed product (10 N + 4 D + 7 F + 4 R, #109 §3.1). #107's reserved-token anchor table populates those slots at init (#107 §3 Prop C).
- **#107 ↔ #110.** *Strong synergy.* #110's Fisher-Rao natural-gradient step (#110 §3.1) wants parameters on Δ°₃₉. #107 puts them there. Without #107, natural-gradient applies only to the cognitive-state head; with #107 it covers the embedding table too.
- **#107 ↔ #111.** *Strong synergy.* #111's 39-dim bottleneck and #107's 40-dim simplex embedding describe the same surface from two ends. Compose them and **the entire information path is on Δ°₃₉ from token-id to head**, with no unstructured R^k step in between.
- **#108 ↔ #109.** *Tension.* Both want to "lift" the Topos Reasoner. #108 §3 Prop E lifts it mid-stack as FiLM conditioning; #109 §3.1 makes it the output head. Reconciled in §5: do both — #108's lift is a 21-truth-value *conditioning signal* and #109's head is a 25-dim *structured output*.
- **#108 ↔ #110.** *Tension.* #108's RPM dynamic-depth halt gates *whether the next layer runs*. #110's RPM section-retraction guard gates *whether a parameter step is applied*. Both consume the same `gate_satisfaction` cache. If #108 halts layer L+1, that layer got no gradient and #110's guard has nothing to clip. Order-of-operations, not contradiction. Reconciled in §5.
- **#108 ↔ #111.** *Orthogonal.* #108 reshapes per-layer compute; #111 changes a single bottleneck dimension. They don't touch the same code path.
- **#109 ↔ #110.** ***Live tension — Fisher-Rao used in two places.*** #109 §3.4 puts Fisher-Rao geodesic distance into the **loss** (target one-hot smoothed; gradient through `2·arccos(Σ√(p_k q_k))`). #110 §3.1 puts the **inverse Fisher diagonal** as a preconditioner on the **gradient** before the step. Same metric, two roles. They compose constructively *only* if eps clamps match near the boundary; mismatched eps will produce blowup steps. Treated in §5 Tension 1 and §8 R-α.
- **#109 ↔ #111.** *Synergy.* #111's 39-dim simplex bottleneck is the natural input to #109's Topos head. #109's `bottleneck = 64` becomes `bottleneck = 39 (on Δ°₃₉)`, and the 25-dim operand product reads off the simplex by typed projection.
- **#110 ↔ #111.** *Strong synergy.* #110's Fisher-Rao natural-gradient is *defined* on the simplex. #111 moves the bottleneck onto the simplex. With both, the entire training dynamics — forward (representation) and backward (gradient) — happen in the same Riemannian geometry.

**Conflict count: zero outright. One genuine tension (#109 ↔ #110 Fisher-Rao double-use) needs aligned hyperparameters. One scope-overlap tension (#108 mid-stack lift vs #109 output head) resolves by separating their shapes.**

---

## §3 The unified architecture proposal

Every component below is replaceable behind a feature flag (per #109 §9, ADR-07 pattern); the v1 K=9 checkpoint remains byte-equivalent when all flags are False.

```
   raw token_ids
        │
        ▼
┌───────────────────────────┐  per #107 §3.B + §3.C
│  SimplexEmbedding         │  shape (V, 40); softmax+eps; reserved-token anchors
│  (~1.28M params)          │  trace: simplex_logits[id].softmax() == the token's CAS reading
└───────────────────────────┘
        │ (B, S, 40)  on Δ°₃₉
        ▼
┌───────────────────────────┐  per #107 §8 (40→d_model expand)
│  SimplexToHidden          │  Linear(40, d_model); ~21K params
└───────────────────────────┘
        │ (B, S, d_model=512)
        ▼
┌───────────────────────────────────────────────────────┐  per #108 §8 CASBlockV2
│  CASBlockV2  (×n_layers, dynamic depth)               │
│   ├─ aggregate tokens → 40-slot bank (slot_weights)   │
│   ├─ Hutchinson IFS on slot bank (Prop B)             │
│   ├─ slot-to-slot attn w/ P≻C≻E≻O descent mask        │
│   ├─ scatter back to tokens (token_out)               │
│   ├─ small FFN                                        │
│   └─ RPM halt: sat_a0,d,w,p → halt_score              │
│  per_layer_rpm + halt_score → trace                   │
│  (~5.0M params/layer; halt may end stack early)       │
└───────────────────────────────────────────────────────┘
        │ (B, S, d_model)
        ▼
┌───────────────────────────┐  per #111 §8 simplex bottleneck
│  SimplexBottleneck        │  Linear(d_model, 40)→softmax+eps→drop coord 0 → R^39
│  on Δ°₃₉                  │  enables Fisher-Rao distance between samples
└───────────────────────────┘
        │ (B, 39) on Δ°₃₉
        ▼
┌───────────────────────────────────────────────────────┐  per #109 §3.1 ToposStructuredHead
│  ToposStructuredHead                                  │
│   ├─ op_logits  (B, 5)        × ÷ ∘ + −                │
│   ├─ operand_logits (B, M, 25) typed: 10 N | 4 D | 7 F | 4 R│
│   ├─ omega_logits (B, 2)      named-emergent flag     │
│   └─ aux heads (turn_type, expr_family, ...)          │
│  (~6.9K params; legacy 12-key dict derived by rule)   │
└───────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────┐  per #109 §3.2-§3.5 + #110 §3
│  topos_structured_loss                                │
│   ├─ L_geodesic  (Fisher-Rao on Δ°₃₉ — #109 §3.4)     │
│   ├─ L_admit     (compiler-derived admissibility — §3.2)│
│   ├─ L_inv_N/W/F (probabilistic Inversion-Scan shadow — §3.3)│
│   ├─ rpm-gated:  sat * L + (1-sat) * L_rpm_repair (§3.5)│
│   └─ L_aux       (small CE on auxiliary heads)        │
│  every term named → trace                             │
└───────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────┐  per #110 CASOpt
│  CASOpt (replaces AdamW)                              │
│   ├─ §3.1 Fisher-Rao natural-gradient on simplex-tied blocks│
│   ├─ §3.2 RPM section-retraction guard (consumes halt cache)│
│   ├─ §3.3 Domain-keyed LR + symmetric Drive-pair decay │
│   └─ §3.4 Inversion-Scan one-step lookahead step modulator│
│  per-step trace: which guard fired, which pair clipped│
└───────────────────────────────────────────────────────┘
```

The architecture is reversible at every flag. Any one component can be flipped off without affecting the others — except the two stated tensions (Fisher-Rao eps alignment between #109 and #110; halt vs guard interaction between #108 and #110), addressed in §5.

---

## §4 Combined number estimates

Worked from each specialist's baseline (current K=9 checkpoint, d_model = 512, vocab = 32 000, n_layers = 6, bottleneck = 64).

**Static parameter count (full model):**

| Section | Today | Unified | Δ | Source |
|---|---:|---:|---:|---|
| Surface embedding stack | 16.5 M | 1.30 M | **−92%** | #107 §4 table |
| Transformer 6-layer stack | 49.1 M | 30.0 M (Prop A+B) — 21 M (Prop A+B+D) | **−39 to −57%** | #108 §4 table |
| Bottleneck projection | 4.1 K | 2.5 K | −1.6 K | #111 §4 |
| Prediction head | 37.6 K | 42.7 K | +5.0 K | #109 §4 |
| Mid-stack topos lift (#108 Prop E) | — | +10 K | +10 K | #108 §4 |
| **Estimated total** | **~65.7 M** | **~31.4-40.4 M** | **−39% to −52%** | sum |

**Inference compute** (#108 Prop C dynamic-depth halt): **~−25-60% wall-clock**, depending on input difficulty distribution. The "easy questions stop at layer 2" property predicts >40% of the 1K eval halts at L ≤ 4 of 6 (#108 P3 prediction).

**Optimizer state** (#110 §4 table): ~200 M floats → ~30 M floats, **~6-7× reduction**, freeing ~0.6 GB of GPU memory for batch headroom.

**Predicted capability gain (combined falsification battery):** taking each specialist's quantitative prediction and conservatively summing the non-overlapping ones:

- #107 P2: structured init reaches 50% canonical-exact in epoch 1 (vs <30% for random init); P3: simplex embeddings within 5pp of full baseline at 1/12 the params.
- #108 P3: dynamic-halt cuts inference compute >25% with no canonical regression.
- #109 A: admissibility-rate of inadmissible predictions ≤ 1% (from current ~7%); B: paraphrase-canonical operator-balance correlation drops to |r| < 0.1.
- #110 #1: ≥ +1.5 pp canonical-exact; #2: drive-head accuracy ≥ +3 pp.
- #111 #1: ≤ 2 pp regression on bottleneck swap (a *passing* threshold; expect 0-1 pp).

Combined headline at full epoch budget: **+1.5 to +3.0 pp on canonical exact, +3-5 pp on drive head, near-zero inadmissible structural error, with 30-50% fewer total parameters and 25-60% less inference compute**.

---

## §5 Conflicts and reconciliations

**Tension 1 — Fisher-Rao used in both loss (#109 §3.4) and optimizer (#110 §3.1).**

*The setup.* #109 puts geodesic distance into `L_geodesic = 2·arccos(Σ√(p_k q_k))` against a smoothed target. #110 multiplies the raw gradient by the diagonal Fisher inverse `pk·(1−pk)` before stepping. Both are correct uses of the simplex's natural geometry; they live at different points in the chain rule.

*The risk.* Near the simplex boundary (small pk), `L_geodesic` gradient diverges as `1/√(pk)` and `1/(pk(1−pk))` blows up. If #109's smoothing eps and #110's `pk(1-pk)+1e-12` floor are inconsistent, one denominator can be small while the other is not, producing one or two numerical-blowup steps per epoch.

*Resolution.* Tie the two epsilons. Pick a single `simplex_floor = 1e-6` (raised from 1e-8 for BF16 safety per #111 §7 risk 3) used by both #109's target smoothing AND #110's Fisher diagonal. Add a unit test that walks the entire pipeline at `pk = simplex_floor` and verifies finite gradient. **Net result: the two Fisher-Rao uses compose constructively; the loss measures distance in the right metric, and the optimizer takes steps that are uniform in that metric.** This was the single biggest reason to do both at once: AdamW + Fisher-Rao loss has a known cancellation (#110 §5 bullet 1) that disappears when the optimizer is also Fisher-Rao.

**Tension 2 — Topos Reasoner location: mid-stack lift (#108 Prop E) vs output head (#109 §3.1).**

*The setup.* Both specialists want the Topos Reasoner doing real computational work, not just decoration. #108 wants a 21-truth-value conditioning signal mid-stack; #109 wants the structured output head.

*Resolution.* Do both, with renamed roles. #108's mid-stack object is a **TruthValueConditioning** (21 truth values × 1 layer's worth of FiLM modulation). #109's output object is a **ToposStructuredHead** (25-dim typed operand product over the 5 generative operations). They share *the idea* of intuitionistic 3-valued logic but operate on different shapes and at different depths. The compiler in `api/notation/compiler.py` already validates both (atom-level admissibility for the head, cross-axis admissibility for the conditioning); no double-counting.

**Tension 3 — RPM dynamic-depth halt (#108 Prop C) vs RPM section-retraction guard (#110 §3.2).**

*The setup.* #108's halt asks "should the next layer compute at all?" #110's guard asks "should this parameter group take its proposed step?" Both consume `gate_satisfaction`. If layer L+1 is halted, its parameters got no gradient — so #110's guard is moot for that layer, but **the optimizer also cannot use the halt event as a learning signal that the lower-layer parameters need to retreat**.

*Resolution.* Sequence them:

1. **Forward pass:** layers compute or halt per #108's halt threshold τ. Halt events are logged.
2. **Backward pass:** gradients flow through the un-halted prefix only.
3. **Optimizer step:** for parameter groups whose forward path traversed an *un-halted* layer, #110's section-retraction guard fires normally. For parameter groups in halted layers, the guard simply records "no step needed" in the trace.
4. **Halt threshold τ is itself a learnable scalar** (per #108 §7 open question 2), gradient-coupled to the halt-frequency target. This means the optimizer *can* indirectly tune halt behavior even when no layer-internal gradients flowed.

Net: #108 saves inference compute, #110 saves optimizer steps, **the union saves both** without contradiction.

**Tension 4 — Per-domain learning rate (#110 §3.3) vs domain-precedence-respecting init (#107 §3 Prop A.3).**

*The setup.* #110 wants P-domain heads to learn slowly (lr ratio 1:1.5:2:3 across P:C:E:O). #107 wants P-domain weights initialized larger (1.5× / 1.0× / 0.7× / 0.5×). Both express the same priorhood ("P is higher in the precedence stack and should change slowly / start strong"), but they're priors at different times (init vs runtime).

*Resolution.* Compatible by design. The init bias gives the model the *correct starting point*; the optimizer scaling keeps it from drifting too fast. In ablation, run them independently to confirm direction; ship both if both pass falsification (#110 P2 + #107 P1).

**No remaining conflicts requiring user input — all four tensions are resolvable inside the unified architecture.** What does require user input is the deeper-question set in §7.

---

## §6 Phased prototype roadmap

Each phase has a *smoke test* (cheap go/no-go) and an *acceptance gate* (the falsification each specialist hung their proposal on).

### Phase A — Free-lunch validations (no retrain; existing checkpoint)

Estimated total effort: **~1 pod-day** across all three.

- **A.1 Fractal-gate identity check** (#108 §7 Risk 1). Walk the v1 retrain checkpoint; print `fractal_gate` per layer. If gate ≈ 1.0 across layers, the parallel fractal path is a learned identity; dropping it (#108 Prop A) is *free*. If 0.4-0.6, retain. **Smoke:** 1 line of print code on existing checkpoint. **Gate:** if any layer's gate ∈ [0.9, 1.0], that layer's fractal path is provably ablatable.
- **A.2 Reserved-token anchor unit test** (#107 P5). Build the anchor table in #107 §8 code sketch *as a standalone Python script*; verify each of the 14 reserved tokens lands on the spec'd subset of Δ°₃₉ with eps tolerance. **Smoke:** unit test, no GPU. **Gate:** all 14 anchors within 2pp of spec; fail = anchor table bug, not framework bug.
- **A.3 Fisher-Rao retrofit smoke** (#110 §3.1, narrow scope). Replace AdamW with a 50-line `CASOpt-Fisher-only` variant on the **cognitive-state head only** (10 layers × 40 floats of Fisher diagonal). Train for 1 epoch on the 5K Lever-3 paired corpus; compare canonical-exact at epoch 1 vs the AdamW baseline. **Smoke:** ~1 hour A6000 time. **Gate:** ≥ +0.5pp at epoch 1 (the dominant test prediction is faster early-epoch convergence, not final asymptote).

**Phase A is the minimum viable validation. All three are surgical and return data-driven yes/no.**

### Phase B — Small architectural changes (one-checkpoint smoke retrain each)

Estimated total effort: **~2-3 pod-days** in parallel.

- **B.1 Simplex embeddings** (#107 §3 Prop B + Prop C). Replace `nn.Embedding(32K, 512)` with `SimplexEmbedding(32K, 40)` + `SimplexToHidden(40, 512)`. Reserved-token anchor table from A.2 wired in. Single 1-epoch retrain on Lever-3 paired corpus.
  - **Acceptance gate** (#107 P3): canonical-exact within 5pp of the 16.4M-embedding baseline. Falsifies if gap > 10pp.
- **B.2 Topos Structured Head behind feature flag** (#109 §3.1 + §3.2-3.5 loss). Build `ToposStructuredHead` and `topos_structured_loss` as additive files; flag default False. Train 1 epoch with flag True on Lever-3 paired corpus.
  - **Acceptance gate** (#109 A): admissibility-rate of inadmissible predictions ≤ 1% after 1K training steps. Falsifies if ≥ 5%.
- **B.3 39-dim simplex bottleneck** (#111 §3). Add `--simplex-bottleneck` flag to `train_structured_prediction.py`; A/B against 64-dim baseline at matched epoch budget.
  - **Acceptance gate** (#111 #1): aggregate paraphrase exact-match within 2pp of 64-dim baseline. Falsifies regression > 2pp (which would mean the 25 extra dims were doing real work — diagnostic finding either way).

Phases B.1-B.3 can run in parallel (independent code paths). Compose them only after each individually clears its gate.

### Phase C — Larger refactors (multi-day pod time)

Estimated total effort: **~1 pod-week** sequential.

- **C.1 RPM dynamic-depth halt** (#108 Prop C). Surgical edit to layer loop in `CASNativeModel.forward`. Sharpness annealing schedule + load-balancing loss to prevent halt-at-layer-1 collapse (#108 §7 Risk 2).
  - **Acceptance gate** (#108 P3): >40% of 1K eval halts at L ≤ 4 of 6 with no canonical regression vs always-run.
- **C.2 Domain-Descent attention as default + Hutchinson on slot bank** (#108 Prop A + Prop B). Replace `CASTransformerLayer` with `CASBlockV2` (#108 §8 sketch).
  - **Acceptance gate** (#108 P2): merged slot-Hutchinson + descent matches or beats current dual-path at 30% fewer params on canonical exact + meta_relations.
- **C.3 Full 5-op alphabet block sequence** (#108 Prop D). Layer sequence `[+, ∘, ×, ÷, ×, −]` with typed module shapes (#108 §3 Prop D table). Compiler validates the layer sequence the same way it validates CAS expressions (#108 §7 open question 1).
  - **Acceptance gate** (#108 P4): typed beats parity-param all-generic on meta-logic bucket.
- **C.4 Full CASOpt** (#110 §3.1-3.4 all four components). Five-run ablation harness (#110 §7 Risk 5). Wire into `train_structured_prediction.py:906`.
  - **Acceptance gate** (#110 #1-#4): canonical ≥ +1.5pp; drive ≥ +3pp; gate-satisfaction monotone; inversion-penalty monotone-non-increasing in expectation.

### Phase D — Research-grade (gated on external dependencies)

Estimated total effort: **multi-month**, not committed.

- **D.1 48-dim A₀-admission state space** (#107 Prop D, #111 §11). Requires IP attorney consultation (per CLAUDE.md "Authoritative Noetic Definitions" + Clarification 8 §12 legal framing) AND parallel formal write-up extending the Noetic Topos paper from `|I| = 40` to `|I| = 48`. *DO NOT implement before user IP consultation.* If pursued, sized as additive admission of `A₀` only (Δ°₃₉ → Δ°₄₀, not Δ°₄₇), preserving topos paper compatibility.
- **D.2 d_model reduction** (#111 §4 paragraph 5). Reduce d_model from 512 → 39 to compound the bottleneck savings. Couples two changes that should be diagnosed independently first; do AFTER B.3 lands.
- **D.3 Joint structured CRF loss** (#109 §3.6). Most expensive head change; defer until §3.1-§3.5 are validated. Cost is O(|admitted-triples|) per example.

---

## §7 Genuinely open questions for the user

Deduped from all five specialists, ordered by load-bearingness (Phase-A blockers first; Phase-D gates last).

1. **(Blocks Phase B.1)** Should reserved-token anchors be **frozen** (`requires_grad=False`) or **soft-trainable** (gradient-trainable from the anchor)? `RegisterLatent` precedent uses freeze-then-unfreeze warmup (#107 §7 OQ1). Frozen guarantees traceability forever; soft allows refinement. Default proposal: soft, with a freeze-early epochs-then-unfreeze schedule. **Need user direction.**
2. **(Blocks Phase B.2)** Is the legacy 12-key dict surface contract (`predict_cas.py`, chat REPL, belief store, trace package) **frozen** or can the v1 retrain consumer change with the head? Per #109 §7 risk 4, the redesign is built to derive 12 keys from the structured proposal, so the contract is preserved. Should it be?
3. **(Blocks Phase C.1 design)** What is the right interpretation of #108's halt threshold τ — global scalar, per-layer learnable, or input-dependent (#108 §7 OQ2)? Input-dependent is most expressive but adds a discrete trace decision the user might not want.
4. **(Blocks Phase C.4 ablation)** Is the per-domain LR ratio `1:1.5:2:3` (#110 §3.3) defensible against the SDG corpus's *actual* domain distribution, or does the SDG over-represent O-domain examples (in which case the ratio inverts)? **Action: estimate corpus domain ratios before committing the ratio.**
5. **(Blocks Phase D.1)** Is admitting A₀ ("Pure Desire" / Keter) as a 41st state-vector dimension on the table, or out of scope for the current patent / framework version (#111 §6 OQ1, #107 §7 Risk 3)? In scope = framework move to v7.8 + topos paper extension + IP consultation. Out of scope = drop 48-dim variant entirely.
6. **(Blocks Phase D.2)** Should d_model be reduced in lockstep with bottleneck, or kept at 512 for representational headroom on the side-channel (#111 §6 OQ2)?
7. **(Cosmetic but user-facing)** Is the Phase A "Radial Architecture Display" mandala committed to 40 cells, or could it move to a 39-simplex barycentric rendering (#111 §6 OQ3)? Affects user-facing number choice.

Questions 1, 2, 4 block near-term work. Question 5 is the big one — the answer dictates whether Phase D exists at all.

---

## §8 Risks across the unified proposal

Beyond the per-specialist risks (each specialist's §7 still applies in their slice), these are *interaction* risks the consolidator can see only by reading all five together:

- **R-α: Boundary-pile-up under combined Fisher-Rao loss + Fisher-Rao optimizer** (composition of #109 §3.4 and #110 §3.1, addressed in §5 Tension 1). With both pulling toward the simplex interior, the model may "chase the interior" and underweight boundary states (e.g., near-pure-^P predictions). *Mitigation:* monitor entropy of bottleneck distribution per epoch; if mean entropy is climbing monotonically, lower the smoothing eps on the loss side or relax the inversion-modulation in #110 §3.4.
- **R-β: Halt + guard collapse to "halt at layer 1"** (composition of #108 Prop C and #110 §3.2). If load-balancing isn't carefully tuned, the dynamic-depth halt converges to "always halt early" (PonderNet failure mode), AND the section-retraction guard zeros most parameter steps. Compounded, the model stops learning and looks like progress (low compute, satisfied gates). *Mitigation:* monitor `halt_layer` distribution + `step_clip_count` *together*, alarm if both exceed a threshold simultaneously.
- **R-γ: Domain-keyed LR + structured init double-applies the same prior.** If P-domain heads start strong (#107 A.3) and learn slowly (#110 §3.3), they may *under-fit* once the SDG demands the prior be revised. *Mitigation:* the ablation harness in #110 §7 Risk 5 already runs these as separate components; verify each direction on its own before composing.
- **R-δ: Trace explosion.** Each specialist adds keys to `outputs`. Combined: simplex_logits per token, halt_layer per sample, per_layer_rpm, slot_states, op_logits, operand_logits, mid_topos truth values, every loss term, every optimizer-step decision. Without a budget, this dwarfs the predictions. *Mitigation:* trace-size SLA up front (#108 §7 Risk 6); compress detached tensors, sample at a configurable rate, default off in production hot paths.
- **R-ε: Compiler scope gap on v7.6/v7.7.** #109 §3.2 admissibility table only covers operations the compiler currently validates uniformly (state, register_state, rule_four). Production-semantics recipes (Θ, Λ, Ω) and v7.7 cross-register integration (`×` with named emergent result) have partial coverage. If the unified loss penalizes valid v7.7 expressions as inadmissible, training regresses on the meta_logic bucket. *Mitigation:* gate `L_admit` to compiler-validated operations only at first; expand the table as the compiler does (#109 §7 Risk 1).
- **R-ζ: Bottleneck information loss when 25 dims of "non-state residue" disappear.** #111 §7 risk 2 already flags this; the fix is the d_model side-channel. The interaction risk is that #107's simplex embedding **already collapses** 512 → 40 at the input. If the side-channel disappears at *both* ends (input simplex + bottleneck simplex), surface-form features have nowhere to live, and natural-language-only tokens (the 32K BPE wordpieces with no CAS reading) get squeezed out. *Mitigation:* the residual k-dim channel proposed in #107 §3 Prop B Risk mitigation. **This is the architectural decision that makes or breaks the unified design** — see §7 Open Question 2.

---

## §9 Falsification battery

A consolidated experiment list. Each test names its specialist + which phase it gates.

**Phase-A tests (no retrain, existing checkpoint):**

- T-A1. (#108 P0/Risk 1) Print `fractal_gate` per layer on K=9 checkpoint. *Gate:* mean ≥ 0.9 → fractal path is identity.
- T-A2. (#107 P5) Reserved-token anchor unit test. *Gate:* all 14 anchors within 2pp of spec.
- T-A3. (#110 P narrow) AdamW vs CASOpt-Fisher-only on cognitive-state head, 1 epoch. *Gate:* ≥ +0.5pp canonical-exact at epoch 1.
- T-A4. (#107 P1) On a fresh `CognitiveStateEmbedding`, apply A.1 domain-block bias init. *Gate:* mean P(P-row) > C > E > O with gap ≥ 0.005.

**Phase-B tests (1-epoch retrains):**

- T-B1. (#107 P2 + P3) Run 1 (baseline) vs Run 2 (Prop A init only) vs Run 3 (Prop B simplex embedding). *Gates:* P2 ≥ 50% canonical-exact in epoch 1; P3 within 5pp of full baseline.
- T-B2. (#109 A + B) Topos head + admissibility loss. *Gates:* A: admissibility-rate ≤ 1% after 1K steps; B: paraphrase-canonical operator-balance correlation |r| < 0.1.
- T-B3. (#111 #1 + #2) 39-simplex bottleneck A/B. *Gates:* #1: paraphrase exact-match within 2pp of 64-dim; #2: Fisher-Rao distance correlates with structural similarity at Spearman ρ ≥ 0.5.

**Phase-C tests (multi-epoch full retrains):**

- T-C1. (#108 P3) Dynamic-depth halt. *Gate:* >40% of 1K eval halts at L ≤ 4 of 6, no canonical regression.
- T-C2. (#108 P2 + P5) Domain-descent + slot-Hutchinson; mid-stack topos lift. *Gates:* P2: matches or beats dual-path at 30% fewer params; P5: inversion-axis P flag rate cut > 30%.
- T-C3. (#108 P4) 5-op alphabet on meta-logic bucket. *Gate:* typed beats parity-param all-generic.
- T-C4. (#110 #1-#4) Full CASOpt ablation harness, five runs (AdamW, +Fisher, +RPM-guard, +Domain-LR/Drive-decay, +Inversion-modulation, full). *Gates:* canonical ≥ +1.5pp; drive ≥ +3pp; gate-satisfaction monotone; inversion monotone-non-increasing.
- T-C5. (#109 C + D) Calibration ECE; RPM-gated loss does not regress satisfied-RPM examples. *Gates:* C: Fisher-Rao ECE strictly lower; D: lm_loss does not regress > noise on satisfied examples.

**Phase-D tests (research, gated on user IP consultation):**

- T-D1. (#107 D, #111 §11) 48-dim variant ablation: 40-state vs 41-state (40 + A₀) vs 48-state full. Cannot run without IP consultation green-light.
- T-D2. (#111 §6 OQ2) d_model = 39 lockstep with bottleneck. After B.3 lands.
- T-D3. (#109 §3.6) Joint structured CRF loss. After B.2 + C-tier landings.

---

## §10 Citations

All claims trace to either a specialist note (e.g., "#107 §3.B"), a `CLAUDE.md` section, the Foundational Clarifications, the peer-review paper PDF, or a code file:line.

**CLAUDE.md (project instructions):**

- Authoritative Noetic Definitions, 10 Noetics, ^5 expanded scope, Colloquialism Test, anti-drift annotations.
- Four Critical Mathematical Corrections (1, 2, 3, 4).
- Structural invariants: 10 Noetics + 4 Domains + 7 Drives + 4 Registers; involution pairs CO-2↔CO-3, CO-5↔CO-6, CO-8↔CO-9; self-duals CO-0/1/4/7; Drive inversion pairs F1↔F7, F2↔F6, F3↔F5; F4 self-dual; total order P ≻ C ≻ E ≻ O; 22 Capability Pathways including A0; 7 Inversion Axes (N, W, F, E, S, A, P).
- Phenomenological Register §v7.5; Production Semantics §v7.6 (Θ, Ω, Λ); Register Multiplicity §v7.7 (`+` vs `×` vs `|⟨…⟩`).
- Phase 4 CAS-Native AI deliverable list.

**Foundational clarifications** (`docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`):

- Clarification 1 (10 authoritative Noetics, verbatim canonical); Clarification 5 (^5 substrate); Clarification 6 (Colloquialism Test); Clarification 8 (Register axis, identity-init precedent, §6 P:C:E:O total order, §8 cross-validation, §12 patent legal framing); Clarification 9 §2 (Θ, Ω, Λ definitions); Clarification 9 §6 lines 547-559 (5 Generative Operations); Clarification 10 §3-4 (operator discipline + admissibility); §11 register involutions.

**Peer-review paper** (`peer_review/journal_submission/main.pdf`):

- Page 2, Definition 3.1 (`|I| = 40` with partition `I_A ⊔ I_B ⊔ I_C ⊔ I_D` and preorder A ≽ B ≽ C ≽ D = P ≽ C ≽ E ≽ O).
- Page 7, Definition 8.1 (`Δ°₃₉ ⊆ R^40`, smooth manifold of dimension 39).
- Page 7, Definition 8.4 (Fisher-Rao metric `g^FR_p(u,v) = Σ uk·vk / pk`).
- Page 7, Example 8.5 (canonical noetic manifold dim 78 = 39 × 2).
- Pages 200-243 (section-retraction axioms; Proposition `prop:rpm-pullback`).

**"When Light and Consciousness Share the Same Number" PDF:**

- Page 2 (TKS path to 48 = 40 Elements + 7 Foundations + 1 A₀).
- Page 4 (honest delimitation: "decomposition of 48 is fundamentally different").
- Page 5 (su(7) physics 48 unrelated to TKS additive 48; "consequence of experimental choice").
- Page 6 (Frame 1/2/3 interpretive options; structural-archetype framing).

**Code citations** (all under `noetic-compass-scaffold/noetic-compass/`; specialist note in brackets carries the exact line ranges):

- `cas-native/model/structured_token_embedding.py:22-98` [#107 §2-3] — current 16.4M-param embedding stack.
- `cas-native/model/embedding.py:43-47, 50-97, 70-86` [#107 §2; #111 §2] — NUM_COGNITIVE_STATES=40, SIMPLEX_EPS, CognitiveStateEmbedding, open-simplex projection.
- `cas-native/model/domain_descent.py:23-225` [#108 §2; #111 §2] — descent mask + slot attention.
- `cas-native/model/fractal_attention.py:18-211` [#108 §2-3] — Hutchinson IFS + fractal head.
- `cas-native/model/rpm_gate.py:21-340` [#108 §2; #110 §2-3] — SoftGate, PrerequisiteGateLayer, eta/epsilon, satisfaction cache (lines 76, 104-109), RecursiveRPMGate scaffold.
- `cas-native/model/register_film.py:96-374` [#107 §2; #108 §2] — RegisterLatent zero-init precedent + freeze/unfreeze (lines 209-216).
- `cas-native/model/topos_reasoner.py:40-114` [#108 §3 Prop E; #109 §2] — output-only Topos reasoner.
- `cas-native/model/composition.py:23-145` [#108 §2-3] — CompositionHead monoid table.
- `cas-native/model/lacunarity_gate.py:17-80` [#108 §2] — self-correction lacunarity gate.
- `cas-native/model/expression_proposer.py` [#109 §2] — ADR-07 structured proposer (precedent for §3.1).
- `cas-native/model/structured_prediction.py:58-67` [#109 §2; #111 §2-3] — DOMAIN/DRIVE/REGISTER/REGISTER_MODE labels + 12-head stack.
- `cas-native/model/loss.py:48-365` [#109 §3.4; #110 §2-3.3] — fisher_rao_distance, compute_inversion_penalty, compute_cognitive_drift_loss, InvolutionConstraintLoss.
- `cas-native/model/cas_native_model.py:62-643` [#107 §2; #108 §2-4] — defaults d_model=512, CASTransformerLayer, fractal_gate (line 127), forward, RPM aggregation, register usage.
- `cas-native/training/train_structured_prediction.py:144, 518, 906, 1141` [#110 §2; #111 §2] — AdamW call sites + `--bottleneck-dim` default 64.
- `cas-native/tokenizer/vocabulary.py:37-77` [#107 §3 Prop C] — 8 reserved tokens + source-aware compound keys.
- `cas-native/tokenizer/structured_token.py:35-38` [#107 §2] — axis lengths Noetic 10, Domain 4, Drive 7, Register 4 → signature_dim 25.
- `cas-engine/src/metric/mod.rs:99-162` [#110 §2 + Amari 1998 ref] — Fisher-Rao inner product, Bhattacharyya geodesic.
- `cas-engine/src/inversions/mod.rs:1-120` [#110 §3.4] — 7-axis scanner.
- `api/notation/compiler.py:1588, 2867` [#109 §3.2; #108 §3 Prop D] — `_is_admissible` + v7.7 §4 enforcement.
- `api/notation/inversion.py` [#109 §3.3] — 7-axis Inversion Scan.

**HONEST_STATUS** (`noetic-compass-scaffold/noetic-compass/HONEST_STATUS.md`):

- Lines 23, 36-43, 53-65, 86 — K=9 baseline 93.2% canonical exact, Mode 7 trace SCAFFOLD, NL generation NOT STARTED, vocab14 reserved CAS tokens [#107, #108, #109, #110, #111 §2].

**Memory references (user-ratified durable directives):** `feedback_traceability_is_the_whole_purpose`, `feedback_no_foreign_architecture_cas_only`, `feedback_object_traceability_required`, `feedback_real_metric_is_samples`, `feedback_eval_file_slip_recurrent`, `feedback_limit_default_128_trap`, `feedback_parallelize_sdg_with_training`, `feedback_user_ratifications_2026_05_04`, `feedback_plain_language_no_jargon`, `project_paraphrase_failure_modes_diagnoses`, `project_pr6_diagloop_eval_mode_bug_2026_05_03`, `project_native_gen_open_questions_already_answered`.
