# 09 — Label agreement, attempt 2: plan, version 2.1 (lean)

Status: PROPOSED. Nothing is sealed and nothing is labeled before the owner signs (`label_v21/OWNER_SIGNOFF_SHEET.md`). No passage or label of this attempt exists. The plan was never signed, sealed or used; it was amended in place on 2026-10-05, after the owner's ruling and an outside review (sections 17, 18). Nothing in it changes after the practice labels exist.

It follows the form of `06_VERDICT_PLAN_v1_2.md` (attempt 1). It changes only what the owner asked for on 2026-10-05, in two messages (`OWNER_DIRECTION_POINTING_AND_OPTION_B_20261005.json`, then `OWNER_RULING_MIND_AND_COLLOQUIALISMS_20261005.json`):

- "Use a short, consistent identifying label PLUS the full supporting quote. Don't reduce everything to one word".
- "Also count extra and missing roles separately."
- "MIND IS AN ENTITY, A BEING, ANYTHING THAT THINKS, MACHINE,HUMAN, ANIMAL, AI ETC.  POSITIVE AND NEGATIVE USE THE COLLOQUILISMS (SHOULD BE  IN LOCAL FILES) THE SAME ABOUT THE OTHER NOETICS"

The local file is `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`. So three things differ from attempt 1: the pointing rule, the entry-by-entry count, and presence, which now follows the owner's ruling (section 2).

## 1. The question

For each Noetic `^1` to `^9`: do two independent label teams, from different model families, write the same entries for unfamiliar, unmarked passages under guide v2.1? Two entries are the same when they have the same Noetic, point at the same place in the passage, for the same Mind, with the same related thing.

`^0` Idea is not scored (owner decision in attempt 1: every thing pointed to is an Idea).

## 2. What changed from attempt 1, and what did not

| | Attempt 1 (plan v1.2) | Attempt 2 (this plan) |
|---|---|---|
| Definitions (guide Part A) | canon, word for word | the same ten definitions. A script copies Part A out of the owner's file. It also holds the owner's sentence on Mind and the Colloquialism Test of Clarifications 5 and 6 |
| Who is a Mind (rule 4) | a rule the study wrote | the owner's ruling: any being that thinks. The operator reads it to include a being only spoken of |
| When `^2` to `^9` are present | the study's rules 5, 6, 7, 10 and 13, and for `^8` and `^9` its rules 2 and 3 | rules 5, 6, 7, 10 and 13 are removed; 2 and 3 no longer decide presence (section 15). New rule 5: the Colloquialism Test decides |
| The other working rules | guide v1.2 | rules 1, 8, 9, 11, 12, 14 and 15: the same bytes, but for one clause of rule 15 |
| How an entry points | one field `words`, "as short as possible" | `label`: 1 to 12 words, the passage's own naming of the thing. `support`: the whole sentence or sentences that show the role, at most 4. Rule 16 is one pointing rule of six steps |
| The saying | not written down | new field `saying`, 2 to 20 words, `""` for `^1`. It shows that the test was applied. Never compared, never scored |
| What is counted | passages. A case agreed when one pair of entries matched | entries. Each entry pairs with at most one entry of the other team. An entry only one team wrote counts against agreement |
| "The same place" | half of the content words of the longer quote | the two labels overlap in the passage, and every content word of the shorter is in the longer |
| Bars | 0.80 and 0.60, with 50 and 50 | the same numbers, proposed again. 0.80 now applies to entry agreement |
| Passages | 440 from a blind writer, nine kinds | 440 new ones. The same writer, brief, kinds and counts. New settings |
| Labeling run | one try, no checker; only the model name asked for was stored | a form checker, up to three tries. Withdrawn and dropped entries are counted. The model name in every reply is stored |

## 3. What a pass and a failure show

- A pass means: two model teams point at the same things for that Noetic under this guide.
- A pass does not show that the labels are right. Two teams can agree and both be wrong. Two language models can share a bias.
- A pass tests no reader. No reader is run in this attempt.
- A failure is a failure of this method for that Noetic. It is not a statement about CAS.
- The passages are written by a language model. Only two model families label (Claude and DeepSeek).

