# Who decides when HELM looks deeper? — design v1 (DESIGN ONLY: nothing built, nothing run, 0 USD)

**Asked by the owner, 2026-10-21 (verbatim):** "WHAT IF WE LET THE EYE OR SOME OTHER REASONING PART DETERMINE IF MORE RPM DEPTH
WAS NEEDED/NECESSARY ON A GIVEN MATTER? HOW WOULD THAT WORK AND COULD THAT WORK?"

**How this was made.** Two readers read the code on `origin/claude/project-thread-pmbzd6` at `5dcbf23c` (facts files in this folder). Three
designers each argued one answer (the Eye advises; a separate depth part decides; no new part, arithmetic only). A judge merged them
(`DEPTH_V_DRAFT_SUPERSEDED.md`). A skeptic then read the code again and found 30 problems in that draft (`SKEPTIC_REVIEW.md`). This file
is the corrected answer. Every code claim below was either in a reader's facts with a file and line, or checked again by the operator.
Claude is not the research governor: everything here is a PROPOSAL for the owner.

## Said plainly first

- **Could it work? Yes, but not with the Eye making the decision.** An exact arithmetic rule should decide, at the RPM gate. You already
  have one, built and scored: your **decoupling stop**. On HELM's made-up cascade exam it read `DECOUPLING_EARNED` (spec 7.69): 203
  descents instead of 609 for the old fixed cap, 64 good answers instead of 60, and 0 false fuse trips on solvable items instead of 4.
  That claim is `LICENSED` only within `SYNTHETIC_ONLY`.
- **The Eye's right job is to check that rule from the outside**, never to make it. Later, with a new owner ruling, it could ask for *more*
  depth on a kind of item where its checks found the rule stopping too soon. It should never be allowed to ask for *less*. That way the
  worst thing the Eye can cause is extra work, never a wrong answer.
- **In today's live chat there is no depth choice to make.** The loop always starts at depth 0, each repair opens exactly one level beside
  the others, and the brain only takes single-recipe orders. So any depth decider plugged into today's chat would measure nothing
  (`VACUOUS`). Depth becomes a real choice when an ingredient has its own recipe (a sauce inside a dish). That is the wave-3 cascade world,
  not yet the live chat.

## How depth works in HELM today (facts)

There are two different "depths" (full detail with file and line numbers in `FACTS_RPM_DEPTH.md`):

1. **RPM recursion depth.** The gate's cause carries a depth (root = 0). A REPAIR opens a child one level down. The limit is
   `HORIZON = 12`, by the owner's ruling of 2026-10-16; the book's own number is 5, and both sentences stay on record
   (`docs/working/noetic_council/OWNER_RULING_DEPTH_12_20261016.md`). Reaching the limit means **flatten** into side-by-side sub-problems,
   never raise the number.
2. **Recipe-expression depth inside one order.** Capped at 5 (`DEPTH_CAP`) in the sealed wave-1 brain; the live loop only ever sends a
   single-recipe order, so this is always 1.

What the live loop actually does:

- Nothing chooses depth. The gate's own docstring says it "does NOT decide ... what the depth is"; the loop hard-codes `depth=0`.
- A REPAIR opens one child per missing item, one after another, all at depth 1 (sideways, never deeper). A stock child can fetch a verified
  stored amount and turn "how much X?" into an answer. A requirement child can never succeed ("a requirement cannot be made up").
- The wide brain (on by default) opens no children at all: a REPAIR verdict simply ends its turn with a question.
- **One real defect found (0 USD fix proposed below):** the gate checks the parent's depth and the actor checks the child's depth, so the
  two disagree by one level. The deepest child the actor will ever open is 11, although the depth module allows a chain to sit at 12.

## Why the Eye should not decide

- **By design it cannot.** The Unity Eye has three properties, each enforced in code: it sits outside what it watches, it cannot write, and
  **it never gates** — nothing it returns is read by any decision (`docs/working/noetic_council/faculties_v2/eye/eye.py`, header). Every
  proposal it makes carries the word `REPORT_ONLY`.
- **Its own remedy table points the other way.** For a station starved of input, the Eye's design prescribes "ask for the missing stock by
  name", and it quotes "recursing harder is not a fix" (`UNITY_EYE.md`, faults table, in the faculties-circuit design packet). It also reads
  "depth n against 5", not against 12: that reading must be reconciled before the Eye audits depth.
- **Its acting is not licensed.** "The Eye may act outside tests" is `NOT LICENSED` (spec 7.38, 7.40). What the Eye has earned is
  scanning and pairing on made-up worlds (`EYE_SCAN_EARNED_KEEP`, `EYE_PAIRING_EARNED_KEEP`, spec 7.77, 7.78).
- **Making it decide would cost its strongest guarantee:** today, removing the Eye changes no decision. A deciding Eye breaks that.

## The proposal (corrected after the skeptic)

