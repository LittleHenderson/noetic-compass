# The Loop — bias, proposal, ASOM readout, RPM gate, disengage ladder

Built 2026-10-16 in `C:\Users\wakil\Documents\Codex\2026-10-16\the_loop\`.
This is **step 4** of the build plan (`THE_BUILD_RESTART_PLAN_20261016.md`, section 6):
*wire ASOM into the loop as a readout only.* Standard library only. No torch. No numpy.
No network. No AWS. No spend.

## The claim ceiling

Verbatim, and it is the whole ceiling:

```
MECHANISM ONLY. THE GATE IS A STUB. NO REAL RPM DECISION IS MADE HERE.
```

## The three roles, kept apart

Four things run in one turn. Each has one job, and each one is forbidden the others' jobs.

### 1. The Bias is the working memory

The Bias is where a coordinator writes the facts the next step needs. Attention writes into
it; the next CJT reads it. It holds named facts only, it has one owner, and its version goes
up by exactly one on every write and never comes down, so a stale Bias can never be
presented as a newer one.

What it must never do: be written by a second coordinator. It refuses that, and a refused
write moves nothing — not the version, not the digest.

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

### 3. RPM is the gate

The gate alone decides whether the next step may proceed. There are three words: `PROCEED`,
`REPAIR`, `REFUSE`. In this build the gate is also given the prerequisite names the caller
supplies, unchanged.

**The gate is a stub.** It always proceeds, and it says so in its own reason text. Wiring RPM
into that gate is a later step of the build plan. Until then the gate is a placeholder, and
that is a limit of this step, not a claim about anything. See "what the stub gate means"
below.

### 4. The ladder is what happens when the gate cannot proceed

The owner's ladder, four steps in order:

`NOT_DECLARED` → `CONFUSED` ("I cannot tell.") → `ASK_CLARITY` (naming the exact gap) →
`DISENGAGE` (with a reason).

The ladder never guesses. It never fills a gap. It refuses a disengage that carries no
reason, and it refuses to ask a question that names nothing. Every step it performs is
written into the turn's receipt, so a later reader can see that it asked before it gave up.

## One turn, in this order

| # | stage | what goes in | what comes out |
| --- | --- | --- | --- |
| 1 | `READ_BIAS` | the Bias | a frozen snapshot: version, facts, digest |
| 2 | `PROPOSE` | that snapshot | a proposal (text, and the facts it cites) |
| 3 | `OBSERVE` | region, semantic outcome, saturated | one ASOM label — **recorded, not consulted** |
| 4 | `GATE` | a `GateRequest` | the gate's verdict: proceed / repair / refuse |
| 5 | `DISENGAGE_OR_CONTINUE` | the verdict | either `CONTINUE`, or the ladder's four steps |

Each stage's output is the next stage's input. `Loop.turn()` returns a frozen `TurnRecord`
carrying all five stage outputs, the ASOM label, the gate verdict and the receipt. The loop
itself checks the order and refuses to return a record if the first four stages did not run in
order.

A turn that continues has five receipt entries. A turn that stops has the four stage entries
followed by one entry per ladder step actually performed.

## The proof that ASOM cannot gate

The hard requirement is that the label is recorded and cannot influence the verdict. This
build meets it in five ways, and the test file proves each one:

1. **There is nowhere to put it.** The gate is called with a `GateRequest`. That record has
   six fields — turn, coordinator, bias version, bias digest, proposal text, prerequisites —
   and no field for the label, the region, the semantic outcome or saturation. A gate cannot
   read the readout out of the record it is given. A test asserts the field list exactly.
2. **There is only one decision function.** `may_continue()` takes the gate's verdict and
   nothing else, so no other value is even in scope where continue-or-stop is decided. A test
   runs every verdict word against every gap and reason combination and checks the answer is a
   function of the verdict alone.
3. **The whole matrix is run twice.** 150 turns — 3 regions × 5 semantic outcomes × 2
   saturation flags × 5 gates — are run once with the label computed and once with the label
   forced to each of the five possible outputs, **including a forced `MISALIGNED`**. Every
   decision is identical every time: the verdict, the gap, the reason, the turn's outcome, the
   ladder's steps, its ask and its disengage reason. The gate requests are identical too.
4. **The comparison is checked for being vacuous.** Forcing the label is proven to have
   actually differed from the computed label in that cell, so the equality above is not
   "ALIGNED equals ALIGNED" 150 times. The computed run is also proven to produce all five
   labels, not one.
5. **The rule is broken on purpose and caught.** A copy of `loop.py` is compiled in memory
   with three lines added that let a `MISALIGNED` label overrule the gate. The same matrix run
   against that copy produces different decisions, which is the failure the test above must
   catch — and does. The injection is also proven to have taken effect. *A test that cannot
   fail proves nothing; this one is shown failing on demand.*

The same matrix also proves the further claim: **the ASOM label never changes a disengage
decision.** With a gate that refuses, forcing the label to any of the five outputs leaves the
ladder's steps, its ask, its reason and the turn's outcome identical.

And the gate is the only thing that can stop or allow a turn:

- with a gate that proceeds, the label is forced to `MISALIGNED`, `STARVED` and an unknown
  value in turn, and **no turn stops** — not one, over the whole observation matrix;
- with a gate that refuses, every turn stops **even when the label says `ALIGNED`**;
- across all 150 turns, a turn continues if and only if the gate said `PROCEED`;
- each turn calls the gate exactly once, so no second opinion can stop or allow anything.

## What the stub gate means for what this cannot claim

The gate is a placeholder. It always proceeds. It performs no prerequisite check of any kind.

Therefore this build **cannot** claim:

1. **That anything was gated.** No turn in this build was ever stopped by RPM, because RPM is
   not here. Every refusal the tests exercise comes from a gate written in `test_all.py`,
   which exists to show that the ladder runs when a gate refuses — not to stand in for RPM.
2. **That a prerequisite was ever checked, repaired or satisfied.** The prerequisite names a
   caller passes go into the `GateRequest` and out again. Nothing reads them.
3. **That `REPAIR` means anything.** Nothing in this build can repair. A `REPAIR` verdict is
   treated as "may not proceed" and runs the ladder; that reading is listed as undecided
   below, and it is a reading, not a decision the sources settle.
4. **That anything was thought, meant, understood or carried.** Every case is a mechanism
   check on inputs a person supplies.
5. **That ASOM is calibrated.** No saturation threshold, no region vocabulary and no
   assignment of a label to a real CJT is fixed here. The three observation inputs arrive from
   outside, exactly as the copied readout requires.

When RPM is wired into `loop.py`, the claim ceiling moves and this README must move with it.
The line to change is the gate call in `Loop.turn`, and the stub's own reason text is what
makes the change detectable: a real gate will not say "STUB".

## What is here

| file | what it is |
| --- | --- |
| `bias.py` | the working memory: named plain facts, one writer, a strictly increasing version, a digest per version |
| `loop.py` | one turn: read, propose, observe, gate, disengage-or-continue; the gate is a stub |
| `asom.py` | **copied** from `continuity_build_v3` — the four-label readout |
| `disengage.py` | **copied** from `continuity_build_v3` — the owner's ladder |
| `test_all.py` | the whole suite, plain Python, no pytest |
| `README.md` | this file |
| `PROVENANCE.md` | where the two copies came from, and the sha256 of each |

Nothing was copied from `dwp_engine` and nothing imports it: RPM is the gate, the gate is a
stub, and copying the RPM engine in would put a real prerequisite resolution behind a
placeholder. `PROVENANCE.md` says why in full.

## How to run the tests

```
cd C:\Users\wakil\Documents\Codex\2026-10-16\the_loop
python -B test_all.py
```

One line printed per case, then a total. Exit code 0 when all pass, 1 when any fails. No
pytest needed, no files written, no network.

## The undecided lines

Every point the sources do not settle is marked in the code with
`# UNDECIDED IN SOURCES: <question>` and is listed below, word for word, with the reading this
build took. A test reads the markers out of the code and fails if one of them is missing from
this list, so the list cannot drift away from the code.

