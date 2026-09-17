# The registered `^6` module can reach the closed-form solution exactly

**Record:** `records/encoder_capacity_001/`
**Script:** `measure_reachable_solution.py` (pure standard library; no torch, no device,
no network, no wall-clock input)
**Raw output:** `reachable_solution.txt`
**Spend:** $0.00. No model was executed. No GPU was touched.

---

## The question this answers

This record had already measured that the actual encoded slot the learner receives
decodes the focus world at **63.65%** by closed-form ridge with a *free* readout, while
the trained learner, whose readout is *frozen*, reaches **1.24%**.

Those are not the same task, so the contrast was not yet decisive. The learner's forward
pass is

    logits = readout_rows[alias_indexes] @ vector,    vector = ^6(slot)

with `readout_rows` frozen at build time. A free readout is 4,096 free numbers; a frozen
one is 64 fixed directions. The open question was therefore whether the frozen readout, or
the registered module's shape, blocks the solution.

Two facts decide it. Both are now checked numerically rather than argued.

---

## Fact 1 — the frozen readout imposes no constraint at all

The score the learner computes for class `c` is

    r_c · (T φ)  =  (Tᵀ r_c) · φ

where `r_c` is the frozen readout row for world alias `Wc`, `T` is whatever linear map the
`^6` block implements, and `φ` is the block's input.

Write `W` for the free-readout weight matrix, column `c` equal to `W_c`. The construction
needs `Tᵀ r_c = W_c` for every `c`, which is

    Tᵀ = W (Rᵀ)⁻¹

with `R` the 64 × 64 matrix whose row `c` is `r_c`. That inverse exists exactly when the
readout rows are linearly independent — which must be measured, not assumed.

**Measured.**

| quantity | value |
|---|---|
| registered readout rows | 90 |
| world-alias symbols among them | 65 (`W0` … `W64`) |
| L2 norm of every readout row | min 1.000000000, max 1.000000000 |
| linear independence | **INDEPENDENT** |
| max &#124;Rᵀ R⁻ᵀ − I&#124; | **2.798e-14** |

Each readout row is 64 entries of ±0.125, so every row has L2 norm exactly 1 — the codebook
is already unit-normalised, which is why the earlier vertex measurement found all 65 symbols
selectable. They are pseudo-random and independent, so `(Rᵀ)⁻¹` exists and the construction
is available.

**Consequence.** Whenever the alias rows span R⁶⁴, the frozen readout is not a bottleneck
of any kind: every linear classifier a free readout could express is realisable through the
frozen one, with `Tᵀ = W (Rᵀ)⁻¹`.

---

## Fact 2 — the registered `^6` module contains that linear map exactly

`cas_cjt.neural._DecomposeTransform` (the registered `^6` decompose module) is

```python
self.left  = nn.Linear(64,  64, bias=False)
self.right = nn.Linear(64,  64, bias=False)
self.merge = nn.Linear(128, 64, bias=False)

def forward(self, value):
    parts = torch.cat((torch.tanh(self.left(value)),
                       torch.tanh(self.right(value))), dim=-1)
    return self.merge(parts)
```

Set

    left  = I₆₄        (64 × 64 identity)
    right = 0          (64 × 64 zeros)
    merge = [T | 0]    (64 × 128: left half T, right half 0)

Then for any input `x`,

    ^6(x) = [T | 0] @ [ tanh(I x) ; tanh(0 x) ] = [T | 0] @ [ tanh(x) ; 0 ] = T @ tanh(x)

**exactly.** No approximation, no residual term, no extra parameters, no change to the
registered parameter list (`left.weight`, `merge.weight`, `right.weight`), no change to the
registered shapes, no change to the frozen encoder, no change to the frozen readout, and no
change to the registered `max_updates` ceiling.

The reachable function class is therefore `{ x ↦ T · tanh(x) }`.

---

## What that class actually achieves

Measured on the 564 cached packets, at the **real encoded slot** the learner receives
(`normalize((packet_vector + slot_query_row) / √2)`, i.e. what `encoder.encode_slot` line
212 hands over), 5-fold cross-validated, target = focus world alias:

| reachable class | dims | 5-fold CV | vs 1/64 | vs strongest null |
|---|---:|---:|---:|---:|
| free readout on the encoded slot `x` | 64 | **63.65%** | 40.7× | 13.81× |
| free readout on `tanh(x)` — what `^6` can build | 64 | **63.83%** | 40.9× | 13.85× |
| through the **frozen readout rows** (`T`, then `R`) | 64 | **63.83%** | 40.9× | 13.85× |
| held-out rows where the frozen and free argmaxes agree | — | **100.00%** | — | — |

Supporting measurements:

- encoded slot L2 norm: min 1.000000, max 1.000000
- tanh distortion ‖tanh(x) − x‖ / ‖x‖: min **0.009792**, mean **0.014927**, max **0.022331**

The 1–2% distortion is what the linear-regime reading predicted: the encoder emits unit
vectors with components of order 0.125, and tanh(0.125) = 0.124352. The nonlinearity is
present but nearly transparent here.

The frozen-readout column reproducing the free-readout column exactly, to 100.00% argmax
agreement on held-out rows, is the numerical confirmation of Fact 1.

---

## Null baselines — a correction to a headline this record already published

This run also measured the class balance of the 564-row sample for the first time.

