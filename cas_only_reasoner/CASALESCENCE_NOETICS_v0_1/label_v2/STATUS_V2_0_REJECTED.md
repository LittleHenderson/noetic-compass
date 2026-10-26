# Labeling method v2.0: built, reviewed, rejected, never used

Written 2026-10-05, 07:20 PDT, by the operator (Claude Code). No passage was written, sealed or labeled under v2.0. No result exists for it.

## What v2.0 was

- Guide `02_LABELING_GUIDE_v2_0.md` (108,661 bytes), plan `09_LABEL_AGREEMENT_PLAN_v2_0.md` (99,597 bytes), sign-off sheet `label_v2/OWNER_SIGNOFF_SHEET.md`, tools `tools/*_v2.py`, fixture `label_v2/fixture/`.
- It did the three things the owner asked for: a short label plus the full supporting quote, and extra and missing roles counted apart.
- It also changed WHEN a role counts as present: eight "held" kinds and seventeen "working lines". That part went beyond the owner's direction.

## Reviews

| Review | Who | Result |
|---|---|---|
| Round 1, three lenses | Claude reviewers | All three REJECT: 3 blocking, 19 major findings. Fixers handled them; 2 major findings on the seal tool stayed open. Record: `label_v2/BUILD_REVIEW_ROUND1.json` |
| Guide and sign-off sheet | `deepseek-v4-pro` (answered by `deepseek-v4-pro`) | REJECT: 3 blocking, 3 major. Record: `label_v2/OUTSIDE_REVIEW_GUIDE_AND_SHEET.md` |
| Plan | `deepseek-v4-pro` (answered by `deepseek-v4-pro`) | REJECT: 1 blocking, 4 major. Record: `label_v2/OUTSIDE_REVIEW_PLAN.md` |

The outside reviewer's blocking findings, in one line each:

1. Working lines contradict the canon table of sayings ("Muscle memory." and "Practice makes perfect." are listed under `^7`; the guide sent them elsewhere).
2. Two guide rules order opposite things for the same sentence (rule 10(a) against hold code H7-UNBROKEN).
3. "Clue" entries were written as `^6` with no whole, which does not fit the `^6` definition.
4. (Plan) The owner could change items after seeing practice labels and waive the practice guard, which allows tuning after the fact.

The reviewer also said the held kinds and working lines are not needed for the owner's three aims and add risk.

## Decision

v2.0 is dropped. It is kept here as a record and is not to be used for labeling.

The replacement is v2.1 LEAN (`02_LABELING_GUIDE_v2_1.md`, `09_LABEL_AGREEMENT_PLAN_v2_1.md`, `label_v21/`): guide v1.2 with only the label-plus-quote entry format, one short pointing rule, and entry-by-entry counting. Rules 1 to 15 and the definitions stay byte-identical. Nothing about presence is changed.

## What is still useful from v2.0

`design_v2/labeling_final.json`, field `spec.questions_only_the_owner_can_settle`, lists 23 places where it is unclear what a definition covers (for example: is comfort without a pull `^2`; is a plain job title `^5`). They are the owner's to rule on, whenever the owner wishes. No study step waits on them.
