# 09 — Label-agreement attempt 2: plan, version 2.0

This is a new attempt, not an edit of plan v1.2. Plan v1.2 and its sealed verdict (`verdict/`) stay as they are.

The first attempt ran on 428 passages. Only `^1` met its bars. The owner then gave a direction (`OWNER_DIRECTION_POINTING_AND_OPTION_B_20261005.json`): keep identifying which thing occupies each role; "Use a short, consistent identifying label PLUS the full supporting quote. Don't reduce everything to one word"; "Also count extra and missing roles separately".

The design is fixed in `design_v2/labeling_final.json`. It had one review round by three reviewers: 2 blocking and 21 major findings, each answered there. The build (guide, plan, programs) then had one review round of its own: 3 blocking and 19 major findings. Section 22 says what was done with each. This plan was written before any new passage or any new label exists. Nothing in it changes after labels are seen.

## 0. What is a proposal, and who signs

- **PROPOSED, not in force:** the two bars, the minimum counts, the hold table (eight codes), the outcome words and their order, the `^5` bar row, the nine conventions of guide rule 16, and the seal conditions S1 to S5. Also proposed, and on the same sheet: the seventeen working lines of guide section B5 (sheet item 9), and the rule that the practiced files are the sealed files (sheet item 10).
- They take effect only when the owner signs them. The owner signs on one sheet: `label_v2/OWNER_SIGNOFF_SHEET.md`.
- The signature must exist before any new passage is sealed. `tools/seal_v2.py` refuses to seal without the owner sign-off record (section 20).
- The build and the practice pass may go ahead before the signature.
- A failed bar is a failure. There is no "pass with notes". Outcome words come only from the program.
- This plan decides no question about what a definition covers. Every such question stays with the owner (section 19). What the teams do until the owner answers is not the same for every question. The owner should know which is which before signing:
    - **The owner's two open questions.** The entry is written and counted in its own row with no bar (uncertain pairs; conclusions reached by reasoning; clues).
    - **Eight held kinds.** The entry is written, marked held, and counted in its own row with no bar.
    - **Twelve more questions have no held row.** The fixed design closed the hold list at eight codes. For ten of these, both teams follow one working line of the guide inside the pass/fail rows. For some kinds that line says to write no entry at all. For the other two there is no working line, and the labelers may differ inside the pass/fail rows. So a pass or a fail for `^1` to `^9` is a result under those working lines. Each working line is on the sign-off sheet as item 9, so that the owner can strike it before the seal.
    - The rule this attempt was given says: every such entry is written, marked held, and counted in its own row. The working lines do not meet that rule in full. Meeting it in full needs new hold codes. That is a change of the fixed design, and this plan does not make it. It is held for the owner (section 19, question 27).

## 1. The question

For each Noetic `^1` to `^9`: can two independent label teams, from different model families, apply the canon definitions to unfamiliar, unmarked passages and write down the same roles? "The same role" means: the same thing, in the same Noetic, for the same Mind, pointing at the same place in the passage.

`^0` Idea is not scored (owner decision: it stays in the representation; every thing pointed to is an Idea).

What is new against plan v1.2:

1. An entry is a short identifying **label** plus the full **supporting quote**. For `^4` and `^7` it also has a **measure** (the how-much words, or the rate and pattern words).
2. Agreement is counted **entry by entry**. Extra roles and missing roles are printed in their own columns. One matching pair no longer makes a whole passage count as agreement.
3. Eight kinds that wait on an owner question are written, marked **held**, and counted in their own rows with no bar. Other open questions have no held row; section 0 and section 19 say what is done with them.

## 2. What the result can and cannot show

- It shows whether the labels are **consistent** between two teams. It does not show the labels are **right**. Agreement between two language models is not correctness. Two teams can agree and both be wrong, and two language models can share a bias.
- The passages are written by a language model, not found in the world. One writer model and clean passages make any result kinder than found text would be.
- Only two model families label (Claude and DeepSeek).
- A Noetic that misses a bar is "not labelable under this method". That is a statement about this guide and these teams. It is not a statement about CAS.
- The new count is harder than the old one. Old and new numbers cannot be set side by side.
- A pointing rule fixes pointing only. It does not make two teams agree on whether a role is there.
- Holding moves a disagreement out of the bar row. It does not make the teams agree. A pass then covers the clear entries only, and the report must say so in its scope line.
- A held kind gets a verdict only if the owner answers its question before the seal, or in a later attempt on new passages. A re-score after the labels is for reading only.
- A working line (sheet item 9) does the opposite of a hold. It keeps a kind inside the bar row, or leaves it unwritten, by a convention the owner has not confirmed. A pass or a fail for `^2` to `^9` is a result under those lines. It is not a result on the definition alone.
- The new set has a different mix of kinds from the first set. K1 was 60 of 440 passages (13.6%). It is now 140 of 760 (18.4%). A result describes this mix.
- The checker shapes the labels. Both teams get the same program with the same fixed messages, and it never sees the other team. Still, agreement after re-asks is agreement with help. The report gives the re-ask counts per team and per check.
- Every number in this plan that comes from the old labels is hindsight. It shows how the new count behaves. It is practice arithmetic, not a test of guide v2.0. Only the new sealed set is a test.

## 3. Frozen inputs

`tools/seal_v2.py` reads each file below, at the path shown or at a path named on its command line. It writes each file name and its sha256 into `SEAL.json` before any label team starts. The definitions are named by their commit. A sha256 is a fingerprint of a file's exact bytes: if one character changes, the fingerprint changes. To seal is to write down those fingerprints before labeling starts, so that nothing can be swapped later without it showing.

