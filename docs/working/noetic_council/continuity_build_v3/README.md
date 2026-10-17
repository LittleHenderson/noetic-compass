# Continuity build v3 — stations, seams, path, the disengage ladder, and the REAL atlas

Built 2026-10-16 in `C:\Users\wakil\Documents\Codex\2026-10-16\continuity_build_v3\`, as a copy of
`C:\Users\wakil\Documents\Codex\2026-10-16\continuity_build_v2\` with one change and one deletion:

- **one change:** S0 and the CJT crossing now bind to the **real** CAS-RPU Recursive Possibility Atlas
  that already existed in the repository, copied in read-only under `real_atlas/`;
- **one deletion:** the stand-in atlas (`atlas.py`) built by mistake in v2 is **deleted**.

v2 and every other folder are untouched. Standard library plus the real model's own
dependencies only. No torch. No numpy. No network. No AWS. No spend.

## The claim ceiling

Verbatim, and it is the whole ceiling:

```
MECHANISM ONLY. THE ATLAS IS A MINIMAL OBJECT, NOT HELM VISION ABILITY 6 AT FULL SCOPE. NO LANGUAGE PASSED ACROSS IT.
```

## What is now REAL

The owner's ruling is the reason this build exists at all: the vision says "Do not create a
parallel memory framework, RPA build or roadmap because a schema needs a compatible extension",
and "the next circuit test reuses that atlas model at S0; it does not build a new one". v2 broke
that rule by building a smaller atlas of its own. v3 removes it and uses the model that already
existed.

1. **The atlas is the real model.** Six files were extracted from branch
   `codex/helm-rpa-recorded-run-20260922`, commit
   `eb9985566bd11a89f485d627186ef0efa7177f02`, without switching branches, and copied byte for
   byte into `real_atlas/`. `real_atlas/PROVENANCE.md` states the source path, the size and the
   sha256 of each one. `atlas_adapter.verify_real_model()` re-hashes all six on every test run
   and refuses if one byte moved. The measured sha256 of the model itself is
   `rpa_model.py` = `323a53b951644a93603cd2f56204fd5a038a3161f4778e28777e650a4f966f01`.
2. **S0 anchors on a real region digest.** `stations.bind_s0_to_atlas(snapshot, node_id)` returns
   an `S0Position` whose `entry_digest` **is** the real `AtlasNode.region_digest()` of that node
   — a sha256 the real model computes over the node's id, its context and its members. The test
   `s0_anchor_is_the_real_node_region_digest` recomputes that value with the real model's own
   hasher and requires the three numbers to be equal. `continuity.anchor()` returns it through
   `atlas_adapter.anchor_from_binding`, which is the only place the anchor rule lives.
3. **A crossing carries the real link type and both real digests.** `crossings.Crossing` holds
   the real `AtlasNode` at each end and the real `AtlasLink` it travelled, so `relation` is a
   real `LinkType` value (`contains_part`, `refines_state`, `reachable_via`, `overlaps_with`,
   `references_same_idea`), and `from_digest` / `to_digest` are the two real region digests.
   `cross()` refuses a link the real snapshot does not hold, a link that does not join those two
   nodes, and an undeclared crossing between two sorts.
4. **Glue-back is the real model's decision.** `atlas_adapter.glue_back(nodes)` calls the real
   `compatibility(nodes)` and the real `certify_overlap(nodes, witness)` and reports both
   answers. `glue_back_ok(nodes)` is True only when both pass. **There is no glue rule in this
   build**: no field comparison, no overlap test, no witness choice. The test
   `glue_back_is_decided_by_the_real_compatibility` proves that by substituting the two real
   functions and watching the adapter's answer follow them.
5. **A refusal is surfaced, not swallowed.** When the real model refuses — two regions with no
   common member, fewer than two views, an object that is not a real `AtlasNode` — the refusal
   comes out as `atlas_adapter.AtlasAdapterRefusal` with code `REAL_MODEL_REFUSAL` carrying the
   real model's own sentence. A real *negative* answer (conflicting field values) is reported as
   a report with `ok is False`, and is a different thing from a refusal. Both are tested.

## What is now DELETED, and why nothing else needed it

`atlas.py` is **deleted from v3**. It was the parallel atlas: its own four kind words
(`FACT` / `GUESS` / `POSSIBILITY` / `CONTEXT`), its own node digest over `{id, kind, payload}`,
its own edge records with a declaration flag, and its own sub-atlas recursion. Keeping it beside
the real model would have left two atlases in one folder, which is the thing the ruling forbids.

Nothing else needed it. Its only importers were `crossings.py`, `stations.py` and `test_all.py`,
and all three were rewritten to use `atlas_adapter` instead. The test
`the_stand_in_atlas_is_gone_and_s0_refuses_it` checks four things: the file is absent, no module
in the build imports a module named `atlas`, a module named `atlas` is not importable, and an
object that imitates the old stand-in (`entry_digest`, `entry_ids`, `entry_sort`,
`frozen_digest`) is refused as `BAD_ATLAS` by `bind_s0_to_atlas` and as `BAD_SNAPSHOT` by
`atlas_adapter.bind_s0`.

Two consequences are stated plainly rather than hidden:

- **The four kind words are gone from the code.** The real model's own vocabulary is
  `NodeKind` (idea context / state / region / evidence) and `NodeStatus` (observed / hypothetical
  / unknown / rejected / verified). This build renames neither. Where the vision's "facts,
  guesses and contexts stay distinct" rule is still enforced, it is enforced over the real pair
  `(kind, status)`, which this build calls a node's **sort**.
- **The real model has no sub-atlas.** `AtlasSnapshot` holds nodes, links and overlap
  certificates, and one sort of entry: a node. So the v2 questions "how deep may a sub-atlas
  nest" and "what does an S0 bound to a sub-atlas anchor on" no longer exist. They are removed
  rather than answered.

## What each module does, and does not do

Every module has a docstring with the same two headings. This is the short version.

### `atlas_adapter.py` — the one bridge to the real model (new in v3)

**Does.** Imports `real_atlas/rpa_model.py` and gives the build four things:
`bind_s0(snapshot, node_id)` → an `S0Anchor` whose `region_digest` is the real node's own;
`anchor_from_binding(binding)` → the one anchor rule; `cross(...)` → a `CrossingRecord` holding
the real nodes and the real link; and `glue_back` / `glue_back_ok` → the real `compatibility()`
and `certify_overlap()` answers. Also `verify_real_model()`, which re-hashes the six copied files.

**Does not.** Does not define an atlas, a node, a link, a kind, or a digest scheme. Does not
decide glue-back. Does not promote a node's status. Does not copy live objects out: what leaves
is a frozen record of ids, digests, kind and status words, and counts.

### `stations.py` — the station model

**Does.** Names the seven station kinds from STATIONS.md. Holds one frozen record per kind.
Carries the crossing record with its point, FORM gap flag, RPM depth, next-station pointer, and
an optional `atlas_entry`. Enforces the depth cap of 5 nested levels. Builds a valid 40-state
point from named weights with the LM-T2 floor of 1/400 per state.
`bind_s0_to_atlas(snapshot, node_id)` returns the S0 position bound to a real atlas node and
refuses a missing node as `ATLAS_ENTRY_NOT_FOUND`.

**Does not.** Does not invent a threshold. Does not parse or render language. Does not compute
an ASOM word. Does not bind S1-S6 to the atlas. Does not hold, open, extend or build an atlas:
it reads the real node's kind, status and region digest and copies them.

### `crossings.py` — the CJT crossing

**Does.** Defines the CJT as the crossing, not the node: a `Crossing` carries the real node it
left, the real link it took, the real node it arrived at, the tick, the thought, and a digest
over the two region digests, the link, the tick, the thought and the declaration. `cross(...)`
accepts it only when the real snapshot holds that link and the link really joins those two nodes.
`is_cjt()` is True only for a Crossing.

**Does not.** Does not build or change an atlas. Does not decide what a tick is. Does not say
what a crossing means, or whether the arriving node is true. Does not carry language.

### `seams.py` — the seam rule (unchanged)

**Does.** Implements CONTINUITY.md's rule exactly: a seam needs **both** the parsed head (or the
leading register when there is no head) **to change**, **and** the step to reach the threshold.
Measures the step as the Fisher-Rao distance on the open simplex and cross-checks it with the
stable form. Refuses a point that is not strictly positive, 40 states long, summing to 1.
Refuses to interpolate across a seam. Holds two heads as `CO_PRESENT`, never averaged.

**Does not.** Does not decide a threshold. Does not parse language. Does not touch the atlas.

### `continuity.py` — the path builder

**Does.** Accumulates the crossings of one thought and gives `points()`, `form_gaps`,
`anchor()` — the S0 point **or, when S0 is bound to a real atlas node, that node's region
digest** — `displacement()`, `seams()`, `seam_checks()`, `summary()`, `drift_checks()`. Accepts
a sequence of `Crossing` objects, refuses one that does not join end to end, and reports
`atlas_path()`, `atlas_nodes_visited`, `atlas_edges_crossed`, `atlas_sort_pollution` and
`atlas_cross_sort_declared`. New in v3, `atlas_glue_back()` asks the real model whether the nodes
the path touched glue back together, and `atlas_glue_back_ok()` is its yes or no.

**Does not.** Does not build a point from content. Does not decide a threshold. Does not measure
a distance from an atlas digest: it refuses as `ANCHOR_IS_ATLAS_DIGEST` rather than inventing a
number. Does not hold or change an atlas, and computes no region digest.

### `provenance.py` — FOLLOWED, CREATED, ATTEMPTED (unchanged)

**Does.** Classifies each crossing by where the next pointer came from, logs the writer, and
provides `assert_shuffled_control()`.
**Does not.** Does not decide the cases the design left open; it refuses them as
`PROVENANCE_UNDECIDABLE`.

### `disengage.py` — the owner's ladder (unchanged)

**Does.** Runs `NOT_DECLARED`, `CONFUSED`, `ASK_CLARITY`, `DISENGAGE` in order, never fills the
gap, refuses a disengage with no reason, and goes terminal afterwards.
**Does not.** Does not parse English, decide the gap, or retry after a disengage.

## How to run the tests

```
cd C:\Users\wakil\Documents\Codex\2026-10-16\continuity_build_v3
python -B test_all.py
```

One line printed per case, then a total. Exit code 0 when all pass, 1 when any fails. No pytest
needed. The run also prints the real model's branch and commit, the sha256 of its `rpa_model.py`,
the sha256 of a small real `AtlasSnapshot` it builds, and whether `atlas.py` is present. Every one
of those is a number the run states, not a number this file remembers, so none can go stale.

The suite is **50 cases**. The 46 cases v2 had are all still here and still pass: 36 kept their
name and their body, and 10 were rewritten to run against the real model instead of the stand-in
(9 were renamed because the stand-in vocabulary they named is gone, and
`is_cjt_true_only_for_a_crossing` kept its name). Thirteen cases are new. Among them: S0 anchors
on a real `AtlasNode.region_digest()`, glue-back is decided by the real `compatibility()`, a
refused glue-back is surfaced, a crossing record carries the real `LinkType`, and the stand-in is
gone and refused.

## The frozen station-kind table

Seven kinds, one frozen record each, hashed over its own canonical JSON.

```
sha256: 7b9f2e1ad8865deeb6df5abe940ad87d39305e72fcfdfeebcb1de48caecb10e3
```

Every kind's seam, tone and drift threshold is `None` and every kind is marked
`THRESHOLD_UNDECIDED`, because STATIONS.md gives no number for any kind. The LM-T2 dialogue
numbers are recorded in `DIALOGUE_THRESHOLDS_NOT_REUSED` with `licensed_for_station_kinds =
False`. The test file re-hashes the exposed table and fails if it has changed.

## Every UNDECIDED IN DESIGN line

Each line below is copied exactly from the code, where it is marked with the
`# UNDECIDED IN DESIGN:` prefix. Nothing here was decided quietly: where the design was silent,
the build refuses and says why.
The three v2 lines belonging to the deleted stand-in (the maximum sub-atlas depth, the relation
vocabulary, and who may declare a cross-kind edge) went with it. The last two entries are the
real-model questions that replaced them.

