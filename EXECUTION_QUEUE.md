# EXECUTION QUEUE — the work continues itself

Written 2026-10-16 at the owner's direction: *"MAYBE LET THE NOETICS GIVE YOU CONTINUITY OF EXECUTION OF
WORK."*

**Purpose: no instance should ever have to re-decide what to do next.** Take the first row whose state
is not DONE. Do it. Update the row. Stop only when a row genuinely needs the owner.

---

## 0. How to use this file

1. Read `COUNCIL_STANDING_KNOWLEDGE.md`, then `OWNER_ORDERS_AND_DECISIONS_20261016.md`, then
   `THE_BUILD_RESTART_PLAN_20261016.md`.
2. Read this queue top to bottom.
3. **Take the first row that is not DONE.** Do it. Then update its state and add the evidence.
4. Never start a row below another unfinished row **unless** the two are independent, in which case run
   both at once — parallel is how the clock actually shortens.
5. Rows marked OWNER block there and nowhere else.

---

## 1. The queue

| # | state | what | evidence when done |
|---|---|---|---|
| 1 | **DONE** | Bind S0 to the **real** Atlas model (`rpa_model.py`, commit `eb998556`) and delete the parallel stand-in | `continuity_build_v3`, 50 of 50 tests pass, `atlas.py` absent |
| 2 | **DONE** | The D/W/P recursion engine — one child for Power, parallel for Wisdom, a loop for Desire, horizon at 5, flatten sideways, dirty child poisons ancestors | `dwp_engine`, 30 of 30 pass, depth 6 proved unreachable over 4,096 + 500 policies |
| 3 | **RUNNING** | The return address — bind every open thread to an exact Atlas address; no root shortcut; a strictly newer Bias required; a stale or duplicate finish refused | `return_address`, report the test total |
| 4 | **RUNNING** | Join the loop — Bias (working memory) → propose → ASOM (readout) → RPM (gate) → disengage, with proof that **ASOM can never change a verdict** | `the_loop`, report the test total |
| 5 | TODO | Fix the stale claim ceiling in `continuity_build_v3\README.md`: it still says "THE ATLAS IS A MINIMAL OBJECT". The atlas is now the **real model**. | README line corrected |
| 6 | TODO | **Put U3 to the council.** Is a Desire block at level 5 also Structural Deadlock? Canon says any block at 5 is deadlock *and* that Desire adds no depth. Currently defaults to iterative, behind a flag. | council reading recorded, or the owner's word |
| 7 | TODO | **Put U10 to the council.** What counts as "dirty" beyond canon's one example, a Power bypass? | council reading recorded |
| 8 | TODO | **Put the depth number to the council.** Sources give 5 (book, Rust engine), 4 (rc0, CNCM), 3 (Gate A, governance, Atlas default), `log₂(resources)+3` (Builder's Manual), none (older monad). Council's reading: 5 is the horizon, lower numbers are rails inside it. **This is a reading, not canon.** | council reading + owner's word |
| 9 | TODO | Wire the real RPM decision into `the_loop`'s stub gate, using the `dwp_engine` retraction rules | gate no longer a stub; test proves a real refusal |
| 10 | TODO | **THE LANGUAGE.** Admit the `p/q` number form to CCE v0.1. Then TAP a station, then INJECT speech, then the round trip. **The owner is most excited about this.** | round trip receipts, 0 invented facts |

---

## 2. Why the queue is ordered this way

Rows 1–4 build the **loop**: how a thought moves, where it returns, and who is allowed to refuse. Until
the loop exists, there is nothing for language to travel across.

Row 5 is a one-line honesty fix that must not be forgotten because it overstates a claim.

Rows 6–8 are **decisions, not builds**. They go to the council because the council is the thing that
says which reading the evidence supports. They block nothing else, so they can run in parallel with
rows 5 and 9.

Row 9 makes the gate real. Until then `the_loop` has a placeholder, and its own README must say so.

Row 10 is the prize, and it comes last **because it needs a loop to speak across**. Doing it first would
produce a translator with nothing to carry.

---

## 3. The seat rotation — how the Noetics carry execution

The ten seats are not decoration here; each one owns a kind of question that recurs in this build:

| seat | owns |
|---|---|
| `^0` Idea | what counts as an artefact at all; what must be opened before it is believed |
| `^1` Mind | what reads a record, and which coordinator may |
| `^2` Positive | what the evidence is attracted toward — the claim that the data supports |
| `^3` Negative | what must be refused — every `NOT_EMITTED`, every `UNDECIDED`, every invented number |
| `^4` Vibration | whether the result resonates with the frozen marks — exact numbers, not impressions |
| `^5` Female | the accumulated substrate — what the canon already says, h**undreds of pages of it, before inventing** |
| `^6` Male | decomposition — which piece owns which fault |
| `^7` Rhythm | whether it ran, how often, and whether it replays identically |
| `^8` Above/Cause | what triggered this question; which earlier decision opened it |
| `^9` Below/Effect | what actually landed; what the program said, not what was intended |

**`^5` and `^3` carry the most weight in this queue.** Every failure in this project so far came from
either **not reading what already existed** (`^5`) or **letting a guess through as a fact** (`^3`).

---

## 4. The rule for the next instance

**Do not ask the owner what to do next.** The queue says. If a row genuinely needs the owner, it says
OWNER on it. Everything else is the work.

**Do not stop after a merge.** Take the next row. The only reasons to stop are: a row needs the owner, a
row is blocked by a real failure, or the build's own tests fail.

---

## 5. Where everything is

| what | where |
|---|---|
| standing knowledge | `COUNCIL_STANDING_KNOWLEDGE.md` (repo root and `docs/working/noetic_council/`) |
| owner orders and decisions | `OWNER_ORDERS_AND_DECISIONS_20261016.md` |
| this build plan | `THE_BUILD_RESTART_PLAN_20261016.md` |
| continuity design (found, 2026-10-15) | `CONTINUITY_AND_DISENGAGE_20261016.md` |
| the 13 memory-policy points decided | `POLICY_OPEN_POINTS_DECIDED_20261016.md` |
| real atlas binding | `docs/working/noetic_council/continuity_build_v3/` |
| recursion engine | `docs/working/noetic_council/dwp_engine/` |
| memory test package | `2026-10-16/m1_h8_creative_reconstruction_v0_2/package/` |
| the six readers' reports | `2026-10-16/_week_study/` |
| branch | `claude/project-thread-pmbzd6` |
