# TEACH-1 RUN RESULT (2026-10-21 PDT, laptop, 0 USD): verdict `PASS`, status word `INCONCLUSIVE` (U1 failed)

**Plainly.** The exam ran once, on the laptop, on the sealed worlds. Every instrument row and every one of the 12 hard
gates held, so the run is valid. The word is `INCONCLUSIVE` by rule 1, because U1 (the check that the teaching took hold
at all) needs 0 wrong answers in the never-forget arm, and that arm had 7. All 7 are the same case, found by a count
done by program with no item text read: HELM quoted, word for word and labelled EXACT, the person's own correction line
for that fact. The AI writers had phrased the old value without the word "not", and the frozen scoring rule
(A-TEACH1-1 D-TEACH1-12) counts a second number as a wrong value unless it follows "not". The word stands. It is a
negative and is kept. Nothing is licensed.

## Chain of custody

| Step | Record | sha256 |
|---|---|---|
| Owner's line | `COMPACT EXAM at 0 USD`, typed by the owner into the builder session (and, verbatim, "Merge 453 COMPACT EXAM at 0 USD." in the parent session) | line file `74afa660…` |
| Sealed package (seal 5) | `HELM_TEACH1_20261021_SOURCE_TEACH1_v1.zip`, merged by PR #453 at `10f83272` | `811726c45bd3f31a3df1d565295d191382685f7e7681edfc567e70e22e17dc73` |
| Cut check at the merge commit | 173 of 173 files equal | — |
| Approval record | `APPROVAL_RECORD_TEACH1.json` (beside this file) | `fb20fcb0…` |
| Seed derivation (seeds not shown) | `SEEDS.json` | `fcea03ca…` |
| Exam folder | `PINS.json` | `d4516526…` |
| Turns (LLM_WRITTEN, keyed) | `KEYED_TURNS_TEACH1.json` (custody folder only) | `11f2a962…` |
| Attestation | `TEACH1_ATTESTATION.json` (beside this file) | `fa6e4701…` |
| Reading | `TEACH1_READING_20261021.json` (beside this file; counts only) | `c08b5b2010772cc3540aafc8df5a63bff022a4bd68c93d447a6cec556df38e33` |

**The custodian.** The owner chose "do it here", so the custodian ran as a helper agent with its own separate context,
started by the builder session. The builder's context never held a world, a key, a teaching line or a seed. The helper
reported hashes and counts only. Writers: Anthropic `claude-opus-5-5` 171 lines, OpenAI `gpt-5.6-terra` (Codex CLI,
ChatGPT plan) 171, Google `gemini-3-flash-preview` (Gemini CLI) 170. All three families appear in every world. All 448
keyed lines were keyed AGREE by the two families that did not write them (FACT 320, UNKNOWN 64, FIX 32, RESTATE 32).
There were 4 rewrite rounds before keying and 3 `finish` runs. Not confirmed by the custodian: that the Gemini API key
is on the free tier; Codex's configured `priority` service tier draws on the ChatGPT plan's allowance.

**The run, from a fresh extract of the seal.** Zip sha256 equal; cut check ok; HELM's suites from the seal: unittest
`Ran 280, OK (skipped=1)`, pytest `47 passed`; route check 0 bad, exam check all ok; pool 112 of 112 units exit 0 in
227 s, one process at a time.

## The reading (reader v2, frozen order)