No forecast is made. How presence by the owner's ruling moves agreement is NOT MEASURED: no labeler has worked under it. It may go either way. Two careful labelers can choose different sayings for one moment, so the pass mark may be missed for reasons of judgment even when pointing is right. Not measured yet. Rule 4 lists more Minds; that too is not measured.

## 4. Frozen inputs

| Item | File |
|---|---|
| Labeling guide | `02_LABELING_GUIDE_v2_1.md` |
| Part A builder; the canon file it copies from | `tools/build_guide_part_a_v21.py`; `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`, sha256 `cda85c03273c47f7df9ac53258920b95ba7b3b2007b0e760856a67497f661880` |
| The owner's rulings | `OWNER_RULING_MIND_AND_COLLOQUIALISMS_20261005.json` (Mind; the sayings). `OWNER_RULING_SIGN_READING_20261004.json` (guide rule 15) |
| Labeler instructions | `label_v21/LABELER_INSTRUCTIONS.txt` |
| Checker (form only); scorer | `tools/check_labels_v21.py`; `tools/verdict_v21.py` |
| Attempt-1 program | `tools/verdict.py`, never changed (sha256 `ee85ccf5a909…`). It holds the scorer's small-word list and its table of fields that must agree |
| The measure's fixture | `label_v21/fixture/`. `FIXTURE_EXPECTED.json` pins every number of the measure |
| This plan | `09_LABEL_AGREEMENT_PLAN_v2_1.md` |
| Writer, seal tool, team B tool, team A tool | `tools/write_passages_v21.py`, `tools/seal_v21.py`, `tools/label_outside_v21.py`, `tools/team_a_receipt_v21.py` |
| Team A's task message | fixed text in the seal tool, written to `team_a/TASK_MESSAGE.txt` |
| Owner sign-off record | `label_v21/OWNER_SIGNOFF_RECORD.json`, written by the operator from the owner's pasted line |
| Records | `label_v21/practice/PRACTICE_SET.json`, then `label_v21/verdict/SEAL.json` |

The seal tool puts the sha256 of every file above into the two records before a label team starts, except the sign-reading ruling, whose words stand in guide rule 15.

The seal tool refuses, in every mode, unless the Part A builder's check prints IDENTICAL: the canon file must have the sha256 above, and Part A of the guide must be what the script cuts out of it and of the ruling record.

## 5. The measure

### Which entries count (the bar row)

As in plan v1.2:

- Clear entries only. An entry marked `"certainty": "ambiguous"` is not in the bar row.
- A `^9` flagged `"reached_by": "reasoning"` is not in the bar row.

Two more lines, fixed now:

- Entries the checker dropped are not paired. They are counted (section 7).
- A passage that one team could not label is left out of the measure for both teams. It is counted (section 7).

### When two entries may pair

One entry from each team, in the same passage, and all of these hold:

1. **Same Noetic.**
2. **The labels point at the same place.** Their character spans in the passage overlap. And every content word of the shorter label is a content word of the longer label. Content words are what is left when small words such as "the", "of" and "her" are set aside. The list is in `tools/verdict.py`.
3. **Same Mind.** The two `mind` labels pass test 2. `^6` has no Mind.
4. **Same related thing, where plan v1.2 requires one.** That is `^4`, `^6`, `^7`, `^8` and `^9`. The two `relative_to` labels pass test 2. Two empty fields agree. One empty and one filled do not.

The scorer does not read the field `saying`.

Where things stand, for the overlap test:

- A label stands at its first place inside its `support`.
- A `^1` label, and so a Mind, stands at the first place its name stands in the passage. Guide rule 16 puts the `^1` support there, and the checker refuses another one.
- A related thing counts at every place its words stand in the passage.

The pairing is one to one. The program takes the largest set of pairs these tests allow, by a fixed rule. The same files always give the same pairs.

### The counts, per Noetic

- **A entries**, **B entries**: the bar-row entries each team wrote.
- **M**: matched pairs.
- **only A**: entries of team A with no pair. Each is an extra role for A and a missing role for B. **only B**: the same for team B.
- **Entry agreement E = M / (M + only A + only B).**

### A small worked example (made up)

