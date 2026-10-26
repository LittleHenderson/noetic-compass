# Label-agreement verdict — result

Run 2026-10-05, 00:03 to 00:29 PDT. Plan `06_VERDICT_PLAN_v1_2.md`, guide `02_LABELING_GUIDE_v1_2.md` (sha256 `3ed4196dbfb0ad0d96a785f03929229e18d23ff226c7687df363d683bfd8022e`). Every number and outcome below was printed by `tools/verdict.py`, which was unchanged since the seal. Program report: `VERDICT_REPORT.json`, sha256 `52100ec2ae10e9b6b6535bdca1accd89270c797f5f6de88ae4b755557e7f3f33`.

## Short answer

**Eight of the nine Noetics missed the bar. Only `^1` Mind passed.**

The two label teams agree well on **which passages contain** each Noetic. They do not agree closely enough on **exactly which words** occupy it, for which Mind, relative to what. The bar was set on the second, stricter thing, before the run.

Under the plan's rule, `^2` to `^9` are `NOT_LABELABLE_UNDER_THIS_METHOD`. That is a statement about this guide and these two teams. It is not a statement about CAS.

## The run was valid

| Check | Result |
|---|---|
| Passages written by Gemini from the plain brief | 440 |
| Dropped by the mechanical check (forbidden word) | 12 |
| Sealed before any label existed | 428, sha256 `9aa3fc6d3e71bbf7a74a2fff59bdda2a40c6c32db506d4c4a3ce912ced3d760a` |
| Team A (nine Claude Sonnet sub-agents) | 428 of 428 labeled |
| Team B (DeepSeek `deepseek-chat`) | 428 of 428 labeled |
| Passages excluded | 0 |
| Entries dropped for a bad quote | 0 and 0 |
| Seal, guide and program hashes at scoring time | all matched |

## Outcome per Noetic

Strict agreement: of the passages where at least one team gave a clear entry, the share where both did and pointed to the same reading (same words, same Mind, same related thing). Bar 0.80. Kappa: agreement on whether the Noetic is in the passage, after removing chance. Bar 0.60.

| Noetic | Team A marked | Team B marked | Cases | Strict agreement [95% interval] | Kappa [95% interval] | Outcome |
|---|---:|---:|---:|---|---|---|
| `^1` Mind | 368 | 373 | 373 | 365/373 = 0.979 [0.958, 0.989] | 0.950 [0.899, 0.989] | 🏆 `LABELABLE_UNDER_THIS_METHOD` |
| `^2` Positive | 64 | 60 | 65 | 47/65 = 0.723 [0.604, 0.817] | 0.943 [0.890, 0.982] | 👎 `NOT_LABELABLE_UNDER_THIS_METHOD` |
| `^3` Negative | 47 | 51 | 56 | 35/56 = 0.625 [0.494, 0.740] | 0.839 [0.747, 0.914] | 👎 `NOT_LABELABLE_UNDER_THIS_METHOD` |
| `^4` Vibration | 68 | 84 | 96 | 44/96 = 0.458 [0.362, 0.558] | 0.681 [0.586, 0.768] | 👎 `NOT_LABELABLE_UNDER_THIS_METHOD` |
| `^5` Female | 111 | 128 | 129 | 85/129 = 0.659 [0.574, 0.735] | 0.890 [0.843, 0.934] | 👎 `NOT_LABELABLE_UNDER_THIS_METHOD` |
| `^6` Male | 84 | 95 | 100 | 54/100 = 0.540 [0.443, 0.634] | 0.852 [0.785, 0.910] | 👎 `NOT_LABELABLE_UNDER_THIS_METHOD` |
| `^7` Rhythm | 62 | 70 | 79 | 34/79 = 0.430 [0.327, 0.540] | 0.767 [0.671, 0.848] | 👎 `NOT_LABELABLE_UNDER_THIS_METHOD` |
| `^8` Above/Cause | 59 | 64 | 64 | 37/64 = 0.578 [0.456, 0.691] | 0.953 [0.906, 0.990] | 👎 `NOT_LABELABLE_UNDER_THIS_METHOD` |
| `^9` Below/Effect | 59 | 64 | 64 | 37/64 = 0.578 [0.456, 0.691] | 0.953 [0.906, 0.989] | 👎 `NOT_LABELABLE_UNDER_THIS_METHOD` |

