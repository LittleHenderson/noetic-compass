# Outside review

Asked for model: `deepseek-v4-pro`. Answered by model: `deepseek-v4-pro`. Finish reason: `stop`.

Files sent:

- `02_LABELING_GUIDE_v2_0.md` (108661 bytes, sha256 `4ed6cf1c93e80669dcb83e85309a9a5934fd1e9474500a6cd25e45ea3654260f`)
- `OWNER_SIGNOFF_SHEET.md` (13807 bytes, sha256 `def2deeec4cd6a72c312e57a7a43158e6045f7b28b5e4cb464d95f9bab4dd8ee`)

## Reply, word for word

VERDICT: REJECT

**1. BLOCKER — Part B working lines contradict Part A canon.**  
Part A table lists under `^7`: “Practice makes perfect.” and “Muscle memory.” But guide rule 6(b) makes “muscle memory” clear `^5`, and B5 says `^7` is “at most held”; rule 6(a) says practising with no rate gives no `^7`. Rule 14 and sign-off 9q then instruct labelers to follow the numbered rule even when a Part A saying points elsewhere. Why it matters: labelers will write entries that contradict the fixed definitions the owner cannot change; the 0.80 result then measures agreement with Part B, not with canon. Smallest fix: strike 9b/9e/9q and the related B5 lines; keep these as owner-held, never clear `^5` or no-entry.

**2. BLOCKER — Two Part B rules order opposite things for the same text.**  
Rule 10(a): “Words that say a thing has become background give no rate or pattern, so they are not `^7`.” Rule 17 H7-UNBROKEN gives as its example: “The constant hum of the industrial dryers had become a quiet backdrop to her thoughts” and requires a held `^7`. The same sentence is both “not `^7`” and “held `^7`.” Why it matters: two careful labelers will part on the same words; the pass row becomes unreadable. Smallest fix: delete that sentence from rule 10(a), and let H7-UNBROKEN govern when a listed unbroken word is present.

**3. BLOCKER — “Clue” `^6` entries violate the Part A definition of `^6`.**  
Part A defines `^6`: “An Idea impregnated with another Idea, the Ideas an Idea is composed of.” Rule 7 and sign-off 7e require every reasoning clue to be written as `^6` with `relative_to` empty, even when no whole is named, and count clues with no pass mark. Why it matters: these are not `^6` under canon; moving them out of the `^6` row lets the `^6` bar pass on a residual subset while evidential parts are ignored. Smallest fix: do not label no-whole pieces as `^6`; omit them or put them in one owner-open class.

**4. MAJOR — The sign-off sheet misstates the bar and allows wrong pass/fail.**  
Item 1 says the 0.80 bar applies to “every entry either team wrote,” but items 4 and 5 move held, ambiguous, reasoning, and clue entries outside the pass/fail row and say the pass is “for the clear entries only.” Item 3’s minimum counts are not applied to that clear-only row. Why it matters: a Noetic can pass or fail on a small clear subset while most entries are held out; clear-vs-held is counted as a miss in both rows even when both teams agree on presence and location. Smallest fix: score all-entry agreement and clear-only agreement separately; require minimum clear entries per row; treat clear-vs-held as owner-open rather than fail.

**5. MAJOR — The guide is too tangled for one read.**  
The three most likely split points are: (a) rule 16 steps 2–5, pointer chains and label start/stop; (b) `^7` order across rule 6 and rule 17, including the background/unbroken conflict; (c) sign/reasoning versus memory across rules 2, 7, 15, and 17. Why it matters: careful labelers will divide at exactly these boundaries, and the agreement test will measure guide complexity rather than role agreement. Smallest fix: replace these with deterministic cue lists and a single open-class hold; move edge examples to an appendix.

**6. MAJOR — The held kinds and working lines are not needed for the owner’s stated aims.**  
The owner asked only for role identification, short label plus full quote, and separate extra/missing counts. The eight hold codes and 17 working lines create out-of-row classes and the defects above. Why it matters: they add risk without supporting any of the three requested goals. Smallest fix: collapse them into one “owner-open” class; keep ordinary role rows for the requested counts.
