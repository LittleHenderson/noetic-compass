# Label-agreement first look — report

Date: 2026-10-04, about 22:35 to 22:50 PDT. Cost: no AWS; one outside service (DeepSeek), 94,108 input and 9,651 output tokens.

**This is not a verdict.** Its only purpose was to find where labeling guide v0.1 is unclear. Nothing here says a Noetic can or cannot be labeled reliably.

## What was done

- **Passages:** 40 short everyday passages (56 to 81 words), written by a Claude sub-agent from a plain brief with no CAS words. File sha256 `5f5d40d0975a270845bee1f697183a22996f84cc49f6761b2bceb8de46fd5238`. Five are physical-only on purpose.
- **Label teams, working apart, same guide (v0.1), same passages:**
  - Team 1: Claude (Opus) sub-agent.
  - Team 2: Claude (Sonnet) sub-agent.
  - Team 3: DeepSeek `deepseek-chat`, one passage per call.
- **Measures per Noetic:** (a) plain agreement on whether the Noetic is in the passage; (b) the same after removing chance agreement (Cohen's kappa); (c) when both marked it, whether they pointed to the same words (at least half the content words of the shorter quote shared).

## Limits, stated first

- The passages were written to cover four kinds of moment. They are practice material. They are not unmarked test cases and may never be used as such.
- The writer was not blind: Claude sub-agents in this project receive instructions that contain the definitions.
- Teams 1 and 2 are the same model family. Only the pairs with Team 3 cross families.
- 40 passages; each Noetic appears in only 5 to 34 of them. The numbers are rough.

## Results

All three teams marked the same five passages "none of these" (40 of 40 agreement on that).

Passages in which each team marked the Noetic:

| Noetic | Team 1 | Team 2 | Team 3 |
|---|---:|---:|---:|
| `^1` Mind | 34 | 19 | 34 |
| `^2` Positive | 11 | 10 | 11 |
| `^3` Negative | 11 | 10 | 11 |
| `^4` Vibration | 11 | 10 | 2 |
| `^5` Female | 9 | 9 | 16 |
| `^6` Male | 6 | 5 | 5 |
| `^7` Rhythm | 5 | 5 | 6 |
| `^8` Above/Cause | 15 | 15 | 20 |
| `^9` Below/Effect | 15 | 15 | 22 |

Agreement, shown as plain agreement / kappa / same words when both marked:

| Noetic | Team 1 vs Team 2 (same family) | Team 1 vs Team 3 (cross family) | Team 2 vs Team 3 (cross family) |
|---|---|---|---|
| `^1` | 25/40 = 0.625 / 0.275 / 19 of 19 | 38/40 = 0.950 / 0.804 / 30 of 33 | 25/40 = 0.625 / 0.275 / 17 of 19 |
| `^2` | 39/40 = 0.975 / 0.935 / 10 of 10 | 40/40 = 1.000 / 1.000 / 11 of 11 | 39/40 = 0.975 / 0.935 / 10 of 10 |
| `^3` | 39/40 = 0.975 / 0.935 / 10 of 10 | 40/40 = 1.000 / 1.000 / 9 of 11 | 39/40 = 0.975 / 0.935 / 9 of 10 |
| `^4` | 39/40 = 0.975 / 0.935 / 10 of 10 | 29/40 = 0.725 / 0.076 / 1 of 1 | 30/40 = 0.750 / 0.091 / 1 of 1 |
| `^5` | 40/40 = 1.000 / 1.000 / 9 of 9 | 33/40 = 0.825 / 0.607 / 9 of 9 | 33/40 = 0.825 / 0.607 / 9 of 9 |
| `^6` | 37/40 = 0.925 / 0.684 / 4 of 4 | 37/40 = 0.925 / 0.684 / 3 of 4 | 38/40 = 0.950 / 0.771 / 3 of 4 |
| `^7` | 40/40 = 1.000 / 1.000 / 5 of 5 | 39/40 = 0.975 / 0.895 / 5 of 5 | 39/40 = 0.975 / 0.895 / 5 of 5 |
| `^8` | 40/40 = 1.000 / 1.000 / 15 of 15 | 35/40 = 0.875 / 0.750 / 12 of 15 | 35/40 = 0.875 / 0.750 / 12 of 15 |
| `^9` | 40/40 = 1.000 / 1.000 / 15 of 15 | 33/40 = 0.825 / 0.659 / 14 of 15 | 33/40 = 0.825 / 0.659 / 15 of 15 |

Full counts and every disagreement: `agreement_team1_vs_team2.json`, `agreement_team1_vs_team3.json`, `agreement_team2_vs_team3.json`.

## What the first look showed about the guide

1. **`^1` Mind had no workable rule.** Two teams listed nearly every Mind (34 passages); one listed a Mind only on a clear act of awareness (19). The guide's rule 4 allowed both readings.
2. **`^4` Vibration split by family.** The two Claude teams marked it in 10 to 11 passages and agreed with each other. DeepSeek marked 2. The guide did not say what counts as "words that state the degree".
3. **`^5` Female and the `^8`/`^9` pair were marked more often by DeepSeek** (16 against 9; 20 to 22 against 15). The teams reported the same causes: recall by an expert after a cue; a link that is implied but not stated; whether a long stretch of time is `^5` or `^7`.
4. **`^2`, `^3` and `^7` were agreed on by all pairs** on this practice set.
5. **`^6` Male was rare** (5 to 6 passages), so its numbers mean little. Teams asked whether step-by-step reasoning counts.
6. **One measurement fault was mine.** My first word-overlap rule counted "the" as a shared word and reported false `^2`/`^3` confusions. I fixed the rule (filler words are ignored) and recomputed everything above.

## What changed in guide v0.2

Part A (the definitions) is byte-identical. Part B changes are listed at the end of `02_LABELING_GUIDE_v0_2.md`: a mechanical rule for listing Minds; what counts as stating a degree for `^4`, with a new example; when a pair may be marked; a length of time alone is `^5`, not `^7`; `^6` needs a named part; strength does not matter for `^2`/`^3`; a cue that sets off an action; ambiguous between a Noetic and nothing.

These are conventions for applying the definitions in this study. The owner may correct any of them.

## Next

A second practice round on fresh passages written by an outside model, labeled with guide v0.2, to see whether the changes helped. Only then the verdict set (at least 50 fresh passages per Noetic).
