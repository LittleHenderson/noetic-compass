# Outside re-check (deepseek deepseek-reasoner)

Files: OUTSIDE_REVIEW_PLAN_AND_GUIDE.md, REVIEW_RESPONSE.md, 06_VERDICT_PLAN_v1_1.md, 02_LABELING_GUIDE_v1_1.md

VERDICT: ACCEPT_WITH_NOTES

1. **CLOSED** — Plan v1.1 defines strict agreement only over “cases” where at least one team gives a clear entry, excludes neither-marked passages from the primary denominator, and reports all-passage agreement separately with no bar.

2. **CLOSED** — Guide 15(b) still labels a reasoning conclusion as `^9` with `relative_to:""`, but Plan v1.1 excludes flagged `"reached_by": "reasoning"` entries from `^9` scoring and gives them their own no-bar row, so the scored non-canon `^9` risk is removed; residual guide inconsistency is unscored.

3. **CLOSED** — Rule 2 now names both rule-15 exceptions, and 15(d) expressly says an uncertain pair is not a clear pair; Plan excludes uncertain entries from the clear bars.

4. **CLOSED** — Plan v1.1 counts only clear entries and reports uncertain `^8`/`^9` in separate no-bar rows, so shared ambiguity cannot inflate the primary bars.

5. **PARTLY CLOSED** — The longer-quote half-content test is stricter than the old shorter-quote test and reduces short-quote mismatch, but it is not exact normalized match, so different spans with enough overlap can still count as the same reading; risk reduced, not eliminated.

6. **CLOSED** — Plan v1.1 requires agreement on the relevant relational fields: Mind for `^2`, `^3`, `^5`; Mind and related thing for `^4`, `^7`, `^8`, `^9`; related thing for `^6`.

7. **CLOSED** — K8 no-Mind passages are raised to 60, and Plan withholds a verdict if a Noetic has fewer than 50 neither-marked passages, addressing `^1` base-rate risk.

8. **PARTLY CLOSED** — The hard rule of at least 50 cases and 50 absences per Noetic prevents a verdict on too-thin data, but it does not verify/report per-Noetic counts before sealing as requested; residual risk is wasted study or no verdict, not a false verdict.

**NEW BLOCKER: none**
