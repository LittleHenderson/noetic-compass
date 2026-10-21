# HELM talk packet v1 — normal conversation: the ears (CTT), the mouth (voice) and the recipe brain, with the human-written exam that would earn it a word (2026-10-21 PDT)

Status: **DESIGN ONLY. NOTHING BUILT, NOTHING TRAINED, NOTHING RUN, NOTHING LICENSED. 0 USD.**
Every HELM part named here keeps its claim status on the spec sheet (`ENGINEERED-NOT-VALIDATED` for the CTT, the chat, the voice and the memory; the CTT's words on record `EARS_NO_GAIN`, `EARS_HARMED`, `INCONCLUSIVE` stand). No claim moved. No `.py` file was changed. The files changed outside this folder: `CHANGELOG.md`, the spec sheet (§7.110 and the §11 row), the dictionary (one entry), and the rebuilt hub site.

**Amendment A-TALK-1 (2026-10-21 PDT, `AMENDMENT_A_TALK_1.md`, sha256 `f9b6563b96347666eafa32eadba748b55c6e4045fbc268cd8a705e6763179a68`, 27360 bytes):** the owner's rulings are recorded; the human-written stratum is REMOVED (the owner writes no turns and reviews only; every exam turn is written by AI models of at least three families, labelled `LLM_WRITTEN`, keyed by a different family, second-keyed by a third on FACT / FIX / OFF); the off-topic mouth rule M10 (react, keep verbatim, ask one question about what HELM knows, never an opinion, never an untold fact) with marks O1–O3; label and ceiling `LLM_WRITTEN_ONLY`; tone via the C-domain states named as the next design, not scored here; Part M (the owner's further word the same day): the CTT also trained CAS→English as a mouth on (receipt + CAS tags → English) pairs, choosing words but never facts (voice guard, say-back round trip, template fallback, HG13 0 invented facts), scored against today's templated voice on VARIED and TONE, ceiling `LLM_WRITTEN_ONLY`. The pre-code file is NOT edited: its hash `59bed9ba…` stands for the pre-code; the amendment is hashed on its own. Where they disagree, the amendment governs. Lines on record: `TALK TRAIN at 3 USD`, `TALK EXAM at 1 USD` (pre-approvals bound to future sealed zips).

Owner's order (2026-10-21): "talk packet". Owner's words from the same exchange: "THE CTT ... WAS BUILT TO GIVE HELM THE ABILITY TO HAVE NORMAL CONVERSATIONS WITHOUT SOUNDING LIKE IT WAS GIVING RECIPES ALL THE ... TIME".

## What this packet is, in plain words

HELM's brain stays the recipe brain. A person types the way they talk; HELM answers the way a person answers. The **ears** are the CTT (the CAS-token transformer, 9,585,566 parameters), retrained so it can read conversational English and say "nothing to save" on purpose; it proposes a reading only where HELM's hand-written reader would ask, and only when its three copies agree. The **mouth** is the voice: plain English, no CAS tokens, no recipe words on non-recipe turns, exact amounts, "I don't know" when it does not know. The **blocker** is data: public text almost never says what food someone has (15 stock statements in 863,598 sentences, spec §7.94), so the exam must be typed by named people for HELM (K-H), at 0 USD, keyed by the writers, never pasted into any model.

The hand-written reader's half of the same problem — purpose clauses, feelings, past-tense paraphrases on the dialogue items — is the reader-gap packet (spec §7.109, PR #433 merged; designs D1–D7; the owner has ordered D1–D6 built). This packet names that work and does not redo it; the ears are for what the hand-written reader still cannot bind after D1–D5.

## Files

| File | What |
|---|---|
| `README.md` | this page |
| `DESIGN_TALK_V1.md` | what "normal conversation" means (seven kinds of turn, one example each); the three layers and who does what; why the data path is the blocker and the K-H fix with floors and arithmetic; the CTT retraining plan, twin / vote and cost; the mouth rules as a testable checklist; sequencing |
| `PREREGISTRATION_TALK_V1.precode.md` | the exam design: one-sentence question, arms (TALK_ON, EARS_OFF, MOUTH_OFF, REPLAY, ALWAYS_ASK, KEYWORD_ROUTER, RETRIEVAL_VOTE, OLD_EARS), exams (HUMAN, SYNTH, NOISE), scoring, instrument rows, twelve hard gates, marks in two families (UNDERSTOOD, SOUNDED_HUMAN) plus EARS_GAIN and HARM, status words, licence ceiling, forecast, seeds, cost |
| `PREREGISTRATION_TALK_V1.precode.sha256` | the sha256 of the pre-code file |
| `OPEN_QUESTIONS.md` | the eleven decisions that were the owner's, each with a one-line recommendation; answered 2026-10-21 (see the amendment) |
| `AMENDMENT_A_TALK_1.md` | amendment A-TALK-1: the owner's answers; the human-written stratum removed (AI-written turns only, owner reviews); the off-topic mouth rule M10 and marks O1–O4; tone named as the next design; Part M, the transformer mouth trained on the 40 elements |
| `AMENDMENT_A_TALK_1.sha256` | the sha256 of the amendment |
| `INTENT_MOUTH_TRANSFORMER_20261021.md` | the owner's statement of intent for whoever comes after (the transformer mouth trained on the 40 elements), verbatim; sha256 `e8bf17dc90e719fe8602fcd9b0baf39b2fee6e9ed2e05bc61e24b629685c061a`; rendered in full on the HELM Hub roadmap page |

