# WELD v2 — a CAS diagnose→correct loop that can actually FAIL

**Supersedes `WELD_SPEC.md` and `cas_weld_loop.py`.** Those files are left on
disk unmodified as the failure record; nothing here imports them. The v1 build
was reviewed at commit `2be60327` and found to have four fatal defects — every
one of its four success criteria was true by construction. §2 answers each one
with the specific code change and, where possible, an empirical demonstration
rather than a promise.

- Runnable loop: `docs/working/gate5_weld/cas_weld_loop_v2.py`
- Machine-readable result: `docs/working/gate5_weld/weld_v2_run_report.json`
  (`schema: cas_weld_loop.v2`)
- Captured stdout: `docs/working/gate5_weld/weld_v2_run_stdout.txt`

---

## 0. Headline, stated before anything else

**Scope: ONE axis — `A` (Pathway / RPM prerequisite chain) — on the NUMERIC
plane. Nothing else.** That is the single detection the review found genuine:
given only a perturbed 7×4 pathway array with no axis hint,
`cas_engine.InversionScanner` returns `fired_axes=['A']` and only `A`
(resistance `0.857143` = 6/7). Axes N, W, F, E, S and P are **out of scope**,
stated in the disclosures at runtime, not quietly dropped.

**Two scored criteria, one unscored gate.** Six cases. **Three of them are
designed to fail and do.** The loop's status vocabulary is
`LOOP_FALSIFIABLE_AND_HELD` (every case matched its preregistration) or
`PREREGISTRATION_VIOLATED` (exit 1). The tamper check in §6 demonstrates
`PREREGISTRATION_VIOLATED` is reachable.

**No model is loaded. No efficacy claim is made or implied.** This measures
mechanism only.

**What was DELETED rather than repaired.** v1's criteria (c) prefix-distinctness,
(d1) wrong-axis prefix control and (d2) label-space identifiability sweep are
gone. They lived on the epsilon-realizer joint, the numeric plane has no epsilon
realizer, and the review showed the realizers are lossy projections that cannot
separate corrections agreeing on the projected coordinate. Per design rule C, an
unfalsifiable criterion is deleted, not shipped. The loop's **reach is smaller
than v1's** as a direct result: v1 claimed a path from model output text to a
likelihood shift; v2 claims a path from a numeric pathway array to a cleared
axis, and nothing else. That is a deliberate trade of scope for falsifiability.

---

## 1. The loop

```
STAGE 1  INJECT    clean object + seeded RNG        -> perturbed object (+ SEALED fault record)
STAGE 2  GATE      perturbed object ALONE           -> the fired axis set          [BLIND]
STAGE 3  LOCALIZE  perturbed object ALONE           -> the exact broken chain set  [BLIND]
STAGE 4  REPAIR    perturbed object + LOCALIZED set -> repaired object             [CHAINED]
STAGE 5  VERIFY    repaired object ALONE            -> the fired axis set          [BLIND]
CONTROLS           exhaustive + random same-size subset interventions
```

### Per-stage contract

| Stage | Consumes | Produces | Real module |
|---|---|---|---|
| 1 INJECT | clean object, seeded `random.Random` | perturbed object; a `FaultRecord` **sealed** from every stage below | — (Python arithmetic) |
| 2 GATE | **the perturbed object alone** | the fired axis set, read off the scanner's own `axis_scores` | `cas_engine.InversionScanner.scan` |
| 3 LOCALIZE | **the perturbed object alone** | the exact set of violated chain indices | `cas_engine.InversionScanner.scan` (8 calls, leave-one-out) |
| 4 REPAIR | the perturbed object + `localization.indices` | repaired object | `cas_engine.InversionScanner.scan` (per-chain violation query) + a constraint solver |
| 5 VERIFY | **the repaired object alone** | the fired axis set | `cas_engine.InversionScanner.scan` |
| CONTROL | the perturbed object | chance rate of a random same-size intervention | `cas_engine.InversionScanner.scan` |

**The object.** A frozen `AssessmentObject` carrying all seven planes the Rust
scanner consumes: 10 operator scores, 4 domain averages, 7 drive scores, a
40-dimensional state vector on the open simplex (CLAUDE.md Correction 4), a 7×4
sub-drive matrix, and the 7×4 pathway array `[A0, D, W, P]` per drive chain.
Every transform returns a **new** object, so no stage can mutate an object
another stage holds. Each object's sha256 is in the report.

