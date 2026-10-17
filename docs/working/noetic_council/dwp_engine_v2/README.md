# DWP Recursion Engine (v2 — the owner's ruling of 2026-10-16)

A standalone, standard-library-only implementation of the D/W/P recursion engine described in
the published book canon (Chapters 5 and 27, plus the lacunarity and deadlock pass in the full
manuscript).

**MECHANISM ONLY. THIS IS NOT THE HELM BRAIN. NOTHING HERE HAS RUN INSIDE HELM.**

That line is the claim ceiling for this whole directory. Nothing in it is a statement about
Helm, about a mind, about a model, or about any deployed system. It is a mechanism, written to
the book's definitions, with its own tests. That is all it claims.

## What changed from `dwp_engine` (v1) and why

Two numbers moved, on the **owner's explicit ruling of 2026-10-16**. Nothing else moved.

| constant | was | now | what job it does |
| --- | --- | --- | --- |
| `depth.HORIZON` | 5 | **12** | the depth at which a further block is a Structural Deadlock |
| `dwp.DESIRE_BOUND` | unbounded | **12** | how many times a Desire loop may cycle in place before it must stop |

**Both numbers are 12, and they are two different numbers doing two different jobs.** They stay
two named constants with two comments. The Desire loop still does **not** count toward depth —
that rule is unchanged, and it stays true even when the loop exhausts its bound.

**12 is the owner's ruling. It is not derived from canon.** The published book says 5 ("a
maximum depth of 5 levels"), and so does the Rust engine. The sources do not support 12. Every
place the number appears now says so, and `depth.py` keeps the book's own sentence beside the
ruling, unedited: canon calls 5 **"not an arbitrary performance cap, but a stability horizon."**
That quote is still true of the book. It is no longer a description of the number this build
pins.

What became more permissive: a chain may now go twelve levels deep instead of five, so a block
at depth 6, 7, 8, 9, 10 or 11 is now a REPAIR (or a normal resolution) where it used to be a
refusal. What became more restrictive: a Desire loop may no longer cycle without limit; the
13th cycle is refused with the typed word `DESIRE_BOUND_EXHAUSTED`. Before this build, a
1000-cycle loop was legal by construction.

---

## What is here

| File | What it is |
| --- | --- |
| `dwp.py` | The three nodes (D/W/P), the `Blocked` outcome, `resolve()` -- the three resolution functors -- and `DESIRE_BOUND = 12` with the `DesireLoop` runner. |
| `depth.py` | `HORIZON = 12`, `check_depth()`, and `flatten()` -- the horizontal decomposition that replaces a deadlock. |
| `retraction.py` | `SectionRetraction` (the eta/epsilon pair) checked per depth, and dirty-child propagation to the root. |
| `lacunarity.py` | `1 - (mechanisms used / 4)` in exact `fractions.Fraction`. |
| `test_all.py` | The whole suite. Plain Python, no pytest. |

Run the tests:

```
python -B test_all.py
```

No third-party packages. No network. No files written. No spend.

---

## The canon it obeys

Every rule is quoted at the point in the code where it is applied. The load-bearing quotes:

- **Definition 27.2 (Recursive Depth).** "For any parent chain at depth n, a block at node K
  triggers a child chain R^(n+1) whose ultimate output realizes the prerequisite for K."
- **Phi_P (Power).** "It spawns a **single** child chain to solve a resource gap."
- **Phi_W (Wisdom).** "This is the **only** case allowing parallel morphisms. Via CO-6, the
  Wisdom node splits into a **coproduct** of child chains."
- **Phi_D (Desire).** "**Iterative**, not recursive. It does not spawn child chains ... Because
  it is iterative, it does not contribute to the recursion depth limit."
- **Structural Deadlock.** "the state where a recursive chain at depth n=5 encounters another
  blocked node ... The architecture cannot spawn another level without violating the global
  stability axiom."
- **The fix.** "We move from vertical recursion to **horizontal decomposition**."
- **Theorem 27.3 (Depth-Wise Integrity).** "the Section-Retraction identity epsilon^(n) o
  eta^(n) = id^(n) must hold **independently**." A dirty child "propagates back up the stack,
  and the entire parent chain is invalidated."
- **Lacunarity.** "1 - [mechanisms used / 4]".

Quotes are ASCII transliterations: the manuscript's LaTeX (`\Phi`, `\circ`, `\bigoplus`, `\to`,
`\lor`, `\Rightarrow`) appears as `Phi`, `o`, `(+)`, `->`, `v`, `=>`. Wording is untouched.

---

## Module by module

### `dwp.py`

