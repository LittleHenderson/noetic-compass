# Proposal: the Eye whispers about depth, and the RPM gate decides

**Status:** this is a proposal only. Nothing has been built or run. Claude is not the research governor. The owner approves or rejects the test.

## Short answer
Yes, it could work, but only as advice. The Eye proposes a depth, and the gate's written rule decides. There are two limits:
1. **In today's live chat loop it would change nothing.**
   - Every gap there blocks the answer.
   - Children never open grandchildren.
   - Only the stock child can succeed.
   - So there is no depth choice to make. A test on that loop would read VACUOUS.
2. **Where depth is a real choice, a rule already decides it.** That place is the wave 3 cascade. The decoupling-stop rule decides there (`DECOUPLING_EARNED`: 203 descents vs 609, and 64 good chains vs 60). The Eye must beat that rule, not only "always" or "never".

## The decision rule (rule D, inside gate step 4)
**Inputs (all typed):**
- `depth` (an int) and `unsatisfied` (names). These are unchanged.
- `binding` (true or false). True means the child is on the path that decides the answer.
- `incumbent`: DESCEND or SKIP. This is the decoupling-stop rule's choice. It skips only if the child is absorbed AND consolidated AND every face is Peak.
- `depth_whisper`: NONE, DEEPEN or ENOUGH. It comes with a `finding_id` and an evidence digest.

**The order of checks:**
1. Steps 1-3 and the horizon check run first, unchanged. No whisper can override `ANCESTOR_DIRTY`, `STALE_BIAS` or `NO_DEEPER_SUB_GOAL`.
2. The whisper's receipt is checked. If its evidence does not resolve in the Eye's sealed scan, it becomes NONE and the ledger logs `WHISPER_DECLINED_RECEIPT`. The same applies if the target does not exist (`_GATE`) or if 2 whispers were already used this window (`_BUDGET`).
3. If the child is binding, the result is `DESCEND_BINDING`. An ENOUGH whisper here is logged `WHISPER_DECLINED_BINDING`.
4. If the child is not binding:
   - DEEPEN when the incumbent says SKIP gives `DESCEND_WHISPER`.
   - ENOUGH when the incumbent says DESCEND gives `SKIP_WHISPER`.
   - Otherwise the incumbent stands: `DESCEND_RULE` or `SKIP_RULE`.
5. DESCEND becomes today's REPAIR, with the gate's own sub-goal. SKIP becomes the cascade's existing skip.

**What a whisper can never do:**
- Add a name to `unsatisfied`.
- Change the `depth` number.
- Move the limit of 12.
- Touch `DESIRE_BOUND`.

At depth 12, the only fix is still flatten, never a higher limit.

## Who proposes and who decides
- **The Eye proposes.** It reads past `S5 RPM link` trace rows through its digest-checked tap: the depth reached, what each child found, and the receipts.
- **The Eye writes nothing.** A whisper is a typed record. The whisper receiver holds it, as in wave 4. It never enters the brain's store.
- **The gate decides,** by rule D.
- **The actor still decides nothing.**

## Where it sits in the turn
- **Idle time (after S6):** the Eye scans and issues held depth whispers, keyed by kind of gap. This keeps the "no Eye scans while awake" rule.
- **Awake, at S5:** the loop attaches the matching held whisper to the gate request. The gate stays a pure function of its request.

## Cost
- It is in-process Python and costs 0 USD at run time.
- Each gate call does one extra comparison.
- Each decision adds one ledger line, `depth_decision {incumbent, whisper, final, reason}`, which goes into `receipt_hash`.
- An extra descent costs what it costs today: 2 gate calls, one child and 4-5 ledger lines.

## How it fails safe
- A missing, broken or over-budget whisper becomes NONE. The result is then exactly the incumbent's choice.
- Binding children always descend. Missing a fault is worse than wasting a descent. LM-T6's looser stop found 269 of 800 faults, against 800 of 800 with full descent.

## Rulings this needs (I assume none of them)
1. **The gate request grows from 7 fields to 8.** That breaks the "no readout reaches the gate" guard. The 150-row forced-label test must be extended, not removed. The new field may hold only NONE, DEEPEN or ENOUGH.
2. **One of the Eye's three properties changes.** It stays outside what it watches, and it still cannot write. But "it never gates", in its ablation-test form ("removing the Eye changes no decision"), no longer holds. It becomes: "with every whisper NONE, every decision is bit-identical to the incumbent's".
3. **The whisper acts, but only inside the approved test.** Eye acting stays NOT LICENSED outside tests.
4. **Is depth advice "Unity" work?** The acting "never" list says "whisper for anything but Unity". That is FLAG_FOR_HUMAN_REVIEW. Only the owner can answer it.

**Two 0 USD repairs come first:**
- **The gate and the actor disagree by one level.** The actor never opens depth 12, so flatten at 12 can never be reached.
- **The actor's re-check uses placeholders,** such as `bias_digest="digest-1"`.

## Test DEPTH-W1 (synthetic cascade, fresh sealed seeds)
**Arms:**
- **A0 NEVER:** no child is opened.
- **A1 ALWAYS:** descend all the way to the horizon.
- **A2 NEW-INFO:** descend while the last level found something new.
- **A3 INCUMBENT:** the decoupling-stop rule.
- **A4 INCUMBENT + Eye whispers:** the proposal.
- **A5 INCUMBENT + random whispers:** the same count and the same DEEPEN/ENOUGH mix as A4.

**Exam (4 seeds):**
- 800 planted faults at depths 1-11.
- 800 clean chains.
- 40 chains blocked at exactly depth 12.

**Marks:** faults found, descents spent, good chains, and false descents on clean chains.

**Hard gates** (if any fails, the result is INCONCLUSIVE):
- 0 Eye writes.
- 0 horizon breaches.
- Flatten fires on all 40 depth-12 chains and nowhere else.
- A4 with every whisper forced to NONE is bit-identical to A3.
- Every receipt passes.

**Verdict words** (frozen before the run):
- `DEPTH_WHISPER_EARNED_KEEP`: all three hold. A4 finds at least as many faults as A3. A4 spends at most 90% of A3's descents. A4 beats A5 on both of these marks.
- `DEPTH_WHISPER_HARMFUL`: A4 finds fewer faults than A3.
- `DEPTH_WHISPER_NO_GAIN`: anything else.

**Claim limit:** SYNTHETIC_ONLY. The best possible status is ENGINEERED-NOT-VALIDATED.

**Forecast** (my guess, not a measurement):

| Result | Odds |
|---|---|
| NO_GAIN | 50% |
| EARNED_KEEP | 25% |
| INCONCLUSIVE | 15% |
| HARMFUL | 10% |

Two reasons. The incumbent already cut descents by about two thirds. And the Eye's report-only record shows it raising too many alarms: 504 would-HELP on clean dialogues.

**Compute:** CPU only. Under the laptop rule it runs on AWS. I propose a cap of 0.50 USD. The owner sets the real cap.

## The failure that worries me most
The Eye could get stuck in a blind spot that confirms itself.
- It learns only from descents that actually happened.
- When ENOUGH makes the gate skip a child, the Eye never sees what that child would have found. So nothing corrects the Eye.
- Fresh seeds may hide this, because each world is short.

**Guard:** a fixed, seeded audit. Every 10th whispered skip is descended anyway, for the record only. That descent counts toward A4's descents. Anything it finds counts against the Eye.