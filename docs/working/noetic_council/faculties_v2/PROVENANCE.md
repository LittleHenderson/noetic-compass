# PROVENANCE — `faculties_v2`: what was copied in, from where, and what its bytes are

Built 2026-10-16 in `C:\Users\wakil\Documents\Codex\2026-10-16\faculties_v2\`.

This folder is the **merged copy** of `..\faculties\`. The originals are untouched and still
pass (`python -B test_all.py` in `..\faculties\`: `TOTAL 37 cases: 37 passed, 0 failed`).
Two mechanisms that already existed in this project were wired in here:

  * **RESTART_FALLBACK** — RB-C4's seeded alternative fit starts, ported from
    `2026-10-14\rb_c4\fitg.py` into `restart.py` and called by `pondering`;
  * **THE UNITY EYE** — the F1 watcher, built from
    `2026-10-15\helm_language_faculties_circuit_design_v1\UNITY_EYE.md`, in `eye/`.

Nothing in `rb_c4`, `rb_i1`, `u1b_unity_eye` or their neighbours was modified. Nothing outside
this folder was written at all. Every hash below was checked on 2026-10-16 with PowerShell
`Get-FileHash -Algorithm SHA256`.

## Byte-identical copies from `..\faculties\`

These four files are copied in with **no change at all**, and
`test_the_copies_are_byte_identical_to_their_sources` re-hashes both sides on every run.

| copy | copied from | sha256 (source and copy, equal) |
| --- | --- | --- |
| `bias.py` | `..\faculties\bias.py` (itself a copy of `..\the_loop\bias.py`) | `d31a129db14a2c37ae712ec55c703705e4d735f433dab773a848ead68421e1b5` |
| `guard.py` | `..\faculties\guard.py` | `f5e4c805a1827d2e919d7afaa643c4691979ca82749066d596e207d8f349007c` |
| `held.py` | `..\faculties\held.py` | `9d8d715d30c7f401749fa40c24219766d7c6692e43b0149a29201cc7af15fd70` |
| `drive_loop.py` | `..\faculties\drive_loop.py` | `f54791d401971791d5ae1a8f82a13e2c39acba0443ed0ea0f9f37bdfd994ead8` |

bias.py copy sha256: d31a129db14a2c37ae712ec55c703705e4d735f433dab773a848ead68421e1b5
bias.py source sha256: d31a129db14a2c37ae712ec55c703705e4d735f433dab773a848ead68421e1b5

## Copies that this merge changed, and why

| file | source sha256 | what changed |
| --- | --- | --- |
| `faculties.py` | `72684734712b935c5cfa1004ae8a11f596bbda0d58125b68cf36369918745dc3` | `pondering` now takes `refit=None` and, when no refit is passed, runs `restart.restart_refit` (the RB-C4 fallback) instead of refusing for want of a fitter. The old path is unchanged when a refit is supplied. |
| `test_all.py` | `02be876fa698cf76bb7a6dc6cdccc6783e9eb06275e218d43221c798d7b480e1` | the original 37 cases are kept word for word and cases are added for the restart fallback, the Unity Eye, the UNDECIDED IN SOURCES drift check and the byte-identical copies check. |
| `README.md` | `4e275c3970a5c2d8532cdb317a196d5e42cc9f064866d1494d9189b8960f9293` | two new sections (the restart fallback, the Unity Eye), the corrected "what this build does not contain" list, and the UNDECIDED IN SOURCES list. |
| `PROVENANCE.md` | `b04a64982343c9d2a52960c00e3892e75733f7c768f54749b8e9868db31f04dc` | this file. |

## New in this merge

| file | what it is | sha256 at build time |
| --- | --- | --- |
| `restart.py` | the RESTART_FALLBACK port: seeded starts, start 0 first, keep the fewest unexplained, every seed recorded | `d5133233eaf88f592ad93e4ea82b5454d41bf0fce04754eb2dbdefce42ff0bfb` |
| `eye/__init__.py` | the eye package's exports | `fe7f69a8c325e044c422314aa08c3efee6667131f10c46463a767f93a575bcf7` |
| `eye/tap.py` | the read-only digest-checked tap | `e0cb0edd791019e118a3410625eca697530ec80c1b0ac0ae72a8156b6c366ec6` |
| `eye/recipe.py` | the one recipe, Y_T = min_i(x_i / a_i), the Limiting Reagent, gate G1-G3, the eta/epsilon receipt | `9ed765fec23901d2c7ce7154a6834d6321282654e2a65f6259b3d91ffb87e950` |
| `eye/signals.py` | the five measured health ingredients and their count rules | `3d0a20588e075a12cbaee9475b54a33d16504d5b5146783403504ffc9ac35a07` |
| `eye/eye.py` | the watcher: reads, computes, logs, proposes report-only, acts on nothing | `e561ac707e691727e5b0b64bed4fbb909fa3037f18cb79a652c92ee579ffe97d` |
| `eye/recorded_suite_results.json` | the recorded suite results the eye reads, with the exact command and the exact tail of each | regenerated after every change; see below |

The recorded-results file is an **input** to the eye, not something the eye writes. It records
what each package's own suite printed, and the case count in it is cross-checked against the
number of `@case` functions in the suite on every run, so a stale record fails the suite rather
than flattering a package.

## Sources read for the two mechanisms and NOT copied as files

These were read in full and are cited by path and line in `restart.py`, `eye/recipe.py`,
`eye/eye.py` and the README. None of them was edited.

| source | sha256 | what it was read for |
| --- | --- | --- |
| `2026-10-14\rb_c4\fitg.py` | `62951b1d53359313b19515e131d8cecc590c946a330ab451e0fa2f007b653a19` | the RESTART_FALLBACK itself: `fit_routes` (150-179), `route_fit_once` (96-147), `certain_set` (79-93), `MAX_ITER` (52), `CLEAR` (51), the seed rule (109), the fallback fire rule (169-171) |
| `2026-10-14\rb_c4\RESULTS.md` | `01a00e5fe2daae571a1f9b0d85bef9d92632631a682fbec996f1c0e1cdc9b53e` | the measured precedent: fired 8,828 times, 7,823 alternative starts kept (line 43); "a FIT-START win, not a proposal win" (line 52) |
| `2026-10-15\helm_rb_i_faculties_design_v1\FACULTIES.md` | `2afe438e232f0b0dad9466e0396e37b6637452fa58881538432e08164349a555` | the nine faculties, and the pondering card (2.3) that says the fallback is `refit`'s job |
| `2026-10-15\helm_rb_i_faculties_design_v1\CAS_MAPPING.md` | `48fe9dae0ec2556f026ea3f8feabd00addce47dc727b07f7aa48f7b9e8f3328b` | the design labels the faculties carry |
| `2026-10-15\helm_language_faculties_circuit_design_v1\UNITY_EYE.md` | `b9adb8f9cda471410fee52141ce446d48bca4602296216f773ed6592ee98c132` | the eye's form, its recipe, the gate G1-G4, the eta/epsilon receipt, the read-only tap rule, the guardrails |
| `...\OWNER_RULING_UNITY_EYE_20261015.md` | `1f5d3fc13d1a35193ab799f45bc349e42d7127eff6d1f2c60407a0ff17aad3d3` | the owner's ACCEPTED_BY_OWNER ruling: MINI-VERSION form, REPORT-ONLY mode |
| `...\OWNER_RULING_UNITY_EYE_ACTING_20261015.md` | `ca0007cd821b791c8d5a8eadaa0b9f162adc8b847aaea6f3bfb3e87f02f98878` | what acting would mean, and that it needs its own test; this build stays report-only |
| `2026-10-16\_week_study\E_UNITY_EYE.md` | `cc3dc2a9fb641cfc6fb86cd78368e62ec9af0a644cd170b6f3646e8bb3c67af3` | the fullest guide: what is built, what is measured, the failure and the retest |
| `2026-10-15\u1b_unity_eye\RESULTS.md` | `7ba09429f017559dce05f514cf55d45249b62590f43989619b0c9158d6db04cb` | the retest that earned keep: 148 vs 128 faults fixed, 1,816 vs 10,152 false interventions |

## Added 2026-10-16: the real fitter underneath the fallback

`restart.py` was built with no recipe book in this folder, so its own `make_start` fits routes
over cell-binding that the build supplies. Two files put the real machine underneath it, without
changing `restart.py`, `guard.py` or `rb_c4`.

| file | what it is | sha256 at build time |
| --- | --- | --- |
| `real_fit.py` | the adapter: `real_fit_start(terms, train, tau)` returns the `fit_start(start, seed)` that `restart_fallback` calls, running `rb_c4.fitg.route_fit_once` and converting a refusal string to `StartOutcome(refused=...)` and a 5-tuple to `StartOutcome(explained=fit_rows, ...)`; plus `real_restart`, the end-to-end call | `507f0abba7e6397ed883240c898a43711764d0ad99ce446cde7c74d465d45df6` |
| `REAL_FIT_RESULT.txt` | what the real fitter actually did on real `rb_c4` data: every start, its seed, its rows explained, which start was kept, and the held-out counts with a control. Written by `real_fit.py` and byte-identical across two runs | `05ca6d6fe019751ddf9557b00a26e332760b455b5f0cd63c00170d6f075ce8e8` |

`rb_c4\fitg.py` is unmodified and re-hashes to `62951b1d53359313b19515e131d8cecc590c946a330ab451e0fa2f007b653a19`,
the same value recorded in the table above, so the real fitter this folder now calls is the same
file the port was made from.

`real_fit.py` is deliberately **not** in `test_all.py`'s `OWN_MODULES`: it imports `rb_c4`, and
the suite's own rule (`test_..._imports_nothing_outside_the_standard_library`) is that the
build's modules do not. Nothing in `test_all.py` was edited, so the suite still reports 49 cases.

Two facts about `rb_c4` found by running it are recorded in `REAL_FIT_RESULT.txt`, not repaired:
on Task B data start 0 cannot fit any multi-route skeleton (16 of 16 outcomes), and
`route_fit_once` raises `AssertionError` on a one-route skeleton because `fitg.py:145` always
builds a MAX node and `lsr_t4/engine.py:73` requires at least two children.

## How to re-check all of it

```
cd C:\Users\wakil\Documents\Codex\2026-10-16\faculties_v2
python -B test_all.py
```

In `noetic-compass` the same thing, plus the real-fitter run, which rewrites `REAL_FIT_RESULT.txt`
from a live run against `C:\Users\wakil\Documents\Codex\2026-10-14\rb_c4`:

```
cd <worktree>\docs\working\noetic_council\faculties_v2
python -X utf8 -B test_all.py
python -X utf8 -B real_fit.py
```

The run prints the sha256 of `bias.py` before it prints any case result, re-hashes the four
byte-identical copies against `..\faculties\` in a case of its own, and prints the totals last.
