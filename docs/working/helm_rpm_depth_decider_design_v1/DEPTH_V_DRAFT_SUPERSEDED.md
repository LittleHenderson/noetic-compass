**Winner: depth-faculty.** It adds these parts from the other two designs:
- **From eye-advises:**
  - the incumbent rule as a required arm;
  - a check that the Eye's arm matches the faculty exactly when the Eye says nothing;
  - the 1-in-10 audit descent;
  - two 0 USD repairs first.
- **From rule-only:**
  - the stale-number guard;
  - the exact count forecast for mixed turns;
  - asking about the unlearned requirement first, as a separate switch.

# Synthesized design: DEPTH-V (arithmetic decides, the Eye audits)

This is a proposal only. Nothing has been built or run, and 0 USD has been spent. Claude is not the research governor, so the owner approves or rejects it.

## Could that work?
Yes, but not as "the Eye decides." In today's live chat there is no depth choice to make, because every repair opens exactly one level and never a second, so any depth decider there would read VACUOUS. Where depth is a real choice, such as a recipe whose ingredient has its own recipe, an exact arithmetic rule should decide. The Eye's safe job is to check that rule afterwards. With a new owner ruling, it could also ask for more depth, but never for less.

## How it works, step by step
A "child" means one extra level of RPM checking, opened to fill one gap.

1. **S3** builds the `absent` and `unlearned` lists, as today (`helm_end_to_end_loop.py:804-805`).
2. **S5:** the loop's gate call runs unchanged, at depth 0 (`:347`).
3. If the gate says REPAIR, a new read-only **depth faculty** gives one word for each gap the gate named. This happens before the repair loop that goes gap by gap (`:353-362`).
4. **OPEN** gaps go to the actor exactly as today. A **SKIP** ends the turn the way `CHILD_REFUSED` does: `UNDETERMINED_CLARIFY`. The question it asks is the one today's loop would have asked.
5. Each word writes a `depth_voi` ledger line into `receipt_hash`. The line holds the inputs, the word, and the word recomputed from those inputs.
6. **Audit:** a fixed, seeded 1 in 10 of the SKIPs is descended anyway, for the record only.
   - Nothing it finds is glued.
   - It counts as spent descent.
7. After S6, in idle time, the Eye reads these lines through its digest-checked tap.

## The decision rule
The depth faculty has no learned parameters. All arithmetic uses exact `Fraction` values.

**Inputs.** All of these already exist in the loop:
- the gap string;
- the depth d;
- the names the user said are gone this session;
- `_stored_amount(X)` and its source tag;
- the current stock;
- the requirement amounts a_i.

| Word | When |
|---|---|
| `SKIP_AT_HORIZON` | `check_depth(d+1)` is not OK. The fix it names is flatten. It never raises the limit of 12. |
| `SKIP_CANNOT_FILL` | It is a requirement gap. That child returns `ok: False` by construction (`:778-786`). |
| `SKIP_TURN_UNANSWERABLE` | It is a stock gap in a turn that also has a requirement gap. Any glued stock would be thrown away (`:821-842`). |
| `SKIP_NOTHING_STORED` | It is a stock gap, and either the user said it is gone or no verified amount is stored. |
| `SKIP_NOT_LIMITING` | Nested levels only. All three must hold: (1) X's share, x_X/a_X, is strictly above every other share; (2) X's recipe shares no ingredient with the parent; (3) every amount used is `USER_SAID` or `CHECKED` this session. |
| `OPEN` | Everything else: ties, unknown amounts, older stored amounts, unknown gap kinds, any error, and any change to the child code. |

- A tie always gets OPEN, because filling it removes the brain's `G3` tie refusal.
- The teaching replay child and the wide brain always get OPEN.

## Who proposes and who decides
- **The faculty** may only say "no" to a descent the gate already named.
  - It never opens a child the gate did not name.
  - It never edits `depth` or `unsatisfied`.
  - It adds no field to `GateRequest` (7 fields) or `RpmCause` (12 fields).
- **The gate** still makes every decision it makes today: `ANCESTOR_DIRTY`, `STALE_BIAS` and `NO_DEEPER_SUB_GOAL`.
- **The actor** still decides nothing.
- **The owner** decides whether the faculty runs live.
  - It would run beside the owner-adopted decoupling-stop rule.
  - Like that rule, it never skips a binding child.

