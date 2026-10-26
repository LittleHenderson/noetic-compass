# HELM training data scope — owner decision, 2026-10-26

Owner: **"HELM IS A RESEARCH PROJECT NOT COMMERCIAL USE."**

Recorded as a scope decision because it changes which corpora may be used for training.

## What this allows

- Research use of dialogue datasets whose licences are **non-commercial**, including:
  - DailyDialog — **CC BY-NC-SA 4.0**
  - EmpatheticDialogues — **CC BY-NC 4.0**
- Attribution is kept on every row (source and licence fields).
- Share-alike is respected for the adapted dataset: this repository is a research record, not a commercial product.

## What it does not allow

- **Model-generated corpora remain excluded.** ShareGPT, LMSYS-Chat-1M, UltraChat and SODA are outputs of other models.
  Using them as training targets would break the project's no-foreign-distillation rule regardless of licence.
- **Commercial shipping of weights trained on NC data.** If HELM ever becomes a product, any checkpoint trained on
  DailyDialog or EmpatheticDialogues must be excluded or re-reviewed, because those licences forbid commercial use.
  Keep the source field on every row so this can be done mechanically.

## What was built under this decision

`build_public_corpus.py` (OASST1, Apache-2.0) and `build_warm_corpus.py` (DailyDialog + EmpatheticDialogues):

| Source | Licence | Pairs |
|---|---|---:|
| DailyDialog | CC BY-NC-SA 4.0 | 68,548 |
| EmpatheticDialogues | CC BY-NC 4.0 | 39,776 |
| OpenAssistant OASST1 (human-written only) | Apache-2.0 | 6,354 |
| **Total** | | **114,678** |

Filters applied: English, 2–60 words per turn, no links, no code, no assistant boilerplate, deduplicated by
(user, reply), `synthetic` rows dropped from OASST1.

## Known quality problems, before any training

1. **Role direction is unknown in DailyDialog.** Utterances are unlabelled and alternate, so half the pairs may be
   "reply → user" instead of "user → reply". This teaches conversational rhythm but muddies who is speaking.
2. **EmpatheticDialogues includes crude replies.** 87 replies contain profanity and some mock the user. They must be
   filtered before the model learns them as HELM's voice.
3. **OASST1 has parent mismatches.** Example: a question about contrastive learning paired with a reply asking for a
   formal letter. Threading needs a consistency check or those rows must be dropped.
4. **5,234 replies are shorter than four words**, which teaches clipped answers.

None of this is fatal; all of it must be fixed before the corpus is used, or the model will learn the noise.

## Artifacts

- Builders: `build_public_corpus.py`, `build_warm_corpus.py`.
- Stats: `public_corpus_stats.json`.
- Sample committed: `public_turns_sample.jsonl` (203 rows).
- Full corpus (34.4 MB, 114,678 rows) kept in the training payload and uploaded to S3 for durability.
