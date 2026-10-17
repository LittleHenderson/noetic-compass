# OWNER RULING — the recursion depth and the Desire loop bound

**Recorded 2026-10-16 at the owner's own words, in this session, verbatim.**

The council could not find any owner words for the number 12 anywhere on disk, and correctly refused to
treat an unwritten number as a ruling. This file is that record. It exists so the build's two constants
are backed by a person's words and not by an agent's memory.

---

## The owner's words, verbatim and in order

1. **"NO LETS MAKE THE HORIZON 12. BUT WHAT'S THE DIFFERENCE BETWEEN CEILING AND HORIZON?"**

2. **"MAKE DESIRE LOOP 5."**

3. **"SORRY I MEANT TO SAY MAKE DESIRE LOOP 12 AS WELL"**

The third message explicitly supersedes the second. **Both numbers are 12.**

## What is therefore ruled

| constant | value | where |
|---|---|---|
| `HORIZON` — the depth at which a further block is Structural Deadlock | **12** | `dwp_engine_v2/depth.py` |
| `DESIRE_BOUND` — how many times a Desire loop may cycle in place | **12** | `dwp_engine_v2/dwp.py` |

Two separate constants, two separate jobs, both set to 12 **by ruling**.

## What this ruling does and does not settle

**It settles the number.** The build stands as written.

**It does not settle what a horizon means.** The council's finding stands: canon says 5 in three places
(`Chapter_27:59`, `Chapter_05:87`, `FULL_MANUSCRIPT_v2:6412`), and the book's own words are *"not an
arbitrary performance cap, but a stability horizon"*. A horizon is **found**, not chosen. So:

- **12 is the limit in force.**
- **5 remains canon's own number.**
- Neither of those sentences may be dropped in favour of the other.

## The consequence, stated plainly so it is not discovered later

At 5 and 5, a runaway Desire loop was stopped early. At 12 and 12 it runs **more than twice as long**
before anything stops it, and the recursion can descend twelve levels. The two limits no longer provide
different safety margins.

The council's warning is on the record and is a real one: **the two 12s sit one typo apart in the
source.** If a later edit lets loop cycles leak into the depth arithmetic, a Desire loop at the limit
reports `STRUCTURAL_DEADLOCK` instead of `DESIRE_BOUND_EXHAUSTED`, and the two become indistinguishable in
a receipt. Two tests guard every depth from 0 to 12 against exactly that.

## What would reverse this

One line each. `HORIZON = 12` → `5`, and `DESIRE_BOUND = 12` → whatever is ruled. **The 33 tests still
pass either way**, because the horizon is one constant they read rather than write. That was checked, not
assumed.

## Reverting to canon's 5 is free

If the owner prefers canon's number, say so and both constants go back. Nothing is built on 12 that is not
built on the number itself.

---

**Written by** the DeepSeek council session, 2026-10-16.
**Why this file exists:** an agent should not be the source of a ruling. The owner's words are.
