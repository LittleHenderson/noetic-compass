# The Loop v2 — bias, proposal, ASOM readout, **the real RPM gate**, disengage ladder

Built 2026-10-16 in `C:\Users\wakil\Documents\Codex\2026-10-16\the_loop_v2\`.
It is `the_loop` (step 4 of `THE_BUILD_RESTART_PLAN_20261016.md`, *wire ASOM into the loop as a
readout only*) carried forward, with the stub gate replaced by the RPM decision itself, joining
the two packages that already carried the recursion rules: `dwp_engine` and the return rule of
`return_address`. Standard library only. No torch. No numpy. No network. No AWS. No spend.

## The claim ceiling

Verbatim, and it is the whole ceiling:

```
MECHANISM ONLY. THE GATE IS REAL; NOTHING HAS RUN INSIDE HELM.
```

Two things changed and one did not. **The gate is real**: it makes an RPM decision — proceed,
repair or refuse — from the turn's cause, decided by the recursion rules the packages it borrows
already own. The other change is that the words above replaced "the gate is a stub", which was
the ceiling of `the_loop`. What did not change: nothing in this folder has ever run inside Helm,
and nothing here is evidence about a real CJT, a real model or a real mind. The mechanism is the
whole claim.

Said plainly: nothing has run inside Helm. Not a smoke test, not one turn, not one prompt.

## The four roles, kept apart

Four things run in one turn. Each has one job, and each one is forbidden the others' jobs.

### 1. The Bias is the working memory

The Bias is where a coordinator writes the facts the next step needs. Attention writes into it;
the next CJT reads it. It holds named facts only, it has one owner, and its version goes up by
exactly one on every write and never comes down, so a stale Bias can never be presented as a
newer one.

What it must never do: be written by a second coordinator. It refuses that, and a refused write
moves nothing — not the version, not the digest.

### 2. ASOM is a readout

ASOM is a display of how the CJT is operating, in four words:

| label | what it says |
| --- | --- |
| `STARVED` | the CJT is in cutoff — there is no flow to judge |
| `ALIGNED` | active, and the result is the intended one |
| `OVERSATURATED` | saturated, and the result is still the intended one |
| `MISALIGNED` | the result is opposite or off-axis |

The readout is computed from three values the runtime produces: the operating region, the
semantic outcome, and whether the region is saturated. It is recorded on every turn.

What it must never do: gate anything. It is a display. Nothing in this build branches on it.

### 3. RPM is the gate — and the only gate

The gate alone decides whether the next step may proceed, and it answers with one of three
words: `PROCEED`, `REPAIR`, `REFUSE`. It is `rpm_gate.py`, and it is the loop's default gate.

**What it decides, and on what.** One record: the turn's cause, plus the Bias version the turn
read. The cause is `RpmCause`, and it carries exactly this:

| field | what it is |
| --- | --- |
| `blocked_node` | which node of the D/W/P chain is blocked: `"D"`, `"W"`, `"P"`, or `None` |
| `depth` | the depth of the chain carrying that block (root is 0) |
| `ancestor_dirty` | whether a dirty child invalidated the ancestor line |
| `dirty_ancestor`, `dirty_reason` | which ancestor the caller reports, and why it was marked |
| `unsatisfied` | the requirements the runtime reports as **not** realized |
| `resume_from_version` | the Bias version a returning thread was suspended at (or `None`) |
| `wisdom_route`, `decomposition`, `resonant_child` | the CO-5 / CO-6 inputs a Wisdom block needs |
| `iterations`, `state_label` | N for the Desire loop, and the name of the state |

There is no field for the ASOM label, the region, the semantic outcome or saturation on the
cause, and none on the `GateRequest` that carries it. The gate refuses a request whose field
list is not exactly the one it knows — a request carrying one extra field named `label` is
refused, not read around.

**The order of the checks is the order of the rules**, and every rule is somebody else's code:

| # | rule | who owns it | verdict |
| --- | --- | --- | --- |
| 1 | a dirty child invalidates its ancestors, and there is no undo | `retraction.mark_dirty_upward` / `is_dirty` | `REFUSE` |
| 2 | a returning thread must carry a strictly newer Bias | `bias.check_version_increase` | `REFUSE` |
| 3 | nothing blocks and nothing is missing | — | `PROCEED` |
| 4 | a named requirement is unrealized: name the gap, name the sub-goal | canon's gate paragraph, line 71 | `REPAIR` |
| 5 | a block: exactly one functor answers, and `dwp.resolve` applies the horizon itself | `dwp.resolve` + `depth.check_depth` | `REPAIR` or `REFUSE` |

So, in words:

- **`PROCEED`** — nothing on the D/W/P chain is blocked and no requirement the turn carries is
  reported unrealized. The section holds, so the action may be computed.
- **`REPAIR`** — a prerequisite is missing and a sub-goal can be opened to realize it. The gap
  is named **exactly**, and the sub-goal is named too. Three ways to reach it:
  a caller-named requirement (`gap` is that requirement, in its own words — canon's own example
  is "the specific ^P (Principled) safety constraint for a requested task"); a block whose
  functor refuses its input (`gap` is the missing input, e.g. a CO-6 decomposition into at least
  2 parts); or a block whose functor resolves it (`gap` is the node's own prerequisite at that
  depth, `sub_goal` is the engine's notation for the child chain it spawns).
- **`REFUSE`** — the gap cannot be closed from here. Three ways: an ancestor is invalid; the
  returning Bias is not strictly newer; or the sub-goal would sit past the recursion horizon.
  At the horizon the verdict carries `fix`, the flatten plan `depth.flatten` produces at the
  same level — **named, never performed, and never a deeper chain**.

Every verdict carries a stable decision code (`NOTHING_BLOCKED`, `PREREQUISITE_MISSING`,
`BLOCK_NEEDS_A_CHILD_CHAIN`, `FUNCTOR_NEEDS_INPUT`, `ANCESTOR_DIRTY`, `STALE_BIAS`,
`STRUCTURAL_DEADLOCK`, `HORIZON_BREACHED`, `NO_DEEPER_SUB_GOAL`), a `basis` listing what was
asked and what answered, and two honesty flags: `stub` (only the retained placeholder sets it)
and `rpm` (only this gate sets it).

**What the gate does not do.** It does not decide whether a node is blocked, what the depth is,
or whether an ancestor is dirty: those arrive in the cause. It does not open a sub-goal, perform
a repair, or flatten a horizon chain: it names each of those and performs none. It does not
write the horizon number — it reads `depth.HORIZON` from the vendored copy — and it does not
import the readout, the loop, or anything else.

### 4. The ladder is what happens when the gate cannot proceed

The owner's ladder, four steps in order:

`NOT_DECLARED` → `CONFUSED` ("I cannot tell.") → `ASK_CLARITY` (naming the exact gap) →
`DISENGAGE` (with a reason).

The ladder never guesses. It never fills a gap. It refuses a disengage that carries no reason,
and it refuses to ask a question that names nothing. Every step it performs is written into the
turn's receipt, so a later reader can see that it asked before it gave up.

`REPAIR` and `REFUSE` both mean "may not proceed", so both run the ladder. The gate's `gap` is
what the ladder asks for, verbatim; the gate's `reason` is what the disengage says, verbatim.

## One turn, in this order

| # | stage | what goes in | what comes out |
| --- | --- | --- | --- |
| 1 | `READ_BIAS` | the Bias | a frozen snapshot: version, facts, digest |
| 2 | `PROPOSE` | that snapshot | a proposal (text, and the facts it cites) |
| 3 | `OBSERVE` | region, semantic outcome, saturated | one ASOM label — **recorded, not consulted** |
| 4 | `GATE` | a `GateRequest` (the turn's cause) | the gate's verdict: proceed / repair / refuse |
| 5 | `DISENGAGE_OR_CONTINUE` | the verdict | either `CONTINUE`, or the ladder's four steps |

Each stage's output is the next stage's input. `Loop.turn()` returns a frozen `TurnRecord`
carrying all five stage outputs, the ASOM label, the gate verdict, the cause, and the receipt.
The loop itself checks the order and refuses to return a record if the first four stages did not
run in order.

A turn that continues has five receipt entries. A turn that stops has the four stage entries
followed by one entry per ladder step actually performed.

## The proof that ASOM cannot gate

The hard requirement is that the label is recorded and cannot influence the verdict. This build
meets it in six ways, and the test file proves each one:

1. **There is nowhere to put it.** The gate is called with a `GateRequest`: seven fields — turn,
   coordinator, Bias version, Bias digest, proposal text, prerequisites, cause — and no field for
   the label, the region, the semantic outcome or saturation. The cause carries twelve fields
   and none of them is any of those four. A test asserts both field lists exactly, and asserts
   that the gate **refuses** a request carrying one extra field named `label`.
2. **There is only one decision function.** `may_continue()` takes the gate's verdict and
   nothing else, so no other value is even in scope where continue-or-stop is decided.
3. **The whole matrix is run twice.** 150 turns — 3 regions × 5 semantic outcomes × 2 saturation
   flags × 5 gates, one of which is the real RPM gate — are run once with the label computed and
   once with the label forced to each of the five possible outputs, **including a forced
   `MISALIGNED`**. Every decision is identical every time.
4. **The real gate's whole decision surface is run twice as well.** 480 turns — 16 causes × the
   30 observation cells — including all three verdict words and all eight decision codes, run
   once computed and once per forced label. Every decision, every gap, every sub-goal, every
   fix, every ladder step, every ask, every disengage reason and every gate request is
   identical.
5. **The comparison is checked for being vacuous.** Forcing the label is proven to have actually
   differed from the computed label in that cell, and the computed runs are proven to produce all
   five labels and all three verdict words.
6. **The rule is broken on purpose and caught — in two files.** A copy of `rpm_gate.py` is
   compiled in memory with three lines that refuse whenever a `MISALIGNED` label is written into
   its module. Run against the **real** loop it decides exactly what the real gate decides, over
   every cause — because nothing hands it a label. Only when a **broken copy of `loop.py`** also
   writes the label into it do the verdicts move, and then the matrix above catches them. *A test
   that cannot fail proves nothing; this one is shown failing on demand.*

The same matrix also proves the further claim: **the ASOM label never changes a disengage
decision.** With a gate that refuses, forcing the label to any of the five outputs leaves the
ladder's steps, its ask, its reason and the turn's outcome identical.

And the gate is the only thing that can stop or allow a turn:

- with a gate that proceeds, the label is forced to `MISALIGNED`, `STARVED`, an unknown value
  and to `None` in turn, and **no turn stops** — not one, over the whole observation matrix;
- with a gate that refuses, every turn stops **even when the label says `ALIGNED`**;
- across all 150 turns, a turn continues if and only if the gate said `PROCEED`;
- each turn calls the gate exactly once, so no second opinion can stop or allow anything.

## What the gate decides on, checked against the modules it borrows from

The gate does not re-implement the recursion rules; the test file checks the borrowing by asking
the engine the same question:

- **the horizon** — for every node (D, W, P) and every depth from 0 to 7, the gate refuses exactly
  when `dwp.resolve` returns a `DeadlockResolution`; and the flatten plan the verdict carries is
  equal to the notation `depth.flatten` produces, with `child_depth is None` and
  `vertical_levels_added == 0`;
- **the dirty line** — the invalidated chains the verdict reports are the ones
  `retraction.mark_dirty_upward` marked and `retraction.is_dirty` confirms, all the way to the
  root;
- **the newer Bias** — every pair the gate refuses is a pair `bias.check_version_increase`
  refuses, with the same code;
- **the functor** — the `sub_goal` a `REPAIR` names is `dwp.resolve(...).notation`, character for
  character.

One deliberate exception, and it is canon's, not this build's: a **Desire** block at the horizon
is *not* a Structural Deadlock. Canon says the deadlock is a chain at level 5 that "encounters
another blocked node", and also that Phi_D "does not contribute to the recursion depth limit".
`dwp.resolve` already exposes that reading (`iterative_exempt_at_horizon=True`, its default), so
the gate follows the engine: a Desire block at depth 5 is `REPAIR` at the same depth, while Power
and Wisdom blocks at depth 5 are `REFUSE` with the flatten fix named. Both directions are tested.

## What this cannot claim

The gate makes a real decision. Everything it decides is about a record a caller supplied. It
therefore **cannot** claim:

1. **That anything ran inside Helm.** No turn here touched a model, a brain, an atlas, a station,
   a dataset or a person. `NOTHING HAS RUN INSIDE HELM` is literal.
2. **That a block was really observed.** The cause is supplied by the caller: whether a node was
   blocked, at what depth, and whether an ancestor is dirty are all reported to the gate, not
   detected by it. A wrong cause produces a correct decision about a wrong input.
3. **That a repair happened.** A `REPAIR` verdict names the gap and names the sub-goal. Nothing
   opens the sub-goal, nothing tracks it, and no later turn reads it back.
4. **That a horizon chain was flattened.** A `REFUSE` at the horizon names the flatten plan and
   performs nothing. `depth.flatten` is called to *compute the name*, and the chains it builds
   are discarded with the verdict.
5. **That a prerequisite was satisfied.** The gate names what is missing; satisfying it is
   somebody else's act, and it does not exist in this build.
6. **That the three words are the right three words for every case.** Nine of the readings this
   gate takes are listed below as `UNDECIDED IN CANON`, each with what was chosen instead. Those
   are readings, not decisions canon settles.
7. **That ASOM is calibrated.** No saturation threshold, no region vocabulary and no assignment
   of a label to a real CJT is fixed anywhere. The three observation inputs arrive from outside.
8. **That the engine's own suite still passes.** `dwp_engine` reports 30 cases and
   `continuity_build_v3` reports 50; this build re-hashes their files and re-runs neither suite.

## What is here

| file | what it is |
| --- | --- |
| `rpm_gate.py` | **the gate.** RPM decides `PROCEED` / `REPAIR` / `REFUSE` from the turn's cause. |
| `bias.py` | the working memory: named plain facts, one writer, a strictly increasing version, a digest per version (carried forward from `the_loop`, unmodified) |
| `loop.py` | one turn: read, propose, observe, gate, disengage-or-continue; the gate is now the real one |
| `asom.py` | **copied** from `continuity_build_v3` — the four-label readout |
| `disengage.py` | **copied** from `continuity_build_v3` — the owner's ladder |
| `dwp\dwp.py` | **copied** from `dwp_engine` — the three resolution functors |
| `dwp\depth.py` | **copied** from `dwp_engine` — `HORIZON = 5`, `check_depth`, `flatten` |
| `dwp\retraction.py` | **copied** from `dwp_engine` — per-depth integrity and dirty propagation |
| `dwp\lacunarity.py` | **copied** from `dwp_engine` — lacunarity; nothing here imports it |
| `test_all.py` | the whole suite, plain Python, no pytest |
| `README.md` | this file |
| `PROVENANCE.md` | where every copy came from, the sha256 of each, and what was not copied |

The four engine modules are byte-identical to the files in `dwp_engine` and are loaded **by
path** from `dwp\`, under their own module names, so not one byte of them had to change to be
imported here. `PROVENANCE.md` says why `return_address` was not copied and which of its rules
was taken instead.

## How to run the tests

```
cd C:\Users\wakil\Documents\Codex\2026-10-16\the_loop_v2
python -B test_all.py
```

One line printed per case, then a total. Exit code 0 when all pass, 1 when any fails. No pytest
needed, no files written, no network, well under a second.

## The undecided lines

Every point the sources and the canon do not settle is marked in the code — with
`# UNDECIDED IN SOURCES: <question>` where the *sources* (the build plan and the packets) are
silent, and with `# UNDECIDED IN CANON: <question>` where **canon** is silent — and every one is
listed below, word for word, with the reading this build took. A test reads the markers out of
the code and fails if one of them is missing from this list, so the list cannot drift away from
the code. The last four entries came in with the copied `disengage.py` and are marked
`# UNDECIDED IN DESIGN:` there.