## The hashes

`PREREGISTRATION_TALK_V1.precode.md` sha256 `59bed9ba6e7b65e82ee3d4d3df3c22b10bb66efea9235aca4e224627717e3680` (23,448 bytes, LF line endings) — stands for the pre-code, which is not edited.
`AMENDMENT_A_TALK_1.md` sha256 `f9b6563b96347666eafa32eadba748b55c6e4045fbc268cd8a705e6763179a68` (27360 bytes, LF line endings) — the amendment, hashed on its own.

## The short version of the exam

- Arms: **TALK_ON** (ears + mouth + brain; under test), EARS_OFF (hand-written reader only, mouth on), MOUTH_OFF (ears on, raw loop sentence out), REPLAY, ALWAYS_ASK, **KEYWORD_ROUTER** (a 30-line keyword rule over the hand-written reader; the cheap trick the ears must beat), RETRIEVAL_VOTE (copy-closest under the same vote; mechanism-free), OLD_EARS (the c45 weights; reported only).
- Exams: HUMAN (K-H: four named writers, floors 16 per kind × 7 kinds = 112 singles and 16 dialogues; targets 128 + 16; reach floor 16 reader-asks), SYNTH (rule-generated, 128 + 32, bands 2,020 M), NOISE (the HUMAN dialogues with wave 7's small talk inserted, band 2,022 M). HUMAN order band 2,018 M.
- Marks, two families kept apart: UNDERSTOOD U1 FACT ≥ 12 of 16, U2 ASK ≥ 12 of 16, U3 NOTHING ≥ 46 of 48, U4 FIX ≥ 12 of 16, U5 MIX ≥ 8 of 16, U6 dialogue ≥ 60%; SOUNDED_HUMAN S1 recipe-speak ≤ 2 of 48 non-recipe turns, S2 RIGHT − RIGHT_AND_PLAIN ≤ 2 per exam, S3 honest unknown ≥ D − 1, S4 said-back ≥ 90%. EARS_GAIN: +8 singles / +4 dialogue turns over EARS_OFF and over KEYWORD_ROUTER, +4 over RETRIEVAL_VOTE, the same on SYNTH. HARM: 0 wrong facts saved, 0 wrong corrections, CWFW ≤ 2 per 128, ≤ 2 items lost vs EARS_OFF.
- Hard gates: wave 7's ten plus **HG11 no CAS token in any reply** and **HG12 no fact saved on a nothing-to-save turn**.
- Status words, frozen order: `INCONCLUSIVE`, `TALK_HARMED`, `TALK_NO_GAIN`, `TALK_EARNED_KEEP`; label `HUMAN_WRITTEN_ONLY` (and `KH_THREE_WRITERS` if the owner's turns are excluded).
- Ceiling: `HUMAN_WRITTEN_ONLY` for HUMAN / NOISE, `SYNTHETIC_ONLY` for SYNTH. Never "real users in the wild".
- Money: K-H writing 0 USD; training `TALK TRAIN at 3 USD` (expected about 2.2 USD; c45's 1.40 USD on 227,497 rows is the yardstick); exam `TALK EXAM at 1 USD` on a CPU host (the ears cannot run on the laptop: torch needs 475 MiB against a 300 MiB per-process limit, spec §7.82). Three separate owner decisions.

## Sequencing against the owner's order list

1. Round-4 clean word: done (c54, §7.108).
2. Reader-gap packet: designed (§7.109), D1–D6 being built on `claude/helm-reader-gap-build-20261021` by a separate builder. The hand-written reader's half.
3. This packet: K-H writing can start now (0 USD, no code dependency); training and exam after D1–D6 are merged and the owner's two lines are on record.

## Sources read

Spec sheet §7.31, §7.49, §7.60, §7.72, §7.82, §7.85, §7.90, §7.92, §7.94, §7.95, §7.98, §7.99, §7.101–§7.109; dictionary entries CTT, CTT-1, CTT-2R, Voice, Ears / mouth, Chat wave; `Documents\Codex\2026-10-19\cas_token_transformer_design_v1\`, `ctt2_design_v1\ACCEPTANCE_RULE.md` and `TRAINING_CHANGES.md`, `real_stock_source_design_v1\`, `use1\COUNT_REPORT_C1.md`; `Documents\Codex\2026-10-20\r1_wave7\PREREGISTRATION_R1W7.precode.md` (house format); `docs/working/helm_continuity_design_v1/` (layout); `docs/working/r1_wave7/READER_GAP_DESIGN_PACKET_R1W7_20261021.md` (sha256 `26b17c49…`) and `K4_ITEM_DIAGNOSIS_C54.md` (sha256 `368cc65d…`); `helm_chat.py`, `helm_voice.py`, `helm_english_in.py`, `helm_wide_turn.py`, `helm_memory.py`.
