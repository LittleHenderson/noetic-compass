# Continuity build — stations, seams, path, and the disengage ladder

Built 2026-10-16 in `C:\Users\wakil\Documents\Codex\2026-10-16\continuity_build\`.

The design has existed since 2026-10-15 and was never built. This is the build. Five modules,
standard library only. No torch. No numpy. No network. No AWS. No spend.

## The claim ceiling

Verbatim, and it is the whole ceiling:

```
MECHANISM ONLY. NOT THE BRAIN FEATURE. THE ATLAS LINK IS NOT BUILT.
```

## What this build does not connect to

This build does **not** connect to the Recursive Possibility Atlas. There is no atlas object,
no atlas entry, and no call into any atlas code anywhere in these five modules. The station
called S0 is a name for where a thought starts; it is not an atlas position.

The design says any claim that language was carried across an RPA is **NOT LICENSED**. That
was true before this build and it is still true after it. Nothing here changes it. The open work
is still open: how atlas entries attach to a CJT, to Bias, and to an RPM link is undecided in
the packet, and the owner's ruling says so in its own words.

So this build cannot claim continuity across an RPA, and it does not claim it.

## What each module does, and does not do

Every module has a docstring with the same two headings. This is the short version.

### `stations.py` — the station model

**Does.** Names the seven station kinds from STATIONS.md: S0 thought head, S1 CJT trigger,
S2 CJT Bias, S3 CJT arrival, S4 operating point, S5 RPM link, S6 next stage. Holds one frozen
record per kind. Carries the crossing record — the thought, the station, the tick, the parsed
head, the leading register, and the content — plus the point, the FORM gap flag, the RPM depth,
and the next-station pointer that this build needs. Enforces the depth cap of 5 nested levels.
Builds a valid 40-state point from named weights, using LM-T2's floor of 1/400 per state.

**Does not.** Does not invent a threshold. Does not parse or render language. Does not compute
an ASOM word. Does not connect to the Atlas.

### `seams.py` — the seam rule

**Does.** Implements the rule exactly as CONTINUITY.md states it. A seam needs **both** the
parsed head (or the leading register when there is no head) **to change**, **and** the step to
reach the threshold. Measures the step as the Fisher-Rao distance on the open simplex,
`d(p,q) = 2*arccos(sum(sqrt(pk*qk)))`, and cross-checks it with the stable form
`4*arcsin(sqrt(h/2))`. Refuses any point that is not strictly positive, 40 states long, and
summing to 1 within 1e-9. Refuses to interpolate across a seam. Holds two heads as two points
labelled `CO_PRESENT`.

**Does not.** Does not decide a threshold; with no threshold supplied it refuses rather than
defaults. Does not parse language. Does not average two heads, and there is no interpolator in
the file at all.

### `continuity.py` — the path builder

**Does.** Accumulates the crossings of one thought and gives: `points()`, one point per crossing
that has a point; `form_gaps`, the count of crossings that have none; `anchor()`, the S0 point;
`displacement()`, the distance from the anchor; `seams()`, the seams found with their reasons;
`seam_checks()`, every neighbouring pair with the reason it did or did not fire; `summary()`,
the counts; and `drift_checks()`, the drift reading, reported and never scored. Refuses a
crossing whose head differs from the thought's head, because a new head is a new thought.

**Does not.** Does not build a point from content — the tracker that does that is not in this
build. Does not decide a threshold. Does not find seams across thoughts.

### `provenance.py` — FOLLOWED, CREATED, ATTEMPTED

**Does.** Classifies each crossing by where the next pointer came from. `FOLLOWED` when the
pointer was already in the record before this tick. `CREATED` when it was written this tick by
a faculty or an injection and its continuation is later admitted or answered. `ATTEMPTED` when
it was written this tick and the continuation is refused or still held open. Logs the writer —
the faculty's Φ word or the injection's turn index. Provides `assert_shuffled_control()`, which
raises if a shuffled injection produced any `CREATED`.

**Does not.** Does not decide the cases the design left open; it refuses them as
`PROVENANCE_UNDECIDABLE`. Does not show that anything was thought up — these three are
bookkeeping words, and the design says so itself.

### `disengage.py` — the owner's ladder

**Does.** Runs the four steps in order: `NOT_DECLARED`, `CONFUSED`, `ASK_CLARITY`,
`DISENGAGE`. Never fills the gap. Names the actual missing item in the ask. Refuses a disengage
with no reason. Goes terminal after the disengage: a further call returns `ALREADY_DISENGAGED`
and records nothing. Writes one receipt line per step with the step, the gap and the reason.
`run_ladder(gap)` walks the full escalation. `run_ladder(gap, info_provided=True)` shows the
information arriving and the turn returning to normal without disengaging.

**Does not.** Does not parse English, decide what the gap is, or check an answer. Does not map
itself onto the Noetics. Does not retry after a disengage.

## How to run the tests

```
cd C:\Users\wakil\Documents\Codex\2026-10-16\continuity_build
python -B test_all.py
```

One line printed per case, then a total. Exit code 0 when all pass, 1 when any fails. No pytest
needed. The whole run takes well under a second and touches nothing outside this folder.

## The frozen station-kind table

Seven kinds, one frozen record each, hashed over its own canonical JSON.

```
sha256: 7b9f2e1ad8865deeb6df5abe940ad87d39305e72fcfdfeebcb1de48caecb10e3
```

Every kind's seam threshold, tone threshold and drift threshold is `None` and every kind is
marked `THRESHOLD_UNDECIDED`, because STATIONS.md gives no number for any kind. The only
thresholds in the packet are the LM-T2 dialogue numbers — seam `0.841069956`, tone
`1.227592661`, drift `0.984979914` — and CONTINUITY.md:35-37 says they are not reused blindly.
They are recorded in `DIALOGUE_THRESHOLDS_NOT_REUSED` with `licensed_for_station_kinds = False`.

The test file re-hashes the exposed table and fails if it has changed.

## Every UNDECIDED IN DESIGN line

Each line below is copied exactly from the code, where it is marked with the
`# UNDECIDED IN DESIGN:` prefix. Nothing here was decided quietly: where the design was silent,
the build refuses and says why.