**The detection rule is never reimplemented.** Every "is this violated?"
question in the file — including the corrector's own per-chain check — is
answered by calling the Rust scanner. Two constants (`SEVERITY_THRESHOLD=0.05`,
`SATISFACTION_FLOOR=0.5`) are mirrored from the Rust source for reporting and as
the repair's arithmetic target; that mirroring is disclosed at runtime. If the
mirrors drifted, the loop's verdicts would still be the scanner's.

---

## 2. The four fatals, and what changed

### FATAL 1 — the matched control was an algebraic identity

*v1:* the pool `[c for c in ALL_40E if c != true_cell]` **excluded** the true
cell, and all 40 cells produce distinct prefixes, so `epsilon_match_count == 0`
was a theorem. The stated null `0.0256` was false; the real null was exactly 0.

*v2:* the control is an **exhaustive sweep of all C(7,k) same-size
interventions, with the localized subset IN the pool.** The reported chance rate
is `n_clearing / C(7,k)` — a count, not an assertion — and the positive control
(does the localized subset actually clear?) is **observed and reported**, and in
NEG-3 it comes out **False**. A random pick **can** succeed: 1 time in 7 for a
single-chain fault. The derivation is printed with the number. An independent
empirical control draws 2000 seeded random subsets and measures the rate; §5
reports the agreement.

### FATAL 2 — the axis-N detector was handed the answer

*v1:* the loop scanned `f"{clean_expr} {inj.inverted}"` — the concatenation of
the clean and perturbed expressions. Scanning the perturbed object alone
returned `clean=True, fired=[]`.

*v2:* **there is no concatenation anywhere in the file.** `diagnose_blind` takes
exactly one parameter, and that is asserted mechanically at startup via
`inspect.signature`:

```
diagnose_blind_parameters: ['obj']
localize_blind_parameters: ['obj']
repair_parameters: ['obj', 'targets']
```

A function with no parameter for the axis, the clean object or the fault record
**cannot be handed any of them**. This is a structural guarantee, not a
convention.

### FATAL 3 — the axis-W name was hardcoded from the injection parameter

*v1:* `detected_axis = axis`, so criterion (a) evaluated `axis == axis`.

*v2:* **no function in this file receives an axis name.** The fired axis set is
read off `axis_scores` returned by the scanner, thresholded at the scanner's own
`severity_threshold`. The injected axis is never a parameter to anything.

### FATAL 4 — the pipeline was not chained; (b) was an involution identity

*v1:* the corrector received the ground-truth axis, and the corrector **was** the
injector (`invert_expression` both ways), so `f(f(x)) == x` was a theorem.

*v2, chaining:* `repair(obj, targets)` is called with `targets` bound by an `is`
identity check to `localization.indices`, verified at the call site and recorded
in the report. **And this is demonstrated empirically, not asserted** — see the
tamper check in §6, which reproduces fatal 4 on purpose and shows the reported
outcome flips.

*v2, no involution:* the injector overwrites one upstream stage with a seeded
draw from `U(0.05, 0.45)`, destroying the original value. The corrector is a
**constraint solver** that never learns that value: walking each target chain
backwards, any stage below the satisfaction floor is lifted to clear the floor
**and** to dominate every stage downstream of it (the RPM section-retraction
ordering, CLAUDE.md Correction 2). It synthesises a satisfying assignment, it
does not invert anything. `repaired == pre-injection original` is therefore
**measured every run and comes out False**, with the L1 distance reported
(0.10 for POS-1, 0.20 for POS-2, 2.25 for NEG-3). If anyone later replaced the
corrector with an inverse of the injector, this check would catch it.

---

## 3. Blindness and chain invariants — mechanical, not promised

Asserted at startup and printed; all appear in `report.invariants`.

