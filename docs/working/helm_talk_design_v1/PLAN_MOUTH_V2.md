# Mouth v2 — plan (design only, 0 USD; nothing built, trained or spent)

Owner's words (the click, 2026-10-22): "Yes: write a mouth v2 plan (0 USD, design only): fix the 4040 glue bug, add a sense check to the guard, more and better chat lessons, and say what it would cost; don't build or spend yet."

Starting point: MOUTH TRAIN v1 ran (job c59, 1.29 USD) and read `MOUTH_HARMED` (spec §7.128). Every number below is from the c59 outputs and the lessons, measured on the laptop at 0 USD after the run. The v1 marks stay as they are; a miss is answered with better lessons and fixes, never a looser mark (A-TALK-5 F3).

## 1. Why v1 missed (causes, with numbers)

**C1. The lock's word list was missing everyday words.** The rule that built the list (`build_mouth_data.py`, mine) dropped every word of 4+ letters found anywhere in the world's template sentences, to keep out subject nouns. It also dropped "what", "about", "from", "where", "after", "many", "came". Result: the mouth was taught lines it was then forbidden to write. Lessons fully writable under the lock: ANSWER 481/549, SAYBACK 489/539, ASK 489/565, **OFF 173/700**, SMALL 150/175, SELF 82/144, WORLD 129/159. Most-needed missing words in chat lessons: "what" (383 lines), "about" (73), "telling" (72), "from" (33), "where" (33). This is the main reason chat came out broken.

**C2. The joining step glued two allowed numbers.** The mouth wrote "40" twice; the detokenizer joined them into "4040" (my fix from A-TALK-6 G8c). One DEV line; the guard caught it; the frozen reader counts it → HARMED.

**C3. The guard checks facts and shape, not sense.** Broken chat lines pass it, so the fallback count under-reports. Blind raters preferred the template on 170 of 177 off-topic pairs while the guard rejected only 2 of 179 off-topic replies.

**C4. Round trip partly measures the ear, not the mouth.** Many "failed" fact lines are correct English the ear cannot read back: "In September the Nethercote line has fifteen buses. Earlier you said five."; "The Fallowmere yard went to the honey market at Dunholm."; "Did Moorcroft yard still have seventeen colonies in January?" (an ASK question that, naturally, does not repeat the old value but is scored against it). Round trip 512/761.

**C5. Too little variety.** Over 5 turns, 14 of 100 inputs got 1 wording and 27 got 2 (VARIED 59/100).

## 2. The fixes

**F1. Rebuild the word list (fixes C1).** Exclude only fact words (names, numbers, months: the existing `FACT_WORDS`) and the world's own thing and slot nouns from a fixed, written list. Keep every other word seen in ≥ 2 checked lessons. New gate before any training: **every situation ≥ 95 % of lessons writable under the lock**, measured on the laptop. A lesson that still cannot be written is dropped, not trained on.

**F2. Never glue separate numbers (fixes C2).** The lock already knows where a word ends; the detokenizer will join digits only inside one locked number unit, never across two. Tests first: "40 40" stays two words; "14th", "12,000", "1970s" stay whole.

**F3. A sense check in the guard (fixes C3), in two layers.**
- **Layer 1 (rules, free, ready now):** no word twice in a row ("bat bat"); no content word 3+ times. Tested on the 989 rated c59 pairs: it flags 87 lines the raters rejected and wrongly flags only 3 lines they liked. It misses 162 bad chat lines, so it is not enough alone.
- **Layer 2 (learned, needs a free census first):** the CTT's own confidence in the line it wrote (average likelihood per word), with one threshold. Before any freeze, measure it on the 989 rated c59 lines on the laptop GPU (smoke-size, 0 USD). Freeze it only if it separates the raters' "bad" from "good" at least as well as Layer 1 and catches most of the 162 lines Layer 1 misses; otherwise report it and leave it out.
- The fallback mark (≤ 1 in 1,000) is then measured with the sense check on. That makes the mark harder to meet, and honest.

