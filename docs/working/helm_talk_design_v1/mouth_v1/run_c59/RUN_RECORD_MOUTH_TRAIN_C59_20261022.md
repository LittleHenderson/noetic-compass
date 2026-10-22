# MOUTH TRAIN — run record, job c59 (2026-10-22)

Owner's words (the click): "Yes: launch the MOUTH TRAIN run on AWS now (one g5.xlarge, cap 4 USD), read the result, run the AI raters, and record it."

## Word: `MOUTH_HARMED` (frozen reader `read_mouth.py`, order INCONCLUSIVE > MOUTH_HARMED > MOUTH_NO_GAIN > MOUTH_EARNED_KEEP)

Labels: SYNTHETIC_ONLY, LLM_WRITTEN_ONLY, AI_RATED.

- Job `helm-claude-mouthtrain-20261022-c59`, attempt 1 of 1. One g5.xlarge, instance `i-0d2a584bde29c69f3`, launched 14:40:07 UTC, terminated 15:51:03 UTC.
- Sealed zip `423d08a35dde3a4c05dad1bc8af6d0d8f8afc3be74a3f32f060a83633f1931ea` checked on the host. Four CTT copies trained 6,000 steps each from the CUBE TRAIN c57 finals. Runner exit 0.
- Instrument checks: all true (zip, package tests, trained no NaN, audits clean (0 violations), cost estimate, exam 1,076 >= 1,000).

| Mark | Result | Frozen line | Holds |
|---|---|---|---|
| G-NO-NEW-FACT | 1 line with a word outside the lock | 0 | 🟥 no → `MOUTH_HARMED` |
| EAR-GATES | invented 0; AI-written confident wrong 6/357; traps 1/50; SDG 2,000/2,000; keep-old A4-s1 0.9785 → 0.9795, A4-s2 0.979 → 0.9745, A4-s3 0.9775 → 0.98 | frozen CUBE TRAIN rule | ✅ yes |
| F-FALLBACK | 41 of 1,076 (0.038104) | at most 1 in 1,000 | 🟥 no |
| G-ROUNDTRIP | 512 of 761 fact replies (67.3 %) | >= 95 % | 🟥 no |
| VARIED | 59 of 100 inputs with >= 3 wordings | 100 of 100 | 🟥 no |
| SOUNDS-HUMAN | mouth preferred on 682 of 989 pairs (69.0 %) | >= 60 % of >= 300 | ✅ yes (reported; the word was already HARMED) |

## The one new-fact line (load-bearing negative, kept)

DEV input "The bus was 40 minutes late this morning…"; the mouth wrote the allowed number unit "40" twice in a row, and the detokenizer (fixed this morning, A-TALK-6 G8c) glued the two units into "4040", a number not in the input. The lock held; the fault is in the detokenizer's digit gluing. The guard failed the line (fallback), so it would not have been spoken; the frozen reader counts every record, so the word is HARMED. Fix for any rerun: never glue two digit runs that the lock emitted as separate words.

## By situation (exam, speaker A4-s1)

| Situation | Replies | Fallbacks | Round trip | Raters prefer mouth (2 of 3) |
|---|---|---|---|---|
| ANSWER | 267 | 3 | 189 / 264 | 226 / 246 |
| SAYBACK | 267 | 15 | 197 / 252 | 232 / 247 |
| ASK | 266 | 21 | 126 / 245 | 193 / 229 |
| OFF | 179 | 2 | - | 7 / 177 |
| SMALL | 26 | 0 | - | 11 / 23 |
| SELF | 30 | 0 | - | 9 / 26 |
| WORLD | 41 | 0 | - | 4 / 41 |

Raters alone (of 989): anthropic 672, openai 688, deepseek 691 prefer the mouth. 46 pairs left out (same text as the template).

## What it means (plain)

- Fact replies: the mouth mostly writes natural sentences ("Carrow had five colonies in September."), and the raters prefer them to the template about 9 times in 10. But a third of them do not read back as the same fact, and ASK is weakest.
- Chat replies (OFF, SELF, WORLD): the mouth often writes broken English ("Your basement a bat in bat bat in and in it to deal."), and the raters prefer the template almost every time (OFF 7 of 177).
- Guard weakness (found in the smoke, confirmed here): the guard checks facts and shape, not whether a sentence makes sense, so broken lines pass it. F-FALLBACK therefore under-counts bad lines; only the raters and the round trip see them.

## Money, cleanup, files

- Charge 1.29 USD (4,562.6 s host time at list price, rounded up); cautious 1.39 shown, not charged. Hold 4.00 released. Ledger 114.60 → 118.60 (hold) → 115.89 of 200 USD. Addendum `BUDGET_RECONCILIATION_ADDENDUM_CLAUDE_MOUTHTRAIN_C59_20261022T155803Z.json` sha256 `8bd52568aacb1f9f86c22a1379708ea1fd0f27979b237c7f10604c02833c6fc9`.
- Cleanup verified three ways (controller `PRESERVED_AND_PREFIX_PURGE_VERIFIED`, independent `VERIFIED`, direct read-only look: no live instance, no volume, empty prefix). Proof sha256 `ad340946a54f8484fd313aa551c7d882e297e12e06f29cb5fcfba1ce55666960`.
- Deliverable `aws-c59-a1-deliverable.zip` sha256 `ef5b08e7ffb13bbdafef74b1f3d7d442084b6954b6484f5041a7c75be0199330` (125,084,874 bytes); all 35 files of SHA256SUMS.txt verify on the laptop. Weights (not in git): A4-s1 `6d7e0506…`, A4-s2 `a4bac849…`, A4-s3 `aea0eca1…`, A5-s1 `7323bb46…`. Backup `D:/tksCAS-archive/mouth_train_c59_run_20261022/` (35 files, zip sha matched 3 times).
- Claim status: the mouth is `NOT LICENSED`; HELM keeps the template talk layer. Nothing is switched on.
