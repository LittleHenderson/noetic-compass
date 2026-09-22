# How to reproduce everything

**Revised 2026-09-22 after the peer audit** (`codex/helm-peer-audit-20260922` @ `0922f339`). The earlier version of
this file gave counts without saying which code and which tests produced them, kept a comparison that had already
been withdrawn, and pointed one claim at the wrong document. The superseded statements are listed at the end, not
deleted.

**The rule this file now follows: every expected result names two revisions — the implementation and the tests.**
A count is a property of that pair, not of "HEAD". Every number below was re-measured on 2026-09-22 from a clean
export of the named revisions; the receipts are in `receipts_reproduction_pins_20260922/` and
`receipts_restore_four_tests_20260922/`. If your output differs, that is a finding — report it with both.

## Environment

- Windows 11. Python **3.14.0** at `C:/Python314/python.exe`. **pytest 9.0.2** (observed 2026-09-22; the earlier
  version of this file said 9.1.1, which I cannot reproduce on this machine and withdraw).
- No third-party packages are needed for the CAS-Ohm module or the compiler, only `pytest` for the suites.
- Set `PYTHONIOENCODING=utf-8`, or CAS symbols (`^`, `∘`, `∈`) will fail to print on a cp1252 console.
- Point `TEMP` and `TMP` **outside the repository** for every suite. The Q4 key fixtures refuse to run otherwise.
- Every pytest run prints one warning: an unknown `asyncio_mode` config option. It is not a test result.

## Two repositories, not one

| | path | git dir | note |
|---|---|---|---|
| **lab** | `…/_worktrees/helm3-lab` | `…/_worktrees/vision-next/.git` | branch `research/helm-3.0-cas-lab` |
| **main** | `C:/Users/wakil/OneDrive/Desktop/tksCAS` | its own `.git` | on another agent's branch |

A commit in one is not visible in the other. The book canon exists as two commits with identical content
(`d50abbbc` in lab, `eb3c9b1e` in main). The main working tree stores some files CRLF; the lab worktree stores LF.
Take digests over LF-normalised bytes: `hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()`.

**Branch scope.** Statements here are about `research/helm-3.0-cas-lab`. Other branches in the same repository
already hold CAS-Ohm compiler operations and a PCBA reader (for example `codex/helm-rpa-recorded-run-20260922` @
`eb998556`). "Absent here" never means "absent from the project".

## Revisions you will need

| short | what it is |
|---|---|
| `c3855275` | merge base of the two agent lines |
| `7f32129d` | my compiler change, before the merge |
| `d50abbbc` | book canon pin; also the last state of my test files before the merge |
| `04547c55` | the other agent's line, merged in |
| `078d00ed` | the merge — it deleted seven passing tests |
| `86ba3d75` | first CAS-Ohm hardening |
| `a4b2e0d7` | second CAS-Ohm hardening |
| `626cc84b` | three deleted help-text guards restored; the state the peer audit froze |
| `9fe1eb36` | the four remaining deleted tests restored |

---

## 1. The older CAS-Ohm module (`api/cas_ohm/`)

### 1a. The implementation × test matrix

Each cell: `quantifiers.py` + `__init__.py` from the row revision, `test_quantifiers.py` from the column revision,
run as `python -B api/cas_ohm/test_quantifiers.py` from a fresh folder. Script: `receipts_reproduction_pins_20260922/ohm_matrix.py`.

| implementation ↓ / tests → | `078d00ed` | `86ba3d75` | `a4b2e0d7` |
|---|---|---|---|
| `078d00ed` (before any hardening) | `PASSED 39/39` | `PASSED 42/48` — 6 fail | `PASSED 44/51` — 7 fail |
| `86ba3d75` | `PASSED 39/39` | `PASSED 48/48` | `PASSED 50/51` — 1 fail |
| `a4b2e0d7` | `PASSED 39/39` | `PASSED 48/48` | `PASSED 51/51` |
| `9fe1eb36` (this branch now) | `PASSED 39/39` | `PASSED 48/48` | `PASSED 51/51` |

The six failures in the `078d00ed × 86ba3d75` cell are `test_i_pred_refuses_{infinite,nan}_{drive,resistance}`,
`test_r_total_refuses_an_overflowing_sum`, `test_r_total_refuses_non_finite_component`. The seventh, added by the
`a4b2e0d7` tests, is `test_r_hidden_refuses_non_finite_drive`. The `86ba3d75 × a4b2e0d7` failure is that same test.

**What the matrix proves, and what it does not.** The hardening changed the answer for the cases its own tests ask
about. The tests were written by the same author as the fix, so passing them does not show the module is sound.

### 1b. The module on this branch still has open numeric defects

`quantifiers.py` has blob `f842a9f2892a322741fb4976dd8350b9f992066d` at `a4b2e0d7`, `626cc84b` and `9fe1eb36`.
The peer audit's probes (`records/peer_audit_20260922/ohm/contract_boundary_probes.py` on `0922f339`) give
**7 failures and 1 error in 8 tests** against it. Observed on `9fe1eb36`, 2026-09-22:

