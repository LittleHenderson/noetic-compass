# 03 — Scorer rules for model B's answers, version 0.1 (proposed, not yet reviewed, not yet run)

Purpose: decide, before any paid call, how an answer from model B is read and scored. The old scorer gave zero to an answer wrapped in a code fence, and that hid everything else.

These rules change nothing about the run of 2026-10-04. That run keeps its recorded result: program decision `INCONCLUSIVE`, every group 0 of 8. It is never rescored as a new win. The old outputs may be re-described with the categories below, clearly marked as a description after the fact.

## The rule, in order

Given the raw text model B produced and whether it ran out of length:

1. **Cut off.** If the answer ran out of its allowed length without ending, the category is `CUT_OFF`. Stop.
2. **Trim.** Remove spaces and line breaks at the start and end.
3. **One fence allowed.** If the whole text is exactly one fenced block (three backticks, an optional label of letters only such as `json`, a line break, the content, a line break, three backticks) take the content and trim it. Any text before or after the fence, or more than one fence, is `FORMAT_FAIL`.
4. **Parse.** The text must be valid JSON. If not: `FORMAT_FAIL`.
5. **Shape.** It must be one object with exactly one key, `answer`. A missing key, an extra key, a list or a bare value at the top is `FORMAT_FAIL`.
6. **Allowed values.** The value must be a whole number, or a non-empty string of at most 128 characters, or a list of at most 16 such strings. Anything else (decimal, true/false, null, empty string, nested object) is `FORMAT_FAIL`.
7. **Type.** If the value's type differs from the task's answer type (for example the string `"4"` where the answer is the number `4`), the category is `TYPE_MISMATCH`. Nothing is converted.
8. **Compare.** Equal to the task's answer: `CORRECT`. Otherwise: `WRONG`. Strings and lists are compared exactly, including order and letter case.

## What is counted

- **Primary score:** `CORRECT` = 1. Every other category = 0.
- **Always reported beside it, per group:** the count in each of the five categories `CORRECT`, `WRONG`, `TYPE_MISMATCH`, `FORMAT_FAIL`, `CUT_OFF`. Formatting failures are never mixed into "wrong answers".
- **Secondary view, labeled as secondary:** the same table with `TYPE_MISMATCH` re-read after converting a string of digits to a whole number. It is shown so a reader can see how much strict typing matters. No pass rule may use it.

## Fixed in advance

- The same rule applies to every group. The scorer does not know which group an answer came from.
- The answer format asked of model B is the same in every group.
- The rule is frozen with the package version. A change after any paid call needs a new version and a new review.
- A group whose `FORMAT_FAIL` plus `CUT_OFF` share is above 25% on the final cases is reported as "format floor" for that group, and no gain or loss is read from it.
- Before a comparison is run, model B alone must be `CORRECT` on between 30% and 70% of practice tasks. Outside that range the task set is changed first. Practice tasks are never final tasks.

## Known-example check (must pass before any paid model call)

`scorer_examples_v0_1.json` holds 30 hand-written answers with the category each must receive. The new scorer must give exactly those categories. The check runs on AWS as a software test; it loads no model.

## Differences from the old scorer

| Point | Old scorer | This proposal |
|---|---|---|
| Answer inside one code fence | malformed, score 0 | read the content |
| Text around the fence, several fences | malformed | `FORMAT_FAIL` (same outcome, named) |
| Wrong type | score 0, not named | `TYPE_MISMATCH`, counted separately |
| Report | one number per group | one number plus five category counts |
| Floor guard | none | a group above 25% format failures is not read |
| Ceiling/floor on task difficulty | none | B alone must be 30% to 70% right on practice tasks |

## Open points for the reviewer

1. Should a fenced answer with the label `JSON` in capitals, or with spaces after the backticks, be accepted? Proposed: label of letters only, any case; no other characters.
2. Is 25% the right format-floor line? It is a proposal.
3. Should `TYPE_MISMATCH` stay at zero in the primary score? Proposed: yes, so the primary score stays strict and comparable with the old rule on this point.
