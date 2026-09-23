# Two Helm investigations, read together (2026-09-23)

**The owner's instruction.** "Integrate the two investigations as complementary evidence, not competing
verdicts."

**The two investigations.**

| | Claude team review | Codex failure research |
|---|---|---|
| Record | `records/helm_why_review_20260922/` | `records/helm_failure_research_20260922/` |
| Branch and commit | `research/helm-why-review-20260922` @ `26f1b465` | `codex/helm-failure-research-20260922` @ `a6e6f95b` |
| Who | 31 agents | A1 to A6, with judge A7 |
| Committed findings | 32 (D1 to D32) | the judgment in `agents/A7/FINAL_JUDGMENT.md` |
| Judge's result | 15 UPHELD, 17 UPHELD_IN_PART | A7 final judgment |
| Also committed | | `agents/A7/NEXT_ACTIONS.md` |

Both are merged unchanged into `research/helm-integration-20260923`: Claude's at `f1156d03`, Codex's at
`604c1f08`. Neither rewrites the other.

**Where the claim states come from.** The claim states below are each source's own; the table's
"Read together" column adds no new measurement. For every topic, the arithmetic agrees. Where one
investigation measured behaviour and the other found the mechanism, they are combined.

| Topic | Claude review | Codex A7 | Read together |
|---|---|---|---|
| **Why Helm 2.0 got its label** | D10: runs 11/1, 12/0, 7/1; only 20260919 fails (p 9/256); the lineage file names the wrong run | Section 1: the same six-row table; "no zero-loss veto"; `MIN_PASSING_B=7` is the zero-loss minimum only | **Settled.** Two Helm 2.0 runs lost a question. Only one run, 20260919, failed the rule. |
| **The failing run's lost question** | D11: correct from p00 to p08; the VIA gap goes from +6.360389709472656 to -3.6662044525146484 at p10; the start already had 4 of 18 | Section 1: final `VIA_N1 = 26.474693298339844` vs correct `VIA_N3 = 22.808488845825195`; the correct candidate ranks second; all four presentations agree; the loss falls within updates 1177-1470 | **Complementary.** The timing comes from D11, the endpoint scores from A7. **Cause: unproved in both.** The next step is `HELM-REACH-LATE-1`. |
| **Analogy** | D8: every final model gives ONE constant world for all 70 analogy records; "0.42 train / 0.00 held" was a constant, not memorisation | Section 3: the candidate scorer has no focus-to-candidate comparison; 62 candidates score identically across the witness pair; one fixed ranking cannot satisfy both disjoint accepted sets | **Complementary.** D8 is the behaviour; A7 is the mechanism that produces it. The repair is `HELM-ANALOGY-REPAIR-1` (Codex). The wiring check is Claude's probe. |
| **Correspondence** | D12: 0 to 20/20 held in Helm 2.0; a rule that reads no links matches it | Section 3: Helm 1.0 sends the same target-score row to every source, so all bijections tie; the decoder already enumerates complete bijections; normalisation alone cannot change the decision | **Complementary.** Earlier text saying "needs a Sinkhorn decoder" or "cannot express a bijection" misdescribed the **decoder** (see `HISTORICAL_CORRECTIONS.md`, C6). The decoder is preserved. |
| **Helm 1.0 loop defect** | D9: real, but no measurement shows it set the limit | Section 3: the local message input is real, but "the whole model is one-hop" is too strong | **Agree.** |
| **"New worlds"** | D4, D1: only 6 shapes exist, so "new worlds" were renamed practised shapes | Section 3: all 5 held focus worlds match trained worlds; a witness mapping is given | **Agree.** This is why `HSET-1` exists. |
| **No-learning floors** | D6, D7: the floor is 11/18; rules written before the run give 16/18 | A5 (reported by A7): the degree comparator scores 70/70 on analogy; exact-edge search scores 70/70 on analogy and 88/88 on correspondence | **Complementary.** Both go into `HSET-1`'s comparator list (A6). |
| **Ten-node development panel** | D17: every one of its questions is outside the trained input range, so it has no power to explain the misses | Section 2: exact class table; "majority-ABSENT success" is contradicted; a constant ABSENT would match 42/53 | **Complementary.** |
| **Retention** | D12: 86->78, 93->93, 84->82 | Section 2: identical | **Agree.** |
| **Trust tool** | D19: its rule fails 15 cells the grader passes; its agreement check never compares each run's pass result | Section 5: the zero-loss shorthand is "contradicted" | **Agree.** The active repair is Codex's. Claude's reference implementation is `trusted_rescore_reference_claude_v0_3.py` on this branch. |
| **Q4** | D21 to D29: no pass mark; 0/16; no code defect found at the level tested; cause OPEN | Section 5: Q4 does not explain the historical checkpoints | **Agree.** It stays a separate experiment (`Q4-RECON-2`). |
| **Common root** | D31: weak yardsticks; tests that fixed programs already answer; parts built but never fed or never read | Section 4: several plausible causes; no single neural cause is established | **Compatible.** D31 is about the tests and the process; A7 is about neural cause. Neither claims what the other rules out. |

**Differences in emphasis, kept as they are:**
- A7 declines architecture-only or optimizer-only explanations of the gate loss. Claude's judge recorded the
  same caution for the loop question (D9, D14, dissent list).
- Claude's review ran three local-GPU diagnostics on Q4. These are `DIAGNOSTIC_NOT_CLAIM_BEARING`. A7 ran no
  neural work.

**What this integration does not do.**
- It changes no label.
- It certifies nothing.
- It does not choose between the reports. Where they differ only in scope, both stand.