| call | observed | why it is wrong |
|---|---|---|
| `delta_current(100, 0, tolerance=float("nan"))` | sign `WITHIN_TOLERANCE` | an invalid tolerance reports "all is fine" for a difference of 100 |
| `i_pred(1e308, 1e-308)` | `inf` | two finite inputs give an unusable result, emitted as a number |
| `r_hidden(1e308, 0.1, 2.0)` | `magnitude=inf`, `r_apparent=inf` | same, uncensored |
| `r_hidden(8, 0, 2, i_obs_interval=(1, 2))` | `ZeroDivisionError` | the interval path skips the zero guard and crashes |
| `admissible_trend(2, 8, …, earlier_interval=(3, 1), later_interval=(9, 7), …)` | verdict `RISING` | reversed intervals are accepted |
| `maturity_q4(Decimal("2.4999…9"))` (53 nines) | band `Q1`, saved `i_q_exact='2.5'` | reopening the saved value gives band **`Q2`** |

**Do not use this module's outputs as dependable readings until these are closed.** A repair exists on
`codex/ohm-invalid-numbers-20260922` @ `9e2e3a8a` (quantifiers blob `17295cd3…`). It is the other agent's work, not
on the remote, not merged here, and under independent verification at the time of writing.

### 1c. What the first hardening did change (still true)

Against `078d00ed` vs `86ba3d75` code: `i_pred(nan, 4.0)` → `nan` vs refused; `i_pred(8.0, nan)` → `nan` vs refused;
`i_pred(8.0, inf)` → `0.0` vs refused; `i_pred(inf, 4.0)` → `inf` vs refused; `r_total(1e308, 1e308, 1.0, 1.0)` →
`inf` vs refused. Unchanged in both: `i_pred(8.0, 4.0) == 2.0`, `r_total(1, 2, 3, 4) == 10.0`,
`r_hidden(v=8.0, i_obs=2.0, r_known=2.0)` → magnitude `2.0`, `r_apparent` `4.0`.

---

## 2. The compiler suite

From an export of `noetic-compass-scaffold/noetic-compass`, `offline-cas` and `dist` at the named revision (the
help-text tests read files in the last two; the peer audit observed that a sparse checkout without them collects
339 cases, not 639), from
`noetic-compass-scaffold/noetic-compass`:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest --noconftest -o addopts= \
  tests/test_notation_compiler.py tests/test_notation_compiler_nesting_and_defects.py \
  tests/test_notation_compiler_continuation.py tests/test_offline_help_text_canon.py \
  tests/test_full_demo_program.py -q -p no:cacheprovider
```

Implementation and tests from the **same** revision. Script: `receipts_reproduction_pins_20260922/compiler_suite_by_rev.sh`.

| revision | observed | note |
|---|---|---|
| `7f32129d` | `601 passed` | only 3 of the 5 files existed yet |
| `078d00ed` | `458 passed` | the merge; seven passing tests were missing |
| `626cc84b` | `639 passed` | three help-text guards restored |
| `9fe1eb36` | `643 passed` | the four remaining tests restored |

The 99 tests in `tests/test_notation_compiler.py` are unchanged since `c3855275`:
`git diff c3855275 9fe1eb36 -- noetic-compass-scaffold/noetic-compass/tests/test_notation_compiler.py` is empty.

---

## 3. The lab suite

From `…/research/helm_cas_expression_lab`, with `TEMP`/`TMP` outside the repository:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest -o addopts= \
  test_compiler_nesting_facts.py test_foundations28.py test_operation_contracts.py \
  test_q3_behaviour_records.py test_q3_load_and_export.py test_q3_load_boundary.py \
  test_q3_load_errors.py test_learner_q4.py test_q4_followup.py -q -p no:cacheprovider
```

**`348 passed` at `626cc84b`**, reproduced by the peer audit in a complete checkout. The lab folder is unchanged
from `626cc84b` to `9fe1eb36` (`git diff --stat` is empty), so the pin carries. I did not re-run it on 2026-09-22.
The peer audit observed that a sparse checkout missing the export schema gives 342 passed / 6 failed — a setup
error, not a code defect. Takes about three and a half minutes.

---

## 4. The book canon

Canon pin `d50abbbc`. `git diff dbb388ee d50abbbc -- book/CAS_PCBA_Engineer/` → 8 files, **202 insertions, 95
deletions** (commit `0fc6bb30` alone shows 1765/1658: the line-ending mistake fixed by `d50abbbc`).
`git ls-files --eol -- book/CAS_PCBA_Engineer/*.md` → all 39 files `i/lf w/lf`. Both repositories hold identical
book content (`02_MANIFEST.json`, `canon_pin_cross_repository_check`). Listings: **58 blocks, 42 distinct names**
(reproduced by the peer audit):

```python
import pathlib, re
blocks, names = 0, set()
for f in sorted(pathlib.Path("book/CAS_PCBA_Engineer").glob("*.md")):
    for m in re.finditer(r"^\s*(circuit|board)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{", f.read_text(encoding="utf-8"), re.M):
        blocks += 1; names.add(m.group(2))
```