1. **The decider: your decoupling stop, moved into the live loop for nested recipes, behind a switch that is OFF by default.** At a parent,
   a child is skipped only if all three hold: (a) its share is clearly in excess, `v_c / a_c >= (1 + 1/20) * Y_T`; (b) it has a passing
   consolidation receipt in the store; (c) every face of every ground cell under it is at Peak. A binding child (the limiting reagent, or
   within the margin) is always opened. This rule is stricter than the draft's own invention, which dropped the margin and the receipt
   check and would have skipped binding children (`SKEPTIC_REVIEW.md` items 6-7). Its code exists in the sealed wave-3 package
   (`cascade_w3.py`); the rule text is `docs/working/r1_wave3/DESIGN_R1W3.md`, "THE DECOUPLING-STOP RULE".
2. **The Eye, stage 1 — audit only, in idle time (needs one owner line, because no Eye runs on the live chat today).** It re-reads each
   depth decision from its receipt, reports any decision that does not re-derive, reports skipped levels that a shadow check shows would
   have changed the answer, and escalates to the owner. It writes nothing and gates nothing. Whether depth auditing is the Eye's "Unity"
   work is `FLAG_FOR_HUMAN_REVIEW`.
3. **The Eye, stage 2 — may only ask for MORE depth (needs a new owner ruling).** A whisper `DEEPEN` keyed by item kind, at most 2 per idle
   window, admitted only when its evidence points to audit receipts. It can turn a skip into a descent, never the reverse; it never touches
   the limit of 12 or the Desire bound of 12; it never runs inside an awake turn. The ruling must say plainly that this changes one Eye
   property, from "removing the Eye changes no decision" to "with every whisper silent, every decision is bit-identical".
4. **Two 0 USD fixes first, tests first:** (a) the actor checks depth the way the gate does (`check_depth(parent depth)`), so a child may sit
   at depth 12 as the depth module allows; (b) record hygiene: the actor's re-check carries the loop's real digest instead of `digest-1`
   (no decision reads it, so this is hygiene, not a repair). Re-run `repair_performer/test_all.py` and `the_loop_v3/test_all.py`.

## The test, if the owner wants one (DEPTH-V1, PROPOSED)

- **Where:** nested recipes cannot run through today's live brain (single-recipe orders), so the nesting part runs on the wave-3 cascade
  harness with **fresh seeds from its generator** — never the sealed X2 exam. The live-loop part checks only that the switch OFF leaves
  today's trace bit-identical.
- **Arms:** A0 today; A0R today minus the dead requirement child and the duplicate gate call (so savings are not just deleted dead code);
  A1 never descend; A2 "go deeper while the last level found something new" (the mechanism-free baseline); **A3 the decoupling stop
  (required)**; A5 random skips at A3's skip rate. Stage 2 adds A6 Eye `DEEPEN` whispers, A7 random whispers at A6's count, and A8 a plain
  audit counter with no Eye (the cheap rival the Eye must beat).
- **Count work, not children:** store scans, gate calls, chain records, replays.
- **Hard gates (any failure = INCONCLUSIVE):** switch OFF bit-identical trace; 0 Eye writes; depth never above 12; every shadow check runs on
  deep copies (the live brain's memory, learned digest and store write history unchanged); the final answer is scored with the wide brain
  ON; A5 loses at least one answer (else `VACUOUS`).
- **Forecast (a guess, not a result):** the decoupling stop has already beaten the fixed cap, so a *new* rule most likely ties it
  (`NO_SAVING`). For stage 2, most likely `EYE_DEPTH_NO_GAIN` unless a family of items exists that the rule misses and the plain audit
  counter does not catch.
- **Cost if approved:** one small AWS CPU instance, proposed cap 0.25 USD; the owner sets the real cap.

## What a pass would never let us say

That the Eye decides depth in the live chat; that Eye acting is licensed outside tests (it stays `NOT LICENSED`); anything about real-world
questions; that the limit of 12 should rise.

## What needs the owner

1. Whether to make the two 0 USD fixes (tests first).
2. Whether to plan the decoupling stop into the live loop when nested recipes reach the chat (switch OFF until a test passes).
3. One owner line for stage 1 (Eye audits depth, report only, on a live chat trace written to disk).
4. Stage 2 only: a ruling that lets the Eye ask for more depth, with the property change stated above.

## Files in this folder

- `DESIGN.md` — this answer.
- `FACTS_RPM_DEPTH.md`, `FACTS_UNITY_EYE.md` — what the two readers found, with file and line references.
- `DESIGN_A_EYE_ADVISES.md`, `DESIGN_B_DEPTH_PART.md`, `DESIGN_C_ARITHMETIC_ONLY.md` — the three competing designs.
- `DEPTH_V_DRAFT_SUPERSEDED.md` — the judge's merged draft, kept as a negative: the skeptic showed it should not go to the owner as written.
- `SKEPTIC_REVIEW.md` — the 30 problems found, each with its fix.
