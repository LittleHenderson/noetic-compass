# Lacunarity in CTT training — design note v1 (2026-10-23)

Status: **design note, nothing trained, nothing scored, no claim.** Every number below is either (a) measured
today from the c45 artefacts and the frozen corpus, with its source named, or (b) a derivation from a stated
definition, or (c) an explicitly labelled proposal. Claim vocabulary is the project's own:
`MEASURED` / `DERIVED` / `PROPOSED` / `NOT CLAIMED`. Nothing here licenses a change to the frozen CTT pipeline.

Scope: the draft this note refines came from a ChatGPT conversation about "lacunarity in gradient descent". The
draft's instinct is good. Its object, its equation and its stability are wrong, and for CTT-1 its expected effect is
close to zero. This note keeps the good part, fixes the rest, and puts a number on what can be tested.

Files beside this note:
- `lacunarity.py` — the estimator and the bounded schedule (stdlib only; the trainer imports it on the GPU host).
- `test_lacunarity.py` — 14 tests. `python -X utf8 -m pytest -q test_lacunarity.py` → **14 passed in 0.08s**
  (run today on the laptop, CPU, no torch). Status: `MEASURED`.
- `measure_corpus_lacunarity.py` — reproduces section 3's corpus numbers from the frozen `train.jsonl`.
- `PREREGISTRATION_AMENDMENT_DRAFT_v0_LACUNARITY.md` — the experiment this would need, as a draft for the owner,
  not an approval.

---

## 0. Said plainly first

1. **The draft confuses a landscape with a statistic.** "Lacunarity of the gradient" has no meaning until you say
   *which field*, *over what space*, and *at what box size*. Lacunarity is a property of a mass distribution over a
   space, measured at a scale. Gradients are a vector field over parameters; the loss is a field over tokens. The
   draft never fixes either.
2. **Its equation is unbounded and unitless.** `α(t) = α₀·(1 + λ·L(t))` can multiply the step by 50 when the field is
   gappy (lacunarity is not capped at 1). There is no stability argument, no normalisation, and no definition of
   `L(t)`. A single runaway factor at step 900 destroys a run.
3. **Adam already does the thing the draft wants, coordinate by coordinate.** A *global* multiplier on Adam's step
   is just a slower or faster learning rate. It cannot redistribute effort toward the tokens that carry the error.
   Redistribution needs per-block or per-token weighting, not one global number.
4. **CTT-1 is not an optimisation failure.** It reached training loss `1.8003862351179123e-05` and **987 of 1000**
   exact training rows (`MEASURED`, `runs/A4-s1/WEIGHTS_MANIFEST.json`). The exam gap is an abstention / distribution
   shift problem: on the primary exam the translator was called 103 times and offered a reading **1–2 times**
   (`MEASURED`, `CTT_READING.json`). A step-size schedule cannot fix "it almost always asks".
5. **What survives is worth keeping.** Lacunarity is a real, cheap, well-defined measurement. It belongs in CTT
   training as *instrumentation first* (free), as a *per-block trust signal* second (cheap pilot), and as a *global
   step-size modulator* last (null control, expected to do nothing). Section 8 orders the work accordingly.

---

## 1. The refined note (drop-in replacement for the draft)

> **Lacunarity in CTT training**
>
> A CTT does not learn uniformly across its target. Most target tokens are structural and quickly saturated; a few
> carry nearly all the remaining error. How unevenly that error is spread is a measurable property of the field, and
> the measurement has a name: lacunarity — the degree to which mass clusters into a few regions with gaps between
> them. At a box size `b` over a non-negative field, `L(b) = 1 + Var(N_b)/E[N_b]²`: exactly 1 when every window
> carries the same mass, larger as the mass concentrates.
>
> The useful claim is not "follow the lacunarity with the learning rate". It is narrower and testable: measure the
> error field at fixed scales during training, and use *bounded, per-block* adjustments only where a clustered
> gradient mass gives a reason to. Any global multiplier must be normalised, clipped to a stated band, ramped in
> after warmup, and must reduce exactly to the frozen schedule when its weight is zero. A schedule that cannot
> reproduce the baseline bit for bit is not a schedule; it is a new run with unmeasured differences.
>
> For CTT-1 the measurement is expected to show that the error field becomes uniform early, because training
> converges to near-zero loss within a few epochs. That prediction is itself the first experiment: if the field is
> uniform by epoch 3, the step-size idea has nothing to act on, and the honest conclusion is that lacunarity belongs
> in the data and decision layers, not in the optimiser.