The `gate`/`xor` prefix self-correction:

```bash
git show dbb388ee:book/CAS_PCBA_Engineer/Chapter_10_Special_Purpose_Components.md | grep -n "^[[:space:]]*gate [a-z_]*:"
git show dbb388ee:book/CAS_PCBA_Engineer/Appendix_E_Exercise_Answers.md | sed -n '327p'
```

→ `278:    gate dissonance: XOR< attract, averse >;` and `327:    xor dissonance: XOR< attract, averse >;`.

**Open book issues found by the peer audit — not settled by this package, and not edited:** the breakdown flip is
conditional in `Appendix_B:59` but automatic in `Appendix_A:40/:121` and `Appendix_C:549`; XOR/XNOR take two
inputs in `Chapter_10:115–116` and `Appendix_B:389–390` but "two or more" in `Appendix_C:447`; and
`Chapter_16_Feedback_Systems.md:211` calls a gain of exactly 3 "observed", while its own formula gives
`3000/1249 ≈ 2.401922` at A=12 and `1000/433 ≈ 2.309469` at A=10 with β=0.333. Even the infinite-gain limit is
`1000/333 ≈ 3.003`; "exactly 3" holds only as that limit with β exactly `1/3`. These await the owner.

---

## 5. The compiler comparison that decided the merge — corrected

Digests over LF-normalised bytes: mine (`7f32129d`) `f1a44678438a65c3…`, theirs (`04547c55`) `61ed5a45970459e4…`.
Three of the original five points stand:

| expression | mine | theirs |
|---|---|---|
| `let X = ^8^C_{F2\|A} ∘ ^3^C; let Q = {X}; Q` | `['Phi<^8^C_{F2}:^3^C>']` — drops `\|A` | `['Phi<^8^C_{F2\|A}:^3^C>']` |
| `fn h(s) = s ∘ ^3^O; h(^8^C)` | no cross-Domain warning | cross-Domain warning |
| `fractal(^8^C, ^3^O)` | no cross-Domain warning | cross-Domain warning |

"No warning" means **no cross-Domain warning**; the function example already carried an any-typed-contract
warning in both.

Two of the five were **false** and are corrected here, not repeated:

| demo files from ↓ / compiler → | mine | theirs |
|---|---|---|
| `7f32129d` (old `.cas` files) | invalid | invalid |
| `04547c55` (the other agent's edited `.cas` files) | valid | valid |

The files were the variable, not the compiler.

| `let <name> = ^2^C` | before my commit (`7f32129d^`) | mine | theirs |
|---|---|---|---|
| `P1_count`, `F2_total` | refused | refused | accepted |
| `A`, `T`, `Noetics`, `Worlds` | accepted | refused | refused |
| `Charlie` | refused | accepted | accepted |

`P1_count` was refused before I touched the compiler. It was not a regression I introduced.

---

## 6. No model was run

`learner_q4_neural.py` imports torch only inside `build_model`, which raises `GPU_REQUIRED` unless given an explicit
`cuda:N` device that exists. Nothing in this work calls it. This is a statement about the code; the peer audit
correctly notes that "no model ever ran" cannot be proven from local artifacts alone.

---

## 7. The other agent's work before the merge

Their record: `records/continuation_20260921/VERIFICATION.md` at `04547c55`. I said I re-ran their commands before
merging and observed 458, 304, 92, 27, 2 passed. **Accepted as UNVERIFIABLE**: the only record of that run is text
inside the merge commit itself; nothing dated before the merge shows it.

The other agent's refusal to treat my prose as an owner ruling is in
**`CODEX_CONTINUATION_20260921.md`, lines 53–55** (at `04547c55` and at `9fe1eb36`), not in `VERIFICATION.md` as the
earlier version of claim GOV-3 said. The refusal exists; my pointer was wrong.

---

## Superseded statements from the earlier version of this file

| earlier statement | status | correct statement |
|---|---|---|
| compiler suite "Observed: `458 passed`" | stale — true only at `078d00ed` | 639 at `626cc84b`, 643 at `9fe1eb36` (section 2) |
| CAS-Ohm "Observed: `PASSED 48/48`" | stale — true only for tests at `86ba3d75` | 51/51 with tests at `a4b2e0d7` (section 1a) |
| "running HEAD's test file against the pre-fix implementation gives 42/48" | **false as written** | 42/48 needs tests from `86ba3d75`; tests from `a4b2e0d7` give 44/51 |
| "both shipped demo files compile under theirs and not mine" | **false** — withdrawn in `626cc84b` | the `.cas` files were the variable (section 5) |
| "`P1_count` / `F2_total` refused under mine" presented as my regression | **false** — withdrawn in `626cc84b` | refused before my commit (section 5) |
| pytest "9.1.1" | not reproducible | 9.0.2 |
| GOV-3 refusal "in VERIFICATION.md" | wrong pointer | `CODEX_CONTINUATION_20260921.md:53–55` |
| "I verified their work before merging" | UNVERIFIABLE, accepted | section 7 |
