# Outside review (deepseek deepseek-reasoner)

Files reviewed: 06_VERDICT_PLAN_v1_0.md, 02_LABELING_GUIDE_v1_0.md

VERDICT: REJECT

1. **BLOCKER — Plan §Measures, strict agreement denominator is not fixed.** “Share of passages” could mean all 400. If so, both-absent agreements inflate: a Noetic marked in 50 passages with only 20 word matches scores (350+20)/400 = 0.925 and passes 0.80. Fix: compute strict agreement only on passages where at least one team marks the Noetic; require both-marked word match; report all-400 agreement separately.

2. **BLOCKER — Guide Part B rule 15(b) contradicts Part A `^9` and the field table.** It says mark `^9` for a reasoning conclusion with `relative_to: ""` and no `^8`. Part A defines `^9` as “The Idea brought to Mind by an Above/Cause trigger”; the table says `relative_to` = its trigger. This scores a non-canon `^9`. Fix: in scored entries, do not allow `^9` without an `^8` trigger; remove `^9` from 15(b) reasoning scoring, or mark `^8` too. Part A cannot be changed.

3. **BLOCKER — Guide rule 15(d) contradicts rule 2.** Rule 2 allows the `^8`/`^9` pair only when the passage says or plainly shows that noticing one thing brought a different thing to Mind; its only stated exception is 15(b). Rule 15(d) says that when the passage does not reveal which happened, mark the pair as ambiguous. That forces a pair when the guide says not to. Fix: delete 15(d)’s default pair; use `not_enough_information` or mark neither. If retained, exclude those entries from primary bars.

4. **BLOCKER — Plan §Measures counts “clear or uncertain” as marked for bars.** Rule 15(d) directs both teams to mark `^8`/`^9` ambiguous on “knew / recognised / could tell / meant” passages. Shared ambiguity can inflate kappa and strict agreement, so `LABELABLE_UNDER_THIS_METHOD` can be granted without clear agreement. Fix: primary bars use clear entries only—both teams clear and agree. Report ambiguous separately.

5. **MAJOR — Plan §Measures “same words” uses “at least half of the content words of the shorter quote.”** Short or overlapping quotes can be counted as agreement even when teams selected different spans. Fix: primary bar require exact normalized word-string match; keep half-content overlap as secondary.

6. **MAJOR — Plan §Measures strict agreement ignores `mind` and `relative_to`.** For `^4`, `^6`, `^7`, `^8`, `^9`, teams can agree on words but disagree about the Mind or the related Idea. Since those definitions are relational, this inflates agreement. Fix: require agreement on the relevant relational field(s) for those Noetics.

7. **MAJOR — Plan §Passages/K8 gives too few absences for `^1` Mind.** Under guide rule 4, `^1` is marked in every passage with any Mind. Only K8 (20 passages) is designed with no Mind, so `^1` has at most 20 absent cases. Kappa is prevalence-sensitive; the `^1` bar can be driven by base rate rather than real agreement. Fix: add at least 50 no-Mind passages or balanced presence/absence per scored Noetic, or exclude `^1` from the kappa bar.

8. **MAJOR — Plan §Passages does not pre-fix per-Noetic absence counts.** Kinds are writer briefs; label teams may mark extra Noetics, so absent cases for each Noetic are not fixed before labels. This makes kappa unstable and the “fair test” claim unverifiable. Fix: after mechanical checks, verify and report minimum present/absent counts per Noetic before sealing; write more passages if below threshold.