1. `stations.py` — what theta_seam, theta_tone and theta_drift are for each station kind -- STATIONS.md:145-292 gives no number for any kind, and CONTINUITY.md:35-37 forbids reusing the dialogue numbers.

2. `stations.py` — what S0 holds as content -- OWNER_RULING_RPA_ATLAS_20261015.md:35-38 says how an atlas entry attaches to a CJT, to Bias and to an RPM link is not decided by that record.

3. `stations.py` — which ASOM reading is licensed at S4 -- CONTINUITY_AND_DISENGAGE_20261016.md:38 says the ASOM ruling has not been located and must not be invented, so S4 stores its two axes and no word.

4. `stations.py` — what granularity of the real model's region digest is the right anchor for an S0 position -- the real AtlasNode.region_digest covers the node id, its context and its members, so two nodes differing only in their members anchor differently, and no source says whether that is the intended grain for a thought's anchor; this build copies the digest the node has and records the node's real kind and status beside it.

5. `stations.py` — whether a crossing at S0 or S6 may carry a nested depth above 0 -- STATIONS.md:143 says nested levels repeat S1-S5 inside S5 and does not say whether a nested thought has its own head and next stage; this build permits any station at depth 1-5 and only caps the level.

6. `seams.py` — which register leads when a tag is a set |<...> -- CONTINUITY.md:30 says "the leading register" and never says which one leads when several are named; this build takes the first in source order.