Status of that note: `PROPOSED`. It contains one testable prediction and no claim of gain.

---

## 2. Definition, stated so it can be computed

**Lacunarity.** Mandelbrot introduced the word for the gapiness of a fractal: two sets with the same fractal
dimension can differ in how their mass is distributed, and lacunarity is what distinguishes them.

**The estimator used here** (gliding box, Plotnick et al. 1996). For a non-negative field `x` of length `n` and a
box length `b`:

```
N_i = Σ_{j=i}^{i+b-1} x_j          for every start i = 0 … n-b
L(b) = 1 + Var(N) / E[N]²
```

Properties that matter for honest use:
- `L(b) ≥ 1` always; `L(b) = 1` exactly for a uniform field (`Var = 0`).
- `L(b)` depends on `b`. There is no "the lacunarity" of a field, only `L` at stated scales.
- Computation is `O(n)` with a sliding window; on a batch of 256×128 tokens it is microseconds.
- Undefined cases (empty field, all-zero mass, `b > n`) return `None`, never a silent 0 or 1.

**What the field can be, for a CTT** (this is the choice the draft skipped):

| Field | Space | Element | Natural boxes | What a high value means |
|---|---|---|---|---|
| Error field | target tokens of one batch | per-token NLL | 4, 16, 64 tokens | a few token positions hold the error |
| Gradient-mass field | parameters of one named block | `g_i²` | 4, 16, 64 parameters | a few coordinates dominate the update |
| Block field | named parameter blocks | block gradient L2 norm | 2–4 blocks | effort is concentrated in a few blocks |
| Corpus field | vocabulary sorted by frequency | token count | 4–128 tokens | the training distribution itself is gappy |

