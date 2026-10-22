# PROVENANCE — what was copied into `the_loop_v2`, from where, and what its bytes are

Built 2026-10-16 in `C:\Users\wakil\Documents\Codex\2026-10-16\the_loop_v2\`.
It is `the_loop` copied forward, plus the RPM engine vendored read-only, plus one new file
(`rpm_gate.py`). The three source packages were **not** modified.

The test `the_copied_files_are_byte_identical_to_the_recorded_hashes` re-hashes every copy on
every run, requires each copy's digest to equal the `source sha256` recorded here, and — on a
machine where the source packages are still present — re-hashes the **source file itself** and
requires that too. So "nothing in the source packages was modified" is checked rather than
asserted.

## Copied from `continuity_build_v3` (as they already were in `the_loop`)

Source folder: `C:\Users\wakil\Documents\Codex\2026-10-16\continuity_build_v3\`
(that package reports 50 test cases passing; this build does not re-run its suite)

| copy | copied from | role in this build |
| --- | --- | --- |
| `asom.py` | `continuity_build_v3\asom.py` | **the readout.** The four-label gauge, used in stage 3 only. |
| `disengage.py` | `continuity_build_v3\disengage.py` | **the ladder.** The owner's four steps, run in stage 5 only when the gate cannot proceed. |

asom.py copy sha256: 8ebf58277536ff16d133e8066fb53dad30a016f5f1af22d019c0c410e60c11a6
asom.py source sha256: 8ebf58277536ff16d133e8066fb53dad30a016f5f1af22d019c0c410e60c11a6
disengage.py copy sha256: 78a73a853f920e9f819ceeeb272d21dd513c08ba7355254dd7db0dd5314add98
disengage.py source sha256: 78a73a853f920e9f819ceeeb272d21dd513c08ba7355254dd7db0dd5314add98

Both copies keep their own docstrings, their own claim ceilings and their own
`UNDECIDED IN DESIGN` notes exactly as written. They are not edited, not re-worded and not
re-wrapped, because an edited copy cannot be checked against the file it came from.

## Copied from `dwp_engine`, read-only, into `dwp\`

Source folder: `C:\Users\wakil\Documents\Codex\2026-10-16\dwp_engine\`
(that package reports 30 test cases passing; this build does not re-run its suite)

| copy | copied from | role in this build |
| --- | --- | --- |
| `dwp\dwp.py` | `dwp_engine\dwp.py` | **the three functors.** `dwp.resolve` dispatches a block to Phi_D / Phi_W / Phi_P. |
| `dwp\depth.py` | `dwp_engine\depth.py` | **the horizon.** `HORIZON`, `check_depth`, `flatten`. The gate reads the number from here. |
| `dwp\retraction.py` | `dwp_engine\retraction.py` | **the dirty propagation.** `mark_dirty_upward`, `is_dirty`. |
| `dwp\lacunarity.py` | `dwp_engine\lacunarity.py` | resolution lacunarity. Copied because it is part of the engine package; **nothing in this build imports it**, and the gate never asks it anything. |

dwp.py copy sha256: 79668428a7f418c8a9d6e38c1b7acbfeb53631f94c65e5396162b4c4b01373c8
dwp.py source sha256: 79668428a7f418c8a9d6e38c1b7acbfeb53631f94c65e5396162b4c4b01373c8
depth.py copy sha256: f293f2b00994983990cfaf76785ab24c3b662212d9999bc42f32c12e4db97fff
depth.py source sha256: f293f2b00994983990cfaf76785ab24c3b662212d9999bc42f32c12e4db97fff
retraction.py copy sha256: ec979b1ec1c1f36ca9fb7985e586445be8123813f4aee0b5f97d52a3b123c46e
retraction.py source sha256: ec979b1ec1c1f36ca9fb7985e586445be8123813f4aee0b5f97d52a3b123c46e
lacunarity.py copy sha256: d393a46d35575ab4b9cbc4476305f51d28f7fb04824a24e27e044891a36b2634
lacunarity.py source sha256: d393a46d35575ab4b9cbc4476305f51d28f7fb04824a24e27e044891a36b2634

**Not one byte of these four files changed.** They keep their own `UNDECIDED IN CANON (U1)...(U10)`
notes, their own `CANON_*` quotations, their own claim ceilings ("It is a mechanism") and their
own absolute imports (`import dwp`, `from dwp import ...`). That is why `rpm_gate.py` loads them
**by path** from `dwp\` and registers them under their own module names before their bodies run:
so the copies can be imported without being edited, and so nothing this build does can reach a
different copy of the engine.

`dwp_engine\test_all.py` and `dwp_engine\README.md` were **not** copied. This build does not
re-run that suite and makes no claim about it.

## Nothing was copied from `return_address`, and what that means

Source folder: `C:\Users\wakil\Documents\Codex\2026-10-16\return_address\`

`stack.py` (47 KB) and `dirty.py` are not here. `dirty.py` imports `address.py` and `stack.py`,
so copying it would drag a return stack into a build that has none, and importing a stack this
build does not use would be a claim dressed up as a dependency.

What was taken from that package is its **rule**, quoted, not its code:

* "A returned thread must carry a strictly newer Bias; a stale or duplicate finish may not wake
  an unrelated caller." [THE_BUILD_RESTART_PLAN_20261016.md:69, as `stack.py` records it at
  line 54]
* a dirty child invalidates the whole ancestor line, and the invalidation has no undo
  (`dirty.py`'s `CANON_NO_UNDO`, and `retraction.py`'s reading of the same canon line — other
  depths, ancestors invalidated, siblings left valid).

The gate implements that rule with `bias.check_version_increase` (already in `the_loop`) and with
`retraction.is_dirty` (vendored), so both halves of the return rule are somebody else's tested
code rather than a restatement in `rpm_gate.py`.

## Was anything modified?

* `the_loop\*` — **no.** `the_loop` still sits where it was; this folder is a copy of it that
  was then edited.
* `dwp_engine\*`, `return_address\*`, `continuity_build_v3\*` — **no.** Only read.
* `the_loop_v2` — **yes, and only here.** `loop.py`, `test_all.py`, `README.md` and this file
  were rewritten in the copy, and `rpm_gate.py` was added.

## What is original to this folder

| file | what it is |
| --- | --- |
| `rpm_gate.py` | **the gate.** RPM decides PROCEED / REPAIR / REFUSE from the turn's cause. |
| `bias.py` | the working memory: named facts, one writer, a strictly increasing version, a digest — carried forward from `the_loop`, unmodified |
| `loop.py` | one turn: read, propose, observe, gate, disengage-or-continue; the gate is now the real one |
| `test_all.py` | the whole suite, plain Python, no pytest |
| `README.md` | the roles kept apart, what the gate decides and on what, the claim ceiling, every undecided line |
| `PROVENANCE.md` | this file |

## How to re-check all of it

```
cd C:\Users\wakil\Documents\Codex\2026-10-16\the_loop_v2
python -B test_all.py
```

The run prints the sha256 of all six copies before it prints any case result, so the numbers in
this file are visible in the output of every run rather than remembered by this file.
