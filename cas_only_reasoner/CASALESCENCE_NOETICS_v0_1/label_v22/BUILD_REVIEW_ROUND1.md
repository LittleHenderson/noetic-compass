# Build review, round 1 (2026-10-07): two Claude reviewers, and what was done

Two independent Claude reviewers (Opus sub-agents, read-only) reviewed the first build of guide v2.2, plan v2.2 and the v2.2 tools on 2026-10-07. Their reports are summarized finding by finding below, with what was done. The full reports are kept in the session transcripts (`subagents/agent-ade56cadeee259267.jsonl` for the guide, `subagents/agent-a07711935bf3d0479.jsonl` for the plan and tools).

## Reviewer 1: guide v2.2. VERDICT: REJECT

| Finding | Severity | What was done |
|---|---|---|
| B1. Rule 2 still said a reasoned conclusion "is marked on its own", against rule 15(b) as changed | BLOCKER | Rule 2's sentence now follows rule 15: a sign the passage does not link to the Idea is an uncertain pair; a lone entry also covers a conclusion whose evidence is not a Cause |
| B2. Owner answer 10 (a clear pair needs a link) not carried through: X1 stayed a clear pair; 15(a) still listed "came to him" and "was suddenly in" | BLOCKER | X1 is now an uncertain pair (other candidate "none"); the two phrases left 15(a)'s list, with one sentence saying why. Marked "operator, applying answer 10" in the change table |
| B3. 15(b) made evidence a Cause automatically, plus an operator bracket reading canon; X6 conflicted with Part A, A8 ("working out" is `^6`, not `^8`) | BLOCKER | 15(b) now quotes the owner's ruling and applies rule 5 to each piece of evidence: a Cause when it brings the conclusion to Mind as a trigger does, Male only inside a named whole, both, or neither; logical analysis stays `^6` (A8). The bracket is gone. Rule 5 points to the ruling. X6 has no `^8` |
| M1. X6's `^8` label began with a verb | MAJOR | Moot: X6 has no `^8` |
| M2. The reasoning flag decided matching, and (a), (b), (c) differed only by it | MAJOR | The flag is gone from the guide and the instructions (see reviewer 2, finding 1) |
| M3. One trigger with several Ideas, and several things bringing one Idea, had no written form | MAJOR | The table's `^8` row now says: one entry per trigger; things that together bring one Idea as the joint subject of one verb are one `^8`; with several Ideas brought, the related thing is the one the passage says it brought. E10's note says the label is the joint subject of "told her" |
| M4. E4's `^7` label "for years" differs from the approved "had served for years" without saying so | MAJOR | Listed in the change table: "for years" follows rule 16 (rate words as short as possible); both pair under the measure |
| Minor: other_candidate "reasoning" pointed to a rule that no longer used it | MINOR | The field line now says what the value means and points to rule 15(b) |
| Minor: "knew" cases in example passages left unshown | MINOR | Not changed: the worked examples say only the entries for their point are shown |

## Reviewer 2: plan v2.2 and the v2.2 tools. VERDICT: ACCEPT_WITH_NOTES

| Finding | Severity | What was done |
|---|---|---|
| 1. A `^9` flagged as reasoning stays outside the bar row, so the flag could only lower `^9` agreement; the owner's ruling makes such a conclusion an Effect | MAJOR | The reasoning flag is removed from the guide (rule 15(b), the field list, X6) and from the instructions. The measure is unchanged, so every clear `^9` is now in the bar row. With no flag in use, the frozen v2.1 checker and the unchanged v2.1 fixture are used; the draft v2.2 checker and fixture copy were deleted |
| 2. The plan said the seal tool hashes every listed file; it did not hash the owner's answers | MINOR | The seal tool now also fingerprints the owner's answers and team A's wrapper text; plan section 4 names the one exception (the sign-reading ruling, whose words stand in rule 15) |
| 3. A missing earlier passage set was skipped silently; the record kept bare file names | MINOR | The seal tool refuses when an earlier set is missing and records relative paths |
| 4. Three settings were near-copies of earlier ones ("a taxi rank", "a ski lift", "a laundrette") | MINOR | Replaced by "a holiday cottage", "a stationery shop" and "a sweet shop"; job-list fingerprint updated |
| 5. Caps not tied to the plan by the tool; repeat-practice remainder rule dropped; source of "10 USD per run" not found | MINOR | Plan section 13 restores the remainder rule and names the source (the owner's standing authorization of 2026-10-07 in the project settings); the sheet says the limits are set by the operator, at the price read on 2026-10-05 |
| 6. The sheet dropped the operator's reading on Mind; "passages with no entry" was loose | MINOR | Both fixed on the sheet |
| 7. The guide's status named attempt 2's report and outcome (labelers read the guide); the shared scratchpad holds attempt-2 labelers' scripts; the transcript scan was too narrow | MINOR | The status no longer names the report or the outcome. Plan section 10: the operator moves earlier labelers' scripts and the operator's files out of the session scratchpad before team A starts, and the transcript scan lists every path each labeler names |
| 8. Small accuracy points ("five table rows", "DRAFT" in labeler-visible text, no build script for the checker copy, wrapper not hashed) | MINOR | Plan section 2 corrected; the guide's title says "candidate"; the checker is the frozen v2.1 file; the wrapper is `label_v22/TEAM_A_WRAPPER.txt`, fingerprinted by the seal tool |
