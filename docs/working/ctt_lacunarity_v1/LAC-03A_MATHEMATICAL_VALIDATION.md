# LAC-03A — Mathematical validation (Workstream 3), 2026-10-24

Status: **implementation correctness for the tested formulas.** This does not establish predictive or intervention
value. All tests are free, local, and deterministic. The research scorecard is `LAC-03_RESEARCH_SCORECARD.md`.

## 1. What was tested

Two test files, 30 checks total:

- `test_cas_metrics.py` (16 checks) — the existing CAS mirror `api/pipeline/lacunarity.py`, against values computed by
  hand from its own docstrings.
- `test_lacunarity_families.py` (14 checks) — the two new PROPOSED measures, `recipe_fragility` (R-2) and
  `rpm_fragility` (P-2), on synthetic structures with hand-derived answers.

Run command: the cas-gpu Python has no pytest, so the tests were executed by a small runner that imports each module
and calls every `test_*` function.

## 2. Result

**30 checks, 0 failures** after correction.

| Family | Checks | What they cover |
|---|---|---|
| State lacunarity | 5 | uniform = 0, hand value 2.28 for `[9,1,0,0]`, zero-vector guard, scale invariance, relabel invariance |
| Fractal coverage | 3 | full coverage = 0, half = 0.5, empty = 1.0 |
| Domain coverage | 3 | all active = 0, one active = 0.75, threshold is strict (`0.2` is inactive) |
| Drive coverage | 2 | all seven = 0, one = 6/7 |
| RPM resolution | 2 | four mechanisms = 0, one = 0.75 |
| Negative controls | 1 | uniform fields never trigger any coverage measure |
| Recipe fragility | 7 | single ingredient = 1.0, substitutes split the loss, AND groups = 1.0, zero state = 1.0 |
| RPM chain fragility | 6 | chain of four = 0.6111, star = 1.0, empty = 0.0, two nodes = 1.0, cycle = 0.5, two chains = 1.0 |

## 3. Failures found before the pass

Four checks failed on the first run; all four were resolved, and the split matters:

| Check | Cause | Fix |
|---|---|---|
| RPM cycle | **Real bug in my implementation**: a cycle counted its own start node as downstream, inflating reach | `_downstream` now subtracts the start set |
| Recipe two-substitute | **My arithmetic was wrong** in the test: removing the larger substitute leaves the smaller, not both at 2/3 | expected value corrected to 1/6 |
| RPM four mechanisms | **My test guessed the input shape** (`{"mechanism": ...}`) | corrected to the real shape, `{"resolutions": [{"mechanism": ...}]}` |
| RPM one mechanism | same | same |

The third and fourth are exactly the failure the directive warns about: a test that looks like it checks the code but
actually checks the tester's assumption. They are recorded rather than quietly fixed.

## 4. What this establishes, and what it does not

**Establishes:** the Python mirror computes what its docstring says on the tested inputs; the two new measures compute
what LAC-02 defines on synthetic structures; the negative controls behave.

**Does not establish:** that `lacunarity.rs` (Rust) agrees with the Python mirror — that needs `cargo test` and a
shared vector, which is a separate check; that any value is predictive of failure; that either new measure is useful.

## 5. Known limits recorded, not hidden

- State lacunarity is scale-invariant but **not** duplication-invariant: repeating a value changes it. That is a
  property of `Var/Mean²`, not a bug, but it must be stated before comparing vectors of different lengths.
- Coverage measures are bounded ratios with a hard threshold; a value at exactly the threshold flips the count.
- `recipe_fragility` assumes one unit per alternative; weighted quantities are not yet supported.
- `rpm_fragility` counts nodes, not weighted paths; a long chain and a short chain with the same count score alike.
- The Rust and Python implementations are duplicated; neither has a test that they agree.

## 6. Artifacts

- `lacunarity_families.py`, `test_lacunarity_families.py`, `test_cas_metrics.py` in this directory.
- 30/30 pass, 2026-10-24, local, 0 USD.