**What it is not.** Not curvature, not sharpness (SAM's object), not the Hessian spectrum, not Adam's second
moment, not the gradient noise scale (McCandlish et al. 2018 — that is a variance-to-mean ratio over *examples*
without any box structure). Conflating these is how the draft lost its footing.

---

## 3. What the CTT evidence says (measured today)

### 3.1 The training run converged (not an optimisation problem)

From `a1_unpacked/c45_out/ctt_out/runs/A4-s1/`:

| Quantity | Value | Source |
|---|---|---|
| Steps | 10,668 (12 epochs, batch 256) | `WEIGHTS_MANIFEST.json` |
| Wall clock on A10G | 770.7 s | same |
| Final training loss | `1.8003862351179123e-05` | same |
| Exact training rows (greedy, locked) | 987 / 1000 | same |
| Validation loss by epoch | 0.04835 → 0.0161 → 0.00993 → 0.00868 → 0.00946 → 0.00781 → 0.0094 → **0.00766 (min, epoch 7)** → 0.00788 → 0.00784 → 0.00811 → 0.00815 | `progress.jsonl` |

Reading: training loss is at the floor of fp32 reporting and the model reproduces 98.7% of the training targets
exactly. Validation bottoms at epoch 7 and then rises slightly — the classic memorisation turn. Any schedule change
acts on the *path* to this endpoint, not on a capacity shortfall. The Capacity Rules already say: grow only on
under-fitting. This run is not under-fit.

### 3.2 The corpus is strongly lacunar, and that is where the structure lives

`measure_corpus_lacunarity.py` over `data/train.jsonl` (227,497 rows):

| Measurement | Value |
|---|---|
| Rows | 227,497 (validation 10,098) |
| Distinct target tokens used | 145 (of a 341-token CAS side) |
| Total target tokens | 1,741,066 |
| Top-10 token mass | 1,141,428 / 1,741,066 = **0.6556** |
| Token entropy | **4.9389 bits** (maximum for 145 symbols: 7.1799) |
| First target token: `ANSWER` | 137,111 (60.3%) |
| First target token: `CLARIFY` | 32,066 (14.1%) |
| First target token: `NOT_MINE` | 22,807 (10.0%) |
| First target token: `WITNESS` | 9,556 (4.2%) |
| L over frequency-sorted vocabulary | box 4: **7.412**, 8: **6.143**, 16: **4.788**, 32: 3.556, 64: 2.468, 128: 1.226 |
| L over rows sorted by target length | box 4: 2.655, 8: 2.240, 16: 1.727, 32: 1.026 |
| Target lengths | multi-modal (36 tokens: 1,903 rows; 23: 3,208; 4: 53,190; 1: 22,867 …) |

Reading: at the scale of 8 vocabulary entries the mass is 6.1× more uneven than a uniform field. Two thirds of all
target tokens are ten symbols. The *static* corpus is lacunar; the *dynamic* error field is what training flattens.

### 3.3 The exam gap is abstention, not step size

From `CTT_READING.json` (primary, E-MACHINE-S, 128 items, 119 scored):

| Arm | Right | Translator calls | Readings offered | Malformed | Confident-wrong (cap 2) |
|---|---|---|---|---|---|
| A0 reader alone | 107 | — | — | — | — |
| A4-s1 | 106 | 103 | **1** | 0 | 1 |
| A4-s2 | 106 | 103 | **1** | 0 | 1 |
| A4-s3 | 105 | 103 | **2** | 0 | 2 |
| A2 retrieval (no learning) | 105 | 103 | 2 | 15 | 2 |
| C1 shuffled targets | 106 | 103 | 1 | 75 | 1 |
| C2 untrained | 106 | 103 | 1 | 85 | 1 |

Two facts stand out. First, the trained translator offered a reading on 1–2 of 103 calls — it almost always asked.
Second, the **untrained** control (C2, random weights) also scores 106, because the reader-first design hides the
translator: the exam mostly measures the reader. The frozen reading records the counts; it does not record *why* the
model asked. That mechanism is `NOT MEASURED` here and would need the per-item proposals to establish.

The LLM_WRITTEN pass shows the model can lift the reader (72 → 94/87/86) but it breached its safety gate
(confident-wrong 2/5/3 vs cap 2) → `EARS_HARMED`. So the capability exists; the decision rule around it does not yet
hold.

**Consequence for this design note:** the lever is the offer/abstain decision and out-of-distribution coverage. A
learning-rate modulator cannot move a decision that is made 103 times and yields 1–2 offers.

---

## 4. What the draft says, what breaks, what replaces it

| Draft claim | Problem | Repair used here |
|---|---|---|
| "Lacunarity describes how clustered a pattern is — like a forest with gaps" | Right, but vague; no estimator | Gliding-box `L(b)` with an explicit box size (§2) |
| "Adjust the step size in a way that depends on the lacunarity" | Which field? Over what space? | Four named fields, each with a space and a box (§2, §5) |
| `Lacunarity(t)` "as a function of local gradient variance" | Lacunarity needs a mass field and a scale; gradient variance over parameters has neither until you choose a partition | Field = per-token NLL, or per-block gradient mass, with fixed boxes |
| `α(t) = α₀(1 + λ·L(t))` | Unbounded (L can be 50+), unitless, no stability, no baseline identity | `α(t) = α_base(t)·clip(exp(λ·(L̃ − L̃_slow)), 1/g, g)` with `L̃ ∈ [0,1]`, ramp-in, `λ=0 ⇒ α = α_base` exactly (§6) |
| "Speeds up in sparse regions, slows in dense" | Sign is asserted, not argued; under Adam a global factor is just LR | Sign is a preregistered question; per-block variant is where redistribution can happen |
| "This equation becomes a predictive factor, guiding the model along an optimal path" | Overclaim; no path optimality is established by a heuristic schedule | Treated as a bounded controller with stated invariants and a null control |
| "Universal equation" | No universal constant; `L` is scale-dependent | Nothing universal is claimed; boxes and bounds are frozen per experiment |

---

## 5. Four roles for lacunarity in CTT, ordered by expected value

**R1 — Instrumentation (free; do this first).** Log the error-field lacunarity during ordinary training. No control
action. Deliverable: a curve `L_loss(b, t)` per run at boxes 4, 16, 64, every 100 steps, plus the normalised
`L̃`. Purpose: establish whether the field is uniform by epoch 3 (predicted, §1) and give future arms a cheap
diagnostic. Cost: `O(B·T)` per logged step; no extra forward pass (the per-token NLL is already computed).
Prediction to test: `L_loss(16)` ≤ 1.15 by epoch 3 and within 0.02 of 1.0 by epoch 7 on an A4-shaped run.

**R2 — Per-block trust scaling (cheap pilot).** Compute each named block's own gradient-mass lacunarity and apply a
bounded per-block multiplier. Blocks: English-embedding rows, CAS-token rows (341 vectors), `copy_w`, `gate`,
encoder stack, decoder stack, output bias. Prior: blocks whose gradient mass is concentrated in a few coordinates
get a *damped* step (`m_b < 1`); diffuse blocks keep the base step. This is LAMB-shaped but the statistic is
clustering, not the norm ratio. Prediction: the copy head and CAS-token rows are the blocks with the highest
lacunarity early, and damping them reduces validation loss or raises exact match by ≥ 3 licensed sentences. If
neither, abandon.

**R3 — Batch composition (data-side).** Batch lacunarity over target-token classes, controlled by rejection sampling
against a frozen band. Note a trap: the loader already sorts by length inside chunks of `50 × batch`, so
*length* lacunarity within a batch is artificially compressed — this variant must use token-class lacunarity, not
lengths. Changes data order, so it needs its own RNG stream and its own arm. Not recommended before R1/R2 report.

**R4 — Global step-size modulation (the draft's idea, repaired).** Bounded, normalised, ramped, with a `λ=0`
identity. Expected effect on the exam: **≈ 0**, because training is converged and the bottleneck is the decision
rule. Its value is to close the question with a measured null, not to find a gain.

---

## 6. The control law (exact, with invariants)

Base schedule — identical to `ctt_train/train.py` (`lr_at`), so the controlled run starts from the frozen one:

```
warm = min(warmup_steps, max(1, total_steps // 10))
base(t) = base_lr · (t+1)/warm                                   if t < warm
        = base_lr · 0.5 · (1 + cos(π · (t−warm)/(total_steps−warm)))   otherwise
```

Modulation:

```
L̃(t)      = clip((L(t) − 1) / (L_ref − 1), 0, 1)      # L_ref frozen per experiment, > 1
d(t)      = L̃(t) − L̃_slow(t)                          # L̃_slow: EMA, half-life 500 steps
λ_eff(t)  = λ · min(1, t / warmup_steps)               # zero during warmup, full after
m(t)      = clip(exp(λ_eff(t) · d(t)), 1/g, g)         # g = 2.0 global, 1.5 per block
lr(t)     = base(t) · m(t)
```

**Invariants** (all covered by the tests):
1. `λ = 0 ⇒ m(t) = 1` exactly, so `lr(t) = base(t)` for every step.
2. `m(t) ∈ [1/g, g]` always; no step can exceed the base by more than the stated factor.
3. During warmup `m(t) = 1`: the ramp cannot fight the warmup.
4. The cosine envelope keeps its endpoints; `lr(total) = 0` regardless of `m`.
5. No RNG is introduced, so the seed-to-run mapping is unchanged.

**Why a global multiplier is weak under Adam.** Adam's update is `−lr · m̂/(√v̂ + ε)` per coordinate. A scalar `m(t)`
multiplies every coordinate equally, which is algebraically an LR change — it cannot move effort from saturated
coordinates to the few that carry error. Redistribution requires the factor to differ across coordinates or blocks.
That is R2; R4 is only a thermostat on the whole run.

**Stability.** For a locally quadratic loss with curvature `H`, a step is stable when `lr · λ_max(H) < 2`. The clip
bounds the worst case at `g × base_lr`, and the base schedule already decays to zero; the existing non-finite-loss
abort stays in force. The controller adds no new state to the optimiser and cannot change the parameter count or the
checkpoint format.

---

## 7. Implementation spec (an amendment, not an edit to frozen code)

Where it would go, if approved:
- `ctt_train/train.py`, inside the batch loop, after `loss.backward()` and before `clip_grad_norm_`:
  compute per-block gradient norms; compute the block field and its `L`; update the slow EMA; set the multiplier.
- Per-token NLL for R1: call `F.nll_loss(..., reduction="none")` on the `[B,T]` logits, mask `PAD`, and compute
  `L_loss` at the three frozen boxes every 100 steps.
- New artefact: `runs/<seed>/lacunarity.jsonl`, one object per 100 steps: `{step, boxes:{4,16,64}, l_norm,
  multiplier, block_multipliers, block_norms}`. The frozen `progress.jsonl` schema is untouched, so the existing
  readers keep working.
- Config: `{"lacunarity": {"enabled": false, "weight": 0.0, "bound": 2.0, "boxes": [4,16,64],
  "l_ref": null, "ema_half_life": 500}}` in the amendment's config block, defaulting to disabled.
- Determinism: the estimator is deterministic; the slow EMA is per-run state initialised on the first logged step.
- Cost: the estimator is a sliding-window pass in pure Python over ≤ 32,768 floats per step (≈ ms); measured step
  time in c45 was 770.7 s / 10,668 ≈ **72 ms**, so the overhead is under 1% at every 100th step.

Reference implementation: `lacunarity.py`. Tests: `test_lacunarity.py` (`14 passed`).

---

## 8. Experiment draft (for the owner's approval; nothing runs on this note)

Order matters. Each step gates the next.

**E1 — instrumentation only (free, no behaviour change).** Add R1 logging to the next ordinary A4 run. Verify the
loss trajectory is bit-identical to a no-logging rerun at the same seed for 100 steps. Read `L_loss(16)` at epochs
1, 3, 7. Gate: if `L_loss(16) ≤ 1.05` at epoch 3, the dynamic field is already uniform and R2/R4 lose their
motivation — stop and write that down. If `L_loss` stays high while validation falls, the tail is where learning
happens: R2 becomes worth a pilot.

**E2 — R4 null control (3 seeds, ≈ 0.6 USD at c45 prices).** A4 shapes, `λ = 1`, `g = 2`, boxes `{4,16,64}`,
`L_ref` frozen from E1's epoch-7 median. Preregistered prediction: primary exam right count within 105–107 (the
c45 A4 spread), train loss ≤ 1e-4, validation within ±0.001 of 0.00815. Word expected: `NO_GAIN`. The experiment's
value is the measured null, not a hoped-for lift.

**E3 — R2 per-block damping (3 seeds, ≈ 0.6 USD).** `λ = 0.5`, `g = 1.5`, blocks as in §5. Preregistered success:
either validation loss lower by ≥ 5% at the same step budget, or primary exam exact +≥ 3 licensed sentences over
the A4 median of 106, with H-CWFW still ≤ 2. Failure of both → abandoned, recorded as a negative result.

**Budget basis.** The whole c45 run — six models, including three A4 seeds — cost **1.40 USD** of an 8.00 USD cap
(`RUN_RESULT_CTT1_C45.md`). Two arms of three seeds are therefore ≈ 1.2 USD at the same shapes and epochs. Caps,
one-attempt-plus-one-plumbing-retry and every frozen gate are inherited unchanged.

**Not to be run first:** R3 (data order) and any change to the decoder locks. Both confound the exam, and the exam
cannot see the difference (§3.3).

---

## 9. Risks and how each is handled

| Risk | Why it matters here | Handling |
|---|---|---|
| The controller is a feedback loop on its own input | A rising multiplier raises loss, which changes lacunarity | Clip, ramp-in, slow EMA, and a hard stop on non-finite loss (already in `train.py`) |
| Box-size shopping | Any result can be "found" by choosing `b` after the fact | Boxes `{4,16,64}` frozen in the amendment, before the run |
| Batch composition confound | The loader sorts by length within chunks, compressing length lacunarity | Use token classes, not lengths; state the confound in the record |
| Multiple comparisons across arms | Three arms × three seeds invites a lucky seed | Preregistered decision rule; report per-seed, never the best seed |
| The exam cannot see the change | Reader-first design gave the untrained control 106 | E1 gate first; do not spend on E2/E3 unless E1 shows a live signal |
| Optimiser changes alter the path to a memorised endpoint | Train fit is already 987/1000 | Prediction is "no exam gain"; a positive result would need a mechanism, not a lucky draw |
| Claim inflation | A schedule that "looks fractal" invites narrative | Claim-status table (§10); no word is licensed by a training curve |

---

## 10. Claim status of this note

| Statement | Status |
|---|---|
| Training converged to `1.8003862351179123e-05`; 987/1000 train rows exact | `MEASURED` (`WEIGHTS_MANIFEST.json`) |
| Validation minimum 0.00766 at epoch 7, then 0.00815 | `MEASURED` (`progress.jsonl`) |
| Corpus: 145 target tokens, top-10 mass 0.6556, entropy 4.9389 bits, L(8)=6.143 | `MEASURED` (`measure_corpus_lacunarity.py`) |
| Primary exam: translator called 103 times, 1–2 readings offered; C2 also 106 | `MEASURED` (`CTT_READING.json`) |
| The model asked because of OOD detection or a decision threshold | `NOT MEASURED` — the run records counts, not reasons |
| `L(b) = 1 + Var/E²`; `L ≥ 1`; `λ=0` reproduces the baseline exactly | `DERIVED` (and covered by tests) |
| Error-field lacunarity collapses by epoch 3 | `PROPOSED` — the first falsifiable prediction |
| Per-block damping improves validation or exam exact | `PROPOSED` — untested; the pilot decides |
| Global modulation improves the exam | `PROPOSED` — prior is no effect; E2 is a null control |
| Any gain for CTT-2 or HELM's voice | `NOT CLAIMED` |

---

## 11. References

- Mandelbrot, B. (1983). *The Fractal Geometry of Nature* — lacunarity as the gapiness that distinguishes sets of
  equal dimension.
- Allain, C., Cloitre, M. (1991). Characterizing the lacunarity of random and deterministic fractal sets.
  *Physical Review A* 44, 3552 — the allometric form `Λ(r) = (σ/μ)² + 1`.
- Plotnick, R. E., Gardner, R. H., Hargrove, W. W., Prestegaard, K., Perlmutter, M. (1996). Lacunarity analysis:
  a general technique for the analysis of spatial patterns. *Physical Review E* 53, 5461 — the gliding-box
  estimator used here.
- McCandlish, S., Kaplan, J., Amodei, D., OpenAI Dota Team (2018). An empirical model of large-batch training —
  gradient noise scale; related but not the same statistic.
- You, Y., Gitman, I., Ginsburg, B. (2017). Large batch training of convolutional networks — LARS, layer-wise trust
  ratios. You, Y. et al. (2019) — LAMB.
- Loshchilov, I., Hutter, F. (2017). Decoupled weight decay regularization — AdamW, the optimiser in the frozen run.
- Foret, P., Kleiner, A., Mobahi, H., Neyshabur, B. (2021). Sharpness-aware minimization — the object that is *not*
  lacunarity, listed to keep the two apart.

---

## Appendix A — reproduction

```
# corpus numbers (section 3.2)
python -X utf8 measure_corpus_lacunarity.py

# estimator + schedule tests (section 0)
python -X utf8 -m pytest -q test_lacunarity.py     # 14 passed in 0.08s

# sources read for section 3
.../run_c45_ctt1_20261020/a1_unpacked/c45_out/ctt_out/runs/A4-s1/WEIGHTS_MANIFEST.json
.../run_c45_ctt1_20261020/a1_unpacked/c45_out/ctt_out/runs/A4-s1/progress.jsonl
.../run_c45_ctt1_20261020/a1_unpacked/c45_out/ctt_out/data/train.jsonl
.../run_c45_ctt1_20261020/CTT_READING.json
.../run_c45_ctt1_20261020/RUN_RESULT_CTT1_C45.md
```

## Appendix B — what this note deliberately does not do

- It does not change `FROZEN_CTT.json`, `train.py`, the decoder locks, the data, the exam or the reader.
- It does not add a dashboard, a plot or a "fractal" visual metaphor.
- It does not claim that lacunarity explains learning curves. It claims only that `L(b)` is a cheap, well-defined
  statistic and that one specific use of it can be tested for a stated price.
- It does not rename or extend CAS. The words "lacunarity", "field" and "box" are plain mathematics here. No CAS
  primitive is introduced, and no Clarification is touched.