**Does.** Defines `Node` (D, W, P), `Blocked`, `State`, the `Chain` record, and one dispatcher
`resolve(node, blocked, depth, state)`:

- **P blocked -> exactly one child chain, tag `SINGLE`.** Asking for two is refused, and the
  `SingleChildResolution` class cannot even be built with two.
- **W blocked -> a coproduct of at least two child chains, tag `PARALLEL`.** One child is
  refused. The `CoproductResolution` class cannot be built with one.
- **D blocked -> no child chains at all, tag `ITERATIVE`, and the depth does not move.**

Getting a child out of a Desire resolution is not discouraged, it is impossible: the result
class for Desire has no `children` field, is not a `SpawnedResolution`, and the module-level
accessor `child_chains()` raises `NoChildrenError`. There is nothing to read.

**Also does — the Desire loop's bound.** `DESIRE_BOUND = 12` (the owner's ruling of 2026-10-16;
canon bounds `N` in `loop(N)` nowhere). `resolve()` refuses a state asking for more than 12 cycles
by raising `DesireBoundExhausted`, whose typed word is `DESIRE_BOUND_EXHAUSTED`. `DesireLoop`
runs a resolution's cycle in place and raises the same word on the 13th cycle. Neither the refusal
nor the runner touches the depth counter — a Desire loop adds no level, before or after the bound.

**Does not.** It does not detect blocks (they arrive from outside). It does not score a mind,
measure satisfaction, or compute any metric. It does not implement the CO- operators -- it
names them, in the book's order, and leaves their meaning to the caller. It does not decide the
depth limit (that is `depth.py`). It does not resolve a deadlock. It does not decide how many
cycles a loop *should* run; it only refuses more than the ruled bound.

### `depth.py`

**Does.** Pins `HORIZON = 12` — the owner's ruling of 2026-10-16, not derived from canon (canon
says 5, and the book's own sentence is kept in `HORIZON_QUOTE` next to the ruling).
`check_depth(depth)` answers one question: may a block at this depth spawn anything deeper? `OK`
below the horizon, `STRUCTURAL_DEADLOCK` at or beyond it. `flatten(chain)` takes a chain that
reached the horizon and returns same-level siblings, tagged `HORIZONTAL`, with no children and no
deeper level -- the fix, not an exception and not a retry. `assert_within_horizon(chain)` walks a
whole tree and refuses if anything sits above the horizon.

**Does not.** It does not resolve blocks. It does not raise the number when the number is
inconvenient -- and it did not raise it to 12: the ruling did. It does not choose the content of
the horizontal split beyond a documented placeholder (see U6 below). It does not bound the Desire
loop; that is `dwp.DESIRE_BOUND`, a different number doing a different job.

### `retraction.py`

**Does.** `SectionRetraction` holds one depth's eta (embed) and epsilon (realize) and checks
`epsilon o eta = id` **at that depth only**; it refuses to certify any other depth.
`RetractionRegistry.verify(depth)` consults exactly one depth's pair and nothing else, and each
pair keeps a call log so the independence can be shown rather than claimed. `dirty_child()`
marks one child dirty, marks every ancestor above it invalid, and walks the block to the root,
returning the propagation path.

**Does not.** It does not check `eta o epsilon = id` -- the book explicitly does not require it,
and checking it would be a different theorem. It does not decide on its own that a resolution is
dirty; the caller names the reason (see U10). It does not invalidate the dirty child's siblings
(see U9). It has no undo: canon calls the retraction destructive.

### `lacunarity.py`

**Does.** `resolution_lacunarity(n) = 1 - n/4` as an exact `Fraction`. `0 -> 1`, `1 -> 3/4`,
`2 -> 1/2`, `3 -> 1/4`, `4 -> 0`. Five mechanisms is refused (it is a bad count, not a better
score). Floats, strings and booleans are refused so the arithmetic stays exact. The inverse
`mechanisms_used()` round-trips, and `describe()` prints the exact value and the absent
pathways.

**Does not.** It does not inspect anything to find out how many mechanisms a system has. It does
not decide *which* four mechanisms count (see U1). It does not clamp, round, average, or turn
the result into a verdict.

---

## What the tests prove

`test_all.py` runs 33 tests and asserts, among other things:

