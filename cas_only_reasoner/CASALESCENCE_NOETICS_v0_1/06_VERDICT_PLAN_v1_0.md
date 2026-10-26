# 06 — Label-agreement verdict: plan, version 1.0

Written before any verdict passage or verdict label exists. Nothing in it changes after the labels are seen.

## The question

For each Noetic `^1` to `^9`: can two independent label teams, from different model families, apply the canon definitions to unfamiliar, unmarked passages and agree on which words occupy that Noetic?

`^0` Idea is not scored (owner decision: it stays in the representation; every thing pointed to is an Idea).

## What this verdict can and cannot show

- It shows whether the labels are **consistent** between two teams. It does not show the labels are **right**. Two teams can agree and both be wrong, and two language models can share a bias.
- The passages are written by a language model, not found in the world.
- Only two model families are involved (Claude and DeepSeek).
- A Noetic that misses the bars is "not labelable under this method". That is a statement about this guide and these teams, not about CAS.

## Frozen inputs

| Item | Value |
|---|---|
| Labeling guide | `02_LABELING_GUIDE_v1_0.md`; its sha256 is recorded in `verdict/SEAL.json` before labeling starts |
| Definitions | unchanged from `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 1, commit `1c8531ea` |
| Owner's working ruling on reading a sign | `OWNER_RULING_SIGN_READING_20261004.json`, applied as guide rule 15 |

## Passages

- **Writer:** Gemini `gemini-2.5-flash`. It gets a plain brief with no CAS words and a list of forbidden words. It never sees the guide, the definitions, the labels or any reader. Tool: `tools/write_verdict_passages.py`.
- **Number:** 400, in a fixed seeded order, ten for each of 40 settings. None of the settings was used in the two practice rounds.
- **Kinds of moment asked for** (the writer is told the kind in plain words; the label teams are never told it):

| Kind | Plain description given to the writer | Passages | Meant to give cases of |
|---|---|---:|---|
| K1 | something noticed brings a quite different thing into a person's thoughts | 60 | `^8`, `^9` |
| K2 | drawn toward one thing, put off by another; something lands strongly or hardly at all | 60 | `^2`, `^3`, `^4` |
| K3 | what a person has lived or learned over years shapes how they take something now | 60 | `^5` |
| K4 | someone takes a thing apart into named pieces | 60 | `^6` |
| K5 | the same thing over and over on a schedule has changed how a person acts | 60 | `^7` |
| K6 | an experienced person notices a small sign and knows what it means | 30 | the ruled-on case (rule 15) |
| K7 | a person works through clues step by step to a conclusion | 30 | reasoning roles (rule 15b) |
| K8 | purely physical description, no person's thoughts | 20 | "none of these" |
| K9 | a person does ordinary things; nothing of likes, memories or habits is shown | 20 | `^1` only |

- **Mechanical checks only, before sealing:** a passage is dropped if it contains a forbidden word, has fewer than 30 or more than 120 words, or repeats another passage exactly. Dropped passages are counted. I do not read the passages to choose among them.
- **Seal:** the kept passages get ids `V001…`, are shuffled with a fixed seed, and their file hash is written to `verdict/SEAL.json` before any label team starts.

## Label teams

| Team | Who | How | Sees |
|---|---|---|---|
| A | Claude (Sonnet) sub-agents | eight sub-agents, 50 passages each, working apart | the guide and its own 50 passages; nothing else |
| B | DeepSeek `deepseek-chat` | one passage per call, temperature 0 | the guide and that one passage |

Neither team sees the other's labels, the kinds, the writer's brief, or the practice rounds.

## Measures, per Noetic

A team "marks" a Noetic in a passage if it gives at least one entry for it, clear or uncertain.

1. **Strict agreement:** the share of passages where the teams agree on whether the Noetic is there and, when both mark it, point to the same words. "Same words" means at least half of the content words of the shorter quote are shared, for at least one pair of entries.
2. **Agreement after removing chance** (Cohen's kappa) on whether the Noetic is there.
3. Shown with each: the counts, a 95% interval (Wilson for the share; resampling the passages 2,000 times with seed 20261005 for kappa).
4. Also reported, with no bar: how often both pointed to the same words; which Noetics get confused on the same words; for the `^8`/`^9` pair, how the teams' "clear" and "uncertain" marks line up; a breakdown by the writer's kind; the same table counting clear entries only.

## Bars and outcomes

| Outcome | Rule |
|---|---|
| `LABELABLE_UNDER_THIS_METHOD` | at least 50 passages in which at least one team marks the Noetic, strict agreement at least 0.80, and kappa at least 0.60 |
| `NOT_LABELABLE_UNDER_THIS_METHOD` | at least 50 such passages, and either number below its bar |
| `NOT_ENOUGH_CASES` | fewer than 50 such passages; no verdict for that Noetic |

The outcome uses the measured values. The intervals are reported beside them, and the report says plainly when an interval reaches below a bar.

## When the whole verdict is invalid

- More than 5% of passages could not be labeled by one of the teams after three tries.
- More than 5% of a team's entries had to be dropped because the quoted words were not an exact copy of the passage or the Noetic was not one of `^1` to `^9`.

An invalid verdict is reported as invalid. It is not repaired by relabeling the same passages.

## Rules of conduct

- No guide change, no relabeling, no dropped passage and no changed bar after labels are seen.
- A new attempt needs new passages and a new plan version.
- The program `tools/verdict.py` computes every number and every outcome. I report its output.
- For the owner: a sample of 30 disagreements and 20 agreements, drawn with a fixed seed, with both teams' entries side by side.

## Cost

No AWS. Outside services: Gemini free tier for writing; DeepSeek for 400 labeling calls, estimated under 0.50 USD (cap 2.00). Claude sub-agents use this account's Claude allowance: eight sub-agents, about 150,000 tokens each.
