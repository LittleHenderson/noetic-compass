# Continuity build v2 — stations, seams, path, the disengage ladder, and the atlas

Built 2026-10-16 in `C:\Users\wakil\Documents\Codex\2026-10-16\continuity_build_v2\`, as a copy of
`C:\Users\wakil\Documents\Codex\2026-10-16\continuity_build\` with the Recursive Possibility Atlas
added to it. The first build is untouched.

The design has existed since 2026-10-15 and was never built. This is the build. Seven modules,
standard library only. No torch. No numpy. No network. No AWS. No spend.

## The claim ceiling

Verbatim, and it is the whole ceiling:

```
MECHANISM ONLY. THE ATLAS IS A MINIMAL OBJECT, NOT HELM VISION ABILITY 6 AT FULL SCOPE. NO LANGUAGE PASSED ACROSS IT.
```

The previous ceiling — `MECHANISM ONLY. NOT THE BRAIN FEATURE. THE ATLAS LINK IS NOT BUILT.` — is
superseded, and only in one respect: the atlas link now exists as a minimal object. The rest of it
stands word for word. Nothing here is the brain feature.

## What the atlas build now allows, and what it still cannot claim

**What it now allows.** The owner's order was "LIFT THAT RESTRICTION ON RPA ADD IT". The
restriction was that S0 was only a station name and the atlas did not exist in code. Two things
are now true that were not true before.

1. **S0 can be an atlas position.** `atlas.py` builds a Recursive Possibility Atlas: nodes of
   exactly four kinds (`FACT`, `GUESS`, `POSSIBILITY`, `CONTEXT`, kept distinct as HELM vision
   ability 6 requires), directed edges carrying a relation name, sub-atlases at entry ids so the
   atlas is recursive, and one frozen sha256 over the whole thing. `stations.bind_s0_to_atlas()`
   binds S0 to one entry and `continuity.anchor()` then returns **that entry's digest** instead of
   the S0 point. A path with no atlas bound behaves exactly as the first build did.
2. **A thought can travel across atlas nodes and edges.** `crossings.py` defines the CJT as the
   crossing and not the node: a `Crossing` carries the node it left, the edge it took, the node it
   arrived at, the tick, the thought, and its own digest. `crossings.cross()` accepts it only when
   the edge really does join those two nodes. `continuity.atlas_path()` returns the ordered node
   digests visited, and `continuity_summary()` reports `atlas_nodes_visited`,
   `atlas_edges_crossed` and `atlas_kind_pollution`.

**What it still cannot claim.** This is the honest ceiling, and each line is a fact about the code,
not a mood:

- It is **a minimal object, not HELM vision ability 6 at full scope**. Ability 6 asks for an atlas
  that *organizes retained knowledge and possibilities*. What exists here organizes nothing: no
  retention, no retrieval, no narrowing, no ranking, no rebuilding after restore, no comparison of
  answers with and without the atlas. It is a bounded, hashed graph with a kind rule.
- **No language was passed across it.** Not one case in the test file moves a word. The atlas
  payloads are short data dictionaries; nothing is parsed, rendered, tokenised or interpreted. The
  design's rule stands untouched: any claim that language rode an RPA is **NOT LICENSED**.
- **It is not the CAS-RPU atlas model.** That model (branch `codex/helm-rpa-recorded-run-20260922`,
  commit `eb99855`) uses different status words — OBSERVED / HYPOTHETICAL / UNKNOWN / REJECTED /
  VERIFIED — and a different snapshot. The owner's ruling says the next circuit test should *reuse*
  that model, and the vision forbids building a parallel memory framework. This build says plainly
  that it did neither: it is a smaller object with its own four kinds, and the mapping between the
  two vocabularies is not done here. That conflict is recorded as open work, not as settled.
- **Nothing is promoted.** A `POSSIBILITY` or a `GUESS` never becomes a `FACT`; there is no
  function anywhere that changes a node's kind, and an edge that joins a `FACT` to a `GUESS` is
  refused unless the caller declares it.
- **The attachment question the owner left open stays open.** How atlas entries attach to a CJT, to
  Bias and to an RPM link is still not decided by the ruling, and this build does not decide it. S0
  is the one station the ruling moved, and S0 is the one station bound here.
- **No numbers were invented.** The maximum sub-atlas depth, the relation vocabulary, and who may
  declare a cross-kind edge are all undecided in the design, and all refused rather than defaulted.

So this build can now say: **a thought can cross from one atlas node to another along an edge, and
S0 can be an atlas position.** It cannot say that anything was carried, understood, or spoken.

## What each module does, and does not do

Every module has a docstring with the same two headings. This is the short version.

### `stations.py` — the station model

**Does.** Names the seven station kinds from STATIONS.md: S0 thought head, S1 CJT trigger,
S2 CJT Bias, S3 CJT arrival, S4 operating point, S5 RPM link, S6 next stage. Holds one frozen
record per kind. Carries the crossing record — the thought, the station, the tick, the parsed
head, the leading register, and the content — plus the point, the FORM gap flag, the RPM depth,
the next-station pointer, and (new in v2) an optional `atlas_entry`. Enforces the depth cap of 5
nested levels. Builds a valid 40-state point from named weights, using LM-T2's floor of 1/400 per
state. `bind_s0_to_atlas(atlas, entry_id)` returns the S0 position bound to one atlas entry, and
refuses a missing entry as `ATLAS_ENTRY_NOT_FOUND`.

**Does not.** Does not invent a threshold. Does not parse or render language. Does not compute
an ASOM word. Does not bind S1-S6 to the atlas, and does not open, extend or write an atlas — it
reads the entry's id, sort and digest and copies them.

### `atlas.py` — the Recursive Possibility Atlas (new in v2)

**Does.** Holds nodes of exactly four kinds — `FACT`, `GUESS`, `POSSIBILITY`, `CONTEXT` — each
with a stable id, a canonical JSON payload, and a sha256 over {id, kind, payload}, so two nodes
are the same node only if their digests match. Holds directed edges with a relation name and their
own digests, and no self-loops. Holds sub-atlases at entry ids, so an entry may be a sub-atlas and
the atlas is recursive, under a maximum depth the caller declares. Refuses a duplicate id with a
different digest, an edge naming a missing node, a self-loop, and a cycle unless it is marked
allowed. `entry()`, `entry_digest()`, `entry_sort()` and `neighbours()` read it; `frozen_digest()`
is one sha256 over the whole atlas in canonical order, sub-atlases included.
`kind_pollution_report()` lists every edge joining two different kinds and raises `KIND_POLLUTION`
when one of them was not declared `cross_kind_declared=True`.

**Does not.** Does not reuse the CAS-RPU atlas model, whose statuses are
OBSERVED / HYPOTHETICAL / UNKNOWN / REJECTED / VERIFIED; the mapping between the two vocabularies
is not done here. Does not promote a possibility or a guess to a fact. Does not retain, retrieve,
narrow, rank or rebuild anything. Does not decide a maximum depth, a relation vocabulary, or who
may declare a cross-kind edge. Does not hold language.

### `crossings.py` — the CJT crossing (new in v2)

**Does.** Defines the CJT as the crossing, not the node: a `Crossing` carries the node it left,
the edge it took, the node it arrived at, the tick, the thought, and a digest over all of them,
plus the same edge, in one act, `cross(atlas, from_node_id, edge, to_node_id)`, which refuses any
edge that is not held by the atlas, any edge that does not start at `from_node_id`, any edge that
does not end at `to_node_id`, and any undeclared crossing between two kinds. `is_cjt()` is True
only for a Crossing.

**Does not.** Does not build or change an atlas. Does not decide what a tick is or whether an
atlas crossing spends one. Does not say what a crossing means, or whether the arriving node is
true. Does not carry language.

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
the file at all. Does not touch the atlas.

### `continuity.py` — the path builder

**Does.** Accumulates the crossings of one thought and gives: `points()`, one point per crossing
that has a point; `form_gaps`, the count of crossings that have none; `anchor()`, which is the S0
point **or, when S0 is bound to an atlas entry, that entry's digest**; `displacement()`, the
distance from the anchor; `seams()`, the seams found with their reasons; `seam_checks()`, every
neighbouring pair with the reason it did or did not fire; `summary()`, the counts; and
`drift_checks()`, the drift reading, reported and never scored. New in v2 it also accepts a
sequence of `Crossing` objects, refuses one that does not join end to end to the last, and reports
`atlas_path()`, `atlas_nodes_visited`, `atlas_edges_crossed` and `atlas_kind_pollution`. Refuses a
crossing whose head differs from the thought's head, because a new head is a new thought.

**Does not.** Does not build a point from content — the tracker that does that is not in this
build. Does not decide a threshold. Does not find seams across thoughts. Does not measure a
distance from an atlas digest: it refuses as `ANCHOR_IS_ATLAS_DIGEST` rather than inventing a
number. Does not hold or change an atlas.

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
cd C:\Users\wakil\Documents\Codex\2026-10-16\continuity_build_v2
python -B test_all.py
```