## What the Eye does and does not do
**Stage 1 (no new ruling needed): report only, idle time only.** The Eye:
- re-derives each `depth_voi` word from its receipt and reports any mismatch;
- reports each audit descent that would have changed the answer ("the rule missed this");
- reports expensive descents, which matches the PROPOSED dispatch reading;
- uses its Body scan to flag stored amounts that no longer re-derive (stale numbers);
- escalates to the owner.

**Stage 2 (needs a new ruling): whispers that can only say DEEPEN.**
- The whisper is held from an idle scan and keyed by gap kind.
- At most 2 are allowed per idle window.
- It is admitted only if its target exists and its evidence resolves to audit receipts. These are the wave 4 checks.
- At S5, the faculty turns a SKIP of that gap kind into OPEN.

**The Eye never:**
- says ENOUGH (turning an OPEN into a SKIP);
- adds a gap;
- changes the depth;
- touches `HORIZON = 12` or `DESIRE_BOUND = 12`;
- reaches the gate;
- writes anything;
- scans while a turn is in progress.

The worst case of Stage 2 is today's behavior plus some extra compute.

## Cost
- **Run time:** in-process standard-library Python. No GPU, no network, no model, 0 USD.
- **Per gap:** one set lookup, one store scan and a few divisions.
- **Each skipped gap saves:** 2 gate calls, 4-5 ledger lines, and the `teach_step_b` replays a requirement child runs.
- **Scale:** the savings are small today. They grow with depth, because each gate call builds d+1 chain records.
- **Audit:** it gives back about 10% of the skipped descents.

## How it fails safe
- Any doubt gives OPEN, which is exactly today's behavior.
- A wrong SKIP gives a question to the user, never a wrong number. These stay unchanged:
  - the gate;
  - the glue rules;
  - the brain's gates `G1`-`G5` and `DEPTH_CAP`;
  - the valve.
- If the Eye is absent, broken or over budget, its whisper counts as NONE. The faculty then runs alone.

**Two 0 USD repairs come first. They change no claim.**
1. Make the gate and the actor agree on depth. Today flatten at exactly 12 can never be reached.
2. Make the actor's re-check carry the loop's real digest, not `digest-1`.

## Test DEPTH-V1 (synthetic, 4 fresh sealed seeds)
**Exam:**
- **Part L (live loop), 240 turns:**
  - stock complete;
  - stock missing but stored;
  - stock missing and not stored;
  - stock the user said is gone;
  - an unlearned requirement;
  - 60 mixed turns, each with 1 requirement gap and 2 stock gaps. In 30 the store holds both amounts; in 30 it holds neither;
  - depths 10-12.
- **Part N (nesting, test-only), 240 items:**
  - depths 1-12, with 40 chains blocked at exactly 12;
  - ties and shared ingredients;
  - about one third non-limiting intermediates;
  - stale stored amounts.
- **Part H (Stage 2 only), 60 items:** a family of rule holes that the custodian picks and seals. The rule's author never sees it.
- **Labels:** every child runs in shadow. A child counts as useful if it changes the outcome word, the yield, the limiting reagent (the ingredient that runs out first) or the spoken line.

**Arms:**

| Arm | What it does |
|---|---|
| A0 ALWAYS | Today's loop. |
| A1 NEVER | Never opens a child. |
| A2 NOVELTY | The mechanism-free baseline: go deeper while the last level glued something new. |
| A3 DECOUPLING | The owner's incumbent rule. It reads NOT_EXERCISED if it cannot be ported without new inputs. |
| A4 | The depth faculty. |
| A5 | Random skips at A4's own skip rate. |
| A6 (Stage 2) | A4 plus the Eye's DEEPEN whispers. |
| A7 (Stage 2) | A4 plus random DEEPEN whispers, at A6's count. |

**Hard gates** (if any fails, the result is INCONCLUSIVE):
- 0 Eye writes.
- Depth never goes above 12.
- Flatten fires on all 40 depth-12 chains and nowhere else.
- 100% of words re-derive from their receipts.
- 0 invented quantities and 0 glue without PROCEED.
- The existing suite passes: the 7/12 field counts, the 150-row matrix, and the tests that keep the two 12s apart.
- A6 with every whisper forced to NONE is bit-identical to A4.
- A5 loses at least 1 answer on Part N. If not, the result is VACUOUS.

