# 09 — Label agreement, attempt 3: plan, version 2.2

Status: PROPOSED. Nothing is sealed and nothing is labeled before the owner signs (`label_v22/OWNER_SIGNOFF_SHEET.md`). No passage or label of this attempt exists.

This plan repeats attempt 2 (`09_LABEL_AGREEMENT_PLAN_v2_1.md`, sha256 `657413f77f182c7310071505e89d01452eb9e62cd97ac0c69d954051218430cd`, signed by the owner on 2026-10-06) with one deliberate change: the labeling guide. The owner gave his answers on 2026-10-07 after comparing the guide with his book *Reality Engineering* (`label_v22_draft/OWNER_ANSWER_REALITY_ENGINEERING_EXAMPLES_20261007.json`). Everything else stays as in attempt 2, except what the guide change forces in the instructions, the new passages, and the team B token caps for a longer guide. The measure, the bars, the validity rules, the form checker and the measure's fixture are those of attempt 2, unchanged.

## 1. The question

The same as attempt 2. For each Noetic `^1` to `^9`: do two independent label teams, from different model families, write the same entries for unfamiliar, unmarked passages, now under guide v2.2? `^0` is not scored.

## 2. What changed from attempt 2, and what did not

| | Attempt 2 (plan v2.1) | Attempt 3 (this plan) |
|---|---|---|
| Labeling guide | v2.1 | v2.2 (`02_LABELING_GUIDE_v2_2.md`). Part A unchanged; the builder's check prints IDENTICAL. Changed: rules 2, 3, 5 and 15; seven table rows (`^2` to `^6`, `^8`, `^9`); the field list (no reasoning flag); examples X1, X5 and X6; ten worked examples E1 to E10 taken from attempt 2's sealed passages. The change tables up to version 2.1 move out, by a pointer. Its last change table lists every change, the owner's answer behind it, and which changes are the operator's |
| The owner's open questions on signs and reasoning | open; rule 15 kept the study's reading | answered on 2026-10-07. A recognized sign that brings another Idea to Mind is a clear Cause and Effect. A memory that only follows a sign, with no linking word, is an uncertain pair. A conclusion reached by reasoning is an Effect. Evidence is a Cause when it independently meets the definition, and Male only inside a named whole |
| Reasoning flag (`"reached_by": "reasoning"`) | set on a reasoned conclusion, which the measure then kept out of the bar row | not used, and no text a labeler reads names its field. A gate program stops the run if any final entry carries it (section 7). So every scored clear `^9` is in the bar row (operator's design after review; section 5) |
| Reasoning-flag gate | none | `tools/flag_gate_v22.py`, new: before the verdict it prints `RUN_INVALID_NO_OUTCOME` if any final entry of either team carries the flag |
| Form checker | `tools/check_labels_v21.py` | the same file, unchanged |
| Labeler instructions | `label_v21/LABELER_INSTRUCTIONS.txt` | `label_v22/LABELER_INSTRUCTIONS.txt`: the guide's name changes, and the line on the reasoning flag is removed |
| Measure, bars, outcome words, validity rules | plan v2.1, sections 5, 6 and 7 | unchanged, word for word (section 5 below) |
| Scorer | `tools/verdict_v21.py` | `tools/verdict_v22.py`: the same program with new file names, schema names and default paths; it imports the unchanged checker. The measure is unchanged |
| Fixture | `label_v21/fixture/` | the same folder, unchanged; the scorer's fixture mode prints PASS |
| Passages | 440 from 40 settings; 30 practice from 10 settings | 440 and 30 new ones, from 40 and 10 new settings (section 8) |
| Team A start | the plan said "a workflow script"; attempt 2 used the Agent tool with one fixed wrapper (recorded as a deviation) | the Agent tool with the fixed wrapper `label_v22/TEAM_A_WRAPPER.txt`, fingerprinted by the seal tool (section 10) |
| What the seal tool fingerprints | plan v2.1, section 4 | the same, plus the owner's answers of 2026-10-07, team A's wrapper and the gate; it refuses if an earlier passage set is missing |
| Team B caps | 4.00 USD over practice and verdict | 5.00 USD: the guide is longer (section 13) |

## 3. What a pass and a failure show

As in plan v2.1, section 3. A pass means two model teams point at the same things for that Noetic under this guide. It does not show that the labels are right, and it tests no reader. A failure is a failure of this method for that Noetic, not a statement about CAS. No forecast is made. How the owner's answers move agreement is NOT MEASURED.

## 4. Frozen inputs

| Item | File |
|---|---|
| Labeling guide | `02_LABELING_GUIDE_v2_2.md` |
| Part A builder; the canon file it copies from | `tools/build_guide_part_a_v21.py` (unchanged); `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`, sha256 `cda85c03273c47f7df9ac53258920b95ba7b3b2007b0e760856a67497f661880` |
| The owner's rulings and answers | `OWNER_RULING_MIND_AND_COLLOQUIALISMS_20261005.json`; `OWNER_RULING_SIGN_READING_20261004.json`; `label_v22_draft/OWNER_ANSWER_REALITY_ENGINEERING_EXAMPLES_20261007.json` |
| Labeler instructions | `label_v22/LABELER_INSTRUCTIONS.txt` |
| Checker (form only); scorer; reasoning-flag gate | `tools/check_labels_v21.py` (unchanged); `tools/verdict_v22.py`; `tools/flag_gate_v22.py` |
| Attempt-1 program | `tools/verdict.py`, never changed (sha256 `ee85ccf5a909…`) |
| The measure's fixture | `label_v21/fixture/` (unchanged) |
| This plan | `09_LABEL_AGREEMENT_PLAN_v2_2.md` |
| Writer, seal tool, team B tool, team A tool | `tools/write_passages_v22.py`, `tools/seal_v22.py`, `tools/label_outside_v22.py`, `tools/team_a_receipt_v22.py` |
| Team A's task message; team A's wrapper | the fixed text of attempt 2, in the seal tool, written to `team_a/TASK_MESSAGE.txt`; `label_v22/TEAM_A_WRAPPER.txt` |
| Owner sign-off record | `label_v22/OWNER_SIGNOFF_RECORD.json`, from the owner's pasted line |
| Records | `label_v22/practice/PRACTICE_SET.json`, then `label_v22/verdict/SEAL.json` |

The seal tool puts the sha256 of every file above into the two records before a label team starts, except the sign-reading ruling, whose words stand in guide rule 15. It refuses as in plan v2.1, sections 4 and 9. Between practice and the 440 it also refuses if the owner's answers or team A's wrapper changed.

## 5. The measure

Plan v2.1, section 5, applies unchanged, word for word: the bar row (clear entries, not a `^9` reached by reasoning), the pairing tests, the one-to-one pairing, E, the printed views, the strict-label view, kappa, the intervals, the mechanism-free floor and the reasoning-flag hint line.

Guide v2.2 does not use the reasoning flag, and no text a labeler reads names its field. The gate of section 7 stops the run if any final entry carries it. So every clear `^9` that is scored is in the bar row, including a conclusion reached by reasoning, and the rule-15 row "`^9` reached by reasoning" is empty. The hint line still lists clear `^9` entries whose support holds one of rule 15(b)'s words; it changes no count.

## 6. Bars and outcome words

As in plan v2.1, section 6, proposed again for the owner to sign: E at least 0.80 and kappa at least 0.60, with at least 50 cases and at least 50 passages where neither team wrote a bar-row entry of that role. Outcome words: `LABELABLE_UNDER_THIS_METHOD`, `NOT_LABELABLE_UNDER_THIS_METHOD`, `NOT_ENOUGH_CASES`. A failed bar is a failure.

## 7. When no verdict is printed, and when the run is invalid

As in plan v2.1, section 7: the same final records, the same three 5% limits, and `RUN_INVALID_NO_OUTCOME` for an invalid run.

One more condition, new in this attempt. Before the scorer runs for a verdict, the operator runs `tools/flag_gate_v22.py` on both teams' labels files. If it prints `RUN_INVALID_NO_OUTCOME`, no verdict is computed, and the report gives the gate's line. The gate also runs on the practice labels before the seal; a flag there is a tool problem, to be fixed in the instructions as plan v2.1, section 9, allows.

## 8. Passages

- **Writer:** Gemini `gemini-2.5-flash` through `tools/write_passages_v22.py`, with the brief, the nine kinds, their counts and the forbidden words of attempts 1 and 2, checked by sha256 before it runs.
- **New settings.** 40 settings for the 440 (eleven each, seed 20261031, job list sha256 `3ca66a165b6fb0d765e9b3a002614a7846709513807bbb57b16dc152a3d633e3`) and 10 for the 30 practice passages (three each, seed 20261032, job list sha256 `218c8f8f3214e0060e9375137bca2b98972fd314c80694151e9d5fa4796d0c9e`). The 162 settings of earlier rounds are in the tool's list `EARLIER`; its check reads them from the earlier tools and confirms the list is complete. None of the 50 is an earlier setting, and none shares a word of five letters or more with one. Three near-copies found in review ("a taxi rank", "a ski lift", "a laundrette") were replaced before any passage was written.
- **Mechanical checks, before sealing** (`tools/seal_v22.py`): forbidden word, 30 to 120 words, and exact repeats of this set, its practice set, the 428 passages of attempt 1, and the 427 sealed and 30 practice passages of attempt 2. Dropped passages are counted and not replaced. Nobody reads the passages to choose among them.
- **Seal:** shuffle seeds 20261033 (the 440) and 20261034 (practice); ids `W001…` and `R01…`. The writer's kinds go to the folder `_HIDDEN_FROM_LABELERS` beside the set.
- **Quota:** the free tier allows 20 requests a day and resets at midnight Pacific. The writer counts its requests in the same ledger as attempt 2 and stops cleanly at its daily count or on HTTP 429; a stopped run resumes.
- The passages of attempts 1 and 2 are never scored for a verdict again. The ten used as worked examples in guide v2.2 come from attempt 2's sealed set, which the exact-repeat check covers.

## 9. The practice tool check

As in plan v2.1, section 9, with the v2.2 files: 30 practice passages, both teams, `PRACTICE CHECK: PASS` or no seal. It decides nothing else.

## 10. Label teams, and who sees what

- **Team A:** Claude Sonnet sub-agents, one for each chunk of about 40 passages. The operator starts each with the Agent tool and gives it the text of `label_v22/TEAM_A_WRAPPER.txt`, word for word, with its prompt file's path in place of `<PROMPT FILE>`, and nothing else. The wrapper is attempt 2's, but for one number: "about 70 KB" instead of "about 46 KB", the size of a version 2.2 prompt file. The prompt file is written by `tools/team_a_receipt_v22.py prompt`.
- **A clean start.** Before team A starts, the operator moves every file of earlier labelers and of the operator out of the session's scratch folder into `label_v22_draft/operator_scratch/`, which no labeler is pointed to.
- **Team A's receipt** is written by `tools/team_a_receipt_v22.py receipt`, as in plan v2.1, section 10. Before the verdict the operator lists every path each team A transcript names, and records any path outside the labeler's prompt file, chunk file, working file and its own new scratch files, any run of the checker's `check` mode, and any import of the checker.
- **Team B:** DeepSeek, asked for as `deepseek-chat`, through `tools/label_outside_v22.py`: one passage per call, temperature 0, the same guide, instructions and checker, up to three tries. In attempt 2 every reply named `deepseek-flash`; the report will say what this run's replies name.
- Each team sees the guide, the instructions, its passages and the checker's messages, and nothing of the other team, the kinds or the writer's brief. The guide does not name attempt 2's report or its outcome. Label files are named `labels…`; the seal tool refuses a folder that holds one.

## 11. Order of work

1. Build, and one Claude review round (two reviewers; `label_v22/BUILD_REVIEW_ROUND1.md`).
2. One outside review by `deepseek-v4-pro`, which does not label (REJECT: `label_v22/OUTSIDE_REVIEW.md`); the fixes (`label_v22/OUTSIDE_FIX_RECORD.md`); one outside recheck.
3. Owner signature.
4. Practice tool check, with the gate on the practice labels.
5. Seal the 440. The seal tool runs the practice check again first.
6. Both teams label. The gate runs; then the program prints the verdict.
7. Spec sheet and changelog entry, with the artifact path.

## 12. Rules of conduct

As in plan v2.1, section 12. No guide change, relabeling, dropped passage or changed bar after labels are seen. A new attempt needs new passages and a new plan version. The scorer computes every number. Claude is not the research governor: what follows a failure is the owner's decision.

## 13. Cost and cap

No AWS.

- **Writer:** Gemini free tier; 16 calls plus retries.
- **Team B, DeepSeek. ESTIMATE.** MEASURED in attempt 2: 469 tries for 427 passages, 5,884,931 tokens sent and 176,544 returned, with a system text of about 44,900 characters, so about 3.58 characters per token. Here the system text is 66,111 characters (the team B tool's dry run), so about 18,600 tokens per try. With 1.1 tries per passage over 470 passages: about 9.6 million tokens sent and 0.2 million returned. At the price read on 2026-10-05 and not checked again (0.30 USD per million sent and 1.20 per million returned at peak hours; half that off-peak): about 3.1 USD at peak, about 1.6 off-peak.
- **Caps, in the team B tool's token counts, set by the operator on its command line:** practice at most 1,200,000 tokens sent and 60,000 returned; verdict at most 12,000,000 and 400,000. At the peak price that is at most 4.51 USD. A second practice labeling is a new labels file; the operator gives it at most the tokens the first practice file left unused, so the total stays inside the cap. **Registered cap for team B: 5.00 USD.** The owner's standing authorization of 2026-10-07, in the project's settings, allows a paid job inside its registered cap or 10 USD per run, whichever is higher. Raising a cap is the owner's decision.
- **Other:** the outside review call to `deepseek-v4-pro` (MEASURED: 32,280 tokens sent, 10,903 returned) and one recheck. Team A is about 12 Claude sub-agents on this account's allowance (about 3.1 million sub-agent tokens in attempt 2).

## 14. What stays open

- The operator's reading that a being only spoken of is a Mind (guide rule 4) is put to the owner on the sign-off sheet: signing adopts it; he may strike it instead.
- The changes the guide's last change table marks "operator" are listed by name on the sign-off sheet: the reasoning flag removed; what counts as a link between a sign and an Idea; "came to him" and "was suddenly in" not links, so X1 is an uncertain pair; one `^8` per trigger and one `^9` per conclusion. Signing adopts them; the owner may correct any.
- A case the Colloquialism Test leaves open stays open; the study adds no rule for it.

## 15. Build checks already done

- Part A of guide v2.2: `tools/build_guide_part_a_v21.py check` prints IDENTICAL.
- Every example record of guide v2.2 (P00, X1 to X11, and E1 to E10 from ten sealed passages of attempt 2) passes the unchanged checker `tools/check_labels_v21.py` in its operator mode. No example record carries the reasoning flag.
- No text a labeler reads names the flag's field: the guide, the instructions, team A's task message and team A's wrapper each hold it 0 times.
- `tools/flag_gate_v22.py` on attempt 2's final labels, which did use the flag: it finds 84 flagged entries and prints `RUN_INVALID_NO_OUTCOME`, exit 1.
- `tools/verdict_v22.py` fixture mode on the unchanged `label_v21/fixture/`: PASS. It reads rule 15(b)'s five example words from guide v2.2.
- `tools/write_passages_v22.py`: both dry runs pass; its earlier-settings check finds 162 earlier settings, all in `EARLIER`, and none of the new ones.
- `tools/label_outside_v22.py --dry-run`: system text 66,111 characters; at most 22,237 tokens for one first try by the tool's own upper estimate.
- Build scripts and drafts: `label_v22_draft/` (`make_guide_v22_draft.py`, `build_worked_examples.py`, `make_v22_tools.py`).
