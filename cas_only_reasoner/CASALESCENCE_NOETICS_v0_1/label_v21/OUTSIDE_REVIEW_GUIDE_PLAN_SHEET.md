# Outside review

Asked for model: `deepseek-v4-pro`. Answered by model: `deepseek-v4-pro`. Finish reason: `stop`.

Files sent:

- `02_LABELING_GUIDE_v2_1.md` (39954 bytes, sha256 `d65ad695bfa13755f812938cf3bd97b03f4048e9bdcb769bb2e0d9e87cacc958`)
- `09_LABEL_AGREEMENT_PLAN_v2_1.md` (24992 bytes, sha256 `84d8743647471c345fbdbcc90862e7e8e152a4143086705f751d0907de6d20ea`)
- `OWNER_SIGNOFF_SHEET.md` (3174 bytes, sha256 `32cad8c21aec891a42307079a95142d404e3c23cb7d300fe6ff1adeccf157d7a`)

## Reply, word for word

VERDICT: REJECT

1. **BLOCKER — Guide Part B, rule 15, last bullet.** It says: “A bodily reaction alone is not a `^9`… It may be `^4` under rule 10.” But Part B rule 10 is now a stub: “*Removed by the owner's ruling of 2026-10-05; rule 5 now decides.*” This is a direct contradiction/dangling reference. A labeler cannot apply the owner’s sign/body rule as written, and teams will diverge on flinch/startle cases. Fix: replace “under rule 10” with “if the Colloquialism Test marks it as `^4`,” or delete that clause.

2. **MAJOR — Guide Part B, rule 2 still decides presence.** Quote: “Mark a clear pair only when the passage says or plainly shows that noticing one thing brought a different thing to Mind.” The plan says rules 2 and 3 no longer decide presence, but this is still a study-written WHEN gate. It can suppress a pair that the Colloquialism Test would otherwise mark when the passage only implies the trigger/effect relation. Fix: remove the “only when…” gate and make rule 2 purely about how to write pairs, lone entries, and flags after rule 5 decides presence.

3. **MAJOR — Rule 5 is not a faithful operationalization of Part A’s test.** Part A A4 says the sayings are “representative, not exhaustive”; rule 5 tells labelers to match the Noetic “whose canonical sayings (A4, A5) and definition (A1) that saying matches.” Two careful labelers can supply different native-speaker sayings and part widely on: (i) `^2` vs `^3` vs no entry for mild attraction/aversion; (ii) `^8` trigger vs `^9` alone vs reasoning; (iii) one moment as several Noetics. The owner should expect 0.80 entry agreement may fail for judgment reasons even when pointing is correct. Fix: no guide change that invents a presence rule; disclose this explicitly in the sign-off and plan.

4. **MAJOR — Plan §5 matching test can pass for the wrong reason.** It pairs when “their character spans in the passage overlap. And every content word of the shorter label is a content word of the longer label.” Guide rule 16 forbids bare nouns and forbids running into the words that state what the thing did. But the scorer would pair a bare noun like “the ferry” with the correct “the ferry to her grandmother's island,” and would pair an overrun label like “The smell of hot tar drifted over the wall” with the correct “The smell of hot tar.” So rule-16 violations still count as agreement. Fix: require identical normalized content-word sequence for a pair, not containment.

5. **MAJOR — Reasoning `^9` separation depends only on a self-reported flag.** Guide rule 15(b) has the labeler write `"reached_by": "reasoning"`; plan §5 excludes only “A `^9` flagged `"reached_by": "reasoning"`.” If both teams omit the flag on a conclusion reached by reasoning, those entries enter the clear bar row as ordinary `^9` pairs and can satisfy the pass mark. The sign-off says “an Effect reached by reasoning” is shown apart, but that is true only when the labeler sets the flag. Fix: amend the sign-off to state that the flag is unverified, or add a report-only scan of clear `^9` entries whose support contains the guide’s own reasoning words (“worked out,” “checked,” “ruled out,” “compared,” “so it had to be”).