7. `seams.py` — what a station-level tone seam compares, and against which threshold -- LM-T2 counts tone seams beside subject seams (CONTINUITY.md:16-17) and the packet gives no station-level tone rule; this build compares the leading register and nothing else.

8. `continuity.py` — what the anchor is when the S0 tap has no point (a FORM gap at the head) -- "Anchor of a thought = its S0 point" (CONTINUITY.md:29) does not cover that case, so this build refuses instead of choosing a fallback.

9. `continuity.py` — how a crossing is addressed when the same station code occurs twice (a nested level inside S5, or the other route of an ALT order) -- the packet gives no addressing scheme, so this build refuses the ambiguous name and asks for an index.

10. `provenance.py` — which word applies to a pointer written this tick by the drive loop's arm rule -- CONTINUITY.md:48-50 names only "a faculty or an injection" as the writer of a CREATED pointer, while CONTINUITY.md:86 gives the arm rule the choice of the next focus; this build refuses rather than choose a word for it.

11. `provenance.py` — what makes two pointer records the same pointer -- CONTINUITY.md:48 says only "the pointer to the next station", so this build matches on the same thought, the same station, the same next station, and a pointer_id when one is given.

12. `provenance.py` — which word applies to a crossing with no next-station pointer at all (the last station of a thought) -- the three words at CONTINUITY.md:46-50 do not cover it, so this build refuses rather than invent a fourth.

