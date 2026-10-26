# 08 — Option B usefulness test: the plan, version 1.0

**Status: PROPOSED. Not sealed yet. Nothing has been run. No model was called. No money was spent.**

**Revised on 2026-10-05 after review round 1.** Six reviewers read the draft. Section 26 lists every blocking and major finding and what was done. The version number stays 1.0, because nothing was sealed before the revision.

**Amended on 2026-10-05 after an outside review.** A reviewer that is not Claude read the plan (`optionb/OUTSIDE_REVIEW_PLAN.md`). Its verdict was ACCEPT_WITH_NOTES, with seven major findings. The operator then made twelve amendments, A1 to A12. Section 27 lists every finding and every amendment and what was done. The version number stays 1.0, because nothing was sealed.

**Amended again on 2026-10-05 after an owner ruling.** The owner ruled on Mind and on the canonical colloquialisms (`OWNER_RULING_MIND_AND_COLLOQUIALISMS_20261005.json`). The operator then made one more amendment, A13: in the role notes that model B reads, each canon definition line is followed by that Noetic's canonical sayings. A13 is the operator's reading of the ruling, applied to a place the owner did not name. The owner may strike it. A short list of small faults was fixed at the same time. Sections 27.3 and 27.4 list both. The version number stays 1.0, because nothing was sealed.

This is the pre-registration. A pre-registration is a plan that is fixed, and hashed, before any result exists. After the seal, no rule in it changes.

Three files belong together and are sealed together:

- this plan: `C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/CASALESCENCE_NOETICS_v0_1/08_OPTION_B_PLAN_v1_0.md`
- every number and wording a program needs: `optionb/PLAN_CONSTANTS.json`
- every file that passes between programs: `optionb/FILE_FORMATS.md`

If this plan and `PLAN_CONSTANTS.json` ever disagree, that is a build error. The build stops. Nobody picks a side by hand.

The design this plan fixes is `design_v2/optionB_final.json` (sha256 `de0a0a50dcde3914054ee7cca2951b5a5077348f42409478240c1e40dbc52425`). Its three reviews are `design_v2/optionB_reviews.json` (sha256 `06c9d2884b1510ad7f65946ae8a69d88a1d16d9fe3f8f51fa7898d677ba6ffe5`). The operator then made ten decisions, D1 to D10. They are listed in section 23 and are applied everywhere in this text. After the outside review the operator made twelve amendments, A1 to A12 (section 27). Where an amendment and an older decision differ, the amendment holds. After the owner's ruling of 2026-10-05 the operator made amendment A13 (section 27.3). It holds in the same way.

**Words used for every number in this plan**

| Word | Meaning |
|---|---|
| REAL | Measured on 2026-10-05 from the sealed files, by a small counting script. |
| PROPOSED | A rule of this plan. It is not a measurement. |
| EXPECTED | An estimate. Nobody has measured it. |
| ASSUMED | An input to a simulation. Not a measurement. |
| NOT MEASURED | Nobody knows yet. The build or the practice phase will print it. |

**Canon rule.** The Noetic definitions are quoted word for word from Part A of `02_LABELING_GUIDE_v1_2.md`. Programs read them from that file when they build a note. Nobody retypes or rewords them. This plan does not retype them either. The canonical sayings of amendment A13 are handled the same way. Programs copy them, character for character, from the table "Canonical colloquialism map" in Clarification 6 of `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`. Nobody retypes, rewords, shortens or reorders a saying. This plan prints no saying. Noetics are written `^1` to `^9`. No Worlds, Domains, Drives or Registers appear in any note, question, brief or label.

---

## 1. The question

Model B is `Qwen/Qwen2.5-0.5B-Instruct`, frozen. It answers a multiple-choice question about a short passage.

**Is B right more often when its prompt also holds a checked role description of that passage?**

A role description says which words occupy which Noetic `^1` to `^9`, for which Mind, relative to what. It comes from the two label teams, and only where both teams agree.

Second question, same run: do the role notes break answers that B already gets right?

Third question, same run: do the role names add anything beyond pointing at the right words?

This is the owner's option B. It tests whether the information is useful. It does not test any reader. The owner's sentence stands: "A later test must still show that the internal reader can supply equally useful descriptions."

## 2. What decides

"Better" means better than the strongest ordinary help of the same length. Ordinary help is plain notes from an equally strong model that never saw the CAS guide. Beating "no notes" is not enough.

A program applies the rules in sections 13 to 16 and prints exactly one outcome code. No status comes from prose. A failed condition is a failure. It is never "pass with caveats".

The test is built to answer four objections. Each has its own control.

| Objection | Control |
|---|---|
| "It was just more words." | group FILLER |
| "A strong model summarised the passage." | groups ORD-INFORMED and ORD-FREE |
| "The answer leaked." | the seals, the blindness rules, the answer-leak screen |
| "It only pointed at the right sentence." | groups QUOTES-ONLY and MIXED |

## 3. Sources and their hashes

All sources are read-only. All hashes are REAL (sha256, computed 2026-10-05).

| File (under `CASALESCENCE_NOETICS_v0_1/`) | Bytes | sha256 |
|---|---:|---|
| `verdict/labels_team_a.json` | 314,980 | `afb609c95adc45da43a8ef2b3ab5718ffbfc46e4a92bd1b56d8b3dfae7218584` |
| `verdict/labels_team_b.json` | 358,934 | `8c5be47223ea6b7a840c11f7e3eba51fbb34767640240c924869b8515038b460` |
| `verdict/passages_kinds_HIDDEN_FROM_LABELERS.json` | 174,797 | `e9b6f8030d698af7c6f3bb8bb8439ba26fcfcceccbc4740769e64eb71e139622` |
| `02_LABELING_GUIDE_v1_2.md` | 19,265 | `3ed4196dbfb0ad0d96a785f03929229e18d23ff226c7687df363d683bfd8022e` |
| `tools/verdict.py` | 13,018 | `ee85ccf5a909d0ed252f6b3faa42cdb5f57510613781e89d8d4aaa2d0d52cbbb` |
| `../../docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` | 64,154 | `cda85c03273c47f7df9ac53258920b95ba7b3b2007b0e760856a67497f661880` |

The sixth file is new with amendment A13. It holds the canonical sayings. It lies outside that folder. Its full path is `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`. The constants and the seal file write it as `../../docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`: counted from the study folder like every other path, two steps up. REAL, 2026-10-05: 64,154 bytes, LF line ends, last commit `1c8531ea` (2026-04-21), unchanged since that commit. Its hash is the one in the owner's ruling record.

Also pinned in `PLAN_CONSTANTS.json`: `tools/write_verdict_passages.py`, `03_SCORER_RULES_v0_1.md`, `tools/scorer_v0_1.py`, `scorer_examples_v0_1.json`, the directive, the owner's direction, and the owner's ruling of 2026-10-05 on Mind and the colloquialisms (`OWNER_RULING_MIND_AND_COLLOQUIALISMS_20261005.json`, 4,245 bytes, sha256 `a88d9fe8179f7c052e1c91f69bcdbcdff9745757b1e35cf2276dc1b714c1b024`).

- **The sayings (amendment A13).** Programs read one thing from the sixth file: the table under the heading `### Canonical colloquialism map` in Clarification 6. The table has one row per Noetic and three columns: the Noetic, its authoritative definition, and its folk-form colloquialisms. REAL, checked by a small script on 2026-10-05: the table has 10 rows, `^0` to `^9`. In every row the definition cell equals, character for character, the definition of that Noetic's line in Part A of the guide.
- **Passages.** REAL: 428 passages, 41 to 70 words each, in 40 settings. Written by Gemini `gemini-2.5-flash` from a brief with no CAS word.
- **Labels.** Team A is Claude Sonnet sub-agents. Team B is DeepSeek, asked for under the model name `deepseek-chat`. Both used guide version 1.2. The labels existed before any question exists. That is the main guard against leaked answers.
- **A fact about that model name** (REAL, measured 2026-10-05; the record is `verdict/NOTE_TEAM_B_MODEL_NAME_20261005.md`). The name `deepseek-chat` is now an alias. A call that asks for it is answered by `deepseek-flash`. Label team B was asked for under the name `deepseek-chat`, and the model that answered was not recorded then. So this plan can not prove which model wrote team B's labels. Wherever this plan says DeepSeek `deepseek-chat`, it means "asked for under that name". From now on every tool that calls an outside service stores, for every call, the model name the service put in its reply (amendment A9).
- **Model B.** `Qwen/Qwen2.5-0.5B-Instruct`, revision `7ae557604adf67be50417f59c2c2f167def9a775`. REAL: 7 pinned files, 999,586,347 bytes; `model.safetensors` sha256 `fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe`. Weights frozen. No training. This job never calls model A.

## 4. What "checked" means

An entry is **checked** only when both teams gave a clear entry for the same Noetic and the pair passes the same-reading test that is already frozen in `tools/verdict.py`.

- **Clear entry.** Not marked uncertain. For `^9`, not flagged "reached by reasoning".
- **Same reading.** The two quotes share at least half the content words of the longer quote. The Mind and the related thing also agree, by the same test, where the guide requires them for that Noetic.
- **One to one.** Entries are paired one to one, per passage and per Noetic. One match can not cover extra entries. This is the owner's "count extra and missing roles separately".
- **Pairing rule (PROPOSED, fixed).** Take team A's clear entries in file order. For each, take the first team B clear entry in file order that is not yet used and is the same reading. REAL: on these labels this simple rule finds as many pairs as the largest possible pairing, in every passage and every Noetic.
- Programs import the frozen functions from `tools/verdict.py` after checking its hash. They do not copy or rewrite them.

Entries that only one team gave are left out of every note. They are counted apart as "only team A" and "only team B".

REAL entry counts over all 428 passages, as agreed / only team A / only team B:

| `^1` | `^2` | `^3` | `^4` | `^5` | `^6` | `^7` | `^8` | `^9` |
|---|---|---|---|---|---|---|---|---|
| 384/19/46 | 51/24/19 | 35/13/17 | 54/40/58 | 88/31/65 | 173/140/156 | 35/31/61 | 38/23/32 | 38/23/34 |

Limit: two language-model teams agreeing is consistency. It is not proof of correctness.

## 5. The exclusion rule

Two definition questions are still open with the owner (section 22, questions 1 and 2). No task may depend on either.

**Rule.** A passage is left out of every family and every group when either team wrote any rule-15 entry on it. A rule-15 entry is any raw entry that has:

- Noetic `^8` or `^9` with `"certainty": "ambiguous"`, or
- `"other_candidate": "reasoning"`, or
- `"reached_by": "reasoning"`.

REAL: that is 104 passages (K6 30, K7 30, K3 29, K4 11, K5 3, K1 1). It includes every K6 and K7 passage. 324 passages remain.

Also not used: K8 and K9 passages. Passages `V009` and `V076` are barred, because an earlier design printed them with example questions. They never become a task.

**Eligible passages.** A passage is eligible when it is not excluded and its agreed entries open at least one question form (section 7). REAL: 192 passages (K1 36, K2 55, K3 25, K4 37, K5 39).

`tools/ob_eligibility.py` must reproduce every REAL count in `PLAN_CONSTANTS.json` under `counts_real`. If it cannot, it stops and nothing is sealed.

## 6. How a role description is built

A program builds it. No model writes it. Nobody edits it. No label is changed. For each agreed pair of entries:

- **Short label** = the shorter of the two teams' quotes, by number of characters. On a tie, team A's.
- **Mind and related thing** = for each field, the shorter of the two teams' quotes that is not empty.
- **Full supporting quote** = the whole sentence or sentences of the passage that hold both teams' quotes.

Why the whole sentence: the owner asked for a short label PLUS the full supporting quote, and warned against one word alone.

**Sentence rule (fixed).** A sentence ends at one or more of `.` `!` `?`, plus any closing quote mark or bracket, when white space or the end of the text follows. A single full stop right after `Mr`, `Mrs`, `Ms`, `Dr`, `Prof`, `St`, `Jr` or `Sr` does not end a sentence. REAL: the passages hold `Dr.` 11 times, `Mr.` 11 times, `Mrs.` 4 times and `Ms.` once.

**The ROLE note, line by line.**

1. The canon definition line, word for word from guide Part A, for each Noetic that appears in this passage's entries, in number order. The line is printed as `<number> <name> — <definition>`. Right after each definition line comes that Noetic's sayings line (amendment A13; see "The sayings line" below).
2. One line per agreed entry. The `^1` lines come first. Then come the other entries. Both parts are in passage order. Passage order means: by where the quotes first appear in the passage; then by Noetic number.
3. A `^1` line has the label only. Every other line has the label, then `For the Mind "…".` and `Relative to "…".` where the guide gives that Noetic such a field, then the supporting quote.
4. A supporting quote that was already printed in the same note is replaced by `Supporting quote: same as for "<earlier label>".`

Fields printed per Noetic: `^2`, `^3`, `^5`: the Mind. `^6`: the related thing. `^4`, `^7`, `^8`, `^9`: both. `^1`: none.

**The sayings line (amendment A13).** It is the word `Sayings`, a colon, one space, then that Noetic's canonical sayings. The template is `Sayings: <<SAYINGS>>`. The sayings are the third cell of that Noetic's row in the table under the heading `### Canonical colloquialism map` (section 3), exactly as the cell stands in the file. Nothing is added, cut, reordered or changed: not a quote mark, not a slash, not a full stop.

Nothing is retyped. `tools/ob_role_notes.py` reads the table from the file when it runs. It builds no note unless all three hold:

- the file has the size and the sha256 of section 3;
- the table has exactly 10 rows, one for each of `^0` to `^9`;
- in each of the 10 rows the definition cell equals, character for character, the definition of that Noetic's line in Part A of the guide.

If a definition cell and the guide differ, the tool stops and reports. It writes nothing. Nobody picks one of the two texts.

The owner's sentence about Mind is not printed in any note. It governs labeling only (section 21).

Exact form, shown on a made-up passage that is never a case. Canon lines and sayings lines are shown as placeholders here, because this plan does not retype them:

```
Notes:
[Padding: neutral]
<canon line for ^1, copied from the guide>
<sayings line for ^1, copied from the table of Clarification 6>
<canon line for ^8, copied from the guide>
<sayings line for ^8, copied from the table of Clarification 6>
<canon line for ^9, copied from the guide>
<sayings line for ^9, copied from the table of Clarification 6>
- ^1 Mind: "Halima".
- ^8 Above/Cause: "the smell of wet rope". For the Mind "Halima". Relative to "her uncle's ferry". Supporting quote: "Halima unlocked the boathouse and the smell of wet rope met her at the door."
- ^9 Below/Effect: "her uncle's ferry". For the Mind "Halima". Relative to "the smell of wet rope". Supporting quote: "At once she was thinking of her uncle's ferry, the bench by the engine hatch, the tin of biscuits he kept under it."
```

There is no heading that claims authority. Every group sits under the same plain heading `Notes:` and nothing else.

Checks on the descriptions: the two teams agreeing is the check. No third model judges them, because no other model has seen the guide. A seeded sample of 20 built notes is written for the owner (`optionb/notes_role/owner_sample_20.json`).

Known limit, stated now: the stand-in rule adds whole sentences that the teams did not choose. Labels made under a new pointing rule may behave differently.

A second limit, from amendment A13: the labels behind these notes were made under guide version 1.2, before the owner's ruling of 2026-10-05. They were not made again (section 21).

## 7. Tasks

**A task** is one passage, one question, lettered options and exactly one right option. B replies with one JSON object, for example `{"answer": "C"}`. The right answer is one capital letter, as a string. Scoring is exact match on that letter.

### 7.1 Family R: role-step questions (the benefit set)

Every question adds a new condition that is not in the passage, and asks what most likely follows. To answer, the solver must first know which thing plays which part, then take one more step. The question never asks "which role is this?".

Six types, twelve forms. A program opens a form for a passage only when the two teams agree on the entries it needs. No person chooses. Passage counts are REAL.

| Type | Passages | Form id | Plain name | Needs agreed | What the question asks |
|---|---:|---|---|---|---|
| BRING | 36 | `MEET_AGAIN` | Meet it again | one `^8` and one `^9` | Later and elsewhere, which option would most likely bring the same thing back to the person? |
| BRING | | `TAKE_AWAY` | Take it away | one `^8` and one `^9` | Suppose the noticed thing had not been there; which option would most likely not have happened? |
| PULL-PUSH | 54 | `GOES_FOR` | Goes for | one `^2` | At a later free moment, which does the person choose? |
| PULL-PUSH | | `KEEPS_AWAY` | Keeps away | one `^3` | Which does the person avoid? |
| LAND | 43 | `WHAT_STUCK` | What stuck | one `^4` | At a later moment, which thing is the person most likely to bring up? |
| LAND | | `WHAT_SLID_OFF` | What slid off | one `^4` | At a later moment, which thing is the person least likely to bring up? |
| FORMED | 45 | `SWAP_PERSON` | Swap the person | one `^5` | Someone without that past stands in the same spot; what most likely goes differently? |
| FORMED | | `WHERE_HELPS` | Where it helps | one `^5` | In which new situation would this background help most? |
| PARTS | 37 | `WHAT_LEFT` | What is left | two or more `^6` | Some named parts are dealt with; which named part is still left? |
| PARTS | | `NOT_BELONG` | Does not belong | two or more `^6` | A spare kit holds one of each named part; which of these would not be in it? |
| HABIT | 33 | `LONG_BREAK` | After a long break | one `^7` | The repeated thing stops for a year or two; which action has most likely faded? |
| HABIT | | `NEW_STARTER` | New starter | one `^7` | Someone on their first day takes the person's place; which of these would most likely be missing? |

REAL: together the types cover 192 passages. 137 open one type, 54 open two, 1 opens three.

Rules per passage:

