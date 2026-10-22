# Proposal: a depth faculty that looks deeper only when it could change the answer

**Status:** this is a proposal only. Nothing has been built or run, and it cost 0 USD. Any claim that the rule helps is NOT LICENSED until the test in section 6 runs.

**Short answer: yes, it can work, but only in a narrow form.** The rule in plain words: look one level deeper only if that level could change the final answer. Otherwise stop.

In today's live loop there is almost nothing for this rule to decide:
- The gate always starts at depth 0.
- Each child sits at depth 1.
- No child ever opens a grandchild.

The rule only pays off once a child can go deeper itself. An example would be making an intermediate, like dough, from its own recipe.

## 1. The decision rule

This faculty is new and separate from the Eye. It has no learned parameters.

**Inputs.** All are already in the loop, and all are read-only:
- the gap string
- the depth `d`
- the session's set of names the user said are gone
- `_stored_amount(X)`
- the current stock
- the requirement book's amounts (a_i)

**Output.** For each gap that the gate's REPAIR verdict names, in the loop's own order, the faculty gives one word. All arithmetic is exact `Fraction` arithmetic.

| Word | When |
|---|---|
| `SKIP_AT_HORIZON` | `check_depth(d+1)` is not OK. This is the actor's stricter check, so the off-by-one between gate and actor cannot matter. The fix it names is flatten. It never raises the limit of 12. |
| `SKIP_CANNOT_FILL` | It is a requirement gap. That child returns `ok: False` by construction (`helm_end_to_end_loop.py:778-786`). |
| `SKIP_TURN_UNANSWERABLE` | Another gap in the same turn is `SKIP_CANNOT_FILL`. Any stock glued in this turn would be thrown away (`:821-842`). |
| `SKIP_NOTHING_STORED` | It is a stock gap, and either the user said X is gone this session or no verified amount is stored. |
| `SKIP_NOT_LIMITING` | Nested levels only. X's share, x_X/a_X, is strictly above the smallest share among the other ingredients, and X's own recipe shares no ingredient with the parent. More X then cannot raise the yield or change the limiting reagent (the ingredient that runs out first). |
| `OPEN` | Everything else. This includes any tie at the minimum, any unknown amount, any unknown gap kind, and any error. |

Ties always get `OPEN`. Filling a tied ingredient removes the brain's `G3` tie refusal, so that descent does change the answer.

## 2. Who proposes and who decides

- **The faculty only proposes.**
  - It may only say no to a descent the gate has already allowed.
  - It never opens a child the gate did not name.
  - It never edits `depth` or `unsatisfied`.
  - It adds no field to `GateRequest` (7 fields) or `RpmCause` (12 fields).
- **The gate and the actor are unchanged.** The gate still decides ancestor-dirty, stale-Bias and horizon, exactly as today.
- **What a SKIP does.** It ends the turn the way `CHILD_REFUSED` does: `UNDETERMINED_CLARIFY`. The question asked is the one today's loop would have asked: the first failing gap, in the loop's own order.
- **The Eye only watches.** It is report-only, works in idle time only, and never writes or gates.
  - It re-derives each word from the recorded inputs and reports any mismatch.
  - It also reports expensive descents, matching the PROPOSED dispatch reading.
  - No new Eye ruling is needed.
- **The owner decides** whether a new stop rule may run in the live loop.
  - It would sit beside the owner-adopted decoupling-stop rule.
  - Like that rule, it never skips a binding child, meaning one at or tied for the minimum, or one with no answer possible without it.

## 3. Where it sits in the S0-S6 turn

It sits in the S5 RPM link. It runs after the loop's gate call (`helm_end_to_end_loop.py:347`) and before the per-gap `perform_repair` loop (`:353-362`).

Two paths are out of scope, and both always get `OPEN`:
- The wide brain.
- The teaching replay (`:951-977`). Its result can change the outcome word, so it must not be skipped.

## 4. What it costs