Three passages, Noetic `^2`, one Mind in each.

- Passage 1. A: "the old brass scale". B: "the old brass scale on the counter". 1 pair (one label inside the other).
- Passage 2. A: "the smell of fresh sawdust" and "her grandfather's plane". B: "the smell of fresh sawdust". 1 pair (same span exactly), 1 only A.
- Passage 3. A: none. B: "the quiet of the early shift". 1 only B.

M = 2. only A = 1. only B = 1. E = 2 / (2 + 1 + 1) = 0.50. M / A = M / B = 0.667. Cases 3. Fully matched cases 1. Strict-label view: passage 1 is no pair, so 1 / (1 + 2 + 2) = 0.20.

### Printed beside E, per Noetic

- **Strict-label view**, no bar: E after a new pairing in which a pair counts only if the two labels also have the same content words in the same order. A pair by containment only then counts as one entry only A wrote and one only B wrote.
- M / A and M / B.
- Cases: passages where at least one team has a bar-row entry. Fully matched cases: cases with no unpaired entry.
- Cohen's kappa on presence: does the team have at least one bar-row entry of that Noetic in the passage.
- How the M pairs split: same span exactly; one label inside the other; other overlap. A pair is listed by the loosest of its label, its Mind and its related thing.
- 95% intervals for E and kappa, by resampling whole passages 2,000 times, seed 20261006.

### Printed with no bar

- The same table over all entries, clear and ambiguous pooled.
- The rule-15 rows of plan v1.2: uncertain `^8`, uncertain `^9`, `^9` reached by reasoning.
- Attempt 1's passage-level "strict agreement", recomputed on the new labels, for comparison.
- A mechanism-free floor. The Noetic symbols are shuffled among team B's entries inside each passage, 300 times, seed 20261007, and E is recomputed. It shows what E is when the role names carry no information.
- An Effect reached by reasoning is shown apart only when the labeler sets the flag. One line lists where the flag may be missing: per team, clear `^9` entries without it whose support holds an example word of guide rule 15(b).

The `^8` row and the `^9` row are close to one measurement printed twice. In a pair, each needs the other as its related thing.

## 6. Proposed bars and outcome words

These bars are PROPOSED. The owner signs them before anything is sealed or labeled.

| Outcome | Rule |
|---|---|
| `LABELABLE_UNDER_THIS_METHOD` | at least 50 cases, at least 50 passages where neither team has a bar-row entry, E at least 0.80, and kappa at least 0.60 |
| `NOT_LABELABLE_UNDER_THIS_METHOD` | enough cases and enough such passages, and either number below its bar |
| `NOT_ENOUGH_CASES` | fewer than 50 cases, or fewer than 50 such passages. No verdict for that Noetic |

- The outcome uses the measured values. The report says plainly when an interval reaches below a bar.
- A failed bar is a failure. It is never a pass with caveats.
- The program prints the outcome words. Nobody else does.
- The 0.80 is harder to reach than in attempt 1. Every entry only one team wrote now counts against it.
- If the owner signs other numbers, those are in force. The operator puts them in the scorer. The seal tool refuses to seal unless the scorer holds the signed numbers. The seal record keeps both sets.

## 7. When no verdict is printed, and when the run is invalid

The scorer refuses to print a verdict unless:

- the hashes in `SEAL.json` match the files: passages, guide, instructions, checker, scorer, plan, and the attempt-1 program;
- every sealed passage has a final record from both teams;
- each team's receipt names the sealed guide hash.

A final record is one of two things, in the words of the checker both teams use:

- `LABELED`: the last try has no checker message. That record is final.
- `NOT_LABELED`: three tries were made, and the third still has a message. Its row carries `"labeler_failed": true` and no entries.

A passage with a failing last try and fewer than three tries is `OPEN`. It is not final.

The run is INVALID if, for either team:

- more than 5% of the passages could not be labeled; or
- more than 5% of the team's entries were dropped by the checker. The scorer runs the checker again on the last try of every passage. An entry that still has a message there is dropped and counted; or
- more than 5% of the team's entries were withdrawn between tries. An entry that was in an earlier try and is absent from the final record is withdrawn. The checker counts, per Noetic, how many more entries an earlier try held than the last try holds. An entry taken out because a checker message said so counts too.