| Row | Value | Reads |
|---|---|---|
| Instrument rows I1–I15 | all hold | 🟩 |
| Hard gates (12) | all hold: HG-H8 4,029 memory-served answers, every label right; HG-INVENT 0; HG-CAS 0; HG-REPLAY equal | 🟩 |
| Verdict | `PASS` | 🟩 |
| **U1** (VERBATIM_ONLY taught: avg ≥ 10 and 0 wrong) | avg 13.56 (217 of 256), **7 wrong** | 🟥 → `INCONCLUSIVE` |
| U2 (0 wrong on Q-TAUGHT in every arm) | VERBATIM 7, five compacting arms 5 each, FIFO_DROP 0 | 🟥 |
| R1 vs FIFO_DROP | +148 (≥ +8) | 🟩 |
| R2 vs SUMMARY_TEXT | 0 (≥ +4) | 🟥 the forecast tie |
| R3 vs RANDOM_REFRESH | +3 (≥ +4) | 🟥 |
| R4 vs VERBATIM_ONLY, undamaged items (A-TEACH1-2) | 0 lost (≤ 2); all-items count 5, reported | 🟩 |
| R5 vs NO_REFRESH (reported) | +2 | 🟩 |
| F1 / F2 / F3 (reported) | 21 of 30 confirmed; 21 strengthened, 21 stayed; filing and lookup order hold | 🟩 |
| S1 / S2 / S3 / S4 | recipe-speak 512 of 512 / worst 2 per quiz / unknown markers missed / 0 of 32 corrections said back | 🟥 🟩 🟥 🟥 |

| Arm | RIGHT taught | RIGHT squeezed | RIGHT refreshed | WRONG taught |
|---|---|---|---|---|
| VERBATIM_ONLY | 217 | 217 | 217 | 7 |
| COMPACT_ON / REPLAY | 216 | 210 | 212 | 5 |
| SUMMARY_TEXT | 216 | 210 | 212 | 5 |
| NO_REFRESH | 216 | 210 | 210 | 5 |
| RANDOM_REFRESH | 216 | 209 | 209 | 5 |
| FIFO_DROP | 64 | 64 | 64 | 0 |

Each arm answered 256 questions per quiz (16 worlds × 16).

## The 7 wrong answers, by program (no item text read by the builder)

All 7 are VERBATIM_ONLY answers to a counted fact that the person had corrected, spread over 6 worlds, and the same 7
recur in each of the three quizzes. The program identified the quoted line from HELM's own reply. In every one, HELM
matched 2 memories (the first statement and the correction), served the newest, the FIX line, and labelled it EXACT.
That line names two numbers, the new value and the old one. The scorer counts the old one as a second stated value
because the writer did not put "not" before it. In COMPACT_ON, REPLAY, SUMMARY_TEXT and NO_REFRESH the 5 wrong answers
per quiz are the same case (the FIX line quoted, 1 match). In RANDOM_REFRESH, Q-REFRESHED has one more wrong answer of
a different kind. There HELM quoted the first, superseded statement of a corrected fact (a FACT line, 1 match). That is
a genuine wrong answer by that arm. The other cases are a rule of the frozen reader meeting AI-written phrasing. They are
recorded, not fixed, and the word stands.

## What this does and does not say

- It says: on 16 sealed AI-written worlds, every honesty and integrity gate held (no rebuilt memory called exact, no
  invented fact, no CAS token, replay equal, brain and cubes untouched). Compaction recalled 148 more answers than
  today's FIFO memory and lost 0 against never forgetting on the undamaged items. A plain text note with the same clues
  tied it (R2 0), and asking random items came within 3 (R3).
- It does not say anything licensed. U1 failed, so by the frozen order the word is `INCONCLUSIVE`, and the RECALL marks
  decide nothing. Claim status of every mechanism: `ENGINEERED-NOT-VALIDATED`.
- **Cubes:** the taught facts did not become cubes. The chat files a plain-conversation line with `cubes_written=[]`, so
  every capsule points at no cube (practice: 0 of 1,115; the Eye flagged each `UNBOUND_CLUE`). HG-CUBE held, because no
  cube face changed. The capsule-to-cube binding and the cube half of strengthening were never exercised.

## Backups

`D:\tksCAS-archive\teach1_run_20261021\` (122 run files + reading, three sha256 passes). The custody folder
`C:\Users\wakil\Documents\Codex\2026-10-21\teach1_custody\` keeps the exam content; it is not in the repo.
