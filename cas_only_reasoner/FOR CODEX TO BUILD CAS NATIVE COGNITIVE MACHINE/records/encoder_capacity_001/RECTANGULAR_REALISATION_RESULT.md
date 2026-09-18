# RECTANGULAR_REALISATION_RESULT — the fitted-readout gain does not survive the registered readout

**Round 36. The rectangular solve is built and tested; the measurement it enables closes a route.**
**$0.00. Pure Python, standard library plus the project's pure modules. No torch, no GPU, no model,
no training, no new run.**

Code: `cncm/analytic_decompose.decompose_from_free_readout_rectangular` (new).
Tests: `tests/test_analytic_decompose_rectangular.py` (13 new; **189 passed** with the existing
module tests).
Measurement: `records/encoder_capacity_001/measure_rectangular_realisation.py`,
`rectangular_realisation.txt`.

---

## 1. The engineering step that was owed

`decompose_from_free_readout` builds `^6` parameters with `T = R⁻¹Wᵀ` so the frozen readout `R`
behaves as a chosen free readout `W`. It **requires `nclass == core_width`**, and the registered
readout is **`[90, 64]`** — so it refuses the real readout, and every analytic measurement since has
had to work on a 64-row submatrix.

Round 36 added the rectangular construction:

```
T = (RᵀR)⁻¹ Rᵀ Wᵀ          minimum-norm least squares
```

It **cannot** realise every `W`. `R T` always lands in the column space of `R`, which has dimension at
most `core_width`, so the construction realises the **orthogonal projection** of `Wᵀ` onto that space —
and it **reports the residual**, which is the honest statement of what the frozen readout costs.

Thirteen tests defend it: registered shapes; `forward(x) = T·tanh(x)`; refusal when the readout is
narrower than the core, has too few rows, or has mismatched class count, or is singular; **numerical
agreement with the square construction when `nclass == D`**; exactness when `Wᵀ = R·B` (the reachable
case); and — the test that matters — that in the unreachable case `R T` lies in the column space and
`Wᵀ − R T` is **orthogonal to every column of `R`**, with the reported residual equal to the largest
entry of that leftover.

## 2. The measurement, and it is a negative

Round 30 fitted a free readout `W` on `tanh(encoded)` and scored it through the project's own
`score_decisions` and `assemble_answer`: the many-decision half went **5.0167% → 12.0401%**, and
`definition` reached 48.5714%. **That was a substituted readout, not the machine's**, and the open
question was whether it could be installed through the registered path.

Now measured, five folds by question, 299 many-decision questions, real `[90, 64]` readout:

```
fold 0: residual 0.1475689756   exact False
fold 1: residual 0.1440038168   exact False
fold 2: residual 0.1442578014   exact False
fold 3: residual 0.1850843724   exact False
fold 4: residual 0.1716314452   exact False
```

| kind | q | recorded | direct `W` | **through `T`** | `T` − direct |
|---|---|---|---|---|---|
| `edge_account` | 70 | 0.0000% | 1.4286% | **0.0000%** | −1.4286% |
| `role_set` | 36 | 8.3333% | 8.3333% | **11.1111%** | +2.7778% |
| `parts` | 53 | 22.6415% | 3.7736% | **3.7736%** | +0.0000% |
| `context` | 70 | 0.0000% | 4.2857% | **0.0000%** | −4.2857% |
| `definition` | 70 | 0.0000% | **48.5714%** | **8.5714%** | **−40.0000%** |
| **MANY DECISIONS** | **299** | **5.0167%** (15) | **14.3813%** (43) | **4.0134%** (12) | **−10.3679%** |

**The construction routes the readout through the registered block and lands at 4.0134% — below the
run's own 5.0167%.** The residual is 0.1440–0.1851 and is **never exactly zero**, in any fold. The
fitted readout's transpose does not lie in the frozen readout's column space, and the projection loses
**10.3679 of the 14.3813 points** — `definition` alone loses 40.0000.

## 3. What this closes, and it is worth having

**Round 30's fitted-readout gain is an idealisation that cannot be installed through the registered
frozen readout.** Not "not yet measured" — measured, and it does not survive. **`Fix A` cannot improve
the many-decision half by this route**, and no GPU run should be spent trying.

It also explains something that looked like an arbitrary restriction: `decompose_from_free_readout`'s
square requirement is not arbitrary. When `R` is square and invertible, `R·T = Wᵀ` is **exactly**
satisfiable and `Fix A`'s 62.94%/62.06% on focus identification is real. With 90 rows and 64 columns
only the projection is reachable, and **the projection is where the gain dies.**

**And it is consistent with everything measured before it.** Round 29 found the packet inert per slot
in the pre-block decision; round 30 found a fitted readout could exploit the slot's *name*; this round
finds that the *name*-derived fit cannot be expressed through the frozen readout either. **Three
independent measurements now point at the same component: the frozen readout, not the block and not
the composer.**

## 4. Where the remaining levers are

| lever | status |
|---|---|
| **the declared-constraint layer** | **mined.** +36.83 questions per run truth-free, rounds 32–35. Round 35 bounded the "declared by absence" class at eight cells. |
| **installing a fitted readout through the frozen readout** | **closed this round.** 14.3813% → 4.0134%, below the machine's own 5.0167%. |
| **the readout itself** | **untouched and now the named obstacle.** Either it is unfrozen, or the encoder's binding is changed so the frozen readout sees what it needs. Both are architecture changes, both need owner authority, and neither is measured. |

**Round 35's conclusion was that the constraint layer is now as good as the readout underneath it.
Round 36 has removed the one remaining way of improving that readout without changing it.** The next
step is not a measurement; it is a decision about what may be changed.

## 5. Claim status

- **REAL:** the construction and its thirteen tests. `tests/test_analytic_decompose_rectangular.py`,
  189 tests passing with the existing module tests, no tested module's existing behaviour changed.
- **REAL:** §2's residuals and score table, from recorded artifacts and the checksum-gated frozen
  bytes (gate: `readout 14da2c58…c667`, `projection 4481b1d2…fdd9`, both MATCH).
- **WITHDRAWN:** round 30's fitted-readout gains as a *score* prospect. 12.0401% and 16.0535% are
  idealised figures; the installable figure is **4.0134%**.
- **NOT LICENSED:** that unfreezing or replacing the readout helps. Untested, and a different change.
- **FLAG_FOR_HUMAN_REVIEW:** the decision this round lands on. The measured components are exhausted;
  what remains is a change to a frozen component, which this record does not authorise.