| Invariant | How it is enforced | Observed |
|---|---|---|
| The detector sees only the object | `inspect.signature(diagnose_blind).parameters == ['obj']` | `['obj']` |
| The localizer sees only the object | `inspect.signature(localize_blind).parameters == ['obj']` | `['obj']` |
| The corrector takes only the object and the detected targets | `inspect.signature(repair).parameters == ['obj','targets']` | `['obj','targets']` |
| The corrector's input **is** the localizer's output | `assert targets is loc.indices` at the call site | `True`, all cases |
| The neutral object is genuinely clean | scanner verdict, not authorial claim | `fired_axes = []`, all seven severities `0.0` |
| The probe chain used for substitution is genuinely clean | scanner verdict | axis-A severity `0.0` |
| The severity quantum is one broken chain in seven | scanner verdict | `0.142857143`, `= 1/7` to 1e-9 |

**Ground truth is read in exactly one place** — the scoring of criterion 1 —
through `FaultRecord.read_broken_chains(why)`, which logs every read into
`report.cases[*].ground_truth_reads`. An unreported read would be visible. It is
never read by the gate, the localizer, the corrector or the controls. Criterion
2 needs no ground truth at all: the detector decides it.

---

## 4. The criteria

### GATE — a precondition, deliberately NOT scored as identification

> A blind scan of the perturbed object alone fires axis `A`.

**How it fails, and does:** NEG-1 injects a real prerequisite inversion — `A0`
lowered to 0.55 while `D` stays at 0.80 — that the detector is structurally
unable to see, because `detect_pathway_inversion` opens its guard only when the
earlier stage falls **below 0.5**. The scanner reports clean, the chain
**stops**, and criteria 1 and 2 are recorded as `null` (not evaluated), not as
passes. NEG-2 injects nothing and produces the same stop.

**Chance null: NONE, and none is claimed.** This is stated plainly rather than
dressed up. The seven axis detectors in `cas-engine/src/inversions/mod.rs` read
**disjoint slices** of the input — `detect_pathway_inversion` reads
`pathway_scores` and nothing else — so perturbing the pathway plane can only
move axis A. "The right axis fires, and only it" is **analytically entailed**
once the threshold is crossed. A discrimination control across planes would have
a chance rate of exactly 0, which is the Fatal-1 pattern, so it is not shipped.
What the gate genuinely tests is **threshold crossing**, which is a real
property of the fault and which NEG-1 fails.

### CRITERION 1 — LOCALIZATION

> The blind leave-one-out procedure names the **exact** set of violated chains.

The scanner's only axis-A output is a **scalar** (`violated_chains / 7`). It
never says *which* chain. The procedure substitutes each chain in turn with the
detector-certified clean chain, re-scans, and keeps the indices whose
substitution lowers severity. Input is the perturbed object and nothing else.

**Chance null: 1/C(7,k).** Derivation in §5. Measured exhaustively **and**
empirically.

**How it fails, and does:** NEG-3 runs the identical object and the identical
corrector through a **different, real localizer** — "the broken chain is the one
with the weakest stage", the heuristic almost anyone would write first. It is
wrong, because the detector flags a chain only when an *unsatisfied* stage is
*dominated by a later one*; a uniformly weak but monotonically descending chain
is perfectly clean. NEG-3's object contains exactly that decoy. The naive
localizer names chain 3 (min 0.20, clean); the truth is chain 5 (min 0.30,
violated). Criterion 1 returns **False**.

### CRITERION 2 — CORRECTION VIA THE DETECTED SET

> The solver, driven by the **localized** set (`is`-checked, never ground truth),
> clears axis `A` under a fresh blind scan; **and** the repaired object differs
> from the pre-injection original; **and** the exhaustive same-size control is
> identifying (exactly one intervention clears).

**Chance null: 1/C(7,k)**, the same control.

**How it fails, and does:** NEG-3's mislocalization propagates. The corrector
repairs the clean decoy chain — a no-op, because the corrector is idempotent on
chains the detector calls clean — and VERIFY still reports `fired=['A']` at
severity 0.142857. Criterion 2 returns **False**, the exhaustive control's
positive-control field returns **False**, and the case verdict is `FAIL`.

**A criterion that was considered and dropped:** "the corrector restores the
original array." It cannot be required, because the corrector is a solver that
does not know the original. Requiring it would have forced the corrector to be
the injector's inverse, which is exactly fatal 4.

---

## 5. The control — and its true chance rate, derived

