# Outside review

Asked for model: `deepseek-v4-pro`. Answered by model: `deepseek-v4-pro`. Finish reason: `stop`.

Files sent:

- `09_LABEL_AGREEMENT_PLAN_v2_0.md` (99597 bytes, sha256 `d62cee8ada2b7ebbe57ef61c747a9db971f5e4634297f31fe8cd43e2522d1718`)

## Reply, word for word

VERDICT: REJECT

BLOCKER
- Section 14, “The practiced files are the sealed files” and “item 10 = waived”; Section 15 step 5; Section 20 “When the owner changes a number.”  
Why: The owner may sign after seeing practice labels, change bars, `FIVE_BAR_ROW`, hold rulings, working lines, or guide/program files, and then waive item 10. That lets S2–S5 remain from the pre-change files, so the practice guard no longer tests the final method. The two-practice-round limit is bypassed. This permits post-hoc tuning with label-like practice results in hand.  
Fix: require the owner’s signature on all scored items before practice labels are generated, and remove the item 10 waiver. Any guide/checker/scorer/instruction/launch change after practice must require a new practice pass with the final files, or no seal.

MAJOR
- Section 7, matching step 5: “share at least one content word at the same place” and “first words at most 2 words apart”; “where a label stops is free.”  
Why: This is too permissive and can pair labels that are not the same thing or not the same extent, inflating E near the 0.80 bar. A one-word overlap plus close start can hide real label disagreements.  
Fix: require full content-word overlap of the shorter label inside the longer label at the same positions, or exact normalized label span; at minimum report how many matches depend on the loose rule.

MAJOR
- Section 10, outcome word 3, `NO_VERDICT_WAITING_ON_OWNER`.  
Why: The rule only compares outside-row total entries to inside-row total entries. It can be driven by volume of held/uncertain/ambiguous entries, not by whether those entries agree. It can also let large hidden outside disagreement through when outside is slightly less than inside.  
Fix: base withholding on outside-row agreement or a fixed maximum outside share, e.g. outside entries > 25% of all entries for that Noetic, rather than only outside > inside.

MAJOR
- Section 4, “Why these counts” and K1 = 140; Section 10, outcome `LABELABLE_UNDER_THIS_METHOD`.  
Why: The verdict set is deliberately enriched toward near-pass roles. The plan discloses the mix, but the outcome word is unqualified, so readers may take it as a general labelability verdict.  
Fix: make the outcome or report heading say `LABELABLE_ON_THIS_MIX` or otherwise state the stratified-set limitation in the verdict word itself.

MAJOR
- Section 21, “What team A’s receipt cannot show: which guide a sub-agent really read.”  
Why: The verdict treats Team A as following the sealed guide, but there is no programmatic record of what a Team A sub-agent actually read. It could use another guide or old labels without detection, which would invalidate the agreement claim.  
Fix: run Team A through a controlled labeling tool that sends and logs the guide, or add an auditable record of the exact guide/task read by each sub-agent.
