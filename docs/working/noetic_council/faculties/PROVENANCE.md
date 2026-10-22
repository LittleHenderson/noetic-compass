# PROVENANCE — what was copied into `faculties`, from where, and what its bytes are

Built 2026-10-16 in `C:\Users\wakil\Documents\Codex\2026-10-16\faculties\`.
`bias.py copy sha256` and `bias.py source sha256` are equal below, and the test
`test_the_copied_bias_is_byte_identical_to_the_recorded_hash` re-hashes the copy on every run
and fails if a single byte moves.

## Copied from `the_loop`

Source folder: `C:\Users\wakil\Documents\Codex\2026-10-16\the_loop\`
(measured today with `python -B test_all.py` in that folder: `TOTAL 25 cases: 25 passed,
0 failed`; this build does not re-run its suite)

| copy | copied from | role in this build |
| --- | --- | --- |
| `bias.py` | `the_loop\bias.py` | **the Bias.** The working memory a faculty may read and may not write. Its one-writer rule (`BIAS_OWNED_BY_ANOTHER_COORDINATOR`) is one of the three walls in the test "no faculty can write the Bias". |

bias.py copy sha256: d31a129db14a2c37ae712ec55c703705e4d735f433dab773a848ead68421e1b5
bias.py source sha256: d31a129db14a2c37ae712ec55c703705e4d735f433dab773a848ead68421e1b5

The copy keeps its own docstring, its own `UNDECIDED IN SOURCES` notes and its own refusals
exactly as written. It is not edited, not re-worded and not re-wrapped, because an edited copy
cannot be checked against the file it came from.

## What was read from `the_loop` and NOT copied

| read | why it was read | why it is not here |
| --- | --- | --- |
| `loop.py` | it is the only place in the tree that shows how a Bias is read by a stage, how a coordinator is named, and how a turn records what it did. `DriveLoop`'s coordinator handling and `TurnRecord`'s shape follow it. | This build's tick is the RB-I drive loop, not the five-stage LSR turn. Importing `Loop` would put a second scheduler in a package that must have one. |
| `asom.py`, `disengage.py` | they belong to the same loop. | No readout and no ladder is in this build's scope. Copying them in would import claims this package does not test. |
| `test_all.py`, `README.md` | the house style for a runner, for the claim ceiling, and for an undecided list that a test checks against the code. | The runner and the README here are written for this package's cases. |

## Read from `continuity_build_v3` and NOT copied

| read | why it was read | why it is not here |
| --- | --- | --- |
| `provenance.py` | the owning instruction names it as a piece to integrate with. Its writer record is the tree's existing way of naming who wrote something: `writer_label` (provenance.py:140-167) accepts `{"kind": "FACULTY", "phi": "<non-empty>"}` or `{"kind": "INJECTION", "turn": n}` and refuses every other kind instead of guessing a word. | It classifies a **next-station pointer** inside an atlas thought. This package has no atlas, no station and no next-station pointer: its moves are held-buffer state transitions. Copying it would import an untested claim and a `seams` dependency for vocabulary this package does not use. |

What **is** taken from it, and is checked in the tests: `held.Transition` carries the same
writer shape, flattened onto one frozen record -- `writer_kind` (`FACULTY`, `VERIFIER`,
`CONSOLIDATOR`), `moved_by`, and `phi` -- and
`test_every_state_transition_records_who_moved_it_and_why` requires every faculty move to carry
a non-empty phi, exactly as `writer_label` does. Its refusal style (`CODE: detail`, never a
guessed word) is the style of every refusal in this package.

## What is original to this folder

| file | what it is |
| --- | --- |
| `guard.py` | the two evidence types, the one verifier, the faculty-return check, the single door to the Bias |
| `held.py` | the held buffer: `HELD`, `ADMITTED`, `REFUSED`, `EXPIRED`, and every move recorded |
| `faculties.py` | wondering, pondering, imagination, self-notice |
| `drive_loop.py` | when each faculty gets a turn |
| `test_all.py` | the whole suite, plain Python, no pytest |
| `README.md` | the guardrail as the spine, one line per faculty, the claim ceiling, every undecided line |
| `PROVENANCE.md` | this file |

## Nothing was modified outside this folder

`the_loop`, `continuity_build_v3`, `helm_rb_i_faculties_design_v1` and
`helm_creativity_design_v1` were read only. Nothing in them was edited, and nothing here
imports from any of them at run time: the only copy is `bias.py`, and this folder runs with
nothing else on the path.

## How to re-check all of it

```
cd C:\Users\wakil\Documents\Codex\2026-10-16\faculties
python -B test_all.py
```

The run prints the sha256 of the copy before it prints any case result, so the number above is
visible in the output of every run rather than remembered by this file.