"The team's entries" are the entries of its last tries. For the withdrawn share, the withdrawn entries are added to them. Dropped and withdrawn entries are printed per team and per Noetic. For an invalid run the program prints `RUN_INVALID_NO_OUTCOME` for every Noetic. It is not repaired by relabeling the same passages.

## 8. Passages

- **Writer:** Gemini `gemini-2.5-flash`, as in attempt 1. Tool: `tools/write_passages_v21.py`. It sends the brief of attempt 1, character for character, with the same twelve forbidden words. The tool checks this by sha256 before it runs. The writer never sees the guide, the definitions, a label or a reader. The model name in each reply is stored.
- **Number:** 440, 30 per call, in a fixed seeded order (seed 20261021), eleven for each of 40 settings. Job list sha256 `b72264e963574e6b58930344ec0baf476b2a5a480e7a5b7532e033188b5c7efb`.
- **Kinds:** the nine kinds of attempt 1, K1 to K9, with the same counts: 60, 60, 60, 60, 60, 30, 30, 60, 20. The table in `06_VERDICT_PLAN_v1_2.md` says what each kind is. The wording sent to the writer is copied from `tools/write_verdict_passages.py`; the tool checks that by sha256. The label teams are never told the kind.
- **New settings only.** Earlier rounds used 112 settings. The tool holds that list and refuses to run if one is used again. The 40 new settings are `SETTINGS['verdict']` in the tool. The job list sha256 above fixes them.
- **Mechanical checks only, before sealing** (`tools/seal_v21.py`): a passage is dropped if it holds a forbidden word, has fewer than 30 or more than 120 words, or repeats exactly another passage of this set, a practice passage, or one of the 428 old passages. Dropped passages are counted and not replaced. Nobody reads the passages to choose among them.
- **Seal:** the kept passages are shuffled with seed 20261023 and get ids `W001…`. Their hash goes into `label_v21/verdict/SEAL.json`. The writer's kinds go to `label_v21/verdict_HIDDEN_FROM_LABELERS/`, outside the folder the teams work in.
- The 428 passages of attempt 1 are never scored for a verdict again.

## 9. The practice tool check

- **When:** after the owner has signed, and before the 440 are sealed.
- **What:** 30 fresh passages, ids `R01…`: three for each of 10 settings used nowhere else (`SETTINGS['practice']` in the writer tool). Kinds: K1, K2 and K4 four each; the other six three each. Writer seed 20261022, job list sha256 `29e3075b9ed9b53e7fa94eece0a12bf12b3cfc098d5849dcd91bf3854fb88d2c`, shuffle seed 20261024.
- **It may show only two things:**
  1. The tools chain end to end: writer, seal tool, both teams with the checker, both receipts, scorer.
  2. Each team stays inside the three 5% limits of section 7, and the checker rejects fewer than 5% of its entries (exactly 5% does not pass).
- **It decides nothing else.** The scorer's practice mode prints no agreement number and no outcome word, only `PRACTICE CHECK: PASS` or `NOT PASSED`.
- **What may not change after practice labels exist:** the guide, the measure and the bars. A defect found there is a new version with a new review. The seal tool refuses to seal the 440 unless the guide, this plan, the owner sign-off, the canon file, the owner's ruling record, `tools/verdict.py` and every file of `label_v21/fixture/` are the ones in the practice record.
- **What may change:** a tool bug may be fixed, in a program or in the labeler instructions. The fix may not change what the guide or this plan says, or a number in `FIXTURE_EXPECTED.json`. Every changed file is listed in `SEAL.json` with both hashes.
- **A new practice pass with the final files, or no seal.** After a change to the instructions or the checker, both teams label the 30 passages again under a new file name. After a change to a team's tool or to team A's task message, that team does. The seal tool enforces this. Both practice receipts must name the files about to be sealed. Then the tool runs the scorer's practice mode itself, and that must print `PRACTICE CHECK: PASS`.
- **If the check does not pass:** nothing is sealed. A cause in the guide, the measure or the bars stops this version.

