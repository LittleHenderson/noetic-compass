# Stage 28B Noetic Colloquialism Realization

**Status:** `NULL_NOETIC_COLLOQUIALISM_REALIZATION_NOT_ESTABLISHED`

## Plain English

This report tests the colloquialism route: natural-language Noetic phrases are processed by Pythia, then the existing Stage 9 Noetic probe reads the resulting layer-5 phrase-token hidden state.

## Probe And Fixture

- Model: `EleutherAI/pythia-160m`
- Runtime device: `cpu`
- Locked probe readout: `X_focus` layer `5`
- Runtime readout: `phrase_first_token` layer `5`
- Noetic probe test accuracy: `0.9145`
- Artifact contract: `LOCKED_ARTIFACT_MATCH`
- Fixture rows: `40`

## Metrics

- Exact accuracy: `0.1250` (5 / 40)
- Exact-binomial p vs 10-way chance: `0.370982`
- Top-2 accuracy: `0.1500` (6 / 40)
- Mean target probability: `0.1240`
- Target probability lift over chance: `0.0240`
- Involution target > partner share: `0.5000` (12 / 24)
- Mean target-partner probability margin: `0.1167`

## Per-Noetic Readout

| Noetic | Name | Exact | Top-2 | Mean target probability | Predicted counts |
|---|---|---:|---:|---:|---|
| `^1` | Mind | 0.000 | 0.000 | 0.001 | `{'^2': 1, '^8': 2, '^9': 1}` |
| `^2` | Positive | 0.000 | 0.250 | 0.000 | `{'^8': 4}` |
| `^3` | Negative | 0.000 | 0.000 | 0.000 | `{'^2': 1, '^8': 3}` |
| `^4` | Vibration | 0.000 | 0.000 | 0.000 | `{'^2': 1, '^8': 3}` |
| `^5` | Female | 0.000 | 0.000 | 0.000 | `{'^3': 1, '^8': 2, '^9': 1}` |
| `^6` | Male | 0.000 | 0.000 | 0.000 | `{'^8': 4}` |
| `^7` | Rhythm | 0.000 | 0.000 | 0.000 | `{'^8': 4}` |
| `^8` | Above/Cause | 0.750 | 0.750 | 0.736 | `{'^8': 3, '^9': 1}` |
| `^9` | Below/Effect | 0.500 | 0.500 | 0.501 | `{'^4': 1, '^6': 1, '^9': 2}` |
| `^0` | Idea | 0.000 | 0.000 | 0.002 | `{'^1': 1, '^4': 1, '^8': 1, '^9': 1}` |

## Row Audit

| Target | Phrase | Predicted | Exact | Target probability | Focus token |
|---|---|---|---|---:|---|
| `^1` | paying attention | `^8` | `False` | 0.000 | `pay` |
| `^1` | making up my mind | `^8` | `False` | 0.000 | `making` |
| `^1` | using my head | `^9` | `False` | 0.000 | `using` |
| `^1` | becoming aware | `^2` | `False` | 0.003 | `be` |
| `^2` | drawn to it like a moth to a flame | `^8` | `False` | 0.000 | `drawn` |
| `^2` | speaks to me | `^8` | `False` | 0.000 | `spe` |
| `^2` | can't resist it | `^8` | `False` | 0.000 | `can` |
| `^2` | pulled toward it | `^8` | `False` | 0.000 | `pull` |
| `^3` | can't stomach it | `^8` | `False` | 0.000 | `can` |
| `^3` | rubs me the wrong way | `^2` | `False` | 0.000 | `rub` |
| `^3` | wouldn't touch it with a ten-foot pole | `^8` | `False` | 0.000 | `would` |
| `^3` | pushed away from it | `^8` | `False` | 0.000 | `p` |
| `^4` | hit me hard | `^8` | `False` | 0.000 | `hit` |
| `^4` | struck a chord | `^8` | `False` | 0.000 | `stru` |
| `^4` | resonated with me | `^2` | `False` | 0.000 | `res` |
| `^4` | made an impression | `^8` | `False` | 0.000 | `made` |
| `^5` | we are the sum of our experiences | `^3` | `False` | 0.000 | `we` |
| `^5` | it's who I am | `^9` | `False` | 0.000 | `it` |
| `^5` | part of what makes me me | `^8` | `False` | 0.000 | `part` |
| `^5` | shaped by what came before | `^8` | `False` | 0.000 | `shaped` |
| `^6` | unpacking an idea | `^8` | `False` | 0.000 | `un` |
| `^6` | breaking it down | `^8` | `False` | 0.000 | `breaking` |
| `^6` | looking at what's underneath | `^8` | `False` | 0.000 | `looking` |
| `^6` | pulling apart the argument | `^8` | `False` | 0.000 | `pull` |
| `^7` | practice makes perfect | `^8` | `False` | 0.000 | `practice` |
| `^7` | you are what you repeatedly do | `^8` | `False` | 0.000 | `you` |
| `^7` | getting into a groove | `^8` | `False` | 0.000 | `getting` |
| `^7` | muscle memory | `^8` | `False` | 0.000 | `mus` |
| `^8` | that reminds me | `^9` | `False` | 0.000 | `that` |
| `^8` | one thing leads to another | `^8` | `True` | 0.945 | `one` |
| `^8` | triggered a memory | `^8` | `True` | 1.000 | `trig` |
| `^8` | made me think of something else | `^8` | `True` | 1.000 | `made` |
| `^9` | it just popped into my head | `^9` | `True` | 1.000 | `it` |
| `^9` | out of nowhere I thought of it | `^6` | `False` | 0.000 | `out` |
| `^9` | the thought came to me | `^4` | `False` | 0.002 | `the` |
| `^9` | it just clicked | `^9` | `True` | 1.000 | `it` |
| `^0` | it's all in your head | `^9` | `False` | 0.000 | `it` |
| `^0` | a thought on my mind | `^1` | `False` | 0.006 | `a` |
| `^0` | something on my mind | `^8` | `False` | 0.000 | `something` |
| `^0` | the idea itself | `^4` | `False` | 0.003 | `the` |

## Boundary

Stage 28B is a single-Noetic colloquial phrase realization probe on Pythia-160M. It does not prove Noetic clusters, exact neurons, complete circuits, raw CAS-symbol understanding, free-form generation control, or cross-model generality.