One line printed per case, then a total. Exit code 0 when all pass, 1 when any fails. No pytest
needed. The whole run takes well under a second and touches nothing outside this folder.

The run also prints the frozen sha256 of a small report atlas it builds, plus that atlas's counts.
That digest is a number the run states, not a number this file remembers, so it cannot go stale.

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

17. `stations.py` — what an S0 bound to a sub-atlas holds as its anchor digest -- a plain node entry has a node digest and a sub-atlas entry has the frozen digest of its whole subtree, and no source says whether those two sorts of digest may serve as one kind of anchor; this build copies whichever digest the bound entry has and records which sort it was.

18. `atlas.py` — what the maximum depth of sub-atlas nesting is -- CONTINUITY.md:28 and STATIONS.md:143 give a cap of 5 for NESTED RPM LEVELS and the packet gives no number for ATLAS nesting, so this build invents none: the Atlas class refuses to be built without a caller-declared max_depth and never defaults it.

19. `atlas.py` — which relation names an atlas edge may carry -- no source in the packet names an atlas relation vocabulary, so this build copies the caller's relation name byte for byte and checks it against no list.

20. `atlas.py` — who may declare a cross-kind edge legal, and on what evidence -- the vision says facts and guesses stay distinct and names no declaring act, so this build accepts an explicit cross_kind_declared=True from the caller, records it on the edge and inside the edge's digest, and never infers it.