### UNDECIDED IN SOURCES — 14 line(s)

Where the *sources* (the build plan and the packets) are silent.

1. **`bias.py`** — who counts as "a coordinator" -- THE_BUILD_RESTART_PLAN_20261016.md:24 says one coordinator writes the Bias and never defines the coordinator's identity, its lifetime or its credentials, so this build takes a caller-supplied name string and compares it exactly, by value.
2. **`bias.py`** — whether a fact may be overwritten once written -- the plan says attention writes relevant information into the Bias and says nothing about replacing a fact, so this build allows a later write under the same key, records it as a new version, and never refuses it.
3. **`bias.py`** — whether a fact may ever be deleted from the Bias -- the sources describe writing and reading and give no delete, so this build has no delete at all rather than invent one.
4. **`bias.py`** — which fields a Bias snapshot's digest must cover -- THE_BUILD_RESTART_PLAN_20261016.md:24 says a Bias snapshot is the ^5 and no source says what it hashes, so this build hashes the version and the facts in canonical JSON and records the coordinator beside the digest without hashing it.
5. **`bias.py`** — whether the next CJT that reads may be a different coordinator from the one that wrote -- the plan says attention writes and the next CJT reads and does not say whether those are the same actor, so this build refuses a second WRITER and allows any reader.
6. **`loop.py`** — whether one turn runs the ladder all the way to DISENGAGE or stops at ASK_CLARITY and ends there waiting for an answer -- the ladder's own ask (disengage.py:259) implies someone may answer it, while the owner's ladder is written as four steps ending in a disengage and "every step goes in the receipt" (THE_BUILD_RESTART_PLAN_20261016.md:88-94), so this build runs all four steps inside the one turn and never resumes inside it.
7. **`loop.py`** — whether a REPAIR verdict is "the gate refusing" -- RPM is said to decide proceed / repair / refuse and the sources say what a repair names but never say what a turn does next, so this build treats REPAIR as "may not proceed", runs the ladder, and records the word REPAIR; nothing in this build performs a repair.
8. **`loop.py`** — whether the disengage reason must be the gate's own stated reason or a separately named one -- the ladder requires a reason and says nothing about where it comes from, so this build passes the gate's reason through unchanged and lets the ladder refuse it if it is empty, rather than manufacturing one.
9. **`loop.py`** — what a proposal must carry, and whether a proposal may cite a fact the Bias never carried -- the plan says the CJT proposes "under Bias" (THE_BUILD_RESTART_PLAN_20261016.md:13) and gives no content rule, so this build records the facts a proposal cites and refuses a citation of a fact the Bias did not hold, as a checkable form of "never invent".
10. **`loop.py`** — who proposes, and whether the CJT that proposes must be the coordinator that owns the Bias -- the proposer is a pluggable callable here and no source says who may act on a Bias, so this build requires a proposer to be supplied and checks nothing about its identity.
11. **`loop.py`** — whether the gate may read the operating region, the semantic outcome or the saturation flag at all -- RPM is described as deciding whether the next step may proceed and no source says what it may consult, so this build does not pass those three to the gate, which is what makes it structurally impossible for the ASOM label built from them to reach it.
12. **`loop.py`** — whether the five stages are the whole turn, or whether a turn also writes the Bias -- attention is said to write into the Bias and the five stages only read it, so this build writes nothing during a turn and leaves writing to Loop.remember as a separate act.
13. **`loop.py`** — what a proceeded turn hands to the next turn, and whether the next turn's Bias must be strictly newer than the one this turn read -- the plan's return rule requires a strictly newer Bias for a returned thread and says nothing about an ordinary consecutive turn, so this build requires a strictly newer Bias only of a thread that says it is returning (resume_from_version), and an ordinary turn requires nothing of the sort.
14. **`loop.py`** — whether a gate that cannot proceed still needs its ASOM label recorded -- the plan says ASOM reports and never gates and says nothing about a turn that stops, so this build records the label on every turn, including the ones that disengage.