It is standard-library Python. It uses no GPU, no network and no model.

- **Per gap, the faculty itself costs:** one set lookup, one store scan and a few divisions. That is about the same as a stock child.
- **So today's savings are small.** Each skipped gap saves:
  - 2 gate calls
  - 4-5 ledger lines
  - the `teach_step_b` replays that a requirement child runs
- **Savings grow with depth.** Each gate call builds depth+1 chain records.

## 5. How it fails safe

- Any doubt or error gives `OPEN`, which is exactly today's behavior.
- A wrong SKIP can only produce a question to the user. It can never produce a wrong number, because the gate, the glue rules and the brain's gates are untouched.
- Every word writes a `depth_voi` ledger line holding its inputs, the word, and a check that recomputes the word from those inputs. This line goes into `receipt_hash`.

## 6. Falsifiable test (proposed name: VOI-D1)

**Setup.** A synthetic, sealed exam, run on an AWS CPU instance under the laptop rule. Proposed cap: 0.25 USD. It needs the owner's word.

**Exam shape:**
- **Part L (live loop):** 240 turns through the real loop. Mix of cases:
  - stock already complete
  - missing stock that is stored
  - missing stock that is not stored
  - user said it is gone
  - an unlearned requirement
  - an unlearned requirement plus stored stock
  - depths 10-12
- **Part N (test-only nesting):** 240 items.
  - Intermediates can be made from their own recipes.
  - Depths run from 1 to 12, including exactly 12.
  - The set includes ties, shared ingredients, and about one third non-limiting intermediates.
  - The children only work out what could be made. They commit nothing.
- **Labels:** every child is run in shadow. Each is marked by whether it changed the final answer: the outcome word, the yield, the limiting reagent, or the spoken line.

**Arms:**

| Arm | What it does |
|---|---|
| A0 ALWAYS | Today's loop. |
| A1 NEVER | Never opens a child. |
| A2 NOVELTY | Goes deeper while the last level glued something new. This is the cheapest rule with no mechanism. |
| A3 DECOUPLING | The owner's cascade rule. It reads `NOT_EXERCISED` if it cannot be ported without new inputs. |
| A4 VOI | This faculty. |
| A5 RANDOM | Skips at random, at A4's own skip rate. |

**Hard gates:**
- H1: A4 loses zero answers.
- H2: A4's answer is identical to A0's on every item.
- H3: All of the following hold:
  - 100% of words re-derive from their receipts.
  - Depth never exceeds 12.
  - The Eye writes 0.
  - Removing the Eye changes no receipt digest.
- H4: A5 loses at least 1 answer. If not, the exam is too easy and the result is `VACUOUS`.

**Benefit mark:** on Part N, A4 must open at least 25% fewer children than A0, and fewer than A2, unless A2 loses answers.

**Outcome words:**
- `VOI_EARNED_KEEP`
- `VOI_NO_SAVING`
- `VOI_LOST_ANSWERS`, which counts as a FAILURE
- `VACUOUS`
- `INCONCLUSIVE`

**Forecast:**
- Part L hard gates pass: 90%.
- Overall result:

| Result | Odds |
|---|---|
| `VOI_EARNED_KEEP` | 50% |
| `VOI_NO_SAVING` | 30% (most likely cause: A2 ties A4 on Part N) |
| `VOI_LOST_ANSWERS` | 10% |
| `VACUOUS` or `INCONCLUSIVE` | 10% |

## 7. The failure that worries me most

The faculty's idea of "the answer" is narrower than the loop's real answer.

- Yield and limiting reagent are only part of the answer.
- The answer also carries the brain's gates `G1`-`G5` and `DEPTH_CAP`, the valve, the exact question asked, and shared-ingredient use.

I found two hidden channels: ties and shared ingredients. The rule now opens on both. There may be others I did not see. The shadow labels catch a hidden channel only for the item kinds the exam contains. So a clean result would not prove the rule safe on kinds the exam never saw.