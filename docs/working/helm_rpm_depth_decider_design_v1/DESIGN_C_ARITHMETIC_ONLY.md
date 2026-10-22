**Design D-ARITH: no new reasoning part. The recipe arithmetic sets the order and the stop. (PROPOSAL. Not built. Not run.)**

I checked three facts myself with `git show 5dcbf23c` (read-only):
- the gate names `unsatisfied[0]` (`docs/working/noetic_council/the_loop_v3/rpm_gate.py:669-670`);
- the loop lists stock gaps before requirement gaps (`helm_end_to_end_loop.py:812-813`);
- when the gate does not say PROCEED, the reply checks `still_absent` before `unlearned` (`:824-828`).

**Why I doubt we need a new part**
1. **There is no "more depth" to decide today.** Every child sits at depth 1. No child calls the gate, so no grandchild ever opens. The only real choice is sideways: which gap to open first, and when to stop.
2. **The arithmetic already answers that choice exactly.**
   - The gate says PROCEED only when every gap is closed.
   - A requirement child can never close its gap. It always returns `ok: False` (`:778-786`).
   - Stock amounts are only kept after PROCEED (`:821-842`).
   - So on any turn with an unlearned requirement, every stock child's work is thrown away. Today the loop opens those children anyway.
3. **An exact rule is its own answer key.** A reasoning part can at best tie it. Each miss either wastes work or skips a child that mattered.
4. **The Eye is barred from this seat.**
   - No scans while awake (`PREREGISTRATION_R1W4.md:203`).
   - Eye acting is NOT LICENSED outside tests (spec:1460, 2839).
   - The gate's request has no field the Eye could fill. It holds exactly 7 fields, and the cause exactly 12.
   - The Eye's report-only reading logged 504 would-HELP on clean dialogues.
   - A loose stop rule has lost deep faults before: LM-T6 A8 found 269 of 800, against 800 of 800 (`DECOUPLING_STOPPED_EARLY`).
   - Letting the Eye decide depth during a turn needs a NEW owner ruling. I forecast no gain from it.

**The decision rule**
- **Inputs.** Two lists the loop already builds when the question arrives (S3, `:804-805`):
  - `absent`: stock names the user has not given;
  - `unlearned`: requirement names the brain has not learned.
- **Output.** One word per turn. It is written as `{"what":"depth_rule","word":…,"absent":[…],"unlearned":[…]}` and folded into `receipt_hash`.
  - `NO_GAP`: both lists are empty. The gate says PROCEED. No child opens. Same as today.
  - `STOCK_ONLY`: only stock gaps. One child per stock gap, in today's order. Same as today.
  - `LACUNA_FIRST`: at least one unlearned requirement.
    - The loop lists requirement gaps first, so the gate's own step 4 names one of them.
    - That requirement child fails, and the loop stops at the first failure (`:353-362`). No stock child opens.
    - The reply's two branches swap places, so `unlearned` is checked first.

**A second rule for later.** Nothing can test it today, because the live loop sends only single-recipe orders.
- Look deeper into ingredient i's own recipe only if i can still be the limiting reagent. That means the stock x_i is unknown, or no known k has x_k/a_k < x_i/a_i. The words are `DESCEND_LIMITING` or `SKIP_EXCESS`.
- If several ingredients tie at the minimum, look deeper into every tied one.
- Reason: more of an ingredient you already have in excess can never raise min(x_i/a_i).
- This is the arithmetic meaning of the cascade's existing rule that "a binding child is always descended" (spec:2266).

**Who proposes, who decides**
- The rule only reorders gap names.
- The gate still gives every verdict. The actor still follows the gate's sub-goal.
- The owner decides whether to adopt the rule.
- The Eye has no role during a turn. It stays idle and report-only, and may read `depth_rule` lines afterwards. That idle reading of "deep RPM descents" is still PROPOSED.

**Where it sits in the turn**
- Order: S3 → rule → S5 gate at depth 0, unchanged → actor.
- These do not change: `rpm_gate.py`, `actor.py`, `depth.py`, the 7/12 field counts, `HORIZON = 12`, `DESIRE_BOUND = 12`.
- Putting the rule inside the gate itself would need either an 8th request field or code that reads English gap names. I recommend neither.

**Cost**
- The rule itself is a few list operations per turn.
- It removes about 2 gate calls and 4-5 ledger lines for each stock child it skips.
- The saving is tiny. The real point is that no new part is needed.

**How it fails safe**
- It only reorders names and swaps two reply branches. It cannot add a gap, store a value, invent a quantity, or go deeper.
- A wrong order still ends without PROCEED. So the worst case is a question to the user, never a wrong number.
- If a requirement child ever starts to succeed, the actor removes that gap and the loop moves on to the stock gaps. Nothing is lost.
- The switch `LACUNA_FIRST` stays OFF until the test passes.

**Test (needs the owner's approval)**
- **Exam:** 240 turns from a fixed random seed, on a dev-seed copy, frozen before the run.
  - G1: 60 turns with all stock given.
  - G2: 60 turns with stock gaps the store holds.
  - G3: 60 turns with stock gaps the store lacks.
  - G4: 60 mixed turns, each with 1 unlearned requirement and 2 stock gaps. In 30 the store holds both amounts; in 30 it holds neither.
- **Arms:**
  - A: the rule.
  - B0: today's loop. It also equals "go deeper while the last level found something new".
  - B1: never open a child.
  - B2: always open every gap.
- **Answer key:** run B2. Mark a child useful if removing it changes the final word, the yield or the limiting reagent.
- **Hard gates:**
  - H1: 0 invented quantities and 0 values stored without PROCEED, in every arm.
  - H2: A is byte-for-byte equal to B0 on G1-G3, 180 of 180.
  - H3: the existing test suite still passes (7/12 fields, the depth limit, `DESIRE_BOUND`, the 150-row matrix).
  - H4: A skips 0 useful children.
- **Measures:** children opened on G4. How many G4 turns ask first about the unlearned requirement.
- **Forecast:**
  - On G4, A opens 60 children and B0 opens 120 (90 + 30).
  - A asks about the requirement first on 60 of 60 turns. B0 does on 30 of 60.
  - B1 loses all 60 answers on G2.
  - B2 ties A on answers and opens the most children.
  - The number of user turns needed to reach an answer ties. I forecast no gain there.
  - Odds: 85% that all hard gates pass with this pattern; 10% that a bug in the reply path fails H2; 5% something I have not seen.
- **Running it:** plain Python, about 1,200 turns, seconds of work. Per the standing order it runs on one small AWS CPU instance, capped at 0.10 USD and 20 minutes, then shut down and checked.
- **Claim limit if it passes:** ENGINEERED-NOT-VALIDATED, SYNTHETIC_ONLY. As research it is close to VACUOUS, because it only shows the code obeys arithmetic. That is the skeptic's point.

**The failure that worries me most: stale numbers**
- The arithmetic is only as true as the amounts (x_i) and requirements (a_i) it reads.
- The stock child never checks how old a stored amount is.
- So `SKIP_EXCESS` could act on an old count and confidently skip the real limiting reagent.
- The η∘ε receipt would still match, because it re-checks against the same stale numbers.
- **Guard:**
  - `SKIP_EXCESS` may only rely on amounts marked `USER_SAID` or `CHECKED` in this session.
  - The Eye's idle Body scan ("store answers still re-derive", spec:2583) is the natural report-only watcher for exactly this.