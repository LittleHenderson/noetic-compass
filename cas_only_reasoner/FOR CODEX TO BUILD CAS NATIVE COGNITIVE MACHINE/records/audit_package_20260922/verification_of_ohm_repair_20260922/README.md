# Independent verification of the CAS-Ohm numeric repair — 2026-09-22

**Subject.** Codex's repair of the older diagnostic module `noetic-compass-scaffold/noetic-compass/api/cas_ohm/`:
commit `9e2e3a8a` on `codex/ohm-invalid-numbers-20260922` (identical tree `34b0d982`, which is reachable on the remote
from `codex/cas-reconcile-20260922` @ `5f7111d5`). Base `eb998556`. Quantifiers blob `17295cd374d460407ee24f7c1233ffd2498acf9c`.

**Why this exists.** The owner's plan: one agent repairs, a separate agent verifies. Codex repaired. This is the
verification. Seven independent agents each took one angle, and a critic re-ran every reported defect and settled
disagreements. None of them wrote any of the code. Nothing under the repository was modified; all runs were on
exports or private clones. No model, GPU or cloud job ran. Raw structured results: `verifier_results_raw.json`.

## Verdict

**The repair does what it was asked to do, for the right reasons, and touches nothing else. It is not clean: it
introduces one new defect of its own, and its new tests are weaker than their count suggests.**

| question | answer | status |
|---|---|---|
| Are the six peer-audit failures fixed? | Yes. All 8 peer probes pass, each by a named refusal or a named censor marker — never by an accidental error. | ✅ verified |
| Do its own numbers reproduce? | Yes, every one: 70 functions / 203 cases; base `86/117`, `a4b2e0d7` `111/92`, repaired `203/0`, case by case. | ✅ verified |
| Did it keep the earlier tests unchanged? | Yes. 39 original bodies match `eb998556`; the 12 from Claude's hardening are byte-identical to `a4b2e0d7`. | ✅ verified |
| Did it change anything outside its scope? | No. 19 files, all in `api/cas_ohm/` or its record folder. Compiler, atlas, Rust engine byte-identical. | ✅ verified |
| Do the compiler CAS-Ohm and atlas still work with the same meaning? | Yes. Identical results at base and repair (314 / 98 + 1 environment failure / 64); board-to-compiler example still exact `3/1`, `NO_MEASUREMENT_PERFORMED`. | ✅ verified |
| Did it clip, round away, swallow errors, or weaken tests? | No hidden clamping, rounding or swallowed errors. Signed residuals stay signed; tiny positive values still work. | ✅ verified |
| Did it introduce a new defect? | **Yes — one P2** (below). | 🟧 open |
| Are its new tests strong? | **Only partly.** They check that something is refused, not which refusal. | 🟧 open |
| Is every behaviour change documented? | **No — six are not in its policy.** | 🟨 open |

## The six peer findings — each closed for the intended reason

Re-run with the peer audit's own probe files, logic unchanged (`contract_boundary_probes.py`, `audit_ohm.py` from
`0922f339`). Against `626cc84b`: 8 tests, 7 failures, 1 error. Against `9e2e3a8a`: all 8 pass.

| peer finding | before | after |
|---|---|---|
| invalid tolerance | `delta_current(100, 0, tolerance=nan)` → `WITHIN_TOLERANCE` | named `ValueError` |
| finite overflow | `i_pred(1e308, 1e-308)` → `inf`; `r_hidden(1e308, 0.1, 2)` → `inf` | refused or censored |
| interval bypasses the zero guard | `r_hidden(8, 0, 2, i_obs_interval=(1, 2))` → `ZeroDivisionError` | `CensoredResult` with a named marker |
| reversed / malformed intervals | accepted, verdict `RISING` | `InadmissibleTrendError` |
| exact Decimals collapse to one float | two separated intervals near 1.0 → `NO_TREND` | `RISING` |
| save/replay | `2.4` + 52 nines → `Q1`, saved `'2.5'`, reopens `Q2` | every digit kept; same band on replay |

Of the peer audit's 50 `audit_ohm` probes, all 43 belonging to its numbered findings or their valid controls now behave
as asked. The other 7 are the peer's side observations; the repair leaves them unchanged and says so in its limits.

Save/replay was attacked harder than the peer did: 99 cut-point values under 9 tampered Decimal contexts plus a fresh
thread — **0 mismatches** (the earlier code had 1,477). Importing the module no longer changes the global Decimal
precision (it stays 28; before the repair it was changed to 50).

## What is wrong with the repair

