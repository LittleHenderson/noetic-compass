# PROVENANCE — what was copied into `the_loop_v3`, from where, and what its bytes are

Built 2026-10-16 in `C:\Users\wakil\Documents\Codex\2026-10-16\the_loop_v3\`.
It is `the_loop_v2` copied forward with **one substitution**: the vendored engine is now
`dwp_engine_v2` instead of `dwp_engine`. `dwp_engine_v2` carries the owner's ruling of
2026-10-16 — `HORIZON = 12` (was 5) and a new `DESIRE_BOUND = 12` (canon bounds the loop
nowhere). Nothing else about the build changed: `bias.py`, `loop.py`, `asom.py`, `disengage.py`
and `test_all.py`'s cases are the same as `the_loop_v2`'s, and `rpm_gate.py` changed only where
the delegation required it (see "What was modified" below).

**Neither 12 is derived from canon.** The book says 5 and bounds the Desire loop nowhere. Both
numbers are the owner's ruling of 2026-10-16, recorded in the engine's own comments, and the
book's own sentence ("not an arbitrary performance cap, but a stability horizon") is kept beside
the ruling rather than replaced by it.

The test `the_copied_files_are_byte_identical_to_the_recorded_hashes` re-hashes every copy on
every run, requires each copy's digest to equal the `source sha256` recorded here, and — on a
machine where the source packages are still present — re-hashes the **source file itself** and
requires that too. So "nothing in the source packages was modified" is checked rather than
asserted. The source it re-hashes for the four engine modules is `dwp_engine_v2`, which is the
folder this build actually copied from.

## The hash is taken over NORMALIZED bytes, and this was a real false green

Fixed 2026-10-17, after Codex's audit.

As first written, this check hashed the **raw bytes** of each file. git normalizes CRLF to LF on
commit, so the raw sha256 of the same committed file differs between a Windows checkout (CRLF)
and a Linux one (LF). The suite therefore **passed on the Windows machine it was written on and
failed on Linux**. Codex ran it on AWS at commit `4cdcdbd5526ff42056318a136a0fbc52804f2ede` and
got exactly that: 7 packages passed, `the_loop_v3` failed 1 of 35, the recorded `asom.py` hash
matching the Windows checkout but not the committed Git blob, and normalizing the line endings
reproducing the Git blob exactly.

Every earlier "the_loop_v3 35/35" this build reported was true on Windows and **not** true on a
fresh Linux checkout. That is a false green, and calling it 35/35 without naming the platform was
wrong.

The check now hashes `sha256(bytes.replace(b"\r\n", b"\n"))` and the twelve recorded values
(`copy` and `source` for each of the six modules) are recomputed to match. A provenance check
must mean "these are the same file", not "these were checked out on the same operating system".

Verified by exporting the committed tree with LF endings and running the suite there, not only
in the Windows working copy.

## Copied from `continuity_build_v3` (as they already were in `the_loop`)

Source folder: `C:\Users\wakil\Documents\Codex\2026-10-16\continuity_build_v3\`
(that package reports 50 test cases passing; this build does not re-run its suite)

| copy | copied from | role in this build |
| --- | --- | --- |
| `asom.py` | `continuity_build_v3\asom.py` | **the readout.** The four-label gauge, used in stage 3 only. |
| `disengage.py` | `continuity_build_v3\disengage.py` | **the ladder.** The owner's four steps, run in stage 5 only when the gate cannot proceed. |

asom.py copy sha256: 6c8f964e7f031a1d3bdf9e6bcf1c4a72101a507bcf8cc6ad4fee28d0e4a6b4fd
asom.py source sha256: 6c8f964e7f031a1d3bdf9e6bcf1c4a72101a507bcf8cc6ad4fee28d0e4a6b4fd
disengage.py copy sha256: 78a73a853f920e9f819ceeeb272d21dd513c08ba7355254dd7db0dd5314add98
disengage.py source sha256: 78a73a853f920e9f819ceeeb272d21dd513c08ba7355254dd7db0dd5314add98

Both copies keep their own docstrings, their own claim ceilings and their own
`UNDECIDED IN DESIGN` notes exactly as written. They are not edited, not re-worded and not
re-wrapped, because an edited copy cannot be checked against the file it came from.

## Copied from `dwp_engine_v2`, read-only, into `dwp\`

Source folder: `C:\Users\wakil\Documents\Codex\2026-10-16\dwp_engine_v2\`
(that package reports 33 test cases passing; this build does not re-run its suite)

`dwp_engine_v2` is `dwp_engine` (v1) with exactly two changes, both from the owner's ruling of
2026-10-16: `depth.py`'s `HORIZON` moved from 5 to 12, and `dwp.py` gained `DESIRE_BOUND = 12`
with the `DesireBoundExhausted` refusal and the `DesireLoop` runner that counts cycles against it.
`retraction.py` and `lacunarity.py` are untouched by the ruling and are byte-identical to v1's.

| copy | copied from | role in this build |
| --- | --- | --- |
| `dwp\dwp.py` | `dwp_engine_v2\dwp.py` | **the three functors and the loop bound.** `dwp.resolve` dispatches a block to Phi_D / Phi_W / Phi_P; `DESIRE_BOUND = 12` bounds the Desire loop and the 13th cycle is refused as `DESIRE_BOUND_EXHAUSTED`. |
| `dwp\depth.py` | `dwp_engine_v2\depth.py` | **the horizon.** `HORIZON = 12` (the owner's ruling), `check_depth`, `flatten`. The gate reads the number from here and writes none of its own. |
| `dwp\retraction.py` | `dwp_engine_v2\retraction.py` | **the dirty propagation.** `mark_dirty_upward`, `is_dirty`. Byte-identical to `dwp_engine`'s copy. |
| `dwp\lacunarity.py` | `dwp_engine_v2\lacunarity.py` | resolution lacunarity. Copied because it is part of the engine package; **nothing in this build imports it**, and the gate never asks it anything. Byte-identical to `dwp_engine`'s copy. |

dwp.py copy sha256: cde1a1c4d0cc8198b83fd12db13ca80a721491e4eb2aabf3df8b6d32b4a9bbca
dwp.py source sha256: cde1a1c4d0cc8198b83fd12db13ca80a721491e4eb2aabf3df8b6d32b4a9bbca
depth.py copy sha256: 92e06ded47fe550b559ebf8b37a39751b384f1c84e1ad600cfca50d930e7b4ab
depth.py source sha256: 92e06ded47fe550b559ebf8b37a39751b384f1c84e1ad600cfca50d930e7b4ab
retraction.py copy sha256: ec979b1ec1c1f36ca9fb7985e586445be8123813f4aee0b5f97d52a3b123c46e
retraction.py source sha256: ec979b1ec1c1f36ca9fb7985e586445be8123813f4aee0b5f97d52a3b123c46e
lacunarity.py copy sha256: d393a46d35575ab4b9cbc4476305f51d28f7fb04824a24e27e044891a36b2634
lacunarity.py source sha256: d393a46d35575ab4b9cbc4476305f51d28f7fb04824a24e27e044891a36b2634

**Not one byte of these four files changed on the way in.** They keep their own
`UNDECIDED IN CANON (U1)...(U11)` notes (U11 is the horizon-number question the ruling answers),
their own `CANON_*` quotations — including canon's own "5", unedited — their own claim ceilings
and their own absolute imports (`import dwp`, `from dwp import ...`). That is why `rpm_gate.py`
loads them **by path** from `dwp\` and registers them under their own module names before their
bodies run: so the copies can be imported without being edited, and so nothing this build does
can reach a different copy of the engine.

`dwp_engine_v2\test_all.py` and `dwp_engine_v2\README.md` were **not** copied. This build does
not re-run that suite and makes no claim about it, beyond reporting the count it claims.

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

* `dwp_engine\*`, `the_loop_v2\*`, `return_address\*`, `continuity_build_v3\*` — **no.** Only
  read. Each still sits where it was, unchanged, and each still passes its own suite.
* `dwp_engine_v2\*` — **yes, in that folder only, and only as the ruling requires**:
  `depth.py`'s `HORIZON` 5 → 12, `dwp.py`'s new `DESIRE_BOUND = 12` with the refusal and the
  loop runner, plus the comments that mark both as the owner's ruling and the test cases that
  prove depth 13 unreachable and the loop bound exact. `retraction.py` and `lacunarity.py` are
  untouched.
* `the_loop_v3` — **yes, and only here.** `PROVENANCE.md`, `README.md` and `test_all.py` were
  rewritten in the copy; `rpm_gate.py` changed only where the delegation required it: a
  `DESIRE_BOUND_EXHAUSTED` code, one `except dwp.DesireBoundExhausted` clause that returns a
  REFUSE verdict (it must sit above the `ArchitectureViolation` catch, or the bound would become
  a broken-contract error instead of a decision), and the comments that name both numbers. Its
  horizon arithmetic is unchanged: it still reads `depth.HORIZON` and writes no number.
* `the_loop_v2\*` — **no.** It is where this folder came from, and it stays as it was.

## What is original to this folder

| file | what it is |
| --- | --- |
| `rpm_gate.py` | **the gate.** RPM decides PROCEED / REPAIR / REFUSE from the turn's cause. |
| `bias.py` | the working memory: named facts, one writer, a strictly increasing version, a digest — carried forward from `the_loop`, unmodified |
| `loop.py` | one turn: read, propose, observe, gate, disengage-or-continue; the gate is the real one |
| `test_all.py` | the whole suite, plain Python, no pytest |
| `README.md` | the two numbers and their two jobs, the roles kept apart, what the gate decides and on what, the claim ceiling, every undecided line |
| `PROVENANCE.md` | this file |

## How to re-check all of it

```
cd C:\Users\wakil\Documents\Codex\2026-10-16\the_loop_v3
python -B test_all.py
```

The run prints the sha256 of all six copies before it prints any case result, so the numbers in
this file are visible in the output of every run rather than remembered by this file.