### UNDECIDED IN CANON — 13 line(s)

Where **canon** is silent.

15. **`loop.py`** — whether the turn's cause may be supplied by the same actor that proposes, and whether anything verifies that a block or a dirty ancestor really happened -- canon says nothing about who observes a block, so this build takes the cause from the caller, records it verbatim in the receipt, and checks nothing about its identity or its truth.
16. **`loop.py`** — whether a REPAIR verdict ends the turn or pauses it waiting for the sub-goal -- canon says the action cannot be computed and never says whether the same turn resumes once the sub-goal is realized, so this build ends the turn at the ladder's disengage and records the named sub-goal in the receipt, and no later turn reads it back.
17. **`loop.py`** — whether the sub-goal a REPAIR names must be recorded anywhere outside the turn -- no source gives a ledger for open sub-goals, so this build records it on the record and in the receipt and keeps no register, which is what makes the second turn in this build independent of the first.
18. **`rpm_gate.py`** — whether a block below the horizon is a REPAIR or a PROCEED -- canon says a block triggers a child chain (Definition 27.2) and that the gate stops the action when a requirement is unsatisfied (line 71), and never says which of the three words a resolvable block gets; this gate answers REPAIR because when the verdict is taken the prerequisite is still missing and nothing in this build opens the child chain.
19. **`rpm_gate.py`** — whether the gap a REPAIR names must be a node of the D/W/P chain or a caller-supplied requirement -- canon's own example names a requirement ("the specific ^P (Principled) safety constraint for a requested task", line 71) while Definition 27.2 names a node; this gate prefers a caller-named requirement and falls back to the blocked node's own name.
20. **`rpm_gate.py`** — whether a turn declares the prerequisites it needs at all, and whether the declared names must agree with the blocked node -- canon describes no declaration step; this gate records the declared names in its basis and never derives a gap from them, because the gap comes from the cause.
21. **`rpm_gate.py`** — whether an invalidated ancestor line forbids a first attempt or only a resume -- canon says "the entire parent chain is invalidated" (line 63) and says nothing about a fresh evaluation; this gate refuses any turn whose chain or ancestor line is invalid, on the reading that an invalidated chain cannot be evaluated.
22. **`rpm_gate.py`** — whether the gate itself may flatten at the horizon, or must only name the fix -- canon presents flattening as the fix and never says who performs it; this gate names the flatten plan in its verdict and performs no flatten.
23. **`rpm_gate.py`** — whether a chain at a depth beyond the horizon is a refusal or an error -- depth.py refuses any block at or beyond HORIZON and depth.flatten is available only exactly at the horizon, so this gate refuses with HORIZON_BREACHED and names no fix.
24. **`rpm_gate.py`** — whether a block on the Desire node at the horizon is also a Structural Deadlock -- canon defines the deadlock as a chain at level 5 that "encounters another blocked node" and also says Phi_D "does not contribute to the recursion depth limit"; this gate follows dwp.resolve's documented default (iterative_exempt_at_horizon=True), so a Desire block at the horizon is a REPAIR at the same depth, not a REFUSE.
25. **`rpm_gate.py`** — whether "strictly newer" for a returning Bias means any greater version or exactly one greater -- return_address/stack.py records the same gap for the same rule; this gate accepts any strictly greater version, matching that reading.
26. **`rpm_gate.py`** — whether N, the Desire loop's iteration count, is bounded anywhere, and what it defaults to -- canon writes loop(N) with no bound; this gate takes N from the caller and defaults to dwp.State's own default, so the two can never disagree about the number.
27. **`rpm_gate.py`** — whether a horizon refusal should name the blocked node's prerequisite or the horizon itself as the gap -- canon names the deadlock and not the ask; this gate names the missing prerequisite so the ladder asks a real question, and puts the horizon in the reason.