**Verdicts (frozen before the run):**
- `DEPTH_RULE_EARNED_KEEP` needs all of these:
  - A4 loses 0 answers against A0 on Part L and Part N.
  - A4 opens at least 25% fewer children on Part N.
  - A4 opens fewer children than A2.
  - If A3 was exercised, A4 opens no more children than A3.
- Otherwise `DEPTH_RULE_NO_SAVING`, `DEPTH_RULE_LOST_ANSWERS` (a FAILURE), VACUOUS or INCONCLUSIVE.
- **Stage 2:** `EYE_DEPTH_EARNED_KEEP` needs all of these:
  - A6 recovers at least half of A4's Part H losses.
  - A6 recovers more than A7.
  - A6 adds at most 10% descents on Parts L and N.
  - Otherwise `EYE_DEPTH_NO_GAIN`.
- A4's Part H losses are reported as a limit of the rule's coverage. They are never deleted.

**Forecast (a guess, not a measurement):**
- **Part L:** 85% that A4's answers equal A0's, and that on the mixed turns A4 opens about 18 children (audit only) against A0's 120.

| Result | Odds |
|---|---|
| `EARNED_KEEP` | 45% |
| `NO_SAVING` (A2 or A3 ties) | 30% |
| `LOST_ANSWERS` | 10% |
| VACUOUS or INCONCLUSIVE | 15% |

| Stage 2 result | Odds |
|---|---|
| `EYE_DEPTH_EARNED_KEEP` | 30% |
| `EYE_DEPTH_NO_GAIN` | 50% |
| INCONCLUSIVE | 20% |

For Stage 2, the 1-in-10 audit gives the Eye only about 6 sightings of the hole family per seed.

**Compute:** one small AWS CPU instance, per the laptop rule. Proposed cap: 0.25 USD and 20 minutes. Source, purpose, instance, limits and cleanup are recorded. The owner sets the real cap.

## What a pass would let us say, and never say
**A pass lets us say:**
- "On a synthetic exam, an exact arithmetic depth rule cut descents by the measured amount and lost 0 answers." Status: ENGINEERED-NOT-VALIDATED, SYNTHETIC_ONLY.
- **Stage 2:** "On that exam, the Eye's idle-time DEEPEN whispers closed rule holes better than random whispers."

**A pass never lets us say:**
- that the Eye decides depth in live chat;
- that Eye acting is licensed outside tests (it stays NOT LICENSED);
- that the rule is safe on item kinds the exam lacked;
- anything about real-world questions;
- that 12 should rise;
- that it beats the decoupling rule, if A3 read NOT_EXERCISED.

## What needs an owner ruling
1. Approve DEPTH-V1 and its cap.
2. Allow the faculty in the live loop, beside the decoupling-stop rule. Its switch stays OFF until the test passes.
3. **Stage 2 only:** DEEPEN whispers change one Eye property. "Removing the Eye changes no decision" would become "with every whisper NONE, every decision is bit-identical."
4. **Stage 2 only:** does depth advice count as "Unity" work? FLAG_FOR_HUMAN_REVIEW.
5. **Optional separate switch:** ask about the unlearned requirement before stock. It changes the spoken line, so its result is reported apart.

Nothing here changes `HORIZON = 12` or `DESIRE_BOUND = 12`.

## The failure that worries me most
A skip leaves no trace. Nobody ever sees what a skipped child would have found. So the rule and the Eye can both be confidently wrong on a kind of item nobody planted. The 1-in-10 audit is the only window, and it may be too thin to show a rare hole.

---

## Scores (1-10)

| Design | Safety | Testability | Gain vs baseline | Cost | Clarity | Total |
|---|---|---|---|---|---|---|
| eye-advises | 6 | 8 | 3 | 6 | 7 | 30 |
| depth-faculty (winner) | 8 | 8 | 6 | 8 | 7 | 37 |
| rule-only | 9 | 6 | 3 | 9 | 8 | 35 |

- **eye-advises:** it adds an 8th gate field, breaks the Eye's "never gates" ablation property, and needs 4 rulings. Its forecast gain is low (25%).
- **depth-faculty:** it changes no gate field, and any doubt falls back to today's behavior. Its gain shows mainly in the test-only nesting exam.
- **rule-only:** it is the safest and cheapest. But its gain is a near-certain tiny saving, so as research it is near-VACUOUS.

I built this from the facts given in the task. I read no files and changed none.