**Construction.** For a fault the localizer resolves to `k` chains, enumerate
**all** `C(7,k)` size-`k` subsets of the seven RPM chains — the localized subset
among them — apply `repair` to each, re-scan, and count how many clear axis `A`.

**Derivation of the null.** There are exactly `C(7,k)` same-size interventions.
A uniformly random pick lands on any one of them with probability `1/C(7,k)`. If
`m` of them clear the axis, a random intervention succeeds with probability
`m/C(7,k)`. **A random guess CAN produce the loop's outcome** — 1 time in 7 for
a single-chain fault. The pool is complete and includes the true item, so the
count is a measurement: `m = 0` would mean the positive control did not fire,
`m > 1` would mean the intervention is not identifying and the loop's success
would carry no information. Both outcomes are reported as they come.

**Measured, this run (`--seed 20260819 --draws 2000`):**

| Case | k | C(7,k) | subsets that clear | chance rate | empirical (2000 draws) | z |
|---|---|---|---|---|---|---|
| POS-1 | 1 | 7 | 1 | **1/7 = 0.142857** | 298/2000 = 0.149000 | +0.79 |
| POS-2 | 2 | 21 | 1 | **1/21 = 0.047619** | 87/2000 = 0.043500 | −0.87 |
| NEG-3 | 1 | 7 | 1 | **1/7 = 0.142857** | 263/2000 = 0.131500 | −1.45 |
| ROBUST | 1 | 7 | 1 | **1/7 = 0.142857** | 284/2000 = 0.142000 | −0.11 |

The empirical control agrees with the exhaustive derivation within sampling
noise (all |z| < 1.5, binomial standard error). It is an independent check: had
the repair had cross-chain side effects, the two would have diverged.

**In NEG-3 the same control reads `positive_control: False`** — exactly one of
the seven interventions clears the axis, and it is **not** the one the loop
chose. The control distinguishes a right answer from a wrong one, which is the
whole thing v1's control could not do.

**Honest limit on this control.** That `m = 1` is provable a priori from the
Rust source: repairing a chain other than the violated one leaves the violated
one violated, and the corrector is idempotent on clean chains. So the *value* is
predictable. What is **not** an identity is the *null*: it is `1/7`, not `0`, and
a random intervention really does hit it about one time in seven — as the
empirical column shows. That is the difference between this control and v1's.

---

## 6. The tamper check — the chain proved load-bearing, empirically

Assertions about wiring are cheap. The loop therefore ends by **reproducing
fatal 4 on purpose, once**, in a function never called from the measurement
path: it re-runs NEG-3 with the corrector driven by the sealed ground truth
instead of the localizer's output.

```
chained   : repair(perturbed, localizer   -> [3])  axis A cleared = False
TAMPERED  : repair(perturbed, ground truth-> [5])  axis A cleared = True
>>> the chain is LOAD-BEARING: True
```

The two disagree, so the reported outcome **depends on which one drives the
corrector**. If the chain were decorative, NEG-3 would come out the same either
way.

Run against a hand-tampered copy of the whole script (`targets =
tuple(fault.broken_chains)`), the loop reports:

```
NEG-3 ... prereg FAIL  actual PASS  c1 True  c2 True  match False
LOOP STATUS: PREREGISTRATION_VIOLATED
exit 1
```

So the v1 defect **manufactures a success where v2 reports a failure**, and the
`PREREGISTRATION_VIOLATED` / exit-1 branch is reachable, not dead code.

---

## 7. What the run did

`python cas_weld_loop_v2.py` — exit **0**, 18,154 scanner calls, zero GPU, zero
API cost, no model.

| Case | prereg | actual | C1 | C2 | match |
|---|---|---|---|---|---|
| POS-1 one broken RPM chain | PASS | **PASS** | True | True | ✅ |
| POS-2 two broken RPM chains | PASS | **PASS** | True | True | ✅ |
| NEG-1 sub-threshold ordering inversion (detector blind spot) | GATE_FAILED | **GATE_FAILED** | — | — | ✅ |
| NEG-2 no fault at all | NO_FAULT | **NO_FAULT** | — | — | ✅ |
| NEG-3 detection failure propagates to correction failure | FAIL | **FAIL** | False | False | ✅ |
| ROBUST in-scope fault beside an out-of-scope one | PASS | **PASS** | True | True | ✅ |

