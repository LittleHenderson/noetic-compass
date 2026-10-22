# HELM talk packet v1 — normal conversation: ears, brain, mouth, memory (design, 2026-10-21 PDT)

Status: **DESIGN ONLY. NOTHING BUILT, NOTHING TRAINED, NOTHING RUN, NOTHING LICENSED. 0 USD.**
No `.py` file changes by this packet. No claim moves. Every HELM part named here keeps the claim status it has on the spec sheet (`docs/CAS_HARNESS_SPEC_SHEET.md`).

Owner's order (2026-10-21, verbatim): "talk packet".
Owner's words from the same exchange (verbatim): "THE CTT ... WAS BUILT TO GIVE HELM THE ABILITY TO HAVE NORMAL CONVERSATIONS WITHOUT SOUNDING LIKE IT WAS GIVING RECIPES ALL THE ... TIME".
Owner's earlier words (2026-10-19, verbatim): "what if we made a transformer for and of recipes or basically a transformer for CAS Syntax the HELM uses to communicate in like make them tokens then translate them into normal english"; "if interpretability is an issue let's just separate the cas transformer from the brain we already built and have".

The goal in one sentence (the coordinator's words to the owner, accepted): HELM's brain stays the recipe brain; a person types the way they talk and HELM answers the way a person answers; the CTT is the ears; the voice module is the mouth; recipe-speak all the time is the symptom that the ears and mouth are not doing their job.

## 0. Words used on this page, each defined once

- **HELM**: the system under test. It keeps kitchen stock (what food is on hand), learns recipes, and answers how much of a dish can be made.
- **Recipe brain**: HELM's thinking part. Today the canonical brain is the wide brain (RB-W1, owner ruling 2026-10-20, spec §7.56). It reads any ingredient name. It is **untouched** by this packet.
- **Hand-written reader** (`helm_english_in.py`, reader v1.1; and the wide reader in `helm_wide_turn.py`, v5): a program made of written rules that turns an everyday English sentence into HELM's checked form, or asks a question when it cannot. No learning inside it.
- **CTT** (CAS-token transformer, `helm_cas_translator`): a small translator trained from scratch, 9,585,566 parameters, with CAS symbols on one side and English word pieces on the other. It **proposes** a reading only when the hand-written reader would ask. It never writes a fact. HELM's own checks decide. Spec §7.82, §7.90, §7.92, §7.95.
- **Ears**: the CTT in the direction English in, proposed CAS record out.
- **Mouth**: the voice (`helm_voice.py`, `HELMVoice`): a rule-based writer that turns a brain receipt into one to three sentences of plain American English and reads every sentence back against the receipt (numbers, names, outcome words).
- **Memory** (`helm_memory.py`): the chat's working memory: turns, user facts (`user_facts`, at most 20), preferences, inventory, last goal.
- **Chat** (`helm_chat.py`, `HELMConversationalSession.handle_turn`): the window a person types into; it routes each line (commands, memory questions, agentic goals, recipe turns) and speaks through the voice.
- **Key**: the answer sheet for an exam turn, written before scoring, by someone who never sees HELM's output for that turn.
- **Custodian**: a separate agent that holds exams and keys and never shows them to the builder.
- **Builder**: whoever writes the code. Blind to exam text.
- **K-H**: "human-written" exam turns: sentences typed by named people for HELM, never by a machine. Named in `real_stock_source_design_v1/OPEN_QUESTIONS.md` Q6 (owner's pick: "human-written for HELM (K-H ...), never a looser K-S").
- **LLM_WRITTEN**: sentences written by a large language model under the pool rules of CTT-2R (Gemini + DeepSeek, custodian-only folder). A stratum label, never a human claim.
- **Mark**: a frozen number a result must reach. **Hard gate**: a must-hold check; one false makes the whole run `FAILURE`.
- **Status word**: the one word the frozen reader prints at the end, from a fixed ordered list.
- **Recipe-speak**: words that belong to HELM's recipe machinery said to a person on a turn that is not about a recipe (examples in section 5).
- **CAS token**: any CAS notation symbol (`^`, `|A`, `×`, `Φ⟨…⟩`, and the rest) or CAS jargon word matched by `helm_voice.cas_tokens`.

## 1. What "normal conversation" means for HELM, concretely

Normal conversation is a set of **kinds of turn**. Each kind gets one example sentence written by this designer (never exam text). The kinds are the exam's strata (PREREGISTRATION_TALK_V1 §4).

| Kind | Code | Example turn (designer's own words) | What a person would expect back |
|---|---|---|---|
| Greeting / small talk | `SMALL` | "hey, long day, how's it going" | A short friendly line. Nothing saved. No recipe words. |
| Kitchen fact said the way people say it (purpose clause, feeling, past tense, hedge, typo) | `FACT` | "ok so i grabbed like 3 cups of flour yesterday for the bread we're gonna make, and honestly i think we're out of sugar, cant find any" | HELM saves flour = 3 cups and sugar = none; says it back exactly ("3 cups of flour, no sugar"); says "yesterday" changed nothing about the amount; the purpose clause ("for the bread") is heard but not stored as stock. |
| A question in ordinary words | `ASK` | "so what can we still make with that" | An answer with exact amounts, or "I don't know" if nothing is known. |
| A correction | `FIX` | "no, I meant two cups" | The last amount of the last named ingredient becomes 2 cups; HELM says the change back; the old value is withdrawn. |
| A question about HELM itself | `SELF` | "wait, do you actually remember what I told you or do you forget each time" | A truthful plain line about what HELM keeps (this session's turns, up to 20 user facts, stock) and what it does not. Nothing saved. |
| Off-topic talk | `OFF` | "my sister's moving to Denver next month, kind of nervous for her" | A short human acknowledgement, no recipe words, nothing saved to stock; whether the fact is kept as a user fact is the owner's Q6 (OPEN_QUESTIONS.md). |
| A mixed turn | `MIX` | "thanks! oh and we've got 2 eggs left, that's it" | Thanks acknowledged; eggs = 2 saved and said back; the "that's it" is not read as "nothing else exists" (it is an `UNDETERMINED` clause; HELM may ask). |

What is NOT in this list, on purpose: open-domain knowledge questions ("who won the game"), requests to write code, and anything the agentic branch of `helm_chat.py` handles. "Normal conversation" here means the seven kinds above. Whether `OFF` turns may go beyond acknowledgement is the owner's decision (OPEN_QUESTIONS.md Q6).

## 2. The three layers, and who does what

```
person types ──> CHAT (helm_chat.handle_turn)
                   │
                   ├─ hand-written reader reads first (helm_english_in / helm_wide_turn)
                   │      reads ──────────────────────────────┐
                   │      asks ──> EARS (CTT ×3 copies, vote) │
                   │                 agree ──> read-back question to the person
                   │                 disagree / silent ──> the reader's own question
                   │                                        │
                   ▼                                        ▼
                 BRAIN (wide recipe brain, untouched) ◄── checked record only
                   │
                   ▼ receipt
                 MOUTH (helm_voice) ──> plain English, read back against the receipt
                   │
                   ▼
                 MEMORY (helm_memory) records the turn; saves stock only through the brain
```

### 2.1 Ears (the CTT)
- Called **only** when the hand-written reader would ask (CTT-1 rule, spec §7.82). The reader's reading, when it has one, stands.
- Three trained copies decode; a reading is a candidate only if all three produce one, each passes every check (grammar lock, pointers into the user's own words, name table, exact-number rule, round trip), and the three records are byte-identical after normalisation (ACCEPT-2, `ctt2_design_v1/ACCEPTANCE_RULE.md` §2 step 2; tested in CTT-2R, spec §7.95: 0 confident wrong proposals with the vote against 0 / 5 / 5 without it).
- **Ask is the default.** A candidate is offered as a read-back question ("Just to check: 3 cups of flour and no sugar?"), never used before a yes (ACCEPT-2 steps 1 and 3).
- **New in this packet: `NOTHING_TO_SAVE` is a first-class answer.** On `SMALL`, `SELF`, `OFF` turns the ears' right answer is a single token meaning "no stock, no recipe, no correction here". Today the CTT has no such output; it either proposes a record or stays silent, and silence is read as "ask the reader's question", which on a greeting is the recipe-speak the owner hears. Section 4 covers how it is trained.
- **Division of labour with the hand-written reader (fixed by §7.109).** The reader-gap packet (spec §7.109, PR #433 merged; `docs/working/r1_wave7/READER_GAP_DESIGN_PACKET_R1W7_20261021.md` sha256 `26b17c499f073243f150858665e81a0a2acc1b04e1edfffc754a8fd3a8ad7108`; `K4_ITEM_DIAGNOSIS_C54.md` sha256 `368cc65d55216f13143376d836d03b12e7d2bb74f7e0428b7e0fae9f597b7cef`) measured that the hand-written face lexicon's 31 rows already fit 28 of 28 face clauses on c54 once the name slot is opened. So a feeling or purpose clause on the hand-written side is a **name-table change, not a new grammar**. Its designs D1–D6 (D1 clause split in the wide reader's stock branch; D2 `helm_faces_in` with names as given; D3 the wide path records faces into the loop's triad table; D4 the wide question applies the face values; D5 paraphrase forms: leading time phrase, "the X ran out first"; D6 the custodian refuses raw lines with more than one quantity span) are **the hand-written reader's half**, ordered built by the owner on branch `claude/helm-reader-gap-build-20261021`. This packet does **not** redo D1–D7 and the talk layer must **not** re-learn those forms. The ears are for the sentences the hand-written reader **still cannot bind after D1–D5**: free word order, slang, typos, hedges, amounts stated in clauses the rules never listed, and the `NOTHING_TO_SAVE` decision on non-kitchen turns.

### 2.2 Brain (the recipe brain)
- Untouched. Receives only checked records (the reader's, or an ears reading the person said yes to). Spec §7.56 canonical pointer unchanged.

### 2.3 Mouth (the voice)
- Every reply to a person goes through `helm_voice` and its read-back guard (already true for recipe turns in `helm_chat._speak`; wave 7's P PLAIN mark held 0 not-plain on c52 and c54, spec §7.104, §7.108).
- Rules the mouth must obey are the checklist in section 5. The design change is small: today the chat's **non-recipe** replies (greetings, memory answers, agentic plans) are written by `helm_chat.py` and `helm_agentic_executor.speak_plan_result` without the voice guard. Under this design every reply, recipe or not, is guarded for CAS tokens and recipe-speak, and a non-recipe reply has a fixed small set of templates (`say_small_talk`, `say_about_self`, `say_off_topic`, `say_nothing_saved`), each read back the same way.
- Exact amounts: `helm_voice.say_amount` already says kitchen fractions exactly (denominator up to 16) and keeps "about" for long decimals (wave 7 FIX FIRST round 1). Kept as is.
- Honesty: when the key says HELM cannot know, the reply must carry one of the voice's `nodata` or `never` markers ("I don't know", "outside what I know", "never been taught"). Markers exist in `helm_voice.MARKERS`; kept as is.

### 2.4 Memory
- May recall: this session's turns, the `user_facts` list (at most 20, verbatim), preferences, the stock HELM holds (always through the brain's receipts), the last goal.
- May **not**: invent a fact it never recorded; save stock from a turn whose outcome was `NOTHING_TO_SAVE`; answer a `SELF` question with claims about abilities HELM does not have.
- Whether an `OFF` turn's personal fact is kept in `user_facts` is Q6.

## 3. Why the data path is the blocker, and the fix

### 3.1 The blocker, in numbers
- Public text almost never says what food someone has. USE-1 (spec §7.94) counted **15** first-person stock statements in **863,598** sentences of StackExchange Cooking (**0.174 per 10,000**), and 0.3 per 10,000 or less in all five public sources counted. CTT-2R's custodian census found **7** real stock sentences the reader gives up on, against a floor of **24** (spec §7.95), so Part R was `NOT_EXERCISED` and the word was `INCONCLUSIVE`.
- So an exam of "people typing to HELM" cannot be drawn from public text. It has to be **typed by people, for HELM**: K-H.
- The templated dialogue generator (wave 6 / wave 7's `gen_conv`) does **not** test this and cannot: every turn is a template around a fixed sentence pool. It tests whether the chat routes and the brain answers on sentences HELM's builders already wrote the shapes of. It never contains a hedge, a typo, a purpose clause the pool did not list, or a greeting in a person's own words. Wave 7's 20 of 64 undetermined dialogues (§7.104, §7.108) are templates HELM's reader could not bind, not people HELM could not understand. A pass on templates licenses `SYNTHETIC_ONLY` and nothing about people.

### 3.2 The fix: human-written turns, at 0 USD, never pasted into a model

**Who writes.** The owner plus three named people (named in the custodian's consent file, not here). Four writers. Whether the owner's own turns may be an exam stratum is Q2 (OPEN_QUESTIONS.md); the floors below hold with or without the owner by design (section 3.3).

**How, at 0 USD and private.**
1. The custodian prepares one plain text file per writer, `KH_<writer>.txt`, with a consent line at the top the writer types in their own words (what they wrote, that it may be used as a HELM exam, that it is not to be shown to any outside model). Writers type into that file on their own machine, or on paper photographed and typed by the custodian. No form service, no web page, no model in the loop.
2. Each writer writes, per turn, two lines: the turn itself, then its **key** (section 3.4). The writer is the first keyer: nobody knows better what they meant.
3. Each file is pinned: the custodian computes sha256 of the file bytes, records it with the date and the writer's code name in `KH_PINS.json`, and stores the files in a custodian-only folder (`Documents\Codex\<date>\helm_talk\kh_custody\`, never the repo, never the hub, never a model prompt).
4. The custodian strips nothing and edits nothing. A turn that breaks a rule (section 3.5) is excluded by id and the exclusion counted.
5. The builder sees **counts and hashes only**. The operator copies the sealed carrier to the host by hash and never opens it.
6. **No turn is ever pasted into an LLM.** Not for keys, not for cleaning, not for translation. (CTT-2R's pool rules allow LLM-written sentences in a separate, labelled stratum; those are never human turns and never go in this exam.)

**Second key.** Each writer also keys a slice of another writer's turns, blind to the first key (the custodian hands over the turn lines only). Target: a second key on **every** turn (4 writers, round-robin). Agreement is reported per kind and overall: a turn whose two keys disagree is scored `UNDETERMINED` (reported, never counted right or wrong). Two keys are required on every `FACT` and `FIX` turn (the turns where a wrong key could make a wrong save look right); on the other kinds one key suffices if the second is missing, and the count of single-keyed turns is reported.

### 3.3 How many: floors, with the arithmetic
- Seven kinds. Floor **16 turns per kind** for singles (the smallest count at which one wrong turn is under 7 percent, and the count wave 7 used as its smallest representable floor, I14). Singles floor: 7 × 16 = **112**.
- Dialogues: **16 short dialogues** of 3 to 5 turns (floor 48 turns), each mixing at least three kinds, so that a correction can refer to something said two turns earlier and a greeting can sit between two facts.
- Writers: 4 × **32 singles** = **128** singles (margin 16 over the floor of 112, so one excluded writer's slice of a kind, at most 8 per kind, still leaves the kind at or above 8 — the `I-REACH` floor of section 3.6) and 4 × **4 dialogues** = **16**. Per writer: 32 singles = about 4 or 5 per kind, written against a kind list the custodian gives them with the kind codes only (no example sentences, so the designer's examples above never leak into the exam).
- If the owner's turns are excluded (Q2 = no), the three remaining writers give 96 singles (12 or more per kind) and 12 dialogues; the exam then runs with **reduced floors 12 per kind / 12 dialogues**, written in the preregistration as the alternative, and the status word carries the label `KH_THREE_WRITERS`.
- Reach floor (`I-REACH`, as CTT-2R): the ears can only gain where the hand-written reader asks. At least **16** `FACT`/`MIX` turns across the exam must be turns the hand-written reader (post D1–D5) asks on, counted by the custodian with the sealed reader before the run; else EARS_GAIN is `NOT_EXERCISED` and the word is `INCONCLUSIVE` by rule 1 (never `TALK_NO_GAIN`).

### 3.4 The key a writer writes
One line per turn, in this fixed shape (the custodian's template; the writer fills the blanks):

`KEY: <kind> | <meant> | <amounts> | <unknown?>`

- `<kind>`: one of `SMALL FACT ASK FIX SELF OFF MIX`.
- `<meant>`: one of `fact` (save this stock), `question` (answer this), `nothing` (nothing to save, nothing to answer about stock), `correction` (change the last amount), `both` (for `MIX`: which part is fact and which is nothing, written as `fact+nothing`).
- `<amounts>`: for `fact`, `correction`, `both`: each ingredient and amount the writer meant, in the writer's own units (`flour=3 cups; sugar=none`); for `question`: the answer the writer expects given what they told HELM earlier in the dialogue, or `unknown` if they expect HELM not to know.
- `<unknown?>`: `yes` when the writer expects an honest "I don't know"; else `no`.

The scorer compares HELM's saved record (ingredient, amount, unit after the unit table) and HELM's reply against this key with the frozen rules of PREREGISTRATION §5. The writer's key never sees HELM's output.

### 3.5 Turn rules (exclusions, counted)
- A turn with a person's real full name, address, phone, or any identifier other than the writer's code name is excluded.
- A turn copied from any book, website or the designer's examples is excluded (the custodian checks against the CTT training rows by exact and eight-word match, as c45 did: 0 exact / 0 eight-word required).
- A turn longer than 60 words is excluded (the CTT's input cap; H-LEN).

### 3.6 What this gives and what it never gives
- An exam ceiling of `HUMAN_WRITTEN_ONLY`: "four named people typing for HELM". Never "real users in the wild".

## 4. The CTT retraining question

### 4.1 Why retraining is needed at all
The c45 weights (spec §7.90) were trained on **227,497** rows: kitchen-world sentences and notation rows, English on one side, CAS records on the other. They have no greetings, no off-topic talk, no questions about HELM, and no way to say "nothing here". On a `SMALL` turn the ears can only be silent (then the reader's recipe question is asked) or propose a record (a confident wrong proposal, the H-CWFW class). Conversation needs two things on the English side and one on the CAS side:
1. conversational English as input (the seven kinds),
2. `NOTHING_TO_SAVE` as a first-class output token (one new CAS-side special token; vocabulary 8,349 → 8,350),
3. corrections as an input shape with a target record that **withdraws** an amount (the existing `UNIT_KIND_MISMATCH` / withdraw path in the wide reader is the model for the target form).

### 4.2 Training data plan (designed; exact counts written on the host)
| Stratum | Source | Rows (target) | Label | Use |
|---|---|---|---|---|
| T0 kitchen world and notation | c45's existing data, unchanged | 227,497 | as c45 | kept so the ears do not forget the kitchen |
| T1 synthetic conversational turns | rule-generated on the host: templates × slot fills × noise (typos, hedges, purpose clauses from a fixed list, past-tense paraphrase, feeling words), for all seven kinds; `NOTHING_TO_SAVE` target on `SMALL`/`SELF`/`OFF`, withdraw-record target on `FIX` | about 120,000 (about 40,000 of them `NOTHING_TO_SAVE`) | `SYNTH_CONV` | the main new signal |
| T2 LLM-written turns | the CTT-2R pool rules (Gemini + DeepSeek, custodian-only folder; c45's and c49's pools are spent and excluded) | about 4,000 | `LLM_WRITTEN` | a separate stratum, kept apart in the data manifest; never human exam turns; allowed only if the owner says yes (Q4) |
| Never | any K-H turn, any X-REAL / CTT / RTR / CTT-2R / wave exam item | 0 | — | leakage check 0 exact / 0 eight-word on every exam, as c45 |

Noise rate for T1 as c45's A-world: 35 percent of rows carry at least one noise operation. The synthetic generator's templates are the designer's and are published in the package; the exam turns are people's, so template overlap is the custodian's leakage check, not a risk to hide.

### 4.3 Twin and vote
- Three main copies (seeds 1, 2, 3; 9,585,566 parameters each) for the vote; the 2,482,718-parameter twin as the size check only (ACCEPT-2 keeps the twin out of the vote); C1 shuffled-pairs control (one seed) and C2 frozen-at-init control, as c45.
- Parameter count asserted equal to the formula on the host, as c45 (the vocabulary grows by one token: the assertion's formula changes by one embedding row and one output row; the new count is written in the preregistration's final form, never read from the run).

### 4.4 Cost (AWS g5.xlarge class, us-west-2; c45 as the yardstick)
- c45: 227,497 rows, 6 trainings (3 main + twin + C1 + C2), host 4,931.3 s, charge **1.40 USD** (list 1.006 USD/h).
- This run: about 351,500 rows (227,497 + 120,000 + 4,000), the same six trainings, the same step rule → about 1.55 × c45's training time; plus the NO-HARM harness and the K-H / SYNTH scoring under the vote (three decodes per handed-over turn, about 3 × 46 s per exam on c45's sizes). Expected **about 2.2 USD** (about 7,800 host seconds); cautious 2.6.
- **Proposed cap: 3.00 USD.** Proposed owner line: `TALK TRAIN at 3 USD` (19 UTF-8 bytes). One attempt + one plumbing retry. Fallback g4dn.xlarge only if g5 capacity is refused. `GPU_REQUIRED`: no CPU fallback, nothing neural on the laptop.
- **The training run is a separate approval from the exam.** The exam (PREREGISTRATION §9) has its own line. Training without the exam gives weights and no word; the exam without new training is CTT-2R again and cannot say `NOTHING_TO_SAVE`.

### 4.5 Can the ears run on the laptop for the exam?
No. The weights are small (9,585,566 parameters × 4 bytes ≈ 38 MB), but spec §7.82 measured that the torch library alone needs 475 MiB of RAM, above the laptop's 300 MiB per-process limit, with free RAM 744–772 MB. So the exam's inference runs on an AWS **CPU** host (one m6i.xlarge-class instance, as wave 7's c52/c54 hosts, 0.01–0.02 USD each): no GPU is needed to decode 9.6 M parameters on about 400 turns × 3 copies × 7 arms. Proposed exam line: `TALK EXAM at 1 USD` (18 UTF-8 bytes), cap 1.00 USD. The hand-written-reader arms (EARS_OFF, KEYWORD_ROUTER) can run on the laptop at 0 USD and are run on the host too so every arm shares one input hash (HG9).

## 5. The mouth rules, as a checklist a reader can test

Reusing wave 7's P PLAIN mark (RIGHT − RIGHT_AND_PLAIN ≤ 2 per exam, spec §7.98 §6) and `helm_voice`'s existing guard where it exists. Each line is a program check, not a judgement.

| # | Rule | How it is checked | Exists today? |
|---|---|---|---|
| M1 | **No CAS token in any reply**, recipe turn or not. | `helm_voice.cas_tokens(reply) == []` on every reply of every arm (notation regex + jargon regex). | Yes for recipe replies (`_speak`); extended to all replies by this design. Also hard gate HG11. |
| M2 | **No recipe-speak on a non-recipe turn.** On turns keyed `SMALL`, `SELF`, `OFF` (and the `nothing` half of `MIX`), the reply must not match the recipe-speak list: `recipe`, `ingredient(s)`, `stock`, `inventory`, `limiting`, `yield`, `batch`, `receipt`, `foundation loop`, `station`, `gate`, `RPM`, `cube`, `verified facts`, `how much .* do (?:we|you) have`, any ingredient name from the brain's table that the person did not say. | A frozen regex list `RECIPE_SPEAK_RX` in the package (published before the exam); count per exam. | No (new). Mark S1. |
| M3 | **Exact amounts.** Every number in a reply about stock or yield equals the stored or computed value exactly, in the voice's fraction or mixed-number form; "about" only for a decimal longer than four places. | wave 7's RIGHT_AND_PLAIN comparison (`say_amount`, a test fixes the comparison). | Yes (wave 7 FIX FIRST round 1). Mark S2. |
| M4 | **Say what was saved, say when nothing was.** A `FACT` reply names each ingredient and amount saved; a `NOTHING_TO_SAVE` outcome ends with the words "Nothing was saved." (already appended on wide-path turns in `_speak`). | string check per turn against the saved record. | Partly (wide path only). |
| M5 | **Honest unknown.** Where the key says `unknown? = yes`, the reply carries one of the voice's `nodata` or `never` markers (`helm_voice.MARKERS`); it carries no `success` marker. | `MARKER_RX` match; `FORBIDDEN_MARKERS` for the situation. | Yes (the guard). Mark S3. |
| M6 | **Corrections said back.** A `FIX` reply states the new amount and the old one it replaces ("2 cups of flour now, not 3"). | numbers in reply ⊇ {new, old}; names in reply ⊇ {ingredient}. | No (new; the voice's `repaired` situation is the nearest). |
| M7 | **One to three sentences**, no bullet lists, no headings, no "Status:" lines in a reply to a person (the `STUDY_HYPOTHESIS` branch of `helm_chat.py` today prints a six-line structured block; under this design it is never reached from the seven kinds). | `helm_voice.sentence_count` 1–3; no line starting with `-` or `Status`. | Partly. |
| M8 | **No shell command, no tool engine turn** on any of the seven kinds (wave 7's D-W7-19 count, 0 on c52/c54). | tool-engine turns per unit = 0. | Yes (wave 7 FIX FIRST round 2). |
| M9 | **No question that the person already answered in this session** (an ask on an amount the brain already holds for that ingredient is an unexplained ask). | wave 6's K4 rule on `FACT` turns. | Yes (K4). |

## 6. Sequencing against the owner's order list

1. **Done:** round-4 clean word (c54, spec §7.108, `PASS` / `CHAT_WAVE_NO_GAIN`, clean instrument).
2. **Done (design) and being built:** the reader-gap packet (spec §7.109, PR #433 merged; D1–D6 ordered built on `claude/helm-reader-gap-build-20261021`). That is the hand-written reader's half. It lands first because the ears are only called where the reader asks, so the reader's asks must be the honest ones before any ears gain can be read.
3. **Then this packet**, in three separate owner decisions: (a) the K-H writing (0 USD; can start now, in parallel with step 2, since it does not depend on code); (b) `TALK TRAIN at 3 USD`; (c) `TALK EXAM at 1 USD` on the retrained weights, after D1–D6 are merged and HELM's suites pass, with the exam drawn against the merged reader.
4. The continuity packet (§7.99) stays parked behind the chat line as before; nothing here changes its sequencing.

## 7. What this packet does not claim
Nothing. No run, no word. Every part stays `ENGINEERED-NOT-VALIDATED`; the CTT's words on record (`EARS_NO_GAIN`, `EARS_HARMED`, `INCONCLUSIVE`) stand.

## 8. Sources read
Spec sheet §7.31, §7.49, §7.60, §7.72, §7.82, §7.85, §7.90, §7.92, §7.94, §7.95, §7.98, §7.99, §7.101–§7.109; `docs/reference/CAS_HELM_DICTIONARY.md` (CTT, CTT-1, CTT-2R, Voice, Ears / mouth, Chat wave); `Documents\Codex\2026-10-19\cas_token_transformer_design_v1\` (ARCHITECTURE, DATA, TEST_PLAN, OPEN_QUESTIONS); `...\ctt2_design_v1\ACCEPTANCE_RULE.md`, `TRAINING_CHANGES.md`; `...\real_stock_source_design_v1\` (DESIGN, SOURCES, OPEN_QUESTIONS); `...\use1\COUNT_REPORT_C1.md`; `...\2026-10-20\r1_wave7\PREREGISTRATION_R1W7.precode.md`; `docs/working/helm_continuity_design_v1/`; `docs/working/r1_wave7/READER_GAP_DESIGN_PACKET_R1W7_20261021.md`, `K4_ITEM_DIAGNOSIS_C54.md`; live code `helm_chat.py` (`handle_turn`, `_speak`, the agentic trigger), `helm_voice.py` (`say_amount`, `cas_tokens`, `MARKERS`, `FORBIDDEN_MARKERS`, `verify`), `helm_english_in.py` (`read`, `split_clauses`, `_hedged`, `ABSENT_STATED`), `helm_wide_turn.py`, `helm_memory.py` (`user_facts`, `add_user_fact`, `summarize_session_state`). `helm_cas_translator` is not on the thread branch (it lives in the sealed CTT v3 zip `f280633d…`); its interface is taken from spec §7.82 and the CTT-2R packet.