- At most two role-step tasks.
- They must come from two different forms.
- Their right options must not be the same thing. The program compares the two right options with the looser word test in `tools/verdict.py` (they share at least half the content words of the shorter text). If they match, only one is kept.
- Different types are preferred where the passage opens two.
- A second LAND question is allowed only when the passage has two agreed `^4` entries.

These are everyday inferences from the role relations. They are not canon statements. Whether they are fair uses of the Noetics is an owner question (section 22, question 4).

Left out on purpose: no "which statement matches the passage" question (it would copy the note). No "really there, or only in thought" type. No counting form for parts. No question about what a sign means. No question about a conclusion someone worked out.

### 7.2 Family F: plain-fact questions (the no-harm set)

One per passage. It asks about a fact stated outright: where a thing was, who did what, which object. It must not depend on anyone's thoughts, likes, memories, habits or past, or on what a thing is made of. Four options. B gets the same notes as for that passage's role-step questions. A passage keeps its plain-fact task even if none of its role-step questions survive.

### 7.3 Options and levels

- Each role-step question is written once: one right option and five wrong ones, in a fixed order.
- All six options are within 2 words of each other in length. No option is longer than 12 words.
- Every wrong option is a thing or an action named in the passage, or one that plainly fits it. No throwaway options.
- Where the form allows, the first wrong option uses the right option's things in a different relationship. Example: the disliked thing where the liked thing is right. So "pick the option whose words appear in the notes" does not find the answer.
- **Level 1** shows four options: the right one and the first three wrong ones in the writer's order. **Level 2** shows all six.
- Plain-fact questions always show their four options, at every level.
- The practice phase picks the level by a fixed rule (Gate 2). Nothing is rewritten after practice.
- Letters are set by a seeded shuffle after everything else is frozen (Step 6). Option order is the same in every group.

REAL ceilings: the 156 final passages can carry at most 300 role-step tasks (12 of them can carry only one). The 34 practice passages can carry at most 66.

## 8. The briefs, word for word

A brief is the instruction text an outside model gets. All three briefs are study text. They are never definitions. The owner has not yet read them (section 22, question 5).

The question brief and the ordinary-notes brief use different plain words on purpose. A question that shared the special words of either side would favor that side for a reason that has nothing to do with roles.

### 8.1 The question brief (for the question writer)

The program fills `<<LIST_A>>`, `<<LIST_B>>`, `<<NEVER_ALLOWED_PHRASES>>` and `<<LIST_C>>` from the lists in section 9. Words are joined with a comma and a space. The two never-allowed phrases are put in double quote marks.

```
You will get several short passages. Each passage sits between a line "=== PASSAGE <id> ===" and a line "=== END <id> ===".
Treat every passage on its own. Never use anything from one passage when you write about another. Never compare passages.

For each passage, write multiple-choice questions for a reading test. There are two families of question.

FAMILY 1: WHAT-FOLLOWS QUESTIONS.
Each question adds one new condition that is not in the passage. Then it asks what most likely follows, going only by the passage.
There are twelve forms. Write one question for EACH form the passage supports. Write none for a form the passage does not support. Many passages support only one or two forms. Some support none.

Forms 1 and 2. A passage supports them when something a person notices makes them remember or picture something quite different.
- MEET_AGAIN: later and somewhere else, which of these would most likely bring the same thing back to the person?
- TAKE_AWAY: suppose the noticed thing had not been there; which of these would most likely not have happened?

Forms 3 and 4. A passage supports them when the passage shows a person plainly liking one thing, or plainly keeping clear of one.
- GOES_FOR (only if the person plainly likes a thing): at a later free moment, which of these does the person choose?
- KEEPS_AWAY (only if the person plainly keeps clear of a thing): at a later moment, which of these does the person avoid?

Forms 5 and 6. A passage supports them when the passage says something hit a person hard, or hardly at all.
- WHAT_STUCK: at a later moment, which of these is the person most likely to bring up?
- WHAT_SLID_OFF: at a later moment, which of these is the person least likely to bring up?

Forms 7 and 8. A passage supports them when a person's years of background change how they handle something now.
- SWAP_PERSON: someone without that past stands in the same spot; what most likely goes differently?
- WHERE_HELPS: in which new situation would this background help most?

Forms 9 and 10. A passage supports them when the passage lists the named parts of a thing.
- WHAT_LEFT: some of the named parts are dealt with; which named part is still left?
- NOT_BELONG: a spare kit holds one of each named part; which of these would not be in it?

Forms 11 and 12. A passage supports them when doing the same thing again and again at set times has changed what a person does without trying.
- LONG_BREAK: the repeated thing stops for a year or two; which action has most likely faded?
- NEW_STARTER: someone on their first day takes the person's place; which of these would most likely be missing?

Rules for every FAMILY 1 question:
- Give exactly six different options: one right option and five wrong options. Exactly one option may be right.
- Give the five wrong options in a fixed order. Where the form allows it, the FIRST wrong option uses the same things as the right option in a different relationship. Example: where the right option is the thing the person likes, the first wrong option is the thing the person keeps clear of.
- Every wrong option is a thing or an action named in the passage, or one that plainly fits the passage. No throwaway options.
- No option is longer than 12 words. All six options are within 2 words of each other in length. The right option must not stand out by its length. No option may contain another option.
- The question is at most 45 words long.
- Give one or two anchors. An anchor is an exact, unbroken copy of words from the passage, at most 8 words long, that the question turns on.
- Never ask the reader to name or sort the kind of moment. Ask only what most likely follows.
- Never ask what a sign means. Never ask about a conclusion that someone worked out step by step.

FAMILY 2: ONE PLAIN-FACT QUESTION.
Write exactly one for every passage. It asks about a fact the passage states outright: where a thing was, who did what, which object.
The fact must not depend on what anyone thinks, likes, remembers, usually does or has been through, or on what a thing consists of.
Give exactly four different options: one right option and three wrong options. The same length rules apply.

WORDS YOU MUST NOT USE.
In every question and in every option, never use these words or any word that begins with them: <<LIST_A>>.
In every question and in every option, never use the sign ^ and never use these words: <<LIST_B>>.
In every question and in every option, never write: <<NEVER_ALLOWED_PHRASES>>.
In the question sentence itself, also never use these words or phrases: <<LIST_C>>.

REPLY FORMAT.
Reply with ONE JSON array and nothing else. It holds one object per passage, in the order the passages were given:
[{"passage": "<id>", "what_follows": [{"form": "<FORM NAME>", "question": "...", "right": "...", "wrong": ["...", "...", "...", "...", "..."], "anchors": ["..."]}], "plain_fact": {"question": "...", "right": "...", "wrong": ["...", "...", "..."]}}]
"what_follows" may be an empty list. Use the form names exactly as they are written in this brief.

The passages follow.
```

After the brief comes one empty line, then the passages of the batch, with one empty line between them. Each passage is fenced like this:

```
=== PASSAGE <<ID>> ===
<<PASSAGE>>
=== END <<ID>> ===
```

### 8.2 The ordinary-notes brief, ORD-INFORMED

`<<N>>` is the word target (section 11.3).

```
A weaker reader will be asked multiple-choice questions about this passage. You do not know the questions. They may ask what brought what into someone's thoughts, what someone is drawn toward or put off by, how strongly or weakly something landed, what a person has lived or learned, what named pieces a thing is made of, what someone does over and over on a schedule, and plain details. Write the notes that would help most. Plain words. Add nothing the passage does not support. About <<N>> words.
```

### 8.3 The ordinary-notes brief, ORD-FREE

It is the ORD-INFORMED brief without the sentence that lists the kinds of question.

```
A weaker reader will be asked multiple-choice questions about this passage. You do not know the questions. Write the notes that would help most. Plain words. Add nothing the passage does not support. About <<N>> words.
```

### 8.4 How a brief is sent to the note writer

First writing:

```
<<BRIEF>>

Reply with the notes only, as plain text. No heading.

Passage:
<<PASSAGE>>
```

The one allowed rewrite, after a failed support check:

```
<<BRIEF>>

An earlier set of notes for this passage failed a check: at least one sentence was not supported by the passage. Write the notes again from the start.

Reply with the notes only, as plain text. No heading.

Passage:
<<PASSAGE>>
```

### 8.5 The support-check brief (for the note checker)

```
You will get several items. Each item sits between a line "=== ITEM <id> ===" and a line "=== END <id> ===". Each item holds one passage and one note about that passage.
Treat every item on its own. Never use one item to judge another.

For each item decide one thing only: is every sentence of the note supported by its passage?
A sentence is supported when the passage states it or plainly shows it. A sentence that says the passage does not mention something is supported when the passage indeed does not mention it.
A sentence is not supported when it adds a fact, a reason, a feeling or a detail that the passage does not give.
If every sentence is supported, the verdict is PASS. If one or more sentences are not supported, the verdict is FAIL.

Reply with ONE JSON array and nothing else. It holds one object per item, in the order the items were given:
[{"item": "<id>", "verdict": "PASS"}, {"item": "<id>", "verdict": "FAIL"}]

The items follow.
```

### 8.6 The two solver texts

With the passage:

```
Read the passage. Then answer the multiple-choice question. Go only by the passage.

Passage:
<<PASSAGE>>

Question: <<QUESTION>>
<<OPTION_LINES>>

Reply with one JSON object and nothing else.
If exactly one option fits best, reply {"answer": "<its capital letter>"}.
If more than one option fits equally well, reply {"answer": "MORE_THAN_ONE"}.
If no option fits, reply {"answer": "NONE"}.
```

Without the passage:

```
Answer the multiple-choice question. The question was written about a short passage, but you are not given that passage. Use common sense only. Pick the single most likely option. You must pick one.

Question: <<QUESTION>>
<<OPTION_LINES>>

Reply with one JSON object and nothing else: {"answer": "<its capital letter>"}.
```

The text sheets for the Claude sub-agents carry the same instructions as a header. Their exact wording is in `PLAN_CONSTANTS.json` under `briefs`.

## 9. Every forbidden-word list

A question that breaks one of these rules is dropped by a program (Step 2).

| List | Words | Where it applies | How it is matched |
|---|---|---|---|
| A | cause, effect, trigger, positive, negative, vibration, rhythm, idea, mind, noetic, resonate, resonance | the question and every option | any letter case; any word that begins with the listed word |
| sign | `^` | the question and every option | the character anywhere |
| B | female, male, above, below, CAS, affinity, attracted, adverse, repelled, impression, impregnated, composed, entraining, conditioning | the question and every option | any letter case; the whole word exactly |
| C | thoughts, drawn, put off, landed, lived, learned, pieces, made of, over and over, schedule, moth, flame, stomach, ten-foot, chord, resonated, groove, muscle, popped, clicked | the question sentence only | any letter case; the whole word or phrase exactly |
| never allowed | all of the above, none of the above | the question and every option | any letter case; anywhere |

- List A is the passage writer's own list, `tools/write_verdict_passages.py` line 19. The program compares the two and stops if they differ.
- List B is the Noetic names that list A does not already hold, the letters CAS, and the special words of the canon lines.
- List C has two parts. Its first ten entries are the relation phrases of the ORD-INFORMED brief. Its last ten entries are distinctive words of the canonical sayings, added by amendment A13: moth, flame, stomach, ten-foot, chord, resonated, groove, muscle, popped, clicked. Options are built from passage things and may hold these everyday words. The question sentence may not. So a question can not simply repeat a saying that the ROLE note prints. The word `resonated` is also caught by list A.
- The question writer is told the whole of list C in its brief (section 8.1). So it now also reads those ten words. They are everyday words. None is a Noetic name. The wording of the brief did not change.
- The special words of the canon lines stay barred as before (lists A and B). Amendment A13 changed neither list.

The answer-leak screen (Step 7) has its own three words: answer, option, correct.

## 10. The eight steps for making and checking questions and keys

Everything here happens before model B runs once. It costs no AWS money. Its DeepSeek calls cost money, under the cap of section 19.2.

**Rule above all.** Nobody who has seen a label, a role note, the labeling guide or any other note writes or edits a question, a key or an ordinary note. The operator (Claude Code) can open every file, so it only runs programs. Every removal comes from a program rule and is logged with its reason. This is custody by rule and by record. It is not custody by lock.

**Practice first.** The order is fixed:

1. The questions for the practice settings are written and checked first (Steps 1 to 6). The program prints how many questions survive each filter. The reserve rule is applied (section 12.1). Then the practice set is fixed (seal steps 3A and 3B).
2. Step 7 is then run on the practice set alone. The practice ordinary notes are written and support-checked. The answer-leak screen is run on the practice set in report-only mode: it prints its counts and writes no file.
3. The numbers are printed: the practice passages and tasks left after the support check and after the screen, the hits per screen rule, and each note's words against its word target (both are stored in `notes_ord/ordinary_notes_practice.json`).
4. Only then is the first final question written. If the practice set is by then under the launch floor, no final question is written: do not launch; report the numbers to the owner. The final passages then stay unused.
5. No brief, no filter and no screen rule is changed because of these numbers without a new reviewed plan version.

Why points 2 to 4: Step 7 can only remove passages. Without this order its real loss rate would first be seen after every final question was written. EXPECTED cost of the order: more waiting. The practice support check needs up to 17 to 25 Gemini calls in its first round (two passages per call; at most 34 to 50 practice passages). How long that takes is NOT MEASURED, because the daily cap of the checker's model is not known. No program enforces the order of points 2 to 4. Every call log line and every file carries its time, and the reviewer checks the order from them.

### Step 1. The question writer

- **Who.** Gemini `gemini-3.5-flash-lite` (amendment A1). Gemini is a third vendor. It is not the vendor of label team A (Claude) and not the vendor of label team B (DeepSeek). That is what the outside reviewer asked for. This model was never a label team and never saw the guide. The passages were written by another model of the same vendor, `gemini-2.5-flash`. Claude does not write questions, because Claude agents get the CAS definitions in their project instructions and can not be blind.
- **Batches.** The writer works in batches of up to **4** passages per call. The passages of a set are sorted by id, shuffled with a fixed seed, and cut into groups of 4. So the order is seeded and fixed. Each passage is clearly fenced. The brief tells the writer to treat every passage on its own.
- **One model.** One model writes the practice set, the final set and the spare pass. The tool refuses any other model name. There is no fallback writer in this version.
- **Refused calls.** REAL, measured by the operator on 2026-10-05: 47 one-word calls to this model were answered with no refusal. The daily cap is not known. On an HTTP 429 reply the tool stops cleanly, keeps its checkpoint, and resumes when it is run again later.
- **Model name.** The tool stores the model name from every reply, next to the name it asked for. If the name in the replies changes while a set is written, the record shows it. No program stops for it.
- **All passages are asked.** The writer writes for ALL 293 K1 to K5 passages, not only the eligible ones. So being asked tells it nothing. REAL: 58 are in the practice settings and 235 in the final settings.
- **What it sees.** The question brief and the fenced passages. Never the guide, the definitions, a label, a note or another model's work.
- **What it returns.** For each form it judges the passage to support: the form name, the question, the right option, five wrong options in a fixed order, and one or two anchors. An anchor is an exact stretch of passage words, at most 8 words, that the question turns on. It also returns one plain-fact question with four options.
- **Spare pass.** A second run with the same brief and a different seeded batch order gives a spare question per form. A spare is used only where the first question for that form was dropped by a program check (Step 2 or Step 3). A spare never replaces a first question that passed.
- **Log.** Every call is logged: the model asked for, the model name in the reply, batch number, passage ids, prompt hash, reply hash, full prompt and raw reply.
- Settings: temperature 1.0 (the same as when the passages were written). A reply that is not a readable JSON array is asked for once more. A refused call (HTTP 429) is not counted as a try.

### Step 2. Form check by program

A role-step question is dropped if any of these is true:

- it does not have exactly six different options;
- an option is longer than 12 words, or the question is longer than 45 words;
- the options differ by more than 2 words in length;
- one option sits inside another;
- it has no anchor, or more than two; an anchor is not an exact copy of passage words; an anchor is longer than 8 words;
- it holds a forbidden word (section 9);
- its form name is not one of the twelve.

A plain-fact question goes through the same check, with four options and no anchor.

Words are counted by splitting on white space. An anchor is compared with the passage after curly quote marks are turned into straight ones and runs of white space into one space. Letter case must match.

### Step 3. Two label checks by program

This is the only place labels touch questions. The writer never learns what was kept.

**(a) Anchor check.** A role-step question is kept only if the passage is eligible, its form is open, and at least one of its anchors matches an agreed entry of a Noetic its form needs. "Matches" is the looser test in `tools/verdict.py`: the two texts share at least half the content words of the shorter one. The anchor is compared with either team's quote for that entry and, where the entry has a related thing, with either team's quote for the related thing.

**(b) Option check.** A role-step question is set aside when any of its six options matches, by the same looser test, an entry of the needed Noetics that only one team gave. For `^4` and `^7` the option is also compared with that entry's related thing. This removes questions where the role note is known to be short on the very point asked. For the two PULL-PUSH forms the needed Noetics here are both `^2` and `^3`. For the two BRING forms they are `^8` and `^9`.

Both checks are counted and logged by reason. Plain-fact questions have no label check.

After Steps 2 and 3 there is one candidate per passage and form: the first-pass question if it passed, else the spare if the first was dropped and the spare passed.

### Step 4. Key check by two blind solvers from two families

