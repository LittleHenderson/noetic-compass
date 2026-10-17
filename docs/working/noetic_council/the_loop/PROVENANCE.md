# PROVENANCE — what was copied into `the_loop`, from where, and what its bytes are

Built 2026-10-16 in `C:\Users\wakil\Documents\Codex\2026-10-16\the_loop\`.

Nothing in either source package was modified. Both copies were made with a byte-for-byte
file copy, and the `copy sha256` and `source sha256` values below are equal for each file.
The test `the_copied_files_are_byte_identical_to_the_recorded_hashes` re-hashes both copies on
every run and fails if a single byte moves.

## Copied from `continuity_build_v3`

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
re-wrapped, because an edited copy cannot be checked against the file it came from. Their own
claim ceilings still hold: the ASOM copy still says it is a diagnostic display that must never
be used to block or allow an operation, and the disengage copy still says it carries no
language across anything.

## What was taken from `continuity_build_v3` but NOT copied

Everything else in that package is left where it is and is not needed here:
`atlas_adapter.py` and the read-only `real_atlas/` model, the `crossings.py` crossing record,
`stations.py` (S0-S6), `seams.py`, `continuity.py` and `provenance.py`. This step of the build
plan joins a Bias, a proposal, a readout, a gate and a ladder; it does not touch an atlas, a
station, a seam or a crossing record, so copying those in would import a claim this step does
not make and cannot test.

## Nothing was copied from `dwp_engine`, and that is deliberate

Source folder: `C:\Users\wakil\Documents\Codex\2026-10-16\dwp_engine\`
(that package reports 30 test cases passing; this build does not re-run its suite)

`dwp.py` (the D/W/P resolution functors), `depth.py` (`HORIZON = 5`, `flatten`),
`retraction.py` and `lacunarity.py` are **not** in this folder, are not imported, and are not
reachable from any module here.

The reason is the role separation this step exists to keep. RPM is the gate. The gate in this
build is a **stub** — it always proceeds and it says so in its own reason text. Wiring RPM is a
later step of the build plan, and importing the RPM engine now would put a real prerequisite
resolution behind a gate that is supposed to be a placeholder, which would make the one claim
this build is allowed to make ("nothing real is decided here") false.

So the gate here takes its verdict from a callable, and the place where a real RPM call belongs
is a single line in `loop.py`, marked as such in the code and named in the README's "what is
still not built" list. No piece of the D/W/P chain is needed to draw the outline of that line,
and no piece of it is copied in.

## What is original to this folder

| file | what it is |
| --- | --- |
| `bias.py` | the working memory: named facts, one writer, a strictly increasing version, a digest |
| `loop.py` | one turn: read, propose, observe, gate, disengage-or-continue |
| `test_all.py` | the whole suite, plain Python, no pytest |
| `README.md` | the three roles stated separately, the claim ceiling, every undecided line |
| `PROVENANCE.md` | this file |

## How to re-check all of it

```
cd C:\Users\wakil\Documents\Codex\2026-10-16\the_loop
python -B test_all.py
```

The run prints the sha256 of both copies before it prints any case result, so the numbers in
this file are visible in the output of every run rather than remembered by this file.