21. `crossings.py` — what tick an atlas crossing is stamped with, and whether an atlas crossing spends a tick at all -- CONTINUITY.md:21 indexes a thought's path by station and tick and gives no tick semantics for a crossing between atlas nodes (the tick is described there as a station boundary), so this build takes the tick from the caller and never stamps or increments one.

Items 17-21 are the lines the atlas build added. Items 1-16 are the lines the first build
carried, unchanged.

## What is not in this build

- No parser and no renderer. `parse(render(C)) == C` is not run anywhere here.
- No tracker. The point for a station is handed in by the caller, not derived from content.
- No brain, no faculty, no drive loop, no receipts from a writer.
- No reuse of the CAS-RPU atlas model (`rpa_model.py` at `eb99855`), and no mapping between its
  status words and the four kinds used here — that work is not done, and the conflict is stated
  in the section above rather than papered over.
- No retention, retrieval, narrowing, ranking or restore in the atlas. It is a bounded hashed
  graph with a kind rule, and nothing in it learns or remembers anything across a restart.
- No learned parameters. Every rule here is programmed.
- No scoring, no thresholds, no verdicts.
- No network, no cloud, no spend.

## One sentence on what this build cannot claim

It shows the mechanisms of the design working on inputs a person supplies, it shows a thought
crossing from one atlas node to another with S0 as an atlas position, and it cannot claim that
language, meaning, or a continuity of thought was carried across the Recursive Possibility Atlas
— no language passed across it, the design says that claim is NOT LICENSED, and this build does
not change that.