- **Solver 1.** DeepSeek, asked for as `deepseek-chat`, temperature 0, one item per fresh call, no memory. The tool stores the model name from every reply.
- **Solver 2.** A Claude Sonnet sub-agent that is given text only and has no file access. Its model id is pinned: `claude-sonnet-5-5` (amendment A3). By the operator's statement that is the model the Agent tool's `sonnet` alias names. The operator records the model name from every sub-agent transcript. The tool writes a plain text sheet of items with neutral ids, no key, no label and no note (export step). The sub-agent's reply sheet is read back by the tool, together with that model name (import step).
- **A limit of solver 2, stated plainly.** A Claude sub-agent carries the CAS definitions in its project instructions. So it is not blind to CAS. It only picks a letter. It never writes or edits a question, a key or a note.
- Each solver sees the passage, the question and all the options in a shuffled order. Each solver gets its own shuffle.
- Each answers one letter, or "more than one fits", or "none fits".
- A question is kept only if both pick the writer's right option and neither raises a flag. An unreadable reply counts as not picked.

### Step 5. No-passage check

The same two solvers, in separate calls, get the question and options with no passage. They must pick one letter. The Claude sheet goes to a fresh sub-agent that never saw the first sheet. If both pick the right option, the question can be guessed from common sense and is dropped.

Steps 4 and 5 apply to role-step questions and to plain-fact questions.

### Step 6. Selection by program

1. **Pick.** Per passage, at most two role-step questions, by the rules in section 7.1, chosen with a seed. One plain-fact question per passage.
2. **Length backstop.** Across the role-step tasks of a set, the right option may be the single longest of its six options in at most 35% of tasks, and the single shortest in at most 35% of tasks. Seeded drops enforce both. They are counted.
3. **Reserve rule (practice set only).** If fewer than **45** practice role-step tasks or fewer than **25** practice plain-fact tasks survive, reserve settings move from final to practice one at a time, in the sealed order, until both targets are met or all 4 are used. See section 12.1. This is done before seal step 3A and before any final question is written. Three tools act on this rule: `tools/ob_write_questions.py`, `tools/ob_select.py` and `tools/ob_seal.py`. All three read the same block, `reserve`, of `select/selection_practice.json` (amendment A8).
4. **Letters.** Right letters are set by a seeded shuffle. Per set, per task family and per level, the tasks are shuffled inside each type, the types are joined in their fixed order, and the letters are dealt in turn over the whole joined list. The count does not start again at A for a new type. So each letter is right equally often, to within one task, inside every type and over the whole family. This is done last, in `tools/ob_assemble.py`, after Step 7, when everything else is frozen. So "always answer A" scores chance to within one task. The exact rule is in `PLAN_CONSTANTS.json` under `selection.letters`.

### Step 7. Ordinary notes, then the answer-leak screen

Ordinary notes are written only after the questions of that set are sealed.

- **Writer.** DeepSeek, asked for as `deepseek-chat`, temperature 0, one passage per call, no memory. That is the name label team B was asked for under. So the writer is EXPECTED to be no weaker than the source of the role notes. That the same model answers both is not proven (section 3). The tool stores the model name from every reply. The writer never sees a question, an option, a key, a label, the guide or a role note.
- **What it writes.** For every passage that carries a task: two briefs times three lengths (section 11.3). That is six notes per passage.
- **Support check.** Gemini `gemini-3.1-flash-lite` (amendment A2) says PASS or FAIL on "every sentence is supported by the passage". It works in batches of up to 12 notes per call: the six notes of two passages. Items carry neutral ids. Same checkpoint and resume as the question writer. The tool stores the model name from every reply.
- **One checker. No fallback.** There is no fallback checker any more (amendment A2). Before the outside review a Claude sub-agent was the fallback. A Claude sub-agent carries the CAS definitions in its project instructions, so it must not shape the rival notes. If Gemini refuses a call, the build waits: the same step is run again later, from its checkpoint. Nobody else judges a note. So one checker judges every note of both sets, and nobody can pick a checker after seeing verdicts. The daily cap of this model is NOT MEASURED.
- **One rewrite.** A failed note is written again once by the same blind writer, with the rewrite frame in section 8.4. The second version is checked once. If it fails too, the passage is dropped for every group and the reason is logged. The support check is the only thing that can cause a rewrite.
- **A note the writer can not produce (PROPOSED; a small fault fixed with amendment A13).** A reply that is empty, or that the service marks as cut off, is not a note. It is logged with the reason `REPLY_EMPTY` or `REPLY_CUT_OFF`. The same note is asked for once more, in a later run of the same step. If the reply for that note is empty or cut off a second time, the note is not asked for a third time. The passage is then dropped for every group, with the status `DROPPED_NOTE_NOT_WRITTEN`, and the reason is logged. This holds for a first writing and for a rewrite. A call that brought no reply at all (no answer, a refused call) is not counted. So the build never waits for ever on one note. A guard against a fault of the whole service: at most **3** passages of a set may be dropped this way. If one more would be dropped, the tool drops nothing more and stops with `STOPPED_TOO_MANY_NOTES_NOT_WRITTEN`. Then: stop and report. Many notes that do not come point to a fault of the service or of the tool, not of single notes.

Then one program screens every note of every group. A note is **hit** if it holds any of these:

- **(a)** an option letter written as a choice, such as `A.`, `(B)` or `answer: C`, outside text copied from the passage;
- **(b)** the question, word for word, or any sentence of it that has 5 or more words;
- **(c)** the full text of an option that is NOT in the passage. An option that is passage text is not tested, because the passage is in every prompt;
- **(d)** the whole word `answer`, `option` or `correct`, counted only outside passage text.

"Outside passage text" is defined like this. For a program-built note (FILLER, ROLE, MIXED, QUOTES-ONLY) only its fixed frame words are tested; the quoted passage parts are blanked first. For an ordinary note, (a) and (d) are a hit when the pattern or word appears more often in the note than in the passage. REAL: 4 eligible passages hold the whole word `correct` in their own text (`V027`, `V231`, `V335`, `V413`).

**The sayings lines are frame words (amendment A13).** The fixed frame words of a ROLE or MIXED note include its canon definition lines and its sayings lines: the word `Sayings` and the sayings text. A sayings line holds quote marks, but it is not a passage part. It is never blanked. So rules (a) to (d) test it like every other frame word. REAL, checked by a small script on 2026-10-05 on all ten table rows: no sayings line holds the whole word `answer`, `option` or `correct`, and no letter pattern of rule (a) matches a sayings line.

**What a hit does.** A hit never causes any note to be written again. The passage is dropped for every group, by the program, with the reason logged. So the answer key can never decide what the rival may say. All three lengths of both ordinary notes are screened.

**Known risk of rules (c) and (d), stated now.** The word target of an ordinary note is about 2.6 times the passage length at the median (counted by the builder of the note tool before amendment A13; **to be measured again by the tool fixer**, because the sayings lines make the ROLE note longer and so the target larger). EXPECTED with A13, not yet measured by the tool: about 3.8 times at the median. That is the plan fixer's own count on 2026-10-05: the dry role notes of that day plus the size of the sayings lines. Such a note restates the things of the passage. EXPECTED, NOT MEASURED: it can hold a short option, or one of the three words, by chance. Each such hit drops a passage that held no leak. The rules stay as written, because a looser rule would weaken the screen. The report-only run on the practice set ("Practice first", point 2) shows the real hit rate before any final question is written.

**Known risk of amendment A13, stated now.** The sayings lines make the ROLE and MIXED notes longer. The ordinary notes are sized to the ROLE note by the unchanged rule of section 11.3, so they grow too. EXPECTED, NOT MEASURED: a longer ordinary note about the same short passage fails the support check more often. It also holds a short option, or one of the three screen words, by chance more often. Each such case drops a passage. The practice numbers ("Practice first", points 2 and 3) show the real rates before any final question is written. One more case: an option whose whole text stands inside a sayings line of the note, and not in the passage, is a rule (c) hit like any other. It drops the passage. And one risk for the job itself: if the writer writes far fewer words than it is asked for, the ordinary notes come out shorter than the ROLE note, their padding grows, and the padding rule of section 11.3 (10%) can stop the job in its self-test. The practice numbers print each note's words against its word target, so this is seen before any final question is written.

### Step 8. One review round

An outside reviewer (the DeepSeek reasoning model, as before) reads the plan, the programs, all practice items and a seeded 10% sample of final items. It gets a checklist:

- the eight fixed rules in section 15.5;
- the question brief and the ordinary-notes brief side by side;
- throwaway options;
- the runner's file rules (section 19.4).

Reviewers do not edit. A BLOCKER or MAJOR finding holds the launch until a new plan version is written and sealed. There is one round.

### Launch floor

Do not launch with fewer than **100** final role-step tasks, fewer than **100** final plain-fact tasks, fewer than **36** practice role-step tasks or fewer than **20** practice plain-fact tasks.

The reserve targets of Step 6 (45 and 25) are not launch floors. They only decide how many reserve settings move.

### Owner checkpoint

After the full build the owner gets the real counts and the detection table for those counts. The owner settles the size question then (section 22, question 12).

Honest limit: a key that the writer and two language models agree on is a consistent key. It is not proof of a right key, most of all for "most likely" questions.

## 11. Order of seals, groups and the prompt

### 11.1 Order of seals

A seal is a hash written to `optionb/SEAL_OPTIONB.jsonl` before the next step starts. `tools/ob_seal.py` writes it. It refuses a step out of order. It refuses a step when an earlier sealed file has changed.

| Step | What is sealed |
|---|---|
| 1 | **The plan first:** this plan, `PLAN_CONSTANTS.json`, `FILE_FORMATS.md`, the six source files of section 3 with their paths, sizes and hashes (the sixth is the file that holds the canonical sayings; amendment A13), the 104-passage exclusion list, the eligible list with open forms, the 8 practice settings and the 4 reserve settings in order. **Also the eleven laptop tools** `tools/ob_*.py` that write, filter and select the questions and notes. |
| 2 | The role notes (ROLE, MIXED, QUOTES-ONLY). |
| 3A | Practice questions and their keys as text (which option is right). Written only when the reserve rule is finished. |
| 3B | The practice set is fixed (how many settings are practice). Written only when both practice launch floors are met. |
| 3C | Final questions and their keys as text. |
| 4 | The ordinary notes, all three lengths, every version, and the support-check results. |
| 5 | The answer-leak screen log, the removal log, the assembled prompt parts, and the lettered keys. |
| 6 | The programs: scorer, runner, gate program, analysis program, and the scorer's known examples. The reviewer checks them against the sealed plan. |
| 7 | The pre-check receipt (section 19.1), and the owner's signed table of status words (section 21). |

Only then may B run. The job's guest refuses a package that does not match the seal.

**Step 7 takes only a passed pre-check on the sealed package (amendment A8).** `tools/ob_seal.py` reads the receipt of the pre-check job. It refuses step 7 unless the receipt says `precheck_kind` is `SEALED_PACKAGE` and the status is `PRECHECK_COMPLETE_SELFTEST_PASS`. It also refuses unless the `source.zip` it is given holds the seal file up to its last program line. So a rehearsal, or a test on made-up data, can never be sealed as step 7. The exact checks are in `FILE_FORMATS.md`, section 15.1.

**The tools are sealed too.** The eleven tools hold many small choices. So their hashes go into seal step 1. Every tool that runs after seal step 1 already checks, before it does anything, that no sealed file has changed. From seal step 1 on that check covers the tools themselves. A tool that was changed stops itself, every other tool and every later seal step. So a filter can not differ between the practice set and the final set without a record.

**When the practice set is final.** Seal step 3A is written only when the reserve rule is finished: both reserve targets are met, or all 4 reserve settings are used. Before that, the next reserve setting is moved and the practice tools run again. After step 3A no practice question file is written again. Seal step 3B is written only when the practice set meets both launch floors (36 role-step and 20 plain-fact tasks). If it does not: do not launch; report.

**Repair lines (narrowed by amendment A5).** Two kinds of line may be added to the seal file besides the nine steps. Both are PROPOSED. Each has a window. Outside its window `tools/ob_seal.py` refuses the line with `REPAIR_OUTSIDE_ITS_WINDOW`. Their exact form is in `FILE_FORMATS.md`, section 15.

| Line | Window: allowed only | For which fault | What may change |
|---|---|---|---|
| `TR_TOOLS_REPAIRED` | After seal step 1 and while no final question exists. That is: while the practice set is still being processed. The window closes when the first file of the final set is written. | A tool stops, crashes or refuses for a fault in its own code, or a reviewer shows that its code does not do what the sealed plan says. | Only `tools/ob_*.py`. |
| `6R_PROGRAMS_REPAIRED` | After a failed pre-check job on the sealed package (section 19.1) and before seal step 7. So it comes before any call to model B. At most **2** such lines. | The fault sits in a job program. | Only the five files of seal step 6. |

**A plan-only run closes the tool window too (a small fault fixed with amendment A13).** A run of the final question writer with `--max-calls 0` makes no call and writes no question. But it already writes two files of the final set. From then on a tool repair is refused. So the final question writer is not run, not even with `--max-calls 0`, before the practice set is fully done ("Practice first", section 10).

**After the window.** A fault in a tool after the first final question exists means: stop, report, and write a new reviewed plan version. The same holds for a fault in a job program after seal step 7. There is no repair line for either.

Rules for every repair:

1. A sealed file of steps 1 to 5 is never edited and never built again.
2. A repair changes program code only, and only to bring it in line with the sealed plan. Neither kind of repair may change the plan, the constants, a brief, a threshold, a key, a task or a note. It never changes a rule, a number or a wording.
3. A reviewer who did not write the change reads the diff against the sealed plan and writes a review record. Each repair needs its own review record. Without the verdict `REPAIR_ALLOWED` no line is added.
4. The old copy of each changed file, the diff and the review record are kept and hashed in the line. The line holds the old and the new hash. From then on the new hash is the one in force.
5. A tool repair is refused when the fault could have changed a file that is already sealed. Then: no repair, no launch, a new plan version. This is the guard against a filter that works one way on practice and another way on final.
6. After a tool repair the tool goes on from its checkpoint. A logged reply of an outside model is never asked for again and never deleted. Nobody edits a derived file by hand. A derived file that the fault could have changed, and that is not sealed yet, is deleted and derived again by the repaired tool, from the same logged replies. Each deletion is listed in the line.

Who sees what:

| Who | Sees | Never sees |
|---|---|---|
| Question writer | fenced passages, the question brief | labels, notes, keys, the guide |
| Key solvers | passage, question, options | the key, labels, notes |
| Ordinary-note writer | one passage, its brief | questions, options, keys, labels, the guide, role notes |
| Note checker | passage and note | everything else |

All outside calls are stateless and logged with hashes. Every tool that calls an outside service stores, for every call, the model name the service put in its reply (amendment A9). For the Claude sub-agents the operator records the model name from each transcript.

### 11.2 The guidance groups

The ROLE-PLAIN group is **struck** (operator decision D1). The owner has not approved its plain sentence frames, and the canon may not be paraphrased. There is no code path, no prompt part and no call for it.

Seven must-run groups, in this order:

| # | Group | What B gets | How it is made | Why it is there |
|---|---|---|---|---|
| 1 | NONE | Passage, question, options, closing instruction. No Notes block at all. | The frame with the Notes block removed. | The baseline. It defines which tasks B "already gets right". |
| 2 | FILLER | The padding line, then the sentence `No notes are provided for this passage.` | By the program. | Answers "it was just more words". It is the yardstick for answers that flip for no reason. |
| 3 | ROLE | The padding line, then the role note of section 6, with the canon definition lines word for word (operator decision D2). Right after each definition line comes that Noetic's canonical sayings line (amendment A13). | By the program, from agreed entries only. Sealed before any question exists. | The one tested group. This is the owner's option B. |
| 4 | MIXED | The ROLE text with every role tag swapped by one fixed table: `^2` with `^3`, `^5` with `^6`, `^8` with `^9`, `^4` with `^7`. `^1` stays. Each swapped tag brings its own canon line and its own sayings line (amendment A13). Labels, Minds, related things and supporting quotes stay where they were. | By the program, mechanically. | The directive's "mixed-up CAS guidance". If ROLE does not beat MIXED, the gain did not come from knowing which thing occupies which role. |
| 5 | ORD-INFORMED | The padding line, then free plain notes written from the brief in 8.2. | DeepSeek, blind (Step 7). | The strongest fair rival. Answers "a strong model summarised the passage". |
| 6 | ORD-FREE | The padding line, then free plain notes written from the brief in 8.3. | Same writer, same checker, same blindness. | "Ordinary help" in the everyday sense. ROLE must beat BOTH rivals. Nobody picks the rival after seeing results. |
| 7 | QUOTES-ONLY | The padding line, then the same labels and supporting quotes as ROLE. No Noetic, no Mind, no related thing, no definition line, no sayings line. Role-step tasks only. | By the program, from the same agreed entries. | Separates the role names from the pointing. Right tags (ROLE), no tags (QUOTES-ONLY), wrong tags (MIXED). |

Two more conditions:

| Condition | What B gets | Where | Why |
|---|---|---|---|
| ANSWER-GIVEN | The padding line, then `The right answer to the question is <letter>.` | Practice role-step tasks only. Never a final task. | Checks that B reads the Notes block at all (Gate 5). |
| NO-PASSAGE | The question and options. No passage. No notes. | Practice role-step tasks as a gate (Gate 6). Final role-step tasks last, reported only. | Shows how much B can guess with no text. |

A plain-fact task runs in groups 1 to 6. A role-step task runs in all seven.

QUOTES-ONLY is derived from the role reading. It is never counted as ordinary help.

Amendment A13 changed two groups only: ROLE and MIXED. The texts of QUOTES-ONLY and FILLER, the questions and every brief are unchanged. The ordinary notes are written from the same two briefs. They are only sized to the longer ROLE note, by the unchanged rule of section 11.3.

### 11.3 How length is matched

For each passage, the Notes block has the same number of tokens in every group. A token is one of the word-pieces the model reads. Tokens are counted with B's own tokenizer, inside the job, with no model call.