### UNDECIDED IN DESIGN — 4 line(s)

Inherited with the copied files, in their own words.

28. **`disengage.py`** — whether the NOT DECLARED step speaks, and in what words -- the owner's ladder gives no sentence for it and CONTINUITY_AND_DISENGAGE_20261016.md:113-116 maps only step 2 onto "I cannot tell."; this build records the step in the receipt and says nothing.
29. **`disengage.py`** — what content the disengage reason must carry -- CONTINUITY_AND_DISENGAGE_20261016.md:122 requires "no, because X" and states no required fields; this build refuses only an empty reason.
30. **`disengage.py`** — whether a step may be skipped (for example disengage without asking) -- the ladder is given as an escalation and skipping is neither allowed nor forbidden; this build only ever takes the next step in order.
31. **`disengage.py`** — whether the same turn may re-enter the ladder after the information is supplied -- the packet says supplying it returns to normal and does not say whether a second gap in the same turn starts the ladder again; this build leaves the ladder resolved and starts no second one.

## What is still not built

This is the honest list. Each line is a whole piece of work that does not exist.

1. **No repair.** The gate names a sub-goal and nothing opens it. There is no register of open
   sub-goals, no resumption, and no second pass at the same turn.
2. **No flattening.** The gate names the flatten plan at the horizon and performs nothing. No
   code here builds a horizontal decomposition in order to use it.
