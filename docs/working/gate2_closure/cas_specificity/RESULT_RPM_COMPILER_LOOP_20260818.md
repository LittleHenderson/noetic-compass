# RESULT — RPM/DWP → notation → compiler → detect → correct loop (2026-08-18)

**Verdict: PROVEN at the symbolic layer (ran end-to-end on real modules, exit 0) — with
named gaps.** Owner's claim under test: *"RPM's D/W/P stages can each be translated into
CAS notation, tested by the CAS compiler, and corrected or inverted on any of its axes."*
This is the Claim-B algebra half ("the ruler does real work"), NOT a weights claim.

Demo: `noetic-compass-scaffold/noetic-compass/rpm_compiler_loop_demo.py` — every call hits
real repo modules (`api.notation.compiler`, `api.notation.inversion`,
`cas-native/belief/inversion_gate.py`, Rust `cas_engine` PyO3). Nothing stubbed. `EXIT=0`.

## What ran (real calls, real output)
1. **Translate** — `compile_expression('RPM(F5)')` → `valid=True`, emits the chain
   `["A0 -> D5", "D5 -> W5", "W5 -> P5"]`. The D/W/P stages as drive-tagged state
   literals all compile: `^2^C_{F5}` (D5, dominant C2), `^6^E_{F5}` (W5, E6),
   `^9^O_{F5}` (P5, O9). Descent as two binary transitions, both `valid=True`,
   `descent_ok=True`.
2. **Inject + detect, axis A** (RPM-chain violation, numeric plane) —
   `cas_engine.InversionScanner().scan(...)` with F5 pathway scores broken to
   `[0.20, 0.10, 0.10, 0.90]` (P towers over unsatisfied A0/D/W): axis-A resistance
   drops `1.0000 → 0.8571` (severity exactly 1/7). **The scanner names the axis.**
   Belief gate cross-check: `axis_a_check → clean=False`.
3. **Correct, axis A** — restore well-ordered scores `[0.85, 0.80, 0.75, 0.90]` →
   resistance back to `1.0000`. (Manual re-scoring; see gaps.)
4. **Inject + detect + correct, axis N** (involution, symbolic plane) —
   `invert_expression('^2^P_{F5}', 'N') → '^3^P_{F5}'`; detector flags
   `flagged_pairs=[(2, 3)]`, `N.clean=False`; invert back → restores original,
   recompiles `valid=True`. **Full symbolic round trip.**

## Honest gaps (each disclosed in the script)
- **"Any of its axes" is 4/7 at string level.** `IMPLEMENTED_AXES=('N','W','F','P')`;
  `DEFERRED_AXES=('E','S','A')` raise `DeferredAxisError`. Axis A inject/detect/correct
  was done on the NUMERIC plane (pathway-score arrays), not by a string corrector.
- **No auto-repair dispatcher.** The scanner names which axis fired, but no code yet takes
  "axis A fired" → produces the corrected object automatically; correction was applied by
  the caller.
- **Pathway node tokens `A0/D5/W5/P5` are not lexable inputs** — stages are carried by
  `RPM(F5)` (which emits the chain as output) + drive-tagged literals.
- **Arrows are strictly binary** — `A -> B -> C` is rejected by typecheck (matches the
  known grammar rule); descent must be split into binary transitions.
- **`completeness: 1.0` in `RPM(F5)` is hardcoded** — the compiler type-checks form; real
  prerequisite satisfaction lives in the Rust RPM engine (`rpm/recursive.rs`, exercised
  only by its own Rust tests here).

## Claim-state separation
- **Real:** compiler + inversion detect/correct calls all executed on real modules; the
  injected axis was the detected axis in both tested cases (A numeric, N symbolic).
- **Open:** string-level correctors for E/S/A; an auto axis→repair dispatcher; wiring the
  corrected notation into the steering levers (ε-prefix black-box / drive-local eraser
  white-box) as one welded machine.
- **Not claimed:** anything about 20B weights/geometry. This is a notation+rule-checker
  result — the compiler accepting and correcting notation says nothing about whether a
  transformer internally represents CAS (that is the separate, still-negative
  CAS-specificity track).

## Why this matters for the reframe
Claim B ("CAS is a measurement + correction language") requires the algebra to do real
work — not just relabel. This demo shows: translation compiles, violations are detected
ON THE NAMED AXIS, and inversion is a mechanical, reversible operation. Combined with the
validated steering levers (ε-realization to 20B +1.412; drive-local eraser +0.84 p<1e-14)
and the behavioral proxy loop (targeted 7.19 > generic 4.59), every link of
diagnose→localize→correct→steer now has a live demonstration — the remaining build is the
weld, not the links.