1. **Padding line first.** Every group with a Notes block carries the padding line as the FIRST line of the block, ROLE and MIXED included. The shortest padding line is `[Padding: neutral]`. A longer one repeats the word: `[Padding: neutral neutral neutral]`. No group has padding next to the question.
2. **Sizing the ordinary notes.** The size count of a text is its number of words plus its number of punctuation marks. Role notes are full of quote marks and signs, so matching by words alone would leave the ordinary notes short in tokens. The word target is

   `N = (percent × C_role × W_p + 50 × M_p) // (100 × M_p)`

   where `C_role` is the size count of the passage's ROLE note, `W_p` is the number of words in the passage, and `M_p` is the size count of the passage. `//` is whole-number division. By amendment A13 the ROLE note also holds the sayings lines, so `C_role` is larger than before. The rule itself did not change.
3. **Three lengths.** The ordinary writer writes three lengths per passage and brief: 90%, 100% and 110%. Each must pass the support check.
4. **Picking a length.** Inside the job, for each passage and each ordinary group, the program takes the length whose token count is nearest to the ROLE note's. On a tie: 100% first, then 90%, then 110%. This choice looks at length only.
5. **The target.** The target for a passage is the largest block among its groups, built with the shortest padding line. Every block is padded up to it at the start. One token of difference is allowed and recorded. A larger difference stops the job (`GATE_STOP_SELFTEST`).
6. **Fixed rule, checked in the self-test before any model call.** The padding share of a block is the tokens of its padding line divided by the tokens of the block. If the average padding share is above **10%** in ROLE, MIXED, ORD-INFORMED or ORD-FREE, the job stops with `GATE_STOP_PADDING`. The average is worked out for the practice passages and for the final passages apart. Either one above 10% stops the job. No task is spent. Average padding per group is always reported.

NONE is shorter by design. FILLER covers that.

The laptop does not run the tokenizer. That is why three lengths are written and the choice is made in the job. The guard is untested. The pre-check job (section 19.1) tests it before the GPU attempt.

### 11.4 The exact prompt frame

One user message goes through the model's own chat template. The template's default system text is left as it is, the same for every group.

Frame for every group that has a Notes block:

```
Read the passage and answer the question.

Passage:
<<PASSAGE>>

Notes:
<<PADDING_LINE>>
<<NOTES>>

Question: <<QUESTION>>
<<OPTION_LINES>>

<<CLOSING>>
```

Frame for group NONE (the whole Notes block is absent):

```
Read the passage and answer the question.

Passage:
<<PASSAGE>>

Question: <<QUESTION>>
<<OPTION_LINES>>

<<CLOSING>>
```

Frame for NO-PASSAGE:

```
Answer the question.

Question: <<QUESTION>>
<<OPTION_LINES>>

<<CLOSING>>
```

Each option line is `<letter>. <option text>`, one per line, in letter order. With six options the letters run to F.

### 11.5 The three closing wordings, word for word

The closing instruction names exactly the letters shown for that task. `<<LETTERS_OR>>` becomes `A, B, C or D` or `A, B, C, D, E or F`. `<<LETTERS_COMMA>>` becomes `A, B, C, D` or `A, B, C, D, E, F`.

Wording 1:

```
Return exactly one JSON object with key answer and no other text. The value of answer is one capital letter: <<LETTERS_OR>>.
```

Wording 2:

```
Reply with one JSON object only. Its single key is "answer". Its value is the capital letter of your choice (<<LETTERS_OR>>) and nothing more. No option text, no explanation, no code fence.
```

Wording 3:

```
Output format: {"answer": "<letter>"} where <letter> is exactly one of <<LETTERS_COMMA>>. Output the JSON object only.
```

None of them shows a sample letter as an answer. Practice picks one (Gate 1). A tie goes to the first listed.

### 11.6 Decoding settings

- Always the single most likely next token (greedy). No sampling.
- Repetition penalty set to 1.0 explicitly.
- At most 64 new tokens. Stop at the end token.
- One prompt at a time. One call per task and group. No retry.
- 32-bit floats. One A10G GPU. The runner refuses a CPU with `GPU_REQUIRED`.
- `cut_off` is true when B wrote 64 new tokens with no end token.
- The same closing instruction, decoding, 64-token cap and scorer for every group. The scorer is never told the group.

## 12. Practice, gates and the launch floor

### 12.1 The practice split

Practice and final are split by whole settings, before any final question is written. A practice task is never a final task.

**Rule.** `random.Random(20261005).sample(sorted setting names, 12)`. Seed **20261005**. REAL, reproduced on 2026-10-05:

The 8 practice settings, in order:

1. a locksmith's van
2. a tailor's shop
3. a mountain hut
4. a quarry
5. a dairy at milking time
6. a chess club
7. a swimming pool
8. a beekeeper's yard

The 4 reserve settings, in order:

1. a cheese cellar
2. a boxing gym
3. a post office sorting room
4. a taxi rank at night

Every other setting is final.

REAL counts by number of practice settings:

| Practice settings | Practice passages | Final passages | Role-step ceiling, practice | Role-step ceiling, final |
|---:|---:|---:|---:|---:|
| 8 | 34 | 156 | 66 | 300 |
| 9 | 40 | 150 | 77 | 289 |
| 10 | 45 | 145 | 87 | 279 |
| 11 | 47 | 143 | 91 | 275 |
| 12 | 50 | 140 | 96 | 270 |

With 8 practice settings, REAL passages per type: practice BRING 5, PULL-PUSH 11, LAND 8, FORMED 8, PARTS 7, HABIT 4; final BRING 30, PULL-PUSH 43, LAND 35, FORMED 37, PARTS 29, HABIT 29.

**Reserve rule.** It is counted after Step 6 on the practice set. If fewer than **45** practice role-step tasks or fewer than **25** practice plain-fact tasks survive, the next reserve setting moves from final to practice. Repeat until both targets are met or all 4 are used. No setting is moved once both targets are met. This is done before seal step 3A and before any final question is written.

The two targets are PROPOSED. They are above the launch floor (36 and 20) on purpose. Step 7 comes after the reserve rule and can only remove passages: a second support-check failure or an answer-leak hit drops the whole passage, and one practice passage carries up to two role-step tasks. A target equal to the floor would leave no room for that. The launch floor itself does not change.

If the practice set is under the launch floor with all 12 settings, do not launch; report the survival numbers to the owner. Missing a reserve target with all 12 settings is not a stop. Only the launch floor decides. No brief and no filter is changed without a new reviewed plan version.

Cost of the higher targets, REAL from the table above: each reserve setting that moves takes 2 to 6 passages from the final set. With all 4 moved the final set has 140 passages and a role-step ceiling of 270, not 156 and 300.

How many tasks survive the filters is NOT MEASURED.

### 12.2 One job, gated

Practice is phase 1 of the same AWS job. Its gates are a program with fixed rules. The final phase starts only if every gate passes. No final prompt is sent to the model until every practice gate has passed. The cost of this choice: no person reads B's raw practice answers before final tasks are used.

Practice may never pick or drop a single final task. It may not remove a question type.

Two words used by the gates:

- **Clean reply:** a reply scored CORRECT or WRONG whose value is one of the letters shown for that task.
- **Chance:** 25% with four options. 16.67% with six.

Practice calls run in three steps. P1: group NONE at level 1, on every practice task, under each of the three closing wordings. P2: group NONE at level 2, on role-step tasks, under the chosen wording. P3: every other condition at the chosen level. P3 does not start if Gate 2 or Gate 3 already fails.

### 12.3 Every gate, with its number and stop code

The gates are checked in order. The first one that fails gives the stop code.

| Gate | What is checked | Number | Stop code |
|---|---|---|---|
| 0, self-test | No model loaded. See below. | padding at most 10%; score time times 5 at most 240 s | `GATE_STOP_SELFTEST`, `GATE_STOP_PADDING` |
| 1, closing wording | B alone answers every practice task at level 1 under each wording. The wording with the most clean replies is used. A tie goes to the first listed. | — | none |
| 2, difficulty | B alone on practice role-step tasks. Level 1 must be in **35% to 70%**. Level 2 must be in **30% to 70%**. If both are in, the one nearer 50% is taken; a tie goes to level 1. If one is in, that one. If none, stop. | lower edge = the larger of 30% and chance plus 10 points | `GATE_STOP_DIFFICULTY` |
| 3, no-harm base | B alone must be right on at least **60%** of practice plain-fact tasks. | 60% | `GATE_STOP_NO_HARM_BASE` |
| 4, format | At the chosen level, in each of the seven must-run groups, on role-step tasks and on plain-fact tasks counted apart: at least **75%** of practice replies are clean, and FORMAT_FAIL plus CUT_OFF is at most **25%**. Both task families must clear both numbers. (QUOTES-ONLY has role-step tasks only.) NO-PASSAGE under the bar is dropped from the final phase; it does not stop the job. | 75% and 25%, per family | `GATE_STOP_FORMAT` |
| 5, notes are read | Among ANSWER-GIVEN replies that are clean, at least **90%** are right. There must be at least **20** such replies. | 90%, 20 | `GATE_STOP_NOTES_NOT_READ` |
| 6, the passage is needed | Stop only if B with no passage is above chance plus **15** points at the chosen level (above 40% with four options, above 31.67% with six). The difference from B alone is printed. | chance + 15 | `GATE_STOP_GUESSABLE` |
| 7, time | From the measured seconds per call, the seven must-run groups on all final tasks must fit before the work cutoff (minute 135) with a **25%** margin and **300** seconds to spare. NO-PASSAGE is added only if it also fits. Decided once, before the first final call. | 25%, 300 s | `GATE_STOP_TIME` |

**Gate 0 in full.**

- The scorer gives the hand-decided category on every known example (section 17).
- Package hashes match the seal. Every task has every group it should have.
- The GPU is present. The runner refuses a CPU with `GPU_REQUIRED`. (In the pre-check job this one check is skipped and recorded as not checked.)
- The tokenizer loads. The padding plan and the hash of every practice and final prompt are computed and saved. No final prompt is sent to the model.
- The padding rule of section 11.3 is applied.
- The planned number of calls is at most the call cap of 5,000.
- The gate program and the analysis program are run from start to end on five made-up answer sets (section 17.3). Each must print the code worked out by hand in this plan.
- The seconds taken are recorded. The score stage's time limit is 5 times the slowest analysis run, and at least 120 seconds. If 5 times the measured time is above 240 seconds, stop.
- The two hashes the pre-check printed must come out the same (section 19.1).
- Then the guest marks setup complete, before the first model call.

**Gate 4 counts the two task families apart.** Validity rule V3 does the same on the final tasks (section 15.1). If Gate 4 counted them together, a group could pass practice with a format problem on role-step tasks only, and the same problem would then void the run after the final tasks were spent. Cost, stated now: counting apart raises the chance of a format stop on a small practice set. With 20 plain-fact tasks, 6 replies that are not clean in one group stop the job. Such a stop spends no final task.

**Printed by the gate step, with no rule attached:** the share of practice role-step tasks on which ROLE and ORD-INFORMED give different results; the gap in clean replies between ROLE and each ordinary group.

**After a stop.** The final tasks were never sent to the model. They stay sealed and usable by a later reviewed job. Practice results are never reported as a finding about roles.