**P2, new — unbounded exact-arithmetic cost.** To keep exact decisions, the repair now builds Python `Fraction`s
from level and trend-point inputs, with no size check. A short, valid, finite Decimal with a huge exponent makes the
call never finish. `maturity_q4(Decimal("5"), prev_i_q=Decimal("1E-999999999999999999"))` tries to build an integer of
about `4.152410e+17` bytes (the critic's measurement); it was killed at 60 s. On `a4b2e0d7` the same call returned
at once. Growth: `1E-1000000` 0.138 s, `1E-3000000` 0.715 s, `1E+10000000` 7.110 s. A related case raises a raw
`MemoryError` at line 724 instead of the documented `ValueError`. The repair guards the *threshold* this way but not
levels or points, although its README lists "validation before rational allocation" as covered. Rated P2, not P1,
because nothing at runtime calls this module; not P3, because an accepted input can hang the process.

**P2, new — the new tests do not pin the reason for a refusal.** None of the 152 new cases uses `pytest.raises(...,
match=...)`, and none asserts the new censor markers (`OBSERVATION_UNREPRESENTABLE`, `OBSERVED_INTERVAL_INVALID`,
`OBSERVED_POINT_OUTSIDE_INTERVAL`). The critic replaced the named refusal with an accidental Python error: all 152
still passed. It merged the four new markers into one label: all 203 still passed. So "203 passing" says the inputs
are refused, not that they are refused for the stated reason.

**P3, new — six behaviour changes missing from `NUMERIC_POLICY.md`:** a `-0.0` tolerance or minimum effect is no
longer turned into `0.0`; `r_cap` now accepts Decimal bounds (was `TypeError`) and returns `float` where it returned
`int`; `True` is now refused as a maturity/trend threshold while the float functions still accept it; results built by
hand no longer equal returned ones (the appended field changes equality and `astuple` length 4 → 5); a zero-compatible
nonzero Decimal observation now gets `OBSERVATION_UNREPRESENTABLE` although the policy promises it keeps
`OBSERVED_INTERVAL_INCLUDES_ZERO`; and the cost change above.

**P3, new — reproduction.** On this machine's default Git setting (`core.autocrlf=true` in the system gitconfig) the
README's reproduce steps fail: the package files check out with CRLF and the byte checks assert. They pass on an LF
checkout. The runner also creates its temp folder two levels above the repository root, and its `-c os.devnull` flag
strips file names from the raw pytest logs. No number is affected.

**Inherited, still open (present before the repair; the repair's own limits say some stay open):** `r_total`'s
positivity check runs on rounded float sums, so an exactly zero or negative total can pass (P2); `check_eligibility`
admits `stale=None`, `outcome=None` and the string `'UNASSESSED'` (P2); `r_hidden` accepts a negative point observation
and returns a negative apparent resistance, while the same value as an interval is censored with a false "includes or
touches zero" reason (P2); a two-character string such as `'12'` is read as the interval `(1, 2)`; the new
point-inside-interval check compares rounded floats; underflow of a quotient is silent; `delta_current` still defaults
its region to `ACTIVE`; the wrong sentence "NaN compares False against every operator" survives in unreachable code.

## Integration — the owner's decision, not mine

The repair carries Claude's hardening **by content, not by history**: it was built on `eb998556`, so merging it onto
`research/helm-3.0-cas-lab` conflicts in `quantifiers.py` and `CHANGELOG.md`. The content check shows no loss: its
`test_quantifiers.py` is byte-identical to `a4b2e0d7`. Nothing here merges or cherry-picks it.

## What the repairing agent would need to fix before this is clean

1. Bound size or exponent **before** building any `Fraction` from a level or point, and turn the `MemoryError` path
   into the documented `ValueError`.
2. Make the new tests assert the reason: `pytest.raises(ValueError, match=...)` and the exact censor marker per case.
3. Add the six undocumented changes to `NUMERIC_POLICY.md`, or revert the ones that were not intended.
4. Add a `.gitattributes` rule (`eol=lf`) for the package and its record folder, so the reproduce steps work on a
   default Windows checkout.

## Not checked by anyone

The real-browser viewer test (it fails at both commits here, from path length alone, so it cannot tell them apart);
the `836`-case claim in `5f7111d5`; whether the two lines' compiler files mean the same thing.

## Also produced by this verification

`book/OWNER_DECISION_BOOK_ISSUES.md` — the three book issues, with verbatim quotes, exact truth tables and exact gain
values, prepared for the owner's decision. Nothing in the book was edited.