**F4. More and better chat lessons (fixes C1, C3).** About 2,000 off-topic, 500 small-talk, 400 about-HELM and 400 I-don't-know inputs (v1: 297 / 70 / 56 / 60 inputs). Same writers and the same two-family check; Google joins again when its free quota allows (no paid key). The writer brief adds: "use only everyday words and words the person said; ask exactly one short question that uses the person's own word." Each kept lesson must pass the F1 lock check and the F3 Layer 1 rule.

**F5. Variety (fixes C5).** Keep up to 3 differently worded lessons per input (v1 kept one per writer but many inputs had one survivor). No change to sampling (top-p 0.9 stays).

**F6. Round trip (C4) — an owner choice, see Q1.** The round trip is how HELM proves a spoken fact is the fact it holds, so it is not dropped. Two honest ways to stop the ear's weakness counting against the mouth:
- (a) Teach the ear the mouth's natural sentences: AI-checked mouth lessons, read back into CAS, added to the ear's lessons in the same run. The mark stays 95 % and the same reader scores it.
- (b) Keep the ear as is and add a second scorer: two AI families judge "same fact?" on every fact reply; the round trip counts if the ear agrees OR both AI families agree, labelled `AI_RATED`.
- Either way, an ASK question is scored on thing, value and month only (asking whether the new value still holds does not need to repeat the old one); that change needs the owner's word too.

## 3. What is kept, unchanged

The whole-word lock (only everyday words and words from the input), G-NO-NEW-FACT = 0, F-FALLBACK ≤ 1 in 1,000 over ≥ 1,000 exam replies, round trip ≥ 95 %, VARIED 100/100, SOUNDS-HUMAN ≥ 60 % of ≥ 300 pairs, the ear gates and keep-old, synthetic data only, test-first, amendment before code, the owner's click before money. c57 stays the accepted CTT; c59 stays unused.

## 4. Steps and cost

| Step | Where | Cost |
|---|---|---|
| F1 word list + writable census; F2 tests + fix; F3 Layer 1 tests | laptop | 0 USD |
| F3 Layer 2 census on the 989 rated c59 lines | laptop GPU (smoke-size) | 0 USD |
| F4/F5 new lessons (Anthropic helper agents, OpenAI CLI, DeepSeek API, Google free) | laptop | about 0.10 USD (DeepSeek tokens; v1 used 69,890 in / 31,756 out) |
| Amendment A-TALK-7, seal | laptop | 0 USD |
| MOUTH TRAIN v2 on one g5.xlarge (same steps as v1: about 70 min) | AWS | about 1.3 USD expected; cap 3 USD |
| AI raters | laptop | 0 USD |

**Total expected about 1.4 USD, cap 3 USD.** F6 (a) adds ear lessons to the same run (a few minutes more, within the same cap). Ledger now 115.89 of 200 USD.

## 5. Owner questions (nothing is built until these are answered)

- **Q1. Round trip (F6):** (a) teach the ear the mouth's sentences, (b) add a two-AI-family "same fact" scorer, or (c) both. Recommended: (a) — HELM's own reader stays the judge.
- **Q2. ASK scoring:** score an ASK question on thing, value and month only, not the old value? Recommended: yes.
- **Q3. Money:** cap 3 USD for the v2 training run, to be asked again with the sealed package before launch? Recommended: yes.

## 6. Forecast (honest)

The word-list fix should repair most of the broken chat, because most chat lessons could not be written at all in v1. The fallback mark (1 in 1,000) is the hardest: v1 was 41 in 1,076 before any sense check, and the sense check will reject more lines, not fewer. If v2 misses only F-FALLBACK, the expected word is `MOUTH_NO_GAIN` with a much better-sounding mouth, not `MOUTH_EARNED_KEEP`.