13. `provenance.py` — how late a continuation may arrive and still count as CREATED -- CONTINUITY.md:49 says "later admitted or answered" and gives no window or end-of-record rule, so this build treats an outcome that is not on record as still open at the end (ATTEMPTED).

14. `disengage.py` — whether the NOT DECLARED step speaks, and in what words -- the owner's ladder gives no sentence for it and CONTINUITY_AND_DISENGAGE_20261016.md:113-116 maps only step 2 onto "I cannot tell."; this build records the step in the receipt and says nothing.

15. `disengage.py` — what content the disengage reason must carry -- CONTINUITY_AND_DISENGAGE_20261016.md:122 requires "no, because X" and states no required fields; this build refuses only an empty reason.

16. `disengage.py` — whether a step may be skipped (for example disengage without asking) -- the ladder is given as an escalation and skipping is neither allowed nor forbidden; this build only ever takes the next step in order.

17. `disengage.py` — whether the same turn may re-enter the ladder after the information is supplied -- the packet says supplying it returns to normal and does not say whether a second gap in the same turn starts the ladder again; this build leaves the ladder resolved and starts no second one.

18. `atlas_adapter.py` — which of the vision's four kind words a real node carries -- the real model has NodeKind (idea_context / state / region / evidence) and NodeStatus (observed / hypothetical / unknown / rejected / verified) and no word FACT, GUESS, POSSIBILITY or CONTEXT, so this build compares the real (kind, status) pair as a "sort" and renames none of the real words; the mapping from the vision's four kinds onto that pair is not made here.

