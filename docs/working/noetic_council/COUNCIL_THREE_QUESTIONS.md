# Council of Ten Seats — Three Questions

**Sat:** 2026-10-16 · **Mode:** read-only · **Files changed:** this file only
**Sources read:** see the Evidence Index at §0.2. Every quote below carries `file:line`.
**Nothing here ran on AWS. Nothing here spent money.** One local read-only test run is reported at §0.4
and is labelled as measured.

---

# SUMMARY — one page

## Q1 — Is a Desire block at depth 5 also a Structural Deadlock?

**Council reading: `READING — NEEDS THE OWNER`.** The build's default (Desire stays iterative,
not a deadlock) is the reading the sources lean toward, on two grounds that are both in the text:

1. Chapter 27:55 says the Desire loop "does not spawn child chains ... it does not contribute to
   the recursion depth limit."
2. The full manuscript defines the deadlock by what it *costs*: "The architecture cannot spawn
   another level without violating the global stability axiom" (FULL_MANUSCRIPT_v2.md:6428).
   A Desire block never asks for another level, so it never pays that cost.

What the sources do **not** say: what happens when a Desire loop at any depth never reaches its
motivation threshold. Canon puts no bound on the loop ("until the motivation threshold is reached",
Chapter_27:55; `(CO-1 ∘ CO-4 ∘ CO-7)^N`, Chapter_27:55). So the exemption is defensible and the
opposite reading is also defensible, and neither is required by the text.
**The most important disagreement in this whole council is here:** Chapter_19:60 says "If you see a
red node at depth 5, the model has reached a **Structural Deadlock**" — *any* red node, with no
carve-out for Desire. That sentence sits directly against Chapter 5:87 and Chapter 27:55.

## Q2 — What counts as "dirty" beyond the named Power bypass?

**Council reading: `READING — NEEDS THE OWNER` on the list; `SETTLED BY SOURCE` on the test.**
Canon gives a **criterion**, not a list. The criterion is stated twice in the same paragraph:
"a child chain cannot resolve a block by **violating the architecture**" (Chapter_27:63), and the
consequence "the retraction morphism fails" (Chapter_27:63). So: **dirty = the child's
`ε ∘ η = id` does not hold.** The Power bypass is one way to break it, not the definition.

Canon then names **three** concrete architecture violations in Chapter 5 — Bypassing Desire
(Chapter_05:32), Bypassing Wisdom (Chapter_05:33), and the Power bypass (Chapter_27:63) — plus two
adjacent faults filed under *different* names: the Topological Deadlock (Chapter_24:59) and Recursive
Drift (Chapter_26:52). Whether those two count as "dirty" is not stated anywhere.
**Which concrete acts beyond bypasses count is the owner's ruling to make.**

## Q3 — The depth number

**Council reading on the number: `CANNOT BE SETTLED FROM SOURCES`.** Five different numbers are in
play for the *same* quantity, and the survey that collected them refused to choose:
"sources disagree (none chosen here)" (SOURCES_RPM…20261015.md:83). I verified every number below
myself except the Builder's Manual formula (§0.5).

**Council reading on the proposed nesting reading: `READING — NEEDS THE OWNER`.**
It is half-supported and half-contradicted, and no source states it.

- **Supported:** every operational number is **≤ 5** — rails 3 and 2 (governance_rails.py:57-58),
  rc0 4 (rc0_types.py:227), CNCM 4 (cncm/model.py:446), Gate A 3 (PREREGISTRATION_GA.md:17),
  Atlas default 3 (rpa_model.py:472). And the book itself bands depths *inside* the limit:
  tier 3 "handling a depth of 1-3", tier 4 "up to the CAS limit of **5 recursive levels**"
  (Chapter_19:55-56). That is the strongest canonical support the nesting reading has.
- **Contradicted — clause "nothing may exceed 5":** the Builder's Manual gives
  `Max_depth = log₂(resources) + 3` (survey:73). That exceeds 5 as soon as resources pass 4, with no
  cap. And the Atlas's own hard ceiling is `MAX_DEPTH = 32` (rpa_model.py:29) — its 3 is a *default
  argument*, not its maximum.
- **Contradicted — clause "lower numbers are rails inside":** no source says this. The rails code
  calls its number a **cap** and refuses past it: `reason=f"RPM depth {current_depth} exceeds cap
  {depth_cap}"` (governance_rails.py:632). rc0 and CNCM call theirs `max_rpm_depth`. A cap is a
  ceiling in its own system, not a sub-limit of another ceiling. Calling 4 and 3 "rails inside 5" is
  an interpretation the sources do not contain.

**What settles Q3:** an owner ruling on which quantity each number governs (recursion depth vs.
run-time governor vs. map-expansion default), and a decision on whether the Builder's Manual formula
is admitted or excluded. No experiment can decide a naming question.

---

# §0 — How the council sat

## §0.1 The ten seats, verbatim

| # | Seat | Definition (verbatim) | Operation |
|---|---|---|---|
| 0 | `^0` Idea | "All things in and outside the Mind." | What counts as an artefact at all; what must exist first. |
| 1 | `^1` Mind | "Various degrees of awareness that processes, stores, outputs, and intakes Ideas." | Who reads, and what is permitted to read. |
| 2 | `^2` Positive | "An Idea the Mind has an affinity for and is attracted toward." | What the evidence is attracted toward. |
| 3 | `^3` Negative | "An Idea the Mind is adverse to and repelled by." | What must be REFUSED. *Visceral, not analytical.* |
| 4 | `^4` Vibration | "The degree to which an Idea resonates with the Mind, its impression." | Exact numbers, not impressions. |
| 5 | `^5` Female | "A Mind impregnated with an Idea, the Ideas a Mind is composed of." | Read the accumulated substrate. |
| 6 | `^6` Male | "An Idea impregnated with another Idea, the Ideas an Idea is composed of." | Decompose; name which part owns which fault. |
| 7 | `^7` Rhythm | "The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it." | Did it run, how often, does it replay identically. |
| 8 | `^8` Above/Cause | "An Idea that triggers a different Idea than itself to come to Mind." | Trace the trigger. *Associative, not deductive.* |
| 9 | `^9` Below/Effect | "The Idea brought to Mind by an Above/Cause trigger." | What the program actually said. |

Each seat reports **independently**. Synthesis is a separate step and is labelled as such.

## §0.2 Evidence index (exact paths)