ASSUMED (a reviewer's simulation, 20,000 runs, not rerun here): a sound run still stops at a gate about 1 time in 5 to 8. With 36 to 50 practice tasks, B's measured accuracy has a 95% range of about plus or minus 14 to 16 points. That simulation counted Gate 4 over both task families together. With the families counted apart the chance of a stop is somewhat higher. How much is NOT MEASURED.

## 13. The test for "X beats Y"

The passage, not the task, is the unit. Two questions on one passage are not independent.

**The number compared.** For each group: the share of CORRECT answers over the final role-step tasks at the chosen level.

**The test.** For each final passage take `d` = (tasks CORRECT under X) minus (tasks CORRECT under Y). If the notes made no difference, each passage's `d` is as likely to be plus as minus. The program flips the signs at random **100,000** times (seed **20261005**) and counts how often the flipped sum is at least as large as the real one. That share is `p`. "X beats Y" means `p` is at most **0.05**, one-sided: at most 5,000 of the 100,000 flips.

**The range.** The measured difference and a 95% range are always printed beside it. The range comes from resampling the passages **10,000** times with the same seed.

**Two-sided form.** Where a rule says "two-sided", the program counts flips whose sum is at least as far from zero as the real one.

**The random draws, exactly.** The program uses Python's own `random` module. It uses no numpy. A fresh `random.Random(seed)` is made for every test and for every range.

- One flip: `r = rng.getrandbits(n)`, where `n` is the number of passages. The passages are sorted by passage id. Bit `j` of `r`, counted from 0, belongs to passage `j`. A set bit flips the sign of that passage's `d`. Sums are whole numbers.
- One resample: `rng.choices(passages, k=n)`, with the passages in passage-id order. The resampled difference is `100 × sum(d) / sum(tasks)`, in points, kept as a whole number of millionths of a point, rounded down.
- The 95% range is the sorted values at index 250 and index 9749 of the 10,000.
- The standard error is the standard deviation of the 10,000 resampled values. That is the bootstrap standard error. It is used as it stands. It is not divided by the number of resamples, by the number of passages, or by any other count (amendment A4).
- The standard deviation is taken in its plain form: the square root of the average squared distance of the 10,000 values from their average.

This is the one procedure. `PLAN_CONSTANTS.json` holds the same text under `tests`, and `optionb/job/analysis_b1.py` runs it. A recount uses the same Python version as the job.

No correction for several tests is needed for the pass code, because every one of the tests must hold.

Point rules use whole-number arithmetic. Example: "at least 5 points above" means `100 × (right under ROLE − right under rival) ≥ 5 × tasks`.

## 14. Scoring, in short

Scorer version **0.1.1** (section 17). Five categories: CORRECT, WRONG, TYPE_MISMATCH, FORMAT_FAIL, CUT_OFF. Primary score: CORRECT = 1, everything else = 0.

- **Clean reply:** scored CORRECT or WRONG, and its value is one of the letters shown.
- **Not clean:** everything else. That is FORMAT_FAIL, CUT_OFF, TYPE_MISMATCH, and any WRONG reply whose value is not an allowed letter, such as `"C. the smell of damp rope"`.
- **Format floor:** a group with more than 25% FORMAT_FAIL plus CUT_OFF on final tasks. Role-step tasks and plain-fact tasks are counted apart.

## 15. Validity, readability, conditions and outcome codes

All of this is fixed now and is in the first seal. A program applies it and prints exactly one outcome code.

### 15.1 Validity

If one fails, the outcome is `INVALID_RUN` with the reason. No claim, no retry on these tasks, no dropped task, no changed threshold.

- **V1.** Every planned final call in the seven must-run groups has an output.
- **V2.** Model and tokenizer file hashes are the same at the start and after the last model call. The receipt of the second hash must exist; if it is missing the code is `INVALID_RUN`. The package matches the seal. Every prompt hash matches the dry build.
- **V3.** None of the seven must-run groups is at format floor, on role-step tasks and on plain-fact tasks counted apart.

### 15.2 Readability

Checked next, in this order. If one fails, that code is the outcome and no gain or loss is read.

- **R1, `UNINFORMATIVE_DIFFICULTY`.** B alone on the final role-step tasks is above 85%, or below chance plus 5 points.
- **R2, `FORMAT_GAP_NOT_READABLE`.** On final role-step tasks the not-clean share differs between ROLE and ORD-INFORMED, or between ROLE and ORD-FREE, by more than 5 points in either direction, AND the same passage-level test, two-sided, gives `p` at most 0.05.
- **R3, `PADDING_HURTS_B_NOT_READABLE`.** FILLER is 5 or more points below NONE on final role-step tasks, AND the test "NONE beats FILLER" holds.

R2 and R3 stay as the final design wrote them: 5 points AND the test (operator decision D9). Reason, ASSUMED inputs, 20,000 simulated runs by the design's author: a plain 5-point line would void a sound run 10% to 49% of the time, and a voided run spends the final tasks.

### 15.3 Conditions

- **C1.** ROLE beats NONE, and ROLE beats FILLER.
- **C2.** ROLE beats ORD-INFORMED, and ROLE beats ORD-FREE, and ROLE's share is at least 5 points above the better of the two. If the two rivals tie, ORD-INFORMED is the better one.
- **C3.** ROLE beats MIXED.
- **C4.** The no-harm check is HELD (section 16).
- **C5.** ROLE beats QUOTES-ONLY.

### 15.4 Outcome codes, in checking order

These are study codes. They are not spec-sheet status words. Which status word belongs to which code is fixed in one table that the owner signs before the GPU launch (section 21, "Spec sheet"). Nobody picks the word after the result is seen.

| # | Code | When |
|---:|---|---|
| 1 | `INVALID_RUN` | V1, V2 or V3 fails. |
| 2 | `UNINFORMATIVE_DIFFICULTY` | R1. |
| 3 | `FORMAT_GAP_NOT_READABLE` | R2. |
| 4 | `PADDING_HURTS_B_NOT_READABLE` | R3. |
| 5 | `NO_ROLE_HELP_SHOWN` | C1 does not hold. |
| 6 | `HELP_NOT_TIED_TO_CORRECT_ROLES` | C1 holds, C3 does not. |
| 7 | `ROLE_HELP_NOT_ABOVE_ORDINARY_HELP` | C1 and C3 hold, C2 does not. |
| 8 | `HELPS_BUT_BREAKS_RIGHT_ANSWERS` | C1, C2, C3 hold, no-harm is NOT_HELD. Under the directive this is a failure of the stage. |
| 9 | `BEATS_ORDINARY_HELP_NO_HARM_NOT_MEASURED` | C1, C2, C3 hold, no-harm is NOT_MEASURABLE. This is not a pass. |
| 10 | `POINTING_BEATS_ORDINARY_HELP_ROLE_NAMES_NOT_SHOWN` | C1, C2, C3 and C4 hold, C5 does not. This is not the pass code. |
| 11 | `ROLE_HELP_BEATS_STRONGEST_ORDINARY_HELP` | C1 to C5 all hold. **This is the only pass.** |

There are 11 outcome codes, numbered 1 to 11. No number is used twice (amendment A7).

**Exact report sentences.**

- For code 7: "Role information helped B. An advantage over a strong model's ordinary notes was not shown. A gain under about X points could have been missed."
- For code 10: "The checked label-and-quote notes beat ordinary help. A gain from the role names beyond pointing at the words was not shown."
- For the no-harm range: "A loss of up to X points cannot be ruled out."

**The number X in the code 7 sentence.** The program computes it from the final data: the larger of (2.485 times the standard error) and (5 points plus 0.84 times that standard error), rounded up to a whole point. The standard error here is the bootstrap standard error of the ROLE-minus-better-rival difference. That is the standard deviation of the 10,000 resampled ROLE-minus-better-rival differences, in points, as section 13 defines it. Nothing divides it by a count (amendment A4). X is printed in every run, not only with code 7.

**The `_EXPLORATORY` tier rule.**

- At least **200** final role-step tasks on at least **120** final passages: the outcome code is read as it stands.
- 100 to 199 tasks, or fewer than 120 passages: the same rules are applied and the code ends in `_EXPLORATORY`. **This is the tier to expect.**
- Fewer than 100 tasks: do not launch.
- The ending is added to codes 5 to 11, the seven codes that read a result about roles. Codes 1 to 4 say that nothing was read, and never carry it.
- A final passage here means a passage that carries at least one final role-step task.

### 15.5 Eight fixed rules, given to the plan reviewer as a checklist

- (a) The three closing wordings are written out in section 11.5.
- (b) Level 1 shows the right option and the first three wrong options in the writer's order. The swapped-relationship option is first where the form has one.
- (c) Plain-fact tasks always show four options, at every level.
- (d) The anchor is matched against either team's quote for the entry, or for its related thing, by the looser test.
- (e) The format floor counts role-step and plain-fact tasks apart; both must clear. Gate 4 counts them apart in the same way on the practice tasks.
- (f) Ties: the level nearer 50% goes to level 1 on a tie; the better rival is ORD-INFORMED on a tie.
- (g) Struck with the ROLE-PLAIN group (D1). No ROLE-PLAIN result is printed, because none exists.
- (h) The scorer version is 0.1.1.

### 15.6 Stopping rules

The job stops at a practice gate, at the call cap (5,000), at the work cutoff, or on any failed check. A stop is reported as a stop. Once the final phase starts there is no interim look and no early stop. After final outputs exist: no dropped case, no changed threshold, no new scoring rule. A new attempt after a failure needs new cases and a newly reviewed version.

## 16. The no-harm check

**The question.** Do the role notes make B lose answers it gets right without them?

Two measures on final tasks. BOTH must hold for `HELD`.

- **H1, plain-fact tasks.** Loss = share right with no notes minus share right under ROLE. Rule: the measured loss is at most **5** points.
- **H2, keeping what was right.** Take every final task, both families, that B got CORRECT with no notes. Count the share still CORRECT under each group. Rule: the share kept under ROLE is not more than **5** points below the share kept under FILLER. FILLER is the only yardstick.

Why FILLER: some of B's right answers are lucky. Any change to the prompt flips some of them. FILLER changes the prompt and adds no information. The ordinary rival is not a yardstick here, because its writer is told to include plain details; that is the rival helping, not the role notes harming.

**`NOT_MEASURABLE`.** Fewer than **100** final plain-fact tasks, or fewer than **80** final tasks CORRECT with no notes. Then the pass code is not available.

**Always printed.** The 95% range of each difference. The upper end of the one-sided 95% range of the H1 loss, inside the fixed sentence. The same two measures for MIXED, QUOTES-ONLY and both ordinary rivals. (QUOTES-ONLY has no plain-fact tasks; its H2 is worked out on role-step tasks only and labeled so.) The full two-by-two table against no notes for every group.

**What `HELD` does and does not mean.** ASSUMED inputs, 4,000 simulated runs per line by the design's author: `HELD` comes out 90% of the time when the true loss is 0; 47% to 52% when it is 5 points; 10% to 12% when it is 10 points; 1% when it is 15 points. So it rules out a large loss. It does not rule out a loss of 5 or 10 points. A harmless note fails about 1 time in 10.

Not covered: what a "nothing marked here" note does to B. K8 and K9 passages are not used.

## 17. Scoring, version 0.1.1

### 17.1 The rules

The written rules are `03_SCORER_RULES_v0_1.md`. The source is `tools/scorer_v0_1.py`. Version 0.1.1 is the same rules with one defect fixed (operator decision D10).

**The defect (REAL, read in the source).** Rule 5 says the reply must be one object with exactly one key. The source reads the text with `json.loads`, which silently keeps the last of two repeated keys. So `{"answer": "A", "answer": "B"}` is read as `"B"` and accepted. A hedged double answer could be marked CORRECT.

**The fix.** In version 0.1.1 a reply whose object repeats a key is `FORMAT_FAIL`. Nothing else changes. The new file is `optionb/job/scorer_v0_1_1.py`. The seal names 0.1.1 and its hash. The seal never names two versions.

By the rules as written, `"c"`, `"C."`, `"(C)"` and `"C. the smell of damp rope"` are WRONG. That is strict, and it is the same for every group.

### 17.2 Known examples

The 30 examples in `scorer_examples_v0_1.json` stay, with the same expected categories. Ten are added, decided by hand from the rules as written. The task answer is `"B"` in each.

| # | Reply | Category |
|---:|---|---|
| 1 | `{"answer": "B"}` | CORRECT |
| 2 | `{"answer": "b"}` | WRONG |
| 3 | `{"answer": "B."}` | WRONG |
| 4 | `{"answer": "B. the side door"}` | WRONG |
| 5 | `{"answer": 2}` | TYPE_MISMATCH |
| 6 | `{"answer": ["B"]}` | TYPE_MISMATCH |
| 7 | `{"answer": "B"}` inside one code fence on its own lines | CORRECT |
| 8 | a fence on one line: three backticks, `{"answer": "B"}`, three backticks | FORMAT_FAIL |
| 9 | `{"answer": "A", "answer": "B"}` | FORMAT_FAIL |
| 10 | `{"answer": "B"` with the cut-off flag set | CUT_OFF |

The scorer must give exactly these 40 categories in the self-test.

### 17.3 The five made-up answer sets and the code each must print

The self-test builds five made-up answer sets from the practice tasks. It runs the gate program and the analysis program on each, from start to end. The analysis program treats the practice tasks as if they were final tasks, at level 1, with two equal made-up hash receipts. The gate program gets a made-up clock.

| Set | Replies | Gate program must print | Analysis program must print |
|---|---|---|---|
| `ALL_RIGHT` | Every reply is the right letter, well formed. | `GATE_STOP_DIFFICULTY` | `UNINFORMATIVE_DIFFICULTY` |
| `ALL_WRONG` | Every reply is well formed and is the first shown letter that is not the right one. | `GATE_STOP_DIFFICULTY` | `UNINFORMATIVE_DIFFICULTY` |
| `DESIGNED` | Role-step tasks are sorted by id and numbered from 0. ROLE and ANSWER-GIVEN: right on every task. NO-PASSAGE: wrong on every task. Every other group: right on even numbers, wrong on odd numbers. Plain-fact tasks: right in every group. | `GO`, wording 1, level 1 | `BEATS_ORDINARY_HELP_NO_HARM_NOT_MEASURED_EXPLORATORY` |
| `RANDOM_LETTERS` | Every reply is well formed; its letter is drawn with a fixed seed from the letters shown. | `GO` or any listed stop code | any listed code that is not the pass code |
| `ALL_MALFORMED` | Every reply is plain text with no JSON. | `GATE_STOP_DIFFICULTY` | `INVALID_RUN` |

Why these codes, worked out by hand:

- `ALL_RIGHT`: B alone is 100% right. That is outside both difficulty windows and above 85%.
- `ALL_WRONG`: B alone is 0% right. That is outside both windows and below chance plus 5 points.
- `DESIGNED`: B alone is about 50% right, so R1 passes. ROLE is 100% and every other group about 50%, so C1, C2, C3 and C5 hold. A practice set has fewer than 100 plain-fact tasks, so no-harm is `NOT_MEASURABLE`. It has fewer than 200 role-step tasks, so the code ends in `_EXPLORATORY`.
- `ALL_MALFORMED`: accuracy is 0%, so the gate stops at difficulty, which is checked before format. Every group is at format floor, so the analysis prints `INVALID_RUN`.

### 17.4 Where scoring runs

Inside the AWS job, as a separate stage, after all model calls are finished, their outputs hashed and the model files hashed again. The analysis program prints every number and the one outcome code. It uses whole-number counts and writes its result file so that a not-a-number value can not appear. The report repeats the program's output. Anyone can repeat the scoring from the returned files.

After a stop, the score stage still runs. It then writes the stop code into the result file, and no table about final tasks.

Key custody in the job: final keys sit in a separate folder. The stages that call model B are given the prompt folder only. The scoring stage opens the key folder after all outputs are written and hashed.

## 18. Always printed beside the code

These have no power to change the code.

- The no-harm line: `HELD`, `NOT_HELD` or `NOT_MEASURABLE`.
- ROLE against QUOTES-ONLY, MIXED against QUOTES-ONLY, MIXED against FILLER, each with its difference and range.
- The same tests on four fixed sub-views:
  1. without the LAND and HABIT types (the owner noted the teams often disagreed on whether `^4` and `^7` were present);
  2. only tasks whose type has no left-over entry on its needed Noetics;
  3. only passages with no left-over `^2` to `^9` entry at all;
  4. only tasks where the word-matching rule does not pick the right option under ROLE.
- For each ordinary group, the share of kept questions whose anchor words appear in its note.
- The not-clean share per group and its gap from ROLE. Average padding per group.
- The five category counts per group. Tables per question type. Letter counts per group. Two-by-two tables against NONE.
- The word-matching rule's score per group. This rule has no model in it: it picks the option that shares most content words with the notes.
- The NO-PASSAGE score, if that block ran.
- The near-miss count: WRONG replies that are a valid letter with punctuation, or the exact option text.
- The value X of section 15.4.

Tables per question type and per Noetic are description only.

**Three of these views need the frozen word function.** They are: sub-view 4, the word-matching rule's score per group, and the share of kept questions whose anchor words appear in each ordinary note. All three use `content()` from `tools/verdict.py`. So `tools/verdict.py` is in the job package, at the path `tools/verdict.py`, with the hash pinned in section 3. The analysis program imports the function after checking that hash. It does not copy or rewrite it. So the three views are worked out inside the job, and the pre-check job runs their code on the made-up answer sets before the GPU attempt. They are the answer to the objection "it only pointed at the right sentence", so they may not be left to code that first runs after the result is known.

## 19. The AWS jobs: limits and clock

This plan authorizes no spending. The standing approval record is `OWNER_APPROVAL_ALL_STAGES_20261005T0610Z.json`: spend only inside funds the ledger shows as unreserved, with a stated cap and automatic shutdown on every job. Nothing heavy runs on the laptop.

### 19.1 The pre-check job (operator decision D7)

Before the GPU job, a cheap CPU-only AWS job runs the runner's self-test command only.

- No model B. The tokenizer only. No GPU.
- It exercises the scorer, the gate program and the analysis program on the five made-up answer sets, the padding plan, and every prompt hash.
- A failure there stops the launch and is reported. It does not use the single GPU attempt. What may follow is fixed below.
- It prints two hashes: one of the list of all prompt hashes, one of the padding plan. They are written to the seal file as step 7. Gate 0 of the GPU job must print the same two hashes. A mismatch stops the GPU job with `GATE_STOP_SELFTEST` before any model call.
- The pre-check kit builds three kinds of job: `SEALED_PACKAGE` (the package of seal step 6, or of the last repair line), `REHEARSAL` and `DEVELOPMENT_TEST` (both below). Each job's receipt names its kind in the field `precheck_kind`. Seal step 7 is written only from a passed job of kind `SEALED_PACKAGE`: `tools/ob_seal.py` reads the receipt and checks the `source.zip` (section 11.1; amendment A8).
- The GPU job repeats the same self-test as Gate 0.
- Limits per pre-check job, PROPOSED by this plan: cap **0.50 USD**, hard time limit **45 minutes**, one attempt, host shuts itself down. These are the limits the pre-check kit is built with (REAL, read on 2026-10-05 in `optionb/controller_b1_draft/precheck_cpu/derive_precheck_job.py`). The operator's decision named no numbers for this job. The operator confirms them before launch.
- At most **4** pre-check jobs in all (PROPOSED). So all pre-check money stays at or under 2.00 USD. Each job has its own job id, folder, cap and automatic shutdown. A job is never retried under its own id.

**What happens after a pre-check that does not pass (PROPOSED).** The job programs have never run. So a fault on the first run is likely, and the rule for it is fixed now. First, every failed pre-check is reported, and its returned files are kept. Then one of four cases applies. The record decides which one, not the operator.

| Case | How it is known | What may follow |
|---|---|---|
| The self-test never started | A host, network or controller-kit fault. No `selftest.json` came back. | The same `source.zip`, with the same hash, may be pre-checked again under a new job id. No seal line is added. |
| Package fault | The self-test check `package_matches_seal` failed, and every sealed file is unchanged. | `source.zip` is built again from the same sealed files and pre-checked under a new job id. No seal line is added. |
| Data stop | The self-test printed `GATE_STOP_PADDING`, or the fault sits in a file of seal steps 1 to 5 (the constants, a prompt part, a key). | **Final. No launch.** No file of steps 1 to 5 is changed. A new attempt needs a new plan version. |
| Program fault | The self-test started and did not end with `SELFTEST_PASS`, and the fault sits in one of the five job files of seal step 6. | The repair rule of section 11.1: a reviewed diff and one `6R_PROGRAMS_REPAIRED` line. Then a new `source.zip` and a new pre-check job. At most **2** such repairs. |

- For a program fault, the review record names the file that holds the fault and the evidence: the failed check and the log line.
- No expected category of the 40 known scorer examples may change in a repair.
- Every job that is launched counts toward the 4. When the 4 are used up: no launch; report to the owner.
- Every failed pre-check and every diff is kept as evidence (section 25).

**Rehearsal (allowed, not required).** After seal step 5 and before seal step 6, one of the 4 jobs may run as a rehearsal. Its package is built from the sealed files of steps 1 to 5, the five job files as they then stand, and a scratch copy of the seal file that ends with the line that `tools/ob_seal.py step 6 --dry-run` prints. Its result is never written to the real seal file. A program fault found there is fixed before seal step 6, so no repair line is needed. A data stop found there is as final as in a sealed pre-check. No model B runs in a rehearsal, so it shows nothing about B.

**The development test on made-up data, before seal step 1 (ordered by amendment A10).** This test is ordered. Review round 1 had left it open.

- **What.** One CPU-only AWS job of kind `DEVELOPMENT_TEST`. At most **2** such jobs. Each has its own job id (`cas-optionb-b1-devtest-d1`, then `-d2`), folder, cap and automatic shutdown.
- **Limits per job.** Cap **0.50 USD**. Hard time limit **45 minutes**. One attempt. The host shuts itself down. So all development-test money stays at or under 1.00 USD.
- **Authority.** The operator's decision of 2026-10-05, under the owner's approval record `OWNER_APPROVAL_ALL_STAGES_20261005T0610Z.json`: spend only inside unreserved funds, with a stated cap and automatic shutdown on every job.
- **What runs.** `runner_b1.py selftest`, in the same mode as the pre-check job, on a small made-up package. No model B. The tokenizer only.
- **What the package holds.** Made-up passages, made-up tasks, made-up notes and made-up keys. It never holds a real passage or a real question. It also holds the job programs, this plan, the constants and the file formats, as they stand that day.
- **Who builds the package.** `optionb/dry/build_dev_package.py`. It runs the real laptop tools on the made-up fixture. Then it runs the real zip and contract builders. So the package has the real layout (`FILE_FORMATS.md`, section 20).
- **Purpose.** To catch program faults before anything is sealed. A fault in a sealed constant, such as a wrong expected self-test code, can not be repaired after seal step 1.
- **What it is not.** Its output is never evidence about roles. Its result is never written to a seal file. It is outside the seal chain. It is not one of the 4 pre-check jobs.
- **If it does not pass.** If the first job does not end with `SELFTEST_PASS`, the fault is fixed and the second job is run. Fixing is allowed, because nothing is sealed yet. If the second job does not pass either: nothing is sealed, and the operator reports to the owner.
- **Order.** Seal step 1 is written only after a development test has ended with `SELFTEST_PASS`. No program enforces this. The job's receipt carries its time, and the reviewer checks it against seal line 1.
- **Limit.** The test covers the files as they stood when its package was built. A file that changes after that is not covered by it.

### 19.2 The GPU job (operator decision D8)

- One `g5.2xlarge` (one A10G 24 GB GPU), image `ami-0dddfa1ffa6b87af7`, launched from a new controller folder derived from `D:/tksCAS-runs/controller_cas_small_op11_claude_c1/` (PROPOSED name: `D:/tksCAS-runs/controller_cas_optionb_b1/`). The old folder is not touched.
- **Cap 5.00 USD. Hard time limit 180 minutes. One attempt. No retry. The host shuts itself down.**
- One job at a time on the shared storage slot, with bus notices before and after.
- **Money.** REAL: the shared ledger showed **12.64 USD** unreserved at 2026-10-05T09:49Z. It is read again before each launch. The ledger pointer is `C:/Users/wakil/Documents/Codex/AWS_COMBINED_ALLOCATION_CURRENT.json`. Arithmetic on that reading: with 5.00 USD held for the GPU job, at most 2.00 USD for the pre-check jobs (4 jobs of at most 0.50 USD) and at most 1.00 USD for the development tests (2 jobs of at most 0.50 USD), 4.64 USD would stay unreserved.
- **Call cap:** 5,000 model calls.
- **Outside services** are separate from the AWS caps (amendment A11).
  - **Gemini:** free tier. No money.
  - **DeepSeek:** at most **4.00 USD** in total, for the ordinary notes and the key solver together.
  - **How the tools enforce it.** As a token count. The two DeepSeek tools keep the count in their call logs, which are their checkpoints. The limits are at most **2,430,240** input tokens and at most **1,156,520** output tokens, added up over both tools and both sets. Before each call a tool adds up the counts. If either limit is reached, it makes no call and stops with `STOPPED_TOKEN_CAP`. A reply that carries no token count stops the tool with `STOPPED_NO_TOKEN_COUNT`. A limit is never raised without a new reviewed plan version.
  - **Where the two numbers come from.** REAL, the operator's reading on 2026-10-05: two calls to `deepseek-v4-pro`, with 60,756 input tokens and 28,913 output tokens in total, cost about 0.10 USD. The input price and the output price were not measured apart. So each limit is 40 times the measured count: 40 × 60,756 and 40 × 28,913. Whatever the split between the two prices, a spend inside both limits costs at most 40 × 0.10 = 4.00 USD at that model's prices.
  - **EXPECTED, NOT MEASURED.** `deepseek-chat` costs no more per input token, and no more per output token, than `deepseek-v4-pro`. The label run's receipt (`verdict/labels_team_b.json.receipt.json`) holds token counts only: 2,327,821 input tokens and 88,948 output tokens in 428 calls. It holds no price. So it gives no price basis.
  - **EXPECTED need.** At the very most about half of each limit: that is the case where every note is written twice and every possible question is solved. The likely need is well below that. This is an estimate from word and punctuation counts. It is not a tokenizer count. EXPECTED spend: under 2 USD. This estimate was made before amendment A13. With A13 the ordinary notes are longer, so the need on the output side is higher. **To be measured again by the tool fixer**, from the new dry run of the role notes. The two limits do not change.
  - **Limit of the count.** Calls that are running when a limit is reached still finish. So a count can pass its limit by a few calls.

### 19.3 The clock

Minutes after launch:

| Point | Minute | Seconds |
|---|---:|---:|
| Setup must end | 30 | 1,800 |
| All model work stops (work cutoff) | 135 | 8,100 |
| The score stage must end | 140 | 8,400 |
| Forced shutdown | 175 | 10,500 |
| Hard limit | 180 | 10,800 |

Why 135: REAL, the guest must finish its end-of-run file hashes 30 minutes before the forced shutdown. With shutdown at 175 that deadline is minute 145.

Model calls, REAL arithmetic on the REAL ceilings (one call = one task in one group):

| Practice settings | Practice calls | Final must-run calls | Final NO-PASSAGE calls | Whole job |
|---:|---:|---:|---:|---:|
| 8 | 1,064 | 3,036 | 300 | 4,400 |
| 12 | 1,552 | 2,730 | 270 | 4,552 |

All are under the cap of 5,000. EXPECTED: about 2,700 calls; 0.3 to 0.5 seconds per call; planned with 1 second. EXPECTED cost: about 0.9 to 2.0 USD. A stop at a practice gate: under 1 USD. A stop in the self-test or in setup: about 0.3 to 0.5 USD.

### 19.4 The runner and its file rules

The runner is `optionb/job/runner_b1.py`. Five commands, in this order: `selftest`, `run-practice`, `gate`, `run-final`, `score`.

For every call one line is written and flushed to disk at once: task id, group, level, full prompt text and its hash, prompt and notes token counts, raw answer, the answer's token ids, cut-off flag, seconds. So finished calls survive a crash. Before each call the runner checks the clock against the work cutoff.

File rules (the guest scans every file under its work folder every 5 seconds; some ordinary habits make that scan fail and kill the stage):

- Write only under one new folder, `work/run_b1/`.
- Create each output file once. Then only append and flush.
- Never rename, delete or use temporary files. No write-then-rename.
- File names use only letters, digits, dot, dash and underscore.
- Write nothing under the source folder or the authority folder.
- Load the model from the payload snapshot path with offline settings. No symlinks, no hard links.

Order of final calls. Block 1, must-run: every final task in a seeded order, its groups back to back. Block 2: NO-PASSAGE on role-step tasks, if the time gate allowed it. A block is never cut in the middle by plan.

### 19.5 What the guest must do

These come from the machine review of the design. The controller's builder owns them.

1. **Setup flag.** Right after the self-test passes and before the first model call: check the setup clock, mark setup complete, force a progress upload.
2. **Deadlines.** The final stage gets the work cutoff (minute 135). The score stage gets minute 140, and a time limit of 5 times its measured self-test time.
3. **Model hash before scoring.** After the last model call and before the score stage, hash the model folder and write `controller/MODEL_AFTER_CALLS.json`. A failure here must not skip scoring. The score command reads that receipt and `controller/MODEL_PRE.json`.
4. **Small result reader.** It returns only the outcome code, the hash of `RESULT.json` and its size. A code that is not capital letters and underscores, at most 80 characters, becomes the fixed text `RESULT_UNREADABLE`.
5. **Cleanup.** Run `independent_cleanup.py` within 30 minutes after `CLEANUP.json` is written. Nothing arms it at launch.
6. **Prior cleanup record.** The launch gate asks for a VERIFIED cleanup record of the last job on the shared slot. If none can be made, the launch is blocked and reported. The gate is not loosened.

Label for the job: built by Claude, checked by a separate reviewer in one review round, never run before.

## 20. Sizes and what can be concluded

### 20.1 Counts

REAL: 192 eligible passages; 34 practice and 156 final with 8 practice settings. At most 300 final role-step tasks and 156 final plain-fact tasks. At most 66 and 34 in practice.

**How many will survive is NOT MEASURED.** Six filters run in a row. **The likely size is 100 to 140 final role-step tasks, on 75 to 100 passages** (EXPECTED; the design author's and a reviewer's reading). By the fixed rule that is the exploratory tier, and the code then ends in `_EXPLORATORY`. The free build prints the real number per filter, on the practice settings first, before any money is spent.

### 20.2 Arithmetic for one comparison

Suppose the role notes lift accuracy by 10 points over the best ordinary notes, and the two groups differ on 30% of tasks. For independent tasks:

`n = (1.645 × sqrt(0.30) + 0.84 × sqrt(0.30 − 0.10²))² / 0.10² = (0.901 + 0.452)² / 0.01 = 183 tasks`

for an 80% chance of detection at the one-sided 5% level. That matches the directive's "roughly 150 to 250".

### 20.3 The detection table

Chance of the one pass code. The design author's simulation: 2,000 runs per cell, passage-level test, every condition included (the five comparisons, the 5-point margin, beating QUOTES-ONLY, no-harm, the padding rule). Not rerun for this plan. ASSUMED, not measured: B alone 45%, filler 44%, ordinary free 52%, ordinary informed 56%, plain facts 80%; two questions on one passage move together. "Gain" is the true gain of ROLE over the better ordinary notes.

**Case A, the kind case:** MIXED 46%, QUOTES-ONLY 50%.

| Size | Groups differ on | Gain 0 | Gain 5 | Gain 10 | Gain 15 |
|---|---|---:|---:|---:|---:|
| 210 tasks on 140 passages | 25% of tasks | 3% | 37% | 77% | 83% |
| 210 tasks on 140 passages | 40% of tasks | 2% | 19% | 59% | 79% |
| 130 tasks on 100 passages | 25% | 3% | 24% | 66% | 83% |
| 130 tasks on 100 passages | 40% | 1% | 12% | 43% | 72% |
| 100 tasks on 75 passages | 25% | 2% | 19% | 53% | 76% |
| 100 tasks on 75 passages | 40% | 1% | 9% | 30% | 60% |

The chance tops out near 82%. A harmless note still fails the no-harm check about 1 time in 10, and the padding rule trips about 1 time in 15.

**Case B, pointing does part of the work:** MIXED 8 points below ROLE, QUOTES-ONLY 6 points below ROLE. Shown as pass code / pointing-only code.

| Size | Groups differ on | Gain 10 | Gain 15 |
|---|---|---:|---:|
| 210 tasks | 25% | 47% / 18% | 50% / 21% |
| 210 tasks | 40% | 24% / 17% | 28% / 22% |
| 130 tasks | 25% | 29% / 19% | 33% / 24% |
| 130 tasks | 40% | 13% / 13% | 17% / 18% |
| 100 tasks | 25% | 21% / 15% | 25% / 21% |
| 100 tasks | 40% | 9% / 9% | 14% / 15% |

**Case C, pointing does all of it:** QUOTES-ONLY equal to ROLE. The pass code comes out 3% to 5% of the time (a wrong "role names shown"). The pointing-only code comes out, for a 10-point gain, 63% of the time at 210 tasks and 44% at 130 tasks when groups differ on 25% of tasks, and 38% and 23% when they differ on 40%.

### 20.4 What this allows, in plain words

- A large total advantage, 15 points or more over the better ordinary notes, would usually be seen at 130 tasks if the role names carry it (72% to 83%).
- A 10-point advantage is seen about 4 to 7 times in 10 at 130 tasks, and 3 to 5 times in 10 at 100 tasks.
- If part of the gain is pointing, the test at this size can not reliably show that the role names add something.
- A wrong pass when there is no true gain: about 1% to 3%.
- A pass still needs the replication on fresh passages that the directive requires before anything is said outside the project.
- A miss means "no advantage of about X points or more was shown". A miss does not mean "no gain". EXPECTED at the likely size: a miss can not tell "no advantage" from "an advantage under about 12 points".
- EXPECTED at the likely size: the test can not reliably tell "role names help" from "pointing helps" unless the role names add about 12 points or more on top of pointing.
- A plain-fact loss of 15 points would be caught. A loss of 5 or 10 points may slip through (section 16).
- The pool can not be made larger from these 428 passages without using rule-15 passages. A larger study needs new passages and new labels.

## 21. What the test can and cannot show

**It can show:**

- Whether B answers role-step questions better with a role description both label teams agree on than with nothing, with filler, with wrong roles, with the same words and no role names, and with two kinds of ordinary notes of the same length from an equally strong model.
- Where a gain comes from: being pointed at key sentences (QUOTES-ONLY against the ordinary notes and FILLER), the formatted role information on top of the pointing (ROLE against QUOTES-ONLY; see "What condition C5 compares" below), or wrong names (MIXED against QUOTES-ONLY).
- Whether the role notes cost B a large share of answers it already had.
- If even agreed role descriptions do not help B, the internal reader is not worth building for this purpose with this model B and this prompt layout. That is the cheap early answer the owner asked for.

**What condition C5 compares (amendment A6).** C5 is "ROLE beats QUOTES-ONLY". It compares the whole role note with the bare labels and quotes. The whole role note holds four things that QUOTES-ONLY does not: the role tags, the canon definition lines, the canonical sayings lines (amendment A13), and the Mind and related-thing fields. All four are removed at once. So a pass shows that the formatted role information adds something beyond pointing. It does not show that the role names alone do. Wherever this plan says "the role names" for what C5 tests, it means this whole formatted role information.

**What the role note holds, and under which labeling rule (amendment A13).**

- The labels behind the role notes were made under labeling guide version 1.2, before the owner's ruling of 2026-10-05 on Mind and the colloquialisms. They were not made again for this test.
- The role note now holds, for each Noetic present: its tag, its canonical definition line and its canonical sayings line.
- The owner's sentence about Mind is not printed in any note. It governs labeling only.
- Printing the sayings in the notes is the operator's reading of the ruling, applied to a place the owner did not name. The owner may strike it (section 22, question 22).

**It cannot show:**

- That the role names alone add something. See "What condition C5 compares" above.
- Which part of the role note did the work: the tag, the definition line or the sayings line. The three come and go together. ROLE has all three right. MIXED has all three swapped to another Noetic (`^1` stays). QUOTES-ONLY has none.
- Anything about labels made under the owner's ruling of 2026-10-05. These labels were made under guide version 1.2, before the ruling. Labels made under the ruling may differ.
- That a reader inside model A can supply such descriptions. This job does not call model A.
- That the role descriptions are right. They are agreed between two language models. Many are also partial: some entry was left out because only one team gave it.
- That role notes help on questions in general. Every kept question turns on words the role note names. That is home ground for the role notes. A win means "on questions that turn on these relations, where the checked description covers the point asked".
- That the help is special to CAS. Two ordinary rivals are not every rival. The directive's stricter test, a fair non-CAS set of roles, is not in this job. No such claim may be made.
- Whether a miss came from "the information did not help" or from "the notation was not read". The group that could split these, ROLE-PLAIN, is struck (D1).
- Anything about sign reading or reasoned conclusions. Those 104 passages are left out until the owner rules.
- Anything about passages where the teams did not agree.
- Anything firm about a single Noetic or question type. Those tables are small.
- Anything about `^4` and `^7` beyond the passages where the teams happened to agree. Their problem is presence, and this test does not repair it.
- Anything about `^0`, passages with no roles, other model pairs, found text or longer passages. One 0.5B model, 53-word passages, English, one prompt layout.
- Learning. Nothing is trained.

**How each result reads:**

| Code | Reading |
|---|---|
| `ROLE_HELP_BEATS_STRONGEST_ORDINARY_HELP` | The premise holds on this test, for the whole formatted role note. That the role names alone add something is not shown (C5, above). Building the reader gains a reason, pending replication on fresh passages. |
| `POINTING_BEATS_ORDINARY_HELP_ROLE_NAMES_NOT_SHOWN` | Checked label-and-quote notes beat ordinary help; the role names did not show an added effect. Whether that is enough reason to build the reader is the owner's call. |
| `ROLE_HELP_NOT_ABOVE_ORDINARY_HELP` | An advantage over a strong model's plain notes was not shown. The report says how large a gain could have been missed. |
| `HELP_NOT_TIED_TO_CORRECT_ROLES` | The notes helped, but right role names did no better than wrong ones. |
| `NO_ROLE_HELP_SHOWN`, `HELPS_BUT_BREAKS_RIGHT_ANSWERS` | Recorded as such, never softened. |
| `FORMAT_GAP_NOT_READABLE`, `PADDING_HURTS_B_NOT_READABLE`, `UNINFORMATIVE_DIFFICULTY`, `INVALID_RUN`, or a gate stop | No finding about roles either way. |

**Risks stated in advance:**

- Too few tasks may survive. Under 100 final role-step tasks, the job does not launch.
- B may be near chance or near perfect at both option levels. The practice gate then stops the job before a final task is spent.
- B may not use the notes at all, as in the pilot. Gate 5 catches that.
- B may dress its answer (`C. the smell of damp rope`). The strict scorer would then give zero to every group. Gates 1 and 4 guard against it.
- The rival may simply win or tie. By the rules that is "no advantage shown", even if role information is useful.
- Pointing may explain the gain. Then the likely code is the pointing-only code, or a miss.
- Keys are soft. "Most likely" questions are checked by the writer and two language models, which can share a bias. A wrong key adds noise to every group alike.
- Few model families. DeepSeek is label team B, ordinary-note writer and key solver, in separate stateless calls. Gemini wrote the passages (`gemini-2.5-flash`), writes the questions (`gemini-3.5-flash-lite`) and checks the notes (`gemini-3.1-flash-lite`): three models of one vendor.
- One key solver is not blind to CAS. The Claude sub-agent carries the CAS definitions in its project instructions. It only picks a letter. It never writes or edits a question, a key or a note. Its vote can still tilt which questions are kept.
- The strength of the ordinary-note writer is not proven equal to label team B's. Both were asked for as `deepseek-chat`. The model that answered team B was not recorded (section 3).
- New code on a single attempt. The runner, the gate and analysis programs and the edited guest have never run. The pre-check job is there to catch faults cheaply.
- Longer notes (amendment A13). The sayings lines make the ROLE and MIXED notes longer, and the ordinary notes grow with them. More passages may be lost at the support check and at the answer-leak screen (section 10, Step 7). How many is NOT MEASURED. If the writer falls well short of the larger word target, the padding rule (10%) can stop the job in its self-test.
- Shared everyday words (amendment A13). The sayings put everyday words into the ROLE and MIXED notes. A question or an option may share such a word. Only ten distinctive words are kept out of the question sentence (section 9). The word-matching views of section 18 show how far plain word overlap goes.

Expectation, not a result: the informed ordinary notes will be a hard rival. The most likely outcome is `ROLE_HELP_NOT_ABOVE_ORDINARY_HELP` or a miss, with the `_EXPLORATORY` ending. Either is a real answer, not a broken test.

**Spec sheet.** The result, pass, fail or stop, goes into `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/CAS_HARNESS_SPEC_SHEET.md` and `CHANGELOG.md` in the same commit, with exact numbers and the artifact path, using that sheet's own status words. A negative result is never deleted.

**The status word is fixed before the result (PROPOSED).** The sheet's words differ a lot. So the word may not be chosen after B's results are seen.

- Before the GPU launch the owner signs one table, `optionb/OUTCOME_STATUS_TABLE.json`. It gives exactly one status word of the sheet's legend to each of 28 keys: the 11 outcome codes (numbers 1 to 11 in section 15.4), the 7 codes that can end in `_EXPLORATORY` (numbers 5 to 11) with that ending, the 8 stop codes, `RESULT_UNREADABLE`, and `NO_RESULT_FILE` (the job returned no result file). 11 + 7 + 8 + 2 = 28. A key is the name of a code, not its number.
- The owner decides the table. This plan fixes only its form and three limits.
  1. The four "nothing was read" codes, every gate stop, `RESULT_UNREADABLE` and `NO_RESULT_FILE` never get a pass word. The pass words are `VALIDATED`, `LICENSED`, `PASS`, `SANITY_PASS` and `HOLDS`.
  2. A code that ends in `_EXPLORATORY` never gets `VALIDATED` or `LICENSED`.
  3. Only the pass code, with or without the ending, may get a pass word. This follows from section 15.4: there is only one pass.
- The table is hashed in seal step 7. `tools/ob_seal.py` refuses step 7 without a table that keeps the limits. So there is no GPU launch without it.
- After the run a program prints the word: `tools/ob_seal.py status-word --result <RESULT.json>`. It looks the code up in the sealed table. Nobody picks the word by hand.

## 22. Questions that stay with the owner

Each has a default. The default applies until the owner says otherwise. If the owner changes one, a new plan version is written and sealed before the build goes on.

| # | Question (shortened) | Default until the owner says otherwise |
|---:|---|---|
| 1 | Does recognizing a familiar sign count as Cause → Effect when it brings another idea to mind? | Guide rule 15 stays as written. All 104 rule-15 passages are left out. The test does not depend on the answer. |
| 2 | Does an idea reached through reasoning also count as Effect? After you rule, should those 104 passages be tested apart? | Same handling. They are not tested here. |
| 3 | If the role notes beat ordinary help but not the same quotes with no role names, the code is `POINTING_BEATS_ORDINARY_HELP_ROLE_NAMES_NOT_SHOWN`, not a pass. Do you accept that? Would pointing alone be reason enough to build the reader? | The code is printed as written and is not a pass. |
| 4 | Are the six question types fair everyday uses of the Noetics? | Used as written in section 7. |
| 5 | Do you approve or correct the plain words given to the question writer and to the ordinary-note writer (section 8)? | Used as written. They are study text, never definitions. |
| 6 | May the canon definition lines be printed, word for word, inside the role notes B reads? | Yes (operator decision D2). No wording is changed. |
| 7 | Is the stand-in acceptable: label = the shorter quote, supporting quote = the whole sentence? Or should option B wait for labels made under a new pointing rule? | The stand-in is used (D3). The test does not wait. |
| 8 | ROLE-PLAIN: approve, correct or strike the plain sentence frames? | Struck (D1). |
| 9 | Is the mixed-up control acceptable? It prints deliberately wrong tags inside that one control group only. | Used as written. |
| 10 | What counts as "carefully checked": every agreed entry (192 passages), or only passages where the teams' entries pair off with nothing left over (56 passages)? | Every agreed entry (D3). The stricter split is printed as a sub-view. |
| 11 | `^4` and `^7`: keep their question types in the pooled set, or report them apart only? | Kept in the pooled set, with a printed view without them. |
| 12 | Size. When you have the real count, run at that size, or first label new passages to reach 200 or more? | The GPU job waits for one yes from the owner after the real counts are shown. A run spends the final passages for good. |
| 13 | Money: one GPU job with a 5.00 USD cap and a 180-minute hard stop; up to 4 small pre-check jobs of at most 0.50 USD each; up to 2 development tests on made-up data of at most 0.50 USD each; outside services extra, with DeepSeek at most 4.00 USD in total. | Limits as in section 19. Spending stays inside unreserved funds. Asked together with question 12. |
| 14 | Do you want to read 20 role notes before they are sealed, and the practice questions before the job? | The sample file is written and offered. The build goes on unless the owner asks it to wait. |
| 15 | R2 and R3: 5 points AND the test, or a plain 5-point line? | 5 points AND the test (D9). |
| 16 | If the outcome is "not above ordinary help": is the reader still wanted for another reason? | No default. It is the owner's decision after the result. |
| 17 | If the final phase comes back invalid or not readable: may new questions be written on the same passages? | No. A new attempt needs new cases and a newly reviewed version. |
| 18 | Do you want fewer groups? | The seven must-run groups of section 11.2. |
| 19 | Should a later round add a fair non-CAS set of roles? | Not in this job. No result here may be called special to CAS. |
| 20 | Which spec-sheet status word belongs to each outcome code and each stop code (section 21, "Spec sheet")? | No default. The GPU job does not launch until the owner has signed the table. The limits of section 21 apply. |
| 21 | Are the review-round rules acceptable: the reserve targets 45 and 25, up to 4 pre-check jobs, up to 2 repairs of the job programs, and the two repair windows (sections 10, 11.1, 12.1 and 19.1)? The rule for a second note checker is gone: there is one checker (amendment A2). | Used as written. They are PROPOSED. |
| 22 | May each canon definition line in the role notes be followed by that Noetic's canonical sayings, copied character for character from the table of Clarification 6 (amendment A13)? This is the operator's reading of your ruling of 2026-10-05, applied to a place you did not name. | Yes: the sayings lines are printed in ROLE and MIXED. The owner may strike it. |

## 23. Changes made by the operator after the design review

| # | Decision |
|---|---|
| D1 | The ROLE-PLAIN group is struck. The owner has not approved its plain sentence frames, and the canon may not be paraphrased. No code path, no prompt part, no call for it. The seven must-run groups stay: NONE, FILLER, ROLE, MIXED, ORD-INFORMED, ORD-FREE, QUOTES-ONLY. Practice-only ANSWER-GIVEN and the task check NO-PASSAGE stay. |
| D2 | Canon definition lines are printed word for word inside ROLE and MIXED notes. Added by amendment A13: each is followed by that Noetic's canonical sayings line, copied character for character. |
| D3 | "Checked" = entries both label teams agree on under the frozen same-reading test in `tools/verdict.py`, paired one to one. The 104 rule-15 passages are left out. The stand-in rule builds label and supporting sentence as the design says. |
| D4 | Replaced by amendment A1 (section 27). The question writer is Gemini `gemini-3.5-flash-lite`. It works in batches of up to 4 passages per call, in a seeded fixed order, each passage clearly fenced, told to treat every passage on its own. One model writes the practice set, the final set and the spare pass. On an HTTP 429 reply the tool stops cleanly, keeps a checkpoint and resumes later. The spare pass is a second run with a different seeded batch order. All of this is logged per call, with the model name from every reply. |
| D5 | Kept by amendment A3. Key solvers: DeepSeek, asked for as `deepseek-chat`, in fresh stateless calls, and a Claude Sonnet sub-agent that is given text only, with the model id `claude-sonnet-5-5`. The tool has an export step and an import step for the Claude solver. |
| D6 | Ordinary notes: DeepSeek, asked for as `deepseek-chat`, temperature 0, one passage per call. Support check, as replaced by amendment A2: Gemini `gemini-3.1-flash-lite` in batches of up to 12 notes per call, with the same checkpoint and resume. There is no second checker. If Gemini refuses, the build waits. |
| D7 | Before the GPU job, a cheap CPU-only AWS pre-check job runs the runner's self-test command only. A failure there stops the launch and does not use the single GPU attempt. The GPU job repeats the same self-test as Gate 0. |
| D8 | Money for the GPU job: cap 5.00 USD, hard time limit 180 minutes, one attempt, host shuts itself down. The shared ledger showed 12.64 USD unreserved at 2026-10-05T09:49Z (not 12.77). It is re-read before launch. |
| D9 | Validity rules R2 and R3 stay as the final design wrote them: 5 points AND the test. |
| D10 | Scorer version 0.1.1 (a repeated key is FORMAT_FAIL), as designed. |

The twelve later amendments, A1 to A12, are in section 27. Rows D4, D5 and D6 above are shown as the amendments left them.

Amendment A13 is in section 27.3. Row D2 above is shown as A13 left it. A13 is the operator's reading of the owner's ruling of 2026-10-05, applied to a place the owner did not name: the role notes that model B reads. The owner may strike it (section 22, question 22).

## 24. Details this plan fixed where the design left them open

Each is the simplest rule that fits the design. None is meant to loosen a control. Review round 1 found that two of them did: item 17 (Gate 4) and the letters rule of item 11. Both were made stricter (section 26). A reviewer or the owner may overrule any of them before the seal.

1. **Pairing.** Entries are paired in file order (section 4). REAL: same counts as the largest possible pairing.
2. **Exclusion.** The rule-15 test reads the raw entries of both teams.
3. **Sentences.** The sentence rule and its short list of titles (section 6).
4. **"Shorter".** By number of characters; a tie goes to team A.
5. **Option check for PULL-PUSH.** It looks at left-over `^2` and left-over `^3` entries for both forms.
6. **Plain-fact questions** go through Step 2, Step 4 and Step 5 as well.
7. **Spare questions** come in only after a Step 2 or Step 3 drop.
8. **Word matching.** List A matches a word and its longer forms. List B matches whole words in any letter case, so `above` and `below` are barred too.
9. **No-passage solvers must pick a letter.** This makes the screen stricter.
10. **Length backstop.** Longest and shortest are counted apart, each at most 35%, per set.
11. **Letters last.** Text keys are sealed at step 3. Letters are set at step 5, after the answer-leak screen, so the letter balance holds on the kept set. Letters are dealt in turn over the whole task family, type after type, without starting again at A for each type.
12. **Ordinary notes.** The word-target formula; one fixed format line in the request; one fixed sentence in the rewrite request; a second failure drops the passage for every group.
13. **Support check.** A batch is the six notes of two passages. One checker judges every note. There is no fallback checker (amendment A2). If Gemini refuses, the build waits.
14. **Answer-leak screen.** The three letter patterns; rule (b) also tests single sentences of 5 words or more; all three note lengths are screened.
15. **Padding.** Counted per passage; averaged for practice and final apart; either above 10% stops the job.
16. **Frames.** The NO-PASSAGE frame starts with `Answer the question.` The ANSWER-GIVEN sentence.
17. **Practice steps P1 to P3.** Gate 4 counts the role-step tasks and the plain-fact tasks of a group apart, and both must clear, as rule V3 does on the final tasks. Gate 7 uses the mean seconds of the must-run practice calls.
18. **`_EXPLORATORY`** is added to codes 5 to 11 only.
19. **The test.** 5,000 of 100,000 flips; whole-number point rules; the standard error is the standard deviation of the resampled values, with no division by a count (amendment A4). The random draws use Python's own `random` module, exactly as section 13 says.
20. **The made-up sets** are defined exactly, with the gate result each must give.
21. **The score stage always writes a result file,** also after a stop.
22. **Pre-check.** Its two hashes bind the GPU job. Its money and time limits are PROPOSED.
23. **Call counts** were recomputed without ROLE-PLAIN.
24. **A tenth scorer example** (cut off) was added.
25. **No fallback question writer** in this version.

Added in review round 1. All are PROPOSED:

26. **Reserve targets.** 45 role-step and 25 plain-fact practice tasks. The launch floors stay 36 and 20.
27. **Practice first, Step 7 included.** The practice notes are written, checked and screened (report only) before the first final question is written.
28. **After a failed pre-check.** Four cases; at most 4 pre-check jobs of at most 0.50 USD and 45 minutes each; at most 2 repairs of the job programs; an allowed rehearsal.
29. **Repair lines.** `6R_PROGRAMS_REPAIRED` and `TR_TOOLS_REPAIRED`, each with a kept old copy, a diff and a review record. Amendment A5 gave each line a window (section 11.1).
30. **The tools are sealed** in step 1.
31. **`tools/verdict.py` is in the job package.**
32. **The status-word table.** Signed by the owner, hashed in seal step 7, with three limits.
33. **The Claude solver's model id** is pinned: `claude-sonnet-5-5` (amendment A3). It serves the key solver only. There is no Claude note checker (amendment A2).

Added with amendment A13. All are PROPOSED:

34. **The sayings line.** Its place (right after the definition line of its Noetic), its form (`Sayings: <<SAYINGS>>`) and its source (the third cell of the table row). In the blanked frame text it stays whole.
35. **The path of the sixth source.** It is written `../../docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`, counted from the study folder like every other path.
36. **List C** got ten distinctive words of the sayings. They bar the question sentence only.
37. **A note the writer can not produce.** After two empty or cut-off replies for one note, the passage is dropped with the status `DROPPED_NOTE_NOT_WRITTEN`. At most 3 passages of a set; one more stops the tool (section 10, Step 7).
38. **Exit codes and output of the laptop tools.** Every `tools/ob_*.py` program ends with code 0, 1, 2 or 3. A code means the same thing in every tool. Only code 0 lets the next step of the run order start. Every tool prints in UTF-8. The exact rule is in `FILE_FORMATS.md`, section 0.

## 25. Evidence kept

**Before launch** (on the laptop, copied to the archive drive): the seal chain with hashes, plan first; every outside call's full prompt and raw reply with hashes, and the model name the service put in each reply; the model name from each Claude sub-agent transcript; the DeepSeek token counts; the removal log with every dropped question, note or passage and the rule that removed it; the survival count per filter, practice first; per passage, the entries used, the entries only team A gave and the entries only team B gave; the answer-leak screen's hits by rule; the record of who could open which file; the plan's one review.

**From the job** (one result archive under 100 MB): one line per model call; the self-test output with the padding plan and the five made-up runs; `GATE.json`; `RESULT.json`; the model file hashes at the start, after the last model call and at the end; every stage's log; the controller's receipts and the cost record.

**After the run:** the spec sheet and the changelog, in the same commit. The status word printed by `tools/ob_seal.py status-word`, with the hash of the owner's table.

**From repairs and failed pre-checks** (under `optionb/repairs/` and in the controller folders): every failed pre-check's receipt and returned files; for every repair, the old copy of each changed file, the diff, the review record and the seal line; the list of derived files that were deleted and derived again.

**From the development test** (in its controller folder): the receipt and the returned files of each job, the made-up package, and the cost record. They are kept as a record of a program test on made-up data. They are never evidence about roles.

## 26. Review round 1: findings and what was done

Six reviewers read the draft of this plan, the constants, the file formats, the tools and the job programs. There was one round. They raised 20 blocking or major findings. Several name the same fault from different sides. One line each, in the order they were given.

"This plan's files" means this plan, `optionb/PLAN_CONSTANTS.json` and `optionb/FILE_FORMATS.md`. Where a tool or a job program must also change, that work belongs to the fixer of that file. It is named in the last column. It is not claimed as done here.

| # | Reviewer | Finding, in short | What was done in this plan's files | Left for another file's fixer |
|---:|---|---|---|---|
| 1 | plan fidelity | The constants named numpy for the test's random draws. The analysis program uses Python's own `random`. | The constants now hold the procedure the program runs. `tests.sign_flip_block_rows` is deleted. Section 13 states the draws exactly. | Hashes of the constants quoted elsewhere are stale (`optionb/job/SELFTEST_EXPECTED.json`, the dry eligibility files). |
| 2 | plan fidelity | Three views that are "always printed" need `tools/verdict.py`, which was not in the job package. | `tools/verdict.py` is in the package list (file formats, section 14). Section 18 says why. | `tools/ob_seal.py` (package path), `analysis_b1.py` (needed files). |
| 3 | plan fidelity | No rule for what follows a failed pre-check. | Section 19.1: four cases, 4 jobs at most, 2 program repairs at most, a rehearsal. Section 11.1 and file formats 15.2 and 15.3: the repair lines. | `tools/ob_seal.py`, the run sheet, the pre-check kit. |
| 4 | plan fidelity | Gate 4 counted both task families together and was weaker than rule V3. | Gate 4 counts them apart; both must clear. Sections 12.3, 15.5 (e) and 24 item 17; constants `gates.gate_4`; file formats 17.7. The higher chance of a format stop is stated. | `gate_b1.py` (the tally). |
| 5 | plan fidelity | The reserve rule had no margin and covered role-step tasks only. | Reserve targets 45 and 25 for both families; launch floors unchanged. "Practice first" now runs Step 7 on the practice set before any final question is written. Sections 10 and 12.1. | `tools/ob_select.py`, `tools/ob_seal.py`. |
| 6 | plan fidelity | The letters rule favored A, and "exactly chance" was false. | Letters are dealt over the whole family without starting again at A per type. The sentence now says "chance to within one task". Section 10 Step 6; constants `selection.letters`. | `tools/ob_assemble.py` (`set_letters` and its balance check). |
| 7 | plan fidelity | The operator could choose the note checker after seeing verdicts. The fallback model id was not pinned. | Then: a fixed rule with no choice, and a place for the model id. Now, by amendments A2 and A3 (section 27): there is one checker and no fallback, and the model id is pinned. | `tools/ob_check_support.py` (the fallback path is taken out). |
| 8 | plan fidelity | The eleven laptop tools were never sealed. | They are sealed in step 1. A tool repair has its own reviewed seal line. Section 11.1; file formats 15. | `tools/ob_seal.py` and each tool's seal check (the hash in force). |
| 9 | plan fidelity | The spec-sheet status word would be chosen after the result. | One owner-signed table, hashed in seal step 7, with three limits; a program prints the word. Sections 15.4, 21 and 22 (question 20); file formats 19. | `tools/ob_seal.py` (step 7 check and the `status-word` command). The owner signs the table. |
| 10 | leakage and custody | Same as 7, seen in the support-check tool: the 24-hour clock, the free `--max-items`, a plain rate refusal counted as a daily-cap stop. | Then: the rule text for the fallback. Now, by amendment A2: the fallback rule, its 24-hour clock and its sheets are deleted. What a daily-cap refusal is, and what a rate refusal is, stay in the constants and in file formats section 9. | `tools/ob_check_support.py`. |
| 11 | leakage and custody | Seal step 3A could be written before the reserve rule was finished; step 3B looked at one floor only. | Decided here: step 3A needs the reserve rule finished; step 3B needs both practice launch floors. File formats 7.1, 7.2 and 15. | `tools/ob_seal.py`, `tools/ob_select.py`. |
| 12 | leakage and custody | Screen rules (c) and (d) may drop many passages that hold no leak, and this could first be seen late. | The rules are kept: a looser rule would weaken the screen. A report-only run on the practice set shows the hit rate before any final question is written. Section 10; constants `leak_screen`; file formats 10.2. | `tools/ob_screen_notes.py` (the `--report-only` mode). |
| 13 | statistics | Same as 1. | As 1. | As 1. |
| 14 | statistics | Same as 2, seen in the analysis program. | As 2. | `analysis_b1.py`. |
| 15 | runner and scorer | Same as 1. | As 1. The standard library procedure was kept; numpy was not added. | As 1. |
| 16 | guest and controller | Same as 3, seen in the run sheet and the pre-check kit: fixed job id, no retry after a host fault. | As 3. Each pre-check job gets its own job id with the attempt number as suffix. | The run sheet, `derive_precheck_job.py`, `precheck_supervisor.py`. |
| 17 | guest and controller | The run sheet calls a sleeping laptop harmless; it is not. No free-memory check before the launch claim. | Nothing to change in this plan's files. | The run sheet and `aws_control.py`. |
| 18 | interfaces | Same as 2, seen in the seal tool. | As 2. The package path of `tools/verdict.py` is fixed as `tools/verdict.py`. | `tools/ob_seal.py`, `analysis_b1.py`. |
| 19 | interfaces | Same as 1. | As 1. | `tools/ob_eligibility.py` is run again, because its files record the hash of the constants. |
| 20 | interfaces | The job programs first run only after they are sealed, with no way to repair them. | As 3: the repair line, the allowed rehearsal before seal step 6, and the test on made-up data before seal step 1. Amendment A10 (section 27) now orders that test. | `tools/ob_seal.py`; `optionb/dry/build_dev_package.py` builds the made-up package. |

No finding was set aside. For finding 12 the reviewer offered two ways. The one that keeps the screen as strict as before was taken.

**Numbers that review round 1 added.** All are PROPOSED. None is a measurement: reserve targets 45 and 25; at most 4 pre-check jobs; 0.50 USD and 45 minutes per pre-check job; at most 2 repairs of the job programs; 28 keys in the status table. Two more numbers of that round are gone: the 24 notes on a sheet and the 24 hours between two daily-cap refusals belonged to the second note checker, which amendment A2 removed.

## 27. Outside review and amendments A1 to A13

After review round 1 an outside reviewer read this plan. The reviewer is not Claude. It was asked for as `deepseek-v4-pro`, and the reply's own model field says `deepseek-v4-pro`. The record is `optionb/OUTSIDE_REVIEW_PLAN.md`. The verdict was ACCEPT_WITH_NOTES, with seven major findings and no blocker.

The reviewer was also asked to judge two changes the operator then had in mind: (1) DeepSeek `deepseek-v4-pro` as the question writer; (2) a Claude Sonnet sub-agent as the support checker from the start. Findings 2, 3 and 4 are about those two.

On 2026-10-05 the operator then made twelve amendments, A1 to A12. They replace anything in this plan that said otherwise. Nothing was sealed and nothing had run. So the version stays 1.0. The numbers of sections 1 to 26 did not change.

"This plan's files" means this plan, `optionb/PLAN_CONSTANTS.json` and `optionb/FILE_FORMATS.md`. Where a tool or a job program must also change, that work belongs to the fixer of that file. It is named in the last column. It is not claimed as done here.

### 27.1 The seven outside findings

| # | Finding, in short | What was done |
|---:|---|---|
| 1 | Sections 13 and 15.4: the standard error behind the number X read as "the standard deviation, divided by the count". That is not a bootstrap standard error. It would make X far too small. | Amendment A4. The old sentence was unclear. Its words "divided by the count and not by the count minus one" were meant to say how the standard deviation itself is taken. They could be read as one more division. The text now says: the standard error is the standard deviation of the resampled ROLE-minus-better-rival differences, and nothing divides it by a count. |
| 2 | Intended change (1): a DeepSeek question writer would share a vendor with label team B, a key solver and the ordinary-note writer. | That change was not made. Amendment A1 keeps the question writer at Gemini, a third vendor. |
| 3 | Intended change (2): a Claude sub-agent carries the CAS definitions, so as support checker it would touch the rival notes. | That change was not made. Amendment A2 goes further: Gemini is the only checker, and the Claude fallback is removed. Amendment A3 states the same limit for the one place where a Claude sub-agent stays, the key solver. |
| 4 | The plan was not in step with the two intended changes. | Both intended changes were dropped. This plan, the constants and the file formats now name the services of A1 and A2 in every place. The dead fallback rule is deleted. |
| 5 | Sections 11.1 and 19.1: the two repair lines let sealed tools and programs change after derived files exist. | Amendment A5. Each repair line has a window. Outside it there is no repair: stop, report, a new reviewed plan version. |
| 6 | Sections 15.3 and 11.2: QUOTES-ONLY drops the role tags, the canon lines and the Mind and related-thing fields at once. So C5 can not show that the role names alone add something. | Amendment A6. Section 21 now says so. No group was added. |
| 7 | Section 15.4: two rows of the outcome table had the number 8. | Amendment A7. The codes are numbered 1 to 11, each number once. |

### 27.2 The twelve amendments

| # | Amendment, in short | What was done in this plan's files | Left for another file's fixer |
|---|---|---|---|
| A1 | Question writer: Gemini `gemini-3.5-flash-lite`. Up to 4 passages per call, seeded fixed order, each passage fenced and treated on its own. One model writes the practice set, the final set and the spare pass. REAL, measured 2026-10-05: 47 one-word calls were answered with no refusal; the daily cap is not known. On HTTP 429 the tool stops cleanly, keeps its checkpoint and resumes later. The model name of every reply is stored. | Section 10 Step 1; section 21; section 23 row D4. Constants: `outside_services.gemini_question_writer`. File formats: section 4. | `tools/ob_write_questions.py`. |
| A2 | Support checker: Gemini `gemini-3.1-flash-lite`, up to 12 notes per call, checkpoint and resume, model name stored. No Claude fallback. If Gemini refuses, the build waits. | Section 10 Step 7; section 22 question 21; section 23 row D6; section 24 items 13 and 33; section 26 rows 7 and 10. Constants: the fallback rule, its two timing constants and the fallback sheet header are removed. File formats: section 9, without the export and import commands. | `tools/ob_check_support.py`. |
| A3 | Key solvers stay: DeepSeek, asked for as `deepseek-chat`, and a Claude Sonnet sub-agent given text only. The Claude model id is pinned as `claude-sonnet-5-5`. The limit is stated: the sub-agent carries the CAS definitions; it only picks a letter. | Section 10 Step 4; section 21; section 23 row D5. Constants: `outside_services.claude_solver`. File formats: sections 6.4 and 6.5. | `tools/ob_solve_blind.py` (the import step stores the model name from the transcript). The operator reads that name from each transcript. |
| A4 | The standard error for X is the standard deviation of the resampled ROLE-minus-better-rival differences. No division by a count. | Sections 13 and 15.4; section 24 item 19. Constants: `tests.standard_error`, `missed_gain_x`. File formats: sections 17.9 and 18. | `optionb/job/analysis_b1.py`: its fixer checks the one function that works out every range and every standard error against this text. |
| A5 | Repair lines narrowed. `TR_TOOLS_REPAIRED` only while no final question exists. `6R_PROGRAMS_REPAIRED` only after a failed pre-check job and before any call to model B. Neither may change the plan, the constants, a brief, a threshold, a key, a task or a note. Each needs its review record. After the window: stop, report, a new reviewed plan version. | Section 11.1; section 24 item 29. Constants: `repairs`. File formats: section 15.2. | `tools/ob_seal.py` (refuses with `REPAIR_OUTSIDE_ITS_WINDOW`). |
| A6 | Section 21 states what C5 compares, and that a pass shows formatted role information, not role names alone. | Section 21. | None. |
| A7 | Outcome codes numbered 1 to 11, no number twice. The status table has the matching keys. Every count of codes agrees. | Section 15.4; section 21; section 24 item 18. Constants: `outcome_codes_in_checking_order`; `report_sentences.code_10` (it was `code_9`). File formats: sections 17.9 and 19. | `optionb/job/analysis_b1.py` (the new name of the sentence). |
| A8 | Left over from review round 1. (a) The question writer's tool must read the reserve block as the other two tools do. (b) Seal step 7 must read the pre-check receipt, need `precheck_kind` `SEALED_PACKAGE`, and check the seal file inside `source.zip`. | (a) Section 10 Step 6. Constants: `split.reserve_block_read_by`. File formats: section 7.1. (b) Sections 11.1 and 19.1. Constants: `seal.step_7_needs`. File formats: section 15.1. | (a) `tools/ob_write_questions.py`. (b) `tools/ob_seal.py`; the run sheet. |
| A9 | Every tool that calls an outside service stores, for every call, the model name from the reply. The DeepSeek alias fact is stated once. | Section 3 (the fact); sections 10, 11.1 and 25. Constants: `outside_services.model_name_rule`. File formats: section 0 and every call log. | `tools/ob_write_questions.py`, `tools/ob_check_support.py`, `tools/ob_solve_blind.py`, `tools/ob_write_ordinary_notes.py`. |
| A10 | The test on made-up data before seal step 1 is ordered: one CPU-only AWS job of kind `DEVELOPMENT_TEST`, at most two, cap 0.50 USD and 45 minutes each. | Sections 19.1 and 19.2; section 22 question 13; section 25; section 26 row 20. Constants: `aws.development_test_job`. File formats: section 20. | `optionb/dry/build_dev_package.py` (the builder of the made-up package); the pre-check kit; the run sheet. |
| A11 | Outside services: DeepSeek at most 4.00 USD in total, enforced by the tools as a token count; Gemini free tier. | Section 19.2; section 22 question 13. Constants: `outside_services.deepseek`. File formats: sections 0, 6.2 and 8.2. | `tools/ob_solve_blind.py`, `tools/ob_write_ordinary_notes.py`. |
| A12 | This section. The version stays 1.0. Section numbers did not change. | Section 27. | None. |

**Numbers that the amendments added.** Operator decisions: 4 passages per question call; at most 2 development-test jobs of at most 0.50 USD and 45 minutes each; at most 4.00 USD for DeepSeek. Worked out from the operator's price reading, as section 19.2 shows: 2,430,240 input tokens and 1,156,520 output tokens. REAL, as the operator reported it: 47 one-word calls to `gemini-3.5-flash-lite` with no refusal; two `deepseek-v4-pro` calls with 60,756 input and 28,913 output tokens for about 0.10 USD. NOT MEASURED: the daily caps of the two Gemini models; the price of `deepseek-chat`.

### 27.3 Amendment A13: the canonical sayings in the role notes

Amendment A13 does not come from the outside review. It comes from an owner ruling.

**The ruling.** On 2026-10-05, at about 08:55 PDT, the owner typed a ruling. The record is `OWNER_RULING_MIND_AND_COLLOQUIALISMS_20261005.json` (4,245 bytes, sha256 `a88d9fe8179f7c052e1c91f69bcdbcdff9745757b1e35cf2276dc1b714c1b024`). The owner's words, unchanged:

"MIND IS AN ENTITY, A BEING, ANYTHING THAT THINKS, MACHINE,HUMAN, ANIMAL, AI ETC.  POSITIVE AND NEGATIVE USE THE COLLOQUILISMS (SHOULD BE  IN LOCAL FILES) THE SAME ABOUT THE OTHER NOETICS"

The local file the owner means is `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`, Clarification 6, the section "Canonical colloquialism map".

**What kind of change A13 is.** The ruling is about labeling. It does not name the role notes of this test. A13 is the operator's reading of the ruling, applied to a place the owner did not name. The owner may strike it (section 22, question 22). Nothing was sealed and nothing had run. So the version stays 1.0. No section number changed.

| # | Amendment, in short | What was done in this plan's files | Left for another file's fixer |
|---|---|---|---|
| A13 | In the role notes that model B reads (groups ROLE and MIXED), each canon definition line is followed by one line with that Noetic's canonical sayings. The line is the word `Sayings`, a colon, one space, then the third cell of that Noetic's table row, copied character for character. In MIXED each swapped tag carries its own definition line and its own sayings line. QUOTES-ONLY, FILLER, the ordinary notes, the questions and every brief are unchanged. Nothing is retyped: the role-note tool reads the table when it runs, and refuses on a wrong file hash or when a definition cell differs from the guide. The file is the sixth sealed source of seal step 1. The owner's sentence about Mind is not printed in any note; it governs labeling only. | The top of this plan; sections 3, 6, 9, 10 (Step 7), 11.1, 11.2, 11.3, 19.2, 21, 22 (question 22), 23 (row D2) and 24 (items 34 to 36). Constants: `sources.canonical_sayings`, `sources.owner_ruling_mind_and_colloquialisms`, the sayings keys of `role_notes`, `role_notes.mixed_rule`, `role_notes.quotes_only_rule`, `forbidden_words.list_c`, `leak_screen.sayings_lines_in_the_frame_text`, `seal.sources_sealed_in_step_1`, `seal.sources_rule`, `seal.step_2_also_checks`. File formats: the top, and sections 3.1, 10.1, 12.1, 15.1, 18 and 20. | `tools/ob_role_notes.py` (reads the table; the three refusals; the sayings lines; the blanked text). `tools/ob_seal.py` (the sixth source in step 1; the check of step 2). `tools/ob_screen_notes.py` and `tools/ob_assemble.py` (each checks the head lines of a note). `optionb/dry/build_dev_package.py` and the dry fixtures (they call the role-note functions). A new dry run of the role notes for the two length figures below. |

**What A13 moves, by rules that did not change.**

- **Note length.** The Notes block of ROLE and MIXED grows. The ordinary notes are sized to the larger count by the rule of section 11.3.
- **The answer-leak screen.** The word `Sayings` and the sayings text are fixed frame words of a program-built note. REAL, checked on 2026-10-05: no sayings line holds the whole word `answer`, `option` or `correct`, and no letter pattern of rule (a) matches one (section 10, Step 7).
- **Questions.** Lists A and B still keep the special words of the canon lines out of every question and option. List C got ten words of the sayings, for the question sentence only: moth, flame, stomach, ten-foot, chord, resonated, groove, muscle, popped, clicked (section 9).

**Two length figures are to be measured again by the tool fixer.** Each is marked where it stands.

1. Section 10, Step 7, "Known risk of rules (c) and (d)": "about 2.6 times the passage length at the median".
2. Section 19.2, "EXPECTED need": "At the very most about half of each limit".

The tool fixer runs `tools/ob_role_notes.py` in dry mode on the real label files, into `optionb/dry/`, and replaces both. The plan fixer found no other figure in this plan that depends on the length of a role note. The constants hold the second figure too, under `outside_services.deepseek.spend_cap_expected`.

### 27.4 Small faults fixed together with A13

The amendment round ended with two last checks. Their record is `optionb/AMEND_1_RECORD.json`, blocks `confirm` and `walk`. Both verdicts were ACCEPT_WITH_NOTES, with minor findings only. From those findings, every fault that could stop, stall or corrupt a real run was taken. All rules below are PROPOSED.

| Fault found | Rule now in this plan's files | Left for another file's fixer |
|---|---|---|
| A tool crashed after it had saved its answers, because its output was not UTF-8 (walk, finding 1). | `FILE_FORMATS.md`, section 0: every laptop tool prints in UTF-8. | The four tools that do not set it: `tools/ob_check_questions.py`, `tools/ob_select.py`, `tools/ob_solve_blind.py`, `tools/ob_write_questions.py`. |
| The exit code did not mean the same thing in every tool (walk, finding 3). | `FILE_FORMATS.md`, section 0: four codes, one meaning in every tool. Only code 0 lets the next step start. | `tools/ob_write_questions.py`, `tools/ob_solve_blind.py`, `tools/ob_select.py`. The dry drivers that compare exit codes. |
| A note that comes back empty or cut off every time stopped the chain with no way on (walk, finding 9). | Section 10, Step 7: after two such replies the passage is dropped, with the status `DROPPED_NOTE_NOT_WRITTEN`. At most 3 passages of a set; one more stops the tool with `STOPPED_TOO_MANY_NOTES_NOT_WRITTEN`. Constants: `ordinary_notes.not_written_rule`, `ordinary_notes.not_written_guard` and `seal.step_4_needs`. File formats: sections 8.1, 8.2, 9, 9.5, 10.1, 11.1, 12, 15.1 and 18. | `tools/ob_write_ordinary_notes.py`, `tools/ob_check_support.py`, `tools/ob_screen_notes.py`, `tools/ob_assemble.py`, `tools/ob_seal.py` (step 4). |
| A plan-only run of the final question writer closed the tool-repair window one step early (walk, finding 2). | Section 11.1 and `FILE_FORMATS.md`, section 15.2: the final question writer is not run, not even with `--max-calls 0`, before the practice set is fully done. | The run sheet. |
| The operator could pick a smaller question batch by hand (confirm, finding 3). | `FILE_FORMATS.md`, section 4: a real run does not give `--batch-size`. | None. |
| The run sheet says the builder of the made-up package is not on disk (confirm, finding 6). | Not in this plan's files. | `optionb/controller_b1_draft/RUN_SHEET_B1.md`. |

Five points of the `confirm` block wait for an operator decision before seal step 1. They are findings 1, 2, 4, 5 and 9. None of them can stop a run. They are not decided here. Every other point of the two blocks was left as it is.

**Numbers that A13 and the small faults added.** REAL, measured on 2026-10-05: the sixth source has 64,154 bytes; the ruling record has 4,245 bytes; the table of sayings has 10 rows, and all 10 definition cells equal the guide. PROPOSED: two empty or cut-off replies, then the passage is dropped; at most 3 passages of a set dropped that way; ten more words in list C; four exit codes, 0 to 3. EXPECTED, not yet measured by the tool: the word target of an ordinary note is about 3.8 times the passage length at the median.