`LOOP_FALSIFIABLE_AND_HELD`. Stable across seeds `1, 42, 777, 20260101, 99991`.

**POS-1 trace.** Injector degraded chain 3 (`F4`) stage `D` from 0.80 to 0.2644.
Gate: `fired=['A']`, severity 0.142857. Localizer: `[3]`. Repair → VERIFY
`fired=[]`, severity 0.0. Repaired ≠ original, L1 0.10. Control 1/7.

**ROBUST is the case that shows the loop does not overclaim.** A pathway fault
sits beside an out-of-scope domain-precedence fault
(`domain_averages = (0.10, 0.90, 0.10, 0.90)` — `C` and `O` dominate `P` and
`E`). The gate names `['W', 'A', 'P']`. The loop localizes and clears **A**;
VERIFY still reports `fired=['W']`, and the loop prints
`OUT OF SCOPE, NOT CORRECTED: axes ['W'] still fired` and records
`residual_out_of_scope_axes`. It reports a partial repair as a partial repair.
(`P` is derived — `compute_compound_severity` returns 0 below two detections —
so it drops out once only `W` remains, and `P` is stripped from every
"which axis was named" set in any case.)

---

## 8. REAL vs ABSENT

| Link | Status | What is real | What is absent |
|---|---|---|---|
| The detector | **REAL** | `cas_engine.InversionScanner.scan`, Rust, called 18,154 times; every verdict in the loop is its output | — |
| Blind axis naming | **REAL** | axes read off `axis_scores`; no function receives an axis name; signatures asserted | — |
| Blind localization | **REAL** | leave-one-out over the real detector; recovers an index the scalar output does not give | the procedure is authored; its correctness is provable from the Rust source (see §9) |
| Chaining | **REAL, and demonstrated** | `is` identity check plus the §6 tamper check showing the outcome flips | — |
| The corrector | **REAL solver** | constraint solver over the RPM ordering; `repaired != original` measured every run | it is authored, and it is not a search — it is a closed-form satisfying assignment |
| The control | **REAL** | exhaustive over all `C(7,k)`, pool includes the true item, plus 2000 seeded random draws | — |
| Axis `A` string corrector | **ABSENT** | — | `invert_expression(src,'A')` raises `DeferredAxisError`; axis A is correctable on the numeric plane only |
| Axes N / W / F / E / S / P | **OUT OF SCOPE** | — | E and S are hardcoded placeholders; P is derived; N/W/F have no numeric-plane corrector here. Not faked, not claimed |
| J1 (text reading → CAS) | **ABSENT** | — | deleted with the PCBA crosswalk; per design rule F, no component vocabulary drives anything |
| J2 (expression → epsilon prefix) | **ABSENT** | — | the numeric plane has no epsilon realizer; the criteria that lived on it were deleted, not fixed |
| Stage 5 (likelihood on a model) | **ABSENT** | — | no model is loaded; **the loop says nothing about efficacy** |
| The return leg | **ABSENT** | — | nothing turns a repaired pathway array back into an instruction in any upstream vocabulary |

---

## 9. What still cannot fail — stated, not hidden

Design rule C asks whether any criterion remains unfalsifiable. Answering
honestly:

1. **The GATE has no chance null.** Reported as a precondition, not scored as
   identification. Its content is threshold crossing, and NEG-1 fails it. §4.

2. **Criterion 1's *value* is provable a priori.** `detect_pathway_inversion`
   makes severity exactly additive over chains (`violated_chains / 7`), so
   substituting chain *i* lowers severity **iff** chain *i* was violated, and
   leave-one-out is exact by construction. Given a gate-passing fault and this
   localizer, criterion 1 cannot fail. Its content is therefore **not**
   "we might be wrong"; it is that the procedure extracts an identity the
   detector's scalar output does not contain, where a random guess gets it
   `1/C(7,k)` of the time — and that a **different** localizer fails (NEG-3).
   The criterion is falsifiable **with respect to the procedure**, not with
   respect to the object.

3. **Criterion 2 inherits that.** Given a correct localization it will clear,
   because the corrector's output is provably outside the detector's violation
   guard. It fails when localization fails (NEG-3), which is exactly the
   propagation the brief asked to be demonstrated.

