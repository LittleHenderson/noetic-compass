# language_v3 — the LM-T1 CCE translator, brought into the repo, with two things added

This folder is the real CAS controlled-English translator: the `lm_t1` package, copied whole so that it runs from
inside this repository. It passes every mark the base passed, and it now adds two things the base lacked: the
`p/q` number form (the owner's Q13 ruling) and sentence forms for the two turn types that had none, REFUSE and
CLOSE.

The base is `C:\Users\wakil\Documents\Codex\2026-10-14\lm_t1`. Every file's source path and sha256 is recorded in
`PROVENANCE.md`. The two additions are described in `GRAMMAR_CCE_v0_1_v3_ADDENDUM.md`. The before and after of
every headline number is in `MEASUREMENTS.md`.

## Run it — read this first, because it cannot run without two folders outside the repo

Two packages are imported read-only and are **not** copied here, because they are not this repo's:

    sdg_bridge_v2          C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011
    lacunarity_machine     C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_machine_v1

Set them on `PYTHONPATH` or nothing below runs. This is the exact line that was verified working:

    $env:PYTHONPATH = "C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011;C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_machine_v1"

Then, from this folder (Python is `C:\Python314\python.exe`, always with `-X utf8 -B`):

    C:\Python314\python.exe -X utf8 -B run_suites.py         # all four suites, exact counts
    C:\Python314\python.exe -X utf8 -B measure_marks.py      # re-measure every marked number
    C:\Python314\python.exe -X utf8 -B test_lm_t1.py         # Ran 26 tests ... OK
    C:\Python314\python.exe -X utf8 -B test_lm_t1b.py        # Ran 11 tests ... OK
    C:\Python314\python.exe -X utf8 -B test_lm_t1c.py        # Ran 5 tests ... OK
    C:\Python314\python.exe -X utf8 -B test_lm_t1v3.py       # Ran 26 tests ... OK

**Plainly: a test that needs those two folders cannot run without them present.** `test_lm_t1c.py` runs alone.
`test_lm_t1b.py` needs `sdg_bridge_v2` for its compiler cross-check. `test_lm_t1.py` needs `lacunarity_machine`
for the coverage-ledger test and `sdg_bridge_v2` for the ALIAS-WIDE tests; with those two paths unset it fails at
import with `ModuleNotFoundError: No module named 'sdg_bridge_v2'`. `measure_marks.py` also reads the 5,268-row
English file set under `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-synthetic\data\path_d` for mark M4. Nothing here
fakes those dependencies, and nothing here is skipped to make a run look green.

A re-measurement is not a run. `worker.py` is the run: it needs a single-use owner permit, hostname `MSI`, blocked
sockets, and it writes receipts to `runs/`. It will refuse to start anywhere else, by design. `measure_marks.py`
calls the same scoring functions in the same order without the permit and prints the same numbers, for comparing a
before and an after on one machine. It is never a run record and never a claim.

## The base package, as it was

This is the base's own README, kept word for word:

- LM-T1: CCE v0.1 (`cce.py`). Results `RESULTS.md`. CAS cross-check with the tksCAS repo compiler
  (`noetic-compass-scaffold/noetic-compass/api/notation/compiler.py`, via `fair_data_experiment_v2_sdg.sdg_source`).
- LM-T1b: CCE v0.1b (`cce_v01b.py`): nested Noetics and set meta-logic. Results `RESULTS_T1B.md`.
- LM-T1c: CCE v0.1c-R (`cce_v01c.py`): dotted fractals under the owner's N1 ruling. Results `RESULTS_T1C.md`.
- Compiler used for LM-T1b and LM-T1c (nesting, meta-logic, book examples, recipe-grammar comparison): the newest
  one, read-only, `C:\Users\wakil\Documents\Codex\2026-10-08\task-4\cas-online\dist\compiler\api\notation\compiler.py`,
  sha256 `464fd4adfae90a35ba54aa794829da1fe713b9b9cccd68b630ecccfdfbca2f56` (recorded in SOURCE_MANIFEST_T1B.json and
  SOURCE_MANIFEST_T1C.json).

`RESULTS.md`, `RESULTS_T1B.md` and `RESULTS_T1C.md` are the frozen records of the 2026-10-14 runs. They were not
edited, including the line in `RESULTS.md` that reads `U-TURN COVERED 4, LACUNA 2`: that is what the base
measured, and it stays as it was written. What this folder measures now is in `MEASUREMENTS.md`.

## What was added, and nothing else

**1. The `p/q` number form (owner's Q13 ruling).** A coefficient such as `1/3` had no written form, which is why
LM-T4 recorded 5,903 yields with no sentence. `<number>` now admits `p/q` wherever a number was allowed: recipe
coefficients, stock amounts, leakage coefficients, degrees and rates. One value keeps one canonical text and
nothing rounds: `1/4` and `0.25` are one quarter and one content, `1/3` stays `1/3`, and asking for a decimal of
something that has none raises `LOSSY_CONVERSION_REFUSED` instead of writing `0.3333…`.

**2. The REFUSE and CLOSE turns.** The base's ledger read `U-TURN COVERED 4, LACUNA 2`, and REFUSE and CLOSE
were the two with no form. Each now has its own sentence, wired into both parse and render:

    I will not do that: boundary violation.        REFUSE — the boundary that was not crossed
    That closes the turn.                          CLOSE — nothing named
    That closes Ω_tea.                             CLOSE — naming the subject

No turn collapses into another: all six turn types parse from their own sentence and read back as themselves, and
every turn type the grammar has no form for still raises. The ledger now reads **U-TURN COVERED 6, LACUNA 0**.

## Files added in this folder (not copied from the base)

| file | what it is |
|---|---|
| `PROVENANCE.md` | every file's source path and sha256, and the `PYTHONPATH` the base needs |
| `MEASUREMENTS.md` | every headline number, before and after, with the exact commands |
| `GRAMMAR_CCE_v0_1_v3_ADDENDUM.md` | the whole of the grammar change: the number form and the two turn forms |
| `test_lm_t1v3.py` | 26 new tests: the fraction form, the two turns, the ledger, and that nothing else moved |
| `measure_marks.py` | re-measures M1–M7 and the side universes without a permit |
| `run_suites.py` | runs the four suites and prints their exact counts |
| `MEASURE_BEFORE.json` | the raw re-measurement of the base, before any edit |
| `MEASURE_AFTER.json` | the same re-measurement after the two additions |

## What did not change

The frames, templates, aliases, tail words, recipes, relations, nesting limit, fractals, refusal codes other than
the one added, and the normalization. `GRAMMAR_CCE_v0_1.md`, `FROZEN.json`, `FROZEN_T1B.json`, `FROZEN_T1C.json`,
`ALIAS_WIDE_LEXICON_v0_1.json`, the `SOURCE_MANIFEST*.json` files, the `handset/` items and the `runs/` receipts
are byte-identical to the base (their sha256 in `PROVENANCE.md` match the source). Because `cce.py` and
`coverage.py` did change, the `SOURCE_MANIFEST*.json` files no longer describe the current bytes; they are kept as
the base build's own record rather than rewritten, and `PROVENANCE.md` says which files changed and how.

No existing test was weakened, changed or deleted. The three base suites are byte-identical files and still pass
26, 11 and 5. The new behaviour is tested only in `test_lm_t1v3.py`.