- Every Noetic had at least 50 cases and at least 50 passages where neither team marked it, so every Noetic got a verdict.
- Kappa cleared its 0.60 bar for all nine. Strict agreement cleared its 0.80 bar for `^1` only. For `^2`, the top of the interval (0.817) reaches above the bar; the measured value does not. For the other seven, the whole interval is below 0.80.

Reported with no bar:

| Row | Team A | Team B | Cases | Strict agreement | Kappa |
|---|---:|---:|---:|---|---|
| `^9` reached by reasoning (rule 15b) | 32 | 44 | 46 | 29/46 = 0.630 | 0.770 |
| uncertain `^8` (rule 15d) | 59 | 59 | 65 | 37/65 = 0.569 | 0.882 |
| uncertain `^9` (rule 15d) | 59 | 59 | 65 | 35/65 = 0.538 | 0.882 |

Both teams marked "none of these" on almost the same passages: 59 and 55, agreeing on 424 of 428.

## Where the misses are

A case that did not count as the same reading is one of three kinds:

| Noetic | Cases | Same reading | Only one team marked it | Both marked it, different words | Same words, different Mind or related thing |
|---|---:|---:|---:|---:|---:|
| `^1` | 373 | 365 | 5 | 3 | 0 |
| `^2` | 65 | 47 | 6 | 12 | 0 |
| `^3` | 56 | 35 | 14 | 7 | 0 |
| `^4` | 96 | 44 | 40 | 3 | 9 |
| `^5` | 129 | 85 | 19 | 25 | 0 |
| `^6` | 100 | 54 | 21 | 4 | 21 |
| `^7` | 79 | 34 | 26 | 5 | 14 |
| `^8` | 64 | 37 | 5 | 15 | 7 |
| `^9` | 64 | 37 | 5 | 8 | 14 |

What this table shows, as description only (it changes no outcome):

- **`^8`/`^9`:** in the 57 passages written as "something noticed brings a different thing to thought", both teams gave a clear pair in 57 of 57. They miss on the stretch of words. Examples from the report: "Its lanolin scent" against "Its lanolin scent filled the small shop"; "The dry, dusty scent of ancient paper" against "This smell" (a later mention of the same thing). In 22 of the 27 misses for `^8`, both teams marked a pair and quoted a different stretch: 15 on the trigger itself and 7 on the thing it is tied to.
- **`^4` Vibration and `^7` Rhythm:** the largest share of misses is one team marking it and the other not (40 of 52, and 26 of 45). That is disagreement about whether the Noetic is there at all. They also have the lowest kappa (0.681 and 0.767).
- **`^5` and `^7` are confused with each other:** in 28 places the same words were `^5` for one team and `^7` for the other.
- **`^6` Male:** 21 of 46 misses are the same words with a different "what it is part of".
- **`^3` Negative:** 14 of 21 misses are one team only.

Agreement on the words alone, without the Mind and related-thing requirement, is also below 0.80 for `^2` to `^9` (0.552 to 0.797). So the related-thing requirement is not the only reason for the misses.

## What this means

1. **There is no word-level answer key yet for `^2` to `^9`.** A reader cannot be scored on "did it point to the right words" against labels that two teams do not agree on.
2. **Passage-level agreement is high.** Whether a Noetic is in a passage is something the two teams agree on (kappa 0.68 to 0.95). That is a weaker kind of label. The plan did not set it as the pass criterion, and I am not promoting it to one.
3. **The canon definitions were not the obstacle in the way I feared for `^8`/`^9`.** After the owner's ruling, the teams agree that a pair is there. The pointing convention is what fails.

## Limits

- Two model families only. Agreement between two language models is not correctness.
- The passages were written by a third model to a brief. They are cleaner than found text.
- The "same words" test is mechanical (shared content words). It cannot see that "This smell" and "The dry, dusty scent of ancient paper" are the same thing.
- One labeling pass per team. No relabeling was done, and none is allowed on these passages.

## For the owner

- `VERDICT_REPORT.owner_sample.json` holds 30 disagreements and 20 agreements drawn with a fixed seed, with the passage text and both teams' entries. Reading ten of them will show whether the teams disagree about meaning or about where to draw the quote.
- A new attempt needs new passages and a new plan version. Options are in the chat report.

## Cost

No AWS. DeepSeek: 2,327,821 input and 88,948 output tokens for the 428 verdict calls; estimated under 1 USD for the night including practice rounds and reviews. I have not seen the provider's bill. Gemini: free tier. Claude sub-agents for the verdict: about 1.39 million tokens across nine agents.
