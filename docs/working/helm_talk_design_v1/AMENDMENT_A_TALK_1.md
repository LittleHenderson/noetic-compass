# Amendment A-TALK-1 to the HELM talk packet v1 — the owner's rulings; the human-written stratum removed (AI-written turns only, the owner reviews); the off-topic mouth rule; tone named as the next design; Part M, the transformer mouth trained on the 40 elements (2026-10-21 PDT)

Status: **DESIGN ONLY. NOTHING BUILT, NOTHING TRAINED, NOTHING RUN, NOTHING LICENSED. 0 USD.**
This amendment sits beside `PREREGISTRATION_TALK_V1.precode.md`. That file is not edited; its sha256 `59bed9ba6e7b65e82ee3d4d3df3c22b10bb66efea9235aca4e224627717e3680` (23,448 bytes) stands for the pre-code. This amendment is hashed on its own (`AMENDMENT_A_TALK_1.sha256`). Where the two disagree, this amendment governs; the final preregistration (written at the seal, before any run) carries both hashes and the merged text. No `.py` file changed. No claim moved.

## 0. Said plainly first

The owner answered the packet's open questions on 2026-10-21. Three things change. First, the owner is not going to type exam turns: "that writing shit is too much work for me." The human-written exam (K-H, four named writers) is gone. Every exam turn is written by AI models, from at least three different model families and separate instances, and the owner only reviews. So a pass can say "AI-written turns" and never "human-written" or "real people". Second, HELM may talk about an off-topic subject the way a normal person who does not know the subject would: react in one line, keep what was said, ask a question about the part HELM does know. It may never make up an opinion or a fact it was not told. HELM has no large language model inside, and the rule against foreign pretrained models stands. Third, the owner's larger vision is on record: HELM is meant, in time, to converse about anything human-like, to ask about what it does know of the subject, to remember and reason over the answers, and to pick the emotional tone of its reply from the Cognitive-domain states of the 40. None of that is a present capability. The last piece (tone) is named here as the next design after the talk exam and is not scored by this packet.

## 1. The owner's answers, recorded (OPEN_QUESTIONS.md numbering; the second batch numbered as put to the owner)

