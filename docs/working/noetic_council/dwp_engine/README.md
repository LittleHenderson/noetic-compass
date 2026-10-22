# DWP Recursion Engine

A standalone, standard-library-only implementation of the D/W/P recursion engine described in
the published book canon (Chapters 5 and 27, plus the lacunarity and deadlock pass in the full
manuscript).

**MECHANISM ONLY. THIS IS NOT THE HELM BRAIN. NOTHING HERE HAS RUN INSIDE HELM.**

That line is the claim ceiling for this whole directory. Nothing in it is a statement about
Helm, about a mind, about a model, or about any deployed system. It is a mechanism, written to
the book's definitions, with its own tests. That is all it claims.

---

## What is here

| File | What it is |
| --- | --- |
| `dwp.py` | The three nodes (D/W/P), the `Blocked` outcome, and `resolve()` -- the three resolution functors. |
| `depth.py` | `HORIZON = 5`, `check_depth()`, and `flatten()` -- the horizontal decomposition that replaces a deadlock. |
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

**Does not.** It does not detect blocks (they arrive from outside). It does not score a mind,
measure satisfaction, or compute any metric. It does not implement the CO- operators -- it
names them, in the book's order, and leaves their meaning to the caller. It does not decide the
depth limit (that is `depth.py`). It does not resolve a deadlock.

### `depth.py`

**Does.** Pins `HORIZON = 5`. `check_depth(depth)` answers one question: may a block at this
depth spawn anything deeper? `OK` below the horizon, `STRUCTURAL_DEADLOCK` at or beyond it.
`flatten(chain)` takes a chain that reached the horizon and returns same-level siblings, tagged
`HORIZONTAL`, with no children and no deeper level -- the fix, not an exception and not a retry.
`assert_within_horizon(chain)` walks a whole tree and refuses if anything sits above the horizon.

**Does not.** It does not resolve blocks. It does not raise the number when the number is
inconvenient. It does not choose the content of the horizontal split beyond a documented
placeholder (see U6 below).

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

`test_all.py` runs 30 tests and asserts, among other things:

- P spawns exactly 1 child; W spawns 2, 3 and 4 and refuses 1; D spawns 0 and leaves depth alone.
- A block at depth 5 returns `STRUCTURAL_DEADLOCK` and nominates no depth-6 child.
- `flatten` returns siblings at the same level, never deeper, and refuses below the horizon.
- **No path reaches depth 6**: every depth-indexed blockade policy over depths 0-5 (all 4096) is
  built and traversed, plus 500 randomised path-dependent policies over depths 0-9. Deepest
  chain seen: 5. Chains at depth 6: zero.
- The Desire loop runs 1000 iterations and depth stays 0.
- A dirty child invalidates every ancestor, proven by walking parent pointers to the root.
- Retraction holds at every depth 0-5, and a failing pair at depth 3 neither pollutes nor is
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

**This build pins 5.** The pin is a *reading* of the book, not a quotation: the comment above
`HORIZON` in `depth.py` says so in as many words, and it quotes the book's actual sentence
("not an arbitrary performance cap, but a stability horizon") next to the brief's paraphrase
("a stability horizon, not an arbitrary cap") so the difference between the two is visible in
the file. If the number changes, `HORIZON = 5` is the single line to change, and the whole
suite re-proves the horizon property at the new number.

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
  the origin. This build pins the root at depth 0, so a block at depth 5 is the deadlock and
  depth 6 cannot occur. A root-at-1 reading changes the label of the root, not the arithmetic.
  *(dwp.py)*

- **(U3) Is a Desire block at depth 5 also a Structural Deadlock?**
  Canon defines the deadlock as a chain at depth 5 meeting *another blocked node* (any node),
  but also says `Phi_D` "does not contribute to the recursion depth limit". Both readings are
  exposed: the default keeps Desire iterative at depth 5; `iterative_exempt_at_horizon=False`
  deadlocks it like Power and Wisdom. *(dwp.py)*

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

- **(U8) Is N in `(CO-1 o CO-4 o CO-7)^N` bounded?**
  Canon writes `loop(N)` and says the loop runs "until the motivation threshold is reached",
  with no maximum and no threshold function. This build takes N from the caller and enforces
  only `N >= 0`, which is why a 1000-iteration loop is legal. *(dwp.py)*

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

- **The pin is a reading.** 5 is pinned because the book says 5, not because this build proved
  5 is correct. The table above is the evidence that the number is contested.
- **U3 is the one that could bite.** If "any block at depth 5 is a deadlock" is the intended
  reading, then the default treatment of Desire at the horizon is wrong. It is a one-flag change
  and a one-test change, but it is a judgement this build made, not one canon settled.
- **`flatten` is structurally proven, not semantically proven.** The tests prove the siblings
  are flat, same-level, tagged, and childless. They cannot prove the decomposition is the *right*
  one, because canon does not say what the right one is (U6).
- **Nothing here has been compared to Helm, to a model, or to a mind.** The engine is consistent
  with the book's definitions and with itself. That is the entire claim.

**MECHANISM ONLY. THIS IS NOT THE HELM BRAIN. NOTHING HERE HAS RUN INSIDE HELM.**