19. `atlas_adapter.py` — who may declare a crossing between two different sorts legal, and on what evidence -- the real model's AtlasLink carries no declaration field and the vision says facts and guesses stay distinct without naming a declaring act, so this build takes an explicit declared=True from the caller, records it on the crossing and inside the crossing's digest, and never infers it.

20. `crossings.py` — what tick an atlas crossing is stamped with, and whether an atlas crossing spends a tick at all -- CONTINUITY.md:21 indexes a thought's path by station and tick and gives no tick semantics for a crossing between atlas nodes (the tick is described there as a station boundary), so this build takes the tick from the caller and never stamps or increments one.

## What is still NOT built

This section is the honest list. Nothing below is a small gap; each line is a whole piece of work
that does not exist.

1. **Nothing organizes the atlas.** HELM vision ability 6 asks for an atlas that *organizes
   retained knowledge and possibilities*. What exists is the real model's bounded, hashed,
   validated graph, plus a binding from S0 and a crossing record. There is no retention, no
   retrieval, no narrowing, no ranking, no rebuilding after restore, and no comparison of answers
   with and without the atlas. The model itself says so: "It is not a general sheaf, an infinite
   planner, a geometric embedding, a probability model, or a mutation authority."
2. **Glue-back is asked, not used to decide anything.** `glue_back_ok()` reports the real model's
   two verdicts, and no code in this build branches on that answer. No thought is routed,
   narrowed, refused, or repaired because of a glue-back result. Wiring it into a decision is not
   done.
3. **The snapshot is built by the test file, not by a circuit.** Every run constructs its own
   small real `AtlasSnapshot` out of four nodes and two links. Nothing in this build produces a
   snapshot from a thought, a source, a recording, or the recorded run in
   `records/rpa_ohm_atlas_20260922/`. The real model's "source" and "principal" questions are
   untouched: its own docstring says it authenticates neither observations nor principals.
4. **`rpa_ohm_atlas.py` is copied but not used.** It is here as reference, and it imports
   `rpa_coordinates.py`, which was not copied, so it cannot run in this folder. It is not
   imported by any module and no test calls it.
5. **No `profile40` validation is exercised on a real station point.** The real model's
   `validate_profile40` is reached once, in a test, to show it refuses a short profile. No 40-state
   point of this build has been checked against it, and no mapping from a station's float point to
   the model's rational coordinates exists.
6. **The model's expansion features are unused.** `expand()`, `DeferredExpansion`,
   `ExpansionResult`, `hypothesis_branch_id` and `focus()` are imported but no code in this build
   calls them; the path never navigates the atlas, it only records crossings the caller already
   made.
7. **The attachment question the owner left open stays open.** How atlas entries attach to a CJT,
   to Bias and to an RPM link is still not decided by the ruling. S0 is the one station the ruling
   moved, and S0 is the one station bound here.
8. **No language passed across the atlas.** Not one case moves a word. The node fields are short
   data strings; nothing is parsed, rendered, tokenised or interpreted. Any claim that language
   rode an RPA is **NOT LICENSED**.
9. **No parser, no renderer, no tracker, no brain, no faculty, no drive loop, no learned
   parameters, no scoring, no thresholds, no verdicts, no network, no cloud, no spend.**

## One sentence on what this build cannot claim

It shows the mechanisms of the design working on inputs a person supplies, over the real atlas
model rather than a stand-in, with S0 anchored on a real node's region digest, and it cannot claim
that language, meaning, or a continuity of thought was carried across the Recursive Possibility
Atlas — no language passed across it, the design says that claim is NOT LICENSED, and this build
does not change that.