## 10. Label teams, and who sees what

- **Team A:** Claude Sonnet sub-agents, one for each chunk of about 40 passages. A workflow script starts them. Each prompt is a file that `tools/team_a_receipt_v21.py prompt` writes: the task message with its three places filled in, the full guide text and the instructions text, and nothing else. The script hands that file over unchanged. The sub-agent hands its records in with `check_labels_v21.py take`, up to three tries per passage, into its chunk's own labels file.
- **Team B:** DeepSeek, asked for as `deepseek-chat`, through `tools/label_outside_v21.py`. One passage per call, temperature 0, the same guide, instructions and checker, up to three tries.
- Each team sees the guide, the instructions, its passages and the checker's messages. Neither sees the other's labels, the kinds, or the writer's brief.
- **Team A's task message** is fixed text in the seal tool (`TEAM_A_TASK`). The seal tool writes it to `team_a/TASK_MESSAGE.txt` and records its sha256. The team A tool fills in its three places and changes nothing else. The message says: hand in only with `take`; never run the checker in another way; open no other file. `take` logs every try. `check` logs nothing and is for the operator only. Before the verdict the operator searches the team A transcripts for a `check` run and for an import of the checker, and reports what is found.
- **Team A's labels file and receipt** are written by `tools/team_a_receipt_v21.py receipt`, not by a sub-agent. It refuses unless the chunks together are the passage file and every prompt file is still the text it builds from the files on disk. It joins the chunks' try logs, line for line, and runs the checker's `take` over all passages with nothing new handed in: no try is logged, and the checker writes team A's labels file. The receipt, `<labels file>.receipt.json`, holds the sha256 of the guide, the instructions, the checker, the passages, the task message, the tool and the labels file; each chunk's files with their sha256; and the session ids the workflow script names (not checked). `"complete"` is true only when that `take` run ended with exit code 0 (every passage final) and every chunk's own labels file holds the same rows. What a sub-agent was really given, only the transcripts show.
- **Team B's model name** is given on the command line, and the name in every reply is stored. `deepseek-chat` is the name attempt 1 asked for. MEASURED on 2026-10-05 (`verdict/NOTE_TEAM_B_MODEL_NAME_20261005.md`): it is an alias answered by `deepseek-flash`, with no reasoning text. The report will say so. The bare name `deepseek-flash` was never tested, so it is not used. The tool also stores, per try, whether the reply held reasoning text; the receipt counts those tries. The name is the same for practice and for the verdict set.
- Label files are named `labels…`. The seal tool refuses to seal a folder that holds one.

## 11. Order of work

1. Build and Claude review (sections 16 and 17).
2. One outside review by `deepseek-v4-pro`, which does not label.
3. Owner signature.
4. Practice tool check (section 9).
5. Seal the 440. The seal tool runs the practice check again first.
6. Both teams label. The program prints the verdict.
7. Spec sheet and changelog entry, with the artifact path.

## 12. Rules of conduct

- No guide change, no relabeling, no dropped passage and no changed bar after labels are seen.
- A finished passage is never asked again. Resuming a stopped run only finishes open passages.
- A new attempt needs new passages and a new plan version.
- The scorer computes every number. The operator reports its output.
- Claude is not the research governor. A failed bar does not license a replacement method. What follows a failure is the owner's decision.

## 13. Cost and cap

No AWS.

- **Passage writer:** Gemini free tier, about 20 requests a day. 16 calls are needed. The tool counts its own requests and stops cleanly at 18 in 24 hours, or on HTTP 429.
- **Team B, DeepSeek. ESTIMATE.**
  - MEASURED in attempt 1: 428 calls, 2,327,821 tokens sent (5,439 per call; guide 19,265 bytes), 88,948 returned (208 per call).
  - This attempt: guide at most 41,000 bytes, instructions at most 3,600. About 12,200 tokens sent per first try, about 600 returned. 470 passages. Assumed: a second try on 1 passage in 4, a third on 1 in 20. Total: about 7.6 million tokens sent, 0.37 million returned.
  - Price of `deepseek-flash`, READ once on 2026-10-05 from the service's price page by the builder of plan v2.0, not checked again. Per million tokens: 0.30 USD sent at peak hours and 0.15 off-peak, with no cache hit; 1.20 and 0.60 returned. So about 2.72 USD at peak hours, about 1.36 off-peak.