| quantity | value |
|---|---|
| rows | 564 |
| **distinct focus worlds present** | **24**, not 64 |
| per-class counts, ascending | 19, 19, 19, 19, 20, 20 … 26, 26, 26, 26 |
| uniform among the 24 worlds present | **4.1667%** |
| majority class (always answer the commonest) | **4.6099%** |
| uniform among all 64 worlds (the nominal chance) | **1.5625%** |

**This record previously reported the 63.65% figure as “40.7× chance”, using 1/64 =
1.5625%.** That multiplier is overstated, because only 24 of the 64 worlds occur in the
sample at all. Against the strongest available null — always answering the commonest world,
4.6099% — the honest multiplier is **13.81×** for the 63.65% figure and **13.85×** for the
63.83% figure.

The result is still far above every null and the conclusion does not change. The stated
multiple does, and the corrected number supersedes the earlier one wherever it appears.
This is recorded here rather than quietly amended because the earlier form is in the
committed history.

---

## The architectural reading

Put the four measurements side by side:

| | value |
|---|---|
| representation — real encoded slot, free readout | 63.65% |
| codebook — world symbols selectable | 65 / 65, min normalised margin 0.7573 |
| frozen readout — is it a constraint? | no; 100.00% argmax agreement, ‖RᵀR⁻ᵀ − I‖ = 2.798e-14 |
| registered `^6` class — can it carry the solution? | yes, exactly, at 63.83% |
| the trained learner, frozen readout, 160 updates | **1.24%** |

The representation is adequate. The codebook is adequate. The frozen readout is not a
constraint. The registered module can implement the solution **exactly, with no
approximation**. And the trained learner still reaches 1.24%, because the training stopped at
the contract ceiling of 176 updates with the loss at its global minimum and the gradient
norm still rising (companion record: `UPDATE_TRAJECTORY_RESULT.md`).

**The gap is an optimisation gap inside a function class the architecture already
contains.**

The construction that closes it is closed-form, adds no parameters, changes no registered
shape and no registered scope, and requires no GPU: fit `W` by ridge on `tanh(x)`, set
`Tᵀ = W (Rᵀ)⁻¹`, set `left = I₆₄`, `right = 0`, `merge = [T | 0]`. It is written up as
`ARCHITECTURE_CHANGE_SPEC_v0.2_ANALYTIC_DECOMPOSE_INIT.md`, which supersedes nothing:
`ARCHITECTURE_CHANGE_SPEC_v0.1.md` remains **WITHDRAWN IN FULL**.

---

## The construction is now code, and it reproduces the recorded figure exactly

Everything above was measured by `measure_reachable_solution.py` using its own local linear
algebra. That is not the code that would run in a worker, so a second check was added in the
same script: the same five folds, the same real features, driven through
`cncm/analytic_decompose.py` — the module committed as the executable form of the proposal.

| path | 5-fold CV through the frozen readout |
|---|---:|
| this script's local linear algebra | 63.83% |
| `cncm.analytic_decompose` | **63.83%** |
| max &#124;free_c − through_c&#124; over held-out rows | **2.447e-14** |

The two agree question for question. The shipped module reproduces the recorded figure
exactly, on the real 564-packet feature set, through the frozen readout rows.

Two mistakes were made while writing that module and both were caught by its own tests. They
are recorded here because both were the kind that produce a plausible wrong number rather than
a crash:

- A **row/column convention error**. `ridge_weights` returns a `d × nclass` matrix with
  **column** `c` the class-`c` weight, so the score vector is `Wᵀ φ`, not `W φ`. The first
  version used `W φ` and the score residual was **29.25** instead of 1e-14.
- A **double-tanh error**. `forward` applies `tanh` itself, so passing a feature `φ = tanh(x)`
  as the module's input applies it twice. The first version did that and reported **64.18%**
  against the recorded 63.83%, for a reason that had nothing to do with the construction.
  `realisation_agreement` and `realisation_score_residual` now take module inputs and apply
  `tanh` on the free side only, and `test_forgetting_the_tanh_breaks_the_identity` pins the
  difference so the mistake cannot be misread as a construction failure.

`cncm/analytic_decompose.py` also carries `shuffled_label_control`, the arm-C null the spec
requires, and a test asserts that a shuffled-label solve scores at most 4 of 64 on separable
data. Without that bound a good arm-A number would not be interpretable.

---

## What is NOT established here

- **This is a single-field result, not a whole-answer result.** The 63.83% is focus-world
  alias decodability, one 64-way field. The learner's 1.24% is whole-answer exact match over
  all eleven fields, which is conjunctive. **The two numbers are not the same metric and
  must never be presented as a like-for-like improvement.** What is established is
  reachability of a strong per-field solution, not that the assembled answer would score
  63.83%.
- **The sample is the learner's own registry.** The 564 packets come from the same registry
  the training run drew on. The 5-fold split is held out within that sample, so this is a
  representability result, not a generalisation result on unseen data.
- **The ridge solution is not trained.** It is a closed-form solve. Nothing here shows that
  stochastic gradient descent could find it, or that placing the block at it survives the
  registered training that follows.
- **Only 24 of 64 worlds occur in the sample.** A held-out evaluation spanning all 64 worlds
  has not been run.
- **No run is proposed or authorised by this record.** Any run that changes the
  initialisation, the loss, or `max_updates` is claim-bearing and needs an owner-signed
  phase record before launch.