4. **The exhaustive control's count of 1 is likewise provable.** What is not an
   identity is the null it produces — `1/7`, not `0` — and the empirical column
   in §5 shows a random intervention really does succeed at that rate.

**The root of all four.** The axis-A detector is a transparent, hand-written
rule over a numeric array. Anything this loop measures about it can be derived
by reading `cas-engine/src/inversions/mod.rs`. **No arrangement of this detector
can produce a result that is surprising in principle.** What the loop can and
does establish is narrower and worth stating exactly:

> a diagnose→correct chain built on this detector **reports failure when the
> diagnosis is wrong**, does not fall back to ground truth, does not manufacture
> a correction when nothing is detected, and beats a stated non-zero chance
> rate that a random intervention can and does hit.

That is the whole claim. It is one axis and two criteria.

---

## 10. What is NOT claimed

- **Not efficacy.** No model is loaded. Nothing here bears on whether CAS
  correction improves any model's behaviour.
- **Not string-plane coverage.** The string detectors are untouched by this
  loop. Their measured effective coverage remains 2 of 7 (v1 §6.5).
- **Not the epsilon bridge.** J2 is absent, so nothing here inherits or
  re-tests the 40E verbatim-continuation leak or the never-run stance-matched
  non-CAS control.
- **Not a component→Noetic mapping.** Per design rule F, no PCBA component type
  (DR / AMP / RS / CONN) appears anywhere. The Component Atlas returned NULL at
  pythia-1b and GREY at pythia-2.8b and gpt-neox-20b, and the board taxonomy
  returned VACUOUS on natural conversation.
- **Not a claim about the detector's coverage of real RPM failures.** NEG-1
  shows the detector misses a whole class of genuine prerequisite inversions —
  every one where the unsatisfied stage stays above 0.5. That is a live gap in
  `detect_pathway_inversion`, surfaced by this loop and left open.

---

## 11. Separate finding — a real bug fixed in shipped code

`noetic-compass-scaffold/noetic-compass/cas-native/belief/inversion_gate.py`

```python
_DOMAIN_RE = re.compile(r"\^([PCEO])\b")        # BEFORE
```

`_` is a word character, so in the drive-tagged literals this project actually
emits there is no word boundary between `E` and `_`, `\b` never matched, and
`_extract_domains` returned `[]`. **Axis W could therefore never fire on any
drive-tagged expression in the repository** — not just in this loop.

```
BEFORE  _extract_domains('^8^E_{F5} -> ^6^C_{F5}')  ->  []
        axis_w_check(same)  ->  clean=True, reason='fewer than 2 domain markers'
```

Fixed by replacing `\b` with a lookahead that is `\b` **with `_` permitted** —
reject only a following letter or digit, which would mean the domain marker is
part of a longer token:

```python
_DOMAIN_RE = re.compile(r"\^([PCEO])(?![A-Za-z0-9])")   # AFTER
```

```
AFTER   _extract_domains('^8^E_{F5} -> ^6^C_{F5}')  ->  ['E', 'C']
        axis_w_check(same)   -> clean=False, 'precedence violated: E (rank 2) followed by C (rank 1)'
        axis_w_check('^8^C_{F5} -> ^6^E_{F5}') -> clean=True   (valid C->E descent, stays clean)
        run_inversion_scan('^8^E_{F5} -> ^6^C_{F5}').axes['W']['clean'] -> False
        run_inversion_scan('^8^C_{F5} -> ^6^E_{F5}').axes['W']['clean'] -> True
```

Seven regression tests added to
`cas-native/tests/belief/test_inversion_gate.py`, covering the drive-tagged
violation, the drive-tagged valid descent, the register form `^3^P|A`, and a
negative guard that `^Extra` is still not a domain marker. **Four of them fail
against the old regex**, so they are genuine regressions and not decoration.
`cas-native/tests/belief/` — **135 passed** before, **142 passed** after
(21 → 28 in this file). The 24 unrelated failures elsewhere in
`cas-native/tests/` (`test_trainer_v2.py`, `test_v2_evaluation.py`) were
confirmed pre-existing by re-running them with the change stashed.
