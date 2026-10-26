# Label-agreement practice round 2 — report

Date: 2026-10-04, about 22:52 to 23:30 PDT. No AWS. Outside services: Gemini (writer), DeepSeek (label team).

**This is still practice, not a verdict.** Its purpose was to see whether guide v0.2 reads the same way to two teams from different model families.

## What was done

- **Passages:** 30 fresh passages (45 to 67 words), written by Gemini `gemini-2.5-flash` from a plain brief with no CAS words. The writer never saw the guide. Ten new settings, none shared with the first look.
- **Label teams, working apart, guide v0.2:**
  - Claude (Sonnet) sub-agent: 30 of 30 labeled.
  - DeepSeek `deepseek-chat`: 30 of 30 labeled, one passage per call.
  - Gemini `gemini-2.5-flash`: 17 of 30 labeled, then refused the rest with "too many requests" (HTTP 429). A paced retry was still being refused, so I stopped it. Gemini's labels are not used in the numbers below. Gemini was also the writer, so it would not have been an independent third team anyway.

## Result: Claude team against DeepSeek team

Both teams marked the same four passages "none of these" (30 of 30 agreement on that).

| Noetic | Claude marked | DeepSeek marked | Both | Plain agreement | Kappa | Same words when both marked |
|---|---:|---:|---:|---|---:|---|
| `^1` Mind | 26 | 26 | 26 | 30/30 = 1.000 | 1.000 | 26 of 26 |
| `^2` Positive | 8 | 8 | 8 | 30/30 = 1.000 | 1.000 | 7 of 8 |
| `^3` Negative | 7 | 7 | 7 | 30/30 = 1.000 | 1.000 | 7 of 7 |
| `^4` Vibration | 7 | 8 | 7 | 29/30 = 0.967 | 0.911 | 7 of 7 |
| `^5` Female | 11 | 12 | 11 | 29/30 = 0.967 | 0.930 | 11 of 11 |
| `^6` Male | 2 | 3 | 2 | 29/30 = 0.967 | 0.783 | 2 of 2 |
| `^7` Rhythm | 5 | 6 | 5 | 29/30 = 0.967 | 0.889 | 5 of 5 |
| `^8` Above/Cause | 7 | 12 | 7 | 25/30 = 0.833 | 0.627 | 7 of 7 |
| `^9` Below/Effect | 7 | 11 | 7 | 26/30 = 0.867 | 0.689 | 7 of 7 |

Full counts and all 14 disagreements: `agreement_claude_vs_deepseek.json`.

## Compared with the first look (cross-family pairs)

| Noetic | First look, guide v0.1 (kappa, two cross-family pairs) | Round 2, guide v0.2 (kappa) |
|---|---|---|
| `^1` | 0.804 and 0.275 | 1.000 |
| `^4` | 0.076 and 0.091 | 0.911 |
| `^5` | 0.607 and 0.607 | 0.930 |
| `^8` | 0.750 and 0.750 | 0.627 |
| `^9` | 0.659 and 0.659 | 0.689 |

**Do not read this as proof the guide changes caused the improvement.** The passages are different, a different model wrote them, and they are shorter and often more explicit. The fair statement is: on this second practice set, with guide v0.2, plain agreement between the two teams was 0.967 or higher on seven of the nine Noetics. On the pair `^8`/`^9` it was lower (0.833 and 0.867), and that pair is the one that remains unsettled.

## The one open problem: reading a sign through experience

All five passages where the teams differ on `^8`/`^9` are the same kind of moment. An experienced person notices a sign and at once knows what it means:

| Passage | The sign | What comes to the Mind |
|---|---|---|
| Q03 | the shape of a coming squall | a storm years ago that nearly took his boat |
| Q11 | the yeast was a little sluggish | the humidity in the air was off |
| Q19 | a new patch of loose gravel | how the bus would handle the rough surface |
| Q27 | a sharp, intermittent knock in the dryer | a shoe had worked its way free |
| Q10 | a loud bang of a metal tray | (she flinched, and barely registered it) |

DeepSeek marked these as an `^8`/`^9` pair. The Claude team marked no pair and treated them as what the Mind is made of (`^5`) at work.

Both readings can be defended from the canon, which is why this needs the owner:

- **For the pair:** the definition of `^8` is "An Idea that triggers a different Idea than itself to come to Mind." A knock bringing "a shoe" to Mind fits those words.
- **Against the pair:** Clarification 6 says `^8` is associative triggering ("that reminds me"), not reasoning, and that working out a cause is `^6` with `^9`. Knowing what a sign means is closer to working it out, even when it is instant.

The guide cannot be frozen for the verdict until this is ruled. I have not chosen a reading.

## Smaller notes from the label teams

- `^1`: unclear for people only heard speaking, and for animals shown only by behaviour.
- `^2`: unclear whether "absorbed in" counts as being attracted toward.
- `^6`: unclear whether the contents of a remembered scene, or a smell's ingredients, are "named parts". `^6` appeared in only 2 to 3 passages, so its number means little. The verdict set must ask writers for more of it.
- `^5`/`^7`: "years of early mornings" has a repeating unit but no rate words.

## Next

1. Owner ruling on reading a sign through experience.
2. Guide frozen as version 1.0 with that ruling.
3. Verdict set: at least 50 fresh passages per Noetic, writer blind to the guide, two label teams from different families, both bars (plain agreement at least 80%, kappa at least 0.6), counts and uncertainty shown.

## Correction added 2026-10-04 23:55 PDT: the numbers above flatter the agreement

An outside reviewer rejected my verdict plan because "plain agreement" counted the passages where neither team marked a Noetic. Those passages are most of the 30, so the share looked high whatever the teams did on the real cases. The reviewer was right.

The same round-2 labels under the stricter measure now fixed in plan v1.1 (cases only; clear entries only; the Mind and the related thing must agree too):

| Noetic | As reported above | Stricter measure |
|---|---|---|
| `^1` | 30/30 = 1.000 | 26/26 = 1.000 |
| `^2` | 30/30 = 1.000 (29/30 on words) | 4/8 = 0.500 |
| `^3` | 30/30 = 1.000 | 6/7 = 0.857 |
| `^4` | 29/30 = 0.967 | 4/7 = 0.571 |
| `^5` | 29/30 = 0.967 | 9/11 = 0.818 |
| `^6` | 29/30 = 0.967 | 0/3 = 0.000 |
| `^7` | 29/30 = 0.967 | 2/5 = 0.400 |
| `^8` | 25/30 = 0.833 | 5/9 = 0.556 |
| `^9` | 26/30 = 0.867 | 5/9 = 0.556 |

My sentence that plain agreement was "0.967 or higher on seven of the nine Noetics" is true of that measure and misleading about the labeling. On the fair measure, only `^1`, `^3` and `^5` reached 0.80 in this practice round, on 5 to 26 cases each. The earlier numbers are left in place above so the record shows both.