| Item | Value |
|---|---|
| Labeling guide | `02_LABELING_GUIDE_v2_0.md`. Part A (the ten definitions and the table of sayings) is byte-identical to Part A of `02_LABELING_GUIDE_v1_2.md`. Rule 15 is not edited. |
| Definitions | unchanged from `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 1, commit `1c8531ea` |
| Owner's working ruling on reading a sign | `OWNER_RULING_SIGN_READING_20261004.json`, applied as guide rule 15, as written |
| Owner's direction for this attempt | `OWNER_DIRECTION_POINTING_AND_OPTION_B_20261005.json` |
| This plan | `09_LABEL_AGREEMENT_PLAN_v2_0.md` |
| The checker | `tools/check_labels_v2.py`: one plain Python program, the same for both teams (section 6) |
| The scorer | `tools/verdict_v2.py`: one plain Python program; it computes every number and every outcome word (sections 7 to 11) |
| The hold table | the eight codes (section 9), and the file that sets each code to `open` for the verdict run (section 12): `label_v2/fixture/rulings/all_codes_open.json`. It is named on the seal command line with `--hold-table`. The seal tool checks that file: exactly the codes that are still held, each set to `open`. The scorer checks that a file given with `--ruling` is this sealed file. |
| The briefs | the constants in `tools/write_passages_v2.py`: brief text, forbidden words, kind texts, counts, settings, seeds |
| The fixture | the folder `label_v2/fixture/`: made-up passages, hand-made label sets and the expected output (section 13, part 2) |
| The labeler instructions | `label_v2/LABELER_INSTRUCTIONS.txt`: the fixed task text both teams get with the guide |
| The team A launch text | `team_a/TEAM_A_LAUNCH.txt`, written by the seal tool into the output folder (section 5). Its words are fixed in two hashed places: the frame in `tools/seal_v2.py` and the recipe in `tools/check_labels_v2.py`. |
| The team B labeling tool | `tools/label_outside_v2.py`. It holds the fixed words team B is sent around the guide and the instructions. |
| Owner sign-off record | the owner's pasted line, recorded as JSON (section 20). The line itself names the guide and the plan by fingerprint. |
| Also hashed into the seal | the two owner records above, the writer tool and the seal tool |

The same roles are written into `PRACTICE_SET.json` for a practice pass, so that practice labels can be tied to the files they were made with.

## 4. Passages

**New passages only.** The 428 old passages are spent: every rule of guide v2.0 was written after reading them. They may be used for tool dry runs, for part 1 of the program check, and as teaching examples. They are never scored for a verdict again.

**Writer, blind.** Gemini `gemini-2.5-flash`, the same writer as the first attempt. Tool: `tools/write_passages_v2.py`. The writer is neither label team. It gets a plain brief with no CAS words and the same list of twelve forbidden words. It never sees the guide, the definitions, the hold table, the checker, any label or any reader. The same writer is kept on purpose: then what differs from the first attempt is the guide and the measure. The label teams are never told the kind.

**How many.** 760 are written: nineteen for each of 40 new settings, in a fixed seeded order. Last time 12 of 440 were dropped by the mechanical check. So about 739 should be kept (ESTIMATE).

**Kinds of moment asked for.** The writer is told the kind in plain words.

| Kind | Plain description given to the writer | Verdict set | Practice pass | Meant to give cases of |
|---|---|---:|---:|---|
| K1 | something noticed brings a quite different thing into a person's thoughts | 140 | 18 | `^8`, `^9` |
| K2a | a person is plainly drawn toward one thing and plainly put off by another thing, shown through what they do or feel | 120 | 18 | `^2`, `^3` |
| K2b | something lands on them either very strongly or hardly at all | 80 | 18 | `^4` |
| K3 | what a person has lived or learned over years shapes how they take something now | 60 | 6 | `^5` |
| K4 | someone takes a thing apart into named pieces | 70 | 18 | `^6` |
| K5 | the same thing over and over on a schedule has changed how a person acts | 100 | 18 | `^7` |
| K6 | an experienced person notices a small sign and knows what it means | 30 | 6 | the ruled-on case (rule 15); no bar |
| K7 | a person works through clues step by step to a conclusion | 30 | 15 | reasoning roles (rule 15b); no bar |
| K8 | purely physical description, no person's thoughts | 80 | 3 | "none of these"; passages with no Mind at all |
| K9 | a person does ordinary things; nothing of likes, memories or habits is shown | 20 | 0 | `^1` only |
| K10 | free: a person at work in the setting; the writer chooses what happens | 30 | 0 | roles that turn up unasked |
| Total | | 760 | 120 | |

- The exact words sent to the writer are the constant `KINDS` in `tools/write_passages_v2.py`. For K1 and K3 to K9 the table above gives the short description of plan v1.2; the words sent are the strings of the first attempt's tool, character for character.
- K2a and K2b are the two halves of the first attempt's K2 string, cut at "; and", character for character. They are shown in full in the table. The old K2 asked for three things in one passage.
- K10 is new, and is shown in full in the table.
- The tool proves the first two statements at every start, by sha256 against the first attempt's strings. It refuses to run if one differs.
- The briefs are not tuned toward the new rules. That would make the test easy.
- Each of `^2` to `^9` is asked for in at most 140 of the 760. So 50 absences are safe.

**Why these counts.**

- K1 is 140 (it was 60) and K2a is 120. For the rows expected near 0.80, the outcome word would otherwise be decided mostly by which passages happened to be written. More K1 also keeps the bar rows of `^8` and `^9` larger than their uncertain rows, which the withheld-pass rule needs (section 10).
- K5 at 100 and K2a at 120 guard `^7` and `^3`. Their bar rows shrink when held kinds are taken out. If a bar row still has fewer than 50 cases, the outcome is `NOT_ENOUGH_CASES`. It is not repaired afterwards.
- K8 is 80 (it was 60). Last time `^1` had exactly 55 passages where neither team marked a Mind. That is close to the floor of 50.
- K10 keeps the test from being only stock phrasing. Roles that turn up unasked were the worst cases last time.

**The 40 new settings of the verdict set.** a hardware store; a car wash; a pharmacy counter; a bowling alley; a paint factory; a sawmill; a blacksmith's forge; a glassblowing workshop; an upholstery workshop; a candle workshop; a campsite; a registry office; a cinema projection booth; a zoo's reptile house; an ice rink; a fire station; a lost property office; a railway signal box; a canal lock; a petrol station; a supermarket checkout; a butcher's shop; a coffee roastery; a brewery; a flour mill; a mushroom farm; an archaeology dig; a horse stable; a driving school car; a planetarium; a weather station; a bottling plant; a motorway service station; an optician's shop; a blood donation centre; a bank branch; a toy shop; a climbing wall; a jeweller's workshop; a brickworks.

**The 6 new settings of the practice pass.** a chocolate factory; a furniture removal van; an auction house; a tennis club; a water treatment plant; a tea room.

**6 settings held back.** They are used only if a second practice pass is needed (section 14), so that its passages are new: a paper mill; a picture framing shop; a snooker hall; a soap workshop; a dance school; a youth hostel.

**None of these 52 was used before.** The 60 settings of the earlier rounds are:

- First look (10): a restaurant kitchen; a hospital ward; a small repair garage; a secondary school; a small farm; a software team's office; a street market; a long train journey; a family home on a weekend; a rehearsal room for musicians.
- Practice rounds 2 and 3 (10; round 3 relabeled the round 2 passages): a fishing boat; a public library; a construction site; a bakery before dawn; a call centre; a veterinary clinic; a village bus route; a pottery studio; a laundromat; an airport gate.
- First verdict set (40): a lighthouse; a dental surgery; a night bus depot; a flower stall; a boxing gym; a recording studio; a mountain hut; a post office sorting room; a hotel laundry; a vineyard at harvest; a tailor's shop; a river ferry; a university laboratory; a care home; a bicycle workshop; a fish market; a courtroom corridor; a radio newsroom; a greenhouse; a quarry; a school canteen; a locksmith's van; a harbour crane cabin; a puppet theatre; a cheese cellar; a customs desk; a chess club; a wind farm control room; a barber shop; a dairy at milking time; a museum storeroom; a taxi rank at night; a scrapyard; a nursery school; a ski lift station; a print shop; a beekeeper's yard; a swimming pool; a shoe repair kiosk; a warehouse loading bay.

MEASURED by a small script on 2026-10-05: no new setting is the same string as an old one.

**Seeds and fixed order.**

| What | Seed | sha256 of the fixed job list (setting and kind of every passage, in order) |
|---|---|---|
| Writer order, practice pass 1 | 20261011 | `a20aa9af008044a738b9d0b6285493f67fedcec712185974bf6265fe1627f166` |
| Writer order, practice pass 2 | 20261012 | `5b630b4cad9a314bb006227975e9c7199552ee8821aaeb0cf657909544551216` |
| Writer order, verdict set | 20261013 | `a7068c8fc92d1170e87941cb528fe67a3601e545c9170958b196f2f5048898bc` |
| Seal shuffle, practice pass 1 | 20261021 | |
| Seal shuffle, practice pass 2 | 20261022 | |
| Seal shuffle, verdict set | 20261023 | |
| Intervals (section 10) | 20261006 | |
| Role-shuffle floor (section 11) | 20261007 | |
| The owner's reading sample (section 11) | 20261008 | |

The writer tool refuses to run if its job list does not have the hash above. The last three seeds are constants of the scorer (`SEED_INTERVALS`, `SEED_SHUFFLE`, `SEED_OWNER_SAMPLE`). The scorer prints them in its report.

**How the writer runs.** 30 passages per call: 4 calls for a practice pass, 26 calls for the verdict set. The tool reads `GEMINI_API_KEY` from the environment and opens no key file. It saves after every call and goes on where it stopped when run again. The free tier allows about 20 requests per day on this key. The tool counts its own requests and stops cleanly at 18 in any 24 hours, or when the service says the quota is used up. So writing the 760 takes at least two days on the free tier (ESTIMATE).

**Mechanical checks only, before sealing.** Tool: `tools/seal_v2.py`. A passage is dropped if it holds a forbidden word, has fewer than 30 or more than 120 words, or repeats another passage exactly (in this set, or in an earlier set named on the seal command line). Drops are counted and listed with their reason. Nobody reads the passages to choose among them.

**Seal.** The kept passages are shuffled with the fixed seed and get new ids `Y001…`. The tool writes `SEAL.json` with the sha256 of the passages, the guide, this plan, the checker, the scorer, the hold table, the briefs, the fixture, the labeler instructions, the team A launch text and the team B labeling tool. The tool refuses to seal:

- if the folder is already sealed, or any label file exists there;
- if no owner sign-off record is named on the command line, or the file does not exist, or the owner's pasted line cannot be read, or the line was signed against another guide or plan than the ones being sealed (section 20);
- if a seal condition S1 to S5 is not met, or the practice report is not tied to the files being sealed (section 14);
- if the hold table file is not exactly the codes that are still held, each set to `open`;
- if a signed value, as proposed or changed by the owner, is not the value the scorer and the checker hold (section 20);
- if a frozen file is missing, or the writer's state is not the finished 760 of this plan.

**The kinds are kept apart.** The file that says which kind each passage was written for (`passages_kinds_HIDDEN_FROM_LABELERS.json`) is not written into the folder that holds the passages and the team A chunks. The seal tool writes it into a folder of its own (`<output folder>_HIDDEN_FROM_LABELERS`, or the folder named with `--hidden-dir`). It refuses a kinds folder that is the output folder, inside it, or around it. No label team is ever pointed at that folder.

Practice passages get ids `PA001…` (pass 1) or `PB001…` (pass 2). Their passage file is `passages_practice.json`. Their record is `PRACTICE_SET.json`. It is not a seal and needs no signature: its schema is the practice-set schema and it says `"is_a_seal": false`. The scorer's verdict mode refuses it.

## 5. Label teams

The two teams are unchanged from the first attempt, for comparability.

| Team | Who | How | Is given |
|---|---|---|---|
| A | Claude (Sonnet) sub-agents | about 50 passages each, working apart: about 15 sub-agents for the verdict set, 3 for the practice pass | the team A launch text; guide v2.0; the labeler instructions; its own passage file (one chunk); the checker's messages on its own records; nothing else |
| B | DeepSeek `deepseek-chat` | one passage per call, temperature 0 | one fixed head line; guide v2.0; the labeler instructions; that one passage; the checker's messages on its own record; nothing else |

Both teams get the same checker, with up to three tries per passage. Neither team sees the other's labels, the kinds, the writer's brief, the old labels or the practice rounds.

**The exact words each team is given are fixed and hashed.**

- **Team B.** The words around the guide and the instructions are constants of `tools/label_outside_v2.py`: the head line, the request and the try-again line. The tool writes their hash into its receipt. The tool's own sha256 is in `PRACTICE_SET.json` and in `SEAL.json`.
- **Team A.** The seal tool writes one launch text, `team_a/TEAM_A_LAUNCH.txt`, into the output folder. It writes its sha256 into `PRACTICE_SET.json` or `SEAL.json`. The launch text is built from two fixed pieces. One is a frame that is a constant of `tools/seal_v2.py` (`TEAM_A_LAUNCH_FRAME`). The other is the recipe for the three tries, a constant of the checker (`TEAM_A_RECIPE`; `check_labels_v2.py --recipe` prints it). A team A labeler is never told to open the source of a program.
- **The start line of team A.** A team A sub-agent is started with one line of this fixed form, and with nothing else: `Read the launch text <TEAM_A_LAUNCH.txt> and do what it says. Guide: <the labeling guide>. Instructions: <the labeler instructions>. Passages: <your chunk file>. Work folder: <your work folder>. Try log: <your try log>.` Only the six paths differ from one sub-agent to the next.
- **A limit.** The three tries of team A rest on the sub-agent following the recipe. The checker counts every run with `--tries` as one try. The labels file is written from the try logs, not from the records. But a sub-agent that looked at its record in some other way would have had a free look, and no program can see that.

**The team B model name is not confirmed.** The first attempt used the name `deepseek-chat`. READ on 2026-10-05 through a page-fetch tool, and not checked by a second reading: the service's price page no longer lists a model of that name. It lists `deepseek-flash` and `deepseek-v4-pro`. Whether the service still accepts the name `deepseek-chat`, and which model then answers, is NOT KNOWN from that page. The first practice call will show it: the team B tool stops by itself when the service rejects a model name. If the name is rejected, the team B model is the owner's choice, and nothing is labeled until the owner has made it. The model name is fixed before the first practice label and is the same for the practice pass and the verdict set.

## 6. The entry and the checker (summary; the guide and the checker are the authority)

**One entry = one thing, in one role, for one Mind.** Every quoted field is an exact copy from the passage, one unbroken stretch.

| Field | What it holds |
|---|---|
| `noetic` | `^1` to `^9` |
| `mind` | the label of this team's own `^1` entry for that Mind; empty only for `^6` |
| `label` | the short identifying name of the thing, 1 to 12 words, inside the support; never a naming phrase cut down to its bare noun |
| `support` | the full supporting quote: whole sentences, at most 4; it holds the label and the measure |
| `measure` | only for `^4` (the how-much words) and `^7` (the rate and pattern words) |
| `relative_to` | `^8`: the label of its `^9`. `^9`: the label of its `^8`. `^6`: the whole. Empty for the others |
| `certainty` | `clear`, `ambiguous` or `held` |
| `other_candidate` | only with `ambiguous`: `^n`, `none` or `reasoning` (rule 15d) |
| `held_under` | only with `held`: one of the eight codes |
| `reached_by` | `reasoning`, only on a `^9` under rule 15(b) |
| `clue` | true, only on a `^6`, in a passage where this team wrote a `^9` reached by reasoning |
| `no_fuller_name` | true, only when no noun anywhere in the passage names the thing |

**The checker.** `tools/check_labels_v2.py`. Plain Python, no model. It runs on one team's output for one passage. It never sees the other team. It has one check of the record as a whole (R0) and nine checks of the entries, C1 to C9: allowed values; exact copies; label length and place; measure; Mind; related thing; pointers ("This smell" is not a label); no duplicates; and one re-ask when a `^2` or `^3` label names a feeling. A re-ask shows the passage, the team's own entry, the names of the failed checks and a fixed message.

**Form lines added after the review of the build** (guide section B1, "How the fields go together", and B2). A `^9` reached by reasoning has no related thing, is never held, and is never the partner of a `^8`. A clue has no whole and is always clear. `mind` is empty in every `^6`, and only there. One thing gets one entry whatever the certainty: the same thing written once clear and once held, or once as a clue and once as a plain part, is a duplicate under C8. An optional field with an empty value is read as left out. The checker and the scorer both apply these lines.

**Drops.** An entry that still fails C1 to C8 after the third try is dropped. A dropped entry does not vanish. If its Noetic and certainty are valid, it stays in its row as an unmatched entry of that team, with the reason `DROPPED`. It can never be matched.

**A failing entry that the labeler leaves out is put back.** A labeler could answer a re-ask by leaving the failing entry out. The entry would then be in no row and in no drop count. So the checker keeps every entry that failed C1 to C7 on a try that was sent back. When the record becomes final and holds fewer entries of that Noetic, the checker puts the missing failed entries back, marked as dropped and as "removed after re-ask". They stay in their row and in the dropped share like any other dropped entry. Not put back: an entry whose own checker message says the labeler may remove it. The checker has two such messages: a repeated entry (C8), and a `^8` that names a `^9` reached by reasoning (rule 15b says "Do not mark `^8`"). Table 5 counts the put-back entries per team, per check and per Noetic.

## 7. How two entries are matched (summary; the frozen scorer is the authority)

The scorer is `tools/verdict_v2.py`. It is plain Python with no model. It computes every number and every outcome word. Its sha256 is in `SEAL.json`. The full text of the method is in `design_v2/labeling_final.json`, field `matching_algorithm_precise`. If this summary and the frozen scorer differ, the scorer is what runs, and the difference is reported as a defect.

**The gate of verdict mode.** The scorer prints an outcome word only for a sealed set. Before it scores anything it must refuse, and score nothing, in each of these cases:

- The record is not a seal: it does not have the seal schema, or `"is_a_seal"` is not true, or it holds no owner sign-off record with a sha256 and a decision for the signed items, or no record of the seal conditions, or no sha256 of the hold table. A practice-set record is refused. So is a hand-made record. The layout of the first attempt's seal is no longer read.
- The guide, the plan, the checker, the scorer or the passages do not have the sha256 the seal names.
- A value the owner signed is not the value the scorer holds. A hold code the owner ruled on is still in the scorer.
- A file given with `--ruling` sets every code to `open` but is not the sealed hold table.
- A label file does not hold exactly one final row for every sealed passage (section 21).
- A label file did not go through the sealed checker: the scorer loads the sealed checker and runs it again on every final record. An entry that fails C1 to C8 and is not marked dropped is a refusal.
- A team's receipt does not name the sealed checker, guide and passages. Or the two label files are the same file.

The report header prints the sha256 of the sign-off record and the items the owner changed or struck.

**The matching steps.**

1. **Clean-up.** Curly quotes become straight quotes. Every run of white space becomes one space.
2. **Words.** A word is an unbroken run of letters and digits, lower-cased. A content word has 2 or more characters and is not one of the 34 filler words of `tools/verdict.py`.
3. **Sentences.** A sentence ends after `.`, `!` or `?` followed by a space or the end. A full stop after Mr, Mrs, Ms, Dr, St, Prof, Sr, Jr, No, vs, etc, e.g or i.e does not end a sentence.
4. **Places.** Each field is located in the passage. A `^1` label is located at the first place the name occurs in the passage, whatever the support. Every other label is located inside its support.
5. **The same thing.** Two labels are the same thing when they share at least one content word at the same place in the passage, and their first words are at most 2 words apart. Where a label stops is free.
6. **The same reading.** Two entries are the same reading when they are in the same passage and the same row, and: the labels are the same thing; the Mind is the same (not asked for `^1` and `^6`); the related thing is the same (`^6`, `^8`, `^9`); the measures overlap (`^4`, `^7`). The supports are never compared.
7. **One-to-one pairing.** Per passage and per row, the scorer finds the largest possible set of pairs. Each entry is used at most once.
8. **Counts.** A = team A's entries in the row. B = team B's entries. M = pairs. only A = A - M. only B = B - M.
9. **One reason for every unmatched entry.** The first that applies: `DROPPED`, `STATUS`, `FIELD`, `MIND`, `START`, `OTHER_LABEL`, `OTHER_NOETIC`, `FACES_A_DROP`, `OTHER_THING`, `ABSENT`. Reasons describe. They never change a count.
10. **Pointing ceiling.** After pairing, leftover entries of the two teams are paired once more when they differ only by pointing. That gives the line "what agreement would be with perfect pointing". It counts toward no bar.

Fixed constants: start tolerance 2 words; label 1 to 12 words; support at most 4 sentences; three tries per passage.

The scorer gives old labels no lift. MEASURED by the designer on the old labels (the middle value of each triple was re-run by the plan writer; the other two were not): entry agreement at start tolerance 0, at 2, and with no start rule is `^2` 0.526 / 0.559 / 0.629; `^5` 0.388 / 0.447 / 0.563; `^6` 0.308 / 0.381 / 0.402; `^7` 0.227 / 0.296 / 0.328; `^8` 0.456 / 0.472 / 0.541; `^9` 0.430 / 0.478 / 0.529. So any gain in the new attempt has to come from the teams following the guide.

## 8. What counts: bar rows and no-bar rows

**Kept from plan v1.2.** Only cases count, never passages where neither team marked the Noetic. Only clear entries count toward a bar. The Mind and the related thing must agree.

**Bar rows: `^1` to `^9`.** A bar row holds the clear entries of that Noetic. It does not hold a `^9` reached by reasoning, a `^6` clue, a held entry, an ambiguous entry or an uncertain entry. Dropped entries that have a valid Noetic and certainty stay in the row.

**The `^5` bar row (PROPOSED).** The bar is on `^5` as the labelers wrote it. The program adds one `^5` entry beside each clear `^7` (a "twin"). Those twins are not in the bar row. The row "`^5` with twins" is printed beside it with no bar. Reason: whether exposure alone is `^5` is open with the owner, and the row without twins does not depend on the answer. The owner may choose the other row as the bar row, before the seal. The scorer holds the choice as the constant `FIVE_BAR_ROW`: `without_twins` (proposed) or `with_twins`. The seal tool compares it with what the owner signed under sheet item 6.

**Rows with no bar.** Each is printed with A, B, M, only A, only B and E:

- "`^9` reached by reasoning" (rule 15b);
- "uncertain `^8`" and "uncertain `^9`" (rule 15d);
- "`^6` clue";
- "ambiguous `^n`";
- "`^5` with twins";
- "held `^n`" for each Noetic that has codes, with one line per code, and, for matched held pairs, how often the two codes agree.

## 9. The hold table (PROPOSED; eight codes; the list is closed)

A held kind is written in full, marked `held`, and counted in its own row. It never counts as clear. A clear entry from one team against a held entry from the other is a miss in both rows. These kinds wait on the owner. The table does not say what any definition means.

| Code | Noetic | The kind, in plain words | Example |
|---|---|---|---|
| H2-COMFORT | `^2` | A thing only gave the Mind a good feeling. No affinity is aimed at it and no move toward it is shown. | "Its simple presence offered a small sense of comfort." |
| H3-NOPULL | `^3` | A thing only failed to draw the Mind. Nothing against it is stated. | "held little appeal" |
| H3-BORED | `^3` | A thing only bored the Mind. | found it "tedious" |
| H5-ROLE | `^5` | A role with an experience word, and nothing said of what was lived or learned. | "the seasoned barber" |
| H7-RESULT | `^7` | The Mind now does a thing without thinking, and no rate words are given. | "Without thinking, he adjusted the ear defenders over his ears." |
| H7-NOEFFECT | `^7` | Rate words are given, and nothing is said of what the exposure did to the Mind. | "Finally, she misted it daily." |
| H7-UNBROKEN | `^7` | Exposure with no break, and no rate words. | "The constant hum of the industrial dryers had become a quiet backdrop to her thoughts" |
| H89-FOLLOWS | `^8`, `^9` | A memory or a picture simply follows something noticed, with no bringing words. | "Thomas observed the young skier struggling with the boarding gate. He remembered his own clumsy attempts decades ago." |

If the owner answers a held question **before** the seal, the code is removed from the guide, the checker, the scorer and the hold table file, and the kind enters this verdict as clear or as nothing. The seal tool refuses while one of the two programs still holds a code the owner ruled on.

If the owner answers **after** the seal, the kind gets no pass and no fail in this attempt. The same labels can be counted again under the ruling, for reading only: every row then prints `REPORTED_ONLY_NO_BAR` (section 12). A verdict for that kind needs new passages.

## 10. Measures, proposed bars, outcome words

**The counts,** per Noetic, over the entries of the bar row: A, B, M, only A, only B (section 7). There is no answer key. So "extra for one team" and "missing from the other" are the same entries. Each is printed once.

**Primary measure: entry agreement.** E = M / (M + only A + only B). In plain words: of every role either team wrote down, the share both wrote down, for the same Mind, pointing at the same place.

Always printed beside it: team A's share matched (M / A); team B's share matched (M / B); and fully matched cases (cases where no bar-row entry of either team is left over).

**Presence measure (unchanged from v1.2).** Cohen's kappa on "this passage has at least one bar-row entry for the Noetic", over all analysed passages. Kappa is agreement after taking away the agreement that chance alone would give.

**Minimum counts (unchanged from v1.2).** A case is a passage where at least one team gave a bar-row entry. A Noetic needs at least 50 cases, and at least 50 passages where neither team gave one.

**PROPOSED BARS.** E at least 0.80. Kappa at least 0.60.

- Why E at 0.80. E is the entry-by-entry twin of the old measure. Keeping 0.80 on E keeps the bar from getting easier while the count gets stricter. E at 0.80 also forces both teams' shares to 0.80 or more.
- The easier choice is 0.80 on each team's own share. That lets E fall to 0.667. The owner sets the number.
- Kappa is a weak gate here. On the old labels `^4` passes it at 0.677 while its entry agreement is 0.378. Nobody should read a kappa pass as agreement on presence.

**OUTCOME WORDS (PROPOSED), computed by the program in this order.**

1. `NOT_ENOUGH_CASES`: fewer than 50 cases or fewer than 50 absences.
2. `NOT_LABELABLE_UNDER_THIS_METHOD`: E below 0.80 or kappa below 0.60.
3. `NO_VERDICT_WAITING_ON_OWNER` (new word): both bars are met, but more entries of this Noetic sit **outside** the bar row than inside it. Outside = every entry of that Noetic in the held rows, the uncertain row, the ambiguous row, the row "`^9` reached by reasoning" and the row "`^6` clue", counted as matched + only A + only B in each. Inside = M + only A + only B of the bar row. This rule can only take a pass away. It can never turn a failure into anything else.
4. `LABELABLE_UNDER_THIS_METHOD`: otherwise. The line must print its scope: "clear entries only; N entries held under codes ...; N clue entries; N uncertain entries; N reached by reasoning; N ambiguous; N dropped; not covered".
5. Every other row: `REPORTED_ONLY_NO_BAR`.

The outcome uses the measured values. A failed bar is a failure.

**The constants, as the scorer holds them (PROPOSED).** This table quotes the constants block at the top of `tools/verdict_v2.py`. The plan and that block must say the same.

| Constant | Value | What it is |
|---|---|---|
| `BAR_ENTRY_AGREEMENT` | 0.80 | entry agreement E must be at least this |
| `BAR_KAPPA` | 0.60 | kappa on presence must be at least this |
| `MIN_CASES` | 50 | fewer cases: `NOT_ENOUGH_CASES` |
| `MIN_ABSENCES` | 50 | fewer passages where neither team marked it: `NOT_ENOUGH_CASES` |
| `MAX_UNLABELED_SHARE` | 0.05 | a larger share of passages not labeled by both teams: the run is invalid |
| `MAX_DROPPED_SHARE` | 0.05 | a larger share of one team's entries dropped: the run is invalid |
| `START_TOLERANCE_WORDS` | 2 | two labels are the same thing only if they start at most this many words apart |
| `RESAMPLES` | 2000 | whole-passage resamples for every 95% interval |
| `SEED_INTERVALS` | 20261006 | seed for the resamples |
| `SHUFFLE_ROUNDS` | 300 | rounds of the role-shuffle floor |
| `SEED_SHUFFLE` | 20261007 | seed for the role-shuffle floor |
| `SEED_OWNER_SAMPLE` | 20261008 | seed for the owner's reading sample |
| `SEAL_S2_MAX_DROPPED_SHARE` | 0.05 | S2: each team must be under this on the practice labels |
| `SEAL_S4_KIND` | K1 | S4 is read on practice passages of this kind |
| `SEAL_S4_MIN_E` | 0.80 | S4: entry agreement for `^8` and for `^9` at least this |
| `SEAL_S5_MIN_WHOLE_SHARE` | 0.80 | S5: share of `^6` part matches that also match on the whole |
| `FIVE_BAR_ROW` | `without_twins` | the `^5` row that carries the bar (sheet item 6); the other value is `with_twins` |
| `BAR_ROW_5_WITH_TWINS` | false | the same setting read as true or false; it follows `FIVE_BAR_ROW` and is never set by hand |
| `HOLD_CODES` | the eight codes of section 9 | each code with the Noetic it may sit on |
| the five outcome words | as listed above | |

Why rule 3 counts all rows outside the bar row. MEASURED on the old labels: `^8` has 89 entries in the bar row and 99 outside. `^9` has 90 in the bar row and 143 outside. For every other Noetic the bar row is the larger one. So on a set shaped like the old one, `^8` and `^9` could not pass. The 140 K1 passages are meant to prevent that. They lower the risk. They do not remove it.

**Intervals.** Entries inside one passage are not independent. So the 95% intervals for E, for both shares and for kappa come from resampling whole passages 2,000 times with seed 20261006, taking the 2.5% and 97.5% values. Resampling means: draw the same number of passages at random from the set, with repeats allowed, and compute the number again. The report says plainly when an interval reaches below a bar. Near 0.80 the interval is about plus or minus 0.07 for `^8` and `^9` (ESTIMATE). The outcome word still follows the measured value, as in plan v1.2. What a pass should be called when its interval reaches below the bar is a question for the owner (section 19).

## 11. Extra and missing: what the report prints

A passage is never called agreed because one pair matches. The only passage-level agreement number is "fully matched cases". The program writes all tables.

**Table 1,** one line per bar row. Columns in this order: Noetic; cases; absences; entries A; entries B; matched (M); only A (extra for A, missing from B); only B (extra for B, missing from A); entry agreement E with 95% interval; A share matched with interval; B share matched with interval; fully matched cases; cases with a match and leftovers (what the old score called agreement); cases with no match; kappa with 95% interval; dropped entries kept in the row, A; the same, B; entries outside the bar row (held, uncertain, ambiguous, reasoning, clue), A and B; outcome word and its scope line.

**Table 2,** two lines per Noetic (team A, team B): why each unmatched bar-row entry was unmatched. Columns: Noetic; team; entries; unmatched; `DROPPED`; `STATUS`; `FIELD` (split: related thing, measure); `MIND`; `START`; `OTHER_LABEL`; `OTHER_NOETIC` (with the count per other Noetic); `FACES_A_DROP`; `OTHER_THING`; `ABSENT`. Every unmatched entry is in exactly one cell. Under each line, five sums:

- pointing: `FIELD` + `START`, plus `OTHER_LABEL` for `^6`, `^8`, `^9`;
- same evidence, other label: `OTHER_LABEL` for `^2`, `^3`, `^4`, `^5`, `^7` (not called pointing);
- presence: `STATUS` + `OTHER_THING` + `ABSENT`;
- role mix-up: `OTHER_NOETIC`;
- format: `DROPPED` + `FACES_A_DROP`.

**Table 3,** one line per no-bar row (section 8) and one line per hold code. Columns: row; entries A; entries B; matched; only A; only B; E; of the unmatched, how many the other team wrote as clear; for matched held pairs, how many carry the same code.

**Table 4,** the checks on the measure, all with no bar:

- all pointed entries (clear and held entries of a Noetic pooled; it shows that holding is not hiding a disagreement);
- the pointing ceiling, two lines;
- E at start tolerance 0 and with no start rule;
- the old view: cases with at least one matched pair; the v1.2 word test; exact-same-span;
- the role-shuffle floor: the Noetic symbols among team B's entries are shuffled inside each passage 300 times with a fixed seed, and E is computed again. It is the cheapest baseline;
- the `^4` row without entries whose measure holds a word from this fixed list: no, not, never, none, nothing, unheard, unnoticed, unseen, unfazed, unaffected, ignored, background;
- for `^6`: matches on the part alone, with the whole ignored.

**Table 5,** health: per team and Noetic the median and the largest label length in words and support length in sentences; pairs whose label starts differ by 1 or 2 words; labels with more than one candidate place; re-asks and drops per check (C1 to C9) and per Noetic; entries put back after the labeler left them out, per check and per Noetic; `no_fuller_name` uses; for `^1`, how many unmatched Minds carry no other entry (bystanders).

**Guide-problem reports.** Every `guide_problem` a labeler wrote is listed with its passage and team. Reports that start with the words "Saying against rule:" are counted apart. They show how often a saying of Part A pointed to a Noetic while a numbered rule said to write no entry (guide rule 14; sheet items 9b, 9e and 9q).

**Table 6:** Tables 1 and 2 broken down by the writer's kind (description only). Also: agreement on "none of these".

**Listing.** One line per unmatched entry: passage id, team, row, label, support, reason, and the other team's nearest entry. So the owner can read any miss.

**The owner's reading sample,** drawn with a fixed seed: 30 unmatched entries (15 per team, spread over the reasons), 20 fully matched passages, and up to 20 `FIELD`, `START` or `OTHER_LABEL` pairs side by side.

**Output for option B.** The program also writes every matched bar-row pair to one file: both teams' label, support, measure, Mind and related thing. Held, unmatched, uncertain, clue and dropped entries are not in that file as settled.

## 12. When the whole verdict is invalid; rules of conduct

**Invalid** (kept from plan v1.2):

- more than 5% of passages could not be labeled by one of the teams after three tries; or
- more than 5% of a team's entries were dropped (dropped entries that stay in a row and dropped entries that fit no row, together).

An invalid verdict is reported as invalid. It is not repaired by relabeling the same passages.

**Not finished is not the same as not labeled.** "Could not be labeled after three tries" means exactly that: the team used its three tries on the passage, and the third gave no record that can be read. A passage that was never sent to a team, or whose tries are not used up, is not such a passage. It is open. The scorer does not score a sealed set while one passage is open for one team: it refuses (section 21). The checker's switch `--close-unfinished` is never used on a sealed set. If a run cannot be brought to a final state for every passage, the attempt is reported as INVALID, with the reason. It is not scored on the passages that happen to be done. This is fixed now, so that nobody can choose after a first look at the scores whether to finish, to close or to leave out the open passages.

**Rules of conduct.**

- No guide change, no relabeling, no dropped passage and no changed bar after labels are seen.
- A new attempt needs new passages and a new plan version.
- The frozen scorer computes every number and every outcome word. The operator reports its output.

**Owner-ruling input (declared now).** The scorer reads one file that sets each hold code to `open`, `counts` or `does_not_count`. The verdict run uses `open` for every code that is still held (all 8, unless the owner ruled on one before the seal). That file is the hold table file of section 3, and its sha256 is in the seal. When a file is given to the scorer with `--ruling`, the scorer compares it with the sealed one. A file that sets a code to `counts` or `does_not_count` is a re-score, never a verdict.

- `open`: held entries with that code stay in their held row.
- `counts`: every held entry with that code is treated as a clear entry of its Noetic.
- `does_not_count`: every held entry with that code is taken out of all rows. A clear entry of the other team that faced it stays in the bar row as that team's unmatched entry, tagged "clear against a kind ruled out".

A re-scored report prints `REPORTED_ONLY_NO_BAR` for every row. It never prints `LABELABLE` or `NOT_LABELABLE`. A verdict under an owner ruling needs new passages and a new plan version. Reason: there are 6,561 settings of the 8 codes, and one picked after the held rows are seen is a choice made after results.

## 13. Checks of the program before the freeze

Five parts. Parts 1 to 4 are seal condition S1: the candidate checker and scorer must print exactly what this section and the frozen file `label_v2/fixture/FIXTURE_EXPECTED.json` say. Part 5 is the practice labels. Parts 3 and 4 were added after the review of the build.

**Part 1, the old labels.** The candidate scorer is run on both teams' old labels of the 428 old passages, converted by one fixed mapping:

- label from old `words`;
- for `^4` and `^7`: label from old `relative_to`, and measure from old `words`;
- a `^6` with an empty whole goes to the clue row;
- an entry whose label cannot be found is left out;
- a converted entry has no support. Each field gets exactly one place: its first place in the passage with word edges, or, if there is none, its first raw place. For the `^6` whole: the place nearest before the part;
- the checker is not run.

It must print these nine rows. The check is on the counts, and on E and kappa to three decimals. The intervals are not part of the check.

| Row | A | B | M | only A | only B | E | cases | absences | fully matched | with at least one pair | kappa |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `^1` | 403 | 430 | 387 | 16 | 43 | 0.868 | 373 | 55 | 314 | 368 | 0.950 |
| `^2` | 75 | 70 | 52 | 23 | 18 | 0.559 | 65 | 363 | 40 | 48 | 0.943 |
| `^3` | 48 | 52 | 39 | 9 | 13 | 0.639 | 56 | 372 | 38 | 38 | 0.839 |
| `^4` | 94 | 110 | 56 | 38 | 54 | 0.378 | 95 | 333 | 29 | 46 | 0.677 |
| `^5` | 119 | 153 | 84 | 35 | 69 | 0.447 | 129 | 299 | 63 | 81 | 0.890 |
| `^6` | 295 | 329 | 172 | 123 | 157 | 0.381 | 98 | 330 | 31 | 52 | 0.842 |
| `^7` | 66 | 96 | 37 | 29 | 59 | 0.296 | 79 | 349 | 22 | 36 | 0.767 |
| `^8` | 61 | 70 | 42 | 19 | 28 | 0.472 | 64 | 364 | 37 | 41 | 0.953 |
| `^9` | 61 | 72 | 43 | 18 | 29 | 0.478 | 64 | 364 | 37 | 42 | 0.953 |

Status of these numbers: MEASURED on the old labels by the designer's sketch scripts, and re-run by the plan writer on 2026-10-05 with the same counts. They are practice arithmetic. They show how the new count behaves. They do not test guide v2.0.

For information, not part of S1 (same source): "`^9` reached by reasoning" 32 / 47 / 27, E 0.519. "uncertain `^8`" 73 / 70 / 46, E 0.474. "uncertain `^9`" 60 / 71 / 42, E 0.472. "`^6` clue": 18 team A entries, 0 team B.

**Part 2, the hand-made fixture.** Six made-up passages and two hand-made label sets, frozen with this plan. In the passage file, F1 has curly quotes and a curly apostrophe; the labels use straight ones.

- F1: Mr. Okoro wound the hall clock. “It runs slow again,” Mr. Okoro said. The smell of brass polish put him back in his uncle’s workshop.
- F2: Ilse heard the bell from the yard. Then the bell took her back to her first school, and to the smell of chalk dust.
- F3: Dana set the fern on the sill. Its green fronds gave her a quiet sense of calm. The radio in the next room barely reached her.
- F4: Every morning before the ferry left, Tomas checked the mooring lines. He no longer had to think about the knots.
- F5: Rosa saw the grey film on the jar and caught a sharp, sour smell. She knew the starter had turned.
- F6: The kiln cooled overnight. Ash lay in a grey ring on the shelf.

Team A's labels:

- F1: `^1` "Mr. Okoro", support sentence 1. `^8` "The smell of brass polish" and `^9` "his uncle's workshop", pointing at each other, support sentence 3.
- F2: `^1` "Ilse". `^8` "the bell" with `^9` "her first school". A second `^8` "the bell" with `^9` "the smell of chalk dust". Support sentence 2 for all four pair entries.
- F3: `^1` "Dana". `^2` "Its green fronds", held, H2-COMFORT, support sentence 2. `^4` "The radio in the next room", measure "barely reached her", support sentence 3.
- F4: `^1` "Tomas". `^7` "checked the mooring lines", measure "Every morning", support sentence 1.
- F5: `^1` "Rosa". `^8` "the grey film on the jar" with `^9` "the starter had turned". `^8` "a sharp, sour smell" with a second `^9` "the starter had turned". All four are ambiguous with `other_candidate` reasoning. Support: both sentences.
- F6: `none_of_these` true.

Team B's labels are team A's, with five differences:

- F1: the `^1` support is sentence 2. The `^8` label is "The smell of brass polish put him back", and the `^9` points back at that string.
- F2: the support of all four pair entries is sentences 1 and 2.
- F3: the `^2` entry is written clear.
- F4: the `^7` label is "checked the mooring ropes". That is not in the passage. It is sent three times unchanged.
- F5: only the first pair is written.

Expected output:

- Sentences: F1 3, F2 2, F3 3, F4 2, F5 2, F6 2. Total 14.
- Checker: team A 18 entries, 0 fail. Team B 16 entries; 1 fails C3 (F4, `^7`), is dropped, and stays in row `^7`. Team B's dropped share is 1 of 16 = 0.0625. That is over 5%, so the run prints INVALID.
- Rows as A / B / matched / only A / only B:
  - `^1` 5 / 5 / 5 / 0 / 0
  - `^2` 0 / 1 / 0 / 0 / 1
  - `^4` 1 / 1 / 1 / 0 / 0
  - `^7` 1 / 1 / 0 / 1 / 1
  - `^8` 3 / 3 / 3 / 0 / 0
  - `^9` 3 / 3 / 3 / 0 / 0
  - held `^2` 1 / 0 / 0 / 1 / 0
  - uncertain `^8` 2 / 1 / 1 / 1 / 0
  - uncertain `^9` 2 / 1 / 1 / 1 / 0
  - `^5` with twins 1 / 0 / 0 / 1 / 0
  - every other row is 0.
- Reasons: `^2` only B: `STATUS`. `^7` only B: `DROPPED`. `^7` only A: `FACES_A_DROP`.
- Every bar row: `NOT_ENOUGH_CASES`.

The fixture folder is `label_v2/fixture/`. The six passages and the two label sets above are its set `spec_six`. The folder also holds further hand-made sets that drive parts of the program the six passages do not reach. When this section was last changed these were: `branches`, `backstop`, `forms` (six passages; in each one team B writes a form that guide section B2 forbids), and three ruling files. One of the ruling files sets every hold code to `open`: `label_v2/fixture/rulings/all_codes_open.json`. The expected output of every set is kept in `label_v2/fixture/FIXTURE_EXPECTED.json`. That file is frozen and hashed with the fixture. S1 covers every value in it. For part 1 and for the six passages, that file and this section must give the same numbers. If they differ, S1 is not met until the difference is found and corrected.

**Part 2 scores raw label files.** No checker is run in part 2. So part 2 tests the scorer alone, with its own backstop: the scorer itself drops an entry it cannot place. The counts above for team B ("1 fails C3 ... is dropped") are reached in part 2 by that backstop, and in part 3 by the checker.

**Part 3, the chain: checker first, then scorer.** The same made-up label files are sent through the checker's own three-try loop. The checker writes the final rows. The scorer scores those rows. This is the hand-over the real run uses. A broken checker, or a broken hand-over, shows here as a value that differs. For each set the expected file holds what the checker marked, what the gate says about the rows, and the scorer's counts. One set is the case the review found: team B answers the re-ask on F4 by leaving the failing entry out on its second try. The checker puts the entry back. So team B still has 16 entries with 1 dropped, and row `^7` still reads 1 / 1 / 0.

**Part 4, the gate of verdict mode.** Hand-made seal records, receipts and label rows are shown to the gate (section 7). For each case the expected file lists the refusals the gate must give. Among them: a record that is not a seal, a record with no owner sign-off, a signed value the scorer does not hold, a file with another hash, a label file with a missing or unfinished row, a raw label file, a receipt that names another guide, and the same file given for both teams.

Status: the sentence counts, the checker counts, the rows and the twin count were printed by the designer's sketch `fixture.py`, and re-run by the plan writer on 2026-10-05 with the same output. The reasons, the outcome words and the wrong-program lines below come from the design text and were not re-run. The programmer confirms all of it by hand.

What a wrong program prints (run by the designer):

- If the Mind is located through the `^1` support: `^1` matched is 4, and `^8` and `^9` matched are 2.
- If a label is located only at its first place in the support: `^8` and `^9` matched are 1.
- If "Mr." ends a sentence: the sentence total is 16.
- If a dropped entry vanishes: row `^7` is 1 / 0.

**Part 5, the practice labels.** The candidate checker and scorer are run on both teams' labels of the practice passages (section 14). Tables 1, 2 and 5 are printed. This is practice, not a verdict.

## 14. The practice pass and the seal conditions

**The practice pass.** 120 fresh passages from 6 settings used nowhere else, twenty each: K1 18, K2a 18, K2b 18, K4 18, K5 18, K7 15, K3 6, K6 6, K8 3. Both teams label them under the candidate guide and checker. The candidate scorer prints Tables 1, 2 and 5. Practice passages are never scored for the verdict. The guide may still change after a practice pass. A changed guide is then covered by the next practice pass, or by the owner's waiver (see "The practice report must be tied to its files" below). A practice result is not a verdict and is not a claim.

**SEAL CONDITIONS (PROPOSED).** They are process checks, not claims. They are read off the practice output.

- **S1.** Parts 1 to 4 of section 13 print exactly what this plan and the frozen expected file say. A part with no value compared is not a pass.
- **S2.** On the practice labels, each team has fewer than 5% of its entries dropped.
- **S3.** No labeler reports, in `guide_problem`, two rules that order opposite things. Every report is listed for the owner.
- **S4.** On the practice passages of kind K1, entry agreement for `^8` and for `^9` is at least 0.80. (About 18 passages: a tripwire, not a measurement.)
- **S5.** Of the practice `^6` pairs whose parts match, at least 0.80 also match on the whole.

**If a condition fails.**

- If S1 fails: fix the program.
- If S2 to S5 fail: fix the guide, write new practice passages (the tool's practice pass 2, with its own 6 settings and its own seed), and practice once more.
- If the second pass also fails: stop and report to the owner. Nothing is sealed.
- At most two practice rounds. There is no third.

**How the seal tool reads the conditions.** The scorer prints S1 to S5 in its practice report, each with a status. Only `PASS` is a pass.

- **S1 is run again by the seal tool itself,** on the scorer, the checker and the fixture that are being sealed. It runs the scorer's own two check commands (the fixture check and the old-labels check). Both must end without a difference. So S1 is always a statement about the final programs, not about an earlier copy.
- **S2, S4 and S5 are read from the practice report.** The seal tool refuses unless each reads `PASS`.
- **S3 is different.** A program cannot tell whether a labeler's report names two rules that order opposite things. The scorer prints `PASS` for S3 when no labeler wrote a guide problem, and `NEEDS_A_READER` when one did. Then a person reads every report, and the reading is written down as a record: who read, how many reports, and that none names two rules that order opposite things. The record names the practice report it belongs to. The seal tool refuses to seal without it. Every report is listed for the owner.

**The practice report must be tied to its files.** In practice mode the scorer writes into its report, under `made_with`, the sha256 of every file it was run with: itself, the checker, the guide, the labeler instructions, the passages, both label files, the kinds file and the fixture. The seal tool reads that block.

- The report must name the practice passages of `PRACTICE_SET.json`. The seal tool always asks for that file. A report on other passages, or a report that names no file, does not open the seal.
- **The practiced files are the sealed files (PROPOSED; sheet item 10).** The report must name the guide, the labeler instructions, the checker and the scorer that are being sealed. The team A launch text must be the one of the practice set. If one of them changed after the practice pass, the seal tool refuses.
- There are two ways on from such a refusal. One: a new practice pass with the final files, inside the limit of two passes. Two: the owner writes `item 10 = waived` in the signing line. The owner then accepts that S2 to S5 were read on the files as they were before the change. The seal records the waiver and the files that differ. S1 is run again on the final programs in every case.
- This matters for the order of work. If the owner changes an item after the practice pass, the guide or a program changes with it. So the cheap order is: signature first, practice pass second.

The sha256 of the practice report, of `PRACTICE_SET.json` and of the reading record go into `SEAL.json`.

The hash of this plan is written into `PRACTICE_SET.json` before any practice label exists. So anyone can check that S1 to S5 were written down before the practice results. They still bind only once the owner signs them.

## 15. Order of work

1. **Build.** Guide v2.0, this plan, the checker, the scorer, the hold table, the fixture, the labeler instructions, the team B tool, the writer tool, the seal tool and the sign-off sheet. The guide's worked examples are made-up twins of the old passages, one for each hold code and each pointing case.
2. **Program checks** on the old labels and on the fixture (S1).
3. **One review round** of the build. Done: section 22. Only blocking or major findings hold the run.
4. **The practice pass** on 120 fresh passages, and the practice part of the program check. Read off S1 to S5. At most two rounds (section 14).
5. **The owner's signature.** The operator prints the line to paste with `tools/seal_v2.py signing-line`. The signature may come at any time before this point. It is needed here at the latest. Without the sign-off record, nothing is sealed. The cheap order is signature first, practice pass second: a change the owner makes after the practice pass needs a new practice pass or the owner's waiver (section 14).
6. **Freeze and hash** the guide, the plan, the checker, the scorer, the hold table, the briefs, the fixture, the labeler instructions and the two teams' fixed words. **Write** the 760. **Seal** them.
7. **Both teams label,** every passage to a final state (section 21). **The program scores.** The operator reports the program's output.

## 16. Compute and cost

- **No AWS.** Labeling is calls to the two label services. The scorer is arithmetic on about 860 short passages. Nothing heavy runs on the laptop.
- **Writer:** Gemini free tier. 4 calls for a practice pass and 26 for the verdict set, more if a call fails.
- **Team A:** Claude sub-agents on this account's allowance.
- **Team B:** DeepSeek, one call per try. The estimate below was redone after the review of the build. The earlier line "under 2.50 USD" is withdrawn: it holds only in the best case.
- This is an estimate, not a bill. This plan grants no spending. Spending rests on the owner's existing approval record (`OWNER_APPROVAL_ALL_STAGES_20261005T0610Z.json`): spend only inside funds the ledger shows as unreserved, with a stated cap, and report each cost.

**Team B: how many tokens (ESTIMATE).**

- MEASURED by the team B tool's dry run on 2026-10-05 (no call was made): the fixed text sent with every call (head line, guide, instructions) is 114,314 characters. A first request for one passage is about 114,700 characters. The guide has grown since plan v1.2: 108,661 bytes against 19,265.
- ESTIMATE, not measured: that is about 29,000 to 33,000 tokens going in per call (3.5 to 4 characters per token), and about 1,000 tokens coming back.
- Calls: about 860 first tries (about 740 verdict passages and 120 practice passages). Every re-ask is one more call of the same size. If half of the passages need one more try: about 1,290 calls. At most, with three tries everywhere: about 2,580 calls.
- Tokens: about 26 to 29 million for the first tries alone. About 39 to 44 million with a re-ask on half of the passages. At most about 88 million. A second practice pass adds about 4 to 12 million.

**Team B: what that costs (ESTIMATE; the price was not confirmed).**

- READ on 2026-10-05 from the service's price page, through a page-fetch tool, not checked by a second reading: the page lists no model named `deepseek-chat` (section 5). For `deepseek-flash` it lists, per million tokens: 0.30 USD going in at peak hours and 0.15 USD off-peak when the service's cache is missed; 0.006 USD and 0.003 USD when the cache is hit; 1.20 USD and 0.60 USD coming back.
- If `deepseek-chat` is billed at that price (an assumption), then with a re-ask on half of the passages:
    - no cache hit, peak hours: about 13 to 15 USD;
    - no cache hit, off-peak: about 7 USD;
    - cache price on the repeated guide text: about 1 to 2 USD.
- First tries alone, no cache hit, peak hours: about 9 to 10 USD. The reviewer's own check, scaling the plan v1.2 figure, gave about 6.1 USD before any re-ask.
- The service decides whether the cache price applies. Every call starts with the same 114,314 characters, so it may. That is not known until the first calls are billed.

**The cap, in USD and in tokens (PROPOSED).**

- The cap for outside services stays as proposed: **6.00 USD**, until the owner's approval record states another figure. The estimate above shows that 6.00 USD may not cover the whole attempt. This plan does not raise the cap. That is the owner's.
- The team B tool counts tokens, not money. It refuses a real run without `--token-cap`. The cap counts over all runs that write one labels file, so a resume cannot start again from zero. Every cap ever given is kept in the receipt.
- **Practice pass: 9,000,000 tokens** for the team B labels file. At the listed peak price with no cache hit that is about 3 USD (ESTIMATE). If the practice pass needs more, the cap may be raised inside the USD cap; the tool records every raise.
- **Verdict set: the token cap is set from the practice receipt, by this fixed rule.** The operator reads three things: the tokens per call in the practice receipt (MEASURED), the share of them the service counted as cache hits (if the service reports it), and the price page of that day. That gives the cost per call. The verdict token cap is the largest number of tokens that keeps every practice pass and the verdict set together under the USD cap in force. It is never more than 90,000,000. It is written into the run record, with the three readings, before the first verdict call.
- **No start on a cap that cannot finish the job.** If that token cap is smaller than the tokens the first tries need plus one fifth (verdict passages x measured tokens per first try x 1.2), team B's verdict labeling does not start. The operator reports the measured cost and the cap to the owner. A run that stops at its cap with passages still open is not finished, and an unfinished set is not scored (sections 12 and 21).
- The writer spends nothing on the free tier.

## 17. The honest forecast

Everything here is an ESTIMATE unless it says MEASURED. The rules were written after reading the old misses. So they fit the old passages better than they will fit new ones.

- "Floor" is MEASURED: entry agreement of the old labels under the new scorer.
- "Ceiling" is MEASURED: the same, if every pointing miss had matched, paired one to one.
- Both were measured by the designer's sketch scripts and re-run by the plan writer on 2026-10-05 with the same values.
- "Expected" is the forecast of the designer and of the feasibility reviewer, from reading. It is not a measurement.

| Noetic | Floor | Ceiling | Expected | Forecast against the proposed bar of 0.80 |
|---|---:|---:|---|---|
| `^1` Mind | 0.868 | 0.868 | about 0.85 to 0.92 | likely pass, not by a wide margin |
| `^8` Above/Cause | 0.472 | 0.845 | about 0.68 to 0.86 | about even, leaning under |
| `^9` Below/Effect | 0.478 | 0.797 | about 0.68 to 0.86 | about even, leaning under |
| `^2` Positive | 0.559 | 0.629 | about 0.60 to 0.78 | under |
| `^3` Negative | 0.639 | 0.639 | about 0.62 to 0.80 | under, or `NOT_ENOUGH_CASES` |
| `^5` Female | 0.447 | 0.563 | about 0.50 to 0.70 | expected to fail |
| `^6` Male | 0.381 | 0.673 | about 0.50 to 0.72 | expected to fail |
| `^4` Vibration | 0.378 | 0.437 | about 0.45 to 0.62 | expected to fail |
| `^7` Rhythm | 0.296 | 0.339 | about 0.35 to 0.60 | expected to fail, or `NOT_ENOUGH_CASES`, or `NO_VERDICT_WAITING_ON_OWNER` |

**In one line.** Likely pass: `^1`. About even: `^8`, `^9`. Under: `^2`, `^3`. Expected to fail: `^4`, `^5`, `^6`, `^7`.

- On the old labels only `^1` meets the proposed bar. With perfect pointing only `^8` would (0.845). `^9` would stand at 0.797, because team B wrote extra Effects that no pointing rule removes.
- `^8` and `^9` have a second risk: a pass is withheld if more of their entries are uncertain or reasoned than clear.
- `^4` and `^7` are mostly a presence problem: one team says the role is there and the other does not. The owner said so, and the numbers agree. This design does not try to make them pass. It makes the count honest. It shows how much of each Noetic is settled and how much waits on the owner.
- Kappa passed for all nine before. Narrower bar rows can lower it for `^7`, `^3` and `^2`. For `^4` the old 95% interval of kappa is [0.579, 0.762] (the designer's resampling; not re-run): it reaches below 0.60.
- Eight Noetics may fail again. That would be a true result. The owner should choose the bar knowingly, before the seal.

**What is expected to still fail, per Noetic** (from the design; ESTIMATE from reading the old misses).

- `^1`: team B lists side people that team A does not (43 against 16 on the old labels). No rule was added for them.
- `^8`, `^9`: a trigger described three ways, where one labeler stops one sentence too early. A scene label that one team starts three or more words later. A clear pair from one team against a held pair (H89-FOLLOWS) from the other. A second memory that one team still gives its own pair.
- `^2`: whether two namings are one thing. The thin line between a word of affinity and a good feeling ("finding comfort in"). A labeler who goes back to the thing although the passage aims at its quality.
- `^3`: on purpose, no rule was added for a bodily reaction with no feeling named, for fear or distress in an aside, or for people spoken of in general. The two holds take entries out of the bar row, so `NOT_ENOUGH_CASES` is possible.
- `^5`: where "the passage names a standing skill" ends and "the passage only shows a skilled action" begins. A remembered episode that one team also marks as lived. Team B marks more (153 entries against 119 on the old labels).
- `^6`: the whole. On the old labels 70 unmatched entries on each side are the same part with a different whole. One split costs every part in a list, 4 or 5 entries at once. The clue row hangs on one judgment: whether the passage is rule 15(b) or rule 15(d). That line waits on the owner.
- `^4`: English says "how much" in open-ended ways. Is "jarring" a size? The size-word list gives examples only. Six owner questions sit under the row.
- `^7`: the rate test has soft edges. "Does the passage say what the exposure did" is a new judgment. A team that marks more keeps part of that habit. Three holds take the largest presence splits out of the bar row. So a pass would mean "rate words plus a stated effect", not Rhythm as a whole.
- Rows with no bar: uncertain pairs (floors 0.474 and 0.472) and conclusions reached by reasoning (0.519) should rise a little. They still wait on the owner's two open questions. No pointing rule settles them.

## 18. How this attempt stands to option B

The owner chose option B for the usefulness test: give model B carefully checked role descriptions from the labeling teams, and compare against ordinary help and no help.

- **This attempt does not hold up the option B usefulness test.** That test uses the matched entries of the first verdict, which are already sealed.
- The matched bar-row pairs of this attempt (section 11, "output for option B") will feed a **later replication** of that test.
- Only matched bar-row entries are "checked by two teams". Whether a Noetic that fails here may still supply its matched entries, with the failure stated beside them, is the owner's call (section 19, question 25).

## 19. Questions that stay with the owner

No question below is decided by this plan, by the guide or by the program. Each line gives the question and what the teams do until the owner answers. That is not the same for every question. There are three groups.

- In the first two groups the entry is written and counted in a row of its own, with no bar.
- In the third group there is no such row. Both teams follow one working line of the guide. What they write then counts toward a pass or a fail. For some kinds the working line says to write no entry at all.

A working line never decides the meaning. It only makes two labelers do the same thing. The question numbers 1 to 26 are the numbers of the first version of this plan. Two questions were split after the review of the build: their second halves are now 3b and 6b in the third group.

**The owner's two open questions (the owner's own words).**

1. "Does recognizing a familiar sign count as Cause -> Effect when it brings another idea to mind?" Default: not decided. Guide rule 15 stays as written. Such a pair is written as uncertain and counted in the rows "uncertain `^8`" and "uncertain `^9`", with no bar.
2. "Does an idea reached through reasoning also count as Effect?" Default: not decided. Such a conclusion is written with `reached_by` reasoning and counted in the row "`^9` reached by reasoning", with no bar. A follow-up: in step-by-step reasoning, are the clues `^6` at all, and which Idea do they compose? Default: not decided. Clues are written with no whole and counted in the row "`^6` clue", with no bar.

**Questions with a hold code.** Until the owner answers: not decided; the entry is written, marked held under the code, and counted in its own held row with no bar.

3. H2-COMFORT. A thing gives a Mind comfort, warmth or calm, and no affinity is aimed at it. Is it `^2` for that Mind? (The second half of this question is 3b, below.)
4. H3-NOPULL and H3-BORED. A thing "held little appeal", or bored the Mind, and nothing against it is stated. Is it `^3`?
5. H5-ROLE. Does a role with a word like "seasoned" or "veteran" state an Idea the Mind is composed of?
6. H7-RESULT. A passage shows only that a Mind now acts without thinking, with no rate or pattern. Is `^7` present? The canon table lists the saying "Muscle memory." under `^7`; the definition names "the rate and pattern". (The second half of this question is 6b, below.)
7. H7-NOEFFECT. A passage states a rate and says nothing of what it did to the Mind. Is that `^7`, or must the entraining be shown?
8. H7-UNBROKEN. Does exposure with no break ("The constant hum") count as a rate and pattern, or does `^7` need repeats?
9. H89-FOLLOWS. A memory simply follows something noticed, with no linking word. Clear Cause -> Effect, uncertain, or nothing?

**Questions with no hold code: twelve.** The fixed design gives these no held row. Its hold list is closed at eight codes. Until the owner answers, both teams follow one working line of the guide, so that they write the same thing. That line is this study's convention, not canon, and the owner has not confirmed it. What the line gives is counted inside the pass/fail rows. Where the line says so, no entry is written at all. So the result for the Noetic is read as "under these working lines". Every working line is on the sign-off sheet as item 9, and in guide section B5, so that the owner can strike it before the seal. A struck line is taken out of the guide, and the teams may then split on that kind. If the owner answers the other way after the seal, labels of that kind are redone on new passages. Two of the twelve (questions 10 and 19) have no working line at all: there the labelers may differ, and the difference lands in the pass/fail rows.

- 3b. `^2`, a stated affinity. Is a stated affinity with no movement shown ("He much preferred an orderly workspace") enough for `^2`? Working line: it is written as a clear `^2`, inside the pass/fail row (guide rule 5; sheet 9a).
- 6b. `^5`, a habit. When a Mind acts without thinking, is that same moment `^5`? Working line: a clear `^5` when the passage names a habit or a skill as the Mind's own ("a habit", "second nature", "ingrained", "muscle memory"). No `^5` entry for words that only say how the action is done ("automatically", "without thinking") (guide rule 6b; sheet 9b). Part A lists the saying "Muscle memory." under `^7`. Under this line those words give a clear `^5`, and the `^7` for that moment is at most held (question 6).

10. `^3`, not ruled on. Is a bodily reaction against a thing with no feeling named (a wince at a clatter) the Mind being repelled? Is fear of a thing, or distress about what may happen? No working line was added. Guide rule 5 stands as it was. Labelers may differ here, and the difference lands in the `^3` bar row.
11. `^5`, plain titles. Is a plain job title or life stage ("a taxi driver", "as a student") `^5`? Working line: no entry and no held entry is written (guide rule 6b and H5-ROLE; sheet 9c). The designer's reason: both old teams left plain titles out in 59 of 61 old passages. If plain titles are `^5` for the owner, the owner says so before the seal.
12. `^7`, what counts as a rate. Three parts.
    - When the passage says a thing "always made her wince", is that a rate of exposure? Working line: no `^7` entry and no held entry is written (guide rule 6a; sheet 9d).
    - Is the line in rule 6 the owner's: "thirty years on the wards", "years of loading and unloading" and "many isolated winters" are lengths of time, `^5` only; "years of early mornings" is also a pattern? Working line: the guide's rate test is used as written. For time spent doing a thing, and for practising with no rate, no `^7` entry and no held entry is written (sheet 9e). A number of winters or years is a length of time, so it gives no `^7` (sheet 9f).
    - Part A lists the saying "Practice makes perfect." under `^7`. Under the working line, practising with no how-often word gives no `^7` entry. The price is known: two old passages of this kind ("years of loading and unloading", "Years of repetitive training") were `^7` for both old teams and now get no entry. A labeler who meets such a case follows the numbered rule and writes a report that starts with the words "Saying against rule:". The scorer counts these reports (guide rule 14; sheet 9q).
13. The `^7` label. In "Every time the bell rang for a new round, Maria automatically snapped into her fighting stance", which is the Idea the Mind is exposed to: the bell, or the stance? Does something the Mind itself keeps doing count as being exposed to an Idea? Working line: the entry keeps both, the stance in the label and the bell in the measure (convention 6 of rule 16; sheet 7f). A second line: an action done without thinking that is the stated effect of a clear `^7` is not written again as a held `^7` (guide rules 13 and 17; sheet 9p). The other choice is a second `^7`, held under H7-RESULT.
14. `^4`, six questions, kept as guide v1.2 had them. (a) Is "no impression at all" a degree of resonance? (b) Does "its impression" cover only how much, or also what kind? (c) When the thing itself is faint or loud and the Mind takes it in, is that `^4`? (d) Does a flinch with no size word show a degree? (e) Is the strength of any feeling a thing gives its own `^4` beside the `^2` or `^3`? (f) Is a thought that keeps coming back `^4`, `^7` or both? `^4` has no hold. Working lines: (a) little or none counts; the no-appeal phrases are written as a clear `^4` beside the held `^3` (sheet 9g), and the report prints the `^4` row a second time without the no-impression words. (b) What kind of impression it was is not `^4` (sheet 9i). (c) How faint or loud the thing itself is, is not `^4`. (d) A flinch with no size word is left out. (e) A how-much word on any feeling gives a `^4` (sheet 9h). (f) No working line.
15. `^5`, what the Idea is. When an experience formed a Mind, is the `^5` Idea the experience, the trait it left, or both? Is exposure alone `^5`? Is a remembered episode that comes to Mind also `^5`? Is one act of learning `^5`? Working line: the experience is the label (convention 3; sheet 7c). The program prints `^5` with and without the twins, and the proposed bar row is the one without (sheet 6 and 7g).
16. `^6`, what counts as composed of. A part named in passing; the steps of a procedure; the listed causes of a fault; the contents of a remembered place. Two levels of parts. Is the whole the object or its problem? Working lines: the whole is taken as the passage words it, and a naming followed by a doing word is skipped (convention 4; sheet 7d and 9n). The steps of a procedure are written as parts (sheet 9j). Details that merely accompany a remembered place are left out, as in guide v1.2. The report prints `^6` matches on the part alone.
17. `^8` and `^9`. After a trigger brings one memory, is each further remembered thing its own Cause -> Effect? When several signs lead to one thing, is the group one Cause? Is an action set off "without a moment's conscious thought" an Idea brought to Mind? Is the Effect the whole scene or its central thing? Working lines: no pair for a further memory unless the passage says what brought it (sheet 9k); one pair per sign (convention 8; sheet 7h); no pair for the action (sheet 9l); the scene is the label. For the held kind H89-FOLLOWS, "follows" means the sentence right before, or the same sentence (sheet 9m).
18. `^2` and `^3`, which thing. When the pull is toward a quality or a use of a thing ("its mechanical might"), which is the Positive: the thing, what the passage names, or both? Working line: the label is what the passage names (convention 2; sheet 7b).
19. `^1`. Is a person shown only doing a physical thing a Mind to be listed? Does a group spoken of in general count as a Mind? There is no working line. Guide rule 4 keeps its v1.2 text. The guide's example E8 does not list such a person, who has no entry of another Noetic. A person who has an entry of another Noetic is always listed. Guide rule 10(c) says to write no `^4` for someone who is not a listed Mind. Labelers may still differ here, and the difference lands in the bar rows of `^1` and `^4`. The report counts unmatched Minds that carry no other entry on their own line.

**Questions about the method (not about a definition).**

20. The bar: which measure, and at what number? Default: nothing is sealed until the owner signs a bar. Proposed: E at least 0.80.
21. A pass near the bar: keep "the measured value decides, and the report says when the interval reaches below the bar", or a different word for such a pass? Default: kept as in plan v1.2. No new word is created.
22. The withheld pass `NO_VERDICT_WAITING_ON_OWNER`, the eight held kinds, the `^5` bar row, the nine conventions, the seventeen working lines, S1 to S5, and the rule that the practiced files are the sealed files: accepted? Default: nothing is sealed until signed.
23. The pointing rule: is "the naming next to the evidence" the short, consistent identifying label the owner meant, or the first naming in the passage? Default: the naming next to the evidence (convention 1), until signed or changed.
24. The passages: 760 from the same blind writer, or a second blind writer from a family that is neither label team for part of them? Default: the same writer, as written here.
25. Option B: may matched entries be used for a Noetic that misses the bar, with the miss stated? Is a third check wanted on them? Default: not decided here. That is the option B plan's question.
26. S3 needs a reader when a labeler wrote a guide problem. Who reads: the operator, an outside reviewer, or the owner? Default: not the operator alone. An outside reviewer or the owner reads, the reader is named in the reading record, and every report is listed for the owner.
27. Working lines, or more held kinds? The rule this attempt was given says that every kind that waits on the owner is written, marked held and counted in its own row. The twelve questions with no hold code do not get that. There are two ways. One: the owner accepts the working lines as they are signed (sheet item 9), and strikes the ones the owner does not accept. Two: the owner asks for new hold codes for the kinds where an entry can be written: a stated affinity with no move, a named habit, a plain job title, "always made her wince", a further memory, practice with no rate. New hold codes change the fixed design, the guide, the checker, the scorer and the fixture, and need a review of their own. Default: the working lines, as signed. This plan does not choose the second way by itself.
28. The team B model. If the service no longer accepts the name `deepseek-chat` (section 5), which model labels for team B? Default: nothing is labeled until the owner has chosen.
29. The cap for outside services. The redone estimate (section 16) shows that 6.00 USD may not cover team B for the whole attempt. Keep 6.00 USD, or state another figure in the approval record? Default: 6.00 USD stays; the verdict labeling of team B does not start on a cap that cannot finish it.

## 20. How the owner's signature is recorded

**The line the owner pastes.** The owner reads `label_v2/OWNER_SIGNOFF_SHEET.md` (items 1 to 10) and pastes one line. `tools/seal_v2.py signing-line` prints it for the operator, with two fingerprints filled in. A fingerprint is the first 12 characters of the sha256 of the guide or of the plan. The line has one of two forms:

- `SIGNED: label-agreement v2.0, guide <fingerprint>, plan <fingerprint>, all items 1 to 10 as proposed.`
- `SIGNED: label-agreement v2.0, guide <fingerprint>, plan <fingerprint>, all items as proposed, except item 1 = 0.75; item 9c = struck.`

**What the seal tool does with it.** The operator records the pasted line, word for word, in one JSON file: the owner sign-off record. The record also names the sha256 of the sheet that was signed. `tools/seal_v2.py` reads the pasted line itself. It refuses to seal:

- if the line is not one of the two forms, or names an item that is not on the sheet. Any other text does not open the seal;
- if a fingerprint in the line is not that of the guide or of the plan being sealed. So the signature is tied to the exact guide and plan the owner read, for every signature, changed or not. If the guide or the plan changes after the signature, one new pasted line is needed;
- if the sheet on disk is not the sheet that was signed;
- if the record lists decisions of its own and they do not say what the pasted line says.

**Every signed value is compared with the programs.**

- Signed as proposed: the scorer must hold the proposed value. That covers the two bars, the minimum counts, the five outcome words, the `^5` bar row (`FIVE_BAR_ROW`), and the numbers of S2, S4 and S5. Each of the eight hold codes must be in the scorer and in the checker.
- Changed by the owner to a number (items 1, 2, 3, 8b, 8d, 8e), or item 6 changed to "with twins": the tool reads the owner's value from the pasted line. The scorer must hold exactly that value. If the scorer still holds the old number, the tool refuses.
- A held kind the owner ruled on (items 4a to 4h): the code must be gone from the scorer, from the checker and from the hold table file. Otherwise the tool refuses.
- A seal condition the owner struck (items 8a to 8e): only then does the tool leave it out.
- Items the tool cannot compare with a program: a convention (7a to 7i) or a working line (9a to 9q) that the owner struck or changed in words, and a change to the outcome words (5). For these the builders change the guide or the scorer, and the record must name the plan, the guide, the scorer and the checker in which the change was made (`changes_applied_in`). The seal lists each such item as "not checked by this tool". The owner's fingerprints in the pasted line are then those of the changed guide and plan.
- The same record of decisions is written into `SEAL.json`. The scorer reads it again before it scores (section 7).

**When the owner changes a number.** The builders change the scorer's constant and this plan. The fixture's expected words at the edges of the outcome rule depend on the bars, and so do two of its hand-made seal cases. Those change too. MEASURED on 2026-10-05 on a scratch copy of the scorer as it stood before the review fixes, with the bar set to 0.75: the fixture check then reported 2 of 1,493 values as different. So S1 must be met again on the final scorer and fixture, and the seal tool runs it itself (section 14).

**Limits.** The tool cannot check that a signature is real. Keeping the record true is the operator's duty. The owner can compare the record, and the copy in `SEAL.json`, with what the owner pasted.

## 21. How the label files are made (fixed before any label)

This section was added after the review of the build. It closes choices that were open until then. None of them may be made after a label file has been scored.

- **Each label file is written by a program, never by hand.** Team A's file is written only by the checker's export, from the try logs of the sub-agents: `check_labels_v2.py PASSAGES --export OUT --tries LOG ... --guide G --instructions I --launch-text L --seal RECORD`. Team B's file is written only by `tools/label_outside_v2.py`, run with `--seal RECORD` and `--token-cap N`. `RECORD` is `PRACTICE_SET.json` for a practice pass and `SEAL.json` for the verdict set. Each program refuses when the guide, the instructions, the checker or the passage file are not the ones the record names.
- **One receipt for each label file.** Each program writes a receipt beside its label file. The receipt names the sha256 of the label file, the passage file, the checker, the guide and the instructions. Team A's also names the launch text. Team B's also names the tool. The scorer compares both receipts with the seal before it scores.
- **What team A's receipt cannot show:** which guide a sub-agent really read. Its guide hash is the file the coordinator named at export. The launch text and the start line (section 5) are what tie a sub-agent to the guide.
- **Every passage is taken to a final state, for both teams.** A passage is final for a team in three ways, and in no other: the checker accepted the record; the three tries are used and the third record stands, with its failing entries dropped; or the three tries are used and the third gave no record that can be read (not labeled).
- **An open passage is resumed, with its own try log.** Team B: the same command is run again, and the tool goes on at the same try. Team A: the same sub-agent, or a new one started with the same start line, goes on with the same try log. A passage keeps one try log: the export refuses a passage whose tries sit in two logs. Tries that are used stay used.
- **`--close-unfinished` is not used in this attempt.** Not on the practice set and not on the verdict set. The switch makes the last try of an open passage final before its third try. Its use would be a choice made after seeing how a run went.
- **The scorer is run on finished files only.** In verdict mode it refuses a label file with an open passage. In practice mode it lists open passages and counts them as not labeled, and the practice report says so.
- **A verdict run that cannot be finished is INVALID.** If a passage is still open when labeling stops for good, the scorer is not run for a verdict. The attempt is reported as INVALID with the reason: for example the service is gone, or the cap is reached and the owner does not raise it. Nothing is scored on the passages that happen to be done.
- **The cap for team B is a number of tokens** (section 16). The tool refuses a real run without it.

## 22. Review round 1: findings and what was done

The build had one review round, by three reviewers, on 2026-10-05: 3 blocking and 19 major findings. There is no second round. Each finding was given to the builder of its file. This section records what was done. For a file that is not the plan writer's (the guide, the checker, the scorer, the fixture, the team B tool), the line says what the plan writer READ in that file on 2026-10-05. It does not say the plan writer tested it. Status words: FIXED; HELD FOR THE OWNER (a question about a definition, or a design change, that no builder may decide).

**Blocking findings.**

1. *The plan told the owner that every open question is held; twelve are not* (sections 0 and 19). FIXED, on paper, by the smaller of the reviewer's two ways. Section 0 and the opening of section 19 now say what is true. The second halves of questions 3 and 6 are now 3b and 6b, among the questions with no hold code, each with its true working line. Every working line is on the sign-off sheet as item 9. HELD FOR THE OWNER: the reviewer's larger way, new hold codes, changes the fixed design (question 27).
2. *A failing entry vanished when the labeler left it out after a re-ask* (checker). READ: the checker now keeps every entry that failed C1 to C7 on a try that was sent back, and puts it back as a dropped entry when the final record lost it. The fixture has the case (F4 left out on try 2). Plan sections 6 and 13 describe it.
3. *The scorer gave a verdict while passages were still open* (scorer; plan section 12). READ: verdict mode now refuses unless both label files hold one final row for every sealed passage. FIXED in the plan: sections 12 and 21 fix that every passage is taken to a final state, that `--close-unfinished` is not used, and that a run that cannot be finished is INVALID.

**Major findings: the owner's signature and the seal (seal tool, sheet).**

4. *The sheet did not show everything the signature puts in force.* FIXED. The sheet has item 9: the seventeen working lines of guide section B5, each in plain words with its other choice. Item 4 says what a ruling after the seal gives. Item 7e says that a clue loses its whole even when the passage names it. Item 7i prints the four word lists and what each leaves out. The sentence "Signing answers no question about what a definition covers" was replaced.
5. *The signature was tied to the sheet only, not to the guide and the plan.* FIXED. The line the owner pastes names the guide and the plan by fingerprint. The seal tool refuses when a fingerprint is not that of the file being sealed, for every signature (section 20).
6. *Any text passed as the owner's line; a changed number was not compared with the scorer; a removed hold code was not checked.* FIXED. The seal tool reads the pasted line itself and accepts only the two forms on the sheet. It compares every number the owner wrote with the scorer's constant. A code the owner ruled on must be gone from the scorer and the checker. The `^5` bar row (item 6) is compared too; the scorer now holds it as a constant.
7. *Nothing tied the practice report to the files being sealed.* FIXED. The scorer writes into its practice report the sha256 of every file it was run with (READ). The seal tool always asks for `PRACTICE_SET.json`, refuses a report on other passages, and refuses when the guide, the instructions, the checker, the scorer or the team A launch text changed after the practice pass, unless the owner waives that (new sheet item 10). It runs S1 again itself on the final scorer, checker and fixture (section 14).
8. *Verdict mode took any record with five hashes as a seal* (scorer; found by all three reviewers). READ: the scorer now has a gate (section 7). A practice-set record, a hand-made record and the first attempt's seal layout are refused. The seal tool writes what the gate asks for. The all-open hold table file exists and is named in section 3.

**Major findings: the labels and the measure (checker, scorer, fixture).**

9. *Nothing tied the label files to the sealed checker and guide.* READ: each label file now has a receipt; the scorer compares the receipts with the seal, runs the sealed checker again on every final record, and refuses the same file for both teams. Section 21 fixes how the label files are made.
10. *Seal condition S1 never ran the checker.* READ: the fixture check has two new parts, the chain (checker, then scorer) and the gate. Section 13 describes them, and S1 now covers parts 1 to 4.
11. *The checker accepted three forms the guide forbids* (found by two reviewers): a clear `^8` tied to a `^9` reached by reasoning; one thing written in two certainties; a clue with a whole. READ: checks C1, C5, C6 and C8 were tightened, the scorer's backstop has the same tests, and the fixture set `forms` has the cases. Section 6 summarises the form lines.
12. *What happens to an unfinished passage was left open until after labels exist.* FIXED: section 21, and the paragraph "Not finished is not the same as not labeled" in section 12.

**Major findings: the guide.**

13. *Two of Part A's three sayings for `^7` are sent out of `^7` by Part B, with no held entry.* Part A and the rule text were not changed. FIXED in the plan and on the sheet: question 12 has the full wording again and says plainly that no `^7` entry and no held entry is written; sheet items 9b, 9e and 9q show the two sayings beside the lines. READ in the guide: rule 14 now tells a labeler to follow the numbered rule and to report the case, and the reports are counted. HELD FOR THE OWNER: a hold code for "repeats with no how-often word" (question 27).
14. *Rule 17 and the notes of three examples ordered opposite things for an action done without thinking.* READ in the guide: rules 13 and 17 now say that an action used as the stated effect of a clear `^7` is not written again as a held `^7`. The choice is on the sheet as item 9p, with its other choice.
15. *The plan said no rule was added on a person shown only doing a physical thing, while a guide example decided it.* READ in the guide: no working line was added, because the question is about who is a Mind; the note of example E8 now says so, and rule 10(c) says to write no `^4` for someone who is not a listed Mind. FIXED in the plan: question 19 now says there is no working line, that labelers may differ, and where the difference lands. HELD FOR THE OWNER: the question itself.

**Major findings: the two teams' fixed words and the cost.**

16. *Team A's exact words were not written down or hashed; the kinds file sat beside the team A chunks.* FIXED. The seal tool writes one launch text for team A from two hashed pieces, and records its sha256 (section 5). The start line of a team A sub-agent has one fixed form. The kinds file goes to a folder of its own. READ in the checker: the recipe is now a constant, no longer text for a labeler to find in the source.
17. *The team B tool's cap was off by default and started from zero on every resume; the cost estimate was not redone.* READ in the tool: a real run is refused without a token cap, and the cap counts over all runs. FIXED in the plan: section 16 has the redone estimate and states the cap in tokens and in USD. Two things came out of it that are the owner's (questions 28 and 29): the model name `deepseek-chat` is no longer on the service's price page, and 6.00 USD may not cover team B.

**What the plan writer measured in this round** (MEASURED on 2026-10-05; stand-in files in a scratch folder; no project file was written by the tests; no call to a label service or to the writer; one public price page was read for section 16).

- The seal tool against stand-in scorers: 22 cases that must be refused were refused, each for the stated reason. Among them: any text as the owner's line; a wrong guide fingerprint; item 1 signed as 0.75 while the scorer holds 0.80; item 3 signed as 100 and 100 while the scorer holds 50 and 50; a ruled-on hold code still in the checker; a practice report that names no file; a practice pass under another guide with no waiver; a kinds folder inside the output folder. 7 cases that must be sealed were sealed.
- The seal tool with the real scorer, checker and fixture as they stood at 06:52 PDT: its own S1 run passed. The scorer printed 3,781 fixture values with 0 different (parts 2, 3 and 4) and 249 old-label values with 0 different (part 1). The real scorer's gate found 0 problems in the seal the seal tool wrote. It found 6 problems in the practice record, so it refused it. The checker's own comparison with the practice record found 0 problems.
- These numbers describe the programs at that minute. The builders were still changing files. S1 is binding only as the seal tool runs it at the seal.

**Not reviewed.** Everything written in this round is new and has had no review: the changed guide lines, the checker's put-back rule, the scorer's gate, the new fixture parts, the team B tool's cap, the seal tool's reading of the pasted line, sheet items 9 and 10, the team A launch text, and sections 16, 19, 20 and 21 of this plan. The owner asked for one review round. The practice pass and the seal conditions are the next check.
