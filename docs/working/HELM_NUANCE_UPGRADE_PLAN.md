# HELM nuance upgrade — measured baseline and plan (2026-10-25)

Status: baseline measured, fix not started. This exists because the owner asked the right question: is HELM's
conversation generative and nuanced, or parroted? The answer today is **parroted**, and here is the evidence.

## 1. What was measured

`eval_helm_paraphrase.py`: 7 intent families × 5 phrasings, each in a fresh session, scored against an explicit
expected behaviour. Distinctness = how many different reply strings the five phrasings produced.

| Family | Correct | Distinct replies |
|---|---:|---:|
| greeting | 3/5 | 3 |
| affect | 2/5 | 3 |
| preference | **1/5** | 3 |
| recipe valid | 5/5 | **1** |
| recipe missing water | 5/5 | **1** |
| recall (after being told) | **1/5** | 3 |
| out-of-domain refusal | 5/5 | 2 |
| **Total** | **22/35 = 0.6286** | **mean 0.4571** |

Examples of the failure mode:

- "Please keep it brief." → *"I don't have verified data on that in my system, so I won't guess without evidence."*
- "I like concise replies." → *"That's fantastic to hear! Glad you're feeling great today."*
- "Good morning." → the same positive-affect reply.
- "What did I tell you about my grandfather?" (after being told) → refusal, while "Tell me what I said about my
  grandfather." retrieves it correctly.
- Every recipe question, right or wrong, gets one of two fixed sentences.

There are **29 hard-coded whole-reply literals** in `helm_chat.py`. Recognition is a set of exact-phrase regexes, and
unknown phrasings fall into a refusal fallback.

## 2. Root causes (three, in order of impact)

1. **Intent recognition is lexical matching on specific phrases.** "I prefer short answers" is matched; "short answers
   please" is not. Paraphrase robustness is therefore near zero for preference and recall.
2. **The refusal fallback swallows unrecognised input.** An unrecognised *preference* or *affect* statement is answered
   as if it were a request for unverified factual data.
3. **Replies are whole canned strings, not compositions.** Even when the intent is right, the sentence is fixed, so
   the system cannot sound different for different inputs.

## 3. The fix, with a held-out guard

**Dev set:** the 35 variants above (already seen; used for development only).
**Held-out set (authored now, not to be used while developing):** 21 new paraphrases, 3 per family, with different
syntax and vocabulary. Written into `eval_helm_paraphrase_holdout.py` before any code change.

**Change 1 — prototype-based intent recognition.** Replace exact phrases with per-intent keyword prototypes and a
scored margin (token overlap, negation-aware), so any phrasing that carries the intent's content words is recognised.
Ambiguity falls to a clarify, never to the factual-refusal path. No model, no LLM, deterministic.

**Change 2 — compositional replies.** Each reply is assembled from parts: acknowledgement + content slot (the fact,
the memory, the computed yield) + a next-step offer. Variation comes from the parts and a deterministic seed of the
input, not from a bank of fixed sentences. Target: no whole-reply literal added; existing literals migrated.

**Change 3 — narrative retention.** Store narrative statements (who/what/where) as user facts and answer recall from
memory; the recall intent exists in Change 1, the storage is the missing half.

## 4. Acceptance (frozen before the work)

1. Held-out paraphrase accuracy ≥ **0.80** (was never measured; dev is 0.63).
2. Mean distinctness on held-out ≥ **0.70** (dev 0.46).
3. The 15-check behavioural baseline does not fall below **9/15**, and recipe arithmetic stays exact.
4. No new whole-reply literals; the count of `speech = "..."` style literals must not increase.
5. All existing tests keep passing.

## 5. What this does not promise

It does not make HELM free-form generative in the LLM sense. It makes recognition generalise beyond exact phrases and
replies composed rather than retrieved. Genuine open-ended generation is a different layer (the v0.5 proposer), and
this plan deliberately does not claim it.

## 6. Artifacts

- `eval_helm_paraphrase.py`; baseline `docs/working/HELM_PARAPHRASE_BASELINE_20261025.json`.
- Behavioural baseline `docs/working/HELM_BEHAVIOUR_BASELINE_20261025.json` (9/15).