- P spawns exactly 1 child; W spawns 2, 3 and 4 and refuses 1; D spawns 0 and leaves depth alone.
- A block at depth 12 returns `STRUCTURAL_DEADLOCK` and nominates no depth-13 child.
- `flatten` returns siblings at the same level, never deeper, and refuses below the horizon.
- **No path reaches depth 13.** Every depth-indexed blockade policy over depths 0-12 is covered:
  4 ** 13 = **67,108,864** policies. The full space is covered by an exact collapse that the test
  proves rather than assumes — the deepest chain is `min(leading W/P run, 12)` — checked by
  building and walking **20,480** whole policies (all 4 ** 6 = 4,096 and all 4 ** 7 = 16,384),
  then by building **16,384** real trees for the 8,192 advance/stop patterns (each pattern built
  twice: Wisdom-advance and Power-advance), then by counting 8,192 patterns x 8,192 policies =
  67,108,864 = 4 ** 13. Deepest chain seen: 12. Chains at depth 13: zero. Plus 500 randomised
  path-dependent policies over depths 0-20.
- The Desire loop allows exactly **12** cycles and refuses the 13th as `DESIRE_BOUND_EXHAUSTED`
  — proved both where the loop is planned (`resolve`, 12 accepted / 13 refused) and where it is
  run (`DesireLoop.step`, the 13th step raises).
- A Desire loop refused by its own bound **never changed the depth counter**: checked at every
  depth 0-12, the depth, `child_depth` and `ITERATIVE` tag are exactly where they were.
- A Desire loop at depth 12 with 13 cycles is refused as `DESIRE_BOUND_EXHAUSTED`; Power and
  Wisdom at depth 12 are refused as `STRUCTURAL_DEADLOCK`. The two words are not interchangeable.