1. `stations.py` — what theta_seam, theta_tone and theta_drift are for each station kind -- STATIONS.md:145-292 gives no number for any kind, and CONTINUITY.md:35-37 forbids reusing the dialogue numbers.

2. `stations.py` — what S0 holds as content -- OWNER_RULING_RPA_ATLAS_20261015.md:35-38 says how an atlas entry attaches to a CJT, to Bias and to an RPM link is not decided by that record.

3. `stations.py` — which ASOM reading is licensed at S4 -- CONTINUITY_AND_DISENGAGE_20261016.md:38 says the ASOM ruling has not been located and must not be invented, so S4 stores its two axes and no word.

4. `stations.py` — whether a crossing at S0 or S6 may carry a nested depth above 0 -- STATIONS.md:143 says nested levels repeat S1-S5 inside S5 and does not say whether a nested thought has its own head and next stage; this build permits any station at depth 1-5 and only caps the level.

5. `seams.py` — which register leads when a tag is a set |<...> -- CONTINUITY.md:30 says "the leading register" and never says which one leads when several are named; this build takes the first in source order.

6. `seams.py` — what a station-level tone seam compares, and against which threshold -- LM-T2 counts tone seams beside subject seams (CONTINUITY.md:16-17) and the packet gives no station-level tone rule; this build compares the leading register and nothing else.

7. `continuity.py` — what the anchor is when the S0 tap has no point (a FORM gap at the head) -- "Anchor of a thought = its S0 point" (CONTINUITY.md:29) does not cover that case, so this build refuses instead of choosing a fallback.

8. `continuity.py` — how a crossing is addressed when the same station code occurs twice (a nested level inside S5, or the other route of an ALT order) -- the packet gives no addressing scheme, so this build refuses the ambiguous name and asks for an index.

9. `provenance.py` — which word applies to a pointer written this tick by the drive loop's arm rule -- CONTINUITY.md:48-50 names only "a faculty or an injection" as the writer of a CREATED pointer, while CONTINUITY.md:86 gives the arm rule the choice of the next focus; this build refuses rather than choose a word for it.

10. `provenance.py` — what makes two pointer records the same pointer -- CONTINUITY.md:48 says only "the pointer to the next station", so this build matches on the same thought, the same station, the same next station, and a pointer_id when one is given.

11. `provenance.py` — which word applies to a crossing with no next-station pointer at all (the last station of a thought) -- the three words at CONTINUITY.md:46-50 do not cover it, so this build refuses rather than invent a fourth.

12. `provenance.py` — how late a continuation may arrive and still count as CREATED -- CONTINUITY.md:49 says "later admitted or answered" and gives no window or end-of-record rule, so this build treats an outcome that is not on record as still open at the end (ATTEMPTED).

13. `disengage.py` — whether the NOT DECLARED step speaks, and in what words -- the owner's ladder gives no sentence for it and CONTINUITY_AND_DISENGAGE_20261016.md:113-116 maps only step 2 onto "I cannot tell."; this build records the step in the receipt and says nothing.

14. `disengage.py` — what content the disengage reason must carry -- CONTINUITY_AND_DISENGAGE_20261016.md:122 requires "no, because X" and states no required fields; this build refuses only an empty reason.

15. `disengage.py` — whether a step may be skipped (for example disengage without asking) -- the ladder is given as an escalation and skipping is neither allowed nor forbidden; this build only ever takes the next step in order.

16. `disengage.py` — whether the same turn may re-enter the ladder after the information is supplied -- the packet says supplying it returns to normal and does not say whether a second gap in the same turn starts the ladder again; this build leaves the ladder resolved and starts no second one.

## What is not in this build

- No parser and no renderer. `parse(render(C)) == C` is not run anywhere here.
- No tracker. The point for a station is handed in by the caller, not derived from content.
- No brain, no faculty, no drive loop, no receipts from a writer.
- No Atlas, no atlas entry, no atlas adapter.
- No learned parameters. Every rule here is programmed.
- No scoring, no thresholds, no verdicts.
- No network, no cloud, no spend.

## One sentence on what this build cannot claim

It shows the mechanisms of the design working on inputs a person supplies, and it cannot claim
that language, meaning, or a continuity of thought was carried across the Recursive Possibility
Atlas — that link is not built, the design says the claim is NOT LICENSED, and this build does
not change that.