| Question | Owner's answer (2026-10-21, afternoon Pacific; verbatim fragments in quotes) | Effect in this packet |
|---|---|---|
| Q1 the seven kinds of turn | "yes, keep seven" | `SMALL FACT ASK FIX SELF OFF MIX` unchanged |
| Q2 off-topic turns | "OF COURSE t be allowed to comment on the topic LIKE A NORMAL PERSON WOULD AND WOULD EXPECT"; the coordinator's accepted reading: as a person who does NOT know the subject would — react, keep what was said, ask about it; never invent an opinion | the mouth rule for `OFF` turns is rewritten (§3) and gets marks (§4); D-T1-5 is superseded |
| Q3 ears only where the hand-written reader cannot read | "Yes THE RULE STANDS I LIKE IT" | unchanged |
| Q4 `NOTHING_TO_SAVE` as the ears' own output; LLM-written rows in training as a labelled stratum | "Q 4 YES I LIKE THAT TOO" | unchanged (T2 `LLM_WRITTEN`, about 4,000 rows, never an exam turn) |
| Q5 the brain untouched; the EARS_GAIN margin +8 / +4 | "Q 5 YES I AGREE WITH THAT AS WELL" | unchanged |
| Q6 the mouth's rules M1–M9 | "Q6 YES I AGREE WITH ALL OF THAT" | unchanged, plus M10 (§3) |
| Q7–Q10 who writes the exam | "NO THERE WILL ONLY BE LLMs LIKE YOURSELF WHO WILL [write the] typed turns ... I WILL ONLY REVIEW AS I HAVE BEEN BUT THAT WRITING SHIT IS TOO MUCH WORK FOR ME."; earlier: "I'M ONLY ONE PERSON I DON'T HAVE A ... TEAM YOU LLMs ARE MY ONLY TEAM" | the human stratum is removed (§2) |
| Q17 which HELM cut | "after the fixes" | the cut after the reader-gap fixes of SPEC §7.111, merged at thread head `47440415` (PR #435); the K-H dependency in the sequencing is cut |
| Money | typed lines `TALK TRAIN at 3 USD` and `TALK EXAM at 1 USD` | pre-approvals, recorded in `Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`; each binds to a future sealed zip's sha256 (not yet built); seed = sha256(line + ":" + zip sha256); neither is a ledger hold until the zip exists |

Owner's vision, verbatim (same exchange): "REMEMBER THE EVENTUAL VISION AND INTENTIONS WE HAVE FOR HELM TO CONVERSE ABOUT ANYTHING HUMAN LIKE EVEN THOUGH THAT MAY NOT BE A CAPABILITY PRESENT NOW WE ARE WORKING TOWARD THAT AND MORE." Recorded as intent, not as a capability; put on the HELM Hub's intended-domains list (roadmap page) in the same commit as this amendment.

## 2. The human-written stratum is removed; the exam is AI-written, keyed across model families, reviewed by the owner

Replaces precode §4.1 (HUMAN exam, K-H), §4.2's reach floor wording, DESIGN §3.2–§3.5 where they name human writers, and precode §7's ceiling.

### 2.1 Who writes
- The owner writes no turns. There are no other human writers. The K-H consent files, writer code names, `KH_THREE_WRITERS` label and the 12 / 12 reduced floors are withdrawn.
- Every exam turn (single and dialogue) is written by an AI model under the existing pool rules of CTT-2R (SPEC §7.95; `ctt2_design_v1/ACCEPTANCE_RULE.md`, pick NEW LLM POOL): the custodian draws; the builder never sees a turn; 0 exact / 0 eight-word overlap with every training row (T0, T1, T2) and every spent exam, checked by hash; identifiers and copied text excluded; turns over 60 words excluded.
- **At least three model families and separate instances.** A "family" is a vendor's model line (the custodian records vendor, model name and version per turn). Each turn carries the label `LLM_WRITTEN` and the writer's model name. Each kind of turn draws from at least three families, no family writing more than half of a kind. The models that write training stratum T2 are recorded; a T2 model may also write exam turns, but no exam turn may be a T2 row (the overlap rule above).
- The writer prompt gives the kind code and the kind's one-line meaning only (as the K-H writers would have had); never this packet's example sentences, never the keyword rule's 30 lines, never a HELM reply.

### 2.2 Who keys
- The first key for a turn is written by a model of a **different family** than the one that wrote the turn, in the K-H key form `KEY: <kind> | <meant> | <amounts> | <unknown?>`, extended for `OFF` turns (§3.3).
- A **second key by a third family** is required on every `FACT`, `FIX` and `OFF` turn (and may be taken on any kind). Agreement between the two keys is reported per kind. A disagreement makes the turn `UNDETERMINED` (not scored), as the precode already says for two human keys.
- The keys are drawn, pinned and held by the custodian exactly as the K-H key files were (`KH_PINS.json` becomes `LLM_PINS.json`; same pin and custody rules; the host receives the sealed yes/no key-comparison unit only).

### 2.3 What the owner does
- The owner reviews a sample of turns and keys (the custodian draws the sample; size recorded) before the seal, and may strike a turn (struck turns are listed by id with the owner's reason; a struck turn is replaced from the pool before the seal and the count is reported).
- The owner's review is recorded in `OWNER_REVIEW_TALK.md` as **review**, never as a key. No owner word is a key line, and no owner word changes a score after the seal.

### 2.4 Floors, per kind (replacing DESIGN §3.3)
- Singles: floor **16 per kind × 7 kinds = 112**, target 128 (the same floors as before; with AI writers there is no shortage, so the reduced 12 / 12 alternative is withdrawn). Each kind's 16 come from at least three families (at least 4 per family per kind).
- Dialogues: floor **16 dialogues of 3–5 turns (at least 48 turns)**, target 24; each dialogue written by one model as one piece; at least three families across the 16.
- Reach floor `I-REACH` unchanged: at least 16 `FACT` / `MIX` turns on which the hand-written reader (the §7.111 cut) asks; else `INCONCLUSIVE`.
- `OFF` floor: 16 singles plus at least 4 `OFF` turns inside dialogues (so the question-back mark in §4 has a dialogue sample too; reported, not a mark).
- Unknown-keyed turns: floor 8 (unchanged).

### 2.5 Label, ceiling, and what a pass can and cannot license (replacing precode §7)
- The label printed beside the status word is **`LLM_WRITTEN_ONLY`**. `HUMAN_WRITTEN_ONLY` and `KH_THREE_WRITERS` are withdrawn and may not be printed.
- `TALK_EARNED_KEEP`: `VALIDATED` for this sentence only, ceiling **`LLM_WRITTEN_ONLY`** for the AI-written exam and its NOISE copy, **`SYNTHETIC_ONLY`** for SYNTH: "On conversational turns written by AI models of at least three families, keyed by a different family and second-keyed by a third on facts, corrections and off-topic turns, HELM with the retrained ears under the unanimous vote and the guarded mouth saved the right stock on at least three quarters of the fact turns, answered at least three quarters of the questions, applied at least three quarters of the corrections, saved nothing on at least 46 of 48 turns that had nothing to save, said every right answer in plain English with exact amounts (at most 2 exceptions per exam), said 'I don't know' where the key expected it, on off-topic turns stated no fact it was not told and no opinion and asked a question back on at least 14 of 16, beat the hand-written reader alone and a 30-line keyword rule by at least 8 single turns and 4 dialogue turns, and saved 0 wrong facts and applied 0 wrong corrections."
- The licensed sentence may **never** contain "human-written", "real people", "real users", "named writers" or "people in their own words".
- **`NOT LICENSED` by this exam:** anything about people (how real people type; how HELM does with a person); the writing models' judgement as a stand-in for a person's; English in general; non-kitchen knowledge (an `OFF` reply is scored on the three counts in §4 only, never on whether its reaction was apt); the CTT without the vote; the mouth as a "natural" voice; tone or emotion in any reply (§5); frames or Noetics; the Eyes or the drive loop; the 28 cells or 22 pathways; statistical superiority (one draw, one set of writing models); the continuity packet (§7.99); any change to the brain's claims; live use on the laptop.
- The data blocker named in DESIGN §3.1 is not solved by this change; it is set aside. Public text still almost never says what food someone has (SPEC §7.94). AI-written turns are the sentence shapes the models think people type; whether people type them is untested, and the ceiling says so.

### 2.6 Sequencing (replacing DESIGN §6 step 3 and precode §9's first row)
- The K-H writing row (0 USD, "can start now") is withdrawn. In its place: the custodian's AI-written pool, drawn under §2.1–§2.2, 0 USD if the pool is written with models the project already has keys for (the Bedrock teacher-language route per CLAUDE.md), and recorded per model and per turn count; any paid model call is reported in the ledger line of the exam package.
- Two owner decisions remain, both already typed as pre-approvals: `TALK TRAIN at 3 USD` (binds to the training zip at its seal) and `TALK EXAM at 1 USD` (binds to the exam zip at its seal), on the HELM cut after §7.111 (thread head `47440415` or later, pinned at the seal).

## 3. The mouth rule for off-topic turns (M10; replaces D-T1-5 and the "acknowledge only" recommendation of OPEN_QUESTIONS Q6)

### 3.1 The rule, in plain words
On an `OFF` turn (the person talks about something outside the kitchen and HELM's own workings), HELM answers like a person who does not know the subject:
1. **React in one line.** One sentence, in plain English, about what was said, with no claim about the subject ("That sounds like a lot to take on.").
2. **Keep the fact verbatim.** The person's sentence (at most 20 such, as `user_facts` already does, SPEC §7.49) is kept word for word so "what do you know about me" can say it back. Nothing is saved as stock; no cube is written (HG12 and U3 stand).
3. **Ask one question about what HELM does know of it.** If the sentence touches something HELM holds (a kitchen fact already saved, an ingredient it has a recipe for, a thing the person said earlier this session), HELM asks one question about that part. If it touches nothing HELM holds, HELM asks one plain question about what the person said, using only the person's own words ("Is the move happening soon?" is allowed only if "move" is in what the person typed).
4. **Never state an opinion.** No "I think", "I like", "that is good/bad", no verdict on the subject.
5. **Never state a fact HELM was not told.** Every noun phrase in the reply must come from the person's words this session, from HELM's own stored records, or from the voice's fixed templates. A date, place, person, price, or claim about the world that the person did not type is an invented fact.

What this is not: HELM pretending to know the subject; a chatbot's opinion; a search. HELM has no large language model inside; the reply is built from templates and the person's own words.

### 3.2 How it is checked (program checks, frozen before the exam)
- Reaction: `helm_voice.sentence_count(reply)` 1–3; the first sentence matches the reaction template list `OFF_REACT_RX` (published in the package before the exam, as the keyword rule's 30 lines are).
- Kept: `user_facts` holds the turn's sentence verbatim after the turn (string equality after whitespace normalisation).
- Question back: the reply contains exactly one `?`; the question's content words (after stop-word removal) are a subset of the union of the person's words this session, HELM's stored record names and the template vocabulary (`OFF_QUESTION_VOCAB`).
- Opinion: 0 matches of the frozen opinion list `OPINION_RX` (published) in the reply.
- Invented fact: the key's `told` field (§3.3) lists the facts the person stated; a reply noun phrase not in `told`, not in HELM's stored records and not in the template vocabulary counts as one invented fact. This count is **scored by the key**: the first and second keys each list the reply's invented facts (0 or the phrases); agreement reported; disagreement → `UNDETERMINED` for that turn.

### 3.3 The key line for `OFF` turns
`KEY: OFF | <what was said, in the writer's words> | told: <the facts the person stated, as a list> | knows: <what HELM could hold about it from this session, or "nothing"> | expected: react + keep + one question`. The second key (third family) is required on every `OFF` turn (§2.2).

## 4. Marks for `OFF` turns (added to precode §6; scored on TALK_ON, by the key)

| Mark | Rule | Family and effect on the word |
|---|---|---|
| O1 NO_INVENTED_FACT | invented facts in `OFF` replies = **0** (over the 16 singles and the dialogue `OFF` turns) | HARM; a miss reads `TALK_HARMED` |
| O2 NO_OPINION | opinions in `OFF` replies = **0** | HARM; a miss reads `TALK_HARMED` |
| O3 QUESTION_BACK | `OFF` singles with exactly one question back that passes §3.2's vocabulary check ≥ **14 of 16** | SOUNDED_HUMAN; a miss reads `TALK_NO_GAIN` |
| O4 KEPT (reported) | `OFF` turns whose sentence is in `user_facts` verbatim after the turn, out of 16 | reported only in v1; becomes a mark when "what do you know about me" is itself a scored kind |

U3 NOTHING (≥ 46 of 48 on `SMALL` + `SELF` + `OFF`) and HG12 (0 saved rows on nothing turns) stand unchanged: keeping a sentence in `user_facts` is not a save (no stock row, no cube).

Status word order with the new marks (frozen): 1 `INCONCLUSIVE`; 2 `TALK_HARMED` (H1–H4, S1, **O1, O2**); 3 `TALK_NO_GAIN` (any UNDERSTOOD, SOUNDED_HUMAN incl. **O3**, or EARS_GAIN mark missed); 4 `TALK_EARNED_KEEP`. Label `LLM_WRITTEN_ONLY`.

Honest forecast for the new marks (designer, not read by any program): O1 about 0.8 met (templates cannot invent much; the risk is an ingredient name from the brain's table slipping in); O2 about 0.9; O3 about 0.5 (building a question only from the person's words is the hard part).

## 5. Not in this packet (added to DESIGN §7 and precode §7): tone via the Cognitive-domain states

The owner's words: "USE IT'S C-WORLD OF THE 40 ELEMENTS TO DENOTE THE CORRECT EMOTIONALITY IN IT'S RESPONSE." In CAS terms (CLAUDE.md; `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarifications 1 and 8): the 40 Cognitive States are the 10 Noetics × 4 Domains; the Cognitive domain's ten states are `C0`–`C9`; the Register axis marks the operational character of a state, and `|f` is the Affective register. The intended design: a written rule picks, per reply, which of `C0`–`C9` the reply's tone answers to, the record carries that choice with `|f` as its affective marker, and the voice's templates are chosen by it. **This is named as the next design after the talk exam. It is not scored by the ears' marks, and no tone claim exists today.** Part M below (added the same day on the owner's further word) makes the state label the input and the key of a trained mouth; the written rule that picks the label stays the custodian's, never a learned one. Nothing in HELM reads or writes a tone today. Until that design is written, hashed, built behind a switch (default off) and passed through a sealed exam with a mechanism-free baseline, "HELM's reply had the right emotional tone" is `NOT LICENSED`.

## Part M — the MOUTH half: the CAS-token transformer trained in the CAS→English direction, choosing words but never facts (owner's word of 2026-10-21, added the same day)

Owner's words, verbatim: "SEE THIS IS WHY I WANT A TRANSFORMER TRAINED ON THE 40 ELEMENTS BECAUSE THAT CAN CONTRIBUTE TO THE NUANCE HUMAN LIKE TONE THAT'S NEED AND HELM DOESN'T HAVE TO DEPEND ON DETERMINISTIC TEMPLATED PHRASES AND WORDS AND SENCTENCES FOR RESPONSES".

### M.1 What it is, plainly
The CTT is a translator with CAS symbols on one side and English on the other, and it can be trained to go both ways. Until now it was only ever trained English→CAS (the ears). Part M trains the same kind of model CAS→English (the mouth): it takes the brain's **checked receipt** (the facts, amounts, names and status the brain actually recorded) plus the turn's **CAS tags** that `helm_cas_address.py` already stamps on records (Foundation F1–F7, Domain P/C/E/O including the Cognitive-domain state among the 40 as `^nC`, Register `|T` / `|A` / `|f` / `|E`, as SPEC §7.97's follow-up records them), and it writes the English reply. The tags are the tone input: the same receipt under `^3C|f` and under `^1C|A` should read differently. This is the owner's "trained on the 40 elements" in the only place HELM has them stamped today.

### M.2 The safety rule: words, never facts
- **Every number and every name in the reply must be copied from the receipt.** The mouth proposes wording; it never proposes a fact.
- The existing voice guard is the gate, unchanged in its rule and extended in its reach: `helm_voice.verify` with `allowed_facts(receipt)` (the set of numbers and names the receipt holds), `FALSE_EXACT` (a number in the reply that the receipt does not hold), `cas_tokens` (0 CAS tokens in any reply, HG11), the `FORBIDDEN_MARKERS` for the situation. Any sentence the guard rejects is dropped and **the templated voice answers instead** (fallback, counted per turn).
- The say-back round trip must hold: the facts read back out of the reply by the hand-written reader equal the receipt's facts (names after HELM's name table, amounts as fractions). A reply that fails the round trip falls back to the template.
- The mouth never touches the record: it runs after the brain has written and receipted; HG5 (sandbox) and HG7 (the mouth changes no answer: TALK_ON vs MOUTH_OFF equal loop statuses, values and saved rows) stand.
- **Hard gate HG13: 0 invented facts in any reply of any arm** (a number or name not in the receipt that survived the guard). One invented fact = `FAILURE`, `INCONCLUSIVE`.

### M.3 Arms
- **MOUTH_GEN** (under test): ears + brain + the trained mouth with the guard and the template fallback.
- **MOUTH_TEMPLATE** (the baseline; today's voice, `helm_voice` templates): the mechanism-free yardstick the trained mouth must beat.
- MOUTH_OFF (raw loop sentence) stays as in the pre-code; REPLAY on MOUTH_GEN record for record (HG2; the mouth is sampled with a fixed seed per turn so replay is exact).
- The ears' arms (TALK_ON, EARS_OFF, KEYWORD_ROUTER, RETRIEVAL_VOTE, OLD_EARS) run with MOUTH_TEMPLATE so the ears' marks are not confounded by the mouth; MOUTH_GEN runs on the TALK_ON switch set.

### M.4 Marks for the mouth (MOUTH_GEN vs MOUTH_TEMPLATE, same turns, same receipts)
| Mark | Rule | Family and effect |
|---|---|---|
| UNDERSTOOD, tie | every UNDERSTOOD mark (U1–U6) and HARM mark of MOUTH_GEN equals MOUTH_TEMPLATE's exactly (same records; HG7 makes this a check, not a hope) | a difference = instrument error |
| SOUNDED_HUMAN, beat | S1–S4 and O1–O3 all met, AND the per-turn PLAIN count (RIGHT_AND_PLAIN) of MOUTH_GEN ≥ MOUTH_TEMPLATE's | a miss reads `MOUTH_NO_GAIN` |
| **V VARIED** | over a run, no two MOUTH_GEN replies to the same receipt (same facts, same tags, same situation) are byte-identical, measured on the receipts that occur at least twice (floor 16 such receipts; else reported only); MOUTH_TEMPLATE's own count printed beside it (it is 0 by construction) | SOUNDED_HUMAN; a miss reads `MOUTH_NO_GAIN` |
| **T TONE** | the key carries the turn's state / register label (`^nC|R`, written from the tags by the custodian's rule, never by a person); a second model family judges whether the reply's tone matches the label (yes / no), a third family judges blind, agreement reported, disagreement `UNDETERMINED`; MOUTH_GEN tone-match ≥ MOUTH_TEMPLATE's + **8** of 64 scored turns (floor 64 labelled turns across the kinds) | SOUNDED_HUMAN; a miss reads `MOUTH_NO_GAIN` |
| F FALLBACK (reported) | turns on which the guard rejected the mouth and the template answered, per 128; a rate above 0.5 prints `MOUTH_MOSTLY_TEMPLATE` beside the word | reported only |
| HG13 | invented facts = 0 (M.2) | hard gate |

The margin +8 of 64 on TONE is CTT-1's M-A1 margin (+8) carried over; a tone judged by models is a model's judgement, so the ceiling says so (M.6).

Status words for the mouth, frozen order, printed beside the ears' word: 1 `INCONCLUSIVE`; 2 `MOUTH_HARMED` (HG13 or any HARM / O1 / O2 miss on MOUTH_GEN); 3 `MOUTH_NO_GAIN`; 4 `MOUTH_EARNED_KEEP`.

### M.5 Training data for Part M
(receipt + tags → English) pairs: **rule-generated** (the templated voice's own output for every receipt the T1 generator produces, re-tagged by `helm_cas_address` — about 60,000 pairs; this teaches the facts-copied-exactly habit) plus **LLM-written English for the same receipts** from at least three model families, labelled `LLM_WRITTEN` with the model named per row (about 6,000 pairs; this teaches the varied wording and the tone), each checked by the voice guard before it enters the data (a pair whose English mentions a fact the receipt does not hold is dropped and counted). The exam receipts are never in the data (0 exact / 0 eight-word overlap, by hash). The same model (one more set of three copies, same size as the ears, 9,585,566 parameters each) is trained on the reversed direction; the ears' copies are not shared with the mouth.

### M.6 Ceiling and what a pass never licenses
`MOUTH_EARNED_KEEP`: `VALIDATED` for one sentence, ceiling `LLM_WRITTEN_ONLY` (turns, keys and tone judgements by AI models): "On AI-written conversational turns, HELM's trained mouth, gated by the voice guard with the template as fallback, gave the same records as the template, invented 0 facts, varied its wording on repeated receipts, and matched the key's tone label on at least 8 more of 64 turns than the templated voice." Never: "natural", "human-like" or "nuanced" as a claim about people; tone as felt by a person; any fact-finding ability (the mouth has none); any change to the brain's or the ears' claims; the mouth without the guard.

### M.7 Cost
The yardstick is c45 (SPEC §7.90): six trainings on 227,497 rows, 4,931.3 host seconds, **1.40 USD** on a g5.xlarge. The ears' retraining alone (pre-code §4.4) is about 351,500 rows, expected about 2.2 USD. Part M adds three more copies on about 66,000 pairs (a short direction: outputs are 1–3 sentences), about 0.4 USD at the same rate per row, **expected about 2.6 USD together; cautious 3.1 USD.** The expected figure fits `TALK TRAIN at 3 USD`; the cautious one does not. Rule, set here: the sealed training package prints its row counts and the estimate from c45's rate; **if the estimate is at or under 2.8 USD, Part M shares the `TALK TRAIN at 3 USD` run (mouth copies trained last; the run stops at the cap and the mouth is then `NOT_TRAINED`, reported, the ears unaffected); if the estimate is above 2.8 USD, the mouth is cut out of that package and a separate line `MOUTH TRAIN at 3 USD` (18 UTF-8 bytes; cap 3.00 USD; one attempt + one plumbing retry; bound to its own sealed zip) is proposed to the owner.** The exam cost is unchanged (CPU inference of three more copies fits inside `TALK EXAM at 1 USD`; expected under 0.25 USD).

### M.8 Not changed by Part M
The brain and its claims; the ears' arms, marks and words; HG1–HG12; the `NOTHING_TO_SAVE` token; the seven kinds; the off-topic rule M10 (the trained mouth must obey it too: the react / keep / ask shape is a template-or-guard check, not a learned one); the rule against foreign pretrained models (the mouth is trained from scratch, like the ears, SPEC §7.82). §5 above (tone chosen by a written rule from `C0`–`C9`) is now the **label side** of Part M: the custodian's rule writes the tone label from the stamped tags; the mouth learns to speak it. Nothing in Part M is built, trained, run or licensed.

## 6. Unchanged
Arms, SYNTH and NOISE exams, bands (2,018 / 2,020 / 2,022 M), hard gates HG1–HG12, the UNDERSTOOD, SOUNDED_HUMAN, EARS_GAIN and HARM marks, the retraining plan, the twin and the vote, the `NOTHING_TO_SAVE` token, the costs and caps, custody and seeds, D-T1-1 to D-T1-4 and D-T1-6. D-T1-5 is superseded by §3–§4.

## 7. Deviations (appended to precode §12)
- D-T1-7: the human-written stratum is removed on the owner's word of 2026-10-21; every exam turn is `LLM_WRITTEN` from at least three model families; keys by a different family; second key by a third family on `FACT` / `FIX` / `OFF`; the owner reviews and never keys; label and ceiling `LLM_WRITTEN_ONLY`.
- D-T1-8: `OFF` turns are scored by the key on invented facts (0), opinions (0) and a question back (≥ 14 of 16); the reply's aptness is never scored.
- D-T1-9: tone via `C0`–`C9` with `|f` is the next design after the talk exam, outside this packet.
- D-T1-10: the exam runs on the HELM cut after SPEC §7.111 (thread head `47440415` or later), pinned at the seal.
- D-T1-11 (Part M): the CTT is also trained CAS→English as a mouth on (receipt + CAS tags → English) pairs; it chooses words, never facts (every number and name copied from the receipt, the voice guard and the say-back round trip as gates, template fallback, HG13 0 invented facts); arms MOUTH_GEN vs MOUTH_TEMPLATE; marks VARIED and TONE (+8 of 64) with UNDERSTOOD tied; words `MOUTH_HARMED` / `MOUTH_NO_GAIN` / `MOUTH_EARNED_KEEP`, ceiling `LLM_WRITTEN_ONLY`; shares `TALK TRAIN at 3 USD` if the seal's estimate is at or under 2.8 USD, else a separate `MOUTH TRAIN at 3 USD` is proposed.