- A dirty child invalidates every ancestor, proven by walking parent pointers to the root.
- Retraction holds at every depth 0-12, and a failing pair at depth 3 neither pollutes nor is
  rescued by the depth-1 check (verified by the pairs' own call logs).
- Lacunarity is exact and refuses 5.
- Every `UNDECIDED IN CANON (Un)` marker in the modules is listed in this README.

---

## The number is not agreed

Different sources in this corpus give different recursion-depth numbers. They are not variants
of one number; they disagree, and this build does not pretend otherwise.

| Depth | Source |
| --- | --- |
| 5 | The book (Chapter 5 "a maximum depth of 5 levels"; Chapter 27 "strictly limited to a maximum depth of 5 levels"; full manuscript "limited to 5 levels ... a stability horizon"), and the Rust engine |
| 4 | rc0, CNCM |
| 3 | Gate A, the governance rails, the Atlas expansion default |
| log2(resources) + 3 | the Builder's Manual |
| none | the older monad formulation (v6.1), which had no depth horizon at all |

**This build pins 12, and 12 is not in that table because no source in this corpus says 12.**
Twelve is the owner's ruling of 2026-10-16. It is not a reading of the book, not a computation
from the sources, and not a result of anything in this package. `depth.py` says so in a comment
directly above `HORIZON`, and it keeps the book's own sentence next to it ("not an arbitrary
performance cap, but a stability horizon") so that the distance between the book's 5 and the
ruling's 12 is visible in the file rather than only in this README. If the ruling is withdrawn,
`HORIZON = 12` is the single line to change, and the whole suite re-proves the horizon property
at whatever number is put there.

The Desire loop's bound, `DESIRE_BOUND = 12` in `dwp.py`, is a *second* ruling of the same day.
It is not the same number as `HORIZON` even though it has the same value: canon bounds `N` in
`loop(N)` nowhere, so before the ruling there was no number at all.

---

## UNDECIDED IN CANON -- the full list

Every point the canon does not settle is marked in the code with
`# UNDECIDED IN CANON (<id>): <question>` and pinned to a documented default. A test checks that
this list and the code agree.

- **(U1) Which four mechanisms count in `1 - (mechanisms used / 4)`?**
  Canon gives the formula, the divisor 4, and one contrast (Power via CO-8/9 versus Wisdom via
  CO-6), but never enumerates the four. The reading used for labelling: `Phi_P (CO-8 o CO-9)`,
  `Phi_W via CO-5`, `Phi_W via CO-6`, `Phi_D (CO-1 o CO-4 o CO-7)` -- the three functors with
  Wisdom split by its two operators, the only split that yields exactly four from the material
  given. The divisor is quoted; the membership of the list is not. *(lacunarity.py)*

- **(U2) Is the root chain depth 0 or depth 1?**
  Canon says "a maximum depth of 5 levels" and "a recursive chain at depth n=5" without fixing
  the origin. This build pins the root at depth 0, so a block at depth **12** is the deadlock and
  depth **13** cannot occur. (Canon's number is 5; the horizon is 12 by the owner's ruling of
  2026-10-16 — see U11.) A root-at-1 reading changes the label of the root, not the arithmetic.
  *(dwp.py)*

- **(U3) Is a Desire block at the horizon also a Structural Deadlock?**
  Canon defines the deadlock as a chain at depth 5 meeting *another blocked node* (any node),
  but also says `Phi_D` "does not contribute to the recursion depth limit". Both readings are
  exposed: the default keeps Desire iterative at the horizon (depth 12); with
  `iterative_exempt_at_horizon=False` it deadlocks like Power and Wisdom. *(dwp.py)*

- **(U4) What is the minimum arity of the Wisdom coproduct?**
  Canon says the node "splits into a coproduct" and prints a two-child example, but states no
  minimum. This build refuses 1: a coproduct of one is not a split, and calling it parallel
  would misreport a single chain as a branch. *(dwp.py)*

- **(U5) May `flatten` be used below the horizon?**
  Canon presents flattening only as the deadlock repair. This build refuses it below the
  horizon rather than license a shortcut canon never granted. *(depth.py)*

- **(U6) What are the sub-problems of a horizontal decomposition?**
  Canon says "solving sub-problems at the same depth level" without saying what they are. This
  build uses the chain's own CO-6 decomposition when it has one, and two clearly labelled
  placeholders (`<label>#h1`, `<label>#h2`) when it does not. Callers with real structure should
  pass `parts=`. *(depth.py)*

- **(U7) Is the CO-5 route a "parallel morphism"?**
  Canon calls Wisdom resolution the only case allowing parallel morphisms, but the CO-5 example
  produces one resonant child, not a split. This build tags CO-5 `SINGLE`, keeps the >= 2 rule
  on CO-6 only, and defaults to CO-6. *(dwp.py)*

- **(U8) Is N in `(CO-1 o CO-4 o CO-7)^N` bounded, and at what value?**
  Canon writes `loop(N)` and says the loop runs "until the motivation threshold is reached",
  with no maximum and no threshold function. The **owner ruled 12 on 2026-10-16**, and that
  ruling is the entire warrant for `DESIRE_BOUND = 12`: a loop may cycle 12 times, and the 13th
  is refused with `DESIRE_BOUND_EXHAUSTED`. Before the ruling this build took N from the caller
  and enforced only `N >= 0`, which is why a 1000-iteration loop used to be legal. *(dwp.py)*

- **(U11) Which number should the recursion horizon be?**
  Canon says 5 in three places, the Rust engine uses 5, and 12 appears in no source in this
  corpus. The **owner ruled 12 on 2026-10-16**, and that ruling is the entire warrant for
  `HORIZON = 12`: 12 is not derived from canon and this build does not claim it is. The ruling
  is kept beside the book's own sentence ("not an arbitrary performance cap, but a stability
  horizon"), not in place of it. *(depth.py)*

- **(U9) Are the siblings of a dirty child invalidated too?**
  Canon names only "the entire parent chain", which is the ancestor line. This build invalidates
  ancestors only; a dirty sibling does not condemn coproduct parts that resolved cleanly.
  *(retraction.py)*

- **(U10) What counts as a "dirty" resolution beyond a Power bypass?**
  Canon gives exactly one example ("e.g., a Power bypass") and no classification procedure.
  This build does not guess: the caller names the reason, and `power_bypass()` is the named
  helper for the canon example. An unnamed judgement therefore cannot enter the record.
  *(retraction.py)*

---

## The honest weak points

- **Both pins are rulings, not readings.** 12 is pinned for the horizon and 12 for the Desire
  loop because the owner ruled so on 2026-10-16, not because this build found 12 anywhere. The
  table above is the evidence that the published number is contested, and 12 is not even in it.
- **U3 is the one that could bite.** If "any block at the horizon is a deadlock" is the intended
  reading, then the default treatment of Desire at the horizon is wrong. It is a one-flag change
  and a one-test change, but it is a judgement this build made, not one canon settled.
- **The biggest new risk is the distance between the two 12s.** They are different numbers doing
  different jobs, and they are one typo apart in the source. If a later edit ever lets the desire
  bound leak into the depth arithmetic — for instance by counting loop cycles as levels — a
  Desire loop at depth 12 would start reporting `STRUCTURAL_DEADLOCK` when it should report
  `DESIRE_BOUND_EXHAUSTED`, and the two refusals would become indistinguishable in a record.
  Two tests exist to catch exactly that, at every depth 0-12.
- **`flatten` is structurally proven, not semantically proven.** The tests prove the siblings
  are flat, same-level, tagged, and childless. They cannot prove the decomposition is the *right*
  one, because canon does not say what the right one is (U6).
- **Nothing here has been compared to Helm, to a model, or to a mind.** The engine is consistent
  with the book's definitions and with itself. That is the entire claim.

**MECHANISM ONLY. THIS IS NOT THE HELM BRAIN. NOTHING HERE HAS RUN INSIDE HELM.**