The last four entries came in with the copied files and are marked
`# UNDECIDED IN DESIGN:` there. They are listed here too, in the copied files' own words.

1. **`bias.py`** — who counts as "a coordinator" -- THE_BUILD_RESTART_PLAN_20261016.md:24 says one coordinator writes the Bias and never defines the coordinator's identity, its lifetime or its credentials, so this build takes a caller-supplied name string and compares it exactly, by value.
2. **`bias.py`** — whether a fact may be overwritten once written -- the plan says attention writes relevant information into the Bias and says nothing about replacing a fact, so this build allows a later write under the same key, records it as a new version, and never refuses it.
3. **`bias.py`** — whether a fact may ever be deleted from the Bias -- the sources describe writing and reading and give no delete, so this build has no delete at all rather than invent one.
4. **`bias.py`** — which fields a Bias snapshot's digest must cover -- THE_BUILD_RESTART_PLAN_20261016.md:24 says a Bias snapshot is the ^5 and no source says what it hashes, so this build hashes the version and the facts in canonical JSON and records the coordinator beside the digest without hashing it.
5. **`bias.py`** — whether the next CJT that reads may be a different coordinator from the one that wrote -- the plan says attention writes and the next CJT reads and does not say whether those are the same actor, so this build refuses a second WRITER and allows any reader.
6. **`loop.py`** — whether one turn runs the ladder all the way to DISENGAGE or stops at ASK_CLARITY and ends there waiting for an answer -- the ladder's own ask (disengage.py:259) implies someone may answer it, while the owner's ladder is written as four steps ending in a disengage and "every step goes in the receipt" (THE_BUILD_RESTART_PLAN_20261016.md:88-94), so this build runs all four steps inside the one turn and never resumes inside it.
7. **`loop.py`** — whether a REPAIR verdict is "the gate refusing" -- RPM is said to decide proceed / repair / refuse and no source says what a turn does when a prerequisite is missing but repairable, so this build treats REPAIR as "may not proceed", runs the ladder, and records the word REPAIR; nothing in this build can perform a repair.
8. **`loop.py`** — whether the disengage reason must be the gate's own stated reason or a separately named one -- the ladder requires a reason and says nothing about where it comes from, so this build passes the gate's reason through unchanged and lets the ladder refuse it if it is empty, rather than manufacturing one.
9. **`loop.py`** — what a proposal must carry, and whether a proposal may cite a fact the Bias never carried -- the plan says the CJT proposes "under Bias" (THE_BUILD_RESTART_PLAN_20261016.md:13) and gives no content rule, so this build records the facts a proposal cites and refuses a citation of a fact the Bias did not hold, as a checkable form of "never invent".
10. **`loop.py`** — who proposes, and whether the CJT that proposes must be the coordinator that owns the Bias -- the proposer is a pluggable callable here and no source says who may act on a Bias, so this build requires a proposer to be supplied and checks nothing about its identity.
11. **`loop.py`** — whether the gate may read the operating region, the semantic outcome or the saturation flag at all -- RPM is described as deciding whether the next step may proceed and no source says what it may consult, so this build does not pass those three to the gate, which is what makes it structurally impossible for the ASOM label built from them to reach it.
12. **`loop.py`** — whether the five stages are the whole turn, or whether a turn also writes the Bias -- attention is said to write into the Bias and the five stages only read it, so this build writes nothing during a turn and leaves writing to Loop.remember as a separate act.
13. **`loop.py`** — what a proceeded turn hands to the next turn, and whether the next turn's Bias must be strictly newer than the one this turn read -- the plan's return rule requires a strictly newer Bias for a returned thread and says nothing about an ordinary consecutive turn, so this build requires nothing of the sort and records the version it read.
14. **`loop.py`** — whether a gate that cannot proceed still needs its ASOM label recorded -- the plan says ASOM reports and never gates and says nothing about a turn that stops, so this build records the label on every turn, including the ones that disengage.
15. **`disengage.py`** (inherited, in the copied file's own words) — whether the NOT DECLARED step speaks, and in what words -- the owner's ladder gives no sentence for it and CONTINUITY_AND_DISENGAGE_20261016.md:113-116 maps only step 2 onto "I cannot tell."; this build records the step in the receipt and says nothing.
16. **`disengage.py`** (inherited, in the copied file's own words) — what content the disengage reason must carry -- CONTINUITY_AND_DISENGAGE_20261016.md:122 requires "no, because X" and states no required fields; this build refuses only an empty reason.
17. **`disengage.py`** (inherited, in the copied file's own words) — whether a step may be skipped (for example disengage without asking) -- the ladder is given as an escalation and skipping is neither allowed nor forbidden; this build only ever takes the next step in order.
18. **`disengage.py`** (inherited, in the copied file's own words) — whether the same turn may re-enter the ladder after the information is supplied -- the packet says supplying it returns to normal and does not say whether a second gap in the same turn starts the ladder again; this build leaves the ladder resolved and starts no second one.

## What is still not built

This is the honest list. Each line is a whole piece of work that does not exist.

1. **No real RPM decision.** The gate is a stub. `dwp.py`, `depth.py`, `retraction.py` and
   `lacunarity.py` are not here. Nothing checks, repairs or refuses a prerequisite.
2. **No recursion.** Nothing spawns a child chain, flattens at the horizon, or handles a
   dirty child. None of that is in scope for this step.
3. **No Atlas, no stations, no seams, no crossings.** Nothing here reads or writes a
   Recursive Possibility Atlas. A thought's anchor is not an Atlas position in this build.
4. **No return address.** A turn's outcome is not bound to an address and no stale return is
   refused. The Bias version that would support it exists; using it that way does not.
5. **No memory of the turn.** A turn does not write what it learned back into the Bias. The
   next turn reads the same Bias, unchanged. That is deliberate — see the undecided line about
   whether a turn writes at all — and it is the largest thing missing here.
6. **No language.** Nothing is parsed or rendered anywhere. No sentence moved, no meaning was
   carried.
7. **No ASOM calibration.** No threshold, no region vocabulary, no label assigned to a real
   CJT by any source this build may cite.
8. **No model, no brain, no scoring, no thresholds, no network, no cloud, no spend.**

## One sentence on what this build cannot claim

It shows one turn of the loop running with its five jobs kept apart — a working memory written
by one coordinator, a proposal made under it, a readout recorded, a gate verdict taken, and the
owner's ladder run when that verdict cannot proceed — and it cannot claim that RPM decided
anything, because the gate is a stub: no real RPM decision is made here.