3. **No observation of a block.** The cause is the caller's report. Nothing here detects a block,
   measures a depth, or discovers that an ancestor is dirty by looking.
4. **No return address.** A turn has no address, is not bound to one, and nothing refuses a stale
   return *of a turn*. What the gate does check is the return rule on the Bias version, and only
   when the caller says the thread is returning.
5. **No Atlas, no stations, no seams, no crossings.** Nothing here reads or writes a Recursive
   Possibility Atlas. A thought's anchor is not an Atlas position in this build.
6. **No memory of the turn.** A turn does not write what it learned back into the Bias. The next
   turn reads the same Bias, unchanged. That is deliberate — see the undecided line about whether
   a turn writes at all — and it is the largest thing missing here.
7. **No language.** Nothing is parsed or rendered anywhere. No sentence moved, no meaning was
   carried.
8. **No ASOM calibration.** No threshold, no region vocabulary, no label assigned to a real CJT
   by any source this build may cite.
9. **No model, no brain, no scoring, no thresholds, no network, no cloud, no spend, no Helm.**

## One sentence on what this build cannot claim

It shows one turn of the loop running with its four jobs kept apart — a working memory written by
one coordinator, a proposal made under it, a readout recorded, an RPM verdict taken from the
turn's cause and decided by the recursion rules the engine already owns, and the owner's ladder
run when that verdict cannot proceed — and it cannot claim that anything ran inside Helm, because
nothing has: the gate is real, and the mechanism is the whole claim.
