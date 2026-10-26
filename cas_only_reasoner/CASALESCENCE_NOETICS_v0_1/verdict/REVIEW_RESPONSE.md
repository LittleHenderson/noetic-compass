# Response to the outside review of plan v1.0 and guide v1.0

Reviewer: DeepSeek reasoning model (`deepseek-reasoner`), 2026-10-04 23:49 PDT. Its full text is in `OUTSIDE_REVIEW_PLAN_AND_GUIDE.md`. Verdict: **REJECT**, four blocking and four major findings. Nothing had been labeled under v1.0.

| # | Severity | Finding | What I did | Followed the reviewer's fix? |
|---|---|---|---|---|
| 1 | BLOCKER | Strict agreement counted passages where neither team marked the Noetic, which inflates it | Plan v1.1: strict agreement is computed on cases only. Agreement over all passages is reported separately, with no bar | Yes |
| 2 | BLOCKER | Rule 15(b) scored a `^9` with no `^8`, against the Part A definition of `^9` | Guide v1.1: a conclusion reached by reasoning is still marked (the owner's ruling says to mark the reasoning roles, and Clarification 6 names `^6` and `^9`), but it carries a flag and is never counted as `^9`. It has its own row with no bar. Whether such a conclusion is a true `^9` is a canon question now listed for the owner | In effect: no unflagged `^9` without an `^8` is scored |
| 3 | BLOCKER | Rule 15(d) required a pair that rule 2 forbade | Guide v1.1: rule 2 names both rule-15 cases. 15(d) says an uncertain pair is not a clear pair | Yes (kept the uncertain marking, excluded from the bars, as the reviewer allowed) |
| 4 | BLOCKER | Counting uncertain entries as "marked" lets shared hedging pass the bars | Plan v1.1: only clear entries count. Uncertain `^8`/`^9` are reported in their own rows | Yes |
| 5 | MAJOR | "Same words" was too loose (half of the shorter quote) | Plan v1.1: half of the content words of the **longer** quote. Exact-match and the old loose test are reported beside it | **Partly.** The reviewer asked for exact match as the primary test. I did not take that: two teams told to quote "as short as possible" will differ by a word or two on the same thing, and an exact-match bar would fail for that reason alone. The longer-quote test stops a short quote from matching a different, longer one, which was the reviewer's concern |
| 6 | MAJOR | Agreement ignored the Mind and the related thing | Plan v1.1: those fields must agree too, per the guide's table | Yes |
| 7 | MAJOR | Too few passages without a Mind, so kappa for `^1` is driven by the base rate | No-person passages raised from 20 to 60. A Noetic with fewer than 50 passages where neither team marks it gets no verdict | Yes |
| 8 | MAJOR | Present and absent counts per Noetic were not fixed in advance | The kinds fix the design counts (each of `^2` to `^9` asked for in at most 150 of 440 passages). Whether a Noetic is truly there is only known after labeling, so the plan adds a hard rule instead: at least 50 cases and at least 50 absences, or no verdict | **Partly.** The reviewer asked to verify the counts before sealing. That cannot be done without labels |

## What the stricter measure does to the practice numbers

I reran practice round 2 (30 passages, labels made under guide v0.2) through the new arithmetic. This is practice data with 5 to 26 cases per Noetic; it is not a verdict.

| Noetic | Old measure I reported (all passages) | Stricter measure (cases only, clear only, Mind and related thing must agree) |
|---|---|---|
| `^1` | 30/30 = 1.000 | 26/26 = 1.000 |
| `^2` | 29/30 = 0.967 | 4/8 = 0.500 |
| `^3` | 30/30 = 1.000 | 6/7 = 0.857 |
| `^4` | 29/30 = 0.967 | 4/7 = 0.571 |
| `^5` | 29/30 = 0.967 | 9/11 = 0.818 |
| `^6` | 29/30 = 0.967 | 0/3 = 0.000 |
| `^7` | 29/30 = 0.967 | 2/5 = 0.400 |
| `^8` | 25/30 = 0.833 | 5/9 = 0.556 |
| `^9` | 26/30 = 0.867 | 5/9 = 0.556 |

The reviewer's first finding was right, and my round-2 summary ("agreed closely on seven of the nine Noetics") overstated the agreement. On the fair measure, only `^1`, `^3` and `^5` were at or above 0.80 in that practice round.