- **Cap for team B: 4.00 USD.** The tool cannot see prices. It enforces token counts, over all runs that write one labels file, kept in its checkpoint file. Practice (30 passages): at most 800,000 tokens sent and 60,000 returned, 0.31 USD at the peak price. Verdict (440 passages): at most 9,200,000 and 740,000, 3.65 USD. If a cap stops a run, open passages stay open. A second practice labeling is a new labels file. The operator gives it at most the tokens the first practice file left unused, so the total stays inside 4.00 USD. Raising a cap is the owner's decision.
- **Other:** one outside review call to `deepseek-v4-pro`, about 19,000 tokens sent, price not read, outside the team B cap. Team A is 12 Claude sub-agents on this account's allowance.
- Money: the owner's approval of 2026-10-04 (`OWNER_APPROVAL_ALL_STAGES_20261005T0610Z.json`) named no figure. The ruling of 2026-10-05 granted none. Spending stays inside funds the ledger shows as unreserved. Each cost is reported.

## 14. Why version 2.0 was dropped

Version 2.0 was built on 2026-10-05, reviewed, rejected and never used. Its builders wrote their own lines on when a role is present. This version adds none: presence follows the owner's ruling and the owner's file. Here the owner signs first, and nothing is waived. Record: `label_v2/STATUS_V2_0_REJECTED.md`.

## 15. What this attempt leaves for the owner

- The two open definition questions, in the owner's words. Guide rule 15 stays in force as written until they are answered.
  1. "Does recognizing a familiar sign count as Cause → Effect when it brings another idea to mind?"
  2. "Does an idea reached through reasoning also count as Effect?"
- One reading is the operator's, not the owner's words: a being that is only spoken of is listed as a Mind (guide rule 4). The owner may strike it.
- Guide rules 2 and 3 no longer decide presence (operator's decision: the ruling is applied in full). A `^8` or `^9` that the test marks is written alone when its partner is not named.
- A case the Colloquialism Test leaves open stays open; the study adds no rule for it. Examples: whether a group (a crew) is a Mind; the questions in `design_v2/labeling_final.json`, field `spec.questions_only_the_owner_can_settle`.

## 16. Review round 1: findings and what was done

Three Claude reviewers read the first build: 2 blocking and 24 major findings.

- **Blocking: a guide line changed when an entry is written.** The v1.2 sentence is back.
- **Blocking: examples X7 and X8 settled presence questions.** Both passages were changed.
- **A Mind could stand at two places; "pointer" had no test.** Guide rule 16 and section 5.
- **The sheet said every role is counted.** Corrected. It also says what the signature starts.
- **Part of the measure was in no seal; the 440 could be sealed with no practice pass.** Sections 4, 7 and 9.
- **The practice check passed labels that make a run invalid.** Check 2 is now the three 5% limits. That is wider than the design's one limit, and it stays.
- **An entry taken out on the checker's own instruction counts as withdrawn.** It stays so (section 7).
- **Nothing fixed team A's task message or its receipt.** Section 10.
- **Pair split; duplicate entries.** Changed in the scorer and the checker.

## 17. The amendment of 2026-10-05

Made after the owner's ruling, before any signature, seal or label. Changed: the presence rows of section 2, the forecast (removed), sections 4 and 10, the cost estimate, section 15 (review round 2). No labeler was run.

## 18. Outside review of version 2.1 and what was done

REJECT: `label_v21/OUTSIDE_REVIEW_GUIDE_PLAN_SHEET.md`.

1. Guide rule 15 named removed rule 10 (blocking): followed. It names rule 5.
2. Rule 2 decided presence: followed. It says only how to write.
3. Rule 5 was not Part A's test: followed. It asks A9's two questions (section 3).
4. Pairs by containment: followed in part. The owner on such selections: "They largely agreed about the meaning but selected different amounts of text". So test 2 stays; the strict-label view stands beside it.
5. The reasoning flag is unchecked: followed (section 5).