| Short name | Full path |
|---|---|
| `Chapter_05` | `C:\Users\wakil\OneDrive\Desktop\tksCAS\book\manuscript\Chapter_05_The_Prerequisite_Chain.md` |
| `Chapter_18` | `C:\Users\wakil\OneDrive\Desktop\tksCAS\book\manuscript\Chapter_18_Why_AI_Needs_Psychology.md` |
| `Chapter_19` | `C:\Users\wakil\OneDrive\Desktop\tksCAS\book\manuscript\Chapter_19_Assessing_AI_with_Noetic_Compass.md` |
| `Chapter_24` | `C:\Users\wakil\OneDrive\Desktop\tksCAS\book\manuscript\Chapter_24_The_Noetic_Topos.md` |
| `Chapter_26` | `C:\Users\wakil\OneDrive\Desktop\tksCAS\book\manuscript\Chapter_26_The_Fractal_Calculus.md` |
| `Chapter_27` | `C:\Users\wakil\OneDrive\Desktop\tksCAS\book\manuscript\Chapter_27_RPM_Structure.md` |
| `v2` | `C:\Users\wakil\OneDrive\Desktop\tksCAS\book\manuscript\FULL_MANUSCRIPT_v2.md` |
| `survey` | `C:\Users\wakil\Documents\Codex\2026-10-15\helm_language_faculties_circuit_design_v1\SOURCES_RPM_CASCADE_DEPTH_AND_RPA_ATLAS_20261015.md` |
| `engine/*` | `C:\Users\wakil\Documents\Codex\2026-10-16\dwp_engine\` (`dwp.py`, `depth.py`, `retraction.py`, `README.md`, `test_all.py`) |
| `recursive.rs` | `C:\Users\wakil\OneDrive\Desktop\tksCAS\noetic-compass-scaffold\noetic-compass\cas-engine\src\rpm\recursive.rs` |
| `cncm/model.py` | `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\cncm\model.py` |
| `rc0_types.py` | `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\recursive_cjt_rc0\sim\rc0_types.py` |
| `governance_rails.py` | `C:\Users\wakil\Downloads\Everthing-Tootra-TKS\tks_features\governance_rails.py` |
| `rpa_model.py` | `D:\tksCAS-worktrees\helm-integration\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\cncm\rpa_model.py` |
| `PREREGISTRATION_GA.md` | `C:\Users\wakil\Documents\Codex\2026-10-06\helm_thread_claude\gate_a\PREREGISTRATION_GA.md` |

## §0.3 Claim vocabulary

- **`SUPPORTED BY SOURCE`** — a source states it and I quote it with a line number.
- **`SILENT`** — I searched, and the source does not state it. The search scope is named so the
  silence is bounded rather than implied.
- **`CONTRADICTED`** — a source states the opposite, quoted with a line number.

## §0.4 What I measured vs. what I am reporting

**Measured by me:** I ran `python -B test_all.py` in the `dwp_engine` directory. Output verbatim:
`RESULT: PASSED. 30/30 tests passed, 0 failed.` and `Depth 6 reached: never. Structural Deadlock
occurs at depth 5 and is flattened, not extended.` Selected lines: `4096 exhaustive policies,
deepest chain = 5, none at depth 6`; `500 randomised policies over depths 0..9, horizon held`;
`D@5: iterative by default (U3), deadlock under the strict reading`; `dirty child -> root.W.c2 ->
root (walked to root)`; `10 UNDECIDED markers, all listed in README.md: U1, U10, U2, U3, U4, U5, U6,
U7, U8, U9`. The run writes no files (README:31) and needs no network.

**Not measured by me:** every claim about the Builder's Manual (it is a PDF at
`C:\Users\wakil\OneDrive\Documents\TKS_ The Tootra Kabbalistic System for Majik - Complete Builder's
Manual.pdf` and I did not open it). That one number is reported at second hand and is marked so.

## §0.5 Hard rules the council kept

- No invented quote. Every quote carries a line number.
- No softening of a disagreement into a compromise. Where seats conflict, the conflict is printed.
- Anything that is the owner's to decide is marked `NEEDS THE OWNER`.
- One file written: this one.

---

# Q1 — U3: Is a Desire block at depth 5 also a Structural Deadlock?

## The question as posed

Canon says a block at depth 5 is a deadlock. Canon also says the Desire loop "is iterative, not
recursive; it does not spawn child chains" and therefore does not count toward depth. A build
currently defaults to: Desire at depth 5 stays iterative and is **not** a deadlock, behind the flag
`iterative_exempt_at_horizon=True`.

## §1.1 Seat findings — independent

### `^0` Idea — what counts as an artefact here at all

`SUPPORTED BY SOURCE`. Before any seat can rule on the Desire claim, the artefact under ruling has to
exist. The text makes three distinct artefacts, and the whole question turns on the difference:

- a **recursive chain** spawned at a depth: "A recursive evaluation $R^{(n)}$ is a nested D/W/P chain
  spawned at depth $n$" (Chapter_27:47);
- an **iterative loop** that spawns nothing: "It does not spawn child chains but instead cycles the
  current state through an exposure loop" (Chapter_27:55);
- a **deadlock state**: "We define Structural Deadlock as the state where a recursive chain at depth
  $n=5$ encounters another blocked node" (v2:6428).

The third artefact is defined over the **first** kind. It is not defined over the second. That is a
statement about what exists, made before any judgement.

### `^1` Mind — who reads, and what is permitted to read

`SUPPORTED BY SOURCE`. Three readers exist and they are permitted to read different amounts:

- the book's formal reader may read the deadlock definition: `$n=5$` (v2:6428);
- the book's informal reader may read the dashboard rule: "If you see a red node at depth 5, the
  model has reached a **Structural Deadlock**" (Chapter_19:60);
- the engine's reader is told the flag exists and that both readings are exposed: "Both readings are
  exposed: with `iterative_exempt_at_horizon=True` (default) a D block at depth 5 stays iterative at
  depth 5; with False it deadlocks like P and W" (engine/dwp.py:574-576).

The book never addresses the engine's reader. `SILENT` on the question the flag actually raises:
no source states which of the two deadlock sentences (Chapter_19:60's "any red node", or
Chapter_27:55's Desire exemption) governs a machine reader rather than a human looking at a picture.
That asymmetry is the reason the flag is a flag.

### `^2` Positive — what the evidence is attracted toward

`SUPPORTED BY SOURCE` for the exemption. The evidence is drawn toward three statements, all of which
point the same way:

1. "**Iterative**, not recursive. It does not spawn child chains ... Because it is iterative, it does
   not contribute to the recursion depth limit." (Chapter_27:55; identical at v2:6406)
2. "Note that Desire loops, being iterative rather than recursive, do not count toward this depth
   limit." (Chapter_05:87)
3. "The architecture cannot spawn another level without violating the global stability axiom."
   (v2:6428) — the deadlock is the cost of spawning a level. A Desire block never tries to.

### `^3` Negative — what must be REFUSED

`CONTRADICTED`. What the council refuses to accept is the flat claim "canon says any block at depth 5
is a deadlock." It is not what canon says, and reading it that way throws away the exemption clause
in the same document. But the council equally refuses the flat claim "canon exempts Desire." Canon
never writes that sentence either.

**Refused outright:** quoting Chapter_19:60 as if it settled the question. "If you see a red node at
depth 5, the model has reached a **Structural Deadlock**" (Chapter_19:60) is a **dashboard reading
rule for a human looking at a picture**. It does not know which node is red, and it does not carve
out Desire. It is the single hardest sentence against the build's default, and it cannot be waved
away.

### `^4` Vibration — does the result resonate exactly with the frozen marks

`SUPPORTED BY SOURCE`, exact numbers, on the code side:

- `HORIZON = 5` (engine/depth.py:63)
- root pinned at depth 0, so the deadlock is at 5 and depth 6 is unreachable (engine/dwp.py:564-569)
- `exempt = (node is Node.D) and iterative_exempt_at_horizon` (engine/dwp.py:603)
- flag is passed everywhere by default: `iterative_exempt_at_horizon=True` (engine/dwp.py:699)
- Rust engine: `const DEFAULT_MAX_DEPTH: u8 = 5;` (recursive.rs:67)

Measured behaviour, from my run: `D@5: iterative by default (U3), deadlock under the strict reading`
— and the assertion behind that line is that the default returns `IterativeResolution` with
`child_depth == 5` while the strict reading returns `DeadlockResolution` (engine/test_all.py:267-275).
The two readings differ in exactly one output type and in no number. Nothing else in the suite moves.

### `^5` Female — what the canon already says, before anything was invented

`SUPPORTED BY SOURCE`, and this is the load-bearing finding:

> "Note that Desire loops, being iterative rather than recursive, do not count toward this depth
> limit." — Chapter_05:87

> "Because it is iterative, it does not contribute to the recursion depth limit." — Chapter_27:55

These sentences were not added by a build. They sit in the published text beside the sentence that
sets the limit of 5 (Chapter_05:87; Chapter_27:59). The exemption is **older than the code**. The
build did not invent it; the build inherited it and flagged that canon had not closed the loop.

Three further sentences of accumulated substrate bear on it:

- "Each level of recursion increases the Total Cognitive Load ($\Gamma$)" (v2:6426) — the horizon is
  a load budget. An exposure loop that adds no level adds no $\Gamma$. **Supports the exemption.**
- "The architecture cannot spawn another level" (v2:6428) — again, level-spawning is the violation.
  **Supports the exemption.**
- "| Structural Deadlock | A terminal state occurring when a recursive reasoning chain **exceeds**
  the stability horizon of 5 levels. |" (v2:7095) — "exceeds", not "reaches". If the glossary is the
  operative wording, a block *at* 5 that cannot go deeper has not exceeded anything. **Supports the
  exemption**, and contradicts the main definition's "at depth $n=5$" wording.

**Note the internal canon conflict the substrate itself contains:** the main definition says a chain
*at* depth 5 is the deadlock (v2:6428); the glossary says a chain that *exceeds* 5 is (v2:7095). They
agree in practice only because the would-be child would sit at 6. That agreement is an argument, not
a sentence, and the council is reporting it as an argument.

### `^6` Male — decompose, and name which part owns which fault

`SUPPORTED BY SOURCE`. The question decomposes into four parts, and they do **not** have the same
owner:

| Part | What it asks | Owner of the fault |
|---|---|---|
| **A. Does a Desire block spawn a depth-6 chain?** | level arithmetic | **Settled. It cannot.** Chapter_27:55 + Chapter_05:87. The exemption is right on this part. |
| **B. Is "another blocked node at $n=5$" fatal regardless of what the resolution needs?** | scope of the definition | **Unsettled.** v2:6428 reads unconditionally ("encounters another blocked node"); but its own next sentence reads conditionally ("cannot spawn another level"). The *same paragraph* carries both. |
| **C. What if the loop never reaches the threshold?** | termination | **`SILENT`.** Canon gives the loop no bound and no outcome for a loop that never terminates. Searched Chapter_05:61-87, Chapter_27:55, v2:6406, v2:6422-6428. |
| **D. Which sentence does a dashboard enforce?** | run-time reporting | **Contradictory.** Chapter_19:60 vs. Chapter_27:55. |

Part **A** is decided. Parts **B, C, D** are not, and the build's flag is a default on **D** dressed
as a decision about **B**.

### `^7` Rhythm — did it run, how often, does it replay identically

`SUPPORTED BY SOURCE` as measured. I ran the suite: 30/30 pass, and the horizon property was
exercised at scale — "4096 exhaustive policies, deepest chain = 5, none at depth 6" and "500
randomised policies over depths 0..9, horizon held". The Desire-at-horizon behaviour has its own
test and both readings are exercised in one function (engine/test_all.py:267-275). The run replays
identically and writes no files.

What the rhythm shows: the exemption has been exercised thousands of times **as a code path**, and
never once **against a mind**. The README states the ceiling plainly: "MECHANISM ONLY. THIS IS NOT
THE HELM BRAIN. NOTHING HERE HAS RUN INSIDE HELM." (engine/README.md:7)

### `^8` Above/Cause — trace the trigger

`SUPPORTED BY SOURCE` for the trigger chain. What brought this question to Mind was not the book. It
was this sentence, written inside the build about its own flag:

> "**(U3) Is a Desire block at depth 5 also a Structural Deadlock?** Canon defines the deadlock as a
> chain at depth 5 meeting *another blocked node* (any node), but also says `Phi_D` "does not
> contribute to the recursion depth limit". Both readings are exposed: the default keeps Desire
> iterative at depth 5; `iterative_exempt_at_horizon=False` deadlocks it like Power and Wisdom."
> — engine/README.md:182-186

and the build's own warning about it:

> "**U3 is the one that could bite.** If "any block at depth 5 is a deadlock" is the intended
> reading, then the default treatment of Desire at the horizon is wrong. It is a one-flag change and
> a one-test change, but it is a judgement this build made, not one canon settled."
> — engine/README.md:230-232

That is the trigger: the build wrote down its own uncertainty and asked. The book did not open this
question; the build did.

### `^9` Below/Effect — what actually landed

`SUPPORTED BY SOURCE` on what the program says, quoted not paraphrased.

- At a Desire block at depth 5, the default lands on an iterative resolution, not a deadlock:
  `exempt = (node is Node.D) and iterative_exempt_at_horizon` (engine/dwp.py:603), and the comment
  that justifies it: "else: fall through to Phi_D, which adds no level and so cannot exhaust the
  horizon." (engine/dwp.py:614)
- The Rust engine lands the same way, by omission rather than by flag. The Desire block runs its
  exposure loop with **no depth gate at all** (recursive.rs:109-131), while Wisdom and Power are both
  gated — `... && wisdom.blocked && depth < max_depth` (recursive.rs:137) and
  `... && power.blocked && depth < max_depth` (recursive.rs:182). Its own header states the rule:
  "Max recursion depth: 5. Section-retraction holds at every level. Desire loops do NOT count toward
  recursion depth." (recursive.rs:19-20)
- But at the horizon the Rust engine does **not** return a deadlock verdict, because it has no
  deadlock verdict: a search of the whole `rpm` module for `deadlock` or `exhaust` returns **no
  matches**. It reports `max_depth_reached: depth >= max_depth` (recursive.rs:219) and stops. So the
  Rust engine does not corroborate the build's *reading* so much as it fails to implement the
  alternative. That distinction matters and is easy to lose.

## §1.2 Where the seats disagree — stated plainly, not averaged

**Disagreement 1 — the operational rule vs. the formal definition.**

- Seat `^5` and `^2` hold: the exemption is in the published text, twice, and is older than any code
  (Chapter_05:87; Chapter_27:55).
- Seat `^3` and the informal reader in `^1` hold: the deadlock is declared for *a red node at depth
  5*, with no node carve-out (Chapter_19:60), and the formal definition names no node either — it
  says "another blocked node" (v2:6428).

These cannot both govern a dashboard. One of them has to lose. The council does not choose.

**Disagreement 2 — inside one paragraph of the full manuscript.**

- "We define Structural Deadlock as the state where a recursive chain at depth $n=5$ encounters
  another blocked node." — unconditional, v2:6428
- "The architecture cannot spawn another level without violating the global stability axiom."
  — conditional on level-spawning, v2:6428, the very next sentence.

The first sentence makes a Desire block at 5 fatal. The second exempts it. Both are canon.

**Disagreement 3 — the main definition vs. the glossary.**

- "at depth $n=5$" (v2:6428) vs. "**exceeds** the stability horizon of 5 levels" (v2:7095).

Under the glossary, an at-5 block that needs no deeper level is not a deadlock at all — which would
make the entire flag moot, and would also make Chapter_19:60 wrong. Nobody has reconciled these two
sentences, and the council will not do it by preference.

## §1.3 The council's reading

**`READING — NEEDS THE OWNER`.**

What the council will say with the sources behind it:

1. The Desire loop cannot cause a depth-6 chain. That part is **settled** (Chapter_27:55;
   Chapter_05:87).
2. The horizon's own stated justification — "cannot spawn another level" (v2:6428) — is satisfied by
   a Desire block. So the build's default is **the better-supported reading**.
3. That is not the same as canon saying it. Canon does not say it. Canon says both things.

What the council will not say: that the flag is correct, or that the strict setting is wrong. The
choice between them is a governance choice about what a dashboard should shout, and it belongs to the
owner.

## §1.4 What would settle it

**Owner ruling (decides it outright):** does the horizon rule fire on *the node that is blocked*, or
on *the request to go deeper*? One sentence from the owner closes U3 permanently.

**Experiment (narrows it, cannot close it):** a bounded-loop test that the sources cannot supply.
Canon puts no bound on the exposure loop — "until the motivation threshold is reached"
(Chapter_27:55) with no threshold function (engine U8, README:208-211). Run a Desire loop at depth 5
with a threshold that is never reached, and record which of two outcomes an observer will accept:

- the loop runs unbounded and the chain never resolves — this is a *stability* failure, and canon has
  **no name** for it. If this outcome is acceptable, the exemption needs a companion rule, not just a
  flag.
- the harness halts the loop at some iteration count and calls it exhaustion — then the horizon rule
  *does* fire on Desire, and the default is wrong.

Either way the experiment produces a fact the text does not contain. It does not produce a ruling.

---

# Q2 — U10: What counts as "dirty" beyond canon's named Power bypass?

## The question as posed

Theorem 27.3 says a dirty child's retraction fails and the block propagates up, but canon names only
one example: "a Power bypass".

## §2.1 Seat findings — independent

### `^0` Idea — what must exist before "dirty" can be said of anything

`SUPPORTED BY SOURCE`. A "dirty" label attaches to a **resolution**, and only a resolution that
crossed a depth boundary can carry it. The unit is fixed by the definition:

> "For any parent chain at depth $n$, a block at node $K$ triggers a child chain $R^{(n+1)}$ whose
> ultimate output realizes the prerequisite for $K$." — Chapter_27:47

So the artefact is: *one child chain, at one level, that claims to have realized the parent's missing
prerequisite*. Everything the council can say about "dirty" is said about that object, and about no
other.

### `^1` Mind — who reads the rule, and what they are permitted to read

`SUPPORTED BY SOURCE` that the reader is told a **mechanism**, and `SILENT` on the reader being told
a list:

> "If a child chain at any level uses a "dirty" resolution (e.g., a Power bypass), the retraction
> morphism fails, the block propagates back up the stack, and the entire parent chain is
> invalidated." — Chapter_27:63 (identical at v2:6416)

The reader is given: a placeholder term in scare quotes ("dirty"), one example after "e.g.", and a
mechanism. The reader is given no enumeration. Searched: the whole manuscript directory for `dirty`
returns 12 matches across 12 files, and **every one of them is this same sentence**. There is no
second occurrence anywhere in the corpus, and no definitional entry in the glossary.

### `^2` Positive — what the evidence is attracted toward

`SUPPORTED BY SOURCE`. The evidence is attracted toward **"violating the architecture"** as the test,
because that phrase is the sentence immediately before the example and it is not an example:

> "This ensures that a child chain cannot resolve a block by **violating the architecture**."
> — Chapter_27:63

The example follows the general rule; the general rule is not derived from the example. Read that way,
"Power bypass" is an *instance* of "violating the architecture", and the real question becomes: what
does the architecture forbid? Which Chapter 5 answers.

### `^3` Negative — what must be REFUSED

`CONTRADICTED`. **Refused: the claim that canon gives only one example and therefore gives nothing
usable.** The council repels that reading. Canon gives a test, a consequence, and three named
violations. The build's own note understates what it has.

Also **refused outright:** a generated taxonomy. A list of ten plausible "dirty" acts invented to
look complete would be exactly the kind of artefact the owner's rules exist to prevent. The council
will not produce one, and neither should any later agent.

### `^4` Vibration — exact marks

`SUPPORTED BY SOURCE`:

- The corpus contains **exactly one** sentence using the word "dirty". 12 file copies, 1 sentence.
- It contains **exactly one** example: `a Power bypass`.
- It contains **exactly three** chain-level bypasses named in prose: Bypassing Desire
  (Chapter_05:32), Bypassing Wisdom (Chapter_05:33), Power bypass (Chapter_27:63).
- It contains **exactly two** additional child-chain faults filed under other names: Topological
  Deadlock (Chapter_24:59) and Recursive Drift (Chapter_26:52).
- It contains **zero** statements classifying either of those two as "dirty".

The build's arithmetic is right about the corpus and wrong about what the corpus gives it: `(U10)` is
described as "Canon gives exactly one example ("e.g., a Power bypass") and no classification
procedure" (engine/README.md:219). The example count is 1. The classification procedure is present
in the same sentence and was not counted.

### `^5` Female — the accumulated substrate

`SUPPORTED BY SOURCE`. Three deposits, in order of age:

1. **Chapter 5 already named two more bypasses, and called the class fatal.** "If you attempt to
   bypass any of these stages, the cognitive architecture collapses." (Chapter_05:30) then:
   - "**Bypassing Desire (The Hollow Compliance Failure):** If an employee is forced to execute a
     complex new company protocol (Wisdom + Power) without any understanding or belief in *why* it
     matters (lack of Desire/Principle), they will perform the actions mechanically."
     — Chapter_05:32
   - "**Bypassing Wisdom (The Icarus Failure):** ... Attempting Power without Wisdom is like strapping
     a rocket to a bicycle." — Chapter_05:33
2. **Chapter 27 states the rule that makes all three violations.** "Power must always remain
   subordinate to Wisdom, and Wisdom must always remain subordinate to Desire. You can never use the
   end of the chain to permanently manufacture the beginning." (Chapter_27:41)
3. **Chapter 27 then names the one that involves Power machinery.** "e.g., a Power bypass"
   (Chapter_27:63) — because a child chain that bridges a *non-Power* block with *Power* machinery is
   the crossing that Chapter 27:41 forbids most directly. It is the example because it is the cleanest
   case, not because it is the only case.

So the substrate already contains the answer at the level of criterion: **a dirty resolution is one
that crosses a prerequisite boundary the wrong way** — the child solved the parent's blocked node
using machinery from *downstream* of that node.

### `^6` Male — decompose, and name the owner of each part

`SUPPORTED BY SOURCE` for the decomposition. Canon contains **five** candidate members and **one**
criterion. They are not the same kind of thing, and canon files them under different names:

| # | Named fault | Where | What it is | Does canon call it "dirty"? |
|---|---|---|---|---|
| 1 | Power bypass | Chapter_27:63 | child bridges a non-Power block with Power machinery | **Yes** — the named example |
| 2 | Bypassing Desire | Chapter_05:32 | Wisdom+Power executed with no Desire/Principle | No — named a bypass, not called dirty |
| 3 | Bypassing Wisdom | Chapter_05:33 | Power executed without Wisdom (the Icarus failure) | No — same |
| 4 | Topological Deadlock (glue failure) | Chapter_24:59 | "If the child chain's resolution morphism does not satisfy the transition axiom at the glue point, the global sheaf fails to extend, and the system enters a **Topological Deadlock**." | No — **different named outcome** |
| 5 | Recursive Drift | Chapter_26:52 | "If the child chain at depth $n$ is more expansive than its parent (e.g., $CO_8$ nested within $CO_8$), the system is in **Recursive Drift**." | No — different named outcome |

Which part owns which fault, stated plainly:

- **Fault at the retraction identity.** Members 1–3. These are the ones for which the mechanism
  sentence holds: "the retraction morphism fails" (Chapter_27:63). Members 2 and 3 are the same fault
  as member 1, on the other two nodes. Their absence from the example list is an editorial gap, not a
  structural difference.
- **Fault at the gluing.** Member 4. The child resolved something, and the piece does not fit the
  parent's boundary. Canon gives this its **own name and its own outcome** — Topological Deadlock, not
  dirty. Whether a dirty child can also be a glue failure is **not stated**.
- **Fault at the growth rate.** Member 5. The child is larger than its parent. Canon gives this its own
  name — Recursive Drift — and its own verdict: "the fractal calculus proves that this mind is moving
  away from reality and toward an unconstrained hallucination" (Chapter_26:52). Again: not called
  dirty.

**So the decomposition's real answer:** "dirty" in canon is the **retraction-identity** fault only,
and it has three members, one of which is named. The other two named child-chain faults are a
different fault class with different outcomes, and folding them into "dirty" would overwrite two
names canon gave them.

`SILENT` on the enumeration the question asks for: canon nowhere lists the acts that make a resolution
dirty, and nowhere says whether member 4 or member 5 sets the dirty bit. Searched the whole manuscript
directory for `dirty` (12 matches, one sentence, no glossary entry), plus Chapter_21's attack
categories, Chapter_10:81's "Recursive Deadlock", and the appendix D "Topological Deadlock" entry
(v2:7095 region). None of them classifies a fault as dirty.

### `^7` Rhythm — did it run, and does it replay

`SUPPORTED BY SOURCE` as measured. The dirty-propagation path ran and was checked by walking parent
pointers: `dirty child -> root.W.c2 -> root (walked to root)`, and siblings were left valid:
`test_dirty_child_leaves_siblings_valid` (engine/test_all.py:433-442). The failure propagates to the
root, exactly as Chapter_27:63 says.

What the rhythm shows about the *question*: the code does not classify, it **records a caller-supplied
reason**: "It does not decide on its own that a resolution is dirty; the caller names the reason (see
U10)" (engine/README.md:104-105). So U10 does not sit in the classifier — there is no classifier. U10
sits in whoever calls `dirty_child()`. It is a **records** question, not an algorithm question, and
that changes what would settle it.

The engine's own default reason already contains the criterion:

> "dirty child resolution: the child did not satisfy epsilon o eta = id, so its retraction failed and
> the block propagates to every ancestor" — engine/retraction.py:76-79

### `^8` Above/Cause — trace the trigger

`SUPPORTED BY SOURCE`. What triggered this question was the same self-reporting pattern as Q1 — the
build noticing its own gap and writing it down:

> "**(U10) What counts as a "dirty" resolution beyond a Power bypass?** Canon gives exactly one
> example ("e.g., a Power bypass") and no classification procedure. This build does not guess: the
> caller names the reason, and `power_bypass()` is the named helper for the canon example. An unnamed
> judgement therefore cannot enter the record." — engine/README.md:218-222

And behind that, the sentence that opened the whole question:

> "This ensures that a child chain cannot resolve a block by violating the architecture."
> — Chapter_27:63

The trigger is Chapter_27:63 itself. It says "violating the architecture" and then, instead of
enumerating, gives one example. The reader is left holding a rule with a one-item example list.

### `^9` Below/Effect — what the program actually said

`SUPPORTED BY SOURCE`:

- The engine refuses to guess: `dirty_child(parent, child_index=0, reason=DEFAULT_DIRTY_REASON)`
  (engine/retraction.py:278), and "(U10) what counts as dirty beyond the one example canon gives"
  is marked in the code at that point (retraction.py:284).
- The named helper is only the canon example: `POWER_BYPASS_REASON` → "Power bypass: the child bridged
  a non-Power block with Power machinery (CO-8/CO-9 fired to cover a Wisdom or Desire gap) -- the
  example canon gives for a dirty resolution" (engine/retraction.py:81-84).
- The default reason states the mechanism, not the example (retraction.py:76-79, quoted in `^7`).

So the program, asked "what counts as dirty beyond a Power bypass?", answers: **"say the reason
yourself."** It does not answer the question. It defers it.

## §2.2 Where the seats disagree — stated plainly

**Disagreement 1 — "one example and nothing else" vs. "a criterion and three members."**

- The build states: canon gives "exactly one example ... and no classification procedure"
  (engine/README.md:219).
- Seat `^5` and `^2` hold: the sentence before the example is a classification procedure — "violating
  the architecture" (Chapter_27:63) — and Chapter 5 supplies two further members of the same class.

This is not a matter of taste. The build under-counted. The council reports the count as 3 members
and 1 criterion.

**Disagreement 2 — is a glue failure "dirty"?**

- Seat `^6` holds: no. Canon gives it a different name and a different outcome — "the system enters a
  **Topological Deadlock**" (Chapter_24:59), not "the entire parent chain is invalidated".
- A practical reader would hold: yes, functionally — a child that does not glue has also failed to
  realize the prerequisite, and the parent is dead either way.

The council states both and does not merge them. The sources do not say.

**Disagreement 3 — is Recursive Drift a dirty resolution?**

- Seat `^6` holds: no. Chapter_26:52 files it as a fractal signature, with a hallucination verdict,
  under its own name.
- A practical reader would hold: yes — "the child chain at depth $n$ is more expansive than its
  parent" is a child that violates the architecture's growth direction, which is what Chapter_27:63
  forbids.

Again: both stated. The sources do not resolve it.

## §2.3 The council's reading

**Two labels, because the question has two halves and they are not equally answerable.**

**`SETTLED BY SOURCE` — the test.** Canon supplies a criterion, and it is usable today:
a resolution is dirty when the child's Section-Retraction identity fails — "the retraction morphism
fails" (Chapter_27:63) — which canon glosses as "violating the architecture" (Chapter_27:63). The
architecture's own statement of what may not be violated is Chapter_27:41: "Power must always remain
subordinate to Wisdom, and Wisdom must always remain subordinate to Desire."

**`READING — NEEDS THE OWNER` — the list.** Whether the two further Chapter 5 bypasses count as dirty,
and whether the two differently-named child faults (Topological Deadlock, Recursive Drift) fold in,
is a governance choice. It changes what the record calls a failure. Canon did not make it, and the
council will not make it for the owner.

**What the council will say about the build:** the build is **safe** and **under-labelled**. It never
records an unearned "clean". It also never records the two bypasses that Chapter 5 does name, and its
README understates canon by one criterion and two members. Both are fixable in the ledger without any
new invention. Neither can be fixed by the council.

## §2.4 What would settle it

**Owner ruling (decides the list).** One sitting, three questions:
1. Are Bypassing Desire (Chapter_05:32) and Bypassing Wisdom (Chapter_05:33) dirty resolutions when
   they occur *inside a child chain*? The council's reading is yes — same fault, other nodes — but it
   is the owner's call.
2. Does a glue failure (Chapter_24:59) set the dirty bit, or does it stay a Topological Deadlock only?
3. Does Recursive Drift (Chapter_26:52) set the dirty bit, or stay its own verdict?

**Experiment (narrows it, cannot close it).** Take the three named violations and build one child
chain per violation, each with a real `η`/`ε` pair whose composition is then checked at that depth by
the existing `SectionRetraction.verify` (engine/retraction.py:109, :151). Prediction from the sources: all
three fail `ε ∘ η = id`, which would make "dirty" = "retraction fails" operational rather than
nominal. That experiment tests the *criterion*. It cannot test the *naming*, because naming is the
owner's.

---

# Q3 — The depth number

## The question as posed

Five numbers claim the same slot. A proposed reading: **5 is the stability horizon; the lower numbers
are rails that sit INSIDE it and may be stricter; nothing may exceed 5.** Assess whether the sources
support that.

## §3.1 The numbers, with the exact place each was found

| Number | Source | Verbatim / exact form | Verified by me? |
|---|---|---|---|
| **5** | book, Chapter 27 | "recursion is strictly limited to a **maximum depth of 5 levels**" (Chapter_27:59) | read directly |
| **5** | book, Chapter 5 | "recursion is limited to a **maximum depth of 5 levels**" (Chapter_05:87) | read directly |
| **5** | book, Ch. 19 | "up to the CAS limit of **5 recursive levels**" (Chapter_19:56) | read directly |
| **5** | book, Ch. 26 | "across depths $1 \to 5$" (Chapter_26:51) | read directly |
| **5** | full manuscript | "limited to 5 levels ... a stability horizon" (v2:6424) | read directly |
| **5** | Rust engine | `const DEFAULT_MAX_DEPTH: u8 = 5;` (recursive.rs:67) | read directly |
| **4** | CNCM | `max_rpm_depth: int = 4` (cncm/model.py:446) | read directly |
| **4** | rc0 simulator | `max_depth: int = 4` (rc0_types.py:227) | read directly |
| **3** | governance rails | `DEFAULT_RPM_DEPTH_CAP_NORMAL = 3` (governance_rails.py:57) | read directly |
| **2** | governance rails, high stakes | `DEFAULT_RPM_DEPTH_CAP_HIGH_STAKES = 2` (governance_rails.py:58) | read directly |
| **3** | Gate A | ``MAX_OPEN_REPAIRS = 3`` (PREREGISTRATION_GA.md:17); "the fourth descent must be refused" (PREREGISTRATION_GA.md:29) | read directly |
| **3** | Atlas expansion default | `def expand(self, *, max_depth=3, ...)` (rpa_model.py:472) | read directly |
| **log₂(resources) + 3** | Builder's Manual | `Max_depth = log₂(resources) + 3` (survey:73, citing the PDF at pp.58-60, 183-184, 250) | **no — second hand, PDF not opened** |
| **none** | older monad version | Chapter_27:9 records the v6.1 monad was replaced; Correction 2 supersedes it | read directly |

The collector of this table reached the same conclusion and refused to break the tie:
> "### The depth limit: sources disagree (none chosen here)
> 5 — the published book (KDP), the Rust engine, rpm_gate · 4 — rc0, CNCM, "usually 4 levels" (TKS
> equation builder) · 3 — HELM Gate A / repair.py, TKS governance rails (2 high-stakes), the PCBA
> learning constructor, the 2-3 layer training packs, the Atlas's own expansion default ·
> log₂(resources)+3 — Builder's Manual · none — the v6.1 / v7.0 monad (superseded by Correction 2)."
> — survey:83-87

## §3.2 Seat findings — independent

### `^0` Idea — is it one artefact or five?

`CONTRADICTED`. The five numbers are **not** all about the same artefact, and the dispute cannot be
settled until that is said. Three different objects are carrying four of the numbers:

- **RPM recursion depth** — the thing Chapter 27:47 defines and Chapter 27:59 caps at 5. Rust engine,
  rc0, CNCM, Gate A, the rails are all limiting this.
- **Run-time governor caps** — the rails' `3` and `2` are chosen by *operational mode*: "Max RPM depth
  in Normal mode" and "Max RPM depth in High-Stakes mode" (governance_rails.py:102-103). A mode-varying
  limit is a policy artefact, not a structural one.
- **Map expansion depth** — `rpa_model.py`'s `3` is the default for walking links in the Atlas:
  `def expand(self, *, max_depth=3, max_nodes=100, ...)` (rpa_model.py:472), and its own hard ceiling
  is `MAX_DEPTH = 32` (rpa_model.py:29). That is a different quantity from RPM recursion.

So the honest count is: **one structural quantity with at least two competing values (5 and 4), one
policy number that varies by mode (3/2), one default argument (3), and one formula (log₂+3).**
"Five sources, five numbers, one slot" is the framing of the question, and the framing is wrong.

### `^1` Mind — who is permitted to read which number

`SUPPORTED BY SOURCE`. Each reader reads its own and none reads another's:

- the book's reader reads 5 (Chapter_27:59);
- the rails' reader reads a cap from config: `rpm_depth_cap_normal` / `rpm_depth_cap_high_stakes`
  (governance_rails.py:119-120);
- the Atlas's reader reads a default argument, overridable up to 32 (rpa_model.py:29, :472);
- the Gate A reader reads a structural ceiling that must be refused past: "the fourth descent must be
  refused ("maximum depth")" (PREREGISTRATION_GA.md:29).

**No source anywhere tells one reader to consult another's number.** `SILENT` on the exact claim the
nesting reading needs: no source states any relationship between these numbers — not "sits inside",
not "is a rail", not "may be stricter". That is why the nesting reading has no textual home: it is a
claim about a relationship between readers that no reader makes.

### `^2` Positive — what the evidence is attracted toward

`SUPPORTED BY SOURCE` for 5, and the attraction is strong:

- the published book says 5 in four separate chapters (Chapter_05:87; Chapter_19:56; Chapter_26:51;
  Chapter_27:59);
- the full manuscript says 5 and explains why (v2:6424, v2:6428);
- the Rust engine ships 5 (recursive.rs:67);
- every other number in the corpus is **≤ 5** except two (see `^3`).

### `^3` Negative — what must be REFUSED

`CONTRADICTED`. Two things are refused:

1. **Refused: "nothing may exceed 5" as a universal claim.** It is false in the corpus.
   - The Builder's Manual's `Max_depth = log₂(resources) + 3` (survey:73) passes 5 as soon as
     resources pass 4, with no ceiling stated.
   - The Atlas's own hard ceiling is 32: `MAX_DEPTH = 32` (rpa_model.py:29). Its `3` is a default, and
     the same function will walk to 32 if asked.
2. **Refused: "the lower numbers are rails inside 5."** No source says it, and one actively resists it.
   `governance_rails.py` calls its number a **cap** and refuses past it:
   `reason=f"RPM depth {current_depth} exceeds cap {depth_cap}",` (governance_rails.py:632). A cap that
   refuses is a ceiling in its own right. Calling it "a stricter rail inside 5" is a re-description of
   a ceiling as a sub-limit, and nothing in the file licenses the re-description.

### `^4` Vibration — exact marks

`SUPPORTED BY SOURCE`, all numbers exact:

- 5: stated in 4 book chapters and the manuscript, plus `DEFAULT_MAX_DEPTH: u8 = 5` in code.
- 4: exactly 2 implementations (`cncm/model.py:446`; `rc0_types.py:227`).
- 3: Rails normal (governance_rails.py:57), Gate A (PREREGISTRATION_GA.md:17), Atlas default
  (rpa_model.py:472) — **3 sources**.
- 2: Rails high-stakes (governance_rails.py:58) — 1 source.
- 32: Atlas hard ceiling (rpa_model.py:29) — 1 source, and it is a different quantity.
- 0: no source gives a depth-6 chain or higher a verdict. The Rust test suite's own claim, which I
  reproduced: `4096 exhaustive policies, deepest chain = 5, none at depth 6`.

### `^5` Female — the accumulated substrate

`SUPPORTED BY SOURCE`. Before this session invented anything, the corpus already contained:

- **5 as the horizon, with its reason stated.** "Why is the recursion depth limited to 5 levels? In
  the formal manifold of CAS, this limit is not an arbitrary performance cap, but a stability
  horizon." (v2:6424)
- **The bands inside 5, stated by the book itself.** Tier 2 "Limited to a recursion depth of 0"
  (Chapter_19:54); tier 3 "handling a depth of 1-3" (Chapter_19:55); tier 4 "up to the CAS limit of
  **5 recursive levels**" (Chapter_19:56). **This is the single strongest canonical support for the
  nesting reading.** It is canon, not inference: the book puts 0, 1–3, and up-to-5 on one axis as
  bands of capability.
- **A convergence requirement across the same range.** "The sequence of fractal signatures across
  depths $1 \to 5$ must show an increasing density of contracting operators (CO-3, CO-9)."
  (Chapter_26:51)
- **The supersession of "none", in canon's own words.** "In the original v6.1 specifications of CAS,
  the RPM chain was modeled as a "Monad" ... In the corrected v7.4 mathematics, this was revised."
  (Chapter_27:9)

### `^6` Male — decompose; name the owner of each part

`SUPPORTED BY SOURCE`. Three parts, three owners:

| Part | What it asks | Owner |
|---|---|---|
| **A. Where does the structural ceiling sit?** | structure | **Book + Rust engine: 5.** rc0/CNCM dissent at 4. Not the owner's to decide by preference — it is decided by which document is canonical, and canon says 5 in five places. This part is close to settled. |
| **B. Is each lower number the same quantity?** | identity of the variable | **Partly false.** Rails = a mode-varying *policy cap*. Atlas `3` = a *default argument* on a map walker whose ceiling is 32. Gate A `3` = *open repair frames*, which is a stack-depth ceiling on nested repairs. Only rc0's and CNCM's `4` are the same quantity as the book's `5`. This is where the nesting reading's supporting evidence breaks: **four of the five "competing numbers" are not the same variable.** |
| **C. May anything exceed 5?** | governance | **Owner.** Book says no ("strictly limited", Chapter_27:59; "cannot spawn another level without violating the global stability axiom", v2:6428). Builder's Manual says it varies with resources. Atlas's ceiling is 32. Somebody has to say which wins, and it is not a question the mathematics answers. |

### `^7` Rhythm — did it run

`SUPPORTED BY SOURCE` as measured. The 5-horizon ran 4096 exhaustive policies and 500 randomised
policies over depths 0..9 with the horizon holding. The 4s and 3s have their own lives: Gate A's
preregistration records four attempts including two failures held on the record — "Run
`helm_gate_a_nested_repair_c10_20261007` (7:23 to 7:28 PM Pacific) failed by code error before any
world took" (PREREGISTRATION_GA.md:52) and "attempt 1 and a FAIL on the frozen criterion"
(PREREGISTRATION_GA.md:71-72). So the 3 in Gate A is a number that has been **exercised against a real
run and failed once before it passed**. The 5 in the book has never been exercised against anything
but its own unit tests.

That asymmetry is not an argument for 3. It is a statement about which number carries evidence.

### `^8` Above/Cause — trace the trigger

`SUPPORTED BY SOURCE`. The trigger for this third question is the build noticing that it had pinned a
number and could not defend the pin:

> "Different sources in this corpus give different recursion-depth numbers. They are not variants of
> one number; they disagree, and this build does not pretend otherwise." — engine/README.md:143-144

> "**This build pins 5.** The pin is a *reading* of the book, not a quotation" — engine/README.md:154

and it names the exact risk the proposal under review is trying to close:
> "**The pin is a reading.** 5 is pinned because the book says 5, not because this build proved 5 is
> correct." — engine/README.md:228-229

And behind the build, the collector who would not choose: "nothing here chooses between conflicting
sources" (survey:7); "none chosen here" (survey:83).

### `^9` Below/Effect — what the program actually said

`SUPPORTED BY SOURCE`:

- the engine pins 5 and says so: `HORIZON = 5` (engine/depth.py:63), with the reasoning printed beside
  it — including the honest note that the brief's phrasing "a stability horizon, not an arbitrary cap"
  is **not** the book's sentence: "The brief paraphrases this as "depth 5 is a stability horizon, not
  an arbitrary cap". That exact sentence is NOT in the manuscript" (engine/depth.py:56-60).
- it refuses to raise the number when inconvenient: "It does NOT raise the limit when the limit is
  inconvenient." (engine/depth.py:19)
- the Atlas, asked to expand, uses 3 and can go to 32 (rpa_model.py:472, :29).
- the rails, asked to permit depth, refuse: `"RPM depth {current_depth} exceeds cap {depth_cap}"`
  (governance_rails.py:632).

## §3.3 Does the corpus support the proposed nesting reading?

The proposal has three clauses. They do not fare equally.

### Clause 1 — "5 is the stability horizon."

**`SUPPORTED BY SOURCE`.** Stated and reasoned:
> "Why is the recursion depth limited to 5 levels? In the formal manifold of CAS, this limit is not an
> arbitrary performance cap, but a stability horizon." — v2:6424

> "The architecture cannot spawn another level without violating the global stability axiom."
> — v2:6428

**One correction, and it is the build's own:** the exact phrase "a stability horizon, not an arbitrary
cap" is the build's paraphrase, not the book's. The book says "not an arbitrary performance cap, but a
stability horizon". The build flags this itself (engine/depth.py:56-66). Quote the book's order, not
the paraphrase's.

### Clause 2 — "The lower numbers are rails that sit INSIDE it and may be stricter."

**`READING — NEEDS THE OWNER`.** Half the evidence helps, half refuses.

**Helps:**
- Every number in the corpus is **≤ 5** except the Builder's Manual formula and the Atlas's internal
  `MAX_DEPTH = 32`.
- The book itself bands the space *inside* the limit: tier 2 = 0, tier 3 = 1–3, tier 4 = up to 5
  (Chapter_19:54-56). This is canon's own nesting of smaller numbers inside 5.
- The rails' own two numbers nest trivially inside one another — 2 (high-stakes) inside 3 (normal) —
  which shows the corpus does use stricter-inside-looser limits as a real pattern
  (governance_rails.py:57-58).

**Refuses:**
- **No source states the relationship.** Nothing says the rails' 3 sits inside the book's 5. The
  relationship is the proposal's, not the sources'.
- **The rails' number is named a cap and enforces refusal**:
  `reason=f"RPM depth {current_depth} exceeds cap {depth_cap}"` (governance_rails.py:632), with the
  mandated action "Reduce depth" (governance_rails.py:634). A cap that refuses is a ceiling, not a
  sub-limit. Describing it as "a rail inside 5" changes what the code means.
- **The Atlas's 3 is a default argument, not a maximum.** `def expand(self, *, max_depth=3, ...)`
  (rpa_model.py:472) with `MAX_DEPTH = 32` above it (rpa_model.py:29). Its ceiling is 32, so on that
  reading the Atlas does not sit inside 5 at all — it exceeds it six times over. The proposal would
  have to exclude the Atlas's own ceiling to keep the Atlas's default inside, and nothing tells us to.
- **rc0 and CNCM are not "stricter rails".** Their `4` is the same quantity as the book's `5` — the
  ceiling on RPM recursion — with no mode switch, no override, and no comment calling itself a rail.
  `max_rpm_depth: int = 4` (cncm/model.py:446) is a peer of `DEFAULT_MAX_DEPTH: u8 = 5`
  (recursive.rs:67), not a subordinate of it. The proposal has to *decide* that 4 is a rail. That
  decision is not in the text.

### Clause 3 — "Nothing may exceed 5."

**`CONTRADICTED`** — twice, and the council states it rather than resolving it.

1. **Builder's Manual:** `Max_depth = log₂(resources) + 3` (survey:73). For resources = 4 it gives
   exactly 5; for resources = 8 it gives 6; for 64 it gives 9. There is no stated cap. Under this
   formula, "nothing may exceed 5" is false by construction as soon as resources are not tiny.
2. **Atlas:** `MAX_DEPTH = 32` (rpa_model.py:29). Whatever quantity that is, it is not bounded by 5.

The honest defence of clause 3 is that both of these are **different quantities** (a resource-scaled
heuristic, and a map-expansion ceiling). That defence may well be right. But it is a defence the
proposal must make explicitly, and having made it, clause 3 becomes "nothing may exceed 5 **for RPM
recursion depth specifically**" — a narrower and more defensible claim than the one proposed.

## §3.4 The council's reading

**On the number: `CANNOT BE SETTLED FROM SOURCES`.** The 5-vs-4 conflict is two live values for one
quantity and no source breaks the tie. The survey declined. The build declined. The council declines
for the same reason: a tie between documents is not a fact about the world, so no amount of reading
creates one.

**On the proposed nesting reading: `READING — NEEDS THE OWNER`.**

The council's finding, stated without softening:

- **Clause 1 is supported.** 5 is called a stability horizon (v2:6424).
- **Clause 2 is half-supported and the half that fails is load-bearing.** The banding evidence is real
  (Chapter_19:54-56). But four of the five "competing numbers" are not the same variable — a policy
  cap, a default argument, a repair-frame ceiling, and a map-expansion ceiling — so most of the
  "tension" the proposal resolves is not tension. Only rc0's and CNCM's 4 genuinely competes with 5,
  and the proposal labels that one a rail without any source saying so.
- **Clause 3 is contradicted** by the Builder's Manual formula and by the Atlas's `MAX_DEPTH = 32`,
  unless limited to RPM recursion depth specifically. Limited that way, it is what the book says:
  "strictly limited to a maximum depth of 5 levels" (Chapter_27:59).

**Verdict on the proposal:** it is a **reasonable house rule** and it is **not a reading of the
sources**. It converts a genuine disagreement (5 vs. 4) into a hierarchy by fiat, and it quietly
demotes the one number that actually competes. The council will not present it as supported. It can be
presented as the council's *recommended* house rule — which is a different claim, and one that needs
the owner's signature, not the council's.

**The disagreement the council will not average away:** the book's 5 and rc0/CNCM's 4 are the same
quantity, and there is no third source that says 4 is subordinate. The nesting reading makes that
problem disappear without answering it. That is the difference between a rule and a reading.

## §3.5 What would settle it

**Owner ruling (required, and it is the only thing that can close it).** Four questions:
1. Is RCA/CNCM's 4 a defect to be fixed to 5, a stricter rail to be declared, or a deliberate divergence?
2. Is the Builder's Manual's `log₂(resources) + 3` admitted into CAS, excluded, or admitted only below 5?
3. Is the Atlas's expansion depth a different quantity from RPM recursion depth — i.e. is `MAX_DEPTH = 32`
   correct as written?
4. Does the horizon rule govern *all* depth numbers, or only RPM recursion?

**Experiments (narrow, and cannot decide a naming question).**
- **The horizon sweep, already run.** `4096 exhaustive policies, deepest chain = 5, none at depth 6`
  (my run of `test_all.py`). This proves the *consequence* of pinning 5, and it is proved at 5 only.
  Re-running it with `HORIZON` set to 4 and to 3 would show exactly what changes downstream — that is
  one line (engine/README.md:158-159) and one re-run. It would tell the owner what each choice *costs*.
  It would not tell anyone which is right.
- **The convergence test canon implies and nobody has run.** Chapter_26:51 requires "an increasing
  density of contracting operators (CO-3, CO-9)" across depths $1 \to 5$. That is a **falsifiable
  claim about how minds actually recurse**, and it is the only place in the corpus where the number 5
  is given a testable consequence rather than a boundary. If observed recursion in real cognitive
  traces runs out of contracting operators before 5, the horizon is too high. If it still converges at
  5, 5 is safe. **This is the one experiment in the whole question set that could produce a fact that
  bounds the number from the evidence rather than from preference.** It needs a corpus of real
  recursive traces, which does not exist yet.

---

# Appendix A — Every number the council found, exact

| Quantity | Value | Where |
|---|---|---|
| Horizon, book | 5 levels | Chapter_05:87; Chapter_19:56; Chapter_26:51; Chapter_27:59; v2:6424 |
| Horizon, Rust engine | `5` | recursive.rs:67 |
| Horizon, dwp_engine | `5` | engine/depth.py:63 |
| CNCM | `4` | cncm/model.py:446 |
| rc0 simulator | `4` | rc0_types.py:227 |
| Rails, normal | `3` | governance_rails.py:57 |
| Rails, high-stakes | `2` | governance_rails.py:58 |
| Gate A open repairs | `3` | PREREGISTRATION_GA.md:17 |
| Atlas expansion default | `3` | rpa_model.py:472 |
| Atlas hard ceiling | `32` | rpa_model.py:29 |
| Lacunarity divisor | `4` | v2:6420 |
| Tests passing (measured) | `30/30` | my run |
| Depth-6 chains (measured) | `0` | my run: "none at depth 6" |
| Policies swept (measured) | `4096` exhaustive + `500` randomised | my run |

# Appendix B — What the council did not read (bounded silence)

The council's `SILENT` findings are scoped to what it actually searched. It did **not** read:

- the published KDP PDF, the DOCX editions, or the EPUBs (the survey reports they carry the same
  Chapter 27 text; I did not verify);
- the Builder's Manual PDF — so the `log₂(resources) + 3` formula is second hand (survey:73);
- `Thinking_in_Cognitive_Architecture_FINAL.docx` and `Thinking_in_Cognitive_Architecture.docx`, which
  the survey reports contain **none** of Def 27.2, Theorem 27.3, the depth-5 limit or Structural
  Deadlock (survey:31-32) — an edition gap the council did not verify and which, if real, is itself a
  source of the disagreement;
- the TKS conversation transcripts, the training packs, the PCBA documents, the monographs and the
  incident database.

Nothing in this document turns on any of them, except the one Builder's Manual number, which is
labelled.

# Appendix C — One thing the council wants said plainly

The three questions were not opened by the book. They were opened by a build that wrote its own
uncertainty into a ledger and refused to paper over it — `(U3)`, `(U9)`, `(U10)` and seven others,
each pinned to a documented default, each listed in a README, and a test that checks the list and the
code agree (`10 UNDECIDED markers, all listed in README.md`, my run). The book does not contain that
habit. The build does.

That is why two of the three questions come out `NEEDS THE OWNER` rather than `CANNOT BE SETTLED`:
the questions were asked precisely. They are answerable — by the owner, or by the one experiment per
question named above. They are not answerable by more reading, because the council has now read it
all and the text says both things.
